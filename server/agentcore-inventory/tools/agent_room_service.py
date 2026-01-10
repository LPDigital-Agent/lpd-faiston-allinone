# =============================================================================
# Agent Room Service - Faiston SGA
# =============================================================================
# Aggregates data from various sources for the Agent Room "Sala de Transparencia".
# Provides humanized views of agent activities, learning stories, and workflows.
#
# Data Sources:
# - DynamoDB Audit Log: Recent agent events
# - DynamoDB Sessions: Active agent sessions
# - HIL Tasks: Pending human decisions
# - Knowledge Base: Learning stories (future)
#
# Design:
# - Polling-first architecture (frontend polls every 3-5 seconds)
# - Single endpoint returns all Agent Room data
# - Leverages existing infrastructure (no new tables needed)
# =============================================================================

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from tools.humanizer import (
    get_friendly_agent_name,
    get_agent_description,
    get_friendly_status,
    get_status_label,
    humanize_audit_entry,
    AGENT_FRIENDLY_NAMES,
)


# =============================================================================
# Configuration
# =============================================================================

# Maximum number of recent events to return
MAX_RECENT_EVENTS = 50

# Primary agents to show in Agent Room (in display order, grouped by function)
PRIMARY_AGENTS = [
    # Importação & Entrada
    "nexo_import",
    "intake",
    "import",
    # Controle & Validação
    "estoque_control",
    "compliance",
    "reconciliacao",
    # Logística & Movimento
    "expedition",
    "carrier",
    "reverse",
    # Evolução & Aprendizado
    "schema_evolution",
    "learning",
    # Suporte & Pesquisa
    "observation",
    "equipment_research",
    "comunicacao",
]

# Agent icons (Lucide icon names)
AGENT_ICONS = {
    "NEXO": "Bot",
    "Leitor de Notas": "FileText",
    "Importador": "Upload",
    "Validador": "Shield",
    "Arquiteto": "Database",
    "Memoria": "Brain",
    "Controlador": "Package",
    "Reconciliador": "Scale",
    "Despachante": "Send",
    "Logistica": "Truck",
    "Comunicador": "Bell",
    "NEXO Estoque": "MessageSquare",
    "Observador": "Eye",
    "Pesquisador": "Search",
    "Reversa": "RotateCcw",
}

# Agent colors
AGENT_COLORS = {
    "NEXO": "magenta",
    "Leitor de Notas": "blue",
    "Importador": "cyan",
    "Validador": "green",
    "Arquiteto": "orange",
    "Memoria": "purple",
    "Controlador": "slate",
    "Reconciliador": "yellow",
    "Despachante": "teal",
    "Logistica": "indigo",
    "Comunicador": "pink",
    "NEXO Estoque": "violet",
    "Observador": "emerald",
    "Pesquisador": "amber",
    "Reversa": "rose",
}


# =============================================================================
# Agent Profiles Service
# =============================================================================

def get_agent_profiles(session_statuses: Optional[Dict[str, str]] = None) -> List[Dict]:
    """
    Get humanized agent profiles for the Agent Room.

    Args:
        session_statuses: Optional dict of agent_id -> status from active sessions

    Returns:
        List of agent profile dicts with friendly names, descriptions, status
    """
    session_statuses = session_statuses or {}

    profiles = []
    for agent_id in PRIMARY_AGENTS:
        friendly_name = get_friendly_agent_name(agent_id)
        status_raw = session_statuses.get(agent_id, "idle")
        friendly_status = get_friendly_status(status_raw)

        profiles.append({
            "id": agent_id,
            "technicalName": agent_id,
            "friendlyName": friendly_name,
            "description": get_agent_description(friendly_name),
            "avatar": AGENT_ICONS.get(friendly_name, "Bot"),
            "color": AGENT_COLORS.get(friendly_name, "slate"),
            "status": friendly_status,
            "statusLabel": get_status_label(friendly_status),
            "lastActivity": None,  # Can be populated from session data
        })

    return profiles


# =============================================================================
# Recent Events Service (Live Feed)
# =============================================================================

def get_recent_events(
    days_back: int = 1,
    limit: int = MAX_RECENT_EVENTS,
    db_client=None
) -> List[Dict]:
    """
    Get recent humanized events from the audit log for the Live Feed.

    Args:
        days_back: How many days of history to query
        limit: Maximum events to return
        db_client: Optional DynamoDB client (lazy loaded if not provided)

    Returns:
        List of humanized event dicts sorted by timestamp (newest first)
    """
    if db_client is None:
        from tools.dynamodb_client import SGADynamoDBClient
        db_client = SGADynamoDBClient(table_name=_get_audit_table())

    events = []
    now = datetime.utcnow()

    # Query each day's partition
    for day_offset in range(days_back):
        date = now - timedelta(days=day_offset)
        date_key = date.strftime("%Y-%m-%d")
        pk = f"LOG#{date_key}"

        try:
            raw_events = db_client.query_pk(pk, limit=limit)
            events.extend(raw_events)
        except Exception as e:
            print(f"[AgentRoom] Error querying audit log for {date_key}: {e}")

    # Sort by timestamp descending and limit
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    events = events[:limit]

    # Humanize each event
    humanized = []
    for event in events:
        try:
            humanized_event = humanize_audit_entry(event)
            humanized.append({
                "id": event.get("event_id", event.get("SK", "")),
                "timestamp": humanized_event["timestamp"],
                "agentName": humanized_event["agent"],
                "message": humanized_event["message"],
                "type": humanized_event["type"],
                "eventType": humanized_event.get("event_type", "unknown"),
            })
        except Exception as e:
            print(f"[AgentRoom] Error humanizing event: {e}")

    return humanized


# =============================================================================
# Learning Stories Service
# =============================================================================

# Static learning stories (will be replaced with KB integration)
LEARNING_STORIES_STATIC = [
    {
        "id": "learn-1",
        "learnedAt": "2026-01-09T14:30:00Z",
        "agentName": "NEXO",
        "story": "Aprendi que suas planilhas geralmente tem o codigo na coluna B",
        "confidence": "alta",
    },
    {
        "id": "learn-2",
        "learnedAt": "2026-01-08T10:15:00Z",
        "agentName": "Leitor de Notas",
        "story": "Reconheco o formato dos seus arquivos SAP automaticamente",
        "confidence": "alta",
    },
    {
        "id": "learn-3",
        "learnedAt": "2026-01-07T16:45:00Z",
        "agentName": "Importador",
        "story": "Sei que 'SN' significa 'Serial Number' nos seus documentos",
        "confidence": "media",
    },
    {
        "id": "learn-4",
        "learnedAt": "2026-01-06T09:20:00Z",
        "agentName": "Memoria",
        "story": "Guardei os padroes de nomenclatura do projeto MXRF",
        "confidence": "alta",
    },
    {
        "id": "learn-5",
        "learnedAt": "2026-01-05T11:00:00Z",
        "agentName": "Arquiteto",
        "story": "Criei a coluna 'observacao_tecnica' para seus dados especiais",
        "confidence": "alta",
    },
]


def get_learning_stories(limit: int = 10) -> List[Dict]:
    """
    Get learning stories for the Agent Room.

    Currently returns static stories. Will be enhanced to query
    from Knowledge Base when learning agent is fully integrated.

    Args:
        limit: Maximum stories to return

    Returns:
        List of learning story dicts
    """
    # TODO: Replace with KB query when learning agent stores patterns
    # from tools.knowledge_base_retrieval_tool import KBRetrievalTool
    # kb = KBRetrievalTool()
    # patterns = kb.query("learned patterns", limit=limit)

    return LEARNING_STORIES_STATIC[:limit]


# =============================================================================
# Active Workflow Service
# =============================================================================

def get_active_workflow(session_id: Optional[str] = None) -> Optional[Dict]:
    """
    Get the currently active workflow for display in the timeline.

    Args:
        session_id: Optional session ID to get specific workflow

    Returns:
        Active workflow dict or None if no workflow is active
    """
    # TODO: Query active import sessions or processing jobs
    # For now, return a sample workflow when there's activity

    return {
        "id": "workflow-sample",
        "name": "Importacao de Planilha",
        "startedAt": datetime.utcnow().isoformat() + "Z",
        "steps": [
            {"id": "step-1", "label": "Recebido", "icon": "FileText", "status": "concluido"},
            {"id": "step-2", "label": "Analisando", "icon": "Search", "status": "concluido"},
            {"id": "step-3", "label": "Validando", "icon": "Shield", "status": "atual"},
            {"id": "step-4", "label": "Importando", "icon": "Upload", "status": "pendente"},
            {"id": "step-5", "label": "Concluido", "icon": "CheckCircle", "status": "pendente"},
        ],
    }


# =============================================================================
# Pending Decisions Service (HIL Integration)
# =============================================================================

def get_pending_decisions(user_id: str, db_client=None) -> List[Dict]:
    """
    Get pending HIL decisions for the Agent Room.

    Leverages existing HIL task infrastructure.

    Args:
        user_id: User ID to filter tasks
        db_client: Optional DynamoDB client

    Returns:
        List of humanized pending decision dicts
    """
    if db_client is None:
        from tools.dynamodb_client import SGADynamoDBClient
        db_client = SGADynamoDBClient()

    decisions = []

    try:
        # Query pending HIL tasks
        raw_tasks = db_client.query_gsi(
            gsi_name="GSI1",
            pk_value=f"USER#{user_id}",
            sk_prefix="TASK#PENDING#",
            limit=20,
        )

        for task in raw_tasks:
            task_type = task.get("task_type", "unknown")
            details = task.get("details", {})

            # Humanize the task
            question = _humanize_hil_question(task_type, details)
            options = _get_hil_options(task_type)

            decisions.append({
                "id": task.get("task_id", task.get("SK", "")),
                "question": question,
                "options": options,
                "priority": task.get("priority", "normal"),
                "createdAt": task.get("created_at", datetime.utcnow().isoformat()),
                "taskType": task_type,
                "entityId": task.get("entity_id"),
            })

    except Exception as e:
        print(f"[AgentRoom] Error getting pending decisions: {e}")

    return decisions


def _humanize_hil_question(task_type: str, details: dict) -> str:
    """Generate humanized question for HIL task."""
    templates = {
        "confirm_nf_entry": "Encontrei uma nota fiscal. Posso importar os {count} itens?",
        "create_new_pn": "Encontrei um item novo: {description}. Posso criar o cadastro?",
        "create_column": "Seus dados tem um campo novo: '{column}'. Posso criar essa coluna?",
        "resolve_mapping": "Nao consegui mapear '{source}'. Qual coluna devo usar?",
        "approve_import": "Tenho {count} itens prontos. Posso importar?",
        "review_divergence": "Encontrei uma divergencia no item {item}. O que devo fazer?",
    }

    template = templates.get(task_type, "Preciso da sua decisao sobre uma tarefa.")

    try:
        return template.format(**details)
    except KeyError:
        return template


def _get_hil_options(task_type: str) -> List[Dict]:
    """Get humanized options for HIL task type."""
    options_map = {
        "confirm_nf_entry": [
            {"label": "Sim, importar", "action": "approve"},
            {"label": "Revisar primeiro", "action": "review"},
        ],
        "create_new_pn": [
            {"label": "Criar cadastro", "action": "approve"},
            {"label": "Ignorar", "action": "reject"},
        ],
        "create_column": [
            {"label": "Criar coluna", "action": "approve"},
            {"label": "Usar metadata", "action": "metadata"},
            {"label": "Ignorar", "action": "reject"},
        ],
        "approve_import": [
            {"label": "Importar", "action": "approve"},
            {"label": "Cancelar", "action": "reject"},
        ],
    }

    return options_map.get(task_type, [
        {"label": "Aprovar", "action": "approve"},
        {"label": "Rejeitar", "action": "reject"},
    ])


# =============================================================================
# Main Aggregation Function
# =============================================================================

def get_agent_room_data(user_id: str, session_id: Optional[str] = None) -> Dict:
    """
    Get all Agent Room data in a single call.

    This is the main entry point for the frontend polling.

    Args:
        user_id: Current user ID
        session_id: Optional session ID for workflow context

    Returns:
        Complete Agent Room data dict with all panels
    """
    # Lazy load DynamoDB client
    from tools.dynamodb_client import SGADynamoDBClient
    db_client = SGADynamoDBClient()

    # Aggregate all data
    return {
        "success": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "agents": get_agent_profiles(),
        "liveFeed": get_recent_events(days_back=1, limit=30, db_client=db_client),
        "learningStories": get_learning_stories(limit=5),
        "activeWorkflow": get_active_workflow(session_id),
        "pendingDecisions": get_pending_decisions(user_id, db_client),
    }


# =============================================================================
# Helpers
# =============================================================================

def _get_audit_table() -> str:
    """Get audit table name from environment."""
    return os.environ.get("SGA_AUDIT_TABLE", "faiston-sga-audit-prod")
