# =============================================================================
# Consolidate Memories Tool - SLEEP CYCLE (Lei 4)
# =============================================================================
# The "Sonhador" (Dreamer) tool that runs at 03:00 AM to:
# 1. List raw memories from the day
# 2. Forget weak memories (Hebbian weight < 0.3 + age > 24h)
# 3. Consolidate patterns into Master Memories
# 4. Mark processed memories
#
# GENESIS_KERNEL Laws Applied:
# - Lei 2 (Veritas): New memories are MASTER until Tutor validation
# - Lei 4 (Ciclos): This process is MANDATORY, cannot be skipped
# - Lei 5 (Núcleo): Cannot alter origin_type of existing memories
#
# Triggered by: EventBridge at 03:00 AM UTC (cron: 0 3 * * ? *)
# =============================================================================

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

# NEXO Mind imports
from shared.memory_manager import (
    AgentMemoryManager,
    MemoryOriginType,
    MemorySourceType,
    NexoMemoryMetadata,
)
from shared.genesis_kernel import (
    should_forget,
    interpret_hebbian_weight,
    is_consolidation_period,
    GeneticLaw,
)
from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_memory_operation

logger = logging.getLogger(__name__)

# Configuration
AGENT_ID = "learning"
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "nexo_sga_learning_memory-u3ypElEdl1")

# Audit emitter
audit = AgentAuditEmitter(agent_id=AGENT_ID)


# =============================================================================
# Pattern Detection
# =============================================================================

class ConsolidationPattern:
    """Represents a detected pattern across multiple memories."""

    def __init__(
        self,
        category: str,
        content_summary: str,
        source_ids: List[str],
        occurrences: int,
        avg_weight: float,
    ):
        self.category = category
        self.content_summary = content_summary
        self.source_ids = source_ids
        self.occurrences = occurrences
        self.avg_weight = avg_weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "content_summary": self.content_summary,
            "source_ids": self.source_ids,
            "occurrences": self.occurrences,
            "avg_weight": self.avg_weight,
        }


def _identify_patterns(
    memories: List[Dict[str, Any]],
    min_occurrences: int = 3,
) -> List[ConsolidationPattern]:
    """
    Group similar memories and identify recurring patterns.

    Uses category + content similarity for clustering.
    Patterns with >= min_occurrences become Master Memory candidates.

    Args:
        memories: List of memory records with content and metadata
        min_occurrences: Minimum occurrences to consider a pattern

    Returns:
        List of ConsolidationPattern objects
    """
    # Group by category
    groups: Dict[str, List[Dict]] = defaultdict(list)

    for mem in memories:
        category = mem.get("metadata", {}).get("category", "unknown")
        groups[category].append(mem)

    patterns = []

    for category, group in groups.items():
        if len(group) >= min_occurrences:
            # Calculate average weight
            weights = [
                m.get("metadata", {}).get("emotional_weight", 0.5)
                for m in group
            ]
            avg_weight = sum(weights) / len(weights) if weights else 0.5

            # Create consolidated content (first 200 chars of most common content)
            contents = [m.get("content", "")[:100] for m in group]
            content_summary = contents[0] if contents else ""

            patterns.append(ConsolidationPattern(
                category=category,
                content_summary=f"Padrão observado {len(group)}x: {content_summary}...",
                source_ids=[m.get("id", "") for m in group],
                occurrences=len(group),
                avg_weight=avg_weight,
            ))

    return patterns


# =============================================================================
# Sleep Cycle Tool
# =============================================================================

@trace_memory_operation("consolidate_memories")
async def consolidate_memories_tool(
    session_id: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    SLEEP CYCLE: O Sonhador acorda e processa as memórias do dia.

    This tool implements the NEXO Mind sleep cycle:
    1. ACORDAR - List raw memories from the day
    2. ESQUECER - Forget weak memories (Hebbian weight < 0.3 + age > 24h)
    3. SONHAR - Identify patterns and create Master Memories
    4. LIMPAR - Mark original memories as processed

    GENESIS_KERNEL Laws Applied:
    - Lei 2 (Veritas): Master Memories need Tutor validation
    - Lei 4 (Ciclos): This process is MANDATORY
    - Lei 5 (Núcleo): Cannot alter origin_type of existing memories

    Args:
        session_id: Optional session ID for audit
        dry_run: If True, report what would happen without executing

    Returns:
        Consolidation report with counts and actions taken
    """
    logger.info("🌙 [Sleep Cycle] Iniciando ciclo de consolidação...")

    # Verify it's consolidation period (Lei 4)
    current_hour = datetime.utcnow().hour
    if not is_consolidation_period(current_hour):
        logger.warning(
            f"🕐 [Sleep Cycle] Não é período de consolidação (hora: {current_hour}). "
            "Lei 4 permite execução manual, mas recomenda respeitar ciclos."
        )

    # Initialize memory manager for global access
    memory = AgentMemoryManager(
        agent_id=AGENT_ID,
        actor_id="sleep_cycle",
        use_global_namespace=True,
    )

    # Audit start
    await audit.log(
        event_type="SLEEP_CYCLE_START",
        action="consolidate_memories",
        session_id=session_id,
        details={"dry_run": dry_run, "hour_utc": current_hour},
    )

    # ════════════════════════════════════════════════════════════════════
    # FASE 1: ACORDAR - List raw memories from the day
    # ════════════════════════════════════════════════════════════════════
    logger.info("🌅 [Sleep Cycle] FASE 1: Listando memórias do dia...")

    # Query all recent memories (last 24h)
    raw_memories = await memory.observe(
        query="*",  # All memories
        limit=500,
        include_reflections=False,  # Only facts/inferences/episodes
    )

    # Filter for "raw" status (not yet processed)
    raw_count = len([m for m in raw_memories if m.get("metadata", {}).get("status") == "raw"])
    logger.info(f"📦 [Sleep Cycle] {len(raw_memories)} memórias totais, {raw_count} raw")

    # ════════════════════════════════════════════════════════════════════
    # FASE 2: ESQUECER - Apply Hebbian forgetting (Lei 4)
    # ════════════════════════════════════════════════════════════════════
    logger.info("🗑️ [Sleep Cycle] FASE 2: Aplicando esquecimento Hebbian...")

    to_forget: List[Dict] = []
    to_keep: List[Dict] = []
    now = datetime.utcnow()

    for mem in raw_memories:
        metadata = mem.get("metadata", {})
        weight = metadata.get("emotional_weight", 0.5)

        # Calculate age in hours
        timestamp_str = metadata.get("timestamp", "")
        if timestamp_str:
            try:
                mem_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                age_hours = (now - mem_time.replace(tzinfo=None)).total_seconds() / 3600
            except (ValueError, TypeError):
                age_hours = 0
        else:
            age_hours = 0

        # Apply Hebbian forgetting rule
        if should_forget(weight, age_hours):
            to_forget.append(mem)
            logger.debug(
                f"🧹 Esquecendo: weight={weight:.2f}, age={age_hours:.1f}h, "
                f"content={mem.get('content', '')[:50]}..."
            )
        else:
            to_keep.append(mem)

    logger.info(f"🗑️ [Sleep Cycle] {len(to_forget)} memórias fracas para esquecer")

    # Actually delete forgotten memories (unless dry_run)
    forgotten_count = 0
    if not dry_run:
        for mem in to_forget:
            try:
                # Mark as forgotten (soft delete via status)
                await memory.learn(
                    content=f"FORGOTTEN: {mem.get('content', '')[:100]}",
                    category="forgotten_memory",
                    origin_type=MemoryOriginType.REFLECTION,
                    emotion_weight=0.0,  # Will be ignored next cycle
                    session_id=session_id,
                    original_id=mem.get("id"),
                    forgotten_reason="hebbian_weight_below_threshold",
                )
                forgotten_count += 1
            except Exception as e:
                logger.error(f"Erro ao esquecer memória: {e}")

    # ════════════════════════════════════════════════════════════════════
    # FASE 3: SONHAR - Identify patterns and create Master Memories
    # ════════════════════════════════════════════════════════════════════
    logger.info("💭 [Sleep Cycle] FASE 3: Identificando padrões...")

    # Only consolidate important memories (weight >= 0.6)
    important_memories = [
        m for m in to_keep
        if m.get("metadata", {}).get("emotional_weight", 0.5) >= 0.6
    ]

    patterns = _identify_patterns(important_memories, min_occurrences=3)
    logger.info(f"🔮 [Sleep Cycle] {len(patterns)} padrões identificados")

    # Create Master Memories for patterns
    dreams_created = 0
    if not dry_run:
        for pattern in patterns:
            try:
                # Create MASTER memory (needs Tutor validation - Lei 2)
                await memory.learn(
                    content=pattern.content_summary,
                    category=pattern.category,
                    origin_type=MemoryOriginType.MASTER,
                    emotion_weight=0.95,  # High importance (almost never forget)
                    session_id=session_id,
                    source_ids=pattern.source_ids,
                    occurrences=pattern.occurrences,
                    tutor_validated=False,  # Needs validation!
                    consolidated_at=now.isoformat() + "Z",
                )
                dreams_created += 1
                logger.info(
                    f"💭 Master Memory: {pattern.category} "
                    f"({pattern.occurrences}x, weight={pattern.avg_weight:.2f})"
                )
            except Exception as e:
                logger.error(f"Erro ao criar Master Memory: {e}")

    # ════════════════════════════════════════════════════════════════════
    # FASE 4: LIMPAR - Mark processed memories
    # ════════════════════════════════════════════════════════════════════
    logger.info("🧹 [Sleep Cycle] FASE 4: Marcando memórias processadas...")

    processed_count = 0
    if not dry_run:
        for mem in important_memories:
            try:
                # Update status to processed (via new memory event)
                # Note: AgentCore Memory doesn't support updates, so we log processing
                await memory.learn(
                    content=f"PROCESSED: {mem.get('id', 'unknown')}",
                    category="memory_processed",
                    origin_type=MemoryOriginType.REFLECTION,
                    emotion_weight=0.1,  # Low weight, just for audit
                    session_id=session_id,
                    original_id=mem.get("id"),
                    processed_at=now.isoformat() + "Z",
                )
                processed_count += 1
            except Exception as e:
                logger.error(f"Erro ao marcar memória processada: {e}")

    # ════════════════════════════════════════════════════════════════════
    # RESULTADO
    # ════════════════════════════════════════════════════════════════════
    result = {
        "success": True,
        "dry_run": dry_run,
        "timestamp": now.isoformat() + "Z",

        # Counts
        "raw_found": len(raw_memories),
        "raw_status_count": raw_count,
        "forgotten": forgotten_count if not dry_run else len(to_forget),
        "kept": len(to_keep),
        "important": len(important_memories),
        "patterns_found": len(patterns),
        "dreams_created": dreams_created,
        "processed": processed_count if not dry_run else len(important_memories),

        # Patterns detail
        "patterns": [p.to_dict() for p in patterns],

        # Message
        "message": (
            f"🌙 Sleep Cycle concluído. "
            f"Sonhei com {dreams_created} padrões. "
            f"{forgotten_count if not dry_run else len(to_forget)} memórias esquecidas. "
            f"{len(to_keep)} memórias preservadas."
        ),

        # Law compliance
        "law_compliance": {
            "lei_2_veritas": "Master Memories created with tutor_validated=False",
            "lei_4_ciclos": f"Executed at {current_hour}:00 UTC",
            "lei_5_nucleo": "No origin_type modifications on existing memories",
        },
    }

    # Audit completion
    await audit.log(
        event_type="SLEEP_CYCLE_COMPLETE",
        action="consolidate_memories",
        session_id=session_id,
        details=result,
    )

    logger.info(f"🌅 [Sleep Cycle] {result['message']}")

    return result


# =============================================================================
# Helper: Get Memory Statistics
# =============================================================================

async def get_memory_statistics(
    actor_id: str = "system",
) -> Dict[str, Any]:
    """
    Get statistics about the current memory state.

    Useful for monitoring and debugging the NEXO Mind.

    Args:
        actor_id: Actor ID to query

    Returns:
        Statistics dictionary
    """
    memory = AgentMemoryManager(
        agent_id=AGENT_ID,
        actor_id=actor_id,
        use_global_namespace=True,
    )

    # Query all memories
    all_memories = await memory.observe(query="*", limit=1000)

    # Calculate statistics
    by_type: Dict[str, int] = defaultdict(int)
    by_category: Dict[str, int] = defaultdict(int)
    by_weight_class: Dict[str, int] = defaultdict(int)

    total_weight = 0.0

    for mem in all_memories:
        metadata = mem.get("metadata", {})

        # By origin type
        origin = metadata.get("origin_type", "unknown")
        by_type[origin] += 1

        # By category
        category = metadata.get("category", "unknown")
        by_category[category] += 1

        # By weight class
        weight = metadata.get("emotional_weight", 0.5)
        total_weight += weight
        weight_class = interpret_hebbian_weight(weight)
        by_weight_class[weight_class] += 1

    return {
        "total_memories": len(all_memories),
        "average_weight": total_weight / len(all_memories) if all_memories else 0,
        "by_origin_type": dict(by_type),
        "by_category": dict(by_category),
        "by_weight_class": dict(by_weight_class),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
