# =============================================================================
# ReconciliacaoAgent - Strands A2AServer Entry Point (SUPPORT)
# =============================================================================
# Reconciliation support agent.
# Uses AWS Strands Agents Framework with A2A protocol (port 9000).
#
# Architecture:
# - This is a SUPPORT agent for inventory reconciliation
# - Handles counting campaigns, divergence analysis, adjustments
# - Manages inventory counting workflows
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

# Centralized model configuration (MANDATORY - Gemini 3.0 Flash for speed)
from agents.utils import get_model, AGENT_VERSION, create_gemini_model

# A2A client for inter-agent communication
from shared.a2a_client import A2AClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "reconciliacao"
AGENT_NAME = "ReconciliacaoAgent"
AGENT_DESCRIPTION = """SUPPORT Agent for Inventory Reconciliation.

This agent handles:
1. CAMPAIGNS: Start and manage counting campaigns
2. COUNTING: Submit and validate counts
3. DIVERGENCE: Analyze count divergences
4. ADJUSTMENT: Propose and approve adjustments

Features:
- Multi-cycle counting
- Blind counting support
- Divergence analysis
- Adjustment proposals
"""

# Model configuration
MODEL_ID = get_model(AGENT_ID)  # gemini-3.0-flash (operational agent)

# Agent Skills (A2A Agent Card)
AGENT_SKILLS = [
    AgentSkill(
        name="start_campaign",
        description="Start a counting campaign with defined scope, cycles, and blind counting support",
        parameters={
            "campaign_type": "Type of campaign (FULL, CYCLE, SPOT, PERPETUAL)",
            "scope": "Campaign scope {location_id, project_id, categories}",
            "cycles": "Number of counting cycles (default 2)",
            "blind_count": "Whether to use blind counting (default True)",
            "assigned_counters": "List of assigned counter user IDs",
            "session_id": "Session ID for context",
            "user_id": "User ID for audit"
        }
    ),
    AgentSkill(
        name="get_campaign",
        description="Get campaign details with status and progress",
        parameters={
            "campaign_id": "Campaign ID to query",
            "session_id": "Session ID for context"
        }
    ),
    AgentSkill(
        name="get_campaign_items",
        description="Get items for counting campaign with optional status filter",
        parameters={
            "campaign_id": "Campaign ID",
            "status": "Optional filter by status (PENDING, COUNTED, DIVERGENT)",
            "session_id": "Session ID for context"
        }
    ),
    AgentSkill(
        name="submit_count",
        description="Submit a count for an item with physical quantity and optional serial numbers",
        parameters={
            "campaign_id": "Campaign ID",
            "part_number_id": "Part number being counted",
            "physical_quantity": "Physical quantity counted",
            "serial_numbers": "Optional list of serial numbers found",
            "location_id": "Optional location of count",
            "notes": "Optional counting notes",
            "session_id": "Session ID for context",
            "user_id": "Counter user ID"
        }
    ),
    AgentSkill(
        name="analyze_divergences",
        description="Analyze divergences in campaign with causes and recommendations",
        parameters={
            "campaign_id": "Campaign ID to analyze",
            "threshold_percent": "Divergence threshold percentage (default 5%)",
            "session_id": "Session ID for context"
        }
    ),
    AgentSkill(
        name="propose_adjustment",
        description="Propose inventory adjustment with type, quantity, and justification",
        parameters={
            "campaign_id": "Campaign ID",
            "part_number_id": "Part number to adjust",
            "adjustment_type": "Type of adjustment (GAIN, LOSS, CORRECTION)",
            "quantity": "Adjustment quantity (positive for gain, negative for loss)",
            "justification": "Adjustment justification",
            "session_id": "Session ID for context",
            "user_id": "User proposing adjustment"
        }
    ),
    AgentSkill(
        name="complete_campaign",
        description="Complete counting campaign with optional adjustment application",
        parameters={
            "campaign_id": "Campaign ID to complete",
            "apply_adjustments": "Whether to apply approved adjustments",
            "session_id": "Session ID for context",
            "user_id": "User completing campaign"
        }
    ),
    AgentSkill(
        name="health_check",
        description="Health check endpoint for monitoring agent status",
        parameters={}
    ),
]

# =============================================================================
# System Prompt (Reconciliation Specialist)
# =============================================================================

SYSTEM_PROMPT = """Voce e o **ReconciliacaoAgent** do sistema SGA (Sistema de Gestao de Ativos).

## Seu Papel

Voce e o **ESPECIALISTA** em inventario e reconciliacao de estoque.

## Suas Ferramentas

### 1. `start_campaign`
Inicia campanha de contagem:
- Define escopo (local, projeto, categoria)
- Configura ciclos de contagem
- Atribui contadores

### 2. `get_campaign` / `get_campaign_items`
Consulta campanhas e itens:
- Status da campanha
- Itens a contar
- Progresso da contagem

### 3. `submit_count`
Registra contagem:
- Quantidade fisica
- Serial numbers
- Observacoes

### 4. `analyze_divergences`
Analisa divergencias:
- Sistema vs Fisico
- Causas provaveis
- Recomendacoes

### 5. `propose_adjustment`
Propoe ajuste de estoque:
- Tipo de ajuste
- Justificativa
- Aprovadores

### 6. `complete_campaign`
Finaliza campanha:
- Gera relatorio
- Aplica ajustes aprovados
- Fecha divergencias

## Tipos de Contagem

| Tipo | Descricao | Ciclos |
|------|-----------|--------|
| FULL | Inventario completo | 2-3 |
| CYCLE | Contagem ciclica | 1-2 |
| SPOT | Verificacao pontual | 1 |
| PERPETUAL | Continua | N/A |

## Analise de Divergencia

| Divergencia | Causa Provavel | Acao |
|-------------|---------------|------|
| +10% | Entrada nao registrada | Verificar NFs |
| -10% | Saida nao registrada | Verificar expedições |
| Serial diff | Troca de equipamento | Rastrear historico |

## Regras Criticas

1. Contagem cega (nao mostrar saldo sistema)
2. Minimo 2 ciclos para divergencias > 5%
3. Ajustes sempre requerem aprovacao
4. Manter audit trail completo
"""


# =============================================================================
# Tools (Strands @tool decorator)
# =============================================================================

# A2A client instance for inter-agent communication
a2a_client = A2AClient()


@tool
async def start_campaign(
    campaign_type: str,
    scope: Dict[str, Any],
    cycles: int = 2,
    blind_count: bool = True,
    assigned_counters: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Start a counting campaign.

    Args:
        campaign_type: Type of campaign (FULL, CYCLE, SPOT, PERPETUAL)
        scope: Campaign scope {location_id, project_id, categories}
        cycles: Number of counting cycles (default 2)
        blind_count: Whether to use blind counting (default True)
        assigned_counters: List of assigned counter user IDs
        session_id: Session ID for context
        user_id: User ID for audit

    Returns:
        Campaign creation result with campaign ID
    """
    logger.info(f"[{AGENT_NAME}] Starting campaign: {campaign_type}")

    try:
        # Import tool implementation
        from agents.reconciliacao.tools.campaign import start_campaign_tool

        result = await start_campaign_tool(
            campaign_type=campaign_type,
            scope=scope,
            cycles=cycles,
            blind_count=blind_count,
            assigned_counters=assigned_counters,
            session_id=session_id,
            user_id=user_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "CAMPAIGN_STARTED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "campaign_type": campaign_type,
                "campaign_id": result.get("campaign_id"),
                "items_count": result.get("items_count", 0),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] start_campaign failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def get_campaign(
    campaign_id: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get campaign details.

    Args:
        campaign_id: Campaign ID to query
        session_id: Session ID for context

    Returns:
        Campaign details with status and progress
    """
    logger.info(f"[{AGENT_NAME}] Getting campaign: {campaign_id}")

    try:
        # Import tool implementation
        from agents.reconciliacao.tools.campaign import get_campaign_tool

        result = await get_campaign_tool(
            campaign_id=campaign_id,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] get_campaign failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def get_campaign_items(
    campaign_id: str,
    status: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get items for counting campaign.

    Args:
        campaign_id: Campaign ID
        status: Optional filter by status (PENDING, COUNTED, DIVERGENT)
        session_id: Session ID for context

    Returns:
        Campaign items list
    """
    logger.info(f"[{AGENT_NAME}] Getting campaign items: {campaign_id}")

    try:
        # Import tool implementation
        from agents.reconciliacao.tools.campaign import get_campaign_items_tool

        result = await get_campaign_items_tool(
            campaign_id=campaign_id,
            status=status,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] get_campaign_items failed: {e}", exc_info=True)
        return {"success": False, "error": str(e), "items": []}


@tool
async def submit_count(
    campaign_id: str,
    part_number_id: str,
    physical_quantity: int,
    serial_numbers: Optional[List[str]] = None,
    location_id: Optional[str] = None,
    notes: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit a count for an item.

    Args:
        campaign_id: Campaign ID
        part_number_id: Part number being counted
        physical_quantity: Physical quantity counted
        serial_numbers: Optional list of serial numbers found
        location_id: Optional location of count
        notes: Optional counting notes
        session_id: Session ID for context
        user_id: Counter user ID

    Returns:
        Count submission result
    """
    logger.info(f"[{AGENT_NAME}] Submitting count: {part_number_id} = {physical_quantity}")

    try:
        # Import tool implementation
        from agents.reconciliacao.tools.counting import submit_count_tool

        result = await submit_count_tool(
            campaign_id=campaign_id,
            part_number_id=part_number_id,
            physical_quantity=physical_quantity,
            serial_numbers=serial_numbers,
            location_id=location_id,
            notes=notes,
            session_id=session_id,
            user_id=user_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] submit_count failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def analyze_divergences(
    campaign_id: str,
    threshold_percent: float = 5.0,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze divergences in campaign.

    Args:
        campaign_id: Campaign ID to analyze
        threshold_percent: Divergence threshold percentage (default 5%)
        session_id: Session ID for context

    Returns:
        Divergence analysis with causes and recommendations
    """
    logger.info(f"[{AGENT_NAME}] Analyzing divergences: {campaign_id}")

    try:
        # Import tool implementation
        from agents.reconciliacao.tools.divergence import analyze_divergences_tool

        result = await analyze_divergences_tool(
            campaign_id=campaign_id,
            threshold_percent=threshold_percent,
            session_id=session_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "DIVERGENCES_ANALYZED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "campaign_id": campaign_id,
                "divergences_count": result.get("divergences_count", 0),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] analyze_divergences failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "divergences": [],
        }


@tool
async def propose_adjustment(
    campaign_id: str,
    part_number_id: str,
    adjustment_type: str,
    quantity: int,
    justification: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Propose inventory adjustment.

    Args:
        campaign_id: Campaign ID
        part_number_id: Part number to adjust
        adjustment_type: Type of adjustment (GAIN, LOSS, CORRECTION)
        quantity: Adjustment quantity (positive for gain, negative for loss)
        justification: Adjustment justification
        session_id: Session ID for context
        user_id: User proposing adjustment

    Returns:
        Adjustment proposal result
    """
    logger.info(f"[{AGENT_NAME}] Proposing adjustment: {part_number_id} {adjustment_type} {quantity}")

    try:
        # Import tool implementation
        from agents.reconciliacao.tools.adjustment import propose_adjustment_tool

        result = await propose_adjustment_tool(
            campaign_id=campaign_id,
            part_number_id=part_number_id,
            adjustment_type=adjustment_type,
            quantity=quantity,
            justification=justification,
            session_id=session_id,
            user_id=user_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] propose_adjustment failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def complete_campaign(
    campaign_id: str,
    apply_adjustments: bool = False,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Complete counting campaign.

    Args:
        campaign_id: Campaign ID to complete
        apply_adjustments: Whether to apply approved adjustments
        session_id: Session ID for context
        user_id: User completing campaign

    Returns:
        Campaign completion result with summary
    """
    logger.info(f"[{AGENT_NAME}] Completing campaign: {campaign_id}")

    try:
        # Import tool implementation
        from agents.reconciliacao.tools.campaign import complete_campaign_tool

        result = await complete_campaign_tool(
            campaign_id=campaign_id,
            apply_adjustments=apply_adjustments,
            session_id=session_id,
            user_id=user_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "CAMPAIGN_COMPLETED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "campaign_id": campaign_id,
                "adjustments_applied": apply_adjustments,
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] complete_campaign failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


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
        "specialty": "RECONCILIATION",
    }


# =============================================================================
# Strands Agent Configuration
# =============================================================================

def create_agent() -> Agent:
    """
    Create Strands Agent with all tools.

    Returns:
        Configured Strands Agent
    """
    return Agent(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model=create_gemini_model(AGENT_ID),  # GeminiModel via Google AI Studio
        tools=[
            start_campaign,
            get_campaign,
            get_campaign_items,
            submit_count,
            analyze_divergences,
            propose_adjustment,
            complete_campaign,
            health_check,
        ],
        system_prompt=SYSTEM_PROMPT,
    )


# =============================================================================
# A2A Server Entry Point
# =============================================================================

def main():
    """
    Start the Strands A2AServer.

    Port 9000 is the standard for A2A protocol.
    """
    logger.info(f"[{AGENT_NAME}] Starting Strands A2AServer on port 9000...")
    logger.info(f"[{AGENT_NAME}] Model: {MODEL_ID}")
    logger.info(f"[{AGENT_NAME}] Version: {AGENT_VERSION}")
    logger.info(f"[{AGENT_NAME}] Role: SUPPORT (Reconciliation)")
    logger.info(f"[{AGENT_NAME}] Skills: {len(AGENT_SKILLS)} registered")
    for skill in AGENT_SKILLS:
        logger.info(f"[{AGENT_NAME}]   - {skill.name}: {skill.description}")

    # Create agent
    agent = create_agent()

    # Create A2A server
    a2a_server = A2AServer(
        agent=agent,
        host="0.0.0.0",
        port=9000,
        serve_at_root=True,  # Serve at / for AgentCore compatibility
        version=AGENT_VERSION,
        skills=AGENT_SKILLS,
    )

    # Start server
    a2a_server.serve()


if __name__ == "__main__":
    main()
