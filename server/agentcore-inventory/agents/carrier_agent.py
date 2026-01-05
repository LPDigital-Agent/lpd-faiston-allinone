# =============================================================================
# Carrier Agent - Faiston SGA Inventory
# =============================================================================
# Agent for handling shipping carrier selection and quotes.
#
# Features:
# - Get quotes from multiple carriers
# - Recommend best carrier based on cost/urgency
# - Track shipments
# - Generate shipping labels
#
# Module: Gestao de Ativos -> Gestao de Estoque
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
#
# NOTE: This agent requires external API integrations for:
# - Correios VIP API
# - Loggi API
# - Gollog/Gol Linhas Aereas API
# - Local transportadoras
#
# The implementation below provides the structure and AI recommendation
# logic, but actual API calls are stubbed pending integration setup.
# =============================================================================

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from .base_agent import BaseInventoryAgent, ConfidenceScore
from .utils import (
    RiskLevel,
    generate_id,
    now_iso,
    log_agent_action,
    parse_json_safe,
)


# =============================================================================
# Carrier Types
# =============================================================================

class CarrierType(Enum):
    """Available carrier types."""
    CORREIOS = "CORREIOS"
    LOGGI = "LOGGI"
    GOLLOG = "GOLLOG"
    TRANSPORTADORA = "TRANSPORTADORA"
    DEDICADO = "DEDICADO"


class ShippingModal(Enum):
    """Shipping modals."""
    GROUND = "GROUND"
    EXPRESS = "EXPRESS"
    AIR = "AIR"
    SAME_DAY = "SAME_DAY"


# =============================================================================
# Carrier Data Classes
# =============================================================================

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
    is_simulated: bool = True  # Flag indicating this is simulated data
    simulation_note: str = "Cotacao estimada. Valores reais podem variar."


@dataclass
class ShipmentTracking:
    """Shipment tracking information."""
    tracking_code: str
    carrier: str
    status: str
    last_update: str
    events: List[Dict[str, Any]]
    estimated_delivery: str


# =============================================================================
# Agent System Prompt
# =============================================================================

CARRIER_AGENT_INSTRUCTION = """
Voce e o CarrierAgent, agente de IA responsavel pela selecao e
cotacao de transportadoras no sistema Faiston SGA.

## Suas Responsabilidades

1. **Cotar Fretes**: Consultar preco e prazo de multiplas transportadoras
2. **Recomendar Modal**: Sugerir melhor opcao custo-beneficio
3. **Rastrear Envios**: Acompanhar status de entregas
4. **Gerar Etiquetas**: Preparar etiquetas de envio

## Transportadoras Suportadas

| Transportadora | Modal | Uso |
|----------------|-------|-----|
| Correios | Expresso/Economico | Volumes pequenos |
| Loggi | Motoboy/Van | Urbano same-day |
| Gollog | Aereo | Urgente longas distancias |
| Transportadoras | Rodoviario | Volumes grandes |
| Dedicado | Exclusivo | Equipamentos criticos |

## Regras de Negocio

### Selecao de Transportadora
- URGENTE + Longa distancia = Gollog (aereo)
- URGENTE + Urbano = Loggi (same-day)
- Normal + Pequeno = Correios SEDEX
- Normal + Grande = Transportadora rodoviaria
- Critico = Dedicado

### Aprovacao de Custos
- Frete < R$ 100: Automatico
- Frete R$ 100-500: Notificar time operacional
- Frete > R$ 500: Aprovacao do projeto

## Formato de Resposta

Responda SEMPRE em JSON estruturado:
```json
{
  "action": "get_quotes|recommend|track",
  "status": "success|pending|error",
  "quotes": [...],
  "recommendation": {...},
  "tracking": {...}
}
```
"""


# =============================================================================
# Carrier Agent Class
# =============================================================================

class CarrierAgent(BaseInventoryAgent):
    """
    Agent for handling shipping carrier selection and quotes.

    NOTE: External API integrations are stubbed. Full implementation
    requires API credentials and integration setup for:
    - Correios VIP
    - Loggi
    - Gollog
    - Local transportadoras
    """

    def __init__(self):
        super().__init__(
            name="CarrierAgent",
            instruction=CARRIER_AGENT_INSTRUCTION,
            description="Agent for carrier selection and shipping quotes",
        )

    # =========================================================================
    # Public Actions
    # =========================================================================

    async def get_quotes(
        self,
        origin_cep: str,
        destination_cep: str,
        weight_kg: float,
        dimensions: Dict[str, float],  # {length, width, height in cm}
        value: float,
        urgency: str = "NORMAL",
    ) -> Dict[str, Any]:
        """
        Get shipping quotes from available carriers.

        NOTE: Currently returns mock data. Real implementation
        requires API integrations.

        Args:
            origin_cep: Origin postal code
            destination_cep: Destination postal code
            weight_kg: Package weight in kg
            dimensions: Package dimensions in cm
            value: Declared value in R$
            urgency: Urgency level

        Returns:
            List of quotes from available carriers
        """
        log_agent_action(self.name, "get_quotes", {
            "origin": origin_cep,
            "destination": destination_cep,
            "weight": weight_kg,
        })

        # Mock quotes - replace with real API calls
        quotes = self._generate_mock_quotes(
            origin_cep, destination_cep, weight_kg, value, urgency
        )

        # Get AI recommendation
        recommendation = await self._get_ai_recommendation(
            quotes, urgency, value
        )

        return {
            "success": True,
            "quotes": [self._quote_to_dict(q) for q in quotes],
            "recommendation": recommendation,
            "note": "Cotacoes simuladas. Integracao com APIs de transportadoras pendente.",
        }

    async def recommend_carrier(
        self,
        urgency: str,
        weight_kg: float,
        value: float,
        destination_state: str,
        same_city: bool = False,
    ) -> Dict[str, Any]:
        """
        Get AI recommendation for best carrier.

        Args:
            urgency: Urgency level (LOW, NORMAL, HIGH, URGENT)
            weight_kg: Package weight
            value: Declared value
            destination_state: Destination state code (SP, RJ, etc.)
            same_city: Whether delivery is within same city

        Returns:
            Carrier recommendation with reasoning
        """
        log_agent_action(self.name, "recommend_carrier", {
            "urgency": urgency,
            "weight": weight_kg,
        })

        # Rule-based initial recommendation
        if urgency == "URGENT":
            if same_city:
                carrier = "LOGGI"
                modal = "SAME_DAY"
                reason = "Urgente na mesma cidade - Loggi same-day"
            else:
                carrier = "GOLLOG"
                modal = "AIR"
                reason = "Urgente longa distancia - Gollog aereo"
        elif weight_kg > 30:
            carrier = "TRANSPORTADORA"
            modal = "GROUND"
            reason = "Peso > 30kg - Transportadora rodoviaria"
        elif weight_kg <= 1 and urgency == "LOW":
            carrier = "CORREIOS"
            modal = "PAC"
            reason = "Pequeno e sem urgencia - PAC economico"
        else:
            carrier = "CORREIOS"
            modal = "SEDEX"
            reason = "Padrao - SEDEX"

        return {
            "success": True,
            "recommendation": {
                "carrier": carrier,
                "modal": modal,
                "reason": reason,
                "confidence": 0.85,
            },
            "alternatives": [
                {"carrier": "CORREIOS", "modal": "SEDEX"},
                {"carrier": "LOGGI", "modal": "EXPRESS"},
            ],
        }

    async def track_shipment(
        self,
        tracking_code: str,
        carrier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Track a shipment.

        NOTE: Currently returns simulated data with is_simulated flag.
        Real implementation requires API integrations with:
        - Correios VIP API
        - Loggi API
        - Gollog API

        Args:
            tracking_code: Tracking code
            carrier: Optional carrier name for faster lookup

        Returns:
            Tracking information with is_simulated flag
        """
        log_agent_action(self.name, "track_shipment", {
            "tracking_code": tracking_code,
        })

        # Simulated tracking - real API integrations pending
        return {
            "success": True,
            "is_simulated": True,
            "tracking": {
                "tracking_code": tracking_code,
                "carrier": carrier or "CORREIOS",
                "status": "UNAVAILABLE",
                "last_update": now_iso(),
                "events": [],
                "estimated_delivery": None,
            },
            "note": "Rastreamento indisponivel. Integracao com APIs de transportadoras pendente.",
        }

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _generate_mock_quotes(
        self,
        origin_cep: str,
        destination_cep: str,
        weight_kg: float,
        value: float,
        urgency: str,
    ) -> List[ShippingQuote]:
        """Generate mock quotes for demonstration."""
        quotes = []

        # CORREIOS SEDEX
        quotes.append(ShippingQuote(
            carrier="Correios",
            carrier_type="CORREIOS",
            modal="SEDEX",
            price=45.00 + (weight_kg * 5),
            delivery_days=3,
            delivery_date="2026-01-07",
            weight_limit=30.0,
            dimensions_limit="100x60x60 cm",
            available=weight_kg <= 30,
        ))

        # CORREIOS PAC
        quotes.append(ShippingQuote(
            carrier="Correios",
            carrier_type="CORREIOS",
            modal="PAC",
            price=25.00 + (weight_kg * 3),
            delivery_days=7,
            delivery_date="2026-01-11",
            weight_limit=30.0,
            dimensions_limit="100x60x60 cm",
            available=weight_kg <= 30 and urgency != "URGENT",
        ))

        # LOGGI
        quotes.append(ShippingQuote(
            carrier="Loggi",
            carrier_type="LOGGI",
            modal="EXPRESS",
            price=55.00 + (weight_kg * 8),
            delivery_days=1,
            delivery_date="2026-01-05",
            weight_limit=50.0,
            dimensions_limit="100x80x80 cm",
            available=True,
        ))

        # GOLLOG
        quotes.append(ShippingQuote(
            carrier="Gollog",
            carrier_type="GOLLOG",
            modal="AEREO",
            price=150.00 + (weight_kg * 15),
            delivery_days=1,
            delivery_date="2026-01-05",
            weight_limit=100.0,
            dimensions_limit="150x100x100 cm",
            available=True,
        ))

        return quotes

    async def _get_ai_recommendation(
        self,
        quotes: List[ShippingQuote],
        urgency: str,
        value: float,
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

    def _quote_to_dict(self, quote: ShippingQuote) -> Dict[str, Any]:
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


# =============================================================================
# Create Agent Instance
# =============================================================================

def create_carrier_agent() -> CarrierAgent:
    """Create and return CarrierAgent instance."""
    return CarrierAgent()
