# =============================================================================
# Shipment Tracking Tools
# =============================================================================
"""
Track shipments via carrier APIs.

Architecture:
- Uses PostalServiceAdapter for real tracking (CARRIER_MODE=real)
- Requires liberation before tracking data is available
- Falls back to mock data if API unavailable

Environment Variables:
- CARRIER_MODE: 'mock' or 'real' (default: 'mock')
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

from ..adapters import get_shipping_adapter

logger = logging.getLogger(__name__)
AGENT_ID = "carrier"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


def _detect_carrier(tracking_code: str) -> str:
    """Detect carrier from tracking code format."""
    code_upper = tracking_code.upper()
    if code_upper.startswith(("SS", "SD", "SQ", "OB", "SP")):
        return "CORREIOS"
    elif code_upper.startswith("LOG"):
        return "LOGGI"
    elif code_upper.startswith("GOL"):
        return "GOLLOG"
    elif code_upper.startswith("MOCK"):
        return "MOCK"
    else:
        return "CORREIOS"  # Default assumption


@trace_tool_call("sga_track_shipment")
async def track_shipment_tool(
    tracking_code: str,
    carrier: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Track a shipment.

    Uses PostalServiceAdapter for real tracking when CARRIER_MODE=real.
    Note: For real API, liberation is required before tracking data appears.

    Args:
        tracking_code: Tracking code
        carrier: Optional carrier name for faster lookup
    """
    audit.working(
        message=f"Rastreando envio: {tracking_code}",
        session_id=session_id,
    )

    try:
        # Get adapter
        adapter = get_shipping_adapter()

        # Detect carrier if not provided
        detected_carrier = carrier or _detect_carrier(tracking_code)

        # Get tracking via adapter
        result = await adapter.track_shipment(
            tracking_code=tracking_code,
            full_details=False,
        )

        # Convert to response format
        events = []
        for event in result.events:
            events.append({
                "timestamp": event.timestamp,
                "status": event.status,
                "description": event.description,
                "location": event.location,
            })

        tracking_data = {
            "tracking_code": result.tracking_code,
            "carrier": result.carrier or detected_carrier,
            "status": result.status,
            "status_description": result.status_description,
            "last_update": datetime.utcnow().isoformat() + "Z",
            "events": events,
            "estimated_delivery": result.estimated_delivery,
            "is_delivered": result.is_delivered,
            "is_simulated": result.is_simulated,
        }

        audit.completed(
            message=f"Rastreamento consultado: {tracking_code} ({detected_carrier})",
            session_id=session_id,
            details={
                "status": result.status,
                "is_simulated": result.is_simulated,
                "adapter": adapter.adapter_name,
            },
        )

        return {
            "success": True,
            "tracking": tracking_data,
            "is_simulated": result.is_simulated,
            "adapter": adapter.adapter_name,
            "note": "" if not result.is_simulated else "Rastreamento simulado. Use CARRIER_MODE=real para dados reais.",
        }

    except Exception as e:
        logger.error(f"[track_shipment] Error: {e}", exc_info=True)
        audit.error(message="Erro ao rastrear envio", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}


@trace_tool_call("sga_liberate_shipment")
async def liberate_shipment_tool(
    tracking_code: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Liberate a shipment for tracking database access.

    Some APIs require a liberation step after creating a shipment
    before tracking data becomes available. This tool handles that.

    Args:
        tracking_code: Tracking code to liberate
    """
    audit.working(
        message=f"Liberando envio para rastreamento: {tracking_code}",
        session_id=session_id,
    )

    try:
        adapter = get_shipping_adapter()

        success = await adapter.liberate_shipment(tracking_code)

        if success:
            audit.completed(
                message=f"Envio liberado: {tracking_code}",
                session_id=session_id,
            )
            return {
                "success": True,
                "tracking_code": tracking_code,
                "liberated": True,
                "message": "Envio liberado para rastreamento",
            }
        else:
            audit.error(
                message=f"Falha ao liberar envio: {tracking_code}",
                session_id=session_id,
            )
            return {
                "success": False,
                "tracking_code": tracking_code,
                "liberated": False,
                "message": "Falha ao liberar envio",
            }

    except Exception as e:
        logger.error(f"[liberate_shipment] Error: {e}", exc_info=True)
        audit.error(message="Erro ao liberar envio", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}
