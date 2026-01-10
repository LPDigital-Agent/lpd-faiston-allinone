# =============================================================================
# NEXO Import Agent - Intelligent Import Assistant
# =============================================================================
# AI-First intelligent import agent using ReAct pattern.
# Guides user through import with questions, learns from corrections,
# and improves over time using AgentCore Episodic Memory.
#
# Philosophy: OBSERVE_SCHEMA → OBSERVE_FILE → THINK → VALIDATE → ASK → LEARN → ACT
#
# SCHEMA-AWARE: Now queries PostgreSQL schema BEFORE analyzing files.
# This enables true schema-aware reasoning and validation.
#
# Module: Gestao de Ativos -> Gestao de Estoque -> Smart Import
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
# Author: Faiston NEXO Team
# Updated: January 2026 - Schema-aware prompts
# =============================================================================

import logging
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

logger = logging.getLogger(__name__)


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
class RequestedNewColumn:
    """A column requested by user that doesn't exist in schema."""
    name: str                           # Sanitized column name (snake_case)
    original_name: str                  # Original name from user instruction
    user_intent: str                    # User's explanation of what this column should store
    inferred_type: str = "TEXT"         # PostgreSQL type inferred from data
    sample_values: List[str] = field(default_factory=list)  # Sample data for type inference
    source_file_column: str = ""        # Original column name in import file
    approved: bool = False              # Whether admin approved creation


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
    # FIX (January 2026): Store "Outros:" user instructions for AI interpretation
    ai_instructions: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # FEATURE (January 2026): Dynamic schema evolution - columns user wants to create
    requested_new_columns: List[RequestedNewColumn] = field(default_factory=list)
    confidence: Optional[ConfidenceScore] = None
    error: Optional[str] = None
    # FIX (January 2026): Track user for audit trail in schema evolution
    user_id: Optional[str] = None
    # FIX (January 2026): Global user feedback for AI interpretation
    global_user_feedback: Optional[str] = None
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
        # Lazy-loaded schema components
        self._schema_provider = None
        self._schema_validator = None

    # =========================================================================
    # Schema-Aware Helpers (OBSERVE_SCHEMA phase)
    # =========================================================================

    def _get_schema_provider(self):
        """
        Get or create SchemaProvider instance (lazy initialization).

        Lazy loading prevents cold start impact - schema is only
        fetched when needed for reasoning prompts.
        """
        if self._schema_provider is None:
            try:
                from tools.schema_provider import get_schema_provider
                self._schema_provider = get_schema_provider()
                logger.info("[NexoImportAgent] Schema provider initialized")
            except Exception as e:
                logger.warning(f"[NexoImportAgent] Schema provider unavailable: {e}")
        return self._schema_provider

    def _get_schema_validator(self):
        """
        Get or create SchemaValidator instance (lazy initialization).
        """
        if self._schema_validator is None:
            try:
                from tools.schema_validator import get_schema_validator
                self._schema_validator = get_schema_validator(self._get_schema_provider())
                logger.info("[NexoImportAgent] Schema validator initialized")
            except Exception as e:
                logger.warning(f"[NexoImportAgent] Schema validator unavailable: {e}")
        return self._schema_validator

    def _sanitize_column_name(self, name: str) -> str:
        """
        Sanitize user-provided column name to valid PostgreSQL identifier.

        Security: Prevents SQL injection and ensures PostgreSQL compatibility.

        Args:
            name: Raw column name from user/AI

        Returns:
            Sanitized snake_case column name (clear, user-friendly naming)
        """
        import re

        if not name:
            return "custom_field"

        # Convert to lowercase
        sanitized = name.lower().strip()

        # Replace spaces and special chars with underscore
        sanitized = re.sub(r'[^a-z0-9_]', '_', sanitized)

        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)

        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')

        # Ensure starts with letter (PostgreSQL requirement)
        if sanitized and sanitized[0].isdigit():
            sanitized = f"col_{sanitized}"

        # FIX (January 2026): Don't add automatic "import_" prefix
        # Column names should be clear and user-friendly
        # The user explicitly requested clearer naming without the import_ prefix

        # Limit length (PostgreSQL max is 63, we use 50 for safety)
        if len(sanitized) > 50:
            sanitized = sanitized[:50]

        return sanitized or "custom_field"

    def _get_schema_context(self, target_table: str = "pending_entry_items") -> str:
        """
        Get PostgreSQL schema context for Gemini prompt injection.

        This is the KEY method that enables schema-aware reasoning.
        The schema context is injected into Gemini prompts so the AI
        knows the exact target table structure.

        Args:
            target_table: Target PostgreSQL table

        Returns:
            Markdown-formatted schema documentation for prompt injection
        """
        provider = self._get_schema_provider()
        if not provider:
            return "⚠️ Schema não disponível - usando mapeamento genérico"

        try:
            schema_md = provider.get_schema_for_prompt(target_table)

            # Add ENUMs section
            enums = provider.get_all_enums()
            if enums:
                schema_md += "\n\n### ENUMs Válidos\n"
                for enum_name, values in enums.items():
                    schema_md += f"- **{enum_name}**: `{', '.join(values)}`\n"

            # Add required columns
            required = provider.get_required_columns(target_table)
            if required:
                schema_md += f"\n\n### Colunas Obrigatórias (NOT NULL)\n"
                schema_md += f"`{', '.join(required)}`\n"

            return schema_md

        except Exception as e:
            logger.warning(f"[NexoImportAgent] Failed to get schema context: {e}")
            return f"⚠️ Erro ao obter schema: {str(e)}"

    def _validate_mappings_against_schema(
        self,
        column_mappings: Dict[str, str],
        target_table: str = "pending_entry_items",
        sample_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Validate column mappings against PostgreSQL schema.

        This is called BEFORE ACT phase to catch invalid mappings
        before they hit the database.

        Args:
            column_mappings: Dict mapping file_column → target_column
            target_table: Target PostgreSQL table
            sample_data: Optional sample data for value validation

        Returns:
            Validation result with errors, warnings, and suggestions
        """
        validator = self._get_schema_validator()
        if not validator:
            return {
                "is_valid": True,  # Permissive when validator unavailable
                "errors": [],
                "warnings": ["Schema validator não disponível - validação ignorada"],
                "suggestions": [],
            }

        try:
            result = validator.validate_mappings(
                column_mappings=column_mappings,
                target_table=target_table,
                sample_data=sample_data,
            )
            return result.to_dict()

        except Exception as e:
            logger.warning(f"[NexoImportAgent] Validation failed: {e}")
            return {
                "is_valid": True,  # Permissive on error
                "errors": [],
                "warnings": [f"Validação falhou: {str(e)}"],
                "suggestions": [],
            }

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
            # FIX (January 2026): Restore AI instructions for "Outros:" answers
            ai_instructions=state.get("ai_instructions", {}),
            # FEATURE (January 2026): Restore requested new columns for dynamic schema evolution
            requested_new_columns=[
                RequestedNewColumn(
                    name=col.get("name", ""),
                    original_name=col.get("original_name", ""),
                    user_intent=col.get("user_intent", ""),
                    inferred_type=col.get("inferred_type", "TEXT"),
                    sample_values=col.get("sample_values", []),
                    source_file_column=col.get("source_file_column", ""),
                    approved=col.get("approved", False),
                )
                for col in state.get("requested_new_columns", [])
            ],
            error=state.get("error"),
            # FIX (January 2026): Restore user_id for audit trail in schema evolution
            user_id=state.get("user_id"),
            # FIX (January 2026): Restore global user feedback for AI interpretation
            global_user_feedback=state.get("global_user_feedback"),
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
            from tools.sheet_analyzer import analyze_file_smart, analysis_to_dict

            # Run analysis - smart detection handles CSV, XLSX, etc.
            session.reasoning_trace.append(ReasoningStep(
                step_type="action",
                content="Executando análise inteligente do arquivo (CSV/XLSX)",
                tool="sheet_analyzer",
            ))

            analysis = analyze_file_smart(file_content, session.filename)
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

                # =============================================================
                # Check if aggregation is needed (no quantity column detected)
                # January 2026: Feature to count identical equipment by PN
                # =============================================================
                try:
                    from tools.sheet_analyzer import detect_aggregation_need

                    # Build parsed rows from file analysis sample data
                    sample_rows = []
                    for sheet in session.file_analysis.get("sheets", []):
                        cols = [c.get("name", f"col_{i}") for i, c in enumerate(sheet.get("columns", []))]
                        samples_by_col = [c.get("sample_values", []) for c in sheet.get("columns", [])]
                        # Transpose: column samples → row dicts
                        max_samples = max((len(s) for s in samples_by_col), default=0)
                        for row_idx in range(max_samples):
                            row_dict = {}
                            for col_idx, col_name in enumerate(cols):
                                samples = samples_by_col[col_idx] if col_idx < len(samples_by_col) else []
                                row_dict[col_name] = samples[row_idx] if row_idx < len(samples) else ""
                            sample_rows.append(row_dict)

                    # Build analysis object for detect_aggregation_need
                    from tools.sheet_analyzer import WorkbookAnalysis, SheetAnalysis, ColumnAnalysis
                    from dataclasses import dataclass

                    # Create minimal analysis structure for detection
                    temp_sheets = []
                    for sheet_data in session.file_analysis.get("sheets", []):
                        temp_cols = []
                        for col_data in sheet_data.get("columns", []):
                            temp_cols.append(ColumnAnalysis(
                                name=col_data.get("name", ""),
                                suggested_mapping=col_data.get("suggested_mapping"),
                                mapping_confidence=col_data.get("mapping_confidence", 0.0),
                                data_type=col_data.get("data_type", "text"),
                                sample_values=col_data.get("sample_values", []),
                            ))
                        temp_sheets.append(SheetAnalysis(
                            name=sheet_data.get("name", ""),
                            row_count=sheet_data.get("row_count", 0),
                            column_count=len(temp_cols),
                            columns=temp_cols,
                            detected_purpose=sheet_data.get("purpose", "data"),
                            purpose_confidence=0.8,
                            has_headers=sheet_data.get("has_headers", True),
                            suggested_action="process",
                        ))

                    temp_analysis = WorkbookAnalysis(
                        filename=session.filename,
                        sheet_count=len(temp_sheets),
                        total_rows=sum(s.row_count for s in temp_sheets),
                        sheets=temp_sheets,
                        relationships=[],
                        recommended_strategy="direct",
                        questions_for_user=[],
                        reasoning_trace=[],
                    )

                    aggregation_check = detect_aggregation_need(temp_analysis, sample_rows)

                    if aggregation_check.get("needs_aggregation"):
                        session.reasoning_trace.append(ReasoningStep(
                            step_type="observation",
                            content=(
                                f"Arquivo sem coluna de quantidade. "
                                f"Detectei {len(aggregation_check.get('duplicates_sample', []))}+ "
                                f"Part Numbers repetidos em {aggregation_check['total_rows']} linhas."
                            ),
                        ))

                        # Store aggregation config in session
                        session.file_analysis["needs_aggregation"] = True
                        session.file_analysis["aggregation_config"] = {
                            "part_number_column": aggregation_check.get("part_number_column"),
                            "unique_parts": aggregation_check.get("unique_parts", 0),
                            "total_rows": aggregation_check.get("total_rows", 0),
                            "duplicates_sample": aggregation_check.get("duplicates_sample", []),
                        }

                        # Add question about aggregation strategy
                        session.questions.append(NexoQuestion(
                            id=generate_id("AGG"),
                            question="Como contar equipamentos com mesmo Part Number?",
                            context=(
                                f"O arquivo não tem coluna de quantidade. "
                                f"Encontrei {aggregation_check['total_rows']} linhas com "
                                f"{aggregation_check['unique_parts']} Part Numbers únicos. "
                                f"Alguns PNs aparecem mais de uma vez: "
                                f"{', '.join(aggregation_check.get('duplicates_sample', [])[:3])}..."
                            ),
                            options=[
                                {
                                    "value": "count_rows",
                                    "label": "Contar linhas (cada linha = 1 unidade)",
                                },
                                {
                                    "value": "use_one",
                                    "label": "Usar quantidade 1 para todos",
                                },
                            ],
                            importance="critical",
                            topic="aggregation_strategy",
                        ))

                        logger.info(
                            f"[NexoImportAgent] Aggregation needed: "
                            f"{aggregation_check['total_rows']} rows → "
                            f"{aggregation_check['unique_parts']} unique PNs"
                        )
                    else:
                        session.file_analysis["needs_aggregation"] = False
                        logger.debug(
                            f"[NexoImportAgent] No aggregation needed: "
                            f"{aggregation_check.get('reason', 'quantity exists')}"
                        )

                except Exception as agg_error:
                    # Non-critical: log but continue without aggregation
                    logger.warning(f"[NexoImportAgent] Aggregation check failed: {agg_error}")
                    session.file_analysis["needs_aggregation"] = False

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
        target_table: str = "pending_entry_items",
    ) -> str:
        """
        Build the prompt for Gemini reasoning WITH SCHEMA CONTEXT.

        This is the critical method that enables schema-aware AI reasoning.
        The PostgreSQL schema is injected so Gemini knows EXACTLY which
        columns exist in the target table.

        Args:
            session: Current import session
            prior_knowledge: Previously learned patterns
            target_table: Target PostgreSQL table (default: pending_entry_items)

        Returns:
            Prompt string with schema context
        """
        analysis = session.file_analysis

        # =================================================================
        # CRITICAL: Get schema context FIRST
        # =================================================================
        schema_context = self._get_schema_context(target_table)

        prompt = f"""Analise este arquivo de importação e sugira mapeamentos de colunas.

## ⚠️ REGRA CRÍTICA - SCHEMA POSTGRESQL

Você DEVE mapear colunas APENAS para campos que existem na tabela destino.
O schema abaixo é a FONTE DA VERDADE - NÃO invente campos que não existem.

{schema_context}

---

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

        prompt += f"""

## ⚠️ REGRAS DE MAPEAMENTO (OBRIGATÓRIO)

1. **COLUNAS VÁLIDAS**: O campo `target_field` DEVE existir na tabela `sga.{target_table}` acima
2. **ENUMS**: Para campos ENUM, use APENAS os valores listados no schema
3. **OBRIGATÓRIOS**: Campos NOT NULL DEVEM ser mapeados (exceto auto-gerados como id, created_at)
4. **TIPOS**: Respeite os tipos de dados (INTEGER para quantidade, VARCHAR para texto)
5. **SE NÃO EXISTIR**: Se uma coluna do arquivo não corresponde a nenhum campo do schema, deixe `target_field: null`

## Sua Tarefa:
1. Analise a estrutura e sugira mapeamentos APENAS para campos que existem no schema
2. Avalie a confiança geral dos mapeamentos
3. Identifique se precisa de esclarecimentos do usuário
4. Gere perguntas específicas se necessário

## Formato de Resposta (JSON OBRIGATÓRIO)
```json
{{
    "thoughts": ["Lista de pensamentos sobre a análise"],
    "observations": ["Lista de observações sobre o arquivo"],
    "confidence": 0.0 a 1.0,
    "needs_clarification": true/false,
    "questions": [{{"question": "...", "options": [...]}}],
    "suggested_mappings": {{
        "coluna_do_arquivo": "campo_do_schema_postgresql"
    }},
    "unmapped_columns": ["colunas que não correspondem a nenhum campo do schema"],
    "validation_warnings": ["avisos sobre possíveis problemas"],
    "recommendations": ["Lista de recomendações"],
    "next_action": "descrição da próxima ação"
}}
```

IMPORTANTE: Responda APENAS em JSON válido, sem markdown code blocks.
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
        user_feedback: Optional[str] = None,  # FIX (January 2026): Global user instructions
    ) -> Dict[str, Any]:
        """
        Process user answers to questions - STATELESS with RE-REASONING.

        Applies answers, re-invokes Gemini for validation, and generates
        follow-up questions if confidence is still low (multi-round Q&A).

        Args:
            session: Import session (in-memory, from frontend state)
            answers: Dict mapping question_id to answer
            user_feedback: Global user instructions for AI interpretation

        Returns:
            Updated session state with optional remaining_questions
        """
        log_agent_action(
            self.name, "submit_answers",
            entity_type="session",
            entity_id=session.session_id,
            status="started",
        )

        session.answers = answers

        # FIX (January 2026): Store global user feedback for AI interpretation
        if user_feedback:
            session.global_user_feedback = user_feedback
            session.reasoning_trace.append(ReasoningStep(
                step_type="observation",
                content=f"Feedback global do usuário: {user_feedback[:200]}..." if len(user_feedback) > 200 else f"Feedback global do usuário: {user_feedback}",
            ))

        # Track current question round (max 3 rounds)
        current_round = len([r for r in session.reasoning_trace if "Ronda" in r.content])
        max_rounds = 3

        session.reasoning_trace.append(ReasoningStep(
            step_type="observation",
            content=f"Processando respostas do usuário (Ronda {current_round + 1}/{max_rounds})",
        ))

        # Step 1: Validate answers against PostgreSQL schema BEFORE applying
        # FIX (January 2026): "Outros:" prefix indicates user INSTRUCTIONS for AI,
        # not literal column names. These must be interpreted by Gemini re-reasoning.
        provider = self._get_schema_provider()
        schema = provider.get_table_schema("pending_entry_items") if provider else None
        valid_columns = schema.get_column_names() + ["_ignore"] if schema else []

        validation_errors = []
        ai_instructions = {}  # Store "Outros:" answers for AI interpretation

        for q in session.questions:
            answer = answers.get(q.id)
            if not answer:
                continue

            # Validate column mapping answers
            if q.topic == "column_mapping" and valid_columns:
                # FIX: "Outros:" answers are AI instructions, NOT literal column names
                # Skip validation - these will be interpreted by Gemini in re-reasoning
                if answer.startswith("Outros:"):
                    ai_instructions[q.id] = {
                        "column": q.column,
                        "instruction": answer,
                        "question": q.question,
                    }
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="observation",
                        content=f"Instrução do usuário para coluna '{q.column}': {answer}",
                    ))
                    # Don't validate - let AI interpret this
                    continue

                if answer not in valid_columns:
                    validation_errors.append(
                        f"Coluna '{answer}' não existe em sga.pending_entry_items"
                    )

        # Store AI instructions in session for Gemini to process
        if ai_instructions:
            if not hasattr(session, "ai_instructions"):
                session.ai_instructions = {}
            session.ai_instructions.update(ai_instructions)

        if validation_errors:
            session.reasoning_trace.append(ReasoningStep(
                step_type="observation",
                content=f"Validação falhou: {'; '.join(validation_errors)}",
            ))
            return {
                "success": False,
                "session": session_to_dict(session),
                "validation_errors": validation_errors,
            }

        # Step 2: Apply answers to session
        # FIX: "Outros:" answers are AI instructions - don't store as literal mappings
        for q in session.questions:
            answer = answers.get(q.id)
            if not answer:
                continue

            session.reasoning_trace.append(ReasoningStep(
                step_type="observation",
                content=f"Usuário respondeu '{answer}' para: {q.question}",
            ))

            if q.topic == "column_mapping" and q.column:
                # FIX: Skip "Outros:" answers - these need AI interpretation first
                # They're stored in ai_instructions and will be processed by Gemini
                if answer.startswith("Outros:"):
                    # Mark as pending AI interpretation (placeholder)
                    session.learned_mappings[q.column] = f"__ai_pending__:{q.id}"
                else:
                    session.learned_mappings[q.column] = answer
            elif q.topic == "column_creation" and q.column:
                # FEATURE: Handle column creation decisions
                await self._handle_column_creation_answer(session, q.column, answer)
            elif q.topic == "sheet_selection":
                if session.file_analysis:
                    session.file_analysis["selected_sheets"] = answer
            elif q.topic == "movement_type":
                if session.file_analysis:
                    session.file_analysis["movement_type"] = answer
            elif q.topic == "aggregation_strategy":
                # Handle aggregation strategy answer
                if session.file_analysis:
                    session.file_analysis["aggregation_answer"] = answer
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="action",
                        content=f"Estratégia de agregação selecionada: {answer}",
                    ))
                    # FIX (January 2026): Mark quantity as aggregation-computed
                    # This ensures schema validation knows quantity will be calculated
                    if answer == "count_rows":
                        session.learned_mappings["__quantity_aggregated__"] = "quantity"
                        session.reasoning_trace.append(ReasoningStep(
                            step_type="observation",
                            content="Quantity será calculada por agregação (contagem por PN)",
                        ))
            elif q.topic == "required_field_strategy":
                # FIX (January 2026): Handle required field strategy answers
                # These are answers to questions about auto-generated fields
                if q.column == "entry_id":
                    if answer == "auto_create":
                        # Store strategy for later use in import execution
                        if not session.file_analysis:
                            session.file_analysis = {}
                        session.file_analysis["entry_id_strategy"] = "auto_create"
                        session.learned_mappings["__entry_id_auto__"] = "entry_id"
                        session.reasoning_trace.append(ReasoningStep(
                            step_type="action",
                            content="entry_id será criado automaticamente (BULK_IMPORT)",
                        ))
                    elif answer == "cancel":
                        session.stage = ImportStage.COMPLETE
                        session.error = "Importação cancelada - entry_id obrigatório"
                        return {
                            "success": False,
                            "session": session_to_dict(session),
                            "error": "Importação cancelada pelo usuário",
                        }
                elif q.column == "line_number":
                    if answer in ("auto_increment", "from_row"):
                        if not session.file_analysis:
                            session.file_analysis = {}
                        session.file_analysis["line_number_strategy"] = answer
                        session.learned_mappings["__line_number_auto__"] = "line_number"
                        session.reasoning_trace.append(ReasoningStep(
                            step_type="action",
                            content=f"line_number será gerado: {answer}",
                        ))
                elif q.column == "quantity":
                    if answer == "count_rows":
                        if not session.file_analysis:
                            session.file_analysis = {}
                        session.file_analysis["needs_aggregation"] = True
                        session.file_analysis["aggregation_answer"] = "count_rows"
                        session.learned_mappings["__quantity_aggregated__"] = "quantity"
                        session.reasoning_trace.append(ReasoningStep(
                            step_type="action",
                            content="Quantity será calculada por agregação",
                        ))
                    elif answer == "use_one":
                        if not session.file_analysis:
                            session.file_analysis = {}
                        session.file_analysis["quantity_strategy"] = "use_one"
                        session.learned_mappings["__quantity_one__"] = "quantity"
                        session.reasoning_trace.append(ReasoningStep(
                            step_type="action",
                            content="Quantity será definida como 1 para todos os itens",
                        ))
            elif q.topic == "ai_failure_handling":
                # Handle HIL decision for AI failure
                if answer == "retry":
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="action",
                        content="Usuário solicitou nova tentativa de análise",
                    ))
                    # Will trigger re-reasoning below
                elif answer == "cancel":
                    session.stage = ImportStage.COMPLETE
                    session.error = "Importação cancelada pelo usuário"
                    return {
                        "success": False,
                        "session": session_to_dict(session),
                        "error": "Importação cancelada pelo usuário",
                    }
                elif answer == "continue_manual":
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="action",
                        content="Usuário optou por continuar com mapeamentos atuais",
                    ))
                    # Skip re-reasoning, go directly to ready_for_processing
                    session.stage = ImportStage.LEARNING
                    session.updated_at = now_iso()
                    return {
                        "success": True,
                        "session": session_to_dict(session),
                        "applied_mappings": session.learned_mappings,
                        "ready_for_processing": True,
                        "re_reasoning_applied": False,
                        "manual_override": True,
                    }

        # Step 3: RE-REASON with Gemini using user answers as context
        session.reasoning_trace.append(ReasoningStep(
            step_type="thought",
            content="Vou reavaliar os mapeamentos com base nas respostas do usuário",
        ))

        re_reasoning_result = await self._re_reason_with_answers(session, answers)

        # Track that re-reasoning was applied (for frontend visibility)
        re_reasoning_failed = "error" in re_reasoning_result
        re_reasoning_applied = not re_reasoning_failed

        # FIX (January 2026): Properly handle re-reasoning failures
        # Previously the system silently continued with success: true even when AI failed
        if re_reasoning_failed:
            logger.error(
                f"[NexoImportAgent] Re-reasoning failed for session {session.session_id}: "
                f"{re_reasoning_result.get('error')}"
            )

            # Check if HIL is required due to failure
            if re_reasoning_result.get("requires_hil"):
                # Force HIL review - do NOT proceed to ready_for_processing
                session.stage = ImportStage.QUESTIONING
                session.updated_at = now_iso()

                # Generate HIL question for user decision
                hil_question = NexoQuestion(
                    id=generate_id("HIL"),
                    question="A reanálise automática falhou. Como deseja prosseguir?",
                    context=(
                        f"O sistema tentou {re_reasoning_result.get('retries_attempted', 1)} "
                        f"vezes mas não conseguiu processar suas respostas.\n"
                        f"Erro: {re_reasoning_result.get('error', 'Desconhecido')}\n\n"
                        "Os mapeamentos atuais podem estar incompletos."
                    ),
                    options=[
                        {"value": "continue_manual", "label": "Continuar com mapeamentos atuais (revisarei manualmente)"},
                        {"value": "retry", "label": "Tentar novamente"},
                        {"value": "cancel", "label": "Cancelar importação"},
                    ],
                    importance="critical",
                    topic="ai_failure_handling",
                    column=None,
                )
                session.questions = [hil_question]

                log_agent_action(
                    self.name, "submit_answers",
                    entity_type="session",
                    entity_id=session.session_id,
                    status="re_reasoning_failed",
                    details={"error": str(re_reasoning_result.get("error"))[:100]},
                )

                return {
                    "success": False,
                    "error": "re_reasoning_failed",
                    "message": "A análise com IA falhou. Revisão manual necessária.",
                    "session": session_to_dict(session),
                    "remaining_questions": [
                        {
                            "id": hil_question.id,
                            "question": hil_question.question,
                            "context": hil_question.context,
                            "options": hil_question.options,
                            "importance": hil_question.importance,
                            "topic": hil_question.topic,
                            "column": hil_question.column,
                        }
                    ],
                    "applied_mappings": session.learned_mappings,
                    "re_reasoning_applied": False,
                    "re_reasoning_error": re_reasoning_result.get("error"),
                    "confidence": session.confidence.to_dict() if session.confidence else None,
                }

        # Step 4: Check if more questions needed (multi-round Q&A)
        follow_up_questions = []
        if current_round < max_rounds - 1:  # Can still ask more
            follow_up_questions = self._generate_follow_up_questions(
                session, re_reasoning_result
            )

        if follow_up_questions:
            session.questions = follow_up_questions
            session.stage = ImportStage.QUESTIONING
            session.updated_at = now_iso()

            log_agent_action(
                self.name, "submit_answers",
                entity_type="session",
                entity_id=session.session_id,
                status="follow_up_needed",
            )

            return {
                "success": True,
                "session": session_to_dict(session),
                "remaining_questions": [
                    {
                        "id": q.id,
                        "question": q.question,
                        "context": q.context,
                        "options": q.options,
                        "importance": q.importance,
                        "topic": q.topic,
                        "column": q.column,
                    }
                    for q in follow_up_questions
                ],
                "applied_mappings": session.learned_mappings,
                "confidence": session.confidence.to_dict() if session.confidence else None,
                "re_reasoning_applied": re_reasoning_applied,
            }

        # =================================================================
        # PRE-FLIGHT VALIDATION: Validate ALL mappings BEFORE ready_for_processing
        # FIX (January 2026): Schema validation was happening TOO LATE in
        # prepare_for_processing(), causing errors after user completed Q&A.
        # Now we validate BEFORE returning ready_for_processing: true.
        # =================================================================
        session.reasoning_trace.append(ReasoningStep(
            step_type="thought",
            content="Validando mapeamentos finais contra schema PostgreSQL...",
        ))

        preflight_validation = self._validate_mappings_against_schema(
            column_mappings=session.learned_mappings,
            target_table="pending_entry_items",
        )

        preflight_errors = preflight_validation.get("errors", [])
        if preflight_errors:
            logger.info(
                f"[NexoImportAgent] Pre-flight validation found {len(preflight_errors)} issues"
            )

            # Categorize errors for different handling strategies
            invalid_columns = []  # Columns that don't exist in schema
            missing_required = []  # Required columns not mapped

            for error in preflight_errors:
                issue_type = error.get("issue_type") if isinstance(error, dict) else None
                field = error.get("field") if isinstance(error, dict) else str(error)

                if issue_type == "invalid_target":
                    # Column mapped to non-existent DB field
                    invalid_columns.append(field)
                elif issue_type == "missing_required":
                    # Required column not mapped
                    missing_required.append(field)

            # Convert invalid columns to RequestedNewColumn for column_creation questions
            for file_col in invalid_columns:
                target_col = session.learned_mappings.get(file_col, "unknown")

                # FIX: Guard against None values in learned_mappings
                # Skip special markers
                if target_col and (target_col.startswith("__") or target_col == "_ignore"):
                    continue

                # Check if already in requested_new_columns
                existing = [c for c in session.requested_new_columns
                           if c.source_file_column == file_col]
                if existing:
                    continue

                session.requested_new_columns.append(RequestedNewColumn(
                    name=self._sanitize_column_name(target_col),
                    original_name=target_col,
                    user_intent=f"Campo sugerido pelo NEXO para '{file_col}'",
                    inferred_type="TEXT",  # Default, could be improved with data analysis
                    source_file_column=file_col,
                    approved=False,
                ))

                session.reasoning_trace.append(ReasoningStep(
                    step_type="observation",
                    content=f"Coluna '{target_col}' não existe - perguntando ao usuário",
                ))

            # Generate questions for missing required fields with auto-generation strategies
            required_field_questions = self._generate_required_field_questions(
                session, missing_required
            )

            # Generate column creation questions using existing infrastructure
            column_creation_questions = self._generate_follow_up_questions(session, {})

            # Combine all questions
            all_preflight_questions = required_field_questions + column_creation_questions

            if all_preflight_questions:
                session.questions = all_preflight_questions
                session.stage = ImportStage.QUESTIONING
                session.updated_at = now_iso()

                logger.info(
                    f"[NexoImportAgent] Pre-flight validation generated "
                    f"{len(all_preflight_questions)} questions"
                )

                log_agent_action(
                    self.name, "submit_answers",
                    entity_type="session",
                    entity_id=session.session_id,
                    status="preflight_questions",
                    details={"question_count": len(all_preflight_questions)},
                )

                return {
                    "success": True,
                    "session": session_to_dict(session),
                    "remaining_questions": [
                        {
                            "id": q.id,
                            "question": q.question,
                            "context": q.context,
                            "options": q.options,
                            "importance": q.importance,
                            "topic": q.topic,
                            "column": q.column,
                        }
                        for q in all_preflight_questions
                    ],
                    "applied_mappings": session.learned_mappings,
                    "confidence": session.confidence.to_dict() if session.confidence else None,
                    "ready_for_processing": False,  # NOT ready - need answers first!
                    "re_reasoning_applied": re_reasoning_applied,
                    "preflight_validation_triggered": True,
                }

        # Pre-flight passed - log success
        session.reasoning_trace.append(ReasoningStep(
            step_type="conclusion",
            content=f"✅ Validação pré-voo OK - {preflight_validation.get('coverage_score', 0):.0f}% cobertura",
        ))

        # No more questions - ready for processing
        session.stage = ImportStage.LEARNING
        session.updated_at = now_iso()

        log_agent_action(
            self.name, "submit_answers",
            entity_type="session",
            entity_id=session.session_id,
            status="completed",
        )

        # Build aggregation config if applicable
        aggregation_config = None
        if session.file_analysis and session.file_analysis.get("needs_aggregation"):
            agg_answer = session.file_analysis.get("aggregation_answer", "count_rows")
            agg_cfg = session.file_analysis.get("aggregation_config", {})

            if agg_answer == "count_rows":
                aggregation_config = {
                    "enabled": True,
                    "strategy": "count_rows",
                    "part_number_column": agg_cfg.get("part_number_column"),
                    "merge_strategy": "first",
                    "unique_parts": agg_cfg.get("unique_parts", 0),
                    "total_rows": agg_cfg.get("total_rows", 0),
                }

                session.reasoning_trace.append(ReasoningStep(
                    step_type="action",
                    content=(
                        f"Agregação ativada: {agg_cfg.get('total_rows', 0)} linhas → "
                        f"{agg_cfg.get('unique_parts', 0)} Part Numbers únicos"
                    ),
                ))
            else:
                aggregation_config = {
                    "enabled": False,
                    "strategy": agg_answer,
                }

        return {
            "success": True,
            "session": session_to_dict(session),
            "applied_mappings": session.learned_mappings,
            "confidence": session.confidence.to_dict() if session.confidence else None,
            "ready_for_processing": True,
            "re_reasoning_applied": re_reasoning_applied,
            "aggregation": aggregation_config,
        }

    async def _handle_column_creation_answer(
        self,
        session: ImportSession,
        file_column: str,
        answer: str,
    ) -> None:
        """
        Handle user's answer to column creation question.

        Possible answers:
        - "create:{column_name}:{column_type}" - Admin approved creating new column
        - "metadata" - Store in JSONB metadata column
        - "map_existing" - User wants to map to existing column (generates follow-up)
        - "_ignore" - Ignore this column
        - Existing column name - Direct mapping to existing column

        IMPORTANT: When user approves column creation, this method calls the
        Schema Evolution Agent (SEA) via MCP Gateway to actually create the column
        in PostgreSQL with advisory locking for concurrency safety.

        Args:
            session: Current import session
            file_column: Column name from import file
            answer: User's answer value
        """
        # Find the RequestedNewColumn for this file_column
        target_new_col = None
        for new_col in session.requested_new_columns:
            if new_col.source_file_column == file_column:
                target_new_col = new_col
                break

        # FIX: Guard against None answer parameter
        if answer and answer.startswith("create:"):
            # Admin approved column creation - call SEA to create via MCP
            parts = answer.split(":", 2)
            column_name = parts[1] if len(parts) > 1 else ""
            column_type = parts[2] if len(parts) > 2 else "TEXT"

            session.reasoning_trace.append(ReasoningStep(
                step_type="action",
                content=f"Criando campo '{column_name}' ({column_type}) via Schema Evolution Agent",
                tool="SchemaEvolutionAgent",
            ))

            # Get sample values from RequestedNewColumn if available
            sample_values = target_new_col.sample_values if target_new_col else None

            # Lazy import SEA to minimize cold start impact
            from agents.schema_evolution_agent import create_schema_evolution_agent

            sea = create_schema_evolution_agent()
            result = await sea.create_column(
                table_name="pending_entry_items",
                column_name=column_name,
                column_type=column_type,
                requested_by=session.user_id or "unknown",
                original_csv_column=file_column,
                sample_values=sample_values,
            )

            if result.success:
                if result.created:
                    # New column was created successfully
                    session.learned_mappings[file_column] = result.column_name
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="observation",
                        content=(
                            f"✅ Campo '{result.column_name}' criado com sucesso "
                            f"({result.column_type})"
                        ),
                    ))
                else:
                    # Column already existed (race condition handled gracefully)
                    session.learned_mappings[file_column] = result.column_name
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="observation",
                        content=f"ℹ️ Campo '{result.column_name}' já existe, usando existente",
                    ))

                # Mark as approved regardless
                if target_new_col:
                    target_new_col.approved = True
            else:
                # Failed - use metadata fallback
                session.learned_mappings[file_column] = "__metadata__"
                session.reasoning_trace.append(ReasoningStep(
                    step_type="observation",
                    content=(
                        f"⚠️ Criação falhou: {result.reason}. "
                        f"Usando metadata JSONB como fallback."
                    ),
                ))
                logger.warning(
                    f"[NexoImportAgent] Column creation failed for '{column_name}': "
                    f"{result.error} - {result.reason}"
                )
                # FIX: Mark as approved even on failure to prevent question from repeating
                # (User already decided, just the implementation failed)
                if target_new_col:
                    target_new_col.approved = True

        elif answer == "metadata":
            # Store in JSONB metadata column
            session.reasoning_trace.append(ReasoningStep(
                step_type="observation",
                content=f"Coluna '{file_column}' será armazenada em metadata (JSONB)",
            ))
            session.learned_mappings[file_column] = "__metadata__"
            # FIX: Mark as approved to prevent question from repeating
            if target_new_col:
                target_new_col.approved = True

        elif answer == "_ignore":
            # Ignore this column
            session.reasoning_trace.append(ReasoningStep(
                step_type="observation",
                content=f"Coluna '{file_column}' será ignorada",
            ))
            session.learned_mappings[file_column] = "_ignore"
            # FIX: Mark as approved to prevent question from repeating
            if target_new_col:
                target_new_col.approved = True

        elif answer == "map_existing":
            # User wants to select from existing columns - needs follow-up question
            session.reasoning_trace.append(ReasoningStep(
                step_type="thought",
                content=f"Usuário quer mapear '{file_column}' para campo existente - aguardando seleção",
            ))
            # Keep as pending - will generate follow-up question
            session.learned_mappings[file_column] = f"__map_existing__:{file_column}"

        else:
            # Direct mapping to an existing column
            session.reasoning_trace.append(ReasoningStep(
                step_type="observation",
                content=f"Mapeando '{file_column}' → '{answer}'",
            ))
            session.learned_mappings[file_column] = answer
            # FIX: Mark as approved to prevent question from repeating
            if target_new_col:
                target_new_col.approved = True

    async def _re_reason_with_answers(
        self,
        session: ImportSession,
        user_answers: Dict[str, str],
        max_retries: int = 3,
        initial_delay: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Re-analyze mappings WITH user answer context using Gemini.

        This is the critical RE-THINK phase. Includes retry logic with
        exponential backoff for transient failures.

        FIX (January 2026): Added retry logic and proper error handling.
        System no longer silently fails - requires HIL when retries exhausted.

        Args:
            session: Current import session
            user_answers: User's answers to questions
            max_retries: Maximum retry attempts (default: 3)
            initial_delay: Initial delay in seconds (doubles each retry)

        Returns:
            Re-reasoning result with updated confidence.
            On failure after retries: {"error": str, "retries_attempted": int, "requires_hil": True}
        """
        import asyncio

        session.reasoning_trace.append(ReasoningStep(
            step_type="action",
            content="Invocando IA para reavaliar com respostas do usuário",
            tool="gemini",
        ))

        last_error = None
        delay = initial_delay

        for attempt in range(max_retries):
            try:
                # Build re-reasoning prompt
                prompt = self._build_re_reasoning_prompt(session, user_answers)

                # Invoke Gemini
                response = await self.invoke(prompt)

                # Parse response
                result = parse_json_safe(response)

                # Validate JSON response - if parse failed, retry
                if "error" in result:
                    raise ValueError(f"Gemini returned invalid JSON: {result.get('error')}")

                # Validate required fields
                if not isinstance(result.get("confidence"), (int, float)):
                    raise ValueError("Invalid response: missing confidence score")

                # SUCCESS - process the result
                new_confidence = result.get("confidence", 0.7)
                session.confidence = self.calculate_confidence(
                    extraction_quality=new_confidence,
                    evidence_strength=0.85,  # Higher after user input
                    historical_match=0.7,
                )

                # Capture AI's reasoning
                thoughts = result.get("thoughts", [])
                for thought in thoughts:
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="thought",
                        content=thought,
                    ))

                # Update mappings if Gemini suggests changes
                suggested = result.get("refined_mappings", {})
                if isinstance(suggested, dict):
                    session.learned_mappings.update(suggested)

                # =============================================================
                # FIX (January 2026): PRIORITY INVERSION BUG
                # Process requested_new_columns BEFORE interpreted_instructions!
                #
                # When Gemini returns BOTH for the same column:
                # - interpreted_instructions: {"COL": "existing_field"}
                # - requested_new_columns: [{source_file_column: "COL", ...}]
                #
                # The user's intent to CREATE a new field must take priority.
                # Otherwise, interpreted_instructions overwrites learned_mappings
                # and requested_new_columns gets skipped due to "final mapping" check.
                # =============================================================

                # STEP 1: Process requested new columns FIRST (dynamic schema evolution)
                # This ensures user's intent to create new fields is respected
                requested_cols = result.get("requested_new_columns", [])
                new_column_sources = set()  # Track columns marked for creation
                if isinstance(requested_cols, list) and requested_cols:
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="observation",
                        content=f"Detectado {len(requested_cols)} campo(s) que não existem no schema",
                    ))

                    # Build lookup of existing requested columns by source_file_column
                    existing_cols_by_source = {
                        col.source_file_column: col
                        for col in session.requested_new_columns
                        if col.source_file_column
                    }

                    for col_info in requested_cols:
                        if isinstance(col_info, dict):
                            source_col = col_info.get("source_file_column", "")

                            # Skip if this column was already processed in previous rounds
                            if source_col and source_col in existing_cols_by_source:
                                existing = existing_cols_by_source[source_col]
                                if existing.approved:
                                    logger.debug(
                                        f"[NexoImportAgent] Skipping already-approved column: {source_col}"
                                    )
                                    continue
                                else:
                                    logger.debug(
                                        f"[NexoImportAgent] Skipping duplicate pending column: {source_col}"
                                    )
                                    continue

                            new_col = RequestedNewColumn(
                                name=self._sanitize_column_name(col_info.get("name", "")),
                                original_name=col_info.get("original_name", col_info.get("name", "")),
                                user_intent=col_info.get("user_intent", ""),
                                inferred_type=col_info.get("inferred_type", "TEXT"),
                                source_file_column=source_col,
                            )
                            session.requested_new_columns.append(new_col)
                            existing_cols_by_source[source_col] = new_col

                            session.reasoning_trace.append(ReasoningStep(
                                step_type="thought",
                                content=f"Usuário quer campo '{new_col.name}' ({new_col.inferred_type}): {new_col.user_intent}",
                            ))

                            # Mark as pending column creation decision
                            if new_col.source_file_column:
                                session.learned_mappings[new_col.source_file_column] = f"__new_column__:{new_col.name}"
                                new_column_sources.add(new_col.source_file_column)

                # STEP 2: Process interpreted instructions from "Outros:" answers
                # BUT skip columns already marked for new field creation
                interpreted = result.get("interpreted_instructions", {})
                if isinstance(interpreted, dict) and interpreted:
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="action",
                        content=f"Interpretando {len(interpreted)} instruções do usuário",
                    ))
                    for file_col, db_col in interpreted.items():
                        # Skip None/empty values from Gemini response
                        if not db_col:
                            logger.debug(
                                f"[NexoImportAgent] Skipping None/empty interpretation for: {file_col}"
                            )
                            continue

                        # FIX: Skip if this column was marked for NEW FIELD creation
                        # User's intent to create new field takes priority over mapping to existing
                        if file_col in new_column_sources:
                            logger.debug(
                                f"[NexoImportAgent] Skipping interpreted_instruction for '{file_col}' - "
                                f"column marked for new field creation (priority: requested_new_columns)"
                            )
                            continue

                        # Replace __ai_pending__ placeholders with actual interpretations
                        if file_col in session.learned_mappings:
                            old_value = session.learned_mappings[file_col]
                            # Guard against None values in learned_mappings
                            if old_value and old_value.startswith("__ai_pending__"):
                                session.learned_mappings[file_col] = db_col
                                session.reasoning_trace.append(ReasoningStep(
                                    step_type="observation",
                                    content=f"Interpretado: '{file_col}' → '{db_col}'",
                                ))

                session.reasoning_trace.append(ReasoningStep(
                    step_type="conclusion",
                    content=f"Reanálise completa. Confiança: {new_confidence:.0%}",
                ))

                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[NexoImportAgent] Re-reasoning attempt {attempt + 1}/{max_retries} failed: {e}"
                )

                session.reasoning_trace.append(ReasoningStep(
                    step_type="observation",
                    content=f"Tentativa {attempt + 1}/{max_retries} falhou: {str(e)}",
                ))

                if attempt < max_retries - 1:
                    # Exponential backoff before retry
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="action",
                        content=f"Aguardando {delay:.1f}s antes de tentar novamente...",
                    ))
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff

        # All retries failed - degrade confidence and require HIL
        logger.error(
            f"[NexoImportAgent] Re-reasoning failed after {max_retries} attempts: {last_error}"
        )

        session.reasoning_trace.append(ReasoningStep(
            step_type="conclusion",
            content=f"Reanálise falhou após {max_retries} tentativas. Revisão manual obrigatória.",
        ))

        # Degrade confidence significantly when AI fails
        session.confidence = self.calculate_confidence(
            extraction_quality=0.3,  # Very low due to AI failure
            evidence_strength=0.5,
            historical_match=0.5,
        )
        session.confidence.requires_hil = True  # Force HIL review

        return {
            "error": str(last_error),
            "retries_attempted": max_retries,
            "requires_hil": True,
            "confidence_degraded": True,
        }

    def _build_re_reasoning_prompt(
        self,
        session: ImportSession,
        user_answers: Dict[str, str],
        target_table: str = "pending_entry_items",
    ) -> str:
        """
        Build prompt for Gemini re-reasoning WITH user answers context.

        This prompt includes the user's clarifications so Gemini can
        refine its understanding and improve confidence.

        FIX (January 2026): Now includes AI instructions from "Outros:" answers
        for Gemini to interpret and extract actual column mappings.
        """
        schema_context = self._get_schema_context(target_table)

        # Format user answers for context
        answers_context = "\n".join([
            f"- Pergunta: {q.question}\n  Resposta: {user_answers.get(q.id, 'Não respondida')}"
            for q in session.questions
            if q.id in user_answers
        ])

        # Format current mappings (excluding __ai_pending__ placeholders)
        # FIX: Guard against None values in learned_mappings
        mappings_context = "\n".join([
            f"- {col} → {target}"
            for col, target in session.learned_mappings.items()
            if target and not target.startswith("__ai_pending__")
        ])

        # FIX: Format AI instructions that need Gemini interpretation
        ai_instructions = getattr(session, "ai_instructions", {})
        ai_instructions_context = ""
        if ai_instructions:
            ai_instructions_context = "\n## INSTRUÇÕES DO USUÁRIO PARA INTERPRETAR\n"
            ai_instructions_context += "O usuário selecionou 'Outros' para estas colunas e forneceu explicações:\n\n"
            for q_id, info in ai_instructions.items():
                ai_instructions_context += f"- Coluna do arquivo: '{info.get('column', 'unknown')}'\n"
                ai_instructions_context += f"  Instrução do usuário: {info.get('instruction', '')}\n"
                ai_instructions_context += f"  Pergunta original: {info.get('question', '')}\n\n"
            ai_instructions_context += """
TAREFA CRÍTICA: Você DEVE interpretar cada instrução acima e determinar:
1. Qual coluna do schema PostgreSQL corresponde à intenção do usuário
2. Se o usuário mencionou múltiplos campos (ex: "Cliente e localidade"), mapeie para o campo principal
3. SE O USUÁRIO QUER UM CAMPO QUE NÃO EXISTE NO SCHEMA:
   - Retorne em "requested_new_columns" com o nome sugerido e tipo inferido
   - NÃO use "_ignore" se o usuário explicitamente quer salvar esse dado

Exemplos de interpretação:
- "import isto como ticket_flux" → SE ticket_flux EXISTE: mapear. SE NÃO EXISTE: requested_new_columns
- "colocado no campo Cliente" → mapear para "client_code" ou similar
- "numero da Nota Fiscal" → mapear para "nf_number" ou similar
- "deve ser de status" → mapear para "status" (se existir no schema)
- "este é o numero do chamado no ServiceNow" → SE não existe: requested_new_columns com nome sugerido
"""

        prompt = f"""Você é NEXO reanalisando um arquivo de importação COM as respostas do usuário.

## SCHEMA POSTGRESQL (FONTE DA VERDADE)
{schema_context}

## ANÁLISE ANTERIOR DO ARQUIVO
- Arquivo: {session.filename}
- Colunas detectadas: {len(session.file_analysis.get('sheets', [{}])[0].get('columns', []))}

## MAPEAMENTOS JÁ CONFIRMADOS
{mappings_context if mappings_context else "(nenhum mapeamento confirmado ainda)"}

## RESPOSTAS DO USUÁRIO (NOVAS INFORMAÇÕES)
{answers_context if answers_context else "(nenhuma resposta)"}
{ai_instructions_context}
{self._format_global_feedback(session)}
## SUA TAREFA

Com base nas respostas do usuário:
1. INTERPRETE as instruções "Outros:" e determine a coluna PostgreSQL correta
2. REFINE os mapeamentos se necessário
3. VALIDE que todos os mapeamentos usam colunas do schema acima
4. CALCULE uma nova confiança (0.0 a 1.0)
5. IDENTIFIQUE se ainda há dúvidas que precisam de mais perguntas

## FORMATO DE RESPOSTA (JSON)
```json
{{
    "thoughts": ["Seu raciocínio sobre as respostas e interpretações..."],
    "refined_mappings": {{"coluna_arquivo": "coluna_db"}},
    "interpreted_instructions": {{"coluna_arquivo": "coluna_db_interpretada"}},
    "requested_new_columns": [
        {{
            "name": "nome_snake_case_sugerido",
            "original_name": "nome_que_usuario_pediu",
            "user_intent": "explicação do que o usuário quer armazenar",
            "inferred_type": "TEXT ou INTEGER ou TIMESTAMP etc",
            "source_file_column": "nome_da_coluna_no_arquivo"
        }}
    ],
    "confidence": 0.85,
    "needs_more_questions": false,
    "uncertain_fields": []
}}
```

IMPORTANTE:
- SOMENTE use colunas que existem no schema PostgreSQL em "refined_mappings" e "interpreted_instructions"
- Para instruções "Outros:", extraia a INTENÇÃO do usuário
- SE o usuário pede um campo que NÃO EXISTE no schema:
  * Adicione em "requested_new_columns" com nome em snake_case e tipo inferido
  * NÃO mapeie para "_ignore" se o usuário explicitamente quer salvar o dado
  * O sistema vai perguntar ao usuário se quer criar esse campo
- Se não tiver certeza sobre um campo existente, inclua em "uncertain_fields"
"""
        return prompt

    def _format_global_feedback(self, session: ImportSession) -> str:
        """
        Format global user feedback for inclusion in Gemini prompt.

        FIX (January 2026): Users can provide global instructions in the feedback
        textarea. These instructions apply to the ENTIRE import, not just a single column.

        Examples of global feedback:
        - "Este arquivo não existe coluna de quantidade, conte quantos equipamentos identicos"
        - "Ignore as linhas com status 'Cancelado'"
        - "Este é um arquivo de entrada de equipamentos novos"
        """
        global_feedback = getattr(session, "global_user_feedback", None)
        if not global_feedback:
            return ""

        return f"""
## INSTRUÇÕES GLOBAIS DO USUÁRIO (CRÍTICO - LEIA COM ATENÇÃO)

O usuário forneceu as seguintes instruções gerais para esta importação:

\"\"\"{global_feedback}\"\"\"

VOCÊ DEVE:
1. Interpretar essas instruções e aplicá-las à análise
2. Se o usuário menciona estratégias de quantidade (contar duplicatas, usar 1, etc), reflita isso nos mapeamentos
3. Se o usuário menciona filtros ou exclusões, anote em "notes" para o executor
4. Se o usuário menciona campos específicos, use essa informação para refinar mapeamentos
5. Se o usuário menciona Nota Fiscal, identifique qual coluna é o número da NF

"""

    def _generate_follow_up_questions(
        self,
        session: ImportSession,
        re_reasoning_result: Dict[str, Any],
    ) -> List[NexoQuestion]:
        """
        Generate follow-up questions based on re-reasoning result.

        Generates questions for:
        1. COLUMN CREATION: User requested fields that don't exist in schema (CRITICAL)
        2. UNCERTAIN FIELDS: Low confidence mappings that need clarification

        Args:
            session: Current import session
            re_reasoning_result: Result from _re_reason_with_answers()

        Returns:
            List of follow-up questions (empty if none needed)
        """
        questions = []

        # =====================================================================
        # PRIORITY 1: Column Creation Questions (Dynamic Schema Evolution)
        # These are CRITICAL - user explicitly requested non-existent fields
        # =====================================================================
        if session.requested_new_columns:
            provider = self._get_schema_provider()
            schema = provider.get_table_schema("pending_entry_items") if provider else None
            existing_options = self._build_schema_aware_options(schema) if schema else []

            # FIX (January 2026): Build set of columns already answered to avoid re-asking
            answered_columns = set()
            for q in session.questions:
                if q.topic == "column_creation" and q.column and q.id in session.answers:
                    answered_columns.add(q.column)
                    logger.debug(f"[NexoImportAgent] Column already answered: {q.column}")

            for new_col in session.requested_new_columns:
                if new_col.approved:
                    logger.debug(f"[NexoImportAgent] Skipping approved column: {new_col.source_file_column}")
                    continue  # Already approved in previous round

                # FIX: Defense-in-depth - also check if this column was answered
                if new_col.source_file_column in answered_columns:
                    logger.debug(
                        f"[NexoImportAgent] Skipping already-answered column: {new_col.source_file_column}"
                    )
                    continue

                if new_col.source_file_column in session.learned_mappings:
                    # FIX (January 2026): Check if it's a FINAL decision or just a pending marker
                    mapping_value = session.learned_mappings[new_col.source_file_column]
                    # FIX: Guard against None values in learned_mappings
                    # __new_column__: markers are PENDING, not final - still need approval!
                    # Only skip if it's a real column, _ignore, __metadata__, or __create_column__
                    if mapping_value and not mapping_value.startswith("__new_column__:"):
                        logger.debug(
                            f"[NexoImportAgent] Skipping column with final mapping: "
                            f"{new_col.source_file_column} → {mapping_value}"
                        )
                        continue  # Already decided (ignored, metadata, or mapped)

                # Build options for column creation question
                options = [
                    {
                        "value": f"create:{new_col.name}:{new_col.inferred_type}",
                        "label": f"✅ Criar campo '{new_col.name}' ({new_col.inferred_type})",
                    },
                    {
                        "value": "metadata",
                        "label": "📦 Armazenar em metadata (JSONB)",
                    },
                    {
                        "value": "_ignore",
                        "label": "❌ Ignorar esta coluna",
                    },
                ]

                # Add "map to existing" option with schema-aware options
                if existing_options:
                    options.insert(2, {
                        "value": "map_existing",
                        "label": "🔄 Mapear para campo existente",
                    })

                questions.append(NexoQuestion(
                    id=generate_id("CC"),  # CC = Column Creation
                    question=f"O campo '{new_col.original_name}' não existe no banco de dados. O que deseja fazer?",
                    context=(
                        f"Sua intenção: {new_col.user_intent}\n"
                        f"Nome sugerido: {new_col.name}\n"
                        f"Tipo de dado: {new_col.inferred_type}\n\n"
                        "⚠️ NOTA: Criar novos campos requer permissão de administrador."
                    ),
                    options=options,
                    importance="critical",
                    topic="column_creation",
                    column=new_col.source_file_column,
                ))

            # If we have column creation questions, return them first
            if questions:
                return questions

        # =====================================================================
        # PRIORITY 2: Uncertain Fields (only if no column creation pending)
        # =====================================================================

        # Check if Gemini explicitly said more questions needed
        if not re_reasoning_result.get("needs_more_questions", False):
            return questions

        # Check confidence threshold
        if session.confidence and session.confidence.overall >= 0.8:
            return questions

        # Get uncertain fields from Gemini response
        uncertain_fields = re_reasoning_result.get("uncertain_fields", [])
        if not uncertain_fields:
            return questions

        # Generate schema-aware questions for uncertain fields
        provider = self._get_schema_provider()
        schema = provider.get_table_schema("pending_entry_items") if provider else None

        for field_info in uncertain_fields[:2]:  # Max 2 follow-up questions
            field_name = field_info if isinstance(field_info, str) else field_info.get("name", "")
            if not field_name:
                continue

            # Build schema-aware options
            options = self._build_schema_aware_options(schema)

            questions.append(NexoQuestion(
                id=generate_id("FQ"),  # FQ = Follow-up Question
                question=f"Confirmação: qual é o campo correto para '{field_name}'?",
                context="O NEXO ainda não tem certeza sobre este mapeamento após a reanálise.",
                options=options,
                importance="high",
                topic="column_mapping",
                column=field_name,
            ))

        return questions

    def _generate_required_field_questions(
        self,
        session: ImportSession,
        missing_required: List[str],
    ) -> List[NexoQuestion]:
        """
        Generate questions for missing required fields with auto-generation strategies.

        Required fields in pending_entry_items that are NOT in the CSV need special handling:
        - entry_id: Create parent pending_entries record, use its UUID
        - line_number: Auto-increment based on row order
        - quantity: Calculate from aggregation OR ask user

        FIX (January 2026): Previously these errors only appeared at prepare_for_processing,
        too late for user to provide input. Now we ask BEFORE ready_for_processing.

        Args:
            session: Current import session
            missing_required: List of required field names that are not mapped

        Returns:
            List of NexoQuestion objects for required field handling
        """
        questions = []

        # Track which required fields we've already asked about
        answered_required = set()
        for q in session.questions:
            if q.topic == "required_field_strategy" and q.column and q.id in session.answers:
                answered_required.add(q.column)

        for field_name in missing_required:
            # Skip if already answered
            if field_name in answered_required:
                continue

            # Skip auto-generated fields that are handled automatically
            auto_handled = {"created_at", "updated_at", "entry_item_id"}
            if field_name in auto_handled:
                continue

            # Generate question based on field type
            if field_name == "entry_id":
                questions.append(NexoQuestion(
                    id=generate_id("RQ"),  # RQ = Required field Question
                    question="Como criar o registro pai (pending_entries)?",
                    context=(
                        "O campo 'entry_id' é obrigatório e referencia um registro pai.\n"
                        "Para importar itens, precisamos primeiro criar uma entrada principal "
                        "(pending_entries) com informações do documento/lote."
                    ),
                    options=[
                        {
                            "value": "auto_create",
                            "label": "✅ Criar automaticamente (BULK_IMPORT)",
                        },
                        {
                            "value": "use_existing",
                            "label": "🔗 Usar entrada existente (informar ID)",
                        },
                        {
                            "value": "cancel",
                            "label": "❌ Cancelar importação",
                        },
                    ],
                    importance="critical",
                    topic="required_field_strategy",
                    column=field_name,
                ))

            elif field_name == "line_number":
                questions.append(NexoQuestion(
                    id=generate_id("RQ"),
                    question="Como numerar as linhas do documento?",
                    context=(
                        "O campo 'line_number' é obrigatório para identificar cada item.\n"
                        "Como o arquivo não tem uma coluna para isso, precisamos gerar."
                    ),
                    options=[
                        {
                            "value": "auto_increment",
                            "label": "✅ Numerar automaticamente (1, 2, 3...)",
                        },
                        {
                            "value": "from_row",
                            "label": "📊 Usar número da linha do arquivo",
                        },
                    ],
                    importance="high",
                    topic="required_field_strategy",
                    column=field_name,
                ))

            elif field_name == "quantity":
                # Check if aggregation is already configured
                has_aggregation = (
                    session.file_analysis and
                    session.file_analysis.get("needs_aggregation") and
                    session.file_analysis.get("aggregation_answer")
                )

                if has_aggregation:
                    # Aggregation is configured but quantity not mapped - this is a bug
                    # Mark it for auto-handling based on aggregation answer
                    session.reasoning_trace.append(ReasoningStep(
                        step_type="observation",
                        content=(
                            "Agregação configurada mas quantity não mapeada - "
                            "será calculada automaticamente"
                        ),
                    ))
                    # Add synthetic mapping marker for quantity
                    session.learned_mappings["__quantity_aggregated__"] = "quantity"
                    continue  # Don't generate question

                # No aggregation - need to ask
                questions.append(NexoQuestion(
                    id=generate_id("RQ"),
                    question="O arquivo não tem coluna de quantidade. Como definir?",
                    context=(
                        "O campo 'quantity' é obrigatório mas não foi mapeado.\n"
                        "Precisamos saber como determinar a quantidade de cada item."
                    ),
                    options=[
                        {
                            "value": "count_rows",
                            "label": "📊 Contar linhas por Part Number (agregação)",
                        },
                        {
                            "value": "use_one",
                            "label": "1️⃣ Usar quantidade 1 para todos",
                        },
                        {
                            "value": "from_column",
                            "label": "📝 Mapear de outra coluna (especificar)",
                        },
                    ],
                    importance="critical",
                    topic="required_field_strategy",
                    column=field_name,
                ))

            else:
                # Generic required field question
                questions.append(NexoQuestion(
                    id=generate_id("RQ"),
                    question=f"O campo obrigatório '{field_name}' não está mapeado. Como proceder?",
                    context=(
                        f"O campo '{field_name}' é NOT NULL no banco de dados.\n"
                        "Precisamos de um valor para cada registro."
                    ),
                    options=[
                        {
                            "value": "default_empty",
                            "label": "📝 Usar valor padrão vazio",
                        },
                        {
                            "value": "from_column",
                            "label": "🔄 Mapear de outra coluna",
                        },
                        {
                            "value": "_ignore",
                            "label": "❌ Ignorar (pode causar erros)",
                        },
                    ],
                    importance="high",
                    topic="required_field_strategy",
                    column=field_name,
                ))

        return questions

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
            # Pass parameters matching create_episode() signature
            episode_result = await learning_agent.create_episode(
                user_id=user_id,
                filename=session.filename,
                file_analysis=session.file_analysis or {},
                column_mappings=session.learned_mappings,
                user_corrections=user_corrections or {},
                import_result=import_result,
                target_table="pending_entry_items",
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
        file_analysis: Optional[Dict[str, Any]] = None,
        user_id: str = "anonymous",
    ) -> Dict[str, Any]:
        """
        Retrieve prior knowledge before analysis (RECALL phase).

        Queries LearningAgent for similar past imports to provide
        context and suggested mappings before AI reasoning.

        NOTE: file_analysis is OPTIONAL. When not provided (e.g., before
        file has been analyzed), we match by filename pattern alone.
        Full signature matching happens after analysis.

        Args:
            filename: Name of file being imported
            file_analysis: Initial file analysis (optional - can be None)
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

            # Handle case where file_analysis is not yet available
            # (frontend calls this before analysis is complete)
            if file_analysis is None:
                file_analysis = {}  # Use empty dict for safe .get() calls

            # Build context for retrieval
            # Note: Can match by filename pattern alone if no analysis available
            context = {
                "filename": filename,
                "filename_pattern": self._extract_filename_pattern(filename),
                "file_type": self._detect_file_type(filename),
                "file_signature": self._compute_file_signature(file_analysis) if file_analysis else "",
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
        target_table: str = "pending_entry_items",
    ) -> Dict[str, Any]:
        """
        Prepare final configuration for import processing (ACT phase) - STATELESS.

        NOW WITH SCHEMA VALIDATION: Validates all mappings against PostgreSQL
        schema before allowing import to proceed. This catches invalid columns
        BEFORE they hit the database.

        Args:
            session: Import session (in-memory, from frontend state)
            target_table: Target PostgreSQL table

        Returns:
            Processing configuration with updated session state
        """
        session.reasoning_trace.append(ReasoningStep(
            step_type="thought",
            content="Preparando configuração final para processamento",
        ))

        # =================================================================
        # AUTO-MAPPINGS: Add system-generated column mappings
        # These columns are NOT required from the file - they're auto-generated
        # =================================================================
        # FIX (January 2026): Required columns were failing validation because
        # they weren't mapped, but they should be auto-generated during import
        auto_mappings_added = []

        # line_number - Auto-incremented during import (1, 2, 3, ...)
        if "line_number" not in session.learned_mappings.values():
            session.learned_mappings["__line_number_auto__"] = "line_number"
            auto_mappings_added.append("line_number (auto-increment)")

        # entry_id - Auto-created with parent BULK_IMPORT entry record
        if "entry_id" not in session.learned_mappings.values():
            session.learned_mappings["__entry_id_auto__"] = "entry_id"
            auto_mappings_added.append("entry_id (auto-create)")

        # quantity - Default to 1 if not mapped from file
        if "quantity" not in session.learned_mappings.values():
            session.learned_mappings["__quantity_one__"] = "quantity"
            auto_mappings_added.append("quantity (default: 1)")

        if auto_mappings_added:
            session.reasoning_trace.append(ReasoningStep(
                step_type="observation",
                content=f"Auto-mapeamentos adicionados: {', '.join(auto_mappings_added)}",
            ))
            logger.debug(f"[NexoImportAgent] Added auto-mappings: {auto_mappings_added}")

        # =================================================================
        # CRITICAL: VALIDATE mappings against schema BEFORE processing
        # =================================================================
        session.reasoning_trace.append(ReasoningStep(
            step_type="action",
            content=f"Validando mapeamentos contra schema sga.{target_table}...",
            tool="schema_validator",
        ))

        validation_result = self._validate_mappings_against_schema(
            column_mappings=session.learned_mappings,
            target_table=target_table,
        )

        # Check for validation errors
        if not validation_result.get("is_valid", True):
            errors = validation_result.get("errors", [])
            error_messages = [
                e.get("message", str(e)) if isinstance(e, dict) else str(e)
                for e in errors
            ]

            session.reasoning_trace.append(ReasoningStep(
                step_type="error",
                content=f"❌ Validação falhou: {'; '.join(error_messages[:3])}",
            ))

            return {
                "success": False,
                "ready": False,
                "error": "Mapeamentos inválidos contra schema PostgreSQL",
                "validation_errors": errors,
                "validation_warnings": validation_result.get("warnings", []),
                "suggestions": validation_result.get("suggestions", []),
                "session": session_to_dict(session),
            }

        # Log warnings and suggestions
        warnings = validation_result.get("warnings", [])
        if warnings:
            for warn in warnings[:3]:
                warn_msg = warn.get("message", str(warn)) if isinstance(warn, dict) else str(warn)
                session.reasoning_trace.append(ReasoningStep(
                    step_type="observation",
                    content=f"⚠️ Aviso: {warn_msg}",
                ))

        session.reasoning_trace.append(ReasoningStep(
            step_type="conclusion",
            content=f"✅ Validação OK - {validation_result.get('coverage_score', 0):.0f}% cobertura",
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
            # FIX: Validate values before storing to prevent None in learned_mappings
            for col, mapping_info in suggested_mappings.items():
                if isinstance(mapping_info, dict):
                    value = mapping_info.get("field", "")
                    if value:  # Only store non-empty values
                        session.learned_mappings[col] = value
                elif mapping_info:  # Only store non-None values
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

    def _build_schema_aware_options(
        self,
        schema,
        include_ignore: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Build column options dynamically from PostgreSQL schema.

        This replaces the hardcoded column list with actual database columns.

        Args:
            schema: TableSchema from SchemaProvider
            include_ignore: Whether to include "Ignorar" option

        Returns:
            List of option dictionaries with label and value
        """
        # Human-readable labels for common columns
        column_labels = {
            "part_number": "Part Number / SKU",
            "quantity": "Quantidade",
            "serial_number": "Número de Série",
            "serial_numbers": "Lista de Números de Série",
            "location_code": "Código da Localização",
            "destination_location_id": "Destino",
            "source_location_id": "Origem",
            "project_code": "Código do Projeto",
            "project_id": "Projeto",
            "nf_number": "Número da NF",
            "nf_date": "Data da NF",
            "nf_key": "Chave da NF",
            "supplier_name": "Fornecedor",
            "supplier_cnpj": "CNPJ do Fornecedor",
            "description": "Descrição",
            "unit_value": "Valor Unitário",
            "total_value": "Valor Total",
            "movement_type": "Tipo de Movimento",
            "reason": "Motivo/Observação",
            "purchase_date": "Data de Compra",
            "condition": "Condição do Item",
            "manufacturer": "Fabricante",
            "model": "Modelo",
            "category": "Categoria",
        }

        options = []

        if schema:
            # Use actual schema columns
            for col in schema.columns:
                # Skip auto-generated and internal columns
                if col.is_primary_key:
                    continue
                if col.name in ("created_at", "updated_at", "created_by", "is_active", "metadata"):
                    continue

                label = column_labels.get(col.name, col.name.replace("_", " ").title())

                # Add data type hint for clarity
                if col.udt_name and "timestamp" in col.data_type:
                    label += " (Data)"
                elif col.data_type == "integer" or col.data_type == "numeric":
                    label += " (Número)"

                options.append({"label": label, "value": col.name})
        else:
            # Fallback to common columns if schema unavailable
            options = [
                {"label": "Part Number / SKU", "value": "part_number"},
                {"label": "Quantidade", "value": "quantity"},
                {"label": "Número de Série", "value": "serial_number"},
                {"label": "Localização", "value": "location_code"},
                {"label": "Descrição", "value": "description"},
                {"label": "Número da NF", "value": "nf_number"},
                {"label": "Fornecedor", "value": "supplier_name"},
                {"label": "Valor Unitário", "value": "unit_value"},
            ]

        if include_ignore:
            options.append({"label": "🚫 Ignorar esta coluna", "value": "_ignore"})

        return options

    def _build_movement_type_options(self) -> List[Dict[str, str]]:
        """
        Build movement type options from PostgreSQL ENUM.

        Uses SchemaProvider to get valid movement_type values.
        """
        provider = self._get_schema_provider()
        if provider:
            enum_values = provider.get_enum_values("movement_type")
            if enum_values:
                # Map ENUM values to user-friendly labels
                enum_labels = {
                    "ENTRADA": "✅ ENTRADA (Recebimento)",
                    "SAIDA": "📤 SAÍDA (Expedição)",
                    "TRANSFERENCIA": "🔄 TRANSFERÊNCIA",
                    "AJUSTE": "⚖️ AJUSTE de Estoque",
                    "RESERVA": "📌 RESERVA",
                    "LIBERACAO": "🔓 LIBERAÇÃO de Reserva",
                    "DEVOLUCAO": "↩️ DEVOLUÇÃO",
                }
                return [
                    {"label": enum_labels.get(v, v), "value": v}
                    for v in enum_values
                ]

        # Fallback
        return [
            {"label": "✅ ENTRADA", "value": "ENTRADA"},
            {"label": "📤 SAÍDA", "value": "SAIDA"},
            {"label": "⚖️ AJUSTE", "value": "AJUSTE"},
        ]

    def _generate_targeted_questions(
        self,
        session: ImportSession,
        movement_type: str,
        movement_confidence: float,
    ) -> List[NexoQuestion]:
        """
        Generate targeted questions only for uncertain fields - SCHEMA-AWARE.

        TRUE agentic pattern: Don't ask about everything, only ask about
        fields where the agent is genuinely uncertain. Uses PostgreSQL
        schema for column options instead of hardcoded values.

        Args:
            session: Current import session
            movement_type: Inferred movement type
            movement_confidence: Confidence in inference

        Returns:
            List of targeted questions (fewer than full HIL)
        """
        questions = []

        # Get schema for column options
        provider = self._get_schema_provider()
        schema = provider.get_table_schema("pending_entry_items") if provider else None

        # Only ask about movement type if confidence is below 90%
        if movement_confidence < 0.90:
            questions.append(NexoQuestion(
                id=generate_id("Q"),
                question=f"Confirma que este arquivo é uma **{movement_type}**?",
                context=f"O NEXO inferiu que este arquivo representa uma {movement_type} "
                        f"com {movement_confidence:.0%} de confiança. "
                        f"Confirme ou corrija se necessário.",
                options=self._build_movement_type_options(),  # SCHEMA-AWARE
                importance="critical",
                topic="movement_type",
            ))

        # Ask about uncertain column mappings (only those with low confidence)
        if session.file_analysis:
            # Build schema-aware column options ONCE
            column_options = self._build_schema_aware_options(schema)

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
                            options=column_options,  # SCHEMA-AWARE (not hardcoded)
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
        # FIX (January 2026): Include AI instructions for "Outros:" answers
        "ai_instructions": session.ai_instructions,
        # FEATURE (January 2026): Dynamic schema evolution - columns user wants to create
        "requested_new_columns": [
            {
                "name": col.name,
                "original_name": col.original_name,
                "user_intent": col.user_intent,
                "inferred_type": col.inferred_type,
                "sample_values": col.sample_values,
                "source_file_column": col.source_file_column,
                "approved": col.approved,
            }
            for col in session.requested_new_columns
        ],
        "confidence": session.confidence.to_dict() if session.confidence else None,
        "error": session.error,
        # FIX (January 2026): Include global user feedback for AI interpretation
        "global_user_feedback": session.global_user_feedback,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
