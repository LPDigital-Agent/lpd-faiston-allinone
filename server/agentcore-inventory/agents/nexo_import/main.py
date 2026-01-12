# =============================================================================
# NexoImportAgent - Strands A2AServer Entry Point (ORCHESTRATOR)
# =============================================================================
# Main entry point for the NexoImport ORCHESTRATOR agent.
# Uses AWS Strands Agents Framework with A2A protocol (port 9000).
#
# Architecture:
# - This is the MAIN ORCHESTRATOR that receives all inventory input
# - Routes to SPECIALIST agents via A2A protocol
# - Follows ReAct pattern: OBSERVE → THINK → LEARN → ACT + HIL
#
# Reference:
# - https://strandsagents.com/latest/
# - https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
# =============================================================================

import os
import sys
import logging
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

# Centralized model configuration (MANDATORY - Gemini 3.0 Pro + Thinking)
from agents.utils import get_model, requires_thinking, AGENT_VERSION, create_gemini_model

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

AGENT_ID = "nexo_import"
AGENT_NAME = "NexoImportOrchestrator"
AGENT_DESCRIPTION = """NEXO Import Orchestrator - Main entry point for intelligent file import.

This is the MAIN ORCHESTRATOR that:
1. OBSERVES: Analyzes incoming files (CSV, XLSX, XML, PDF)
2. THINKS: Routes to appropriate SPECIALIST agent via A2A
3. LEARNS: Stores patterns via LearningAgent
4. ACTS: Executes validated imports

Specialists available via A2A:
- /intake/ - NF (Nota Fiscal) XML/PDF parsing
- /import/ - CSV/XLSX spreadsheet processing
- /estoque-control/ - Movement creation
- /learning/ - Pattern storage and retrieval
- /observation/ - Audit logging
"""

# Model configuration
MODEL_ID = get_model(AGENT_ID)  # gemini-3.0-pro (with Thinking)

# =============================================================================
# System Prompt (ReAct Pattern)
# =============================================================================

SYSTEM_PROMPT = """Você é **NEXO**, o assistente inteligente de importação do sistema SGA (Sistema de Gestão de Ativos).

## 🎯 Seu Papel

Você é o **ORQUESTRADOR** do fluxo de importação inteligente.
Coordena com agentes especialistas usando o padrão ReAct:

1. **OBSERVE** 👁️: Analise a estrutura do arquivo recebido
2. **THINK** 🧠: Raciocine sobre qual especialista deve processar
3. **LEARN** 📚: Consulte/armazene padrões via LearningAgent (A2A)
4. **ACT** ⚡: Execute com decisões validadas

## 🔗 Delegação A2A (IMPORTANTE)

Você ORQUESTRA outros agentes via A2A protocol:

- **IntakeAgent** (/intake/): Processar NF XML/PDF
- **ImportAgent** (/import/): Processar CSV/XLSX
- **EstoqueControlAgent** (/estoque-control/): Criar movimentos
- **LearningAgent** (/learning/): Conhecimento prévio, aprendizado
- **ObservationAgent** (/observation/): Audit trail

## ⚠️ Regras Críticas

1. Confiança < 80% → gere pergunta HIL (Human-in-the-Loop)
2. Confiança >= 90% → aplique automaticamente
3. SEMPRE emita eventos de audit via ObservationAgent
4. NUNCA acesse banco de dados diretamente - delegue aos especialistas

## 🌍 Linguagem

Português brasileiro (pt-BR) para interações com usuário.
"""


# =============================================================================
# Tools (Strands @tool decorator)
# =============================================================================

# A2A client instance for inter-agent communication
a2a_client = A2AClient()


@tool
async def analyze_file(
    s3_key: str,
    filename: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze file structure from S3.

    OBSERVE phase: Detect file type, extract structure, identify columns.

    Args:
        s3_key: S3 key where file is stored
        filename: Original filename for type detection
        session_id: Session ID for context

    Returns:
        File analysis with columns, types, and routing recommendation
    """
    logger.info(f"[{AGENT_NAME}] OBSERVE: Analyzing file {filename or s3_key}")

    try:
        # Import tool implementation
        from agents.nexo_import.tools.analyze_file import analyze_file_impl

        result = await analyze_file_impl(
            s3_key=s3_key,
            filename=filename,
            session_id=session_id,
        )

        # Log to ObservationAgent via A2A
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "FILE_ANALYZED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {"s3_key": s3_key, "filename": filename},
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] analyze_file failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def reason_mappings(
    file_analysis: Dict[str, Any],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reason about column mappings using schema context and prior knowledge.

    THINK phase: Use Gemini 3.0 Pro to reason about mappings.

    Args:
        file_analysis: Result from analyze_file
        session_id: Session ID for context

    Returns:
        Mapping recommendations with confidence scores
    """
    logger.info(f"[{AGENT_NAME}] THINK: Reasoning about mappings")

    try:
        # Query LearningAgent for prior knowledge via A2A
        prior_response = await a2a_client.invoke_agent("learning", {
            "action": "retrieve_prior_knowledge",
            "file_analysis": file_analysis,
        }, session_id)

        prior_knowledge = {}
        if prior_response.success:
            import json
            try:
                prior_knowledge = json.loads(prior_response.response)
            except json.JSONDecodeError:
                pass

        # Import tool implementation
        from agents.nexo_import.tools.reason_mappings import reason_mappings_impl

        result = await reason_mappings_impl(
            file_analysis=file_analysis,
            prior_knowledge=prior_knowledge,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] reason_mappings failed: {e}", exc_info=True)
        return {"success": False, "error": str(e), "mappings": {}}


@tool
async def generate_questions(
    mappings: Dict[str, Any],
    confidence_threshold: float = 0.8,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate HIL (Human-in-the-Loop) questions for low-confidence mappings.

    HIL phase: Request human approval when uncertain.

    Args:
        mappings: Mapping recommendations from reason_mappings
        confidence_threshold: Threshold below which to ask questions (default 0.8)
        session_id: Session ID for context

    Returns:
        List of questions for user approval
    """
    logger.info(f"[{AGENT_NAME}] HIL: Generating questions for confidence < {confidence_threshold}")

    try:
        from agents.nexo_import.tools.generate_questions import generate_questions_impl

        result = await generate_questions_impl(
            mappings=mappings,
            confidence_threshold=confidence_threshold,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] generate_questions failed: {e}", exc_info=True)
        return {"success": False, "error": str(e), "questions": []}


@tool
async def execute_import(
    s3_key: str,
    column_mappings: Dict[str, str],
    target_table: str = "pending_entry_items",
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute import with validated column mappings.

    ACT phase: Delegate to EstoqueControlAgent for movement creation.

    Args:
        s3_key: S3 key of file to import
        column_mappings: Validated column mappings
        target_table: Target table for import
        session_id: Session ID for context
        user_id: User ID for audit

    Returns:
        Import result with row counts
    """
    logger.info(f"[{AGENT_NAME}] ACT: Executing import to {target_table}")

    try:
        # Delegate to ImportAgent for actual import execution
        import_response = await a2a_client.invoke_agent("import", {
            "action": "execute_import",
            "s3_key": s3_key,
            "column_mappings": column_mappings,
            "target_table": target_table,
            "user_id": user_id,
        }, session_id)

        if not import_response.success:
            return {"success": False, "error": import_response.error}

        import json
        result = json.loads(import_response.response)

        # LEARN: Store successful pattern via LearningAgent
        if result.get("success") and result.get("rows_imported", 0) > 0:
            await a2a_client.invoke_agent("learning", {
                "action": "store_pattern",
                "pattern_type": "column_mapping",
                "column_mappings": column_mappings,
                "target_table": target_table,
                "success": True,
            }, session_id)

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "IMPORT_COMPLETED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "s3_key": s3_key,
                "rows_imported": result.get("rows_imported", 0),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] execute_import failed: {e}", exc_info=True)
        return {"success": False, "error": str(e), "rows_imported": 0}


@tool
async def route_to_specialist(
    file_type: str,
    payload: Dict[str, Any],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Route request to appropriate specialist agent via A2A.

    ORCHESTRATION: Central routing logic for multi-agent coordination.

    Args:
        file_type: Detected file type (NF_XML, NF_PDF, CSV, XLSX, etc.)
        payload: Payload to send to specialist
        session_id: Session ID for context

    Returns:
        Response from specialist agent
    """
    logger.info(f"[{AGENT_NAME}] Routing {file_type} to specialist")

    # Determine specialist based on file type
    specialist_map = {
        "NF_XML": "intake",
        "NF_PDF": "intake",
        "CSV": "import",
        "XLSX": "import",
        "XLS": "import",
        "TEXT": "import",
    }

    specialist = specialist_map.get(file_type.upper(), "import")

    try:
        response = await a2a_client.invoke_agent(specialist, payload, session_id)

        if response.success:
            import json
            try:
                return json.loads(response.response)
            except json.JSONDecodeError:
                return {"success": True, "response": response.response}
        else:
            return {"success": False, "error": response.error}

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] route_to_specialist failed: {e}", exc_info=True)
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
            analyze_file,
            reason_mappings,
            generate_questions,
            execute_import,
            route_to_specialist,
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

    # Create agent
    agent = create_agent()

    # Create A2A server
    a2a_server = A2AServer(
        agent=agent,
        host="0.0.0.0",
        port=9000,
        serve_at_root=True,  # Serve at / for AgentCore compatibility
    )

    # Start server
    a2a_server.serve()


if __name__ == "__main__":
    main()
