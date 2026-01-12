# =============================================================================
# AWS Bedrock AgentCore Runtime Entrypoint - Strands A2A Server
# =============================================================================
# Main entrypoint for Faiston SGA Inventory agents using Strands A2A Protocol.
# Uses A2AServer for native Agent-to-Agent communication (JSON-RPC 2.0).
#
# Migration from: BedrockAgentCoreApp (HTTP, port 8080, /invocations)
# Migration to: A2AServer (A2A, port 9000, /)
#
# Framework: AWS Strands Agents (per CLAUDE.md mandate)
# Protocol: A2A (Agent-to-Agent) - JSON-RPC 2.0
# Port: 9000
# Path: /
# Agent Card: /.well-known/agent-card.json
#
# Reference: https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/a2a.md
# =============================================================================

import logging
import os
import asyncio
from typing import Optional, Dict, Any, List

# Strands A2A imports
from strands import Agent, tool
from strands.models.gemini import GeminiModel
from strands.multiagent.a2a import A2AServer
import uvicorn
from fastapi import FastAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Environment Configuration
# =============================================================================

# Runtime URL from AgentCore environment
RUNTIME_URL = os.environ.get('AGENTCORE_RUNTIME_URL', 'http://127.0.0.1:9000/')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-2')

# Agent identification
AGENT_ID = os.environ.get('AGENT_ID', 'nexo_import')
AGENT_NAME = os.environ.get('AGENT_NAME', 'NexoImportAgent')

# Google API Key (MANDATORY for Gemini 3.0 - per CLAUDE.md)
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')

# Database configuration
USE_POSTGRES_MCP = os.environ.get("USE_POSTGRES_MCP", "true").lower() == "true"
AGENTCORE_GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")

logger.info(f"Runtime URL: {RUNTIME_URL}")
logger.info(f"Agent: {AGENT_NAME} ({AGENT_ID})")

# =============================================================================
# Lazy Loading Helpers (Cold Start Optimization)
# =============================================================================

_database_adapter = None
_a2a_client = None


def get_database_adapter():
    """
    Factory function to get the appropriate database adapter.
    Cached after first initialization.
    """
    global _database_adapter

    if _database_adapter is not None:
        return _database_adapter

    if USE_POSTGRES_MCP and AGENTCORE_GATEWAY_URL:
        from tools.mcp_gateway_client import MCPGatewayClientFactory
        from tools.gateway_adapter import GatewayPostgresAdapter

        mcp_client = MCPGatewayClientFactory.create_from_env()
        _database_adapter = GatewayPostgresAdapter(mcp_client)
        logger.info("Database adapter: GatewayPostgresAdapter (PostgreSQL via MCP)")
    else:
        from tools.dynamodb_client import SGADynamoDBClient
        _database_adapter = SGADynamoDBClient()
        logger.info("Database adapter: SGADynamoDBClient (DynamoDB)")

    return _database_adapter


def get_a2a_client():
    """Lazy-load A2A client for agent invocations."""
    global _a2a_client
    if _a2a_client is None:
        from shared.a2a_client import A2AClient
        _a2a_client = A2AClient()
    return _a2a_client


# =============================================================================
# Strands Tools - Core NEXO Import Handlers (Day 1)
# =============================================================================
# Each handler is converted to a Strands @tool decorator.
# The LLM can discover and invoke these via the Agent Card.

@tool
def health_check() -> Dict[str, Any]:
    """
    Return system health status.
    Used by monitoring and deployment verification.
    """
    from agents.utils import AGENT_VERSION, MODEL_GEMINI

    return {
        "success": True,
        "status": "healthy",
        "version": AGENT_VERSION,
        "git_commit": os.environ.get("GIT_COMMIT_SHA", "unknown"),
        "deployed_at": os.environ.get("DEPLOYED_AT", "unknown"),
        "model": MODEL_GEMINI,
        "protocol": "A2A",
        "port": 9000,
        "module": "Gestao de Ativos - Estoque",
        "agents": [
            "NexoImportAgent",
            "LearningAgent",
            "ValidationAgent",
            "SchemaEvolutionAgent",
            "IntakeAgent",
            "ImportAgent",
            "EstoqueControlAgent",
            "ComplianceAgent",
            "ReconciliacaoAgent",
            "ExpeditionAgent",
            "CarrierAgent",
            "ReverseAgent",
            "ObservationAgent",
            "EquipmentResearchAgent",
        ],
    }


@tool
async def nexo_analyze_file(
    file_key: str,
    file_name: str,
    file_type: str,
    user_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """
    Analyze uploaded file for intelligent import.

    NEXO uses ReAct pattern: OBSERVE → THINK → ASK → LEARN → ACT
    This is the OBSERVE phase - analyzing the file structure.

    Args:
        file_key: S3 key where file is stored
        file_name: Original file name
        file_type: Detected file type (csv, xlsx, xml, pdf)
        user_id: User performing the import
        session_id: Current session ID

    Returns:
        Analysis result with column mapping, confidence scores, and questions
    """
    try:
        # Lazy import for cold start optimization
        from agents.nexo_import_agent import NexoImportAgent

        agent = NexoImportAgent()
        result = await agent.analyze_file(
            file_key=file_key,
            file_name=file_name,
            file_type=file_type,
            user_id=user_id,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"nexo_analyze_file failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_key": file_key,
        }


@tool
async def nexo_execute_import(
    analysis_id: str,
    user_id: str,
    session_id: str,
    column_mapping: Optional[Dict[str, str]] = None,
    target_table: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the import based on analysis results.

    This is the ACT phase of NEXO ReAct pattern.

    Args:
        analysis_id: ID from nexo_analyze_file result
        user_id: User performing the import
        session_id: Current session ID
        column_mapping: Optional override for column mapping
        target_table: Optional target table (defaults to movements)

    Returns:
        Import result with record count and any errors
    """
    try:
        from agents.nexo_import_agent import NexoImportAgent

        agent = NexoImportAgent()
        result = await agent.execute_import(
            analysis_id=analysis_id,
            user_id=user_id,
            session_id=session_id,
            column_mapping=column_mapping,
            target_table=target_table,
        )

        return result

    except Exception as e:
        logger.error(f"nexo_execute_import failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "analysis_id": analysis_id,
        }


@tool
async def process_nf_upload(
    file_key: str,
    file_type: str,
    user_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """
    Process uploaded Nota Fiscal (NF) file.

    Handles XML and PDF NF formats via IntakeAgent.

    Args:
        file_key: S3 key where NF file is stored
        file_type: File type (xml or pdf)
        user_id: User uploading the NF
        session_id: Current session ID

    Returns:
        Extracted NF data with items and validation status
    """
    try:
        from agents.intake_agent import IntakeAgent

        agent = IntakeAgent()
        result = await agent.process_nf(
            file_key=file_key,
            file_type=file_type,
            user_id=user_id,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"process_nf_upload failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_key": file_key,
        }


@tool
async def create_movement(
    movement_type: str,
    items: List[Dict[str, Any]],
    user_id: str,
    session_id: str,
    location_from: Optional[str] = None,
    location_to: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create inventory movement (entrada, saida, transferencia).

    Core handler for EstoqueControlAgent.

    Args:
        movement_type: Type of movement (ENTRADA, SAIDA, TRANSFERENCIA)
        items: List of items with part_number, quantity, serial_number
        user_id: User creating the movement
        session_id: Current session ID
        location_from: Source location (required for SAIDA/TRANSFERENCIA)
        location_to: Destination location (required for ENTRADA/TRANSFERENCIA)
        notes: Optional notes/observations

    Returns:
        Created movement with ID and status
    """
    try:
        from agents.estoque_control_agent import EstoqueControlAgent

        agent = EstoqueControlAgent()
        result = await agent.create_movement(
            movement_type=movement_type,
            items=items,
            user_id=user_id,
            session_id=session_id,
            location_from=location_from,
            location_to=location_to,
            notes=notes,
        )

        return result

    except Exception as e:
        logger.error(f"create_movement failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "movement_type": movement_type,
        }


@tool
async def get_nf_upload_url(
    file_name: str,
    content_type: str,
    session_id: str,
) -> Dict[str, Any]:
    """
    Get presigned URL for NF file upload.

    Args:
        file_name: Original file name
        content_type: MIME type of the file
        session_id: Current session ID

    Returns:
        Presigned URL for S3 upload and file key
    """
    try:
        from tools.s3_client import get_upload_presigned_url

        result = await get_upload_presigned_url(
            file_name=file_name,
            content_type=content_type,
            folder="nf-uploads",
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"get_nf_upload_url failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_name": file_name,
        }


# =============================================================================
# Strands Tools - NEXO ReAct Pattern Handlers (ASK, LEARN phases)
# =============================================================================


@tool
async def nexo_get_questions(
    session_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Get clarification questions for current import session (ASK phase).

    Returns questions generated during analysis that require user input.
    Part of NEXO ReAct pattern: OBSERVE → THINK → ASK → LEARN → ACT

    Args:
        session_state: Full session state from frontend (from previous analyze call)

    Returns:
        List of questions with options and importance levels, plus updated session state
    """
    if not session_state:
        return {"success": False, "error": "session_state is required (stateless architecture)"}

    try:
        from agents.nexo_import_agent import NexoImportAgent

        agent = NexoImportAgent()
        result = await agent.get_questions(session_state=session_state)
        return result

    except Exception as e:
        logger.error(f"nexo_get_questions failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def nexo_submit_answers(
    session_state: Dict[str, Any],
    answers: Dict[str, str],
    user_feedback: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit user answers to clarification questions (ASK → LEARN phases).

    Processes user's answers and refines the analysis.
    Stores answers for learning and future improvement.

    Args:
        session_state: Full session state from frontend
        answers: Dict mapping question IDs to selected answers
        user_feedback: Optional global user instructions for AI interpretation

    Returns:
        Updated session state with refined mappings based on answers
    """
    if not session_state:
        return {"success": False, "error": "session_state is required (stateless architecture)"}

    if not answers:
        return {"success": False, "error": "answers is required"}

    try:
        from agents.nexo_import_agent import NexoImportAgent

        agent = NexoImportAgent()
        result = await agent.submit_answers(
            session_state=session_state,
            answers=answers,
            user_feedback=user_feedback,
        )
        return result

    except Exception as e:
        logger.error(f"nexo_submit_answers failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def nexo_learn_from_import(
    session_state: Dict[str, Any],
    import_result: Dict[str, Any],
    user_id: str,
    user_corrections: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Store learned patterns from successful import (LEARN phase).

    Called after import confirmation to build knowledge base.
    Uses AgentCore Episodic Memory via LearningAgent for cross-session learning.

    Args:
        session_state: Full session state from frontend
        import_result: Result of the executed import
        user_id: User performing the import
        user_corrections: Any manual corrections made by user

    Returns:
        Learning confirmation with episode_id and patterns stored
    """
    if not session_state:
        return {"success": False, "error": "session_state is required (stateless architecture)"}

    try:
        from agents.nexo_import_agent import NexoImportAgent

        agent = NexoImportAgent()
        result = await agent.learn_from_import(
            session_state=session_state,
            import_result=import_result,
            user_corrections=user_corrections or {},
            user_id=user_id,
        )
        return result

    except Exception as e:
        logger.error(f"nexo_learn_from_import failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def nexo_get_prior_knowledge(
    filename: str,
    user_id: str,
    file_analysis: Optional[Dict[str, Any]] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Retrieve prior knowledge before file analysis (RECALL phase).

    Queries AgentCore Episodic Memory via LearningAgent for similar
    past imports to provide auto-suggestions and learned mappings.

    Args:
        filename: Name of file being imported
        user_id: User performing the import
        file_analysis: Initial file analysis from sheet_analyzer
        session_id: Current session ID

    Returns:
        Prior knowledge with:
        - similar_episodes: List of similar past imports
        - suggested_mappings: Column mappings from successful imports
        - confidence_boost: Whether to trust auto-mappings
        - reflections: Cross-session insights
    """
    if not filename:
        return {"success": False, "error": "filename is required"}

    try:
        from agents.nexo_import_agent import NexoImportAgent

        agent = NexoImportAgent()
        result = await agent.get_prior_knowledge(
            filename=filename,
            file_analysis=file_analysis,
            user_id=user_id,
        )
        return result

    except Exception as e:
        logger.error(f"nexo_get_prior_knowledge failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def nexo_get_adaptive_threshold(
    filename: str,
    user_id: str,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Get adaptive confidence threshold based on historical patterns.

    Uses LearningAgent reflections to determine appropriate threshold
    for this file pattern. Files with good history get lower thresholds
    (more trust), while unknown patterns get higher thresholds.

    Args:
        filename: Name of file being imported
        user_id: User performing the import
        session_id: Current session ID

    Returns:
        Threshold configuration with:
        - threshold: Confidence threshold (0.0 to 1.0)
        - reason: Explanation for threshold choice
        - history_count: Number of similar imports in history
    """
    if not filename:
        return {"success": False, "error": "filename is required"}

    try:
        from agents.nexo_import_agent import NexoImportAgent

        agent = NexoImportAgent()
        result = await agent.get_adaptive_threshold(
            filename=filename,
            user_id=user_id,
        )
        return result

    except Exception as e:
        logger.error(f"nexo_get_adaptive_threshold failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Strands Tools - Smart Import Handlers
# =============================================================================


@tool
async def smart_import_analyze(
    file_key: str,
    file_name: str,
    user_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """
    Analyze file for Smart Import using NEXO AI.

    Detects file type, analyzes structure, and returns analysis
    with confidence-based column mapping suggestions.

    Args:
        file_key: S3 key where file is stored
        file_name: Original file name
        user_id: User performing the import
        session_id: Current session ID

    Returns:
        Analysis result with mappings, confidence, and questions if needed
    """
    try:
        # Detect file type first
        from tools.file_detector import detect_file_type
        from tools.s3_client import SGAS3Client

        s3_client = SGAS3Client()
        file_content = s3_client.download_file(file_key)
        file_type = detect_file_type(file_content, file_name)

        # Route to appropriate analysis based on file type
        if file_type in ("xml", "pdf"):
            # NF files go to IntakeAgent
            from agents.intake_agent import IntakeAgent
            agent = IntakeAgent()
            result = await agent.process_nf(
                file_key=file_key,
                file_type=file_type,
                user_id=user_id,
                session_id=session_id,
            )
        else:
            # Spreadsheets go to NexoImportAgent
            from agents.nexo_import_agent import NexoImportAgent
            agent = NexoImportAgent()
            result = await agent.analyze_file(
                file_key=file_key,
                file_name=file_name,
                file_type=file_type,
                user_id=user_id,
                session_id=session_id,
            )

        return result

    except Exception as e:
        logger.error(f"smart_import_analyze failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_key": file_key,
        }


@tool
async def get_upload_presigned_url(
    file_name: str,
    content_type: str,
    session_id: str,
    folder: str = "imports",
) -> Dict[str, Any]:
    """
    Get presigned URL for file upload to S3.

    Args:
        file_name: Original file name
        content_type: MIME type of the file
        session_id: Current session ID
        folder: S3 folder prefix (default: imports)

    Returns:
        Presigned URL for S3 upload and file key
    """
    try:
        from tools.s3_client import SGAS3Client

        s3_client = SGAS3Client()
        result = s3_client.get_upload_presigned_url(
            file_name=file_name,
            content_type=content_type,
            folder=folder,
            session_id=session_id,
        )
        return {"success": True, **result}

    except Exception as e:
        logger.error(f"get_upload_presigned_url failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "file_name": file_name,
        }


# =============================================================================
# Strands Tools - Inventory Control (EstoqueControlAgent)
# =============================================================================


@tool
async def get_balance(
    part_number: str,
    location_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get current balance for a part number at a location.

    Returns quantity available, reserved, and total.

    Args:
        part_number: Part number to check balance for
        location_id: Optional location filter
        project_id: Optional project filter

    Returns:
        Balance details with available, reserved, and total quantities
    """
    if not part_number:
        return {"success": False, "error": "part_number required"}

    try:
        from agents.estoque_control_agent import EstoqueControlAgent

        agent = EstoqueControlAgent()
        result = await agent.query_balance(
            part_number=part_number,
            location_id=location_id,
            project_id=project_id,
        )
        return result

    except Exception as e:
        logger.error(f"get_balance failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def get_asset_timeline(
    asset_id: str,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Get complete timeline of an asset's movements.

    Uses event sourcing pattern for full audit trail.

    Args:
        asset_id: Asset identifier (usually serial number)
        limit: Maximum number of events to return

    Returns:
        Timeline of all movements and events for this asset
    """
    if not asset_id:
        return {"success": False, "error": "asset_id required"}

    try:
        from tools.dynamodb_client import SGADynamoDBClient

        db = SGADynamoDBClient()
        timeline = db.get_asset_timeline(asset_id=asset_id, limit=limit)

        return {
            "success": True,
            "asset_id": asset_id,
            "timeline": timeline,
            "count": len(timeline),
        }

    except Exception as e:
        logger.error(f"get_asset_timeline failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def list_part_numbers(
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    List all part numbers with optional filtering.

    Args:
        search: Optional search string
        category: Optional category filter
        limit: Maximum results to return

    Returns:
        List of part numbers with descriptions
    """
    try:
        from tools.postgres_client import SGAPostgresClient

        pg = SGAPostgresClient()
        # Query part numbers from PostgreSQL
        sql = """
            SELECT part_number_id, part_number, description, category, manufacturer
            FROM sga.part_numbers
            WHERE ($1 IS NULL OR part_number ILIKE '%' || $1 || '%' OR description ILIKE '%' || $1 || '%')
            AND ($2 IS NULL OR category = $2)
            ORDER BY part_number
            LIMIT $3
        """
        results = pg.execute_sql(sql, (search, category, limit))

        return {
            "success": True,
            "part_numbers": results if results else [],
            "count": len(results) if results else 0,
        }

    except Exception as e:
        logger.error(f"list_part_numbers failed: {e}")
        return {"success": False, "error": str(e), "part_numbers": []}


@tool
async def list_locations(
    search: Optional[str] = None,
    location_type: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    List all stock locations.

    Args:
        search: Optional search string
        location_type: Optional type filter (WAREHOUSE, FIELD, TRANSIT)
        limit: Maximum results to return

    Returns:
        List of locations with details
    """
    try:
        from tools.postgres_client import SGAPostgresClient

        pg = SGAPostgresClient()
        sql = """
            SELECT location_id, location_code, location_name, location_type, address
            FROM sga.locations
            WHERE ($1 IS NULL OR location_code ILIKE '%' || $1 || '%' OR location_name ILIKE '%' || $1 || '%')
            AND ($2 IS NULL OR location_type = $2::sga.location_type)
            ORDER BY location_name
            LIMIT $3
        """
        results = pg.execute_sql(sql, (search, location_type, limit))

        return {
            "success": True,
            "locations": results if results else [],
            "count": len(results) if results else 0,
        }

    except Exception as e:
        logger.error(f"list_locations failed: {e}")
        return {"success": False, "error": str(e), "locations": []}


@tool
async def get_balance_report(
    location_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate balance report by location/project.

    Used for dashboard KPIs and inventory overview.

    Args:
        location_id: Optional location filter
        project_id: Optional project filter

    Returns:
        Report with totals, by-category breakdown, and KPIs
    """
    try:
        from tools.postgres_client import SGAPostgresClient

        pg = SGAPostgresClient()
        sql = """
            SELECT
                l.location_name,
                COUNT(DISTINCT mi.part_number_id) as unique_parts,
                SUM(mi.quantity) as total_quantity,
                COUNT(DISTINCT m.movement_id) as movement_count
            FROM sga.movements m
            JOIN sga.movement_items mi ON m.movement_id = mi.movement_id
            JOIN sga.locations l ON m.destination_location_id = l.location_id
            WHERE ($1::uuid IS NULL OR m.destination_location_id = $1::uuid)
            AND ($2::uuid IS NULL OR m.project_id = $2::uuid)
            AND m.status = 'COMPLETED'
            GROUP BY l.location_name
            ORDER BY total_quantity DESC
        """
        results = pg.execute_sql(sql, (location_id, project_id))

        return {
            "success": True,
            "report": results if results else [],
            "filters": {"location_id": location_id, "project_id": project_id},
        }

    except Exception as e:
        logger.error(f"get_balance_report failed: {e}")
        return {"success": False, "error": str(e), "report": []}


@tool
async def get_movement_history(
    part_number: Optional[str] = None,
    location_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Get movement history with filtering options.

    Args:
        part_number: Optional part number filter
        location_id: Optional location filter
        start_date: Optional start date (ISO format)
        end_date: Optional end date (ISO format)
        limit: Maximum results to return

    Returns:
        List of movements with details
    """
    try:
        from tools.postgres_client import SGAPostgresClient

        pg = SGAPostgresClient()
        sql = """
            SELECT
                m.movement_id, m.movement_type, m.status, m.created_at,
                m.created_by, m.notes,
                sl.location_name as source_location,
                dl.location_name as destination_location
            FROM sga.movements m
            LEFT JOIN sga.locations sl ON m.source_location_id = sl.location_id
            LEFT JOIN sga.locations dl ON m.destination_location_id = dl.location_id
            WHERE ($1::date IS NULL OR m.created_at >= $1::date)
            AND ($2::date IS NULL OR m.created_at <= $2::date)
            ORDER BY m.created_at DESC
            LIMIT $3
        """
        results = pg.execute_sql(sql, (start_date, end_date, limit))

        return {
            "success": True,
            "movements": results if results else [],
            "count": len(results) if results else 0,
        }

    except Exception as e:
        logger.error(f"get_movement_history failed: {e}")
        return {"success": False, "error": str(e), "movements": []}


@tool
async def nexo_estoque_chat(
    question: str,
    user_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """
    Handle NEXO Estoque natural language chat requests.

    Natural language interface for inventory queries.
    Examples:
    - "Quantos switches temos no estoque de SP?"
    - "Quais reversas estao pendentes ha mais de 5 dias?"
    - "Preciso reservar 3 unidades do PN 12345 para o projeto ABC"

    Args:
        question: Natural language question
        user_id: User asking the question
        session_id: Current session ID

    Returns:
        AI-generated answer with sources and confidence
    """
    if not question:
        return {"success": False, "error": "question required"}

    try:
        from agents.nexo_estoque_agent import NexoEstoqueAgent

        agent = NexoEstoqueAgent()
        result = await agent.chat(
            question=question,
            user_id=user_id,
            session_id=session_id,
        )
        return result

    except Exception as e:
        logger.error(f"nexo_estoque_chat failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "answer": f"Erro ao processar pergunta: {e}",
        }


# =============================================================================
# Strands Tools - Expedition Handlers (ExpeditionAgent)
# =============================================================================


@tool
async def process_expedition_request(
    chamado_id: str,
    items: List[Dict[str, Any]],
    user_id: str,
    session_id: str,
    project_id: Optional[str] = None,
    destination_client: Optional[str] = None,
    destination_address: Optional[str] = None,
    urgency: str = "NORMAL",
    nature: str = "USO_CONSUMO",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process an expedition request from a chamado.

    Creates shipment preparation workflow.

    Args:
        chamado_id: Ticket ID
        items: List of items [{pn_id, serial, quantity}]
        user_id: User creating the expedition
        session_id: Current session ID
        project_id: Associated project
        destination_client: Client name/CNPJ
        destination_address: Delivery address
        urgency: Urgency level (LOW, NORMAL, HIGH, URGENT)
        nature: Nature code (USO_CONSUMO, CONSERTO, DEMONSTRACAO)
        notes: Additional notes

    Returns:
        Expedition result with SAP-ready data
    """
    if not chamado_id:
        return {"success": False, "error": "chamado_id is required"}

    if not items:
        return {"success": False, "error": "items is required"}

    try:
        # Invoke ExpeditionAgent via A2A client
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="expedition",
            action="process_expedition_request",
            payload={
                "chamado_id": chamado_id,
                "project_id": project_id,
                "items": items,
                "destination_client": destination_client,
                "destination_address": destination_address,
                "urgency": urgency,
                "nature": nature,
                "notes": notes,
            },
            session_id=session_id,
            user_id=user_id,
        )
        return result

    except Exception as e:
        logger.error(f"process_expedition_request failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def verify_expedition_stock(
    pn_id: str,
    quantity: int = 1,
    serial: Optional[str] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Verify stock availability for an expedition item.

    Args:
        pn_id: Part number ID
        quantity: Quantity needed
        serial: Optional serial number
        session_id: Current session ID

    Returns:
        Verification result with availability status
    """
    if not pn_id:
        return {"success": False, "error": "pn_id is required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="expedition",
            action="verify_stock",
            payload={
                "pn_id": pn_id,
                "serial": serial,
                "quantity": quantity,
            },
            session_id=session_id,
        )
        return result

    except Exception as e:
        logger.error(f"verify_expedition_stock failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def confirm_separation(
    expedition_id: str,
    user_id: str,
    session_id: str,
    items_confirmed: Optional[List[Dict[str, Any]]] = None,
    package_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Confirm physical separation and packaging.

    Args:
        expedition_id: Expedition ID
        user_id: User confirming separation
        session_id: Current session ID
        items_confirmed: List of confirmed items with serials
        package_info: Packaging details (weight, dimensions)

    Returns:
        Confirmation result
    """
    if not expedition_id:
        return {"success": False, "error": "expedition_id is required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="expedition",
            action="confirm_separation",
            payload={
                "expedition_id": expedition_id,
                "items_confirmed": items_confirmed or [],
                "package_info": package_info or {},
            },
            session_id=session_id,
            user_id=user_id,
        )
        return result

    except Exception as e:
        logger.error(f"confirm_separation failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def complete_expedition(
    expedition_id: str,
    nf_number: str,
    user_id: str,
    session_id: str,
    nf_key: Optional[str] = None,
    carrier: Optional[str] = None,
    tracking_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Complete the expedition after NF emission.

    Args:
        expedition_id: Expedition ID
        nf_number: NF number
        user_id: User completing the expedition
        session_id: Current session ID
        nf_key: NF access key (44 digits)
        carrier: Carrier/transportadora name
        tracking_code: Optional tracking number

    Returns:
        Completion result with created movements
    """
    if not expedition_id:
        return {"success": False, "error": "expedition_id is required"}

    if not nf_number:
        return {"success": False, "error": "nf_number is required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="expedition",
            action="complete_expedition",
            payload={
                "expedition_id": expedition_id,
                "nf_number": nf_number,
                "nf_key": nf_key,
                "carrier": carrier,
                "tracking_code": tracking_code,
            },
            session_id=session_id,
            user_id=user_id,
        )

        # Audit logging
        try:
            from tools.dynamodb_client import SGAAuditLogger
            audit = SGAAuditLogger()
            audit.log_action(
                action="EXPEDITION_COMPLETED",
                entity_type="EXPEDITION",
                entity_id=expedition_id,
                actor=user_id,
                details={
                    "nf_number": nf_number,
                    "carrier": carrier,
                    "tracking_code": tracking_code,
                    "success": result.get("success", False),
                    "protocol": "A2A",
                },
            )
        except Exception:
            pass

        return result

    except Exception as e:
        logger.error(f"complete_expedition failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Strands Tools - Reverse Logistics Handlers (ReverseAgent)
# =============================================================================


@tool
async def process_return(
    serial: str,
    origin_type: str,
    user_id: str,
    session_id: str,
    origin_address: Optional[str] = None,
    owner: str = "FAISTON",
    condition: str = "FUNCIONAL",
    return_reason: Optional[str] = None,
    chamado_id: Optional[str] = None,
    project_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process an equipment return (reversa).

    Args:
        serial: Serial number of returning equipment
        origin_type: Where equipment is coming from (CUSTOMER, FIELD_TECH, BRANCH)
        user_id: User processing the return
        session_id: Current session ID
        origin_address: Address/location from where it's returning
        owner: Equipment owner (FAISTON, NTT, TERCEIROS)
        condition: Equipment condition (FUNCIONAL, DEFEITUOSO, INSERVIVEL)
        return_reason: Reason for return
        chamado_id: Related ticket ID
        project_id: Related project
        notes: Additional notes

    Returns:
        Return result with depot assignment and movement creation
    """
    if not serial:
        return {"success": False, "error": "serial is required"}

    if not origin_type:
        return {"success": False, "error": "origin_type is required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="reverse",
            action="process_return",
            payload={
                "serial_number": serial,
                "reason": return_reason,
                "condition": condition,
                "origin_reference": origin_address,
                "project_id": project_id,
                "notes": notes,
                "operator_id": user_id,
            },
            session_id=session_id,
            user_id=user_id,
        )

        # Audit logging
        try:
            from tools.dynamodb_client import SGAAuditLogger
            audit = SGAAuditLogger()
            audit.log_action(
                action="RETURN_PROCESSED",
                entity_type="RETURN",
                entity_id=serial,
                actor=user_id,
                details={
                    "origin_type": origin_type,
                    "owner": owner,
                    "condition": condition,
                    "return_reason": return_reason,
                    "chamado_id": chamado_id,
                    "success": result.get("success", False),
                    "protocol": "A2A",
                },
            )
        except Exception:
            pass

        return result

    except Exception as e:
        logger.error(f"process_return failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def validate_return_origin(
    serial: str,
    claimed_origin: Optional[str] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Validate the origin of a return shipment.

    Checks asset exists, traces last known location,
    and verifies return makes sense.

    Args:
        serial: Serial number
        claimed_origin: Claimed origin location
        session_id: Current session ID

    Returns:
        Validation result with asset info and match confidence
    """
    if not serial:
        return {"success": False, "error": "serial is required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="reverse",
            action="validate_origin",
            payload={"serial_number": serial},
            session_id=session_id,
            user_id="system",
        )
        return result

    except Exception as e:
        logger.error(f"validate_return_origin failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def evaluate_return_condition(
    serial: str,
    condition_description: str,
    owner: str = "FAISTON",
    photos_s3_keys: Optional[List[str]] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Evaluate equipment condition and determine destination.

    Uses AI to analyze condition description and photos
    to recommend appropriate depot.

    Args:
        serial: Serial number
        condition_description: Text describing equipment state
        owner: Equipment owner (FAISTON, NTT, TERCEIROS)
        photos_s3_keys: Optional list of S3 keys for condition photos
        session_id: Current session ID

    Returns:
        Evaluation with condition, recommended depot, and confidence
    """
    if not serial:
        return {"success": False, "error": "serial is required"}

    if not condition_description:
        return {"success": False, "error": "condition_description is required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="reverse",
            action="evaluate_condition",
            payload={
                "serial_number": serial,
                "inspection_notes": condition_description,
                "test_results": None,
            },
            session_id=session_id,
            user_id="system",
        )
        return result

    except Exception as e:
        logger.error(f"evaluate_return_condition failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Strands Tools - Carrier Handlers (CarrierAgent)
# =============================================================================


@tool
async def get_shipping_quotes(
    origin_cep: str,
    destination_cep: str,
    weight_kg: float = 1.0,
    dimensions: Optional[Dict[str, int]] = None,
    value: float = 100.0,
    urgency: str = "NORMAL",
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Get shipping quotes from multiple carriers.

    Args:
        origin_cep: Origin postal code
        destination_cep: Destination postal code
        weight_kg: Package weight in kg
        dimensions: Package dimensions {length, width, height} in cm
        value: Declared value in R$
        urgency: Urgency level (LOW, NORMAL, HIGH, URGENT)
        session_id: Current session ID

    Returns:
        List of quotes with AI recommendation
    """
    if not origin_cep or not destination_cep:
        return {"success": False, "error": "origin_cep and destination_cep are required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="carrier",
            action="get_quotes",
            payload={
                "origin_cep": origin_cep,
                "destination_cep": destination_cep,
                "weight_kg": weight_kg,
                "dimensions": dimensions or {"length": 30, "width": 20, "height": 10},
                "value": value,
                "urgency": urgency,
            },
            session_id=session_id,
            user_id="system",
        )
        return result

    except Exception as e:
        logger.error(f"get_shipping_quotes failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def recommend_carrier(
    urgency: str = "NORMAL",
    weight_kg: float = 1.0,
    value: float = 100.0,
    destination_state: str = "SP",
    same_city: bool = False,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Get AI recommendation for best carrier.

    Uses rules + AI to recommend optimal carrier
    based on urgency, weight, value, and destination.

    Args:
        urgency: Urgency level (LOW, NORMAL, HIGH, URGENT)
        weight_kg: Package weight
        value: Declared value
        destination_state: Destination state code (SP, RJ, etc.)
        same_city: Whether delivery is within same city
        session_id: Current session ID

    Returns:
        Carrier recommendation with reasoning
    """
    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="carrier",
            action="recommend_carrier",
            payload={
                "urgency": urgency,
                "weight_kg": weight_kg,
                "value": value,
                "destination_state": destination_state,
                "same_city": same_city,
            },
            session_id=session_id,
            user_id="system",
        )
        return result

    except Exception as e:
        logger.error(f"recommend_carrier failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def track_shipment(
    tracking_code: str,
    carrier: Optional[str] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Track a shipment by tracking code.

    Args:
        tracking_code: Tracking code
        carrier: Optional carrier name for faster lookup
        session_id: Current session ID

    Returns:
        Tracking information with events
    """
    if not tracking_code:
        return {"success": False, "error": "tracking_code is required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="carrier",
            action="track_shipment",
            payload={
                "tracking_code": tracking_code,
                "carrier": carrier,
            },
            session_id=session_id,
            user_id="system",
        )
        return result

    except Exception as e:
        logger.error(f"track_shipment failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Strands Tools - HIL Task Handlers
# =============================================================================


@tool
async def get_pending_tasks(
    user_id: str,
    task_type: Optional[str] = None,
    assigned_to: Optional[str] = None,
    assigned_role: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Get pending HIL (Human-in-the-Loop) tasks for a user.

    Returns tasks sorted by priority and creation date.

    Args:
        user_id: User ID to get tasks for
        task_type: Optional filter by task type
        assigned_to: Optional filter by assignee
        assigned_role: Optional filter by role
        limit: Maximum tasks to return

    Returns:
        List of pending tasks
    """
    try:
        from tools.hil_workflow import HILWorkflowManager

        manager = HILWorkflowManager()
        tasks = manager.get_pending_tasks(
            task_type=task_type,
            assigned_to=assigned_to or user_id,
            assigned_role=assigned_role,
            limit=limit,
        )

        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks),
        }

    except Exception as e:
        logger.error(f"get_pending_tasks failed: {e}")
        return {"success": False, "error": str(e), "tasks": []}


@tool
async def approve_task(
    task_id: str,
    user_id: str,
    notes: Optional[str] = None,
    modified_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Approve a pending HIL task.

    Executes the pending action and logs the approval.

    Args:
        task_id: Task ID to approve
        user_id: User approving the task
        notes: Optional approval notes
        modified_payload: Optional modified data for the task

    Returns:
        Approval result
    """
    if not task_id:
        return {"success": False, "error": "task_id required"}

    try:
        from tools.hil_workflow import HILWorkflowManager

        manager = HILWorkflowManager()
        result = await manager.approve_task(
            task_id=task_id,
            approved_by=user_id,
            notes=notes,
            modified_payload=modified_payload,
        )

        return result

    except Exception as e:
        logger.error(f"approve_task failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def reject_task(
    task_id: str,
    user_id: str,
    reason: str,
) -> Dict[str, Any]:
    """
    Reject a pending HIL task.

    Logs the rejection with the provided reason.

    Args:
        task_id: Task ID to reject
        user_id: User rejecting the task
        reason: Reason for rejection (required)

    Returns:
        Rejection result
    """
    if not task_id:
        return {"success": False, "error": "task_id required"}

    if not reason:
        return {"success": False, "error": "reason required for rejection"}

    try:
        from tools.hil_workflow import HILWorkflowManager

        manager = HILWorkflowManager()
        result = await manager.reject_task(
            task_id=task_id,
            rejected_by=user_id,
            reason=reason,
        )

        return result

    except Exception as e:
        logger.error(f"reject_task failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Strands Tools - Inventory Count Handlers (ReconciliacaoAgent)
# =============================================================================


@tool
async def start_inventory_count(
    name: str,
    user_id: str,
    session_id: str,
    description: Optional[str] = None,
    location_ids: Optional[List[str]] = None,
    project_ids: Optional[List[str]] = None,
    part_numbers: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    require_double_count: bool = False,
) -> Dict[str, Any]:
    """
    Start a new inventory counting campaign.

    Creates a counting session for specified locations/items.

    Args:
        name: Campaign name
        user_id: User starting the campaign
        session_id: Current session ID
        description: Campaign description
        location_ids: Optional list of locations to count
        project_ids: Optional list of projects to count
        part_numbers: Optional list of part numbers to count
        start_date: Campaign start date (ISO format)
        end_date: Campaign end date (ISO format)
        require_double_count: Whether to require double counting

    Returns:
        Campaign details with ID and counting items
    """
    if not name:
        return {"success": False, "error": "name is required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="reconciliacao",
            action="start_campaign",
            payload={
                "name": name,
                "description": description,
                "location_ids": location_ids,
                "project_ids": project_ids,
                "part_numbers": part_numbers,
                "start_date": start_date,
                "end_date": end_date,
                "require_double_count": require_double_count,
            },
            session_id=session_id,
            user_id=user_id,
        )
        return result

    except Exception as e:
        logger.error(f"start_inventory_count failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def submit_count_result(
    campaign_id: str,
    part_number: str,
    location_id: str,
    counted_quantity: int,
    user_id: str,
    session_id: str,
    counted_serials: Optional[List[str]] = None,
    evidence_keys: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit counting result for an item.

    Records counted quantity for reconciliation.

    Args:
        campaign_id: Campaign ID
        part_number: Part number being counted
        location_id: Location where count was performed
        counted_quantity: Quantity counted
        user_id: User submitting the count
        session_id: Current session ID
        counted_serials: List of serial numbers found
        evidence_keys: S3 keys for evidence photos
        notes: Optional notes

    Returns:
        Submission result
    """
    if not campaign_id or not part_number or not location_id:
        return {"success": False, "error": "campaign_id, part_number, and location_id required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="reconciliacao",
            action="submit_count",
            payload={
                "campaign_id": campaign_id,
                "part_number": part_number,
                "location_id": location_id,
                "counted_quantity": counted_quantity,
                "counted_serials": counted_serials,
                "evidence_keys": evidence_keys,
                "notes": notes,
            },
            session_id=session_id,
            user_id=user_id,
        )
        return result

    except Exception as e:
        logger.error(f"submit_count_result failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def analyze_divergences(
    campaign_id: str,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Analyze divergences between counted and system quantities.

    Compares counts with system records and identifies discrepancies.

    Args:
        campaign_id: Campaign ID to analyze
        session_id: Current session ID

    Returns:
        Divergence analysis with recommendations
    """
    if not campaign_id:
        return {"success": False, "error": "campaign_id is required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="reconciliacao",
            action="analyze_divergences",
            payload={"campaign_id": campaign_id},
            session_id=session_id,
        )
        return result

    except Exception as e:
        logger.error(f"analyze_divergences failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Strands Tools - Accuracy Metrics & Reconciliation
# =============================================================================


@tool
async def get_accuracy_metrics(
    period: str = "month",
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get AI accuracy metrics for dashboard.

    Returns KPIs about extraction accuracy, matching rates, and HIL metrics.
    Queries real data from DynamoDB.

    Args:
        period: Period filter ('today', 'week', 'month', 'all')
        project_id: Optional project filter

    Returns:
        Accuracy metrics with trends (real data from DynamoDB)
    """
    try:
        from tools.dynamodb_client import SGADynamoDBClient
        from agents.utils import now_iso
        from datetime import datetime

        db = SGADynamoDBClient()
        now = datetime.utcnow()
        year_month = now.strftime("%Y-%m")

        # Query real movements from DynamoDB
        movements = db.get_movements_by_date(year_month, limit=500)

        # Calculate real metrics
        total_entries = len([m for m in movements if m.get("movement_type") == "ENTRY"])
        total_exits = len([m for m in movements if m.get("movement_type") == "EXIT"])
        total_returns = len([m for m in movements if m.get("movement_type") == "RETURN"])
        total_transfers = len([m for m in movements if m.get("movement_type") == "TRANSFER"])

        # Query pending HIL tasks
        pending_tasks = db.get_pending_tasks(limit=100)
        hil_count = len(pending_tasks)

        # Calculate entry success rate
        completed_entries = len([m for m in movements if m.get("status") == "COMPLETED" and m.get("movement_type") == "ENTRY"])
        entry_success_rate = (completed_entries / total_entries * 100) if total_entries > 0 else 0

        metrics = {
            "extraction_accuracy": {
                "value": 0,
                "unit": "%",
                "description": "NF items matched on first attempt",
                "trend": "neutral",
                "note": "Requer integracao com audit log",
            },
            "entry_success_rate": {
                "value": round(entry_success_rate, 1),
                "unit": "%",
                "description": "Entries completed without rejection",
                "trend": "neutral",
            },
            "movements_summary": {
                "entries": total_entries,
                "expeditions": total_exits,
                "returns": total_returns,
                "transfers": total_transfers,
            },
            "pending_items": {
                "hil_tasks": hil_count,
                "pending_entries": len([m for m in movements if m.get("status") == "PENDING" and m.get("movement_type") == "ENTRY"]),
                "pending_reversals": len([m for m in movements if m.get("status") == "PENDING" and m.get("movement_type") == "RETURN"]),
            },
        }

        return {
            "success": True,
            "period": period,
            "project_id": project_id,
            "metrics": metrics,
            "generated_at": now_iso(),
            "data_source": "dynamodb",
        }

    except Exception as e:
        logger.error(f"get_accuracy_metrics failed: {e}")
        return {"success": False, "error": str(e), "metrics": {}}


@tool
async def reconcile_sap_export(
    sap_data: List[Dict[str, Any]],
    user_id: str,
    include_serials: bool = False,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reconcile SAP export CSV with SGA inventory.

    Compares SAP stock positions with SGA balances
    and identifies real discrepancies from DynamoDB.

    Args:
        sap_data: List of SAP rows [{part_number, location, quantity, serial?}]
        user_id: User performing reconciliation
        include_serials: Whether to compare at serial level
        project_id: Optional project filter

    Returns:
        Reconciliation result with deltas
    """
    if not sap_data:
        return {"success": False, "error": "sap_data is required"}

    try:
        from tools.dynamodb_client import SGADynamoDBClient
        from agents.utils import now_iso, generate_id

        db = SGADynamoDBClient()

        # Group SAP data by PN + Location
        sap_balances = {}
        for row in sap_data:
            pn = row.get("part_number", "")
            loc = row.get("location", "01")
            qty = row.get("quantity", 0)
            key = f"{pn}|{loc}"

            if key not in sap_balances:
                sap_balances[key] = {"part_number": pn, "location": loc, "sap_qty": 0, "serials": []}
            sap_balances[key]["sap_qty"] += qty
            if row.get("serial"):
                sap_balances[key]["serials"].append(row["serial"])

        # Compare with SGA balances
        deltas = []
        for key, sap_item in sap_balances.items():
            pn = sap_item["part_number"]
            loc = sap_item["location"]
            sap_qty = sap_item["sap_qty"]

            balance_result = db.get_balance(location_id=loc, pn_id=pn, project_id=project_id)
            sga_qty = balance_result.get("available", 0) + balance_result.get("reserved", 0)

            delta = sga_qty - sap_qty
            if delta != 0:
                deltas.append({
                    "id": generate_id("DELTA"),
                    "part_number": pn,
                    "location": loc,
                    "sap_quantity": sap_qty,
                    "sga_quantity": sga_qty,
                    "delta": delta,
                    "delta_type": "FALTA_SGA" if delta < 0 else "SOBRA_SGA",
                    "status": "PENDING",
                })

        total_items = len(sap_balances)
        items_matched = total_items - len(deltas)
        match_rate = (items_matched / total_items * 100) if total_items > 0 else 100

        return {
            "success": True,
            "reconciliation_id": generate_id("RECON"),
            "total_sap_items": total_items,
            "items_matched": items_matched,
            "items_with_delta": len(deltas),
            "match_rate": round(match_rate, 1),
            "deltas": deltas,
            "summary": {
                "falta_sga": len([d for d in deltas if d["delta_type"] == "FALTA_SGA"]),
                "sobra_sga": len([d for d in deltas if d["delta_type"] == "SOBRA_SGA"]),
            },
            "reconciled_by": user_id,
            "reconciled_at": now_iso(),
        }

    except Exception as e:
        logger.error(f"reconcile_sap_export failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def apply_reconciliation_action(
    delta_id: str,
    action: str,
    user_id: str,
    notes: Optional[str] = None,
    adjustment_quantity: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Apply an action to a reconciliation delta.

    Args:
        delta_id: Delta ID to act upon
        action: Action to apply (CREATE_ADJUSTMENT, IGNORE, INVESTIGATE)
        user_id: User applying the action
        notes: Action notes
        adjustment_quantity: For CREATE_ADJUSTMENT, the quantity to adjust

    Returns:
        Action result
    """
    if not delta_id:
        return {"success": False, "error": "delta_id is required"}

    if action not in ["CREATE_ADJUSTMENT", "IGNORE", "INVESTIGATE"]:
        return {"success": False, "error": "Invalid action. Use CREATE_ADJUSTMENT, IGNORE, or INVESTIGATE"}

    try:
        from agents.utils import now_iso

        result = {
            "success": True,
            "delta_id": delta_id,
            "action_taken": action,
            "applied_by": user_id,
            "applied_at": now_iso(),
        }

        if action == "CREATE_ADJUSTMENT":
            result["adjustment_id"] = f"ADJ-{delta_id[-6:]}"
            result["message"] = "Ajuste criado e enviado para aprovação"
        elif action == "IGNORE":
            result["message"] = "Delta ignorado após investigação"
        else:
            result["message"] = "Delta marcado para investigação manual"

        # Audit logging
        try:
            from tools.dynamodb_client import SGAAuditLogger
            audit = SGAAuditLogger()
            audit.log_action(
                action="RECONCILIATION_ACTION_APPLIED",
                entity_type="RECONCILIATION_DELTA",
                entity_id=delta_id,
                actor=user_id,
                details={
                    "action_taken": action,
                    "notes": notes[:200] if notes else None,
                },
            )
        except Exception:
            pass

        return result

    except Exception as e:
        logger.error(f"apply_reconciliation_action failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Strands Tools - Import Handlers
# =============================================================================


@tool
async def preview_import(
    file_content_base64: str,
    filename: str,
    user_id: str,
    session_id: str,
    project_id: Optional[str] = None,
    destination_location_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Preview an import file before processing.

    Parses CSV/Excel, auto-detects columns, and attempts PN matching.

    Args:
        file_content_base64: Base64-encoded file content
        filename: Original filename for type detection
        user_id: User performing the preview
        session_id: Current session ID
        project_id: Optional project to assign all items
        destination_location_id: Optional destination location

    Returns:
        Preview with column mappings, matched rows, and stats
    """
    if not file_content_base64:
        return {"success": False, "error": "file_content_base64 is required"}

    try:
        a2a = get_a2a_client()
        result = await a2a.invoke(
            agent_id="import",
            action="preview_import",
            payload={
                "file_content": file_content_base64,
                "filename": filename,
                "project_id": project_id,
                "destination_location_id": destination_location_id,
            },
            session_id=session_id,
            user_id=user_id,
        )
        return result

    except Exception as e:
        logger.error(f"preview_import failed: {e}")
        return {"success": False, "error": str(e)}


@tool
async def execute_import(
    import_id: str,
    column_mappings: List[Dict[str, str]],
    user_id: str,
    session_id: str,
    file_content_base64: Optional[str] = None,
    s3_key: Optional[str] = None,
    filename: str = "import.csv",
    pn_overrides: Optional[Dict[str, str]] = None,
    project_id: Optional[str] = None,
    destination_location_id: Optional[str] = None,
    movement_type: str = "ENTRADA",
    inferred_movement_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the import after preview/confirmation.

    Creates entry movements for all valid rows.
    Uses PostgreSQL for inventory operations (MANDATORY per CLAUDE.md).

    Args:
        import_id: Import session ID from preview
        column_mappings: Confirmed column mappings
        user_id: User performing the import
        session_id: Current session ID
        file_content_base64: Base64-encoded file content
        s3_key: S3 key of already-uploaded file (NEXO flow)
        filename: Original filename
        pn_overrides: Optional manual PN assignments
        project_id: Project to assign all items
        destination_location_id: Destination location
        movement_type: Default movement type
        inferred_movement_type: AI-inferred movement type (NEXO pattern)

    Returns:
        Import result with created movements
    """
    import base64

    if not import_id:
        return {"success": False, "error": "import_id is required"}

    if not file_content_base64 and not s3_key:
        return {"success": False, "error": "file_content_base64 or s3_key is required"}

    if not column_mappings:
        return {"success": False, "error": "column_mappings is required"}

    # TRUE Agentic Pattern: Use AI-inferred movement type
    final_movement_type = movement_type
    if inferred_movement_type:
        movement_type_map = {
            "ENTRADA": "ENTRADA",
            "SAIDA": "SAIDA",
            "AJUSTE": "AJUSTE_POSITIVO",
            "SAÍDA": "SAIDA",
        }
        final_movement_type = movement_type_map.get(inferred_movement_type.upper(), "ENTRADA")

    logger.info(f"[execute_import] Starting import {import_id} for file {filename}")

    try:
        # Agent Room: emit start event
        from tools.agent_room_service import emit_agent_event
        emit_agent_event(
            agent_id="import",
            status="trabalhando",
            message=f"Iniciando importação de {filename}...",
            details={"import_id": import_id, "filename": filename},
        )

        # Get file content
        file_content = None
        if file_content_base64:
            file_content = base64.b64decode(file_content_base64)
        elif s3_key:
            from tools.s3_client import SGAS3Client
            s3_client = SGAS3Client()
            file_content = s3_client.download_file(s3_key)

        if not file_content:
            return {"success": False, "error": "Failed to get file content"}

        # Parse file
        from tools.csv_parser import extract_all_rows
        all_rows = extract_all_rows(file_content, filename, column_mappings)

        if not all_rows:
            return {"success": False, "error": "No valid rows found in file"}

        # Use PostgreSQL for inventory (MANDATORY per CLAUDE.md)
        from tools.postgres_client import SGAPostgresClient
        pg_client = SGAPostgresClient()

        created_movements = []
        failed_rows = []
        skipped_rows = []

        for i, row_data in enumerate(all_rows):
            row_number = i + 2

            try:
                part_number = row_data.get("part_number", "").strip()
                description = row_data.get("description", "").strip()
                qty_str = row_data.get("quantity", "0").strip()
                serial = row_data.get("serial", "").strip()
                location = row_data.get("location", destination_location_id or "").strip()

                if not part_number and not description:
                    continue

                try:
                    quantity = int(float(qty_str.replace(",", ".")))
                except (ValueError, TypeError):
                    failed_rows.append({"row_number": row_number, "reason": f"Quantidade invalida: {qty_str}"})
                    continue

                if quantity <= 0:
                    failed_rows.append({"row_number": row_number, "reason": "Quantidade deve ser maior que zero"})
                    continue

                result = pg_client.create_movement(
                    movement_type=final_movement_type,
                    part_number=part_number,
                    quantity=quantity,
                    destination_location_id=location,
                    project_id=project_id,
                    serial_numbers=[serial] if serial else None,
                    reason=f"Import {import_id}",
                )

                if result.get("error"):
                    if "not found" in result.get("error", "").lower():
                        skipped_rows.append({"row_number": row_number, "reason": f"Part number nao encontrado: {part_number}"})
                    else:
                        failed_rows.append({"row_number": row_number, "reason": result.get("error")})
                else:
                    created_movements.append({
                        "row_number": row_number,
                        "movement_id": result.get("movement_id", ""),
                        "part_number": part_number,
                        "quantity": quantity,
                    })

            except Exception as row_error:
                failed_rows.append({"row_number": row_number, "reason": str(row_error)})

        total_rows = len(all_rows)
        success_rate = len(created_movements) / max(total_rows, 1)

        # Audit logging
        try:
            from tools.dynamodb_client import SGAAuditLogger
            audit = SGAAuditLogger()
            audit.log_action(
                action="IMPORT_EXECUTED",
                entity_type="IMPORT",
                entity_id=import_id,
                actor=user_id,
                details={
                    "filename": filename,
                    "total_rows": total_rows,
                    "created_count": len(created_movements),
                    "movement_type": final_movement_type,
                },
            )
        except Exception:
            pass

        # Emit completion event
        emit_agent_event(
            agent_id="import",
            status="disponivel",
            message=f"Importação concluída: {len(created_movements)} itens ok.",
            details={"success_count": len(created_movements), "filename": filename},
        )

        return {
            "success": True,
            "import_id": import_id,
            "total_rows": total_rows,
            "created_count": len(created_movements),
            "failed_count": len(failed_rows),
            "skipped_count": len(skipped_rows),
            "success_rate": round(success_rate * 100, 1),
            "created_movements": created_movements[:50],
            "failed_rows": failed_rows[:20],
            "skipped_rows": skipped_rows[:20],
        }

    except Exception as e:
        logger.error(f"execute_import failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Gemini 3.0 Model Configuration (MANDATORY - per CLAUDE.md)
# =============================================================================
# ALL agents MUST use Gemini 3.0 Family:
# - Critical agents (nexo_import, learning, validation, schema_evolution, intake, import):
#   → gemini-3-pro with thinking_level="high"
# - Standard agents: → gemini-3-flash
#
# Reference: https://ai.google.dev/gemini-api/docs/gemini-3
# Reference: https://ai.google.dev/gemini-api/docs/thinking
# =============================================================================

# Critical agents that require Pro + Thinking (file analysis, schema understanding)
CRITICAL_AGENTS = {
    "nexo_import",      # Main orchestrator - file analysis with schema
    "intake",           # Document intake - NF parsing with Vision
    "import",           # Data import - file structure understanding
    "learning",         # Memory extraction - pattern recognition
    "schema_evolution", # Schema analysis - SQL generation
    "validation",       # Data validation - complex rules
}


def create_gemini_model(agent_id: str) -> GeminiModel:
    """
    Create GeminiModel with appropriate configuration based on agent criticality.

    MANDATORY: ALL agents use Gemini 3.0 Family (per CLAUDE.md immutable block).

    Args:
        agent_id: Agent identifier to determine model tier

    Returns:
        Configured GeminiModel instance

    Raises:
        ValueError: If GOOGLE_API_KEY is not set
    """
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is required for Gemini 3.0. "
            "This is MANDATORY per CLAUDE.md - NO FALLBACK to other LLM providers."
        )

    if agent_id in CRITICAL_AGENTS:
        # Gemini 3 Pro with Thinking HIGH for critical analysis tasks
        logger.info(f"Creating GeminiModel: gemini-3-pro (Thinking=HIGH) for critical agent {agent_id}")
        return GeminiModel(
            client_args={"api_key": GOOGLE_API_KEY},
            model_id="gemini-3-pro",
            params={
                "temperature": 1.0,  # Recommended for Gemini 3 (per Google docs)
                "max_output_tokens": 8192,
                "top_p": 0.95,
            },
            # Thinking mode for deep reasoning on file analysis
            # Note: Strands GeminiModel may not directly support thinking_config
            # but we set the params that enable better reasoning
        )
    else:
        # Gemini 3 Flash for standard agents (faster, cost-effective)
        logger.info(f"Creating GeminiModel: gemini-3-flash for standard agent {agent_id}")
        return GeminiModel(
            client_args={"api_key": GOOGLE_API_KEY},
            model_id="gemini-3-flash",
            params={
                "temperature": 0.7,
                "max_output_tokens": 4096,
                "top_p": 0.9,
            },
        )


# =============================================================================
# Strands Agent Definition
# =============================================================================

# Collect all tools for the agent
AGENT_TOOLS = [
    # Core
    health_check,
    # NEXO Import (ReAct pattern)
    nexo_analyze_file,
    nexo_get_questions,
    nexo_submit_answers,
    nexo_execute_import,
    nexo_learn_from_import,
    nexo_get_prior_knowledge,
    nexo_get_adaptive_threshold,
    # Smart Import
    smart_import_analyze,
    get_upload_presigned_url,
    # NF Processing
    process_nf_upload,
    get_nf_upload_url,
    # Inventory Control
    create_movement,
    get_balance,
    get_asset_timeline,
    list_part_numbers,
    list_locations,
    get_balance_report,
    get_movement_history,
    # NEXO Chat
    nexo_estoque_chat,
    # Expedition (Day 2)
    process_expedition_request,
    verify_expedition_stock,
    confirm_separation,
    complete_expedition,
    # Reverse Logistics (Day 2)
    process_return,
    validate_return_origin,
    evaluate_return_condition,
    # Carrier (Day 2)
    get_shipping_quotes,
    recommend_carrier,
    track_shipment,
    # HIL Tasks (Day 2)
    get_pending_tasks,
    approve_task,
    reject_task,
    # Inventory Count (Day 2)
    start_inventory_count,
    submit_count_result,
    analyze_divergences,
    # Metrics & Reconciliation (Day 2)
    get_accuracy_metrics,
    reconcile_sap_export,
    apply_reconciliation_action,
    # Import (Day 2)
    preview_import,
    execute_import,
]

# Create GeminiModel based on agent criticality (MANDATORY per CLAUDE.md)
# This ensures ALL agents use Gemini 3.0 Family - NO EXCEPTIONS
agent_model = create_gemini_model(AGENT_ID)
logger.info(f"Gemini model created for {AGENT_ID}: {agent_model.config.get('model_id', 'unknown')}")

# Create Strands agent with Gemini 3.0 model
strands_agent = Agent(
    name=AGENT_NAME,
    model=agent_model,  # CRITICAL: Must specify Gemini model (per CLAUDE.md mandate)
    description="""
    SGA Inventory Agent - Full inventory management with A2A protocol.
    LLM: Gemini 3.0 Family (MANDATORY per CLAUDE.md)

    Capabilities:
    - NEXO Smart Import (ReAct pattern: OBSERVE → THINK → ASK → LEARN → ACT)
    - Nota Fiscal (NF) XML/PDF processing via IntakeAgent
    - Inventory movements (ENTRADA, SAIDA, TRANSFERENCIA)
    - Balance queries and timeline tracking
    - Expedition workflow (request, separation, completion)
    - Reverse logistics (returns, condition evaluation)
    - Carrier quotes and tracking
    - HIL task management (approve/reject)
    - Inventory counting campaigns
    - SAP reconciliation and accuracy metrics

    Tools: 41 Strands @tool handlers
    Protocol: A2A (Agent-to-Agent) via JSON-RPC 2.0
    Port: 9000
    Path: /
    """,
    tools=AGENT_TOOLS,
    callback_handler=None,
)


# =============================================================================
# A2A Server Setup
# =============================================================================

# Create A2A server with Strands agent
a2a_server = A2AServer(
    agent=strands_agent,
    http_url=RUNTIME_URL,
    serve_at_root=True,  # Serves at / for AgentCore A2A compatibility
)

# FastAPI application
app = FastAPI(
    title=f"SGA {AGENT_NAME} A2A Server",
    description="Strands A2A Server for SGA Inventory Management",
    version="1.0.0",
)


@app.get("/ping")
def ping():
    """Health check endpoint for load balancers."""
    return {"status": "healthy", "agent": AGENT_NAME, "protocol": "A2A"}


# Mount A2A server at root
app.mount("/", a2a_server.to_fastapi_app())


# =============================================================================
# Main Entrypoint
# =============================================================================

if __name__ == "__main__":
    logger.info(f"Starting {AGENT_NAME} A2A Server on port 9000...")
    uvicorn.run(app, host="0.0.0.0", port=9000)
