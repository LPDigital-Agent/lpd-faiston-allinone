# =============================================================================
# EquipmentResearchAgent - Strands A2AServer Entry Point (SUPPORT)
# =============================================================================
# Equipment knowledge base support agent.
# Uses AWS Strands Agents Framework with A2A protocol (port 9000).
#
# Architecture:
# - This is a SUPPORT agent for equipment research
# - Handles equipment documentation discovery and knowledge retrieval
# - Integrates with knowledge base for equipment specifications
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

# Centralized model configuration (MANDATORY - Gemini 3.0 Pro for complex reasoning)
from agents.utils import get_model, AGENT_VERSION, create_gemini_model

# A2A client for inter-agent communication
from shared.a2a_client import A2AClient

# Hooks for observability (ADR-002)
from shared.hooks import LoggingHook, MetricsHook, DebugHook

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "equipment_research"
AGENT_NAME = "EquipmentResearchAgent"
AGENT_DESCRIPTION = """SUPPORT Agent for Equipment Research.

This agent handles:
1. RESEARCH: Research equipment specifications and documentation
2. QUERIES: Generate search queries for equipment lookup

Features:
- Equipment specification lookup
- Documentation discovery
- Knowledge base integration
- Manufacturer documentation
"""

# Model configuration
MODEL_ID = get_model(AGENT_ID)  # gemini-3.0-pro (complex reasoning)

# Agent skills for Agent Card discovery
AGENT_SKILLS = [
    AgentSkill(
        name="research_equipment",
        description="Research equipment specifications and documentation from knowledge base and external sources",
        parameters={
            "query": {"type": "string", "description": "Search query or description", "required": True},
            "equipment_type": {"type": "string", "description": "Optional equipment type filter (e.g., notebook, monitor)", "required": False},
            "manufacturer": {"type": "string", "description": "Optional manufacturer filter", "required": False},
            "model": {"type": "string", "description": "Optional model filter", "required": False},
            "part_number": {"type": "string", "description": "Optional part number filter", "required": False},
            "include_docs": {"type": "boolean", "description": "Whether to include documentation links (default: true)", "required": False},
            "session_id": {"type": "string", "description": "Session ID for context tracking", "required": False},
        },
        returns={"type": "object", "description": "Equipment research results with specifications, documentation, and confidence scores"},
    ),
    AgentSkill(
        name="generate_queries",
        description="Generate optimized search queries for equipment lookup based on description and context",
        parameters={
            "description": {"type": "string", "description": "Equipment description or context", "required": True},
            "context": {"type": "object", "description": "Optional additional context (e.g., category, usage)", "required": False},
            "max_queries": {"type": "integer", "description": "Maximum number of queries to generate (default: 5)", "required": False},
            "session_id": {"type": "string", "description": "Session ID for context tracking", "required": False},
        },
        returns={"type": "object", "description": "List of optimized search queries with relevance scores"},
    ),
    AgentSkill(
        name="health_check",
        description="Health check endpoint for monitoring agent status and capabilities",
        parameters={},
        returns={"type": "object", "description": "Health status with agent info, version, model, and capabilities"},
    ),
]

# =============================================================================
# System Prompt (Equipment Research Specialist)
# =============================================================================

SYSTEM_PROMPT = """Voce e o **EquipmentResearchAgent** do sistema SGA (Sistema de Gestao de Ativos).

## Seu Papel

Voce e o **ESPECIALISTA** em pesquisa de equipamentos e documentacao tecnica.

## Suas Ferramentas

### 1. `research_equipment`
Pesquisa especificacoes de equipamento:
- Modelo e fabricante
- Especificacoes tecnicas
- Manuais e documentacao
- Pecas compativeis

### 2. `generate_queries`
Gera queries de busca otimizadas:
- Termos tecnicos
- Codigos de fabricante
- Palavras-chave relevantes

## Fontes de Conhecimento

| Fonte | Tipo | Prioridade |
|-------|------|------------|
| Knowledge Base | Interno | Alta |
| Fabricantes | Externo | Media |
| Datasheets | Externo | Media |
| Historico SGA | Interno | Alta |

## Tipos de Equipamento

- Notebooks/Laptops
- Desktops
- Monitores
- Perifericos
- Servidores
- Equipamentos de rede
- Impressoras
- Telefonia

## Informacoes Buscadas

1. **Identificacao**: Modelo, fabricante, part number
2. **Especificacoes**: Memoria, armazenamento, processador
3. **Compatibilidade**: Pecas, acessorios, upgrades
4. **Suporte**: Garantia, drivers, manuais

## Regras Criticas

1. **SEMPRE** cite a fonte da informacao
2. Priorize fontes internas (KB) sobre externas
3. Inclua nivel de confianca nas respostas
4. Alerte sobre informacoes desatualizadas
"""


# =============================================================================
# Tools (Strands @tool decorator)
# =============================================================================

# A2A client instance for inter-agent communication
a2a_client = A2AClient()


@tool
async def research_equipment(
    query: str,
    equipment_type: Optional[str] = None,
    manufacturer: Optional[str] = None,
    model: Optional[str] = None,
    part_number: Optional[str] = None,
    include_docs: bool = True,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Research equipment specifications and documentation.

    Args:
        query: Search query or description
        equipment_type: Optional equipment type filter
        manufacturer: Optional manufacturer filter
        model: Optional model filter
        part_number: Optional part number filter
        include_docs: Whether to include documentation links
        session_id: Session ID for context

    Returns:
        Equipment research results with specifications and documentation
    """
    logger.info(f"[{AGENT_NAME}] Researching equipment: {query}")

    try:
        # Import tool implementation
        from agents.equipment_research.tools.research_equipment import research_equipment_tool

        result = await research_equipment_tool(
            query=query,
            equipment_type=equipment_type,
            manufacturer=manufacturer,
            model=model,
            part_number=part_number,
            include_docs=include_docs,
            session_id=session_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "EQUIPMENT_RESEARCHED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "query": query,
                "results_count": result.get("results_count", 0),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] research_equipment failed: {e}", exc_info=True)
        # Sandwich Pattern: Feed error context to LLM for decision
        return {
            "success": False,
            "error": str(e),
            "error_context": {
                "error_type": type(e).__name__,
                "operation": "research_equipment",
                "query": query,
                "equipment_type": equipment_type,
                "manufacturer": manufacturer,
                "model": model,
                "part_number": part_number,
                "session_id": session_id,
                "recoverable": isinstance(e, (TimeoutError, ConnectionError, OSError)),
            },
            "suggested_actions": ["retry_with_simpler_query", "check_knowledge_base_status", "escalate"],
            "results": [],
        }


@tool
async def generate_queries(
    description: str,
    context: Optional[Dict[str, Any]] = None,
    max_queries: int = 5,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate optimized search queries for equipment lookup.

    Args:
        description: Equipment description or context
        context: Optional additional context
        max_queries: Maximum number of queries to generate
        session_id: Session ID for context

    Returns:
        List of optimized search queries
    """
    logger.info(f"[{AGENT_NAME}] Generating queries for: {description}")

    try:
        # Import tool implementation
        from agents.equipment_research.tools.generate_queries import generate_queries_tool

        result = await generate_queries_tool(
            description=description,
            context=context,
            max_queries=max_queries,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] generate_queries failed: {e}", exc_info=True)
        # Sandwich Pattern: Feed error context to LLM for decision
        return {
            "success": False,
            "error": str(e),
            "error_context": {
                "error_type": type(e).__name__,
                "operation": "generate_queries",
                "description": description,
                "context": context,
                "max_queries": max_queries,
                "session_id": session_id,
                "recoverable": isinstance(e, (TimeoutError, ConnectionError, OSError)),
            },
            "suggested_actions": ["retry", "use_fallback_keywords", "escalate"],
            "queries": [],
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
        "specialty": "EQUIPMENT_RESEARCH",
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
            research_equipment,
            generate_queries,
            health_check,
        ],
        system_prompt=SYSTEM_PROMPT,
        hooks=[LoggingHook(), MetricsHook(), DebugHook(timeout_seconds=5.0)],  # ADR-002/003
    )


# =============================================================================
# A2A Server Entry Point
# =============================================================================

def main():
    """
    Start the Strands A2AServer with FastAPI wrapper.

    Port 9000 is the standard for A2A protocol.
    Includes /ping health check endpoint.
    """
    logger.info(f"[{AGENT_NAME}] Starting Strands A2AServer on port 9000...")
    logger.info(f"[{AGENT_NAME}] Model: {MODEL_ID}")
    logger.info(f"[{AGENT_NAME}] Version: {AGENT_VERSION}")
    logger.info(f"[{AGENT_NAME}] Role: SUPPORT (Equipment Research)")
    logger.info(f"[{AGENT_NAME}] Skills: {len(AGENT_SKILLS)} registered")
    for skill in AGENT_SKILLS:
        logger.info(f"  - {skill.name}: {skill.description}")

    # Create FastAPI app
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
        serve_at_root=False,  # Mount under / via FastAPI
        version=AGENT_VERSION,
        skills=AGENT_SKILLS,
    )

    # Mount A2A server to FastAPI app
    app.mount("/", a2a_server.to_fastapi_app())

    # Start server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
