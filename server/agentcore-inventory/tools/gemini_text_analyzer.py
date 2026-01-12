# =============================================================================
# Gemini Text Analyzer - AI-First File Analysis for CSV/XLSX
# =============================================================================
# Analyzes text-based files (CSV, XLSX) using Gemini Pro.
# This is the AI-First approach - the LLM understands the data semantically
# and provides column mappings, confidence scores, and HIL questions.
#
# Philosophy: OBSERVE (Text) -> THINK (LLM) -> LEARN -> ACT
#
# For CSV: Read raw text -> Send to Gemini
# For XLSX: Extract text (openpyxl) -> Send to Gemini
#
# Module: Gestao de Ativos -> Gestao de Estoque -> Smart Import
# Author: Faiston NEXO Team
# Created: January 2026
# =============================================================================

import logging
import json
import io
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# =============================================================================
# Lazy Import for Cold Start Optimization
# =============================================================================

_genai_client = None
_s3_client = None

S3_BUCKET = "faiston-one-sga-documents-prod"
AWS_REGION = "us-east-2"


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
        logger.info("[GeminiTextAnalyzer] Gemini client initialized")
    return _genai_client


def _get_s3_client():
    """Lazy load S3 client for cold start optimization."""
    global _s3_client
    if _s3_client is None:
        import boto3
        _s3_client = boto3.client("s3", region_name=AWS_REGION)
        logger.info("[GeminiTextAnalyzer] S3 client initialized")
    return _s3_client


# =============================================================================
# Portuguese Analysis Prompt for Inventory Data
# =============================================================================

INVENTORY_ANALYSIS_PROMPT = """Voce e um especialista em analise de dados de inventario e estoque.

## TAREFA
Analise o conteudo do arquivo (CSV ou planilha) e:
1. Identifique TODAS as colunas e seus tipos de dados
2. Sugira mapeamento para o schema do banco de dados PostgreSQL
3. Calcule confianca do mapeamento (0.0 a 1.0)
4. Gere perguntas para o usuario se confianca < 0.80

## SCHEMA DO BANCO DE DADOS POSTGRESQL
{schema_context}

## PADROES APRENDIDOS (memoria do agente)
{memory_context}

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

{{
  "success": true,
  "file_type": "csv",
  "analysis_confidence": 0.85,
  "quality_issues": [],
  "detected_encoding": "utf-8",
  "detected_delimiter": ";",
  "row_count": 1688,
  "column_count": 10,
  "columns": [
    {{
      "source_name": "Nome Original da Coluna",
      "normalized_name": "nome_normalizado",
      "suggested_mapping": "part_number",
      "mapping_confidence": 0.95,
      "data_type": "string",
      "sample_values": ["valor1", "valor2", "valor3"],
      "is_required": true
    }}
  ],
  "suggested_mappings": {{
    "Nome Original": "target_field",
    "Outra Coluna": "another_field"
  }},
  "hil_questions": [
    {{
      "field": "nome_da_coluna",
      "question": "Esta coluna contem numeros de serie ou codigos de lote?",
      "options": ["Numero de Serie", "Codigo de Lote", "Outro"],
      "reason": "Ambiguidade entre serial e lote"
    }}
  ],
  "recommended_action": "ready_for_import",
  "notes": "Arquivo com 1688 registros de expedicao"
}}

## REGRAS IMPORTANTES

1. **Mapeamento automatico**:
   - Se confianca >= 0.80: mapeamento automatico permitido
   - Se confianca < 0.80: OBRIGATORIO gerar pergunta HIL

2. **Campos obrigatorios para importacao**:
   - part_number (codigo do produto)
   - quantity (quantidade)

3. **Valores especiais**:
   - Celulas vazias: null
   - Valores numericos: manter como number
   - Datas: preservar formato original

4. **Confianca do mapeamento**:
   - 0.95+: Match exato com nome do campo
   - 0.80-0.94: Match por sinonimo ou padrao aprendido
   - 0.60-0.79: Inferencia por amostra de dados
   - <0.60: Incerto - requer HIL

5. **recommended_action**:
   - "ready_for_import": Todos mapeamentos com confianca >= 0.80
   - "needs_user_input": Algum mapeamento < 0.80
   - "error": Arquivo invalido ou campos obrigatorios faltando

## CONTEUDO DO ARQUIVO PARA ANALISE
{file_content}

Analise e retorne o JSON:"""


# =============================================================================
# Default Schema Context (PostgreSQL pending_entry_items)
# =============================================================================

DEFAULT_SCHEMA_CONTEXT = """
Tabela: pending_entry_items (itens pendentes de entrada no estoque)

Campos:
- id: UUID (auto-gerado)
- part_number: VARCHAR(100) - Codigo do produto (OBRIGATORIO)
- description: TEXT - Descricao do item
- quantity: INTEGER - Quantidade (OBRIGATORIO)
- serial_number: VARCHAR(100) - Numero de serie (opcional)
- location_code: VARCHAR(50) - Codigo do local de destino
- project_code: VARCHAR(50) - Codigo do projeto/obra
- supplier: VARCHAR(200) - Fornecedor
- unit_value: DECIMAL(12,2) - Valor unitario
- nf_number: VARCHAR(50) - Numero da nota fiscal
- nf_date: DATE - Data da nota fiscal
- status: VARCHAR(20) - Status (pending, processed, error)
- created_at: TIMESTAMP - Data de criacao
- created_by: VARCHAR(100) - Usuario que criou
- metadata: JSONB - Campos extras dinamicos
"""


# =============================================================================
# File Content Extraction
# =============================================================================

def _extract_csv_content(content: bytes, max_rows: int = 50) -> str:
    """
    Extract CSV content as text for Gemini analysis.

    Args:
        content: Raw CSV bytes
        max_rows: Max rows to sample (for prompt efficiency)

    Returns:
        CSV text with headers + sample rows
    """
    # Detect encoding
    try:
        text = content.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = content.decode("latin-1")
        encoding = "latin-1"

    lines = text.strip().split('\n')

    # Take header + sample rows
    if len(lines) > max_rows + 1:
        sample_lines = lines[:1] + lines[1:max_rows + 1]
        sample_text = '\n'.join(sample_lines)
        sample_text += f"\n\n[... mais {len(lines) - max_rows - 1} linhas ...]"
    else:
        sample_text = text

    return f"Encoding: {encoding}\nTotal linhas: {len(lines)}\n\n{sample_text}"


def _extract_xlsx_content(content: bytes, max_rows: int = 50) -> str:
    """
    Extract XLSX content as text for Gemini analysis.

    Args:
        content: Raw XLSX bytes
        max_rows: Max rows to sample

    Returns:
        JSON-like text representation of the spreadsheet
    """
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)

    sheets_data = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]

        rows_iter = ws.iter_rows(values_only=True)
        headers = next(rows_iter, None)
        if not headers:
            continue

        headers = [str(h) if h else f"Coluna_{i}" for i, h in enumerate(headers)]

        rows = []
        for i, row_values in enumerate(rows_iter):
            if i >= max_rows:
                break
            row_dict = {}
            for j, val in enumerate(row_values):
                if j < len(headers):
                    row_dict[headers[j]] = str(val) if val is not None else None
            rows.append(row_dict)

        total_rows = ws.max_row - 1 if ws.max_row else 0

        sheets_data.append({
            "sheet_name": sheet_name,
            "headers": headers,
            "sample_rows": rows,
            "total_rows": total_rows,
        })

    wb.close()

    return json.dumps(sheets_data, indent=2, ensure_ascii=False, default=str)


def _extract_xls_content(content: bytes, max_rows: int = 50) -> str:
    """
    Extract XLS (legacy Excel) content as text.

    Args:
        content: Raw XLS bytes
        max_rows: Max rows to sample

    Returns:
        JSON-like text representation
    """
    import xlrd

    wb = xlrd.open_workbook(file_contents=content)

    sheets_data = []
    for sheet_idx in range(wb.nsheets):
        ws = wb.sheet_by_index(sheet_idx)

        if ws.nrows == 0:
            continue

        headers = [str(ws.cell_value(0, c)) or f"Coluna_{c}" for c in range(ws.ncols)]

        rows = []
        for r in range(1, min(ws.nrows, max_rows + 1)):
            row_dict = {}
            for c in range(ws.ncols):
                val = ws.cell_value(r, c)
                row_dict[headers[c]] = str(val) if val else None
            rows.append(row_dict)

        sheets_data.append({
            "sheet_name": ws.name,
            "headers": headers,
            "sample_rows": rows,
            "total_rows": ws.nrows - 1,
        })

    return json.dumps(sheets_data, indent=2, ensure_ascii=False, default=str)


# =============================================================================
# Response Parsing
# =============================================================================

def _extract_json_from_response(response_text: str) -> Optional[Dict]:
    """
    Extract JSON from Gemini response text.

    Handles cases where JSON is wrapped in markdown code blocks.
    """
    text = response_text.strip()

    # Try direct JSON parse
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

    # Try to find JSON object anywhere
    start_idx = text.find("{")
    if start_idx >= 0:
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


# =============================================================================
# Main Analysis Functions
# =============================================================================

async def analyze_file_with_gemini(
    s3_key: str,
    schema_context: str = None,
    memory_context: str = None,
) -> Dict[str, Any]:
    """
    Analyze file from S3 using Gemini Pro (AI-First).

    This is the main entry point for AI-First file analysis.

    Flow:
    1. Download file from S3
    2. Extract text content (CSV as-is, XLSX to JSON)
    3. Send to Gemini with schema + memory context
    4. Return analysis with mappings and confidence

    Args:
        s3_key: S3 key where file is stored
        schema_context: Target PostgreSQL schema description
        memory_context: Prior learned patterns (optional)

    Returns:
        {
            "success": bool,
            "file_type": str,
            "analysis_confidence": float,
            "columns": [...],
            "suggested_mappings": {...},
            "hil_questions": [...],
            "recommended_action": str,
        }
    """
    logger.info(f"[GeminiTextAnalyzer] Analyzing file: {s3_key}")

    try:
        # 1. Download file from S3
        s3 = _get_s3_client()
        response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        content = response["Body"].read()

        filename = s3_key.split("/")[-1] if "/" in s3_key else s3_key
        filename_lower = filename.lower()

        # 2. Extract text content based on file type
        if filename_lower.endswith(".csv"):
            file_content = _extract_csv_content(content)
            file_type = "csv"
        elif filename_lower.endswith(".xlsx"):
            file_content = _extract_xlsx_content(content)
            file_type = "xlsx"
        elif filename_lower.endswith(".xls"):
            file_content = _extract_xls_content(content)
            file_type = "xls"
        else:
            return {
                "success": False,
                "error": f"Formato nao suportado: {filename}",
                "file_type": "unknown",
            }

        # 3. Build prompt with context
        prompt = INVENTORY_ANALYSIS_PROMPT.format(
            schema_context=schema_context or DEFAULT_SCHEMA_CONTEXT,
            memory_context=memory_context or "Nenhum padrao aprendido ainda.",
            file_content=file_content,
        )

        # 4. Call Gemini Pro
        client = _get_genai_client()
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            }
        )

        # 5. Parse response
        result = _extract_json_from_response(response.text)

        if not result:
            logger.error(f"[GeminiTextAnalyzer] Failed to parse response: {response.text[:500]}")
            return {
                "success": False,
                "error": "Falha ao processar resposta do Gemini",
                "raw_response": response.text[:1000],
            }

        # 6. Add metadata
        result["filename"] = filename
        result["file_type"] = file_type
        result["s3_key"] = s3_key

        logger.info(
            f"[GeminiTextAnalyzer] Analysis complete: "
            f"confidence={result.get('analysis_confidence', 0):.2f}, "
            f"action={result.get('recommended_action', 'unknown')}"
        )

        return result

    except Exception as e:
        logger.error(f"[GeminiTextAnalyzer] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def extract_data_with_gemini(
    s3_key: str,
    column_mappings: Dict[str, str],
    target_schema: str = None,
    max_rows: int = 5000,
) -> Dict[str, Any]:
    """
    Extract and transform data from file using Gemini (AI-First).

    This function reads the file and uses Gemini to extract
    rows transformed according to the column mappings.

    Args:
        s3_key: S3 key where file is stored
        column_mappings: Validated mappings {source_column: target_field}
        target_schema: Target table schema
        max_rows: Maximum rows to extract

    Returns:
        {
            "success": bool,
            "rows": [...],
            "row_count": int,
            "errors": [...],
        }
    """
    logger.info(f"[GeminiTextAnalyzer] Extracting data from: {s3_key}")

    try:
        # For extraction, we need the full data (not just sample)
        # Use traditional parsing here since Gemini has context limits
        # The AI-First part was the ANALYSIS, extraction is mechanical

        s3 = _get_s3_client()
        response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        content = response["Body"].read()

        filename = s3_key.split("/")[-1] if "/" in s3_key else s3_key
        filename_lower = filename.lower()

        rows = []
        errors = []

        if filename_lower.endswith(".csv"):
            rows, errors = _extract_csv_rows(content, column_mappings, max_rows)
        elif filename_lower.endswith(".xlsx"):
            rows, errors = _extract_xlsx_rows(content, column_mappings, max_rows)
        elif filename_lower.endswith(".xls"):
            rows, errors = _extract_xls_rows(content, column_mappings, max_rows)
        else:
            return {
                "success": False,
                "error": f"Formato nao suportado: {filename}",
                "rows": [],
            }

        logger.info(f"[GeminiTextAnalyzer] Extracted {len(rows)} rows, {len(errors)} errors")

        return {
            "success": True,
            "rows": rows,
            "row_count": len(rows),
            "errors": errors[:50],  # Limit errors
            "errors_count": len(errors),
        }

    except Exception as e:
        logger.error(f"[GeminiTextAnalyzer] Extract error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "rows": [],
        }


# =============================================================================
# Data Extraction Helpers (Mechanical, not AI)
# =============================================================================

def _extract_csv_rows(
    content: bytes,
    column_mappings: Dict[str, str],
    max_rows: int,
) -> tuple:
    """Extract and transform CSV rows using mappings."""
    import csv as csv_module

    # Detect encoding
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    # Detect delimiter
    sample = text[:4096]
    delimiters = [',', ';', '\t', '|']
    delimiter_counts = {d: sample.count(d) for d in delimiters}
    delimiter = max(delimiter_counts, key=delimiter_counts.get)

    lines = text.strip().split('\n')
    reader = csv_module.DictReader(lines, delimiter=delimiter)

    rows = []
    errors = []

    for i, row in enumerate(reader):
        if i >= max_rows:
            break

        try:
            transformed = {}
            for source_col, target_field in column_mappings.items():
                if source_col in row:
                    transformed[target_field] = row[source_col]

            if transformed:
                rows.append(transformed)
        except Exception as e:
            errors.append({"row": i + 2, "error": str(e)})

    return rows, errors


def _extract_xlsx_rows(
    content: bytes,
    column_mappings: Dict[str, str],
    max_rows: int,
) -> tuple:
    """Extract and transform XLSX rows using mappings."""
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)
    headers = next(rows_iter, None)

    if not headers:
        wb.close()
        return [], [{"row": 1, "error": "No headers found"}]

    headers = [str(h) if h else f"Column_{i}" for i, h in enumerate(headers)]

    rows = []
    errors = []

    for i, row_values in enumerate(rows_iter):
        if i >= max_rows:
            break

        try:
            # Build row dict
            row_dict = {}
            for j, val in enumerate(row_values):
                if j < len(headers):
                    row_dict[headers[j]] = val

            # Transform using mappings
            transformed = {}
            for source_col, target_field in column_mappings.items():
                if source_col in row_dict:
                    transformed[target_field] = row_dict[source_col]

            if transformed:
                rows.append(transformed)
        except Exception as e:
            errors.append({"row": i + 2, "error": str(e)})

    wb.close()
    return rows, errors


def _extract_xls_rows(
    content: bytes,
    column_mappings: Dict[str, str],
    max_rows: int,
) -> tuple:
    """Extract and transform XLS rows using mappings."""
    import xlrd

    wb = xlrd.open_workbook(file_contents=content)
    ws = wb.sheet_by_index(0)

    if ws.nrows == 0:
        return [], [{"row": 1, "error": "Empty sheet"}]

    headers = [str(ws.cell_value(0, c)) or f"Column_{c}" for c in range(ws.ncols)]

    rows = []
    errors = []

    for r in range(1, min(ws.nrows, max_rows + 1)):
        try:
            # Build row dict
            row_dict = {}
            for c in range(ws.ncols):
                row_dict[headers[c]] = ws.cell_value(r, c)

            # Transform using mappings
            transformed = {}
            for source_col, target_field in column_mappings.items():
                if source_col in row_dict:
                    transformed[target_field] = row_dict[source_col]

            if transformed:
                rows.append(transformed)
        except Exception as e:
            errors.append({"row": r + 1, "error": str(e)})

    return rows, errors


# =============================================================================
# Convenience Functions
# =============================================================================

def get_default_schema_context() -> str:
    """Get the default PostgreSQL schema context."""
    return DEFAULT_SCHEMA_CONTEXT


async def analyze_file_simple(s3_key: str) -> Dict[str, Any]:
    """
    Simple wrapper for file analysis with default context.

    Use this for quick analysis without custom schema/memory.
    """
    return await analyze_file_with_gemini(
        s3_key=s3_key,
        schema_context=DEFAULT_SCHEMA_CONTEXT,
        memory_context=None,
    )
