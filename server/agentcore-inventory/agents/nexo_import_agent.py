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
# NEXO Import Agent - STATELESS Architecture
# =============================================================================
# This agent is STATELESS - all session state is managed by the frontend.
# Each method receives full state as input and returns updated state.
# No DynamoDB persistence for sessions (inventory table is for ASSETS ONLY).
# =============================================================================


class NexoImportAgent(BaseInventoryAgent):
    """
    Intelligent import assistant using ReAct pattern (STATELESS).

    This agent orchestrates the entire intelligent import flow:
    1. OBSERVE: Analyzes file structure using sheet_analyzer
    2. THINK: Reasons about column mappings using Gemini
    3. ASK: Generates clarification questions when uncertain
    4. LEARN: Stores successful patterns in AgentCore Memory
    5. ACT: Executes import with learned knowledge

    Architecture:
        - STATELESS: No session persistence in DynamoDB
        - Frontend maintains full state
        - Each call receives state and returns updated state
    """

    def __init__(self):
        """Initialize the NEXO Import Agent."""
        super().__init__(
            name="NexoImportAgent",
            instruction=NEXO_IMPORT_INSTRUCTION,
            description="Assistente inteligente de importação com aprendizado contínuo",
        )

    # =========================================================================
    # Session Helpers (In-Memory Only, No Persistence)
    # =========================================================================

    def _create_session(
        self,
        filename: str,
        s3_key: str,
    ) -> ImportSession:
        """
        Create a new import session (in-memory only, no persistence).

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

        log_agent_action(
            self.name, "create_session",
            entity_type="session",
            entity_id=session_id,
            status="completed",
        )

        return session

    def _restore_session(self, state: Dict[str, Any]) -> ImportSession:
        """
        Restore ImportSession from frontend state (deserialization).

        Args:
            state: Session state dict from frontend

        Returns:
            ImportSession object
        """
        return ImportSession(
            session_id=state.get("session_id", generate_id("NEXO")),
            filename=state.get("filename", ""),
            s3_key=state.get("s3_key", ""),
            stage=ImportStage(state.get("stage", "analyzing")),
            file_analysis=state.get("file_analysis"),
            reasoning_trace=[
                ReasoningStep(
                    step_type=r.get("type", r.get("step_type", "observation")),
                    content=r.get("content", ""),
                    tool=r.get("tool"),
                    result=r.get("result"),
                    timestamp=r.get("timestamp", now_iso()),
                )
                for r in state.get("reasoning_trace", [])
            ],
            questions=[
                NexoQuestion(
                    id=q.get("id", generate_id("Q")),
                    question=q.get("question", ""),
                    context=q.get("context", ""),
                    options=q.get("options", []),
                    importance=q.get("importance", "medium"),
                    topic=q.get("topic", "general"),
                    column=q.get("column"),
                )
                for q in state.get("questions", [])
            ],
            answers=state.get("answers", {}),
            learned_mappings=state.get("learned_mappings", state.get("column_mappings", {})),
            confidence=ConfidenceScore(
                overall=state["confidence"].get("overall", 0.5),
                extraction_quality=state["confidence"].get("extraction_quality", 1.0),
                evidence_strength=state["confidence"].get("evidence_strength", 1.0),
                historical_match=state["confidence"].get("historical_match", 1.0),
                risk_level=state["confidence"].get("risk_level", RiskLevel.LOW),
                factors=state["confidence"].get("factors", []),
                requires_hil=state["confidence"].get("requires_hil", False),
            ) if state.get("confidence") and isinstance(state["confidence"], dict) else None,
            error=state.get("error"),
            created_at=state.get("created_at", now_iso()),
            updated_at=now_iso(),
        )

    # =========================================================================
    # AUTONOMOUS Movement Type Inference (TRUE Agentic Pattern)
    # =========================================================================

    async def infer_movement_type(
        self,
        file_analysis: Dict[str, Any],
        sample_data: List[Dict[str, Any]],
        filename: str,
    ) -> tuple:
        """
        AUTONOMOUSLY infer if this is ENTRADA (+) or SAÍDA (-) or AJUSTE.

        This is TRUE agentic behavior: instead of asking the user, the agent
        reasons about the movement type based on:
        - Column semantics (entrada vs saída keywords)
        - Data patterns (supplier vs customer, +/- quantities)
        - Document context (NF de entrada vs romaneio de saída)
        - Filename patterns (e.g., "SOLICITACOES_EXPEDICAO" = SAÍDA)

        Philosophy: OBSERVE → THINK → DECIDE (without asking when confident)

        Args:
            file_analysis: Analyzed file structure
            sample_data: First 10 rows of data for pattern detection
            filename: Original filename for pattern hints

        Returns:
            tuple[str, float, str]: (movement_type, confidence, reasoning_trace)
                - movement_type: "ENTRADA" | "SAIDA" | "AJUSTE"
                - confidence: 0.0 to 1.0
                - reasoning_trace: Explicit reasoning from Gemini
        """
        log_agent_action(
            self.name, "infer_movement_type",
            status="started",
        )

        # Extract column names from all sheets
        all_columns = []
        for sheet in file_analysis.get("sheets", []):
            for col in sheet.get("columns", []):
                all_columns.append(col.get("name", "").lower())

        # Build comprehensive reasoning prompt
        prompt = f"""Você é um especialista em logística e gestão de estoque com 20 anos de experiência.

Analise este arquivo de importação e determine AUTONOMAMENTE se é:
- **ENTRADA**: Itens chegando ao estoque (compra, devolução de cliente, transferência IN)
- **SAIDA**: Itens saindo do estoque (venda, expedição, transferência OUT, romaneio)
- **AJUSTE**: Correção de inventário (positivo ou negativo)

## Nome do Arquivo
`{filename}`

## Colunas do Arquivo
{json.dumps(all_columns, ensure_ascii=False, indent=2)}

## Amostra de Dados (primeiras linhas)
{json.dumps(sample_data[:5], ensure_ascii=False, indent=2)}

## Seu Raciocínio (OBRIGATÓRIO - seja detalhista)

### 1. OBSERVE - Análise do Nome do Arquivo
- O nome contém palavras-chave como "expedição", "saída", "envio", "romaneio"? → SAÍDA
- O nome contém "entrada", "recebimento", "compra", "nf"? → ENTRADA
- O nome contém "ajuste", "inventário", "contagem"? → AJUSTE

### 2. ANALISE as COLUNAS
- Há coluna de FORNECEDOR/SUPPLIER/VENDEDOR? → Indica ENTRADA
- Há coluna de CLIENTE/DESTINATÁRIO/CUSTOMER? → Indica SAÍDA
- Há coluna de ENDEREÇO DE ENTREGA? → Indica SAÍDA
- Há coluna de QUANTIDADE_AJUSTE ou DIFERENÇA? → Indica AJUSTE

### 3. ANALISE os DADOS
- As quantidades são todas positivas? → ENTRADA ou SAÍDA
- Há quantidades mistas (positivas e negativas)? → AJUSTE
- Há informações de transportadora/frete? → SAÍDA

### 4. CONTEXTO SEMÂNTICO
- Planilhas de "solicitação de expedição" são SEMPRE SAÍDA
- Planilhas de "material recebido" são SEMPRE ENTRADA
- Planilhas com "divergência" ou "diferença" são AJUSTE

### 5. CONCLUSÃO FINAL
Com base em toda a análise acima, qual é o tipo de movimento?

## Responda APENAS em JSON válido:
{{
  "movement_type": "ENTRADA" | "SAIDA" | "AJUSTE",
  "confidence": 0.0 a 1.0,
  "reasoning": "Resumo em uma frase do raciocínio principal",
  "evidence": [
    "evidência 1 que suporta a conclusão",
    "evidência 2 que suporta a conclusão",
    "evidência 3 que suporta a conclusão"
  ],
  "alternatives_considered": [
    {{"type": "OUTRO_TIPO", "confidence": 0.X, "why_rejected": "motivo"}}
  ]
}}
"""

        try:
            # Use Gemini Thinking Mode for explicit reasoning
            thinking_trace, response = await self.invoke_with_thinking(prompt)

            # Parse JSON response
            result = parse_json_safe(response)

            movement_type = result.get("movement_type", "ENTRADA")
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            evidence = result.get("evidence", [])

            # Validate movement type
            valid_types = {"ENTRADA", "SAIDA", "AJUSTE"}
            if movement_type not in valid_types:
                movement_type = "ENTRADA"  # Default safe fallback
                confidence = 0.3  # Low confidence due to invalid response

            # Combine thinking trace with structured reasoning
            full_reasoning = f"""## Raciocínio do Gemini (Thinking Mode)
{thinking_trace if thinking_trace else '(sem trace de thinking)'}

## Conclusão Estruturada
- **Tipo**: {movement_type}
- **Confiança**: {confidence:.0%}
- **Motivo**: {reasoning}

## Evidências
{chr(10).join(f'- {e}' for e in evidence)}
"""

            log_agent_action(
                self.name, "infer_movement_type",
                status="completed",
                details={
                    "movement_type": movement_type,
                    "confidence": confidence,
                },
            )

            return movement_type, confidence, full_reasoning

        except Exception as e:
            log_agent_action(
                self.name, "infer_movement_type",
                status="failed",
                details={"error": str(e)[:100]},
            )
            # Safe fallback: ENTRADA with low confidence
            return "ENTRADA", 0.3, f"Falha na inferência: {str(e)}"

    def _extract_sample_data(
        self,
        file_content: bytes,
        file_analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Extract sample data rows from file for movement type inference.

        Args:
            file_content: Raw file content
            file_analysis: Analyzed file structure

        Returns:
            List of dicts representing first 10 data rows
        """
        try:
            # Lazy import to reduce cold start
            from tools.sheet_analyzer import load_workbook_smart

            wb = load_workbook_smart(file_content)
            samples = []

            # Get first sheet with data
            sheets = file_analysis.get("sheets", [])
            if not sheets:
                return []

            first_sheet = sheets[0]
            sheet_name = first_sheet.get("name", "")
            columns = [c.get("name", f"col_{i}") for i, c in enumerate(first_sheet.get("columns", []))]

            # Read from workbook
            if hasattr(wb, 'sheet_names'):  # pandas ExcelFile
                import pandas as pd
                df = pd.read_excel(wb, sheet_name=sheet_name, nrows=10)
                samples = df.head(10).to_dict(orient="records")
            elif hasattr(wb, 'sheetnames'):  # openpyxl Workbook
                ws = wb[sheet_name]
                for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=11, values_only=True)):
                    if row_idx >= 10:
                        break
                    row_dict = {}
                    for col_idx, value in enumerate(row):
                        col_name = columns[col_idx] if col_idx < len(columns) else f"col_{col_idx}"
                        row_dict[col_name] = str(value) if value is not None else ""
                    samples.append(row_dict)

            return samples

        except Exception as e:
            print(f"[NEXO] Warning: Failed to extract sample data: {e}")
            return []

    # =========================================================================
    # OBSERVE Phase: File Analysis
    # =========================================================================

    async def analyze_file(
        self,
        session: ImportSession,
        file_content: bytes,
    ) -> Dict[str, Any]:
        """
        Analyze file structure (OBSERVE phase) - STATELESS.

        Uses sheet_analyzer tool to deeply understand file structure,
        including multi-sheet analysis and column detection.

        Args:
            session: Import session (in-memory, from frontend state)
            file_content: Raw file content

        Returns:
            Analysis result with updated session state
        """
        log_agent_action(
            self.name, "analyze_file",
            entity_type="session",
            entity_id=session.session_id,
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

            log_agent_action(
                self.name, "analyze_file",
                entity_type="session",
                entity_id=session.session_id,
                status="completed",
                details={"count": analysis.sheet_count},
            )

            return {
                "success": True,
                "session": session_to_dict(session),  # Return full state
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
                entity_id=session.session_id,
                status="failed",
            )

            return {
                "success": False,
                "session": session_to_dict(session),
                "error": error_msg,
            }

    # =========================================================================
    # THINK Phase: AI Reasoning
    # =========================================================================

    async def reason_about_mappings(
        self,
        session: ImportSession,
        prior_knowledge: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Reason about column mappings using Gemini (THINK phase) - STATELESS.

        Uses the AI model to analyze the file structure and suggest
        column mappings with confidence scores.

        Args:
            session: Import session (in-memory, from frontend state)
            prior_knowledge: Previously learned mappings from memory

        Returns:
            Reasoning result with updated session state
        """
        if not session.file_analysis:
            return {"success": False, "error": "File not analyzed yet. Call analyze_file first."}

        log_agent_action(
            self.name, "reason_about_mappings",
            entity_type="session",
            entity_id=session.session_id,
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

                # Store suggested mappings (defensive: Gemini may return string instead of dict)
                suggested = result.get("suggested_mappings", {})
                if isinstance(suggested, dict):
                    session.learned_mappings.update(suggested)
                elif isinstance(suggested, str):
                    # Gemini returned JSON string instead of dict - try to parse
                    try:
                        parsed = json.loads(suggested)
                        if isinstance(parsed, dict):
                            session.learned_mappings.update(parsed)
                    except (json.JSONDecodeError, TypeError):
                        print(f"[NEXO] WARNING: suggested_mappings is string, failed to parse: {suggested[:100]}")

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
                    # Defensive: ensure questions is a list
                    if not isinstance(questions, list):
                        questions = []
                    for q in questions:
                        # Defensive: skip non-dict items
                        if not isinstance(q, dict):
                            continue
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

            log_agent_action(
                self.name, "reason_about_mappings",
                entity_type="session",
                entity_id=session.session_id,
                status="completed",
            )

            return {
                "success": True,
                "session": session_to_dict(session),  # Return full state
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
                entity_id=session.session_id,
                status="failed",
            )
            return {
                "success": False,
                "session": session_to_dict(session),
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
        session: ImportSession,
    ) -> Dict[str, Any]:
        """
        Get clarification questions for the user (ASK phase) - STATELESS.

        Returns questions generated during analysis and reasoning.

        Args:
            session: Import session (in-memory, from frontend state)

        Returns:
            Questions with updated session state
        """
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

        return {
            "success": True,
            "session": session_to_dict(session),  # Return full state
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
        session: ImportSession,
        answers: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process user answers to questions - STATELESS.

        Applies answers to refine mappings and prepare for processing.

        Args:
            session: Import session (in-memory, from frontend state)
            answers: Dict mapping question_id to answer

        Returns:
            Updated session state
        """
        log_agent_action(
            self.name, "submit_answers",
            entity_type="session",
            entity_id=session.session_id,
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
                if session.file_analysis:
                    session.file_analysis["selected_sheets"] = answer
            elif q.topic == "movement_type":
                if session.file_analysis:
                    session.file_analysis["movement_type"] = answer

        session.stage = ImportStage.LEARNING
        session.updated_at = now_iso()

        log_agent_action(
            self.name, "submit_answers",
            entity_type="session",
            entity_id=session.session_id,
            status="completed",
        )

        return {
            "success": True,
            "session": session_to_dict(session),  # Return full state
            "applied_mappings": session.learned_mappings,
            "ready_for_processing": True,
        }

    # =========================================================================
    # LEARN Phase: Pattern Storage (with AgentCore Episodic Memory)
    # =========================================================================

    async def learn_from_import(
        self,
        session: ImportSession,
        import_result: Dict[str, Any],
        user_id: str = "anonymous",
        user_corrections: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store learned patterns from successful import (LEARN phase) - STATELESS.

        Uses AgentCore Episodic Memory via LearningAgent to store patterns
        for future imports. Creates episodes that are consolidated into
        reflections for continuous improvement.

        Args:
            session: Import session (in-memory, from frontend state)
            import_result: Result of the import operation
            user_id: User performing the import
            user_corrections: Manual corrections made by user

        Returns:
            Learning result with episode_id
        """
        log_agent_action(
            self.name, "learn_from_import",
            entity_type="session",
            entity_id=session.session_id,
            status="started",
        )

        session.reasoning_trace.append(ReasoningStep(
            step_type="action",
            content="Armazenando padrões aprendidos em Memória Episódica",
            tool="learning_agent",
        ))

        # Build episode data from session + result
        episode_data = {
            "session_id": session.session_id,
            "filename": session.filename,
            "filename_pattern": self._extract_filename_pattern(session.filename),
            "file_type": self._detect_file_type(session.filename),
            "file_signature": self._compute_file_signature(session.file_analysis) if session.file_analysis else "",
            "sheet_structure": {
                "sheet_count": session.file_analysis.get("sheet_count", 1) if session.file_analysis else 1,
                "sheets": [
                    {
                        "name": s.get("name", ""),
                        "purpose": s.get("purpose", s.get("detected_purpose", "")),
                        "column_count": s.get("column_count", 0),
                        "row_count": s.get("row_count", 0),
                    }
                    for s in (session.file_analysis.get("sheets", []) if session.file_analysis else [])
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

        log_agent_action(
            self.name, "learn_from_import",
            entity_type="session",
            entity_id=session.session_id,
            status="completed",
        )

        return {
            "success": True,
            "session": session_to_dict(session),  # Return full state
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
        session: ImportSession,
    ) -> Dict[str, Any]:
        """
        Prepare final configuration for import processing (ACT phase) - STATELESS.

        Consolidates all learned mappings and user decisions into
        a configuration ready for the ImportAgent to execute.

        Args:
            session: Import session (in-memory, from frontend state)

        Returns:
            Processing configuration with updated session state
        """
        session.reasoning_trace.append(ReasoningStep(
            step_type="conclusion",
            content="Preparando configuração final para processamento",
        ))

        # Build column mappings in expected format
        # Convert learned_mappings dict to array format expected by frontend
        column_mappings_array = []
        if session.learned_mappings:
            for file_col, target_field in session.learned_mappings.items():
                column_mappings_array.append({
                    "file_column": file_col,
                    "target_field": target_field,
                })

        # Get selected sheets as array
        raw_sheets = session.file_analysis.get("selected_sheets", []) if session.file_analysis else []
        if isinstance(raw_sheets, str):
            selected_sheets = [raw_sheets] if raw_sheets != "all" else []
        else:
            selected_sheets = raw_sheets if raw_sheets else []

        # Get confidence value
        final_confidence = 0.0
        if session.confidence:
            final_confidence = session.confidence.overall

        session.stage = ImportStage.PROCESSING
        session.updated_at = now_iso()

        # Return response matching NexoProcessingConfig interface
        return {
            "success": True,
            "ready": True,  # CRITICAL: Frontend checks this field
            "import_session_id": session.session_id,
            "column_mappings": column_mappings_array,
            "selected_sheets": selected_sheets,
            "movement_type": session.file_analysis.get("movement_type", "entry") if session.file_analysis else "entry",
            "special_handling": session.file_analysis.get("special_handling", {}) if session.file_analysis else {},
            "final_confidence": final_confidence,
            # Also include session state for stateless architecture
            "session": session_to_dict(session),
            "reasoning": [
                {"type": r.step_type, "content": r.content}
                for r in session.reasoning_trace
            ],
        }

    # =========================================================================
    # Full Flow Orchestration (STATELESS)
    # =========================================================================

    async def analyze_file_intelligently(
        self,
        filename: str,
        s3_key: str,
        file_content: bytes,
        prior_knowledge: Optional[Dict[str, Any]] = None,
        user_id: str = "anonymous",
    ) -> Dict[str, Any]:
        """
        Full intelligent analysis flow with TRUE Agentic Pattern - STATELESS.

        Philosophy: OBSERVE → REMEMBER → THINK → DECIDE → (ASK only if needed)

        This is the main entry point that orchestrates:
        1. OBSERVE: Analyze file structure (sheets, columns, data)
        2. REMEMBER: Query prior knowledge BEFORE reasoning (Memory-First!)
        3. THINK: Infer movement type AUTONOMOUSLY using Gemini Thinking
        4. DECIDE: Calculate confidence and determine if questions needed
        5. ASK: Only generate questions for truly uncertain fields

        Returns FULL SESSION STATE to be stored by frontend.

        Args:
            filename: Original filename
            s3_key: S3 key where file is stored
            file_content: Raw file content
            prior_knowledge: Previously learned patterns (if provided externally)
            user_id: User performing import (for memory queries)

        Returns:
            Complete analysis with FULL SESSION STATE
        """
        # Create session (in-memory only, no persistence)
        print(f"[NexoImportAgent] Creating session for: {filename}")
        session = self._create_session(filename, s3_key)
        print(f"[NexoImportAgent] Session created: {session.session_id}")

        # =====================================================================
        # PHASE 1: OBSERVE - Analyze file structure
        # =====================================================================
        session.reasoning_trace.append(ReasoningStep(
            step_type="observation",
            content=f"📁 Iniciando análise do arquivo '{filename}'",
        ))

        print(f"[NexoImportAgent] OBSERVE phase - analyzing file...")
        analysis_result = await self.analyze_file(session, file_content)
        print(f"[NexoImportAgent] OBSERVE result: success={analysis_result.get('success')}")

        if not analysis_result.get("success"):
            return analysis_result

        # Update session from result
        if analysis_result.get("session"):
            session = self._restore_session(analysis_result["session"])

        # =====================================================================
        # PHASE 2: REMEMBER - Query prior knowledge BEFORE reasoning
        # =====================================================================
        # This is MEMORY-FIRST architecture: retrieve learned patterns BEFORE
        # AI reasoning to provide context and boost confidence.
        session.reasoning_trace.append(ReasoningStep(
            step_type="memory_retrieval",
            content="🧠 Consultando memória episódica para padrões similares...",
        ))

        print(f"[NexoImportAgent] REMEMBER phase - querying prior knowledge...")

        # Use provided prior_knowledge or fetch from LearningAgent
        if not prior_knowledge:
            try:
                from agents.learning_agent import LearningAgent
                learning_agent = LearningAgent()
                prior_knowledge = await learning_agent.retrieve_prior_knowledge(
                    user_id=user_id,
                    filename=filename,
                    file_analysis=session.file_analysis or {},
                )
                print(f"[NexoImportAgent] REMEMBER result: has_prior={prior_knowledge.get('has_prior_knowledge', False)}")
            except Exception as e:
                print(f"[NexoImportAgent] REMEMBER failed (non-critical): {e}")
                prior_knowledge = {"has_prior_knowledge": False}

        # Apply prior knowledge if found
        if prior_knowledge.get("has_prior_knowledge"):
            similar_count = len(prior_knowledge.get("similar_episodes", []))
            suggested_mappings = prior_knowledge.get("suggested_mappings", {})
            confidence_boost = prior_knowledge.get("confidence_boost", 0.0)

            session.reasoning_trace.append(ReasoningStep(
                step_type="memory_hit",
                content=f"✅ Encontrei {similar_count} imports similares! "
                        f"Aplicando {len(suggested_mappings)} mapeamentos sugeridos.",
            ))

            # Pre-populate learned mappings from memory
            for col, mapping_info in suggested_mappings.items():
                if isinstance(mapping_info, dict):
                    session.learned_mappings[col] = mapping_info.get("field", "")
                else:
                    session.learned_mappings[col] = str(mapping_info)
        else:
            session.reasoning_trace.append(ReasoningStep(
                step_type="memory_miss",
                content="📝 Nenhum padrão similar encontrado. Analisando do zero.",
            ))

        # =====================================================================
        # PHASE 3: THINK - Infer movement type AUTONOMOUSLY
        # =====================================================================
        # This is TRUE agentic behavior: instead of asking the user,
        # the agent reasons about the movement type using Gemini Thinking.
        session.reasoning_trace.append(ReasoningStep(
            step_type="thought",
            content="🤔 Iniciando inferência autônoma do tipo de movimento...",
        ))

        print(f"[NexoImportAgent] THINK phase - inferring movement type AUTONOMOUSLY...")

        # Extract sample data for inference
        sample_data = self._extract_sample_data(file_content, session.file_analysis or {})

        # Infer movement type using Gemini Thinking
        movement_type, movement_confidence, movement_reasoning = await self.infer_movement_type(
            file_analysis=session.file_analysis or {},
            sample_data=sample_data,
            filename=filename,
        )

        print(f"[NexoImportAgent] THINK result: type={movement_type}, confidence={movement_confidence:.0%}")

        # Store inference result in session
        if session.file_analysis:
            session.file_analysis["inferred_movement_type"] = movement_type
            session.file_analysis["movement_type_confidence"] = movement_confidence
            session.file_analysis["movement_reasoning"] = movement_reasoning

        session.reasoning_trace.append(ReasoningStep(
            step_type="conclusion",
            content=f"💡 Tipo de movimento inferido: **{movement_type}** "
                    f"(confiança: {movement_confidence:.0%})",
        ))

        # =====================================================================
        # PHASE 4: THINK - Reason about column mappings
        # =====================================================================
        print(f"[NexoImportAgent] THINK phase - reasoning about column mappings...")
        reasoning_result = await self.reason_about_mappings(session, prior_knowledge)
        print(f"[NexoImportAgent] THINK (mappings) result: success={reasoning_result.get('success')}")

        if not reasoning_result.get("success"):
            return reasoning_result

        # Update session from reasoning result
        if reasoning_result.get("session"):
            session = self._restore_session(reasoning_result["session"])

        # =====================================================================
        # PHASE 5: DECIDE - Should we ask questions or process autonomously?
        # =====================================================================
        # TRUE agentic decision: Only ask when truly uncertain
        # High confidence (>=0.85): Process autonomously
        # Medium confidence (0.60-0.85): Ask targeted questions only
        # Low confidence (<0.60): Full HIL required

        overall_confidence = self._calculate_overall_confidence(
            session=session,
            movement_confidence=movement_confidence,
            prior_knowledge=prior_knowledge,
        )

        print(f"[NexoImportAgent] DECIDE phase: overall_confidence={overall_confidence:.0%}")

        # Adaptive threshold from historical patterns
        adaptive_threshold = 0.75  # Default
        if prior_knowledge:
            adaptive_threshold = prior_knowledge.get("adaptive_threshold", 0.75)

        # Decision logic
        if overall_confidence >= 0.85 and movement_confidence >= 0.90:
            # HIGH CONFIDENCE: Process autonomously without questions
            session.stage = ImportStage.PROCESSING
            session.reasoning_trace.append(ReasoningStep(
                step_type="decision",
                content=f"🚀 Confiança alta ({overall_confidence:.0%}). "
                        f"Processando AUTONOMAMENTE sem perguntas.",
            ))
            # Apply inferred movement type
            if session.file_analysis:
                session.file_analysis["movement_type"] = movement_type

            print(f"[NexoImportAgent] DECIDE: AUTONOMOUS processing (no questions)")

            return {
                "success": True,
                "session": session_to_dict(session),
                "session_id": session.session_id,
                "stage": session.stage.value,
                "analysis": analysis_result.get("analysis"),
                "suggested_mappings": reasoning_result.get("suggested_mappings"),
                "confidence": reasoning_result.get("confidence"),
                "ready_for_processing": True,
                "autonomous_decision": True,
                "inferred_movement_type": movement_type,
                "movement_confidence": movement_confidence,
                "reasoning": [
                    {"type": r.step_type, "content": r.content}
                    for r in session.reasoning_trace
                ],
            }

        elif overall_confidence >= adaptive_threshold:
            # MEDIUM CONFIDENCE: Ask only about movement type (not everything)
            session.stage = ImportStage.QUESTIONING
            session.reasoning_trace.append(ReasoningStep(
                step_type="decision",
                content=f"⚖️ Confiança média ({overall_confidence:.0%}). "
                        f"Perguntando apenas sobre campos incertos.",
            ))

            # Generate targeted questions (only for uncertain fields)
            targeted_questions = self._generate_targeted_questions(
                session=session,
                movement_type=movement_type,
                movement_confidence=movement_confidence,
            )

            print(f"[NexoImportAgent] DECIDE: TARGETED questions ({len(targeted_questions)} questions)")

            # Add only targeted questions
            session.questions = targeted_questions

        else:
            # LOW CONFIDENCE: Full HIL required
            session.stage = ImportStage.QUESTIONING
            session.reasoning_trace.append(ReasoningStep(
                step_type="decision",
                content=f"🔍 Confiança baixa ({overall_confidence:.0%}). "
                        f"Solicitando revisão humana completa.",
            ))

            print(f"[NexoImportAgent] DECIDE: FULL HIL required")

            # Get all questions
            questions_result = await self.get_questions(session)
            if questions_result.get("session"):
                session = self._restore_session(questions_result["session"])

        # Return with questions
        final_session = session_to_dict(session)
        return {
            "success": True,
            "session": final_session,
            "session_id": session.session_id,
            "stage": session.stage.value,
            "analysis": analysis_result.get("analysis"),
            "suggested_mappings": reasoning_result.get("suggested_mappings"),
            "confidence": reasoning_result.get("confidence"),
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
            "needs_clarification": len(session.questions) > 0,
            "inferred_movement_type": movement_type,
            "movement_confidence": movement_confidence,
            "reasoning": [
                {"type": r.step_type, "content": r.content}
                for r in session.reasoning_trace
            ],
        }

    def _calculate_overall_confidence(
        self,
        session: ImportSession,
        movement_confidence: float,
        prior_knowledge: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate overall confidence for autonomous processing decision.

        Combines:
        - Column mapping confidence (from Gemini reasoning)
        - Movement type confidence (from autonomous inference)
        - Historical match boost (from prior knowledge)

        Args:
            session: Current import session
            movement_confidence: Confidence in movement type inference
            prior_knowledge: Prior knowledge from memory

        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        # Base confidence from session
        base_confidence = 0.5
        if session.confidence:
            base_confidence = session.confidence.overall

        # Weight factors
        weights = {
            "mapping": 0.4,      # Column mapping quality
            "movement": 0.35,   # Movement type inference
            "historical": 0.25, # Historical match
        }

        # Calculate weighted score
        mapping_score = base_confidence
        movement_score = movement_confidence

        # Historical boost from prior knowledge
        historical_score = 0.5  # Default (no history)
        if prior_knowledge and prior_knowledge.get("has_prior_knowledge"):
            historical_score = 0.7 + prior_knowledge.get("confidence_boost", 0.0)

        overall = (
            mapping_score * weights["mapping"] +
            movement_score * weights["movement"] +
            historical_score * weights["historical"]
        )

        return min(max(overall, 0.0), 1.0)

    def _generate_targeted_questions(
        self,
        session: ImportSession,
        movement_type: str,
        movement_confidence: float,
    ) -> List[NexoQuestion]:
        """
        Generate targeted questions only for uncertain fields.

        TRUE agentic pattern: Don't ask about everything, only ask about
        fields where the agent is genuinely uncertain.

        Args:
            session: Current import session
            movement_type: Inferred movement type
            movement_confidence: Confidence in inference

        Returns:
            List of targeted questions (fewer than full HIL)
        """
        questions = []

        # Only ask about movement type if confidence is below 90%
        if movement_confidence < 0.90:
            questions.append(NexoQuestion(
                id=generate_id("Q"),
                question=f"Confirma que este arquivo é uma **{movement_type}**?",
                context=f"O NEXO inferiu que este arquivo representa uma {movement_type} "
                        f"com {movement_confidence:.0%} de confiança. "
                        f"Confirme ou corrija se necessário.",
                options=[
                    {"label": "✅ Sim, é ENTRADA", "value": "ENTRADA"},
                    {"label": "📤 Não, é SAÍDA", "value": "SAIDA"},
                    {"label": "⚖️ É um AJUSTE de estoque", "value": "AJUSTE"},
                ],
                importance="critical",
                topic="movement_type",
            ))

        # Ask about uncertain column mappings (only those with low confidence)
        if session.file_analysis:
            for sheet in session.file_analysis.get("sheets", []):
                for col in sheet.get("columns", []):
                    mapping_confidence = col.get("mapping_confidence", 0)
                    if mapping_confidence < 0.6 and not col.get("suggested_mapping"):
                        col_name = col.get("name", "")
                        samples = col.get("sample_values", [])[:3]

                        questions.append(NexoQuestion(
                            id=generate_id("Q"),
                            question=f"O que a coluna '{col_name}' representa?",
                            context=f"Exemplos de valores: {', '.join(str(s) for s in samples)}",
                            options=[
                                {"label": "Part Number / SKU", "value": "part_number"},
                                {"label": "Quantidade", "value": "quantity"},
                                {"label": "Número de Série", "value": "serial_number"},
                                {"label": "Localização", "value": "location"},
                                {"label": "Descrição", "value": "description"},
                                {"label": "Ignorar esta coluna", "value": "_ignore"},
                            ],
                            importance="high",
                            topic="column_mapping",
                            column=col_name,
                        ))

                        # Limit to 3 column questions
                        if len([q for q in questions if q.topic == "column_mapping"]) >= 3:
                            break

        return questions


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
