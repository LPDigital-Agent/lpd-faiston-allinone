# =============================================================================
# Divergence Analysis Tools
# =============================================================================

import logging
from typing import Dict, Any, Optional

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "reconciliacao"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


class DivergenceType:
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


# Threshold for significant divergence (10%)
SIGNIFICANT_DIVERGENCE_THRESHOLD = 0.10


@trace_tool_call("sga_analyze_divergences")
async def analyze_divergences_tool(
    campaign_id: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze divergences for a campaign.

    Provides summary statistics, patterns, and recommendations.
    """
    audit.working(
        message=f"Analisando divergencias da campanha: {campaign_id}",
        session_id=session_id,
    )

    try:
        from tools.db_client import DBClient
        db = DBClient()

        # Get campaign
        campaign = await db.get_campaign(campaign_id)
        if not campaign:
            return {"success": False, "error": "Campanha nao encontrada"}

        # Get divergent items
        items = await db.get_campaign_items(campaign_id, status="DIVERGENT")

        if not items:
            return {
                "success": True,
                "message": "Nenhuma divergencia encontrada",
                "total_divergences": 0,
            }

        # Analyze patterns
        analysis = {
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name"),
            "total_items": campaign.get("total_items", 0),
            "counted_items": campaign.get("counted_items", 0),
            "divergent_items": len(items),
            "divergence_rate": len(items) / campaign.get("total_items", 1),
            "by_type": {
                DivergenceType.POSITIVE: 0,
                DivergenceType.NEGATIVE: 0,
            },
            "by_location": {},
            "by_part_number": {},
            "significant_divergences": [],
            "recommendations": [],
        }

        for item in items:
            system_qty = item.get("system_quantity", 0)
            counted_qty = item.get("counted_quantity", 0)
            diff = counted_qty - system_qty

            # Type analysis
            if diff > 0:
                analysis["by_type"][DivergenceType.POSITIVE] += 1
            else:
                analysis["by_type"][DivergenceType.NEGATIVE] += 1

            # Location analysis
            loc = item.get("location_id", "UNKNOWN")
            if loc not in analysis["by_location"]:
                analysis["by_location"][loc] = {"count": 0, "total_diff": 0}
            analysis["by_location"][loc]["count"] += 1
            analysis["by_location"][loc]["total_diff"] += diff

            # Part number analysis
            pn = item.get("part_number", "UNKNOWN")
            if pn not in analysis["by_part_number"]:
                analysis["by_part_number"][pn] = {"count": 0, "total_diff": 0}
            analysis["by_part_number"][pn]["count"] += 1
            analysis["by_part_number"][pn]["total_diff"] += diff

            # Significant divergences
            percentage = abs(diff) / system_qty if system_qty > 0 else 1.0
            if percentage >= SIGNIFICANT_DIVERGENCE_THRESHOLD:
                analysis["significant_divergences"].append({
                    "part_number": pn,
                    "location_id": loc,
                    "system": system_qty,
                    "counted": counted_qty,
                    "difference": diff,
                    "percentage": f"{percentage:.1%}",
                })

        # Generate recommendations
        if analysis["by_type"][DivergenceType.NEGATIVE] > analysis["by_type"][DivergenceType.POSITIVE]:
            analysis["recommendations"].append(
                "Maioria das divergencias sao NEGATIVAS (falta). "
                "Investigar possivel extravio ou erro de lancamento de saidas."
            )
        else:
            analysis["recommendations"].append(
                "Maioria das divergencias sao POSITIVAS (sobra). "
                "Investigar possivel erro de lancamento de entradas."
            )

        # Location patterns
        for loc, data in analysis["by_location"].items():
            if data["count"] > 3:
                analysis["recommendations"].append(
                    f"Local '{loc}' tem {data['count']} divergencias. "
                    "Verificar processos de movimentacao neste local."
                )

        audit.completed(
            message=f"Analise concluida: {len(items)} divergencias",
            session_id=session_id,
            details={
                "divergent_items": len(items),
                "significant": len(analysis["significant_divergences"]),
            },
        )

        return {
            "success": True,
            "analysis": analysis,
        }

    except ImportError:
        return {"success": False, "error": "DBClient not available"}
    except Exception as e:
        logger.error(f"[analyze_divergences] Error: {e}", exc_info=True)
        audit.error(message="Erro na analise de divergencias", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}
