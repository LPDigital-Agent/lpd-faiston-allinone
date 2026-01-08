# =============================================================================
# Learning Agent - Episodic Memory for Import Intelligence
# =============================================================================
# AI-First learning agent using AgentCore Episodic Memory.
# Stores successful import patterns and retrieves them for future imports.
#
# Memory Strategy: EPISODIC
# - Each import = 1 episode
# - Episodes contain: file type, column mappings, user corrections, success rate
# - Reflections are auto-generated across episodes for cross-session learning
#
# Module: Gestao de Ativos -> Gestao de Estoque -> Smart Import
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
import hashlib
import os

from agents.base_agent import BaseInventoryAgent
from agents.utils import (
    APP_NAME,
    MODEL_GEMINI,
    log_agent_action,
    now_iso,
    generate_id,
)


# =============================================================================
# Types
# =============================================================================


@dataclass
class ImportEpisode:
    """
    Represents a single import episode for memory storage.

    An episode captures all the relevant information from one complete
    import interaction, including the file structure, mappings learned,
    user corrections, and final success/failure status.
    """
    episode_id: str
    filename_pattern: str  # Normalized pattern (dates replaced with DATE, etc.)
    file_signature: str    # Hash of column structure for matching

    # File structure
    sheet_count: int
    total_rows: int
    sheets_info: List[Dict[str, Any]]  # [{name, purpose, column_count}]

    # Learned mappings
    column_mappings: Dict[str, str]  # {file_column: target_field}
    user_corrections: Dict[str, Any]  # Corrections made by user

    # Outcome
    success: bool
    match_rate: float  # 0.0 to 1.0
    items_processed: int
    items_failed: int

    # Metadata
    user_id: str
    created_at: str = field(default_factory=now_iso)
    lessons: List[str] = field(default_factory=list)  # Natural language lessons


@dataclass
class ImportReflection:
    """
    A cross-episode insight generated from multiple imports.

    Reflections are higher-level patterns that emerge from analyzing
    multiple episodes, such as "Files from supplier X always map EQUIPAMENTO
    to part_number" or "Multi-sheet files need user confirmation".
    """
    reflection_id: str
    pattern: str          # Natural language pattern description
    confidence: float     # 0.0 to 1.0
    episode_count: int    # Number of episodes supporting this reflection
    applicable_to: str    # File type, supplier, or general
    recommendation: str   # Action to take when pattern matches
    created_at: str = field(default_factory=now_iso)


# =============================================================================
# Agent Instruction
# =============================================================================


LEARNING_INSTRUCTION = """Você é um agente de aprendizado contínuo para o sistema SGA (Sistema de Gestão de Ativos).

## Seu Papel

Você gerencia a memória episódica de importações, permitindo que o sistema aprenda
com cada interação e melhore ao longo do tempo.

## Responsabilidades

1. **Armazenar Episódios**: Após cada importação, registre o episódio com todos os
   detalhes relevantes (estrutura do arquivo, mapeamentos, correções, resultado).

2. **Recuperar Conhecimento Prévio**: Antes de novas importações, busque episódios
   similares para sugerir mapeamentos com base em experiências passadas.

3. **Gerar Reflexões**: Analise padrões across múltiplos episódios para identificar
   insights de alto nível (ex: "Arquivos da planilha X sempre têm EQUIPAMENTO como PN").

4. **Adaptar Confiança**: Ajuste thresholds de confiança com base no histórico de
   sucesso/falha para diferentes tipos de arquivo.

## Formato de Resposta

Sempre responda em JSON estruturado.

## Linguagem

Português brasileiro (pt-BR) para todas as mensagens e padrões.
"""


# =============================================================================
# Learning Agent
# =============================================================================


class LearningAgent(BaseInventoryAgent):
    """
    Episodic memory agent for continuous learning from imports.

    This agent manages the knowledge base of successful imports,
    enabling the system to:
    1. Remember column mappings from past imports
    2. Recognize file patterns and auto-apply learned configurations
    3. Adapt confidence thresholds based on historical success
    4. Generate cross-session reflections

    Memory Strategy: Episodic
    - Episodes are stored per user (actor) for personalization
    - Strategy-level reflections span all users for shared learning

    Attributes:
        memory_enabled: Whether AgentCore Memory is available
        episodes_cache: In-memory cache for cold start optimization
    """

    # Memory configuration
    MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "faiston-sga-import-memory")
    MEMORY_NAMESPACE_BASE = "/strategy/import"

    def __init__(self):
        """Initialize the Learning Agent."""
        super().__init__(
            name="LearningAgent",
            instruction=LEARNING_INSTRUCTION,
            description="Agente de aprendizado contínuo com memória episódica",
        )
        self._memory_client = None
        self._memory_enabled = False
        self._episodes_cache: Dict[str, List[ImportEpisode]] = {}
        self._reflections_cache: List[ImportReflection] = []

        # Initialize memory client if available
        self._init_memory()

    def _init_memory(self):
        """
        Initialize AgentCore Memory client.

        Memory is optional - if not available, falls back to in-memory cache.
        This ensures the agent works during development without full AgentCore.
        """
        try:
            # Check if we have memory configuration
            if not self.MEMORY_ID or self.MEMORY_ID == "faiston-sga-import-memory":
                log_agent_action(
                    self.name, "init_memory",
                    status="skipped",
                    details={"reason": "No AGENTCORE_MEMORY_ID configured"},
                )
                return

            # Try to import and initialize memory client
            # Note: This import may not be available in all environments
            from bedrock_agentcore.memory import MemoryClient, MemoryMode

            self._memory_client = MemoryClient(
                memory_id=self.MEMORY_ID,
                # strategy="episodic",  # Set via AgentCore console
            )
            self._memory_enabled = True

            log_agent_action(
                self.name, "init_memory",
                status="completed",
                details={"memory_id": self.MEMORY_ID},
            )

        except ImportError:
            log_agent_action(
                self.name, "init_memory",
                status="skipped",
                details={"reason": "bedrock_agentcore.memory not available"},
            )
        except Exception as e:
            log_agent_action(
                self.name, "init_memory",
                status="failed",
                details={"error": str(e)},
            )

    # =========================================================================
    # Episode Storage (LEARN Phase)
    # =========================================================================

    async def create_episode(
        self,
        user_id: str,
        filename: str,
        file_analysis: Dict[str, Any],
        column_mappings: Dict[str, str],
        user_corrections: Dict[str, Any],
        import_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create and store an import episode in memory.

        Called after successful import to capture learned patterns.

        Args:
            user_id: User who performed the import
            filename: Original filename
            file_analysis: Analysis from sheet_analyzer
            column_mappings: Final column mappings used
            user_corrections: Any corrections made by user
            import_result: Result of the import execution

        Returns:
            Episode creation result
        """
        log_agent_action(
            self.name, "create_episode",
            entity_type="episode",
            status="started",
        )

        # Build episode
        episode = ImportEpisode(
            episode_id=generate_id("EP"),
            filename_pattern=self._extract_filename_pattern(filename),
            file_signature=self._compute_file_signature(file_analysis),
            sheet_count=file_analysis.get("sheet_count", 1),
            total_rows=file_analysis.get("total_rows", 0),
            sheets_info=[
                {
                    "name": s.get("name"),
                    # Support both field names: 'purpose' (new) and 'detected_purpose' (legacy)
                    "purpose": s.get("purpose", s.get("detected_purpose")),
                    "column_count": s.get("column_count"),
                }
                for s in file_analysis.get("sheets", [])
            ],
            column_mappings=column_mappings,
            user_corrections=user_corrections,
            success=import_result.get("success", False),
            match_rate=import_result.get("match_rate", 0.0),
            items_processed=import_result.get("items_processed", 0),
            items_failed=import_result.get("items_failed", 0),
            user_id=user_id,
            lessons=self._extract_lessons(column_mappings, user_corrections),
        )

        # Store in memory
        if self._memory_enabled and self._memory_client:
            try:
                await self._store_episode_in_memory(user_id, episode)
            except Exception as e:
                log_agent_action(
                    self.name, "create_episode",
                    entity_type="episode",
                    entity_id=episode.episode_id,
                    status="memory_failed",
                    details={"error": str(e)},
                )

        # Always store in cache for session
        if user_id not in self._episodes_cache:
            self._episodes_cache[user_id] = []
        self._episodes_cache[user_id].append(episode)

        # Keep only last 50 episodes per user in cache
        if len(self._episodes_cache[user_id]) > 50:
            self._episodes_cache[user_id] = self._episodes_cache[user_id][-50:]

        log_agent_action(
            self.name, "create_episode",
            entity_type="episode",
            entity_id=episode.episode_id,
            status="completed",
        )

        return {
            "success": True,
            "episode_id": episode.episode_id,
            "lessons_count": len(episode.lessons),
            "memory_stored": self._memory_enabled,
        }

    async def _store_episode_in_memory(
        self,
        user_id: str,
        episode: ImportEpisode,
    ):
        """Store episode in AgentCore Memory."""
        if not self._memory_client:
            return

        namespace = f"{self.MEMORY_NAMESPACE_BASE}/actor/{user_id}"

        # Create event with episode data
        # AgentCore will automatically:
        # - Extract key information
        # - Consolidate into memory record
        # - Generate reflections (if episodic strategy)
        await self._memory_client.create_event(
            event_type="import_completed",
            data={
                "episode_id": episode.episode_id,
                "filename_pattern": episode.filename_pattern,
                "file_signature": episode.file_signature,
                "sheet_count": episode.sheet_count,
                "column_mappings": episode.column_mappings,
                "user_corrections": episode.user_corrections,
                "success": episode.success,
                "match_rate": episode.match_rate,
                "lessons": episode.lessons,
            },
            namespace=namespace,
            role="TOOL",  # Include in episodic memory processing
        )

    # =========================================================================
    # Episode Retrieval (OBSERVE Phase - Prior Knowledge)
    # =========================================================================

    async def retrieve_prior_knowledge(
        self,
        user_id: str,
        filename: str,
        file_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Retrieve prior knowledge relevant to current import.

        Called before analysis to find similar past imports
        and pre-populate suggested mappings.

        Args:
            user_id: User performing the import
            filename: Current filename
            file_analysis: Current file analysis

        Returns:
            Prior knowledge with suggested mappings and confidence
        """
        log_agent_action(
            self.name, "retrieve_prior_knowledge",
            status="started",
        )

        # Compute signatures for matching
        filename_pattern = self._extract_filename_pattern(filename)
        file_signature = self._compute_file_signature(file_analysis)

        # Search for similar episodes
        similar_episodes = []

        # First, check in-memory cache
        if user_id in self._episodes_cache:
            for episode in self._episodes_cache[user_id]:
                similarity = self._compute_similarity(
                    episode,
                    filename_pattern,
                    file_signature,
                )
                if similarity > 0.5:  # Threshold for relevance
                    similar_episodes.append((episode, similarity))

        # Then, query AgentCore Memory if available
        if self._memory_enabled and self._memory_client:
            try:
                memory_episodes = await self._query_memory_episodes(
                    user_id,
                    filename_pattern,
                    file_signature,
                )
                for ep_data, similarity in memory_episodes:
                    similar_episodes.append((ep_data, similarity))
            except Exception as e:
                log_agent_action(
                    self.name, "retrieve_prior_knowledge",
                    status="memory_query_failed",
                    details={"error": str(e)},
                )

        # Sort by similarity and take top 5
        similar_episodes.sort(key=lambda x: x[1], reverse=True)
        top_episodes = similar_episodes[:5]

        if not top_episodes:
            log_agent_action(
                self.name, "retrieve_prior_knowledge",
                status="completed",
                details={"similar_episodes": 0},
            )
            return {
                "has_prior_knowledge": False,
                "similar_episodes": [],
                "suggested_mappings": {},
                "confidence_boost": 0.0,
            }

        # Aggregate mappings from similar episodes
        suggested_mappings = self._aggregate_mappings(top_episodes)

        # Calculate confidence boost based on historical success
        confidence_boost = self._calculate_confidence_boost(top_episodes)

        # Get reflections if available
        reflections = await self._get_relevant_reflections(filename_pattern)

        log_agent_action(
            self.name, "retrieve_prior_knowledge",
            status="completed",
            details={
                "similar_episodes": len(top_episodes),
                "suggested_mappings": len(suggested_mappings),
                "confidence_boost": confidence_boost,
            },
        )

        return {
            "has_prior_knowledge": True,
            "similar_episodes": [
                {
                    "episode_id": ep.episode_id if hasattr(ep, 'episode_id') else ep.get("episode_id"),
                    "filename_pattern": ep.filename_pattern if hasattr(ep, 'filename_pattern') else ep.get("filename_pattern"),
                    "similarity": sim,
                    "success": ep.success if hasattr(ep, 'success') else ep.get("success"),
                    "match_rate": ep.match_rate if hasattr(ep, 'match_rate') else ep.get("match_rate"),
                }
                for ep, sim in top_episodes
            ],
            "suggested_mappings": suggested_mappings,
            "confidence_boost": confidence_boost,
            "reflections": reflections,
        }

    async def _query_memory_episodes(
        self,
        user_id: str,
        filename_pattern: str,
        file_signature: str,
    ) -> List[tuple]:
        """Query AgentCore Memory for similar episodes."""
        if not self._memory_client:
            return []

        namespace = f"{self.MEMORY_NAMESPACE_BASE}/actor/{user_id}"

        # Query by intent (filename pattern or structure)
        results = await self._memory_client.query(
            query=f"import file similar to {filename_pattern} with structure {file_signature[:16]}",
            namespace=namespace,
            top_k=10,
        )

        # Convert results to episode format with similarity
        episodes = []
        for result in results:
            if hasattr(result, 'data'):
                data = result.data
                similarity = result.score if hasattr(result, 'score') else 0.7
                episodes.append((data, similarity))

        return episodes

    async def _get_relevant_reflections(
        self,
        filename_pattern: str,
    ) -> List[Dict[str, Any]]:
        """Get reflections relevant to current file pattern."""
        reflections = []

        # Check cache first
        for ref in self._reflections_cache:
            if ref.applicable_to in filename_pattern or ref.applicable_to == "general":
                reflections.append({
                    "pattern": ref.pattern,
                    "confidence": ref.confidence,
                    "recommendation": ref.recommendation,
                })

        # Query AgentCore Memory for strategy-level reflections
        if self._memory_enabled and self._memory_client:
            try:
                memory_reflections = await self._memory_client.get_reflections(
                    namespace=self.MEMORY_NAMESPACE_BASE,
                    query=filename_pattern,
                )
                for ref in memory_reflections:
                    reflections.append({
                        "pattern": ref.text if hasattr(ref, 'text') else str(ref),
                        "confidence": ref.confidence if hasattr(ref, 'confidence') else 0.7,
                        "recommendation": ref.recommendation if hasattr(ref, 'recommendation') else "",
                    })
            except Exception:
                pass  # Reflections are optional

        return reflections[:5]  # Return top 5

    # =========================================================================
    # Adaptive Confidence (TRUE Agentic Learning)
    # =========================================================================

    async def get_adaptive_threshold(
        self,
        user_id: str,
        filename: str,
        file_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate adaptive confidence threshold based on historical success.

        This implements TRUE agentic learning through reinforcement:
        - Track success/failure patterns per user and file type
        - Adjust threshold based on historical outcomes
        - Learn from user corrections to become more cautious when needed
        - Lower threshold for proven patterns (trust AI more)

        Philosophy: Continuous improvement through outcome-based adaptation

        Args:
            user_id: User performing the import
            filename: Current filename
            file_analysis: Current file analysis

        Returns:
            Dict with threshold and reasoning:
            {
                "threshold": float,
                "reasoning": str,
                "episode_count": int,
                "success_rate": float,
                "recent_corrections": int,
            }
        """
        base_threshold = 0.75

        # Compute signatures for matching
        filename_pattern = self._extract_filename_pattern(filename)
        file_signature = self._compute_file_signature(file_analysis)

        # Query historical episodes for this user
        matching_episodes = []
        similar_episodes = []

        if user_id in self._episodes_cache:
            for episode in self._episodes_cache[user_id]:
                # Exact signature match
                if episode.file_signature == file_signature:
                    matching_episodes.append(episode)
                # Similar filename pattern
                elif episode.filename_pattern == filename_pattern:
                    similar_episodes.append(episode)

        # No history - be cautious with new patterns
        if not matching_episodes and not similar_episodes:
            return {
                "threshold": 0.80,
                "reasoning": "Padrão novo - sendo cauteloso",
                "episode_count": 0,
                "success_rate": 0.0,
                "recent_corrections": 0,
            }

        # Combine matching and similar for analysis
        all_relevant = matching_episodes + similar_episodes[:5]

        if not all_relevant:
            return {
                "threshold": base_threshold,
                "reasoning": "Histórico insuficiente",
                "episode_count": 0,
                "success_rate": 0.0,
                "recent_corrections": 0,
            }

        # Calculate success rate
        successful = sum(1 for ep in all_relevant if ep.success)
        success_rate = successful / len(all_relevant) if all_relevant else 0

        # Check for RECENT user corrections (last 5 imports)
        # This is key for reinforcement learning: if user corrected AI recently,
        # the system should be MORE cautious
        recent_corrections = 0
        for ep in all_relevant[:5]:
            corrections = ep.user_corrections if hasattr(ep, 'user_corrections') else {}
            if corrections and len(corrections) > 0:
                recent_corrections += 1

        # Adaptive threshold logic (reinforcement learning principle)
        threshold = base_threshold
        reasoning = ""

        # Case 1: User corrected AI frequently in recent imports → MORE cautious
        if recent_corrections >= 2:
            threshold = 0.85
            reasoning = f"Usuário corrigiu IA em {recent_corrections}/5 imports recentes - sendo mais cauteloso"

        # Case 2: Proven pattern with 90%+ success and 10+ episodes → TRUST AI more
        elif success_rate >= 0.90 and len(all_relevant) >= 10:
            threshold = 0.65
            reasoning = f"Padrão comprovado: {len(all_relevant)} imports com {success_rate:.0%} sucesso - confiando mais na IA"

        # Case 3: Good track record (80%+) → slightly lower threshold
        elif success_rate >= 0.80 and len(all_relevant) >= 5:
            threshold = 0.70
            reasoning = f"Bom histórico: {success_rate:.0%} sucesso em {len(all_relevant)} imports"

        # Case 4: Mixed results (50-80%) → standard threshold
        elif success_rate >= 0.50:
            threshold = base_threshold
            reasoning = f"Histórico misto: {success_rate:.0%} sucesso - usando threshold padrão"

        # Case 5: Poor history (<50%) → MORE cautious
        else:
            threshold = 0.85
            reasoning = f"Histórico problemático: apenas {success_rate:.0%} sucesso - requerendo confirmação"

        return {
            "threshold": threshold,
            "reasoning": reasoning,
            "episode_count": len(all_relevant),
            "success_rate": success_rate,
            "recent_corrections": recent_corrections,
            "adaptive_threshold": threshold,  # Legacy compatibility
        }

    async def get_adaptive_threshold_simple(
        self,
        context: Dict[str, Any],
    ) -> float:
        """
        Simple threshold getter for backward compatibility.

        Args:
            context: Dict with filename_pattern, file_type, user_id

        Returns:
            Confidence threshold (float)
        """
        user_id = context.get("user_id", "anonymous")
        filename_pattern = context.get("filename_pattern", "")
        file_signature = context.get("file_signature", "")

        # Check historical success for this pattern
        matching_episodes = []

        if user_id in self._episodes_cache:
            for episode in self._episodes_cache[user_id]:
                if episode.file_signature == file_signature:
                    matching_episodes.append(episode)
                elif episode.filename_pattern == filename_pattern:
                    matching_episodes.append(episode)

        if not matching_episodes:
            return 0.75  # Default

        # Calculate success rate
        successful = sum(1 for ep in matching_episodes if ep.success)
        success_rate = successful / len(matching_episodes)

        # Check for recent corrections
        recent_corrections = sum(
            1 for ep in matching_episodes[:5]
            if hasattr(ep, 'user_corrections') and ep.user_corrections
        )

        if recent_corrections >= 2:
            return 0.85
        if success_rate >= 0.90 and len(matching_episodes) >= 10:
            return 0.65
        if success_rate >= 0.80:
            return 0.70
        if success_rate < 0.50:
            return 0.85

        return 0.75

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _extract_filename_pattern(self, filename: str) -> str:
        """Extract normalized pattern from filename."""
        import re

        # Remove date patterns (YYYY-MM-DD, DD-MM-YYYY, etc.)
        pattern = re.sub(r'\d{4}[-_]\d{2}[-_]\d{2}', 'DATE', filename)
        pattern = re.sub(r'\d{2}[-_]\d{2}[-_]\d{4}', 'DATE', pattern)

        # Remove sequential numbers
        pattern = re.sub(r'_\d+\.', '_N.', pattern)

        # Remove random IDs/hashes
        pattern = re.sub(r'[a-f0-9]{8,}', 'ID', pattern, flags=re.IGNORECASE)

        return pattern.lower()

    def _compute_file_signature(self, file_analysis: Dict[str, Any]) -> str:
        """Compute a signature based on file structure."""
        # Build signature from sheets and columns
        sig_parts = []

        for sheet in file_analysis.get("sheets", []):
            # Support both field names: 'purpose' (new) and 'detected_purpose' (legacy)
            sheet_sig = f"{sheet.get('purpose', sheet.get('detected_purpose', 'unknown'))}"
            columns = sheet.get("columns", [])

            # Add column names (sorted for consistency)
            col_names = sorted([c.get("name", "").lower() for c in columns[:20]])
            sheet_sig += ":" + ",".join(col_names[:10])
            sig_parts.append(sheet_sig)

        # Create hash
        sig_str = "|".join(sig_parts)
        return hashlib.md5(sig_str.encode()).hexdigest()[:16]

    def _compute_similarity(
        self,
        episode: ImportEpisode,
        filename_pattern: str,
        file_signature: str,
    ) -> float:
        """Compute similarity between episode and current file."""
        similarity = 0.0

        # Exact signature match = high similarity
        ep_sig = episode.file_signature if hasattr(episode, 'file_signature') else episode.get("file_signature", "")
        if ep_sig == file_signature:
            similarity += 0.6

        # Filename pattern match
        ep_pattern = episode.filename_pattern if hasattr(episode, 'filename_pattern') else episode.get("filename_pattern", "")
        if ep_pattern == filename_pattern:
            similarity += 0.3
        elif ep_pattern and filename_pattern and ep_pattern in filename_pattern:
            similarity += 0.15

        # Success bonus (prefer successful episodes)
        ep_success = episode.success if hasattr(episode, 'success') else episode.get("success", False)
        if ep_success:
            similarity += 0.1

        return min(similarity, 1.0)

    def _aggregate_mappings(
        self,
        episodes: List[tuple],
    ) -> Dict[str, Dict[str, Any]]:
        """Aggregate mappings from multiple episodes with voting."""
        mapping_votes = {}  # {column: {field: count}}

        for episode, similarity in episodes:
            mappings = episode.column_mappings if hasattr(episode, 'column_mappings') else episode.get("column_mappings", {})

            for column, field in mappings.items():
                if column not in mapping_votes:
                    mapping_votes[column] = {}
                if field not in mapping_votes[column]:
                    mapping_votes[column][field] = 0
                # Weight by similarity
                mapping_votes[column][field] += similarity

        # Select winning mapping for each column
        suggested = {}
        for column, votes in mapping_votes.items():
            if votes:
                winner = max(votes.items(), key=lambda x: x[1])
                total_votes = sum(votes.values())
                suggested[column] = {
                    "field": winner[0],
                    "confidence": winner[1] / total_votes if total_votes > 0 else 0,
                    "vote_count": len([e for e, _ in episodes]),
                }

        return suggested

    def _calculate_confidence_boost(
        self,
        episodes: List[tuple],
    ) -> float:
        """Calculate confidence boost from historical success."""
        if not episodes:
            return 0.0

        # Calculate weighted success rate
        total_weight = 0
        success_weight = 0

        for episode, similarity in episodes:
            ep_success = episode.success if hasattr(episode, 'success') else episode.get("success", False)
            ep_match_rate = episode.match_rate if hasattr(episode, 'match_rate') else episode.get("match_rate", 0)

            total_weight += similarity
            if ep_success:
                success_weight += similarity * ep_match_rate

        if total_weight == 0:
            return 0.0

        # Boost ranges from 0.0 to 0.15
        return min((success_weight / total_weight) * 0.15, 0.15)

    def _extract_lessons(
        self,
        column_mappings: Dict[str, str],
        user_corrections: Dict[str, Any],
    ) -> List[str]:
        """Extract natural language lessons from import."""
        lessons = []

        # Lesson from corrections
        for column, correction in user_corrections.items():
            if isinstance(correction, str):
                lessons.append(f"Coluna '{column}' deve mapear para '{correction}'")

        # Lesson from successful mappings
        for column, field in column_mappings.items():
            if field and column.lower() != field.lower():
                lessons.append(f"Coluna '{column}' corresponde ao campo '{field}'")

        return lessons[:10]  # Limit to 10 lessons


    # =========================================================================
    # Feedback Loop: Reflection Generation (TRUE Agentic Learning)
    # =========================================================================

    async def generate_reflection(
        self,
        user_id: str,
        filename_pattern: str,
        recent_outcomes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate cross-episode reflection for continuous improvement.

        This implements TRUE agentic learning: after multiple imports,
        the agent reflects on patterns and generates insights that
        improve future performance.

        Philosophy: LEARN phase - "What did I learn from this experience?"

        Args:
            user_id: User for whom to generate reflection
            filename_pattern: File pattern to focus reflection on
            recent_outcomes: Recent import outcomes (optional)

        Returns:
            Reflection with patterns, insights, and recommendations
        """
        log_agent_action(
            self.name, "generate_reflection",
            status="started",
        )

        # Get relevant episodes
        relevant_episodes = []
        if user_id in self._episodes_cache:
            for episode in self._episodes_cache[user_id]:
                if episode.filename_pattern == filename_pattern:
                    relevant_episodes.append(episode)

        if len(relevant_episodes) < 3:
            return {
                "has_reflection": False,
                "reason": "Não há episódios suficientes para reflexão (mínimo: 3)",
                "episode_count": len(relevant_episodes),
            }

        # Analyze patterns
        successful = [ep for ep in relevant_episodes if ep.success]
        failed = [ep for ep in relevant_episodes if not ep.success]
        success_rate = len(successful) / len(relevant_episodes)

        # Find common mappings in successful episodes
        common_mappings = {}
        for ep in successful:
            for col, field in ep.column_mappings.items():
                if col not in common_mappings:
                    common_mappings[col] = {}
                if field not in common_mappings[col]:
                    common_mappings[col][field] = 0
                common_mappings[col][field] += 1

        # Find best mappings (most frequent in successful imports)
        best_mappings = {}
        for col, votes in common_mappings.items():
            if votes:
                best_field = max(votes.items(), key=lambda x: x[1])
                if best_field[1] >= 2:  # At least 2 occurrences
                    best_mappings[col] = best_field[0]

        # Analyze user corrections
        all_corrections = {}
        for ep in relevant_episodes:
            corrections = ep.user_corrections if hasattr(ep, 'user_corrections') else {}
            for col, correction in corrections.items():
                if col not in all_corrections:
                    all_corrections[col] = []
                all_corrections[col].append(correction)

        # Frequent corrections = areas where AI needs improvement
        problem_areas = []
        for col, corrections in all_corrections.items():
            if len(corrections) >= 2:
                problem_areas.append({
                    "column": col,
                    "correction_count": len(corrections),
                    "common_correction": max(set(corrections), key=corrections.count),
                })

        # Generate natural language reflection using Gemini
        reflection_text = ""
        try:
            prompt = f"""Analise estes dados de imports e gere uma reflexão concisa:

## Estatísticas
- Total de imports: {len(relevant_episodes)}
- Taxa de sucesso: {success_rate:.0%}
- Padrão de arquivo: {filename_pattern}

## Mapeamentos que funcionaram bem
{json.dumps(best_mappings, ensure_ascii=False, indent=2)}

## Áreas problemáticas (correções frequentes)
{json.dumps(problem_areas, ensure_ascii=False, indent=2)}

## Tarefa
Gere uma reflexão em 2-3 frases sobre:
1. O que o sistema aprendeu com estes imports
2. O que pode ser melhorado
3. Uma recomendação para próximos imports similares

Responda em português brasileiro, de forma profissional mas acessível.
"""
            _, reflection_text = await self.invoke_with_thinking(prompt)
        except Exception as e:
            reflection_text = f"Reflexão automática indisponível: {str(e)[:50]}"

        # Build reflection result
        reflection = ImportReflection(
            reflection_id=generate_id("REF"),
            pattern=filename_pattern,
            confidence=success_rate,
            episode_count=len(relevant_episodes),
            applicable_to=filename_pattern,
            recommendation=reflection_text[:500] if reflection_text else "",
        )

        # Cache reflection
        self._reflections_cache.append(reflection)
        if len(self._reflections_cache) > 20:
            self._reflections_cache = self._reflections_cache[-20:]

        log_agent_action(
            self.name, "generate_reflection",
            entity_id=reflection.reflection_id,
            status="completed",
        )

        return {
            "has_reflection": True,
            "reflection_id": reflection.reflection_id,
            "pattern": filename_pattern,
            "episode_count": len(relevant_episodes),
            "success_rate": success_rate,
            "best_mappings": best_mappings,
            "problem_areas": problem_areas,
            "reflection_text": reflection_text,
            "recommendation": reflection.recommendation,
        }

    async def invoke_with_thinking(self, prompt: str) -> tuple:
        """
        Invoke base agent with thinking mode.

        Wrapper that calls parent's invoke_with_thinking if available,
        or falls back to regular invoke.

        Args:
            prompt: Prompt to send

        Returns:
            tuple[thinking_trace, response]
        """
        try:
            # Try thinking mode first
            if hasattr(super(), 'invoke_with_thinking'):
                return await super().invoke_with_thinking(prompt)
            else:
                # Fallback to regular invoke
                response = await self.invoke(prompt)
                return "", response
        except Exception as e:
            return "", f"Error: {str(e)}"


# =============================================================================
# Factory Function
# =============================================================================


def create_learning_agent() -> LearningAgent:
    """Create a new LearningAgent instance."""
    return LearningAgent()
