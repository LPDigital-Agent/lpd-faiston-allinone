# =============================================================================
# Match Items Tool
# =============================================================================
# Matches NF items to existing part numbers in the catalog.
# Uses multiple strategies: supplier code, description AI, NCM.
# =============================================================================

import logging
from typing import Dict, Any, List, Optional


from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

# Centralized model configuration (MANDATORY - Gemini 3.0 Pro + Thinking)
from agents.utils import get_model

logger = logging.getLogger(__name__)

AGENT_ID = "intake"
MODEL = get_model(AGENT_ID)  # gemini-3.0-pro (import tool with Thinking)
audit = AgentAuditEmitter(agent_id=AGENT_ID)


@trace_tool_call("sga_match_items")
async def match_items_tool(
    items: List[Dict[str, Any]],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Match NF items to existing part numbers.

    Matching strategies (in order):
    1. Exact match on supplier code (cProd) - 95% confidence
    2. AI-assisted description matching - 70-85% confidence
    3. NCM code matching - 60% confidence

    Args:
        items: List of items from NF extraction
        session_id: Optional session ID for audit

    Returns:
        Matched and unmatched item lists
    """
    audit.working(
        message=f"Identificando {len(items)} itens...",
        session_id=session_id,
    )

    try:
        matched_items = []
        unmatched_items = []

        for item in items:
            # Try to find matching part number
            match = await _find_part_number(item)

            if match:
                matched_items.append({
                    **item,
                    "matched_pn": match["part_number"],
                    "match_confidence": match["confidence"],
                    "match_method": match["method"],
                })
            else:
                unmatched_items.append({
                    **item,
                    "suggested_pn": _suggest_part_number(item),
                })

        # Calculate overall match rate
        total = len(items)
        matched = len(matched_items)
        match_rate = matched / total if total > 0 else 0

        audit.completed(
            message=f"Identificados {matched}/{total} itens ({match_rate:.0%})",
            session_id=session_id,
            details={
                "matched": matched,
                "unmatched": len(unmatched_items),
                "match_rate": match_rate,
            },
        )

        return {
            "success": True,
            "matched_items": matched_items,
            "unmatched_items": unmatched_items,
            "match_rate": match_rate,
            "total_items": total,
        }

    except Exception as e:
        logger.error(f"[match_items] Error: {e}", exc_info=True)
        audit.error(
            message="Erro ao identificar itens",
            session_id=session_id,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
            "matched_items": [],
            "unmatched_items": items,
        }


async def _find_part_number(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Find matching part number for an NF item.

    Tries multiple strategies in order of confidence.
    """
    # Strategy 1: Match by supplier code (highest confidence)
    supplier_code = item.get("codigo")
    if supplier_code:
        pn = await _query_by_supplier_code(supplier_code)
        if pn:
            return {
                "part_number": pn["part_number"],
                "confidence": 0.95,
                "method": "supplier_code",
            }

    # Strategy 2: Match by description with AI
    description = item.get("descricao", "")
    if description and len(description) >= 5:
        pn = await _query_by_description(description)
        if pn:
            return {
                "part_number": pn["part_number"],
                "confidence": pn.get("match_score", 0.7),
                "method": "description_ai",
            }

    # Strategy 3: Match by NCM (lowest confidence)
    ncm = item.get("ncm")
    if ncm and len(ncm.replace(".", "")) >= 4:
        pn = await _query_by_ncm(ncm)
        if pn:
            return {
                "part_number": pn["part_number"],
                "confidence": 0.6,
                "method": "ncm_match",
            }

    return None


async def _query_by_supplier_code(supplier_code: str) -> Optional[Dict[str, Any]]:
    """
    Query part number by supplier code (cProd).

    This provides highest confidence as supplier codes are
    unique identifiers assigned by vendors.
    """
    if not supplier_code or not supplier_code.strip():
        return None

    try:
        from tools.db_client import DBClient
        db = DBClient()

        result = await db.query_pn_by_supplier_code(supplier_code.strip())
        return result

    except ImportError:
        logger.debug("[match_items] DBClient not available")
        return None
    except Exception as e:
        logger.warning(f"[match_items] Supplier code query error: {e}")
        return None


async def _query_by_description(description: str) -> Optional[Dict[str, Any]]:
    """
    Query part number by description using AI-powered matching.

    Extracts keywords and uses Gemini to rank candidate matches.
    """
    if not description:
        return None

    try:
        from tools.db_client import DBClient
        db = DBClient()

        # Extract keywords
        keywords = _extract_keywords(description)
        if not keywords:
            return None

        # Search for candidates
        candidates = await db.search_pn_by_keywords(keywords, limit=10)
        if not candidates:
            return None

        # Rank candidates with AI
        best_match = await _rank_with_ai(description, candidates)
        return best_match

    except ImportError:
        logger.debug("[match_items] DBClient not available")
        return None
    except Exception as e:
        logger.warning(f"[match_items] Description query error: {e}")
        return None


async def _query_by_ncm(ncm: str) -> Optional[Dict[str, Any]]:
    """
    Query part number by NCM code.

    NCM (Nomenclatura Comum do Mercosul) is a fiscal classification.
    Items with same NCM are in the same category, so confidence is lower.
    """
    try:
        from tools.db_client import DBClient
        db = DBClient()

        matches = await db.query_pn_by_ncm(ncm, limit=5)
        return matches[0] if matches else None

    except ImportError:
        return None
    except Exception as e:
        logger.warning(f"[match_items] NCM query error: {e}")
        return None


def _extract_keywords(description: str) -> List[str]:
    """
    Extract meaningful keywords from product description.

    Filters stopwords and normalizes terms.
    """
    # Common stopwords (Portuguese and English)
    stopwords = {
        "de", "da", "do", "das", "dos", "em", "para", "com", "sem", "por",
        "uma", "uns", "the", "a", "an", "and", "or", "for", "with",
        "unidade", "peca", "item", "kit", "caixa", "pacote", "lote",
    }

    # Split and clean
    words = description.upper().replace(",", " ").replace("-", " ").split()

    # Filter and normalize
    keywords = []
    for word in words:
        clean = "".join(c for c in word if c.isalnum())
        if len(clean) >= 3 and clean.lower() not in stopwords:
            keywords.append(clean)

    # Return unique keywords, max 5
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
            if len(unique) >= 5:
                break

    return unique


async def _rank_with_ai(
    target_description: str,
    candidates: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Use Gemini AI to rank candidate part numbers.
    """
    if not candidates:
        return None

    # Single candidate - use with medium confidence
    if len(candidates) == 1:
        pn = candidates[0]
        return {
            "part_number": pn.get("part_number", pn.get("PK", "").replace("PN#", "")),
            "description": pn.get("description", ""),
            "match_score": 0.75,
        }

    try:
        from google import genai
        from google.genai import types

        # Build candidate list
        candidate_list = []
        for i, pn in enumerate(candidates[:5]):
            pn_code = pn.get("part_number", pn.get("PK", "").replace("PN#", ""))
            pn_desc = pn.get("description", "")
            candidate_list.append(f"{i+1}. {pn_code}: {pn_desc}")

        prompt = f"""Analise a descrição do produto e identifique qual Part Number corresponde.

## Descrição do Produto (da NF)
{target_description}

## Catálogo de Part Numbers
{chr(10).join(candidate_list)}

## Instruções
1. Compare marca, modelo, especificações
2. Se nenhum corresponder bem, responda "NONE"

## Resposta (APENAS JSON)
{{"match_index": <1-5 ou 0 se NONE>, "confidence": <0.0-1.0>, "reason": "<explicação>"}}
"""

        client = genai.Client()
        response = client.models.generate_content(
            model=MODEL,  # gemini-3.0-pro (import tool with Thinking)
            contents=[types.Part.from_text(prompt)],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=256,
            ),
        )

        # Parse response
        import json
        response_text = response.text

        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(response_text[start:end])
            else:
                result = {}
        except json.JSONDecodeError:
            result = {}

        if result and "match_index" in result:
            idx = result.get("match_index", 0)
            confidence = result.get("confidence", 0.7)

            if idx > 0 and idx <= len(candidates):
                matched = candidates[idx - 1]
                return {
                    "part_number": matched.get("part_number", matched.get("PK", "").replace("PN#", "")),
                    "description": matched.get("description", ""),
                    "match_score": min(0.85, max(0.5, confidence)),
                    "ai_reason": result.get("reason", ""),
                }

        return None

    except Exception as e:
        logger.warning(f"[match_items] AI ranking error: {e}")
        # Fallback: return first candidate with low confidence
        if candidates:
            pn = candidates[0]
            return {
                "part_number": pn.get("part_number", pn.get("PK", "").replace("PN#", "")),
                "description": pn.get("description", ""),
                "match_score": 0.6,
            }
        return None


def _suggest_part_number(item: Dict[str, Any]) -> str:
    """
    Suggest a part number code for an unmatched item.

    Based on description and category patterns.
    """
    desc = item.get("descricao", "").upper()

    # Category-based suggestions
    if "SWITCH" in desc:
        return f"SW-{item.get('codigo', 'NEW')[:10]}"
    elif "ROUTER" in desc or "ROTEADOR" in desc:
        return f"RT-{item.get('codigo', 'NEW')[:10]}"
    elif "ACCESS POINT" in desc or " AP " in desc:
        return f"AP-{item.get('codigo', 'NEW')[:10]}"
    elif "CABO" in desc or "CABLE" in desc:
        return f"CBL-{item.get('codigo', 'NEW')[:10]}"
    elif "SFP" in desc:
        return f"SFP-{item.get('codigo', 'NEW')[:10]}"
    elif "SERVER" in desc or "SERVIDOR" in desc:
        return f"SRV-{item.get('codigo', 'NEW')[:10]}"
    else:
        return f"MISC-{item.get('codigo', 'NEW')[:10]}"
