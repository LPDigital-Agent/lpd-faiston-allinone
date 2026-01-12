# =============================================================================
# IntakeAgent - Strands A2AServer Entry Point (SPECIALIST)
# =============================================================================
# NF (Nota Fiscal) parsing specialist agent.
# Uses AWS Strands Agents Framework with A2A protocol (port 9000).
#
# Architecture:
# - This is a SPECIALIST agent for NF processing
# - Receives requests from ORCHESTRATOR (NexoImportAgent) via A2A
# - Handles XML, PDF, and Image (DANFE) parsing
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

AGENT_ID = "intake"
AGENT_NAME = "IntakeAgent"
AGENT_DESCRIPTION = """SPECIALIST Agent for Nota Fiscal (NF) Processing.

This agent processes incoming materials via NF-e (Nota Fiscal Eletrônica):
1. PARSE: Extract data from XML, PDF, or scanned images (DANFE)
2. MATCH: Identify part numbers for NF items
3. PROCESS: Create pending entries with confidence scoring
4. CONFIRM: Validate and create inventory movements

Features:
- Gemini Vision AI for scanned documents (DANFE)
- Automatic part number matching
- Serial number detection (SN:, IMEI:, MAC:)
- HIL routing for low-confidence items (<80%)
- Brazilian NF-e compliance (SEFAZ format)
"""

# Model configuration
MODEL_ID = get_model(AGENT_ID)  # gemini-3.0-pro (with Thinking)

# =============================================================================
# System Prompt (ReAct Pattern - NF Specialist)
# =============================================================================

SYSTEM_PROMPT = """Você é o **IntakeAgent** do sistema Faiston SGA (Sistema de Gestão de Ativos).

## 🎯 Seu Papel

Você é o **ESPECIALISTA** em processamento de NF-e (Nota Fiscal Eletrônica).
Segue o padrão ReAct para processar documentos fiscais:

1. **OBSERVE** 👁️: Analise o documento recebido (XML, PDF, imagem)
2. **THINK** 🧠: Extraia e valide dados fiscais
3. **MATCH** 🔗: Identifique part numbers correspondentes
4. **ACT** ⚡: Crie entradas ou route para HIL

## 🔧 Suas Ferramentas

### 1. `parse_nf`
Parseia NF de diferentes formatos:
- **XML**: Parsing estruturado direto (NFe SEFAZ)
- **PDF**: Extração de texto + AI
- **Imagem**: Gemini Vision OCR (DANFE escaneado)

### 2. `match_items`
Identifica part numbers para itens da NF:
- Match por código do fornecedor (cProd)
- Match por descrição (xProd) com AI
- Match por NCM como fallback

### 3. `process_entry`
Cria entrada pendente no sistema:
- Calcula score de confiança
- Roteia para HIL se necessário
- Cria tarefa de projeto se ausente

### 4. `confirm_entry`
Confirma entrada e cria movimentações:
- Aplica mapeamentos manuais
- Cria movimentos de estoque via A2A (EstoqueControlAgent)
- Atualiza saldos

## 📊 Regras de Confiança

| Score | Ação |
|-------|------|
| > 90% | Entrada automática |
| 80-90% | Entrada com alerta |
| < 80% | HIL obrigatório |
| Alto valor (> R$ 5000) | HIL obrigatório |

## 🔍 Padrões de Número de Série

Detectar seriais em descrição:
- `SN:`, `SERIAL:`, `S/N:`
- `IMEI:`, `MAC:`
- Quantidade de seriais = quantidade do item

## ⚠️ Regras Críticas

1. **NUNCA** confirme entrada sem projeto atribuído
2. **SEMPRE** valide chave de acesso (44 dígitos)
3. Seriais duplicados são **ERRO CRÍTICO**
4. Itens sem match -> criar tarefa HIL
5. Para movimentações -> delegar ao EstoqueControlAgent via A2A

## 🌍 Linguagem

Português brasileiro (pt-BR) para interações com usuário.
"""


# =============================================================================
# Tools (Strands @tool decorator)
# =============================================================================

# A2A client instance for inter-agent communication
a2a_client = A2AClient()


@tool
async def parse_nf(
    s3_key: str,
    file_type: str = "xml",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse NF (Nota Fiscal) from various formats.

    OBSERVE phase: Extract structured data from fiscal documents.

    Supports:
    - XML: Direct structured parsing (NFe SEFAZ format)
    - PDF: Text extraction + AI reasoning
    - Image: Gemini Vision OCR (for scanned DANFE)

    Args:
        s3_key: S3 key where file is stored
        file_type: File type (xml, pdf, image)
        session_id: Session ID for audit

    Returns:
        Extraction result with NF data
    """
    logger.info(f"[{AGENT_NAME}] OBSERVE: Parsing NF ({file_type}) from {s3_key}")

    try:
        # Import tool implementation
        from agents.intake.tools.parse_nf import parse_nf_tool

        result = await parse_nf_tool(
            s3_key=s3_key,
            file_type=file_type,
            session_id=session_id,
        )

        # Log to ObservationAgent via A2A
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "NF_PARSED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "s3_key": s3_key,
                "file_type": file_type,
                "items_count": result.get("items_count", 0),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] parse_nf failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def match_items(
    extraction: Dict[str, Any],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Match NF items to existing part numbers.

    THINK phase: Identify part numbers using multiple strategies.

    Matching strategies (in order):
    1. cProd (supplier code) exact match
    2. Description (xProd) similarity with AI
    3. NCM code as fallback grouping

    Args:
        extraction: Parsed NF data from parse_nf
        session_id: Session ID for context

    Returns:
        Match results with confidence scores per item
    """
    logger.info(f"[{AGENT_NAME}] THINK: Matching items to part numbers")

    try:
        # Import tool implementation
        from agents.intake.tools.match_items import match_items_tool

        result = await match_items_tool(
            extraction=extraction,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] match_items failed: {e}", exc_info=True)
        return {"success": False, "error": str(e), "matches": []}


@tool
async def process_entry(
    extraction: Dict[str, Any],
    matches: Dict[str, Any],
    project_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create pending entry from NF extraction.

    ACT phase: Create entry with confidence-based routing.

    Confidence rules:
    - > 90%: Automatic entry
    - 80-90%: Entry with warning
    - < 80%: Route to HIL for approval
    - High value (> R$ 5000): Always route to HIL

    Args:
        extraction: Parsed NF data
        matches: Item matching results
        project_id: Optional project to assign
        session_id: Session ID for context
        user_id: User ID for audit

    Returns:
        Entry creation result with routing decision
    """
    logger.info(f"[{AGENT_NAME}] ACT: Processing entry")

    try:
        # Import tool implementation
        from agents.intake.tools.process_entry import process_entry_tool

        result = await process_entry_tool(
            extraction=extraction,
            matches=matches,
            project_id=project_id,
            session_id=session_id,
            user_id=user_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "ENTRY_CREATED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "entry_id": result.get("entry_id"),
                "status": result.get("status"),
                "confidence": result.get("confidence"),
            },
        }, session_id)

        # If low confidence, also notify LearningAgent
        if result.get("confidence", 1.0) < 0.8:
            await a2a_client.invoke_agent("learning", {
                "action": "record_low_confidence_event",
                "event_type": "NF_ENTRY",
                "confidence": result.get("confidence"),
                "extraction": extraction,
            }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] process_entry failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def confirm_entry(
    entry_id: str,
    manual_mappings: Optional[Dict[str, str]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Confirm entry and create inventory movements.

    EXECUTE phase: Finalize entry after HIL approval (if needed).

    Args:
        entry_id: Entry ID to confirm
        manual_mappings: Optional manual part number mappings from HIL
        session_id: Session ID for context
        user_id: User ID for audit

    Returns:
        Confirmation result with created movements
    """
    logger.info(f"[{AGENT_NAME}] EXECUTE: Confirming entry {entry_id}")

    try:
        # Import tool implementation
        from agents.intake.tools.confirm_entry import confirm_entry_tool

        result = await confirm_entry_tool(
            entry_id=entry_id,
            manual_mappings=manual_mappings,
            session_id=session_id,
            user_id=user_id,
        )

        # If successful, delegate movement creation to EstoqueControlAgent
        if result.get("success") and result.get("items"):
            movement_response = await a2a_client.invoke_agent("estoque_control", {
                "action": "create_entry_movement",
                "entry_id": entry_id,
                "items": result.get("items"),
                "user_id": user_id,
            }, session_id)

            if movement_response.success:
                import json
                try:
                    movement_data = json.loads(movement_response.response)
                    result["movements"] = movement_data.get("movements", [])
                except json.JSONDecodeError:
                    pass

        # Store successful pattern in LearningAgent
        if result.get("success"):
            await a2a_client.invoke_agent("learning", {
                "action": "store_pattern",
                "pattern_type": "nf_confirmation",
                "entry_id": entry_id,
                "manual_mappings": manual_mappings,
                "success": True,
            }, session_id)

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "ENTRY_CONFIRMED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "entry_id": entry_id,
                "movements_count": len(result.get("movements", [])),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] confirm_entry failed: {e}", exc_info=True)
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
        "role": "SPECIALIST",
        "specialty": "NF_PARSING",
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
            parse_nf,
            match_items,
            process_entry,
            confirm_entry,
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
    logger.info(f"[{AGENT_NAME}] Role: SPECIALIST (NF Parsing)")

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
