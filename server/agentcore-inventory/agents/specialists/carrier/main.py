# =============================================================================
# CarrierAgent - Strands A2AServer Entry Point (SUPPORT)
# =============================================================================
# Carrier and shipping management support agent.
# Uses AWS Strands Agents Framework with A2A protocol (port 9000).
#
# Architecture:
# - This is a SUPPORT agent for carrier management
# - Handles carrier quotes, recommendations, and shipment tracking
# - Integrates with carrier APIs for real-time data
#
# Reference:
# - https://strandsagents.com/latest/
# - https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
# =============================================================================

import os
import sys
import logging
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer
from a2a.types import AgentSkill
from fastapi import FastAPI
import uvicorn

# Centralized model configuration (MANDATORY - Gemini 3.0 Flash for speed)
from agents.utils import get_model, AGENT_VERSION, create_gemini_model

# A2A client for inter-agent communication
from shared.a2a_client import A2AClient

# Hooks for observability (ADR-002)
from shared.hooks import LoggingHook, MetricsHook

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "carrier"
AGENT_NAME = "CarrierAgent"
AGENT_DESCRIPTION = """SUPPORT Agent for Carrier Management.

This agent handles:
1. QUOTES: Get shipping quotes from multiple carriers
2. RECOMMENDATIONS: Recommend best carrier for shipment
3. TRACKING: Track shipment status in real-time

Features:
- Multi-carrier integration
- Price/delivery optimization
- Real-time tracking
- Delivery estimation
"""

# Model configuration
MODEL_ID = get_model(AGENT_ID)  # gemini-3.0-flash (operational agent)

# =============================================================================
# Agent Skills (A2A Discovery)
# =============================================================================

AGENT_SKILLS = [
    AgentSkill(
        name="get_quotes",
        description="Get shipping quotes from multiple carriers based on origin, destination, weight, and dimensions. Returns quotes with pricing, delivery time, and carrier details.",
        tags=["shipping", "quotes", "pricing", "carriers"],
    ),
    AgentSkill(
        name="recommend_carrier",
        description="Recommend the best carrier for a shipment based on priority (cost, speed, balanced), delivery constraints, and cost limits. Provides reasoning for the recommendation.",
        tags=["shipping", "recommendation", "optimization", "carriers"],
    ),
    AgentSkill(
        name="track_shipment",
        description="Track shipment status in real-time using tracking code. Auto-detects carrier if not provided. Returns current status, movement history, and delivery estimation.",
        tags=["tracking", "shipment", "status", "delivery"],
    ),
    AgentSkill(
        name="health_check",
        description="Check agent health status and retrieve agent metadata including version, model, protocol, and specialty.",
        tags=["monitoring", "health", "status"],
    ),
]

# =============================================================================
# System Prompt (Carrier Management Specialist)
# =============================================================================

SYSTEM_PROMPT = """Voce e o **CarrierAgent** do sistema SGA (Sistema de Gestao de Ativos).

## Seu Papel

Voce e o **ESPECIALISTA** em gestao de transportadoras e logistica de envio.

## Suas Ferramentas

### 1. `get_quotes`
Obtem cotacoes de frete de multiplas transportadoras:
- Peso e dimensoes do pacote
- Origem e destino
- Prazo desejado

### 2. `recommend_carrier`
Recomenda a melhor transportadora:
- Melhor custo-beneficio
- Prazo mais rapido
- Mais confiavel para a rota

### 3. `track_shipment`
Rastreia envio em tempo real:
- Status atual
- Historico de movimentacao
- Previsao de entrega

## Transportadoras Integradas

| Transportadora | Tipo | Cobertura |
|---------------|------|-----------|
| Correios | Convencional | Nacional |
| Jadlog | Expresso | Nacional |
| Azul Cargo | Aereo | Nacional |
| Total Express | Porta-a-porta | Nacional |

## Criterios de Recomendacao

1. **Custo**: Melhor preco para o servico
2. **Prazo**: Cumprimento do prazo solicitado
3. **Confiabilidade**: Historico de entregas
4. **Cobertura**: Disponibilidade na regiao

## Regras Criticas

1. **SEMPRE** apresente multiplas opcoes
2. Destaque o melhor custo-beneficio
3. Alerte sobre restricoes de rota
4. Inclua seguro quando necessario
"""


# =============================================================================
# Tools (Strands @tool decorator)
# =============================================================================

# A2A client instance for inter-agent communication
a2a_client = A2AClient()


@tool
async def get_quotes(
    origin_cep: str,
    destination_cep: str,
    weight_kg: float,
    dimensions: Optional[Dict[str, float]] = None,
    declared_value: Optional[float] = None,
    service_type: str = "standard",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get shipping quotes from multiple carriers.

    Args:
        origin_cep: Origin CEP (postal code)
        destination_cep: Destination CEP
        weight_kg: Package weight in kg
        dimensions: Optional package dimensions {length, width, height} in cm
        declared_value: Optional declared value for insurance
        service_type: Service type (standard, express, same_day)
        session_id: Session ID for context

    Returns:
        Quotes from multiple carriers
    """
    logger.info(f"[{AGENT_NAME}] Getting quotes: {origin_cep} -> {destination_cep}")

    try:
        # Import tool implementation
        from agents.carrier.tools.quotes import get_quotes_tool

        result = await get_quotes_tool(
            origin_cep=origin_cep,
            destination_cep=destination_cep,
            weight_kg=weight_kg,
            dimensions=dimensions,
            declared_value=declared_value,
            service_type=service_type,
            session_id=session_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "CARRIER_QUOTES_RETRIEVED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "origin": origin_cep,
                "destination": destination_cep,
                "quotes_count": len(result.get("quotes", [])),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] get_quotes failed: {e}", exc_info=True)
        return {"success": False, "error": str(e), "quotes": []}


@tool
async def recommend_carrier(
    origin_cep: str,
    destination_cep: str,
    weight_kg: float,
    priority: str = "balanced",
    max_delivery_days: Optional[int] = None,
    max_cost: Optional[float] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Recommend the best carrier for shipment.

    Args:
        origin_cep: Origin CEP (postal code)
        destination_cep: Destination CEP
        weight_kg: Package weight in kg
        priority: Priority (cost, speed, balanced)
        max_delivery_days: Maximum acceptable delivery days
        max_cost: Maximum acceptable cost
        session_id: Session ID for context

    Returns:
        Carrier recommendation with reasoning
    """
    logger.info(f"[{AGENT_NAME}] Recommending carrier: {origin_cep} -> {destination_cep}")

    try:
        # Import tool implementation
        from agents.carrier.tools.recommendation import recommend_carrier_tool

        result = await recommend_carrier_tool(
            origin_cep=origin_cep,
            destination_cep=destination_cep,
            weight_kg=weight_kg,
            priority=priority,
            max_delivery_days=max_delivery_days,
            max_cost=max_cost,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] recommend_carrier failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "recommendation": None,
        }


@tool
async def track_shipment(
    tracking_code: str,
    carrier: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Track shipment status in real-time.

    Args:
        tracking_code: Shipment tracking code
        carrier: Optional carrier name (auto-detected if not provided)
        session_id: Session ID for context

    Returns:
        Tracking information with current status
    """
    logger.info(f"[{AGENT_NAME}] Tracking shipment: {tracking_code}")

    try:
        # Import tool implementation
        from agents.carrier.tools.tracking import track_shipment_tool

        result = await track_shipment_tool(
            tracking_code=tracking_code,
            carrier=carrier,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] track_shipment failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "status": "UNKNOWN",
        }


@tool
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring.

    Returns:
        Health status with agent info
    """
    return {
        "status": "healthy",
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "version": AGENT_VERSION,
        "model": MODEL_ID,
        "protocol": "A2A",
        "port": 9000,
        "role": "SUPPORT",
        "specialty": "CARRIER_MANAGEMENT",
    }


# =============================================================================
# Strands Agent Configuration
# =============================================================================

def create_agent() -> Agent:
    """
    Create Strands Agent with all tools.

    Returns:
        Configured Strands Agent with hooks (ADR-002)
    """
    return Agent(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model=create_gemini_model(AGENT_ID),  # GeminiModel via Google AI Studio
        tools=[
            get_quotes,
            recommend_carrier,
            track_shipment,
            health_check,
        ],
        system_prompt=SYSTEM_PROMPT,
        hooks=[LoggingHook(), MetricsHook()],  # ADR-002: Observability hooks
    )


# =============================================================================
# A2A Server Entry Point
# =============================================================================

def main():
    """
    Start the Strands A2AServer with FastAPI /ping endpoint.

    Port 9000 is the standard for A2A protocol.
    """
    logger.info(f"[{AGENT_NAME}] Starting Strands A2AServer on port 9000...")
    logger.info(f"[{AGENT_NAME}] Model: {MODEL_ID}")
    logger.info(f"[{AGENT_NAME}] Version: {AGENT_VERSION}")
    logger.info(f"[{AGENT_NAME}] Role: SUPPORT (Carrier Management)")
    logger.info(f"[{AGENT_NAME}] Skills registered: {len(AGENT_SKILLS)}")
    for skill in AGENT_SKILLS:
        logger.info(f"  - {skill.name}: {skill.description}")

    # Create FastAPI app
    app = FastAPI(title=AGENT_NAME, version=AGENT_VERSION)

    # Add /ping endpoint for health checks
    @app.get("/ping")
    async def ping():
        return {
            "status": "healthy",
            "agent": AGENT_ID,
            "version": AGENT_VERSION,
        }

    # Create agent
    agent = create_agent()

    # Create A2A server with version and skills for Agent Card discovery
    a2a_server = A2AServer(
        agent=agent,
        host="0.0.0.0",
        port=9000,
        serve_at_root=False,  # Mount under /a2a to avoid conflict with /ping
        version=AGENT_VERSION,
        skills=AGENT_SKILLS,
    )

    # Mount A2A server at root
    app.mount("/", a2a_server.to_fastapi_app())

    # Start server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
