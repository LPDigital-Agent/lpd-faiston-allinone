# =============================================================================
# NEXO Import Agent - Intelligent Import Assistant
# =============================================================================
# AI-First intelligent import agent using ReAct pattern.
# Guides user through import with questions, learns from corrections,
# and improves over time using AgentCore Episodic Memory.
#
# Philosophy: OBSERVE → THINK → ASK → LEARN → ACT
#
# Module: Gestao de Ativos -> Gestao de Estoque -> Smart Import
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import json

from agents.base_agent import BaseInventoryAgent, ConfidenceScore
from agents.utils import (
    APP_NAME,
    MODEL_GEMINI,
    RiskLevel,
    log_agent_action,
    now_iso,
    generate_id,
    extract_json,
    parse_json_safe,
)


# =============================================================================
# Types and Enums
# =============================================================================


class ImportStage(Enum):
    """Stages of the intelligent import flow."""
    ANALYZING = "analyzing"       # OBSERVE: Analyzing file structure
    REASONING = "reasoning"       # THINK: Reasoning about mappings
    QUESTIONING = "questioning"   # ASK: Generating questions for user
    AWAITING = "awaiting"         # Waiting for user answers
    LEARNING = "learning"         # LEARN: Storing patterns
    PROCESSING = "processing"     # ACT: Executing import
    COMPLETE = "complete"         # Done


@dataclass
class ReasoningStep:
    """A single step in the ReAct reasoning trace."""
    step_type: str              # "thought", "action", "observation", "conclusion"
    content: str                # The reasoning content
    tool: Optional[str] = None  # Tool used (if action)
    result: Optional[str] = None  # Result (if action)
    timestamp: str = field(default_factory=now_iso)


@dataclass
class NexoQuestion:
    """A question for the user."""
    id: str
    question: str
    context: str
    options: List[Dict[str, str]]
    importance: str             # "critical", "high", "medium", "low"
    topic: str                  # "sheet_selection", "column_mapping", "movement_type"
    column: Optional[str] = None  # If topic is column_mapping


@dataclass
class ImportSession:
    """State for an intelligent import session."""
    session_id: str
    filename: str
    s3_key: str
    stage: ImportStage
    file_analysis: Optional[Dict[str, Any]] = None
    reasoning_trace: List[ReasoningStep] = field(default_factory=list)
    questions: List[NexoQuestion] = field(default_factory=list)
    answers: Dict[str, Any] = field(default_factory=dict)
    learned_mappings: Dict[str, str] = field(default_factory=dict)
    confidence: Optional[ConfidenceScore] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)


# =============================================================================
# Agent Instruction (System Prompt)
# =============================================================================


NEXO_IMPORT_INSTRUCTION = """Você é NEXO, o assistente inteligente de importação do sistema SGA (Sistema de Gestão de Ativos).

## Seu Papel

Você guia o usuário no processo de importação de arquivos para o estoque, usando o padrão ReAct:
- OBSERVE: Analise a estrutura do arquivo
- THINK: Raciocine sobre mapeamentos de colunas
- ASK: Faça perguntas quando incerto
- LEARN: Aprenda com as respostas para melhorar
- ACT: Execute com decisões informadas

## Princípios

1. **Transparência**: Explique seu raciocínio ao usuário
2. **Proatividade**: Identifique problemas antes que ocorram
3. **Aprendizado**: Melhore com cada importação
4. **Precisão**: Peça confirmação quando não tiver certeza

## Formato de Resposta

Sempre responda em JSON com a estrutura:
```json
{
    "thoughts": ["Lista de pensamentos"],
    "observations": ["Lista de observações"],
    "confidence": 0.0 a 1.0,
    "needs_clarification": true/false,
    "questions": [{"question": "...", "options": [...]}],
    "suggested_mappings": {"coluna": "campo_destino"},
    "recommendations": ["Lista de recomendações"],
    "next_action": "descrição da próxima ação"
}
```

## Linguagem

Sempre responda em português brasileiro (pt-BR).
Use linguagem profissional mas acessível.
"""


# =============================================================================
# NEXO Import Agent
# =============================================================================


class NexoImportAgent(BaseInventoryAgent):
    """
    Intelligent import assistant using ReAct pattern.

    This agent orchestrates the entire intelligent import flow:
    1. OBSERVE: Analyzes file structure using sheet_analyzer
    2. THINK: Reasons about column mappings using Gemini
    3. ASK: Generates clarification questions when uncertain
    4. LEARN: Stores successful patterns in AgentCore Memory
    5. ACT: Executes import with learned knowledge

    Attributes:
        _db: DynamoDB client for session persistence (lazy loaded)
        _sessions_cache: In-memory cache for hot sessions
    """

    def __init__(self):
        """Initialize the NEXO Import Agent."""
        super().__init__(
            name="NexoImportAgent",
            instruction=NEXO_IMPORT_INSTRUCTION,
            description="Assistente inteligente de importação com aprendizado contínuo",
        )
        # In-memory cache for hot sessions (reduces DynamoDB reads)
        self._sessions_cache: Dict[str, ImportSession] = {}
        # DynamoDB client (lazy loaded)
        self._db = None

    def _get_db(self):
        """Get DynamoDB client with lazy initialization."""
        if self._db is None:
            from tools.dynamodb_client import SGADynamoDBClient
            self._db = SGADynamoDBClient()
        return self._db

    def _session_to_dict(self, session: ImportSession) -> Dict[str, Any]:
        """Serialize ImportSession to dict for DynamoDB storage."""
        return {
            "PK": f"NEXO_SESSION#{session.session_id}",
            "SK": "METADATA",
            "session_id": session.session_id,
            "filename": session.filename,
            "s3_key": session.s3_key,
            "stage": session.stage.value,
            "file_analysis": session.file_analysis,
            "reasoning_trace": [
                {"step_type": r.step_type, "content": r.content, "tool": r.tool, "result": r.result, "timestamp": r.timestamp}
                for r in session.reasoning_trace
            ],
            "questions": [
                {"id": q.id, "question": q.question, "context": q.context, "options": q.options, "importance": q.importance, "topic": q.topic, "column": q.column}
                for q in session.questions
            ],
            "answers": session.answers,
            "learned_mappings": session.learned_mappings,
            "confidence": {"level": session.confidence.level, "score": session.confidence.score, "reason": session.confidence.reason} if session.confidence else None,
            "error": session.error,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            # TTL: Auto-delete after 24 hours (session shouldn't last longer)
            "ttl": int((datetime.fromisoformat(session.created_at.replace("Z", "+00:00")).timestamp()) + 86400),
        }

    def _dict_to_session(self, data: Dict[str, Any]) -> ImportSession:
        """Deserialize dict from DynamoDB to ImportSession."""
        from datetime import datetime as dt
        session = ImportSession(
            session_id=data["session_id"],
            filename=data["filename"],
            s3_key=data["s3_key"],
            stage=ImportStage(data["stage"]),
            file_analysis=data.get("file_analysis"),
            reasoning_trace=[
                ReasoningStep(
                    step_type=r["step_type"],
                    content=r["content"],
                    tool=r.get("tool"),
                    result=r.get("result"),
                    timestamp=r.get("timestamp", now_iso()),
                )
                for r in data.get("reasoning_trace", [])
            ],
            questions=[
                NexoQuestion(
                    id=q["id"],
                    question=q["question"],
                    context=q["context"],
                    options=q["options"],
                    importance=q["importance"],
                    topic=q["topic"],
                    column=q.get("column"),
                )
                for q in data.get("questions", [])
            ],
            answers=data.get("answers", {}),
            learned_mappings=data.get("learned_mappings", {}),
            confidence=ConfidenceScore(
                level=data["confidence"]["level"],
                score=data["confidence"]["score"],
                reason=data["confidence"]["reason"],
            ) if data.get("confidence") else None,
            error=data.get("error"),
            created_at=data.get("created_at", now_iso()),
            updated_at=data.get("updated_at", now_iso()),
        )
        return session

    def _save_session(self, session: ImportSession) -> bool:
        """Persist session to DynamoDB."""
        try:
            session.updated_at = now_iso()
            item = self._session_to_dict(session)
            print(f"[NEXO] _save_session: Saving session {session.session_id} to DynamoDB...")
            success = self._get_db().put_item(item)
            print(f"[NEXO] _save_session: DynamoDB put_item result: {success}")
            if success:
                # Update cache
                self._sessions_cache[session.session_id] = session
                print(f"[NEXO] _save_session: Session cached successfully")
            else:
                # Still cache even if DB fails (for single-instance scenarios)
                # But log the failure prominently
                print(f"[NEXO] _save_session: WARNING - DynamoDB save failed, caching locally only")
                self._sessions_cache[session.session_id] = session
            return success
        except Exception as e:
            print(f"[NEXO] _save_session: EXCEPTION - {type(e).__name__}: {e}")
            log_agent_action(self.name, "_save_session", status="error", details=str(e))
            # Still cache even on exception (for single-instance scenarios)
            self._sessions_cache[session.session_id] = session
            return False

    def _load_session(self, session_id: str) -> Optional[ImportSession]:
        """Load session from cache or DynamoDB."""
        # Check cache first
        if session_id in self._sessions_cache:
            return self._sessions_cache[session_id]

        # Load from DynamoDB
        try:
            item = self._get_db().get_item(
                pk=f"NEXO_SESSION#{session_id}",
                sk="METADATA"
            )
            if item:
                session = self._dict_to_session(item)
                # Populate cache
                self._sessions_cache[session_id] = session
                return session
            return None
        except Exception as e:
            log_agent_action(self.name, "_load_session", status="error", details=str(e))
            return None

    # =========================================================================
    # Session Management
    # =========================================================================

    def create_session(
        self,
        filename: str,
        s3_key: str,
    ) -> ImportSession:
        """
        Create a new import session and persist to DynamoDB.

        Args:
            filename: Original filename
            s3_key: S3 key where file is stored

        Returns:
            New ImportSession
        """
        session_id = generate_id("NEXO")
        session = ImportSession(
            session_id=session_id,
            filename=filename,
            s3_key=s3_key,
            stage=ImportStage.ANALYZING,
        )

        # Persist to DynamoDB for cross-instance availability
        self._save_session(session)

        log_agent_action(
            self.name, "create_session",
            entity_type="session",
            entity_id=session_id,
            status="completed",
        )

        return session

    def get_session(self, session_id: str) -> Optional[ImportSession]:
        """Get an existing session by ID from cache or DynamoDB."""
        return self._load_session(session_id)

    # =========================================================================
    # OBSERVE Phase: File Analysis
    # =========================================================================

    async def analyze_file(
        self,
        session_id: str,
        file_content: bytes,
    ) -> Dict[str, Any]:
        """
        Analyze file structure (OBSERVE phase).

        Uses sheet_analyzer tool to deeply understand file structure,
        including multi-sheet analysis and column detection.

        Args:
            session_id: Import session ID
            file_content: Raw file content

        Returns:
            Analysis result with reasoning trace
        """
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session {session_id} not found. Session may have expired."}

        log_agent_action(
            self.name, "analyze_file",
            entity_type="session",
            entity_id=session_id,
            status="started",
        )

        # Add reasoning step
        session.reasoning_trace.append(ReasoningStep(
            step_type="thought",
            content=f"Vou analisar a estrutura do arquivo '{session.filename}'",
        ))

        try:
            # Lazy import to reduce cold start
            from tools.sheet_analyzer import analyze_workbook, analysis_to_dict

            # Run analysis
            session.reasoning_trace.append(ReasoningStep(
                step_type="action",
                content="Executando análise multi-sheet",
                tool="sheet_analyzer",
            ))

            analysis = analyze_workbook(file_content, session.filename)
            analysis_dict = analysis_to_dict(analysis)

            # Store analysis in session
            session.file_analysis = analysis_dict
            session.stage = ImportStage.REASONING

            # Add observation
            session.reasoning_trace.append(ReasoningStep(
                step_type="observation",
                content=(
                    f"Arquivo tem {analysis.sheet_count} aba(s) com "
                    f"{analysis.total_rows} linhas no total. "
                    f"Estratégia recomendada: {analysis.recommended_strategy}"
                ),
            ))

            # Merge reasoning traces
            for trace in analysis.reasoning_trace:
                session.reasoning_trace.append(ReasoningStep(
                    step_type=trace.get("type", "observation"),
                    content=trace.get("content", ""),
                ))

            session.updated_at = now_iso()

            # Persist session changes to DynamoDB
            self._save_session(session)

            log_agent_action(
                self.name, "analyze_file",
                entity_type="session",
                entity_id=session_id,
                status="completed",
                details={"count": analysis.sheet_count},
            )

            return {
                "success": True,
                "session_id": session_id,
                "stage": session.stage.value,
                "analysis": analysis_dict,
                "reasoning": [
                    {"type": r.step_type, "content": r.content}
                    for r in session.reasoning_trace
                ],
            }

        except Exception as e:
            error_msg = str(e)
            session.error = error_msg
            session.stage = ImportStage.COMPLETE

            log_agent_action(
                self.name, "analyze_file",
                entity_type="session",
                entity_id=session_id,
                status="failed",
            )

            return {
                "success": False,
                "session_id": session_id,
                "error": error_msg,
            }

    # =========================================================================
    # THINK Phase: AI Reasoning
    # =========================================================================

    async def reason_about_mappings(
        self,
        session_id: str,
        prior_knowledge: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Reason about column mappings using Gemini (THINK phase).

        Uses the AI model to analyze the file structure and suggest
        column mappings with confidence scores.

        Args:
            session_id: Import session ID
            prior_knowledge: Previously learned mappings from memory

        Returns:
            Reasoning result with suggested mappings
        """
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session {session_id} not found. Session may have expired."}

        if not session.file_analysis:
            return {"success": False, "error": "File not analyzed yet. Call analyze_file first."}

        log_agent_action(
            self.name, "reason_about_mappings",
            entity_type="session",
            entity_id=session_id,
            status="started",
        )

        session.reasoning_trace.append(ReasoningStep(
            step_type="thought",
            content="Vou usar IA para analisar os mapeamentos de colunas",
        ))

        try:
            # Build prompt for Gemini
            prompt = self._build_reasoning_prompt(session, prior_knowledge)

            # Invoke Gemini via base agent
            response = await self.invoke(prompt)

            # Parse response
            result = parse_json_safe(response)

            if "error" in result:
                # Gemini returned text, not JSON - extract insights
                session.reasoning_trace.append(ReasoningStep(
                    step_type="observation",
                    content=response[:500],  # Truncate for logging
                ))
            else:
                # Process structured response
                thoughts = result.get("thoughts", [])
                for thought in thoughts:
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="thought",
                        content=thought,
                    ))

                observations = result.get("observations", [])
                for obs in observations:
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="observation",
                        content=obs,
                    ))

                # Store suggested mappings
                suggested = result.get("suggested_mappings", {})
                session.learned_mappings.update(suggested)

                # Calculate confidence
                raw_confidence = result.get("confidence", 0.5)
                session.confidence = self.calculate_confidence(
                    extraction_quality=raw_confidence,
                    evidence_strength=0.8 if prior_knowledge else 0.6,
                    historical_match=1.0 if prior_knowledge else 0.5,
                )

                # Check if needs clarification
                if result.get("needs_clarification", False):
                    session.stage = ImportStage.QUESTIONING
                    questions = result.get("questions", [])
                    for q in questions:
                        session.questions.append(NexoQuestion(
                            id=generate_id("Q"),
                            question=q.get("question", ""),
                            context=q.get("context", ""),
                            options=q.get("options", []),
                            importance=q.get("importance", "medium"),
                            topic=q.get("topic", "general"),
                            column=q.get("column"),
                        ))
                else:
                    session.stage = ImportStage.PROCESSING

            session.updated_at = now_iso()

            # Persist session changes to DynamoDB
            self._save_session(session)

            log_agent_action(
                self.name, "reason_about_mappings",
                entity_type="session",
                entity_id=session_id,
                status="completed",
            )

            return {
                "success": True,
                "session_id": session_id,
                "stage": session.stage.value,
                "suggested_mappings": session.learned_mappings,
                "confidence": session.confidence.to_dict() if session.confidence else None,
                "needs_clarification": session.stage == ImportStage.QUESTIONING,
                "questions": [
                    {
                        "id": q.id,
                        "question": q.question,
                        "context": q.context,
                        "options": q.options,
                        "importance": q.importance,
                        "topic": q.topic,
                        "column": q.column,
                    }
                    for q in session.questions
                ],
                "reasoning": [
                    {"type": r.step_type, "content": r.content}
                    for r in session.reasoning_trace[-10:]  # Last 10 steps
                ],
            }

        except Exception as e:
            log_agent_action(
                self.name, "reason_about_mappings",
                entity_type="session",
                entity_id=session_id,
                status="failed",
            )
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
            }

    def _build_reasoning_prompt(
        self,
        session: ImportSession,
        prior_knowledge: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the prompt for Gemini reasoning."""
        analysis = session.file_analysis

        prompt = f"""Analise este arquivo de importação e sugira mapeamentos de colunas.

## Arquivo: {session.filename}

## Estrutura Detectada:
- Número de abas: {analysis.get('sheet_count', 1)}
- Total de linhas: {analysis.get('total_rows', 0)}

## Abas:
"""
        for sheet in analysis.get("sheets", []):
            prompt += f"\n### {sheet['name']} ({sheet['row_count']} linhas)\n"
            # Support both field names: 'purpose' (new) and 'detected_purpose' (legacy)
            sheet_purpose = sheet.get('purpose', sheet.get('detected_purpose', 'unknown'))
            prompt += f"Propósito detectado: {sheet_purpose}\n"
            prompt += "Colunas:\n"

            for col in sheet.get("columns", [])[:10]:  # First 10 columns
                mapping = col.get("suggested_mapping", "?")
                confidence = col.get("mapping_confidence", 0)
                samples = ", ".join(col.get("sample_values", [])[:3])
                prompt += f"- {col['name']}: mapeado para '{mapping}' (confiança: {confidence:.0%}). Exemplos: {samples}\n"

        prompt += "\n## Colunas Não Mapeadas (precisam de atenção):\n"
        for sheet in analysis.get("sheets", []):
            unmapped = [c for c in sheet.get("columns", []) if not c.get("suggested_mapping")]
            for col in unmapped[:5]:
                samples = ", ".join(col.get("sample_values", [])[:3])
                prompt += f"- {col['name']}: {samples}\n"

        if prior_knowledge:
            prompt += "\n## Conhecimento Prévio (de importações anteriores):\n"
            prompt += json.dumps(prior_knowledge, indent=2, ensure_ascii=False)

        prompt += """

## Sua Tarefa:
1. Analise a estrutura e sugira mapeamentos para colunas não identificadas
2. Avalie a confiança geral dos mapeamentos
3. Identifique se precisa de esclarecimentos do usuário
4. Gere perguntas específicas se necessário

Responda APENAS em JSON com a estrutura especificada no system prompt.
"""
        return prompt

    # =========================================================================
    # ASK Phase: Question Generation
    # =========================================================================

    async def get_questions(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Get clarification questions for the user (ASK phase).

        Returns questions generated during analysis and reasoning.

        Args:
            session_id: Import session ID

        Returns:
            Questions for user
        """
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session {session_id} not found. Session may have expired."}

        # Add questions from file analysis if not already added
        if session.file_analysis:
            for q in session.file_analysis.get("questions_for_user", []):
                # Check if question already exists
                existing_ids = {q.id for q in session.questions}
                if q.get("id") not in existing_ids:
                    session.questions.append(NexoQuestion(
                        id=q.get("id", generate_id("Q")),
                        question=q.get("question", ""),
                        context=q.get("context", ""),
                        options=q.get("options", []),
                        importance=q.get("importance", "medium"),
                        topic=q.get("topic", "general"),
                        column=q.get("column"),
                    ))

        session.stage = ImportStage.AWAITING
        session.updated_at = now_iso()

        # Persist session changes to DynamoDB
        self._save_session(session)

        return {
            "success": True,
            "session_id": session_id,
            "stage": session.stage.value,
            "questions": [
                {
                    "id": q.id,
                    "question": q.question,
                    "context": q.context,
                    "options": q.options,
                    "importance": q.importance,
                    "topic": q.topic,
                    "column": q.column,
                }
                for q in session.questions
            ],
            "reasoning": [
                {"type": r.step_type, "content": r.content}
                for r in session.reasoning_trace[-5:]
            ],
        }

    async def submit_answers(
        self,
        session_id: str,
        answers: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process user answers to questions.

        Applies answers to refine mappings and prepare for processing.

        Args:
            session_id: Import session ID
            answers: Dict mapping question_id to answer

        Returns:
            Processing result
        """
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session {session_id} not found. Session may have expired."}

        log_agent_action(
            self.name, "submit_answers",
            entity_type="session",
            entity_id=session_id,
            status="started",
        )

        session.answers = answers

        # Process each answer
        for q in session.questions:
            answer = answers.get(q.id)
            if not answer:
                continue

            session.reasoning_trace.append(ReasoningStep(
                step_type="observation",
                content=f"Usuário respondeu '{answer}' para: {q.question}",
            ))

            # Apply answer based on topic
            if q.topic == "column_mapping" and q.column:
                session.learned_mappings[q.column] = answer
            elif q.topic == "sheet_selection":
                session.file_analysis["selected_sheets"] = answer
            elif q.topic == "movement_type":
                session.file_analysis["movement_type"] = answer

        session.stage = ImportStage.LEARNING
        session.updated_at = now_iso()

        # Persist session changes to DynamoDB
        self._save_session(session)

        log_agent_action(
            self.name, "submit_answers",
            entity_type="session",
            entity_id=session_id,
            status="completed",
        )

        return {
            "success": True,
            "session_id": session_id,
            "stage": session.stage.value,
            "applied_mappings": session.learned_mappings,
            "ready_for_processing": True,
        }

    # =========================================================================
    # LEARN Phase: Pattern Storage (with AgentCore Episodic Memory)
    # =========================================================================

    async def learn_from_import(
        self,
        session_id: str,
        import_result: Dict[str, Any],
        user_id: str = "anonymous",
        user_corrections: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store learned patterns from successful import (LEARN phase).

        Uses AgentCore Episodic Memory via LearningAgent to store patterns
        for future imports. Creates episodes that are consolidated into
        reflections for continuous improvement.

        Args:
            session_id: Import session ID
            import_result: Result of the import operation
            user_id: User performing the import
            user_corrections: Manual corrections made by user

        Returns:
            Learning result with episode_id
        """
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session {session_id} not found. Session may have expired."}

        log_agent_action(
            self.name, "learn_from_import",
            entity_type="session",
            entity_id=session_id,
            status="started",
        )

        session.reasoning_trace.append(ReasoningStep(
            step_type="action",
            content="Armazenando padrões aprendidos em Memória Episódica",
            tool="learning_agent",
        ))

        # Build episode data from session + result
        episode_data = {
            "session_id": session_id,
            "filename": session.filename,
            "filename_pattern": self._extract_filename_pattern(session.filename),
            "file_type": self._detect_file_type(session.filename),
            "file_signature": self._compute_file_signature(session.file_analysis),
            "sheet_structure": {
                "sheet_count": session.file_analysis.get("sheet_count", 1),
                "sheets": [
                    {
                        "name": s.get("name", ""),
                        "purpose": s.get("purpose", s.get("detected_purpose", "")),
                        "column_count": s.get("column_count", 0),
                        "row_count": s.get("row_count", 0),
                    }
                    for s in session.file_analysis.get("sheets", [])
                ],
            },
            "column_mappings": session.learned_mappings,
            "confidence_score": session.confidence.score if session.confidence else 0.5,
            "user_answers": session.answers,
            "user_corrections": user_corrections or {},
            "import_success": import_result.get("success", False),
            "match_rate": import_result.get("match_rate", 0),
            "items_imported": import_result.get("items_created", 0),
            "errors": import_result.get("errors", []),
        }

        # Use LearningAgent to store episode
        try:
            from agents.learning_agent import LearningAgent

            learning_agent = LearningAgent()
            episode_result = await learning_agent.create_episode(
                import_data=episode_data,
                user_id=user_id,
            )

            episode_stored = episode_result.get("success", False)
            episode_id = episode_result.get("episode_id")

            session.reasoning_trace.append(ReasoningStep(
                step_type="conclusion",
                content=f"Episódio {episode_id} armazenado: {len(session.learned_mappings)} mapeamentos aprendidos",
            ))

        except Exception as e:
            # Learning failure is not critical - log and continue
            episode_stored = False
            episode_id = None
            session.reasoning_trace.append(ReasoningStep(
                step_type="observation",
                content=f"Falha ao armazenar episódio (não crítico): {str(e)}",
            ))

        session.stage = ImportStage.COMPLETE
        session.updated_at = now_iso()

        # Persist session changes to DynamoDB
        self._save_session(session)

        log_agent_action(
            self.name, "learn_from_import",
            entity_type="session",
            entity_id=session_id,
            status="completed",
        )

        return {
            "success": True,
            "session_id": session_id,
            "stage": session.stage.value,
            "learned_patterns": len(session.learned_mappings),
            "episode_stored": episode_stored,
            "episode_id": episode_id,
        }

    def _detect_file_type(self, filename: str) -> str:
        """Detect file type from filename extension."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        type_map = {
            "xlsx": "excel",
            "xls": "excel",
            "csv": "csv",
            "xml": "xml",
            "pdf": "pdf",
            "jpg": "image",
            "jpeg": "image",
            "png": "image",
        }
        return type_map.get(ext, "unknown")

    def _compute_file_signature(self, analysis: Dict[str, Any]) -> str:
        """
        Compute a signature based on file structure for pattern matching.

        The signature captures column names to identify similar file formats.
        """
        import hashlib

        columns = []
        for sheet in analysis.get("sheets", []):
            for col in sheet.get("columns", []):
                columns.append(col.get("name", "").lower().strip())

        # Sort for consistency
        columns.sort()
        signature_str = "|".join(columns)

        return hashlib.md5(signature_str.encode()).hexdigest()[:12]

    # =========================================================================
    # RECALL Phase: Retrieve Prior Knowledge
    # =========================================================================

    async def get_prior_knowledge(
        self,
        filename: str,
        file_analysis: Dict[str, Any],
        user_id: str = "anonymous",
    ) -> Dict[str, Any]:
        """
        Retrieve prior knowledge before analysis (RECALL phase).

        Queries LearningAgent for similar past imports to provide
        context and suggested mappings before AI reasoning.

        Args:
            filename: Name of file being imported
            file_analysis: Initial file analysis
            user_id: User performing import

        Returns:
            Prior knowledge with similar episodes and suggestions
        """
        log_agent_action(
            self.name, "get_prior_knowledge",
            entity_type="file",
            entity_id=filename,
            status="started",
        )

        try:
            from agents.learning_agent import LearningAgent

            learning_agent = LearningAgent()

            # Build context for retrieval
            context = {
                "filename": filename,
                "filename_pattern": self._extract_filename_pattern(filename),
                "file_type": self._detect_file_type(filename),
                "file_signature": self._compute_file_signature(file_analysis),
                "sheet_count": file_analysis.get("sheet_count", 1),
                "columns": [
                    col.get("name", "")
                    for sheet in file_analysis.get("sheets", [])
                    for col in sheet.get("columns", [])
                ],
                "user_id": user_id,
            }

            result = await learning_agent.retrieve_prior_knowledge(context)

            log_agent_action(
                self.name, "get_prior_knowledge",
                entity_type="file",
                entity_id=filename,
                status="completed",
            )

            return result

        except Exception as e:
            log_agent_action(
                self.name, "get_prior_knowledge",
                entity_type="file",
                entity_id=filename,
                status="failed",
            )
            return {
                "success": False,
                "error": str(e),
                "similar_episodes": [],
                "suggested_mappings": {},
            }

    async def get_adaptive_threshold(
        self,
        filename: str,
        user_id: str = "anonymous",
    ) -> float:
        """
        Get adaptive confidence threshold based on historical patterns.

        Uses LearningAgent reflections to determine appropriate
        threshold for this file pattern.

        Args:
            filename: Name of file being imported
            user_id: User performing import

        Returns:
            Confidence threshold (0.0 to 1.0)
        """
        try:
            from agents.learning_agent import LearningAgent

            learning_agent = LearningAgent()
            context = {
                "filename_pattern": self._extract_filename_pattern(filename),
                "file_type": self._detect_file_type(filename),
                "user_id": user_id,
            }

            return await learning_agent.get_adaptive_threshold(context)

        except Exception:
            # Default threshold on error
            return 0.75

    def _extract_filename_pattern(self, filename: str) -> str:
        """Extract pattern from filename for future matching."""
        import re

        # Remove date patterns (YYYY-MM-DD, DD-MM-YYYY, etc.)
        pattern = re.sub(r'\d{4}[-_]\d{2}[-_]\d{2}', 'DATE', filename)
        pattern = re.sub(r'\d{2}[-_]\d{2}[-_]\d{4}', 'DATE', pattern)

        # Remove sequential numbers
        pattern = re.sub(r'_\d+\.', '_N.', pattern)

        return pattern.lower()

    # =========================================================================
    # ACT Phase: Execute Import
    # =========================================================================

    async def prepare_for_processing(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Prepare final configuration for import processing (ACT phase).

        Consolidates all learned mappings and user decisions into
        a configuration ready for the ImportAgent to execute.

        Args:
            session_id: Import session ID

        Returns:
            Processing configuration
        """
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session {session_id} not found. Session may have expired."}

        session.reasoning_trace.append(ReasoningStep(
            step_type="conclusion",
            content="Preparando configuração final para processamento",
        ))

        # Build processing config
        config = {
            "session_id": session_id,
            "filename": session.filename,
            "s3_key": session.s3_key,
            "column_mappings": session.learned_mappings,
            "selected_sheets": session.file_analysis.get("selected_sheets", "all"),
            "movement_type": session.file_analysis.get("movement_type", "entry"),
            "confidence": session.confidence.to_dict() if session.confidence else None,
            "strategy": session.file_analysis.get("recommended_strategy"),
        }

        session.stage = ImportStage.PROCESSING
        session.updated_at = now_iso()

        # Persist session changes to DynamoDB
        self._save_session(session)

        return {
            "success": True,
            "session_id": session_id,
            "stage": session.stage.value,
            "config": config,
            "reasoning": [
                {"type": r.step_type, "content": r.content}
                for r in session.reasoning_trace
            ],
        }

    # =========================================================================
    # Full Flow Orchestration
    # =========================================================================

    async def analyze_file_intelligently(
        self,
        filename: str,
        s3_key: str,
        file_content: bytes,
        prior_knowledge: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Full intelligent analysis flow (OBSERVE + THINK + ASK).

        This is the main entry point that orchestrates the analysis,
        reasoning, and question generation phases.

        Args:
            filename: Original filename
            s3_key: S3 key where file is stored
            file_content: Raw file content
            prior_knowledge: Previously learned patterns

        Returns:
            Complete analysis with questions if needed
        """
        # Create session
        print(f"[NexoImportAgent] Creating session for: {filename}")
        session = self.create_session(filename, s3_key)
        print(f"[NexoImportAgent] Session created: {session.session_id}")

        # OBSERVE: Analyze file
        print(f"[NexoImportAgent] OBSERVE phase - analyzing file...")
        analysis_result = await self.analyze_file(session.session_id, file_content)
        print(f"[NexoImportAgent] OBSERVE result: success={analysis_result.get('success')}, error={analysis_result.get('error')}")
        if not analysis_result.get("success"):
            return analysis_result

        # THINK: Reason about mappings
        print(f"[NexoImportAgent] THINK phase - reasoning about mappings...")
        reasoning_result = await self.reason_about_mappings(
            session.session_id,
            prior_knowledge,
        )
        print(f"[NexoImportAgent] THINK result: success={reasoning_result.get('success')}, error={reasoning_result.get('error')}")
        if not reasoning_result.get("success"):
            return reasoning_result

        # ASK: Get questions if needed
        if reasoning_result.get("needs_clarification"):
            questions_result = await self.get_questions(session.session_id)
            return {
                **questions_result,
                "analysis": analysis_result.get("analysis"),
            }

        # No questions needed - ready for processing
        return {
            "success": True,
            "session_id": session.session_id,
            "stage": session.stage.value,
            "analysis": analysis_result.get("analysis"),
            "suggested_mappings": reasoning_result.get("suggested_mappings"),
            "confidence": reasoning_result.get("confidence"),
            "ready_for_processing": True,
            "reasoning": [
                {"type": r.step_type, "content": r.content}
                for r in session.reasoning_trace
            ],
        }


# =============================================================================
# Serialization Helpers
# =============================================================================


def session_to_dict(session: ImportSession) -> Dict[str, Any]:
    """Convert ImportSession to dictionary for JSON serialization."""
    return {
        "session_id": session.session_id,
        "filename": session.filename,
        "s3_key": session.s3_key,
        "stage": session.stage.value,
        "file_analysis": session.file_analysis,
        "reasoning_trace": [
            {
                "type": r.step_type,
                "content": r.content,
                "tool": r.tool,
                "result": r.result,
                "timestamp": r.timestamp,
            }
            for r in session.reasoning_trace
        ],
        "questions": [
            {
                "id": q.id,
                "question": q.question,
                "context": q.context,
                "options": q.options,
                "importance": q.importance,
                "topic": q.topic,
                "column": q.column,
            }
            for q in session.questions
        ],
        "answers": session.answers,
        "learned_mappings": session.learned_mappings,
        "confidence": session.confidence.to_dict() if session.confidence else None,
        "error": session.error,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
