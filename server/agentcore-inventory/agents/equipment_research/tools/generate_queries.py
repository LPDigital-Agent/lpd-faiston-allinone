# =============================================================================
# Generate Queries Tool
# Creates optimized search queries for equipment documentation
# =============================================================================

import logging
from typing import Any, Dict, List, Optional

from google.adk.tools import tool

logger = logging.getLogger(__name__)

# =============================================================================
# Document Types
# =============================================================================

DOCUMENT_TYPES = {
    "manual": ["user manual", "owner's manual", "operating manual"],
    "datasheet": ["datasheet", "data sheet", "spec sheet"],
    "quickstart": ["quick start", "quickstart", "getting started"],
    "service": ["service manual", "maintenance manual", "repair guide"],
    "specs": ["specifications", "technical specifications", "specs"],
}


# =============================================================================
# Tool Implementation
# =============================================================================


@tool
async def generate_queries_tool(
    part_number: str,
    description: str,
    manufacturer: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate optimized search queries for finding equipment documentation.

    Uses contextual information to create queries that target:
    - User manuals
    - Datasheets
    - Quick start guides
    - Service manuals
    - Technical specifications

    Args:
        part_number: Equipment part number / SKU
        description: Equipment description
        manufacturer: Optional manufacturer name
        additional_info: Optional extra context
        session_id: Session ID for audit trail

    Returns:
        Dict with generated queries and reasoning
    """
    from shared.audit_emitter import AgentAuditEmitter

    audit = AgentAuditEmitter(agent_id="equipment_research")

    audit.working(
        f"Gerando queries para: {part_number}",
        session_id=session_id,
    )

    try:
        if not part_number and not description:
            return {
                "success": False,
                "error": "Part number ou descrição é obrigatório",
            }

        # Extract key terms from description
        desc_terms = _extract_key_terms(description)

        # Detect equipment type
        equipment_type = _detect_equipment_type(description)

        # Detect manufacturer if not provided
        detected_manufacturer = manufacturer or _detect_manufacturer(description)

        # Generate queries
        queries = []

        # Priority 1: Manual queries
        if detected_manufacturer:
            queries.append(f"{detected_manufacturer} {part_number} user manual PDF")
            queries.append(f"{detected_manufacturer} {desc_terms} manual")
        else:
            queries.append(f"{part_number} user manual PDF")
            queries.append(f"{desc_terms} manual PDF")

        # Priority 2: Datasheet queries
        queries.append(f"{part_number} datasheet PDF")
        if detected_manufacturer:
            queries.append(f"{detected_manufacturer} {desc_terms} datasheet")

        # Priority 3: Specification queries
        queries.append(f"{part_number} technical specifications")

        # Deduplicate
        queries = list(dict.fromkeys(queries))

        # Determine priorities
        doc_priorities = ["manual", "datasheet", "specs"]
        if equipment_type in ["server", "network", "storage"]:
            doc_priorities = ["datasheet", "manual", "quickstart"]

        audit.completed(
            f"Geradas {len(queries)} queries",
            session_id=session_id,
            details={
                "query_count": len(queries),
                "equipment_type": equipment_type,
            },
        )

        return {
            "success": True,
            "equipment_analysis": {
                "part_number": part_number,
                "equipment_type": equipment_type,
                "detected_manufacturer": detected_manufacturer,
                "key_terms": desc_terms,
            },
            "search_queries": queries,
            "document_priorities": doc_priorities,
            "reasoning": _generate_reasoning(
                equipment_type=equipment_type,
                manufacturer=detected_manufacturer,
                query_count=len(queries),
            ),
        }

    except Exception as e:
        logger.error(f"[generate_queries] Error: {e}", exc_info=True)
        audit.error(
            f"Erro ao gerar queries: {part_number}",
            session_id=session_id,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
            "search_queries": _fallback_queries(part_number, description),
        }


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_key_terms(description: str) -> str:
    """Extract key terms from description for search."""
    if not description:
        return ""

    # Remove common noise words
    noise_words = ["de", "da", "do", "para", "com", "the", "a", "an", "for", "with"]

    words = description.split()
    filtered = [w for w in words if w.lower() not in noise_words]

    # Take first 5 meaningful words
    return " ".join(filtered[:5])


def _detect_equipment_type(description: str) -> str:
    """Detect equipment type from description."""
    desc_lower = description.lower()

    type_keywords = {
        "server": ["server", "poweredge", "proliant", "systemx"],
        "notebook": ["notebook", "laptop", "latitude", "thinkpad", "elitebook"],
        "desktop": ["desktop", "optiplex", "thinkcentre", "prodesk"],
        "monitor": ["monitor", "display", "lcd", "led"],
        "network": ["switch", "router", "firewall", "access point", "ap"],
        "storage": ["storage", "nas", "san", "hdd", "ssd", "disk"],
        "printer": ["printer", "impressora", "multifuncional"],
        "peripheral": ["mouse", "keyboard", "teclado", "webcam"],
    }

    for eq_type, keywords in type_keywords.items():
        if any(kw in desc_lower for kw in keywords):
            return eq_type

    return "generic"


def _detect_manufacturer(description: str) -> Optional[str]:
    """Detect manufacturer from description."""
    desc_lower = description.lower()

    manufacturers = {
        "Dell": ["dell", "poweredge", "optiplex", "latitude", "precision"],
        "HP": ["hp", "hewlett", "proliant", "elitebook", "prodesk"],
        "Lenovo": ["lenovo", "thinkpad", "thinkcentre", "ideapad"],
        "Cisco": ["cisco", "catalyst", "nexus", "meraki"],
        "Intel": ["intel", "xeon", "core i"],
        "Samsung": ["samsung", "galaxy"],
        "LG": ["lg ", "lg-"],
        "Apple": ["apple", "macbook", "imac", "mac mini"],
        "NVIDIA": ["nvidia", "geforce", "quadro", "tesla"],
        "AMD": ["amd", "ryzen", "epyc", "radeon"],
    }

    for manufacturer, keywords in manufacturers.items():
        if any(kw in desc_lower for kw in keywords):
            return manufacturer

    return None


def _generate_reasoning(
    equipment_type: str,
    manufacturer: Optional[str],
    query_count: int,
) -> str:
    """Generate human-readable reasoning."""
    parts = [f"Equipamento identificado como tipo '{equipment_type}'."]

    if manufacturer:
        parts.append(f"Fabricante detectado: {manufacturer}.")
        parts.append("Queries focadas em site oficial do fabricante.")
    else:
        parts.append("Fabricante não identificado - queries genéricas.")

    parts.append(f"Geradas {query_count} queries priorizando PDFs de manuais e datasheets.")

    return " ".join(parts)


def _fallback_queries(part_number: str, description: str) -> List[str]:
    """Generate fallback queries without AI."""
    queries = []

    if part_number:
        queries.append(f"{part_number} manual PDF")
        queries.append(f"{part_number} datasheet")
        queries.append(f"{part_number} specifications")

    if description:
        terms = description.split()[:3]
        base = " ".join(terms)
        queries.append(f"{base} manual PDF")

    return queries if queries else ["equipment manual PDF"]
