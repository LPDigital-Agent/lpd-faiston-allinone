# =============================================================================
# ReverseAgent - Strands A2AServer Entry Point (SUPPORT)
# =============================================================================
# Returns and reverse logistics support agent.
# Uses AWS Strands Agents Framework with A2A protocol (port 9000).
#
# Architecture:
# - This is a SUPPORT agent for reverse logistics
# - Handles returns processing, origin validation, condition evaluation
# - Manages return workflows and reintegration
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "reverse"
AGENT_NAME = "ReverseAgent"
AGENT_DESCRIPTION = """SUPPORT Agent for Reverse Logistics.

This agent handles:
1. RETURNS: Process material returns
2. VALIDATION: Validate return origin
3. EVALUATION: Evaluate material condition

Features:
- Return authorization
- Condition assessment
- Origin traceability
- Reintegration workflow
"""

# Model configuration
MODEL_ID = get_model(AGENT_ID)  # gemini-3.0-flash (operational agent)

# Agent Skills for A2A Agent Card Discovery
AGENT_SKILLS = [
    AgentSkill(
        name="process_return",
        description="Process material return with origin validation, condition assessment, and reintegration workflow",
        input_schema={
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": "List of items to return [{part_number_id, quantity, serial_numbers}]",
                    "items": {"type": "object"}
                },
                "from_location": {"type": "string", "description": "Origin location of return"},
                "project_id": {"type": "string", "description": "Project/client ID"},
                "return_reason": {"type": "string", "description": "Reason for return"},
                "return_type": {
                    "type": "string",
                    "description": "Type of return",
                    "enum": ["UNUSED", "REPLACED", "DEFECTIVE", "DAMAGED", "OBSOLETE"],
                    "default": "UNUSED"
                },
                "notes": {"type": "string", "description": "Optional return notes"},
                "session_id": {"type": "string", "description": "Session ID for context"},
                "user_id": {"type": "string", "description": "User ID for audit"},
            },
            "required": ["items", "from_location", "project_id", "return_reason"],
        },
    ),
    AgentSkill(
        name="validate_origin",
        description="Validate return origin by verifying if material originated from this inventory, confirming project/client, and validating serial numbers",
        input_schema={
            "type": "object",
            "properties": {
                "serial_number": {"type": "string", "description": "Serial number to validate"},
                "part_number_id": {"type": "string", "description": "Part number ID"},
                "project_id": {"type": "string", "description": "Expected project ID"},
                "session_id": {"type": "string", "description": "Session ID for context"},
            },
            "required": [],
        },
    ),
    AgentSkill(
        name="evaluate_condition",
        description="Evaluate material condition for return and recommend action (GOOD=reintegrate, REPAIRABLE=send to repair, SCRAP=discard)",
        input_schema={
            "type": "object",
            "properties": {
                "serial_number": {"type": "string", "description": "Serial number to evaluate"},
                "part_number_id": {"type": "string", "description": "Part number ID"},
                "visual_assessment": {
                    "type": "string",
                    "description": "Visual condition",
                    "enum": ["good", "scratched", "damaged", "broken"]
                },
                "functional_test": {
                    "type": "string",
                    "description": "Functional test result",
                    "enum": ["passed", "failed", "not_tested"]
                },
                "notes": {"type": "string", "description": "Additional evaluation notes"},
                "session_id": {"type": "string", "description": "Session ID for context"},
                "user_id": {"type": "string", "description": "User ID for audit"},
            },
            "required": [],
        },
    ),
    AgentSkill(
        name="health_check",
        description="Health check endpoint for monitoring and agent discovery",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
]

# =============================================================================
# System Prompt (Reverse Logistics Specialist)
# =============================================================================

SYSTEM_PROMPT = """Voce e o **ReverseAgent** do sistema SGA (Sistema de Gestao de Ativos).

## Seu Papel

Voce e o **ESPECIALISTA** em logistica reversa e devolucoes.

## Suas Ferramentas

### 1. `process_return`
Processa devolucao de material:
- Valida origem e destino
- Registra motivo da devolucao
- Cria movimento de entrada

### 2. `validate_origin`
Valida origem da devolucao:
- Verifica se saiu deste estoque
- Confirma projeto/cliente
- Valida serial number

### 3. `evaluate_condition`
Avalia condicao do material:
- Bom estado (reintegracao)
- Danificado (reparo)
- Defeituoso (descarte)

## Tipos de Devolucao

| Tipo | Descricao | Fluxo |
|------|-----------|-------|
| UNUSED | Nao utilizado | Reintegra estoque |
| REPLACED | Substituido | Verifica garantia |
| DEFECTIVE | Defeituoso | Analise tecnica |
| DAMAGED | Danificado | Avalia reparo |
| OBSOLETE | Obsoleto | Descarte |

## Condicoes de Material

| Condicao | Acao | HIL |
|----------|------|-----|
| GOOD | Reintegra | Nao |
| REPAIRABLE | Envia reparo | Sim |
| SCRAP | Descarte | Sim |

## Regras Criticas

1. **SEMPRE** valide a origem antes de processar
2. Seriais devem ter rastreabilidade
3. Condicao determina o fluxo
4. Devolucoes de garantia tem prioridade
"""


# =============================================================================
# Tools (Strands @tool decorator)
# =============================================================================

# A2A client instance for inter-agent communication
a2a_client = A2AClient()


@tool
async def process_return(
    items: List[Dict[str, Any]],
    from_location: str,
    project_id: str,
    return_reason: str,
    return_type: str = "UNUSED",
    notes: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process material return.

    Args:
        items: List of items [{part_number_id, quantity, serial_numbers}]
        from_location: Origin location of return
        project_id: Project/client ID
        return_reason: Reason for return
        return_type: Type of return (UNUSED, REPLACED, DEFECTIVE, DAMAGED, OBSOLETE)
        notes: Optional return notes
        session_id: Session ID for context
        user_id: User ID for audit

    Returns:
        Return processing result
    """
    logger.info(f"[{AGENT_NAME}] Processing return: {len(items)} items from {from_location}")

    try:
        # Import tool implementation
        from agents.reverse.tools.process_return import process_return_tool

        result = await process_return_tool(
            items=items,
            from_location=from_location,
            project_id=project_id,
            return_reason=return_reason,
            return_type=return_type,
            notes=notes,
            session_id=session_id,
            user_id=user_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "RETURN_PROCESSED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "items_count": len(items),
                "return_type": return_type,
                "return_id": result.get("return_id"),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] process_return failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def validate_origin(
    serial_number: Optional[str] = None,
    part_number_id: Optional[str] = None,
    project_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate return origin.

    Args:
        serial_number: Serial number to validate
        part_number_id: Part number ID
        project_id: Expected project ID
        session_id: Session ID for context

    Returns:
        Origin validation result
    """
    logger.info(f"[{AGENT_NAME}] Validating origin: {serial_number or part_number_id}")

    try:
        # Import tool implementation
        from agents.reverse.tools.validate_origin import validate_origin_tool

        result = await validate_origin_tool(
            serial_number=serial_number,
            part_number_id=part_number_id,
            project_id=project_id,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] validate_origin failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "is_valid": False,
        }


@tool
async def evaluate_condition(
    serial_number: Optional[str] = None,
    part_number_id: Optional[str] = None,
    visual_assessment: Optional[str] = None,
    functional_test: Optional[str] = None,
    notes: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate material condition for return.

    Args:
        serial_number: Serial number to evaluate
        part_number_id: Part number ID
        visual_assessment: Visual condition (good, scratched, damaged, broken)
        functional_test: Functional test result (passed, failed, not_tested)
        notes: Additional evaluation notes
        session_id: Session ID for context
        user_id: User ID for audit

    Returns:
        Condition evaluation result with recommended action
    """
    logger.info(f"[{AGENT_NAME}] Evaluating condition: {serial_number or part_number_id}")

    try:
        # Import tool implementation
        from agents.reverse.tools.evaluate_condition import evaluate_condition_tool

        result = await evaluate_condition_tool(
            serial_number=serial_number,
            part_number_id=part_number_id,
            visual_assessment=visual_assessment,
            functional_test=functional_test,
            notes=notes,
            session_id=session_id,
            user_id=user_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "CONDITION_EVALUATED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "serial_number": serial_number,
                "condition": result.get("condition"),
                "recommended_action": result.get("recommended_action"),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] evaluate_condition failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "condition": "UNKNOWN",
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
        "specialty": "REVERSE_LOGISTICS",
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
            process_return,
            validate_origin,
            evaluate_condition,
            health_check,
        ],
        system_prompt=SYSTEM_PROMPT,
    )


# =============================================================================
# A2A Server Entry Point
# =============================================================================

def main():
    """
    Start the Strands A2AServer with FastAPI wrapper.

    Port 9000 is the standard for A2A protocol.
    """
    logger.info(f"[{AGENT_NAME}] Starting Strands A2AServer on port 9000...")
    logger.info(f"[{AGENT_NAME}] Model: {MODEL_ID}")
    logger.info(f"[{AGENT_NAME}] Version: {AGENT_VERSION}")
    logger.info(f"[{AGENT_NAME}] Role: SUPPORT (Reverse Logistics)")
    logger.info(f"[{AGENT_NAME}] Skills: {[skill.name for skill in AGENT_SKILLS]}")

    # Create FastAPI app first
    app = FastAPI(title=AGENT_NAME, version=AGENT_VERSION)

    # Add /ping health check endpoint
    @app.get("/ping")
    async def ping():
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
        serve_at_root=False,  # Mount at root via FastAPI
        version=AGENT_VERSION,
        skills=AGENT_SKILLS,
    )

    # Mount A2A server at root
    app.mount("/", a2a_server.to_fastapi_app())

    # Start server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
