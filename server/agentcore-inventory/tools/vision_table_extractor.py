# =============================================================================
# Vision Table Extractor - AI-First Table Extraction via Gemini Vision API
# =============================================================================
# Extracts tabular data from images and PDFs using Gemini Vision API.
# This is the AI-First approach - NO traditional OCR libraries.
#
# Philosophy: OBSERVE (Vision) -> THINK (LLM) -> LEARN -> ACT
# The LLM sees the image and understands the data semantically.
#
# Module: Gestao de Ativos -> Gestao de Estoque -> Smart Import
# Author: Faiston NEXO Team
# Created: January 2026
# =============================================================================

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# =============================================================================
# Lazy Import for Cold Start Optimization
# =============================================================================

_genai_client = None


def _get_genai_client():
    """
    Lazy initialization of Gemini client.

    Cold start optimization: Only import google.genai when needed.
    This prevents the 30-second AgentCore timeout.
    """
    global _genai_client
    if _genai_client is None:
        from google import genai
        _genai_client = genai.Client()
        logger.info("[VisionExtractor] Gemini client initialized")
    return _genai_client


# =============================================================================
# Portuguese Vision Prompts for Inventory Table Extraction
# =============================================================================

INVENTORY_TABLE_EXTRACTION_PROMPT = """Voce e um especialista em extracao de dados tabulares de inventario e estoque.

## TAREFA
Analise a imagem/documento e extraia TODOS os dados tabulares visiveis.
Este documento pode ser: lista de materiais, planilha de inventario, relatorio de estoque,
etiquetas de produtos, romaneio de expedicao, ou similar.

## CAMPOS COMUNS DE INVENTARIO (procure ativamente)
- Part Number / Codigo / SKU / Material / PN / Cod
- Descricao / Nome do Item / Produto / Description
- Quantidade / Qtd / Qty / Quant
- Numero de Serie / Serial / SN / NS / IMEI / S/N
- Local / Deposito / Armazem / Localizacao / Location
- Projeto / Obra / Cliente / Project
- Fornecedor / Fabricante / Marca / Supplier
- Valor / Preco / Custo / Unit Value / Price
- NCM / Codigo Fiscal
- Data / Data de Entrada / Validade / Date
- Status / Situacao / Condicao / State

## FORMATO DE RESPOSTA (JSON OBRIGATORIO)

Retorne APENAS JSON valido, sem markdown, sem explicacoes:

{
  "extraction_confidence": 0.85,
  "quality_issues": [],
  "table_detected": true,
  "document_type": "planilha_inventario",
  "headers": ["coluna1", "coluna2", "coluna3"],
  "rows": [
    {"coluna1": "valor1", "coluna2": "valor2", "coluna3": "valor3"},
    {"coluna1": "valor4", "coluna2": "valor5", "coluna3": "valor6"}
  ],
  "total_rows": 2,
  "notes": "observacoes sobre a extracao"
}

## REGRAS IMPORTANTES

1. **Tabela Nao Encontrada**: Se NAO houver tabela visivel:
   {
     "extraction_confidence": 0.0,
     "quality_issues": ["Nenhuma tabela detectada na imagem"],
     "table_detected": false,
     "headers": [],
     "rows": [],
     "total_rows": 0,
     "notes": "Documento nao contem dados tabulares"
   }

2. **Legibilidade**: Se algum texto estiver ilegivel:
   - Use null para valores que nao consegue ler
   - Liste o problema em quality_issues
   - Reduza extraction_confidence proporcionalmente

3. **Valores Numericos**:
   - Mantenha como string para preservar formatacao
   - Exemplo: "1.234,56" ou "1234.56"

4. **Numeros de Serie**:
   - Procure padroes: S/N, Serial, SN:, NS:, IMEI:
   - Extraia TODOS os seriais visiveis

5. **Cabecalhos (Headers)**:
   - Use os nomes EXATAMENTE como aparecem na imagem
   - Se nao houver cabecalho claro, infira com "Coluna_1", "Coluna_2", etc.

6. **Multiplas Tabelas**:
   - Extraia a tabela PRINCIPAL (maior)
   - Mencione outras tabelas em notes

7. **Limite de Dados**:
   - Maximo de 500 linhas
   - Se houver mais, indique em notes

Analise a imagem e retorne o JSON:"""


# =============================================================================
# Response Parsing and Validation
# =============================================================================


def _extract_json_from_response(response_text: str) -> Optional[Dict]:
    """
    Extract JSON from Gemini response text.

    Handles cases where JSON is wrapped in markdown code blocks
    or has extra text before/after.
    """
    text = response_text.strip()

    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract from markdown code block
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass

    # Try to find JSON object anywhere in text
    start_idx = text.find("{")
    if start_idx >= 0:
        # Find matching closing brace
        brace_count = 0
        for i, char in enumerate(text[start_idx:], start_idx):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    try:
                        return json.loads(text[start_idx:i + 1])
                    except json.JSONDecodeError:
                        pass
                    break

    return None


def _calculate_confidence(result: Dict) -> float:
    """
    Calculate confidence score for Vision extraction.

    Factors:
    - Gemini's self-reported confidence (base)
    - Quality issues penalty (-10% each)
    - Data completeness bonus
    - Minimum floor: 30%
    """
    base_confidence = float(result.get("extraction_confidence", 0.5))
    quality_issues = result.get("quality_issues", [])
    rows = result.get("rows", [])
    headers = result.get("headers", [])

    # Apply penalties
    penalty = len(quality_issues) * 0.10  # -10% per issue
    penalty = min(penalty, 0.40)  # Cap at 40%

    # Completeness bonus
    completeness_bonus = 0.0
    if rows and headers:
        total_cells = len(rows) * len(headers)
        filled_cells = sum(
            1 for row in rows
            for h in headers
            if row.get(h) is not None and str(row.get(h)).strip()
        )
        fill_rate = filled_cells / total_cells if total_cells > 0 else 0
        if fill_rate > 0.8:
            completeness_bonus = 0.10
        elif fill_rate > 0.5:
            completeness_bonus = 0.05

    final = base_confidence - penalty + completeness_bonus
    return max(0.30, min(0.95, final))


# =============================================================================
# Vision Extraction Functions
# =============================================================================


def extract_table_from_image(
    content: bytes,
    filename: str,
) -> "WorkbookAnalysis":
    """
    Extract tabular data from image using Gemini Vision API.

    This is the AI-First approach - the LLM understands the image
    semantically and extracts structured data.

    Args:
        content: Raw image bytes (JPG, PNG, GIF)
        filename: Original filename

    Returns:
        WorkbookAnalysis with extracted table data
    """
    from tools.sheet_analyzer import (
        WorkbookAnalysis, SheetAnalysis, ColumnAnalysis,
        SheetPurpose, detect_column_mapping, normalize_column_name
    )

    reasoning_trace = []

    reasoning_trace.append({
        "type": "thought",
        "content": f"Detectei imagem: '{filename}'. Usando Gemini Vision para extrair tabela.",
    })

    # Detect MIME type from magic bytes
    mime_type = _detect_image_mime(content)

    reasoning_trace.append({
        "type": "observation",
        "content": f"Tipo de imagem: {mime_type}",
    })

    # Call Gemini Vision API
    try:
        from google.genai import types

        client = _get_genai_client()

        response = client.models.generate_content(
            model="gemini-3-pro",
            contents=[
                types.Part.from_bytes(data=content, mime_type=mime_type),
                types.Part.from_text(INVENTORY_TABLE_EXTRACTION_PROMPT),
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,  # Low for accuracy
                max_output_tokens=16384,  # Large for many rows
            ),
        )

        response_text = response.text

    except Exception as e:
        logger.error(f"[VisionExtractor] Gemini Vision call failed: {e}")
        reasoning_trace.append({
            "type": "error",
            "content": f"Erro ao chamar Gemini Vision: {str(e)}",
        })
        raise ValueError(f"Falha na análise de imagem via AI: {str(e)}")

    # Parse response
    result = _extract_json_from_response(response_text)

    if not result:
        reasoning_trace.append({
            "type": "error",
            "content": "Não foi possível extrair JSON da resposta do Gemini",
        })
        raise ValueError(
            "Não foi possível extrair dados estruturados da imagem. "
            "Por favor, envie um arquivo XLSX ou CSV."
        )

    # Check if table was detected
    if not result.get("table_detected", False):
        quality_issues = result.get("quality_issues", ["Nenhuma tabela detectada"])
        reasoning_trace.append({
            "type": "observation",
            "content": f"Nenhuma tabela detectada: {', '.join(quality_issues)}",
        })
        raise ValueError(
            "Nenhuma tabela encontrada na imagem. "
            "Certifique-se de que a imagem contém dados tabulares visíveis."
        )

    # Extract data from result
    headers = result.get("headers", [])
    rows = result.get("rows", [])
    quality_issues = result.get("quality_issues", [])
    total_rows = result.get("total_rows", len(rows))

    reasoning_trace.append({
        "type": "observation",
        "content": f"Vision extraiu {len(headers)} colunas e {len(rows)} linhas",
    })

    if quality_issues:
        for issue in quality_issues:
            reasoning_trace.append({
                "type": "warning",
                "content": f"Problema: {issue}",
            })

    # Calculate confidence
    confidence = _calculate_confidence(result)

    reasoning_trace.append({
        "type": "conclusion",
        "content": f"Confiança da extração: {confidence:.0%}",
    })

    # Build column analysis
    columns_analysis = []
    for header in headers:
        sample_values = [
            str(row.get(header, ""))[:100]
            for row in rows[:5]
            if row.get(header) is not None and str(row.get(header)).strip()
        ]

        # Detect column mapping
        mapping, map_conf = detect_column_mapping(header)

        # Detect data type from sample values
        data_type = _detect_data_type_from_samples(sample_values)

        # Count unique and null values
        all_values = [row.get(header) for row in rows]
        unique_vals = set(str(v) for v in all_values if v is not None and str(v).strip())
        null_count = sum(1 for v in all_values if v is None or str(v).strip() == "")

        columns_analysis.append(ColumnAnalysis(
            name=header,
            normalized_name=normalize_column_name(header),
            sample_values=sample_values,
            data_type=data_type,
            unique_count=len(unique_vals),
            null_count=null_count,
            is_likely_key=len(unique_vals) == len(rows) - null_count and len(unique_vals) > 1,
            suggested_mapping=mapping,
            mapping_confidence=map_conf * confidence,  # Adjust by extraction confidence
        ))

    # Build notes
    notes = [f"Extraído via Gemini Vision (confiança: {confidence:.0%})"]
    notes.extend(quality_issues)
    if result.get("notes"):
        notes.append(result["notes"])

    sheet_analysis = SheetAnalysis(
        name="Image Data (Vision)",
        row_count=total_rows,
        column_count=len(headers),
        columns=columns_analysis,
        detected_purpose=SheetPurpose.ITEMS,
        purpose_confidence=confidence,
        has_headers=True,
        suggested_action="process" if confidence >= 0.5 else "review",
        merge_target=None,
        notes=notes,
    )

    return WorkbookAnalysis(
        filename=filename,
        sheet_count=1,
        total_rows=total_rows,
        sheets=[sheet_analysis],
        relationships=[],
        recommended_strategy="vision_extraction",
        questions_for_user=[],
        reasoning_trace=reasoning_trace,
    )


def extract_table_from_pdf(
    content: bytes,
    filename: str,
) -> "WorkbookAnalysis":
    """
    Extract tabular data from PDF using Gemini Vision API.

    Gemini 3.0 Pro can process PDFs natively - no need for
    traditional PDF libraries like PyPDF2.

    Args:
        content: Raw PDF bytes
        filename: Original filename

    Returns:
        WorkbookAnalysis with extracted table data
    """
    from tools.sheet_analyzer import (
        WorkbookAnalysis, SheetAnalysis, ColumnAnalysis,
        SheetPurpose, detect_column_mapping, normalize_column_name
    )

    reasoning_trace = []

    reasoning_trace.append({
        "type": "thought",
        "content": f"Detectei PDF: '{filename}'. Usando Gemini Vision para extrair tabela.",
    })

    # Call Gemini Vision API with PDF
    try:
        from google.genai import types

        client = _get_genai_client()

        response = client.models.generate_content(
            model="gemini-3-pro",
            contents=[
                types.Part.from_bytes(data=content, mime_type="application/pdf"),
                types.Part.from_text(INVENTORY_TABLE_EXTRACTION_PROMPT),
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=16384,
            ),
        )

        response_text = response.text

    except Exception as e:
        logger.error(f"[VisionExtractor] Gemini Vision call failed for PDF: {e}")
        reasoning_trace.append({
            "type": "error",
            "content": f"Erro ao chamar Gemini Vision para PDF: {str(e)}",
        })
        raise ValueError(f"Falha na análise de PDF via AI: {str(e)}")

    # Parse response (same logic as image)
    result = _extract_json_from_response(response_text)

    if not result:
        reasoning_trace.append({
            "type": "error",
            "content": "Não foi possível extrair JSON da resposta do Gemini",
        })
        raise ValueError(
            "Não foi possível extrair dados estruturados do PDF. "
            "Por favor, envie um arquivo XLSX ou CSV."
        )

    # Check if table was detected
    if not result.get("table_detected", False):
        quality_issues = result.get("quality_issues", ["Nenhuma tabela detectada"])
        reasoning_trace.append({
            "type": "observation",
            "content": f"Nenhuma tabela detectada no PDF: {', '.join(quality_issues)}",
        })
        raise ValueError(
            "Nenhuma tabela encontrada no PDF. "
            "Certifique-se de que o PDF contém dados tabulares visíveis."
        )

    # Extract data
    headers = result.get("headers", [])
    rows = result.get("rows", [])
    quality_issues = result.get("quality_issues", [])
    total_rows = result.get("total_rows", len(rows))

    reasoning_trace.append({
        "type": "observation",
        "content": f"Vision extraiu {len(headers)} colunas e {len(rows)} linhas do PDF",
    })

    if quality_issues:
        for issue in quality_issues:
            reasoning_trace.append({
                "type": "warning",
                "content": f"Problema: {issue}",
            })

    # Calculate confidence
    confidence = _calculate_confidence(result)

    reasoning_trace.append({
        "type": "conclusion",
        "content": f"Confiança da extração: {confidence:.0%}",
    })

    # Build column analysis
    columns_analysis = []
    for header in headers:
        sample_values = [
            str(row.get(header, ""))[:100]
            for row in rows[:5]
            if row.get(header) is not None and str(row.get(header)).strip()
        ]

        mapping, map_conf = detect_column_mapping(header)
        data_type = _detect_data_type_from_samples(sample_values)

        all_values = [row.get(header) for row in rows]
        unique_vals = set(str(v) for v in all_values if v is not None and str(v).strip())
        null_count = sum(1 for v in all_values if v is None or str(v).strip() == "")

        columns_analysis.append(ColumnAnalysis(
            name=header,
            normalized_name=normalize_column_name(header),
            sample_values=sample_values,
            data_type=data_type,
            unique_count=len(unique_vals),
            null_count=null_count,
            is_likely_key=len(unique_vals) == len(rows) - null_count and len(unique_vals) > 1,
            suggested_mapping=mapping,
            mapping_confidence=map_conf * confidence,
        ))

    # Build notes
    notes = [f"Extraído de PDF via Gemini Vision (confiança: {confidence:.0%})"]
    notes.extend(quality_issues)
    if result.get("notes"):
        notes.append(result["notes"])

    sheet_analysis = SheetAnalysis(
        name="PDF Data (Vision)",
        row_count=total_rows,
        column_count=len(headers),
        columns=columns_analysis,
        detected_purpose=SheetPurpose.ITEMS,
        purpose_confidence=confidence,
        has_headers=True,
        suggested_action="process" if confidence >= 0.5 else "review",
        merge_target=None,
        notes=notes,
    )

    return WorkbookAnalysis(
        filename=filename,
        sheet_count=1,
        total_rows=total_rows,
        sheets=[sheet_analysis],
        relationships=[],
        recommended_strategy="vision_extraction",
        questions_for_user=[],
        reasoning_trace=reasoning_trace,
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _detect_image_mime(content: bytes) -> str:
    """Detect image MIME type from magic bytes."""
    if content[:4] == b'\x89PNG':
        return "image/png"
    elif content[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    elif content[:4] == b'GIF8':
        return "image/gif"
    elif content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return "image/webp"
    else:
        # Default to JPEG for unknown
        return "image/jpeg"


def _detect_data_type_from_samples(values: List[str]) -> str:
    """Detect data type from sample string values."""
    if not values:
        return "text"

    numeric_count = 0
    date_count = 0

    for v in values:
        if not v:
            continue

        # Check numeric
        try:
            float(v.replace(",", ".").replace(" ", "").replace("R$", "").replace("$", ""))
            numeric_count += 1
            continue
        except ValueError:
            pass

        # Check date patterns
        if any(sep in v for sep in ["/", "-"]) and len(v) <= 20:
            parts = v.replace("-", "/").split("/")
            if len(parts) >= 2:
                try:
                    if all(p.isdigit() for p in parts if p):
                        date_count += 1
                        continue
                except:
                    pass

    if numeric_count >= len(values) * 0.7:
        return "number"
    elif date_count >= len(values) * 0.7:
        return "date"
    else:
        return "text"
