# =============================================================================
# Shipment Creation Tools
# =============================================================================
"""
Create shipments via postal service API.

Architecture:
- Uses PostalServiceAdapter for real shipment creation (CARRIER_MODE=real)
- Creates actual postings with tracking codes
- Auto-liberates shipment for tracking

Important:
- Real shipments auto-expire in 15 days if not physically posted
- Use for actual shipping operations, NOT for quotes

Environment Variables:
- CARRIER_MODE: 'mock' or 'real' (default: 'mock')
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

from ..adapters import get_shipping_adapter

logger = logging.getLogger(__name__)
AGENT_ID = "carrier"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


@trace_tool_call("sga_create_shipment")
async def create_shipment_tool(
    destination_name: str,
    destination_address: str,
    destination_number: str,
    destination_city: str,
    destination_state: str,
    destination_cep: str,
    weight_grams: int,
    length_cm: int = 30,
    width_cm: int = 20,
    height_cm: int = 10,
    declared_value: float = 0.0,
    destination_complement: str = "",
    destination_neighborhood: str = "",
    destination_phone: str = "",
    destination_email: str = "",
    invoice_number: Optional[str] = None,
    invoice_date: Optional[str] = None,
    invoice_value: Optional[float] = None,
    service_code: Optional[str] = None,
    auto_liberate: bool = True,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a shipment and get tracking code.

    Uses PostalServiceAdapter for real shipment creation when CARRIER_MODE=real.
    This CREATES a real posting that can be tracked and labeled.

    Warning: Real postings auto-expire in 15 days if not physically shipped.

    Args:
        destination_name: Recipient name
        destination_address: Street address
        destination_number: Street number (use "S/N" if none)
        destination_city: City name
        destination_state: State code (2 letters)
        destination_cep: Postal code (8 digits)
        weight_grams: Package weight in grams
        length_cm: Package length in cm
        width_cm: Package width in cm
        height_cm: Package height in cm
        declared_value: Declared value for insurance
        destination_complement: Address complement
        destination_neighborhood: Neighborhood
        destination_phone: Phone number
        destination_email: Email address
        invoice_number: Invoice number
        invoice_date: Invoice date (DD/MM/YYYY)
        invoice_value: Invoice total value
        service_code: Optional service code (e.g., "04162" for SEDEX)
        auto_liberate: Automatically liberate for tracking (default: True)
        session_id: Session ID for audit tracking
    """
    audit.working(
        message=f"Criando envio para {destination_name} em {destination_city}/{destination_state}",
        session_id=session_id,
    )

    try:
        adapter = get_shipping_adapter()

        # Build destination dict
        destination = {
            "nome": destination_name,
            "endereco": destination_address,
            "numero": destination_number or "S/N",
            "complemento": destination_complement,
            "bairro": destination_neighborhood,
            "cidade": destination_city,
            "uf": destination_state,
            "cep": destination_cep.replace("-", ""),
            "telefone": destination_phone,
            "email": destination_email,
        }

        # Build volumes list
        volumes = [
            {
                "peso": weight_grams,
                "altura": height_cm,
                "largura": width_cm,
                "comprimento": length_cm,
            }
        ]

        # Build invoices list if provided
        invoices = None
        if invoice_number:
            invoices = [
                {
                    "numero": invoice_number,
                    "data": invoice_date or datetime.utcnow().strftime("%d/%m/%Y"),
                    "valor": invoice_value or declared_value,
                }
            ]

        # Create shipment via adapter
        result = await adapter.create_shipment(
            origin={},  # Uses profile default
            destination=destination,
            volumes=volumes,
            invoices=invoices,
            declared_value=declared_value,
            service_code=service_code,
        )

        if result.success:
            # Auto-liberate if requested
            liberated = False
            if auto_liberate and result.tracking_code:
                try:
                    liberated = await adapter.liberate_shipment(result.tracking_code)
                except Exception as lib_err:
                    logger.warning(f"[create_shipment] Liberation failed: {lib_err}")

            audit.completed(
                message=f"Envio criado: {result.tracking_code}",
                session_id=session_id,
                details={
                    "tracking_code": result.tracking_code,
                    "price": result.price,
                    "delivery_days": result.delivery_days,
                    "liberated": liberated,
                    "adapter": adapter.adapter_name,
                },
            )

            return {
                "success": True,
                "tracking_code": result.tracking_code,
                "carrier": result.carrier,
                "service": result.service,
                "service_code": result.service_code,
                "price": result.price,
                "delivery_days": result.delivery_days,
                "estimated_delivery": result.estimated_delivery,
                "label_available": result.label_available,
                "liberated": liberated,
                "is_simulated": result.is_simulated,
                "adapter": adapter.adapter_name,
            }
        else:
            audit.error(
                message=f"Falha ao criar envio: {result.error_message}",
                session_id=session_id,
                error=result.error_message,
            )

            return {
                "success": False,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "errors": result.errors,
                "is_simulated": result.is_simulated,
            }

    except Exception as e:
        logger.error(f"[create_shipment] Error: {e}", exc_info=True)
        audit.error(message="Erro ao criar envio", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}


@trace_tool_call("sga_get_label")
async def get_label_tool(
    tracking_code: str,
    format: str = "pdf",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get shipping label for a tracking code.

    Args:
        tracking_code: Tracking code for the label
        format: Output format ('pdf' or 'zvp')
        session_id: Session ID for audit tracking

    Returns:
        Dict with label_data (base64) or error
    """
    import base64

    audit.working(
        message=f"Gerando etiqueta: {tracking_code}",
        session_id=session_id,
    )

    try:
        adapter = get_shipping_adapter()

        label_bytes = await adapter.get_label(tracking_code, format)

        if label_bytes:
            audit.completed(
                message=f"Etiqueta gerada: {tracking_code}",
                session_id=session_id,
            )

            return {
                "success": True,
                "tracking_code": tracking_code,
                "format": format,
                "label_data": base64.b64encode(label_bytes).decode("utf-8"),
                "content_type": "application/pdf" if format == "pdf" else "application/octet-stream",
                "size_bytes": len(label_bytes),
            }
        else:
            return {
                "success": False,
                "error": "Label data is empty",
            }

    except Exception as e:
        logger.error(f"[get_label] Error: {e}", exc_info=True)
        audit.error(message="Erro ao gerar etiqueta", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}
