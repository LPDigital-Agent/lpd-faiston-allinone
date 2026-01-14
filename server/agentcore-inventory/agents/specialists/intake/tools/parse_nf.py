# =============================================================================
# Parse NF Tool
# =============================================================================
# Parses NF (Nota Fiscal) from XML, PDF, or image formats.
# Uses Gemini Vision for scanned documents.
# =============================================================================

import logging
from typing import Dict, Any, Optional
import xml.etree.ElementTree as ET


from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

# Centralized model configuration (MANDATORY - Gemini 3.0 Pro + Thinking)
from agents.utils import get_model

logger = logging.getLogger(__name__)

AGENT_ID = "intake"
MODEL = get_model(AGENT_ID)  # gemini-3.0-pro (import tool with Thinking)
audit = AgentAuditEmitter(agent_id=AGENT_ID)


# =============================================================================
# NF Namespaces (Brazilian NFe)
# =============================================================================

NFE_NS = {
    "nfe": "http://www.portalfiscal.inf.br/nfe",
}


@trace_tool_call("sga_parse_nf")
async def parse_nf_tool(
    s3_key: str,
    file_type: str = "xml",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse NF (Nota Fiscal) from various formats.

    Supports:
    - XML: Direct structured parsing
    - PDF: Text extraction + AI
    - Image: Gemini Vision OCR

    Args:
        s3_key: S3 key where file is stored
        file_type: File type (xml, pdf, image)
        session_id: Optional session ID for audit

    Returns:
        Extraction result with NF data
    """
    audit.working(
        message=f"Lendo NF ({file_type})...",
        session_id=session_id,
    )

    try:
        # Download file from S3
        file_data = await _download_from_s3(s3_key)

        if not file_data:
            return {
                "success": False,
                "error": f"Arquivo não encontrado: {s3_key}",
            }

        # Parse based on file type
        if file_type.lower() == "xml":
            extraction = _parse_xml(file_data)
        elif file_type.lower() in ("image", "jpeg", "png"):
            extraction = await _parse_with_vision(file_data, "image")
        elif file_type.lower() == "pdf":
            # Check if PDF is scanned (image-based)
            if _is_scanned_pdf(file_data):
                extraction = await _parse_with_vision(file_data, "pdf")
            else:
                extraction = await _parse_pdf_text(file_data)
        else:
            return {
                "success": False,
                "error": f"Tipo de arquivo não suportado: {file_type}",
            }

        # Validate extraction
        if not extraction or extraction.get("confidence", 0) < 0.3:
            audit.error(
                message="Falha na extração de dados",
                session_id=session_id,
            )
            return {
                "success": False,
                "error": "Falha ao extrair dados da NF",
                "extraction": extraction,
            }

        audit.completed(
            message=f"NF lida: {extraction.get('numero', 'N/A')}",
            session_id=session_id,
            details={
                "nf_numero": extraction.get("numero"),
                "items_count": len(extraction.get("items", [])),
            },
        )

        return {
            "success": True,
            "extraction": extraction,
            "file_type": file_type,
            "items_count": len(extraction.get("items", [])),
        }

    except Exception as e:
        logger.error(f"[parse_nf] Error: {e}", exc_info=True)
        audit.error(
            message="Erro ao ler NF",
            session_id=session_id,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }


async def _download_from_s3(s3_key: str) -> Optional[bytes]:
    """Download file from S3."""
    try:
        from tools.s3_client import SGAS3Client
        s3 = SGAS3Client()
        return s3.download_file(s3_key)
    except Exception as e:
        logger.error(f"[parse_nf] S3 download error: {e}")
        return None


def _parse_xml(xml_data: bytes) -> Dict[str, Any]:
    """
    Parse NF XML (NFe format).

    Brazilian NFe XML has a specific structure defined by
    SEFAZ (Secretaria da Fazenda).
    """
    try:
        xml_text = xml_data.decode("utf-8")
        root = ET.fromstring(xml_text)

        # Find NFe element (may be nested)
        nfe = root.find(".//nfe:NFe", NFE_NS) or root.find(".//NFe") or root

        # Find infNFe element
        inf_nfe = nfe.find(".//nfe:infNFe", NFE_NS) or nfe.find(".//infNFe")

        if inf_nfe is None:
            # Try without namespace
            inf_nfe = root

        # Extract basic info
        ide = inf_nfe.find(".//nfe:ide", NFE_NS) or inf_nfe.find(".//ide") or inf_nfe
        emit = inf_nfe.find(".//nfe:emit", NFE_NS) or inf_nfe.find(".//emit")
        dest = inf_nfe.find(".//nfe:dest", NFE_NS) or inf_nfe.find(".//dest")
        total = inf_nfe.find(".//nfe:total/nfe:ICMSTot", NFE_NS) or inf_nfe.find(".//total/ICMSTot")

        # Get access key from infNFe Id attribute
        chave_acesso = ""
        if inf_nfe is not None:
            id_attr = inf_nfe.get("Id", "")
            if id_attr.startswith("NFe"):
                chave_acesso = id_attr[3:]  # Remove "NFe" prefix

        extraction = {
            "numero": _get_text(ide, "nNF"),
            "serie": _get_text(ide, "serie"),
            "chave_acesso": chave_acesso,
            "data_emissao": _get_text(ide, "dhEmi") or _get_text(ide, "dEmi"),
            "natureza_operacao": _get_text(ide, "natOp"),
            "emitente": {
                "cnpj": _get_text(emit, "CNPJ"),
                "nome": _get_text(emit, "xNome"),
                "ie": _get_text(emit, "IE"),
            } if emit is not None else {},
            "destinatario": {
                "cnpj": _get_text(dest, "CNPJ") or _get_text(dest, "CPF"),
                "nome": _get_text(dest, "xNome"),
            } if dest is not None else {},
            "valor_total": float(_get_text(total, "vNF") or 0) if total is not None else 0,
            "items": [],
            "confidence": 0.95,  # High confidence for XML parsing
            "source": "xml_parsing",
        }

        # Extract items
        det_elements = inf_nfe.findall(".//nfe:det", NFE_NS) or inf_nfe.findall(".//det")

        for det in det_elements:
            prod = det.find(".//nfe:prod", NFE_NS) or det.find(".//prod")
            if prod is None:
                continue

            item = {
                "codigo": _get_text(prod, "cProd"),
                "descricao": _get_text(prod, "xProd"),
                "ncm": _get_text(prod, "NCM"),
                "cfop": _get_text(prod, "CFOP"),
                "unidade": _get_text(prod, "uCom"),
                "quantidade": float(_get_text(prod, "qCom") or 1),
                "valor_unitario": float(_get_text(prod, "vUnCom") or 0),
                "valor_total": float(_get_text(prod, "vProd") or 0),
                "seriais": _extract_serials(_get_text(prod, "xProd") or ""),
            }
            extraction["items"].append(item)

        return extraction

    except ET.ParseError as e:
        logger.error(f"[parse_nf] XML parse error: {e}")
        return {"error": str(e), "confidence": 0, "source": "xml_parse_error"}
    except Exception as e:
        logger.error(f"[parse_nf] Error parsing XML: {e}")
        return {"error": str(e), "confidence": 0, "source": "xml_error"}


def _get_text(element, tag: str) -> str:
    """Get text from XML element, handling namespaces."""
    if element is None:
        return ""

    # Try with namespace
    child = element.find(f".//nfe:{tag}", NFE_NS)
    if child is None:
        # Try without namespace
        child = element.find(f".//{tag}")
    if child is None:
        # Try direct child
        child = element.find(tag)

    return child.text.strip() if child is not None and child.text else ""


def _extract_serials(description: str) -> list:
    """Extract serial numbers from item description."""
    import re

    serials = []

    # Common serial patterns
    patterns = [
        r"SN[:\s]*([A-Z0-9\-]+)",
        r"SERIAL[:\s]*([A-Z0-9\-]+)",
        r"S/N[:\s]*([A-Z0-9\-]+)",
        r"IMEI[:\s]*(\d{15,17})",
        r"MAC[:\s]*([A-F0-9:]{17})",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, description.upper())
        serials.extend(matches)

    return list(set(serials))  # Deduplicate


def _is_scanned_pdf(pdf_data: bytes) -> bool:
    """
    Detect if PDF is scanned (image-based).

    Simple heuristic: check for image markers and few fonts.
    """
    try:
        pdf_str = pdf_data[:50000].decode("latin-1", errors="ignore")

        has_image = "/XObject" in pdf_str and "/Image" in pdf_str
        has_dct = "/DCTDecode" in pdf_str  # JPEG
        font_count = pdf_str.count("/Font")

        return (has_image or has_dct) and font_count < 5

    except Exception:
        return True  # Default to scanned (safer)


async def _parse_pdf_text(pdf_data: bytes) -> Dict[str, Any]:
    """Parse PDF with text content using AI."""
    # For text-based PDFs, extract text and use AI
    # This is a simplified implementation
    return {
        "error": "PDF text extraction not implemented",
        "confidence": 0,
        "source": "pdf_text",
    }


async def _parse_with_vision(file_data: bytes, file_type: str) -> Dict[str, Any]:
    """
    Parse NF using Gemini Vision AI.

    Used for scanned documents (DANFE images, photographed invoices).
    """
    try:
        from google import genai
        from google.genai import types

        client = genai.Client()

        # Determine MIME type
        mime_type = "application/pdf"
        if file_data[:4] == b"\x89PNG":
            mime_type = "image/png"
        elif file_data[:2] == b"\xff\xd8":
            mime_type = "image/jpeg"
        elif file_data[:4] == b"GIF8":
            mime_type = "image/gif"

        prompt = """Extraia os dados desta Nota Fiscal (NF-e/DANFE).

## Dados a Extrair

1. **Identificação**:
   - nf_number: Número da NF
   - nf_series: Série
   - nf_key: Chave de acesso (44 dígitos)
   - nf_date: Data de emissão

2. **Emitente**:
   - supplier_cnpj: CNPJ
   - supplier_name: Razão Social
   - supplier_ie: Inscrição Estadual

3. **Destinatário**:
   - recipient_cnpj: CNPJ/CPF
   - recipient_name: Nome

4. **Itens** (lista):
   - part_number: Código do produto
   - description: Descrição
   - ncm: NCM
   - cfop: CFOP
   - unit: Unidade
   - quantity: Quantidade
   - unit_price: Valor unitário
   - total_price: Valor total
   - serial_numbers: Lista de seriais (se houver)

5. **Totais**:
   - total_value: Valor total da NF

## Resposta

Responda APENAS com JSON válido no formato:
```json
{
  "nf_number": "...",
  "nf_series": "...",
  "nf_key": "...",
  "nf_date": "...",
  "supplier_cnpj": "...",
  "supplier_name": "...",
  "recipient_cnpj": "...",
  "recipient_name": "...",
  "total_value": 0.00,
  "items": [...],
  "extraction_confidence": 0.85,
  "quality_issues": []
}
```
"""

        response = client.models.generate_content(
            model=MODEL,  # gemini-3.0-pro (import tool with Thinking)
            contents=[
                types.Part.from_bytes(data=file_data, mime_type=mime_type),
                types.Part.from_text(prompt),
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=8192,
            ),
        )

        # Parse response
        import json
        response_text = response.text

        # Try to extract JSON
        try:
            # Find JSON in response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                vision_data = json.loads(json_str)
            else:
                vision_data = {}
        except json.JSONDecodeError:
            vision_data = {"error": "Failed to parse Vision response"}

        # Map to standard format
        return _map_vision_to_standard(vision_data)

    except Exception as e:
        logger.error(f"[parse_nf] Vision error: {e}")
        return {
            "error": str(e),
            "confidence": 0,
            "source": "vision_error",
        }


def _map_vision_to_standard(vision_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map Vision AI response to standard extraction format."""
    items = []
    for item in vision_data.get("items", []):
        items.append({
            "codigo": item.get("part_number", ""),
            "descricao": item.get("description", ""),
            "ncm": item.get("ncm", ""),
            "cfop": item.get("cfop", ""),
            "unidade": item.get("unit", "UN"),
            "quantidade": float(item.get("quantity", 1)),
            "valor_unitario": float(item.get("unit_price", 0)),
            "valor_total": float(item.get("total_price", 0)),
            "seriais": item.get("serial_numbers", []),
        })

    confidence = vision_data.get("extraction_confidence", 0.7)
    quality_issues = vision_data.get("quality_issues", [])

    # Penalize for quality issues
    confidence -= len(quality_issues) * 0.05
    confidence = max(0.3, confidence)

    return {
        "numero": vision_data.get("nf_number", ""),
        "serie": vision_data.get("nf_series", ""),
        "chave_acesso": vision_data.get("nf_key", ""),
        "data_emissao": vision_data.get("nf_date", ""),
        "emitente": {
            "cnpj": vision_data.get("supplier_cnpj", ""),
            "nome": vision_data.get("supplier_name", ""),
            "ie": vision_data.get("supplier_ie", ""),
        },
        "destinatario": {
            "cnpj": vision_data.get("recipient_cnpj", ""),
            "nome": vision_data.get("recipient_name", ""),
        },
        "valor_total": float(vision_data.get("total_value", 0)),
        "items": items,
        "confidence": confidence,
        "quality_issues": quality_issues,
        "source": "vision_extraction",
    }
