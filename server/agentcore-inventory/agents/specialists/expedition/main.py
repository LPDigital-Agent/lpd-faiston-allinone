# =============================================================================
# ExpeditionAgent - Strands A2AServer Entry Point (SUPPORT)
# =============================================================================
# Expedition management support agent.
# Uses AWS Strands Agents Framework with A2A protocol (port 9000).
#
# Architecture:
# - This is a SUPPORT agent for expedition management
# - Handles expedition creation, stock verification, SAP export
# - Manages separation confirmation and expedition completion
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

AGENT_ID = "expedition"
AGENT_NAME = "ExpeditionAgent"
AGENT_DESCRIPTION = """SUPPORT Agent for Expedition Management.

This agent handles:
1. PROCESS: Create and process expeditions
2. STOCK: Verify stock availability for expedition
3. SAP: Generate SAP export data
4. SEPARATION: Confirm item separation
5. COMPLETE: Complete expedition workflow

Features:
- Multi-step expedition workflow
- Stock verification
- SAP integration
- Barcode scanning support
"""

# Agent Skills (A2A Agent Card)
AGENT_SKILLS = [
    AgentSkill(
        name="process_expedition",
        description="Create and process expeditions - validates items and quantities, verifies availability, generates output movement",
        parameters={
            "items": "List of items with part_number_id, quantity, and serial_numbers",
            "destination": "Destination address",
            "project_id": "Project/client ID",
            "recipient_name": "Optional recipient name",
            "notes": "Optional expedition notes",
            "session_id": "Session ID for context",
            "user_id": "User ID for audit",
        },
    ),
    AgentSkill(
        name="get_expedition",
        description="Get expedition details including status, items, and event history",
        parameters={
            "expedition_id": "Expedition ID to query",
            "session_id": "Session ID for context",
        },
    ),
    AgentSkill(
        name="verify_stock",
        description="Verify stock availability for expedition - checks available balance, existing reservations, and item locations",
        parameters={
            "items": "List of items with part_number_id and quantity",
            "location_id": "Optional location to check",
            "session_id": "Session ID for context",
        },
    ),
    AgentSkill(
        name="generate_sap_data",
        description="Generate SAP export data for expedition in MM or SD format",
        parameters={
            "expedition_id": "Expedition ID to export",
            "format_type": "SAP format (MM, SD)",
            "session_id": "Session ID for context",
        },
    ),
    AgentSkill(
        name="confirm_separation",
        description="Confirm item separation for expedition with barcode scanning and serial validation",
        parameters={
            "expedition_id": "Expedition ID",
            "scanned_items": "List of scanned items with serial_number and part_number_id",
            "session_id": "Session ID for context",
            "user_id": "User ID for audit",
        },
    ),
    AgentSkill(
        name="complete_expedition",
        description="Complete expedition and generate output NF - updates stock and notifies carrier",
        parameters={
            "expedition_id": "Expedition ID to complete",
            "carrier_id": "Optional carrier ID",
            "tracking_code": "Optional tracking code",
            "session_id": "Session ID for context",
            "user_id": "User ID for audit",
        },
    ),
    AgentSkill(
        name="health_check",
        description="Health check endpoint for monitoring - returns agent status and configuration",
        parameters={},
    ),
]

# Model configuration
MODEL_ID = get_model(AGENT_ID)  # gemini-3.0-flash (operational agent)

# =============================================================================
# System Prompt (Expedition Specialist)
# =============================================================================

SYSTEM_PROMPT = """Voce e o **ExpeditionAgent** do sistema SGA (Sistema de Gestao de Ativos).

## Seu Papel

Voce e o **ESPECIALISTA** em expedicao e saida de materiais.

## Suas Ferramentas

### 1. `process_expedition`
Cria e processa expedicoes:
- Valida itens e quantidades
- Verifica disponibilidade
- Gera movimento de saida

### 2. `get_expedition`
Consulta detalhes de expedicao:
- Status atual
- Itens incluidos
- Historico de eventos

### 3. `verify_stock`
Verifica estoque para expedicao:
- Saldo disponivel
- Reservas existentes
- Localizacao dos itens

### 4. `generate_sap_data`
Gera dados para exportacao SAP:
- Formato MM/SD
- Codigos de material
- Centro/Deposito

### 5. `confirm_separation`
Confirma separacao de itens:
- Leitura de codigo de barras
- Validacao de serial
- Registro de divergencias

### 6. `complete_expedition`
Finaliza expedicao:
- Gera NF de saida
- Atualiza estoque
- Notifica transportadora

## Fluxo de Expedicao

1. Solicitacao -> Verificacao -> Separacao -> Conferencia -> Envio

## Status de Expedicao

| Status | Descricao |
|--------|-----------|
| PENDING | Aguardando processamento |
| SEPARATING | Em separacao |
| CHECKING | Em conferencia |
| READY | Pronto para envio |
| SHIPPED | Enviado |
| DELIVERED | Entregue |
| CANCELLED | Cancelado |

## Regras Criticas

1. **SEMPRE** verifique estoque antes de processar
2. Divergencias bloqueiam a expedicao
3. Seriais devem ser conferidos individualmente
4. NF de saida e obrigatoria
"""


# =============================================================================
# Tools (Strands @tool decorator)
# =============================================================================

# A2A client instance for inter-agent communication
a2a_client = A2AClient()


@tool
async def process_expedition(
    items: List[Dict[str, Any]],
    destination: str,
    project_id: str,
    recipient_name: Optional[str] = None,
    notes: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create and process expedition.

    Args:
        items: List of items [{part_number_id, quantity, serial_numbers}]
        destination: Destination address
        project_id: Project/client ID
        recipient_name: Optional recipient name
        notes: Optional expedition notes
        session_id: Session ID for context
        user_id: User ID for audit

    Returns:
        Expedition result with expedition ID
    """
    logger.info(f"[{AGENT_NAME}] Processing expedition: {len(items)} items to {destination}")

    try:
        # Import tool implementation
        from agents.expedition.tools.process_expedition import process_expedition_tool

        result = await process_expedition_tool(
            items=items,
            destination=destination,
            project_id=project_id,
            recipient_name=recipient_name,
            notes=notes,
            session_id=session_id,
            user_id=user_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "EXPEDITION_PROCESSED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "items_count": len(items),
                "destination": destination,
                "expedition_id": result.get("expedition_id"),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] process_expedition failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def get_expedition(
    expedition_id: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get expedition details.

    Args:
        expedition_id: Expedition ID to query
        session_id: Session ID for context

    Returns:
        Expedition details with items and status
    """
    logger.info(f"[{AGENT_NAME}] Getting expedition: {expedition_id}")

    try:
        # Import tool implementation
        from agents.expedition.tools.process_expedition import get_expedition_tool

        result = await get_expedition_tool(
            expedition_id=expedition_id,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] get_expedition failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def verify_stock(
    items: List[Dict[str, Any]],
    location_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify stock availability for expedition.

    Args:
        items: List of items [{part_number_id, quantity}]
        location_id: Optional location to check
        session_id: Session ID for context

    Returns:
        Stock verification result
    """
    logger.info(f"[{AGENT_NAME}] Verifying stock for {len(items)} items")

    try:
        # Import tool implementation
        from agents.expedition.tools.verify_stock import verify_stock_tool

        result = await verify_stock_tool(
            items=items,
            location_id=location_id,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] verify_stock failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "is_available": False,
        }


@tool
async def generate_sap_data(
    expedition_id: str,
    format_type: str = "MM",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate SAP export data for expedition.

    Args:
        expedition_id: Expedition ID to export
        format_type: SAP format (MM, SD)
        session_id: Session ID for context

    Returns:
        SAP data in requested format
    """
    logger.info(f"[{AGENT_NAME}] Generating SAP data: {expedition_id}")

    try:
        # Import tool implementation
        from agents.expedition.tools.sap_export import generate_sap_data_tool

        result = await generate_sap_data_tool(
            expedition_id=expedition_id,
            format_type=format_type,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] generate_sap_data failed: {e}", exc_info=True)
        return {"success": False, "error": str(e), "data": None}


@tool
async def confirm_separation(
    expedition_id: str,
    scanned_items: List[Dict[str, Any]],
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Confirm item separation for expedition.

    Args:
        expedition_id: Expedition ID
        scanned_items: List of scanned items [{serial_number, part_number_id}]
        session_id: Session ID for context
        user_id: User ID for audit

    Returns:
        Separation confirmation result
    """
    logger.info(f"[{AGENT_NAME}] Confirming separation: {expedition_id}")

    try:
        # Import tool implementation
        from agents.expedition.tools.separation import confirm_separation_tool

        result = await confirm_separation_tool(
            expedition_id=expedition_id,
            scanned_items=scanned_items,
            session_id=session_id,
            user_id=user_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] confirm_separation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "is_complete": False,
        }


@tool
async def complete_expedition(
    expedition_id: str,
    carrier_id: Optional[str] = None,
    tracking_code: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Complete expedition and generate output NF.

    Args:
        expedition_id: Expedition ID to complete
        carrier_id: Optional carrier ID
        tracking_code: Optional tracking code
        session_id: Session ID for context
        user_id: User ID for audit

    Returns:
        Completion result with NF details
    """
    logger.info(f"[{AGENT_NAME}] Completing expedition: {expedition_id}")

    try:
        # Import tool implementation
        from agents.expedition.tools.complete_expedition import complete_expedition_tool

        result = await complete_expedition_tool(
            expedition_id=expedition_id,
            carrier_id=carrier_id,
            tracking_code=tracking_code,
            session_id=session_id,
            user_id=user_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "EXPEDITION_COMPLETED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "expedition_id": expedition_id,
                "nf_number": result.get("nf_number"),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] complete_expedition failed: {e}", exc_info=True)
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
        "specialty": "EXPEDITION",
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
            process_expedition,
            get_expedition,
            verify_stock,
            generate_sap_data,
            confirm_separation,
            complete_expedition,
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
    Start the Strands A2AServer with FastAPI wrapper.

    Port 9000 is the standard for A2A protocol.
    Includes /ping endpoint for health checks.
    """
    logger.info(f"[{AGENT_NAME}] Starting Strands A2AServer on port 9000...")
    logger.info(f"[{AGENT_NAME}] Model: {MODEL_ID}")
    logger.info(f"[{AGENT_NAME}] Version: {AGENT_VERSION}")
    logger.info(f"[{AGENT_NAME}] Role: SUPPORT (Expedition)")
    logger.info(f"[{AGENT_NAME}] Skills: {len(AGENT_SKILLS)} skills registered")
    for skill in AGENT_SKILLS:
        logger.info(f"[{AGENT_NAME}]   - {skill.name}: {skill.description}")

    # Create FastAPI app first
    app = FastAPI(title=AGENT_NAME, version=AGENT_VERSION)

    # Add /ping endpoint
    @app.get("/ping")
    async def ping():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "agent": AGENT_ID,
            "version": AGENT_VERSION,
        }

    # Create agent
    agent = create_agent()

    # Create A2A server with Agent Card discovery
    a2a_server = A2AServer(
        agent=agent,
        host="0.0.0.0",
        port=9000,
        serve_at_root=False,  # Don't serve at root, we'll mount it
        version=AGENT_VERSION,
        skills=AGENT_SKILLS,
    )

    # Mount A2A server at root
    app.mount("/", a2a_server.to_fastapi_app())

    # Start server with uvicorn
    logger.info(f"[{AGENT_NAME}] FastAPI app ready with /ping endpoint")
    uvicorn.run(app, host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
