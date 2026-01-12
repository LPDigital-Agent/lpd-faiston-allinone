# =============================================================================
# ObservationAgent - Strands A2AServer Entry Point (SUPPORT)
# =============================================================================
# Audit logging and analysis support agent.
# Uses AWS Strands Agents Framework with A2A protocol (port 9000).
#
# Architecture:
# - This is a SUPPORT agent for audit trail and observation
# - Receives logging requests from other agents via A2A
# - Follows the OBSERVE -> LEARN -> ACT pattern
#
# Reference:
# - https://strandsagents.com/latest/
# - https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
# =============================================================================

import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

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

AGENT_ID = "observation"
AGENT_NAME = "ObservationAgent"
AGENT_DESCRIPTION = """SUPPORT Agent for Audit Trail and Analysis.

This agent provides:
1. EVENT LOGGING: Log events from all other agents
2. IMPORT ANALYSIS: Analyze import data quality and patterns
3. AUDIT TRAIL: Maintain comprehensive audit logs
4. PATTERN DETECTION: Identify patterns in operations

Features:
- OBSERVE -> LEARN -> ACT pattern
- Confidence scoring
- Risk level assessment
- Pattern detection
"""

# Model configuration
MODEL_ID = get_model(AGENT_ID)  # gemini-3.0-flash (operational agent)

# =============================================================================
# Agent Skills (A2A Agent Card Discovery)
# =============================================================================

AGENT_SKILLS = [
    AgentSkill(
        id="log_event",
        name="Log Event to Audit Trail",
        description="Records operational events from any agent to the centralized audit trail with full context tracking (event_type, agent_id, session_id, user_id, details).",
        tags=["observation", "audit", "logging", "compliance", "tracking"],
    ),
    AgentSkill(
        id="analyze_import",
        name="Analyze Import Data Quality",
        description="Performs intelligent analysis of import preview data following the OBSERVE -> LEARN -> ACT pattern. Generates confidence scores, risk assessments, and actionable recommendations.",
        tags=["observation", "import", "analysis", "quality", "risk-assessment", "data-validation"],
    ),
    AgentSkill(
        id="health_check",
        name="Health Check",
        description="Returns agent health status, version, model, and operational metrics for monitoring and service discovery.",
        tags=["observation", "health", "monitoring", "diagnostics"],
    ),
]

# =============================================================================
# System Prompt (Observation Specialist)
# =============================================================================

SYSTEM_PROMPT = """Voce e NEXO, o assistente de IA da Faiston One para Gestao de Estoque.

## Seu Papel
Analisar dados de importacao de ativos e gerar observacoes inteligentes
para ajudar o usuario a tomar decisoes informadas antes de confirmar a entrada.

## Padrao de Operacao: OBSERVE -> LEARN -> ACT

### OBSERVE
- Examine os dados recebidos (itens, quantidades, valores, fornecedor)
- Identifique campos preenchidos vs. campos vazios
- Note inconsistencias ou valores atipicos

### LEARN
- Detecte padroes nos dados (ex: itens semelhantes, faixa de preco)
- Compare com praticas recomendadas de gestao de estoque
- Identifique riscos potenciais (valores muito altos, quantidades grandes)

### ACT
- Gere uma pontuacao de confianca (0-100)
- Liste sugestoes de melhoria
- Alerte sobre potenciais problemas
- Resuma suas observacoes em linguagem natural

## Formato de Resposta
Responda sempre em portugues brasileiro, de forma clara e profissional.

## Fatores de Confianca
| Fator | Peso | Descricao |
|-------|------|-----------|
| data_completeness | 30% | Campos obrigatorios preenchidos |
| format_consistency | 30% | Consistencia do formato dos dados |
| value_validation | 40% | Valores dentro de faixas esperadas |

## Niveis de Risco
| Nivel | Confianca | Acao |
|-------|-----------|------|
| LOW | >= 75% | Pode prosseguir |
| MEDIUM | 50-74% | Revisar alertas |
| HIGH | < 50% | Requer aprovacao |

## Regras
- Sempre responda em portugues brasileiro
- Mantenha tom profissional mas acessivel
- Nunca inclua dados sensiveis na resposta
- Se dados estiverem incompletos, ainda gere observacoes uteis
"""


# =============================================================================
# Tools (Strands @tool decorator)
# =============================================================================

# A2A client instance for inter-agent communication
a2a_client = A2AClient()


@tool
async def log_event(
    event_type: str,
    agent_id: str,
    details: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Log an event to the audit trail.

    Args:
        event_type: Type of event (e.g., FILE_ANALYZED, IMPORT_COMPLETED)
        agent_id: ID of the agent that generated the event
        details: Optional event details
        session_id: Session ID for context
        user_id: User ID for audit

    Returns:
        Log result with event ID
    """
    logger.info(f"[{AGENT_NAME}] Logging event: {event_type} from {agent_id}")

    try:
        event_id = f"EVT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{event_type[:8]}"

        # In production, this would write to DynamoDB or PostgreSQL audit table
        log_entry = {
            "event_id": event_id,
            "event_type": event_type,
            "agent_id": agent_id,
            "session_id": session_id,
            "user_id": user_id,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        logger.info(f"[{AGENT_NAME}] Event logged: {log_entry}")

        return {
            "success": True,
            "event_id": event_id,
            "logged_at": log_entry["timestamp"],
        }

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] log_event failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def analyze_import(
    preview_data: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze import preview data and generate intelligent observations.

    Follows the OBSERVE -> LEARN -> ACT pattern:
    - OBSERVE: Examine data structure, completeness, values
    - LEARN: Identify patterns, compare with expected norms
    - ACT: Generate confidence scores and recommendations

    Args:
        preview_data: Import preview data containing items, values, etc.
        context: Optional context (project_id, location_id, user_notes)
        session_id: Session ID for audit trail

    Returns:
        Dict with observations, confidence scores, and suggestions
    """
    logger.info(f"[{AGENT_NAME}] Analyzing import data")

    try:
        # Import tool implementation
        from agents.observation.tools.analyze_import import analyze_import_tool

        result = await analyze_import_tool(
            preview_data=preview_data,
            context=context,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] analyze_import failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "confidence": {"overall": 50, "risk_level": "high"},
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
        "specialty": "AUDIT_TRAIL",
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
            log_event,
            analyze_import,
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
    Exposes /ping for health checks and / for A2A protocol.
    """
    logger.info(f"[{AGENT_NAME}] Starting Strands A2AServer on port 9000...")
    logger.info(f"[{AGENT_NAME}] Model: {MODEL_ID}")
    logger.info(f"[{AGENT_NAME}] Version: {AGENT_VERSION}")
    logger.info(f"[{AGENT_NAME}] Role: SUPPORT (Audit Trail)")
    logger.info(f"[{AGENT_NAME}] Skills: {len(AGENT_SKILLS)} registered")
    for skill in AGENT_SKILLS:
        logger.info(f"[{AGENT_NAME}]   - {skill.id}: {skill.name}")

    # Create FastAPI app first
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
        serve_at_root=False,  # Will mount to "/" via app.mount
        version=AGENT_VERSION,
        skills=AGENT_SKILLS,
    )

    # Mount A2A server at root
    app.mount("/", a2a_server.to_fastapi_app())

    # Start server with uvicorn
    logger.info(f"[{AGENT_NAME}] Ready on http://0.0.0.0:9000")
    logger.info(f"[{AGENT_NAME}] Health check: http://0.0.0.0:9000/ping")
    uvicorn.run(app, host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
