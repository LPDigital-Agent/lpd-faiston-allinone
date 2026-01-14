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
from a2a.types import AgentSkill
from fastapi import FastAPI
import uvicorn

# Centralized model configuration (MANDATORY - Gemini 3.0 Pro + Thinking)
from agents.utils import get_model, requires_thinking, AGENT_VERSION, create_gemini_model

# A2A client for inter-agent communication
from shared.a2a_client import A2AClient

# NEXO Mind - Direct Memory Access (Hippocampus)
from shared.memory_manager import AgentMemoryManager

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
# Agent Skills (A2A Agent Card Discovery)
# =============================================================================

AGENT_SKILLS = [
    AgentSkill(
        id="parse_nf",
        name="Parse Nota Fiscal",
        description="Parse NF (Nota Fiscal) from various formats (XML, PDF, Image). Supports NFe SEFAZ XML, PDF text extraction with AI, and Gemini Vision OCR for scanned DANFE documents.",
        tags=["intake", "nf", "parsing", "xml", "pdf", "ocr", "danfe", "vision"],
    ),
    AgentSkill(
        id="match_items",
        name="Match NF Items to Part Numbers",
        description="Match NF items to existing part numbers using multiple strategies: supplier code (cProd) exact match, description similarity with AI, and NCM code fallback grouping. Returns confidence scores per item.",
        tags=["intake", "nf", "matching", "part-number", "ai", "confidence"],
    ),
    AgentSkill(
        id="process_entry",
        name="Process NF Entry",
        description="Create pending entry from NF extraction with confidence-based routing. Automatically routes to HIL for items with confidence < 80% or high value (> R$ 5000). Detects serial numbers (SN, IMEI, MAC) in descriptions.",
        tags=["intake", "nf", "entry", "confidence", "hil", "routing", "serial-detection"],
    ),
    AgentSkill(
        id="confirm_entry",
        name="Confirm NF Entry",
        description="Confirm entry and create inventory movements after HIL approval. Applies manual part number mappings, delegates movement creation to EstoqueControlAgent via A2A, and stores successful patterns in LearningAgent.",
        tags=["intake", "nf", "confirmation", "movement", "hil", "a2a", "learning"],
    ),
    AgentSkill(
        id="health_check",
        name="Health Check",
        description="Health check endpoint for monitoring. Returns agent status, version, model, protocol, and specialty information.",
        tags=["intake", "monitoring", "health", "status"],
    ),
    AgentSkill(
        id="get_upload_url",
        name="Get Upload URL",
        description="Generate presigned S3 URL for document upload. Used before uploading NF documents (XML, PDF, images) for processing. Returns upload_url, s3_key, and expiration time.",
        tags=["intake", "upload", "s3", "presigned-url", "nf"],
    ),
]

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


def _get_memory(actor_id: str = "system") -> AgentMemoryManager:
    """
    Get AgentMemoryManager instance for direct memory access.

    NEXO Mind Architecture: Each agent has its own "hippocampal" connection
    to the shared brain (AgentCore Memory). No A2A gargalo!

    Args:
        actor_id: User/actor ID for namespace isolation

    Returns:
        AgentMemoryManager instance
    """
    return AgentMemoryManager(
        agent_id=AGENT_ID,
        actor_id=actor_id,
        use_global_namespace=True,  # Share patterns across users
    )


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

        # NEXO Mind: LEARN - Record low confidence events directly
        if result.get("confidence", 1.0) < 0.8:
            memory = _get_memory(actor_id=user_id or "system")
            await memory.learn_inference(
                inference=(
                    f"Low confidence NF entry (conf={result.get('confidence', 0):.0%}): "
                    f"NF {extraction.get('nf_number', 'unknown')} with {len(extraction.get('items', []))} items"
                ),
                category="nf_low_confidence",
                confidence=result.get("confidence", 0.5),
                emotional_weight=0.4,  # Lower weight - needs human validation
                session_id=session_id,
            )
            logger.info(f"[{AGENT_NAME}] Recorded low-confidence event in memory")

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

        # NEXO Mind: LEARN - Store successful patterns directly
        if result.get("success"):
            memory = _get_memory(actor_id=user_id or "system")

            # Store manual mappings as confirmed FACTS (HIL validation)
            if manual_mappings:
                for supplier_code, part_number in manual_mappings.items():
                    await memory.learn_fact(
                        fact=f"Supplier code '{supplier_code}' → Part Number '{part_number}'",
                        category="supplier_mapping",
                        emotional_weight=0.9,  # High weight - human confirmed
                        session_id=session_id,
                    )
                logger.info(f"[{AGENT_NAME}] LEARNED: {len(manual_mappings)} supplier mappings as FACTs")

            # Store the confirmation episode
            await memory.learn_episode(
                episode_content=(
                    f"NF entry {entry_id} confirmed successfully with "
                    f"{len(result.get('items', []))} items processed"
                ),
                category="nf_confirmed",
                outcome="success",
                emotional_weight=0.7,
                session_id=session_id,
            )

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


@tool
def get_upload_url(
    filename: str,
    content_type: str = "application/octet-stream",
) -> Dict[str, Any]:
    """
    Generate presigned S3 URL for document upload.

    This tool creates a presigned URL that allows direct upload to S3
    without exposing AWS credentials. Used before processing NF documents.

    Args:
        filename: Original filename for the document (e.g., "nota_fiscal.xml")
        content_type: MIME type of the file (default: application/octet-stream)
            Common types: application/xml, application/pdf, image/png, image/jpeg

    Returns:
        Dict containing:
            - success: True if URL generated
            - upload_url: Presigned URL for PUT request
            - s3_key: S3 key where file will be stored
            - expires_in: URL expiration time in seconds (3600)
        Or error dict if generation fails
    """
    logger.info(f"[{AGENT_NAME}] Generating upload URL for: {filename}")

    if not filename:
        return {"success": False, "error": "filename is required"}

    try:
        # Import S3 client for presigned URL generation
        from tools.s3_client import SGAS3Client

        s3 = SGAS3Client()

        # Generate temp path with unique key
        key = s3.get_temp_path(filename)

        # Generate presigned upload URL
        url_info = s3.generate_upload_url(
            key=key,
            content_type=content_type,
            expires_in=3600,  # 1 hour expiration
        )

        # Rename 'key' to 's3_key' for API consistency
        if url_info.get("success") and "key" in url_info:
            url_info["s3_key"] = url_info.pop("key")

        logger.info(f"[{AGENT_NAME}] Upload URL generated: {url_info.get('s3_key', 'unknown')}")

        return url_info

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] get_upload_url failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


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
            get_upload_url,  # BUG-013: Upload URL generation for NF documents
        ],
        system_prompt=SYSTEM_PROMPT,
    )


# =============================================================================
# A2A Server Entry Point
# =============================================================================

def main():
    """
    Start the Strands A2AServer with FastAPI.

    Port 9000 is the standard for A2A protocol.
    """
    logger.info(f"[{AGENT_NAME}] Starting Strands A2AServer on port 9000...")
    logger.info(f"[{AGENT_NAME}] Model: {MODEL_ID}")
    logger.info(f"[{AGENT_NAME}] Version: {AGENT_VERSION}")
    logger.info(f"[{AGENT_NAME}] Role: SPECIALIST (NF Parsing)")
    logger.info(f"[{AGENT_NAME}] Skills: {len(AGENT_SKILLS)} registered")
    for skill in AGENT_SKILLS:
        logger.info(f"  - {skill.name} ({skill.id})")

    # Create FastAPI app
    app = FastAPI(title=AGENT_NAME, description=AGENT_DESCRIPTION, version=AGENT_VERSION)

    # Add /ping endpoint
    @app.get("/ping")
    async def ping():
        """Health check endpoint for monitoring."""
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
        serve_at_root=False,  # Don't serve at root - we'll mount it
        version=AGENT_VERSION,
        skills=AGENT_SKILLS,
    )

    # Mount A2A server to FastAPI app
    app.mount("/", a2a_server.to_fastapi_app())

    # Start server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
