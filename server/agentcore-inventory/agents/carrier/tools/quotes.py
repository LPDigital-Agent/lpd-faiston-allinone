# =============================================================================
# Carrier Quotes Tools
# =============================================================================

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "carrier"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


@dataclass
class ShippingQuote:
    """Quote from a carrier."""
    carrier: str
    carrier_type: str
    modal: str
    price: float
    delivery_days: int
    delivery_date: str
    weight_limit: float
    dimensions_limit: str
    available: bool
    reason: str = ""
    is_simulated: bool = True
    simulation_note: str = "Cotacao estimada. Valores reais podem variar."


def _generate_mock_quotes(
    origin_cep: str,
    destination_cep: str,
    weight_kg: float,
    value: float,
    urgency: str,
) -> List[ShippingQuote]:
    """Generate mock quotes for demonstration."""
    today = datetime.utcnow()
    quotes = []

    # CORREIOS SEDEX
    sedex_days = 3
    quotes.append(ShippingQuote(
        carrier="Correios",
        carrier_type="CORREIOS",
        modal="SEDEX",
        price=45.00 + (weight_kg * 5),
        delivery_days=sedex_days,
        delivery_date=(today + timedelta(days=sedex_days)).strftime("%Y-%m-%d"),
        weight_limit=30.0,
        dimensions_limit="100x60x60 cm",
        available=weight_kg <= 30,
        reason="" if weight_kg <= 30 else "Peso excede limite",
    ))

    # CORREIOS PAC
    pac_days = 7
    quotes.append(ShippingQuote(
        carrier="Correios",
        carrier_type="CORREIOS",
        modal="PAC",
        price=25.00 + (weight_kg * 3),
        delivery_days=pac_days,
        delivery_date=(today + timedelta(days=pac_days)).strftime("%Y-%m-%d"),
        weight_limit=30.0,
        dimensions_limit="100x60x60 cm",
        available=weight_kg <= 30 and urgency != "URGENT",
        reason="" if weight_kg <= 30 else "Peso excede limite",
    ))

    # LOGGI
    loggi_days = 1
    quotes.append(ShippingQuote(
        carrier="Loggi",
        carrier_type="LOGGI",
        modal="EXPRESS",
        price=55.00 + (weight_kg * 8),
        delivery_days=loggi_days,
        delivery_date=(today + timedelta(days=loggi_days)).strftime("%Y-%m-%d"),
        weight_limit=50.0,
        dimensions_limit="100x80x80 cm",
        available=True,
    ))

    # GOLLOG
    gollog_days = 1
    quotes.append(ShippingQuote(
        carrier="Gollog",
        carrier_type="GOLLOG",
        modal="AEREO",
        price=150.00 + (weight_kg * 15),
        delivery_days=gollog_days,
        delivery_date=(today + timedelta(days=gollog_days)).strftime("%Y-%m-%d"),
        weight_limit=100.0,
        dimensions_limit="150x100x100 cm",
        available=True,
    ))

    # TRANSPORTADORA RODOVIARIA
    trans_days = 5
    quotes.append(ShippingQuote(
        carrier="Transportadora",
        carrier_type="TRANSPORTADORA",
        modal="RODOVIARIO",
        price=80.00 + (weight_kg * 2),
        delivery_days=trans_days,
        delivery_date=(today + timedelta(days=trans_days)).strftime("%Y-%m-%d"),
        weight_limit=500.0,
        dimensions_limit="200x150x150 cm",
        available=True,
    ))

    return quotes


def _quote_to_dict(quote: ShippingQuote) -> Dict[str, Any]:
    """Convert quote to dict with simulation flag."""
    return {
        "carrier": quote.carrier,
        "carrier_type": quote.carrier_type,
        "modal": quote.modal,
        "price": quote.price,
        "delivery_days": quote.delivery_days,
        "delivery_date": quote.delivery_date,
        "weight_limit": quote.weight_limit,
        "dimensions_limit": quote.dimensions_limit,
        "available": quote.available,
        "reason": quote.reason,
        "is_simulated": quote.is_simulated,
        "simulation_note": quote.simulation_note,
    }


def _get_ai_recommendation(
    quotes: List[ShippingQuote],
    urgency: str,
) -> Dict[str, Any]:
    """Get AI recommendation from quotes."""
    # Filter available quotes
    available = [q for q in quotes if q.available]

    if not available:
        return {
            "carrier": None,
            "reason": "Nenhuma opcao disponivel",
        }

    # Sort by urgency preference
    if urgency == "URGENT":
        # Fastest first
        sorted_quotes = sorted(available, key=lambda q: q.delivery_days)
    else:
        # Cheapest first
        sorted_quotes = sorted(available, key=lambda q: q.price)

    best = sorted_quotes[0]

    return {
        "carrier": best.carrier,
        "modal": best.modal,
        "price": best.price,
        "delivery_days": best.delivery_days,
        "reason": f"{'Mais rapido' if urgency == 'URGENT' else 'Melhor custo-beneficio'}",
    }


@trace_tool_call("sga_get_quotes")
async def get_quotes_tool(
    origin_cep: str,
    destination_cep: str,
    weight_kg: float,
    dimensions: Dict[str, float],
    value: float,
    urgency: str = "NORMAL",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get shipping quotes from available carriers.

    NOTE: Currently returns simulated data. Real implementation
    requires API integrations with Correios, Loggi, Gollog.

    Args:
        origin_cep: Origin postal code
        destination_cep: Destination postal code
        weight_kg: Package weight in kg
        dimensions: Package dimensions in cm {length, width, height}
        value: Declared value in R$
        urgency: Urgency level (LOW, NORMAL, HIGH, URGENT)
    """
    audit.working(
        message=f"Consultando cotacoes: {origin_cep} -> {destination_cep}",
        session_id=session_id,
    )

    try:
        # Generate mock quotes (replace with real API calls)
        quotes = _generate_mock_quotes(
            origin_cep, destination_cep, weight_kg, value, urgency
        )

        # Get AI recommendation
        recommendation = _get_ai_recommendation(quotes, urgency)

        audit.completed(
            message=f"Cotacoes obtidas: {len(quotes)} opcoes",
            session_id=session_id,
            details={"quotes_count": len(quotes), "recommended": recommendation.get("carrier")},
        )

        return {
            "success": True,
            "quotes": [_quote_to_dict(q) for q in quotes],
            "recommendation": recommendation,
            "is_simulated": True,
            "note": "Cotacoes simuladas. Integracao com APIs de transportadoras pendente.",
        }

    except Exception as e:
        logger.error(f"[get_quotes] Error: {e}", exc_info=True)
        audit.error(message="Erro ao consultar cotacoes", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}
