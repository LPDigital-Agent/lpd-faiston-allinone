# =============================================================================
# Carrier Recommendation Tools
# =============================================================================

import logging
from typing import Dict, Any, Optional

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "carrier"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


@trace_tool_call("sga_recommend_carrier")
async def recommend_carrier_tool(
    urgency: str,
    weight_kg: float,
    value: float,
    destination_state: str,
    same_city: bool = False,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get AI recommendation for best carrier.

    Uses rule-based logic based on urgency, weight, and destination.

    Args:
        urgency: Urgency level (LOW, NORMAL, HIGH, URGENT)
        weight_kg: Package weight in kg
        value: Declared value in R$
        destination_state: Destination state code (SP, RJ, etc.)
        same_city: Whether delivery is within same city
    """
    audit.working(
        message=f"Recomendando transportadora (urgencia: {urgency}, peso: {weight_kg}kg)",
        session_id=session_id,
    )

    try:
        # Rule-based recommendation
        if urgency == "URGENT":
            if same_city:
                carrier = "LOGGI"
                modal = "SAME_DAY"
                reason = "Urgente na mesma cidade - Loggi same-day"
            else:
                carrier = "GOLLOG"
                modal = "AEREO"
                reason = "Urgente longa distancia - Gollog aereo"
        elif urgency == "HIGH":
            if same_city:
                carrier = "LOGGI"
                modal = "EXPRESS"
                reason = "Alta urgencia mesma cidade - Loggi express"
            else:
                carrier = "CORREIOS"
                modal = "SEDEX"
                reason = "Alta urgencia - SEDEX"
        elif weight_kg > 30:
            carrier = "TRANSPORTADORA"
            modal = "RODOVIARIO"
            reason = "Peso > 30kg - Transportadora rodoviaria"
        elif weight_kg <= 1 and urgency == "LOW":
            carrier = "CORREIOS"
            modal = "PAC"
            reason = "Pequeno e sem urgencia - PAC economico"
        else:
            carrier = "CORREIOS"
            modal = "SEDEX"
            reason = "Padrao - SEDEX"

        # Calculate confidence based on rule clarity
        confidence = 0.90 if urgency in ["URGENT", "LOW"] else 0.85

        # Generate alternatives
        alternatives = []
        if carrier != "CORREIOS":
            alternatives.append({"carrier": "CORREIOS", "modal": "SEDEX"})
        if carrier != "LOGGI":
            alternatives.append({"carrier": "LOGGI", "modal": "EXPRESS"})
        if weight_kg > 20 and carrier != "TRANSPORTADORA":
            alternatives.append({"carrier": "TRANSPORTADORA", "modal": "RODOVIARIO"})

        audit.completed(
            message=f"Recomendacao: {carrier} ({modal})",
            session_id=session_id,
            details={"carrier": carrier, "modal": modal, "confidence": confidence},
        )

        return {
            "success": True,
            "recommendation": {
                "carrier": carrier,
                "modal": modal,
                "reason": reason,
                "confidence": confidence,
            },
            "alternatives": alternatives[:2],  # Top 2 alternatives
            "approval_required": value > 500 or (urgency == "URGENT" and value > 100),
        }

    except Exception as e:
        logger.error(f"[recommend_carrier] Error: {e}", exc_info=True)
        audit.error(message="Erro ao recomendar transportadora", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}
