# =============================================================================
# Base Agent for Faiston SGA Inventory
# =============================================================================
# Base class for all inventory management agents with:
# - Google ADK integration (Gemini 3.0 Pro)
# - Confidence scoring for AI decisions
# - Human-in-the-Loop (HIL) workflow support
# - Audit logging
#
# Module: Gestao de Ativos -> Gestao de Estoque
# All agents inherit from this base class.
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import os

from agents.utils import (
    APP_NAME,
    MODEL_GEMINI,
    RiskLevel,
    log_agent_action,
    now_iso,
)


# =============================================================================
# Confidence Score Data Class
# =============================================================================


@dataclass
class ConfidenceScore:
    """
    AI decision confidence score with multi-dimensional factors.

    Used to determine if an action can be executed autonomously
    or requires Human-in-the-Loop approval.

    Attributes:
        overall: Combined confidence score (0.0 to 1.0)
        extraction_quality: Quality of data extraction (NF parsing, etc.)
        evidence_strength: Strength of supporting evidence
        historical_match: Match with historical patterns
        risk_level: Assessed risk level (low, medium, high, critical)
        factors: List of factors that influenced the score
        requires_hil: Whether HIL is required based on score/risk
    """
    overall: float
    extraction_quality: float = 1.0
    evidence_strength: float = 1.0
    historical_match: float = 1.0
    risk_level: str = RiskLevel.LOW
    factors: List[str] = field(default_factory=list)
    requires_hil: bool = False

    def __post_init__(self):
        """Calculate requires_hil based on score and risk."""
        # Always require HIL for critical risk
        if self.risk_level == RiskLevel.CRITICAL:
            self.requires_hil = True
        # Require HIL for high risk with low confidence
        elif self.risk_level == RiskLevel.HIGH and self.overall < 0.8:
            self.requires_hil = True
        # Require HIL for any score below threshold
        elif self.overall < 0.6:
            self.requires_hil = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "overall": round(self.overall, 3),
            "extraction_quality": round(self.extraction_quality, 3),
            "evidence_strength": round(self.evidence_strength, 3),
            "historical_match": round(self.historical_match, 3),
            "risk_level": self.risk_level,
            "factors": self.factors,
            "requires_hil": self.requires_hil,
        }


# =============================================================================
# HIL Decision Types
# =============================================================================


class HILDecision(Enum):
    """Human-in-the-Loop decision outcomes."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    ESCALATE = "escalate"


# =============================================================================
# Base Inventory Agent
# =============================================================================


class BaseInventoryAgent:
    """
    Base class for all inventory management agents.

    Provides:
    - Google ADK Agent initialization
    - Confidence scoring utilities
    - HIL workflow integration
    - Audit logging

    All inventory agents should inherit from this class.
    """

    def __init__(
        self,
        name: str,
        instruction: str,
        description: str = "",
    ):
        """
        Initialize the base inventory agent.

        Args:
            name: Agent name (e.g., "EstoqueControlAgent")
            instruction: System prompt for the agent
            description: Brief description of agent capabilities
        """
        self.name = name
        self.instruction = instruction
        self.description = description
        self._agent = None  # Lazy initialization

    @property
    def agent(self):
        """
        Lazy-load Google ADK Agent to minimize cold start impact.

        Returns:
            Google ADK Agent instance
        """
        if self._agent is None:
            # Lazy import to reduce cold start time
            from google.adk.agents import Agent

            self._agent = Agent(
                model=MODEL_GEMINI,
                name=self.name,
                instruction=self.instruction,
            )
        return self._agent

    async def invoke(
        self,
        prompt: str,
        user_id: str = "system",
        session_id: str = "default",
    ) -> str:
        """
        Invoke the agent with a prompt.

        Args:
            prompt: User prompt or query
            user_id: User identifier (for memory)
            session_id: Session identifier (for memory)

        Returns:
            Agent response as string
        """
        # Lazy import to reduce cold start time
        from google.genai import types
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        log_agent_action(self.name, "invoke", status="started")

        try:
            # Create session service and runner
            session_service = InMemorySessionService()
            runner = Runner(
                agent=self.agent,
                app_name=APP_NAME,
                session_service=session_service,
            )

            # CRITICAL: Create session BEFORE run_async (Google ADK requirement)
            # InMemorySessionService starts empty - sessions must be created first
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )

            # Build content
            content = types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            )

            # Run agent with created session
            response = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content,
            ):
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts"):
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                response += part.text

            log_agent_action(self.name, "invoke", status="completed")
            return response

        except Exception as e:
            log_agent_action(
                self.name, "invoke", status="failed",
                details={"error": str(e)[:100]}
            )
            raise

    def calculate_confidence(
        self,
        extraction_quality: float = 1.0,
        evidence_strength: float = 1.0,
        historical_match: float = 1.0,
        risk_factors: Optional[List[str]] = None,
        base_risk: str = RiskLevel.LOW,
    ) -> ConfidenceScore:
        """
        Calculate confidence score for an AI decision.

        This method is used to determine if an action can be
        executed autonomously or requires HIL approval.

        Args:
            extraction_quality: Quality of data extraction (0.0 to 1.0)
            evidence_strength: Strength of evidence (0.0 to 1.0)
            historical_match: Match with historical patterns (0.0 to 1.0)
            risk_factors: List of identified risk factors
            base_risk: Base risk level for the operation

        Returns:
            ConfidenceScore with overall score and HIL requirement
        """
        factors = risk_factors or []

        # Calculate overall as weighted average
        weights = {
            "extraction": 0.4,
            "evidence": 0.35,
            "historical": 0.25,
        }
        overall = (
            extraction_quality * weights["extraction"] +
            evidence_strength * weights["evidence"] +
            historical_match * weights["historical"]
        )

        # Adjust risk based on factors
        risk_level = base_risk
        if len(factors) >= 3:
            risk_level = RiskLevel.HIGH
        elif len(factors) >= 1:
            risk_level = RiskLevel.MEDIUM

        # Override for critical operations
        critical_keywords = ["adjustment", "discard", "loss", "high_value"]
        if any(kw in " ".join(factors).lower() for kw in critical_keywords):
            risk_level = RiskLevel.CRITICAL

        return ConfidenceScore(
            overall=overall,
            extraction_quality=extraction_quality,
            evidence_strength=evidence_strength,
            historical_match=historical_match,
            risk_level=risk_level,
            factors=factors,
        )

    def should_require_hil(
        self,
        action_type: str,
        confidence: ConfidenceScore,
        value_threshold: Optional[float] = None,
        item_value: Optional[float] = None,
    ) -> bool:
        """
        Determine if an action requires Human-in-the-Loop approval.

        Some actions ALWAYS require HIL:
        - Inventory adjustments
        - Discards
        - Loss declarations

        Other actions require HIL based on:
        - Confidence score
        - Item value
        - Cross-project operations

        Args:
            action_type: Type of action being performed
            confidence: Calculated confidence score
            value_threshold: Optional value threshold for HIL
            item_value: Optional item value for comparison

        Returns:
            True if HIL is required
        """
        # Always HIL actions (NEVER autonomous)
        always_hil_actions = {
            "adjustment", "discard", "loss", "extravio",
            "create_part_number", "delete_asset",
        }
        if action_type.lower() in always_hil_actions:
            return True

        # HIL if confidence requires it
        if confidence.requires_hil:
            return True

        # HIL if value exceeds threshold
        if value_threshold and item_value:
            if item_value >= value_threshold:
                return True

        return False

    def format_hil_task_message(
        self,
        action_type: str,
        summary: str,
        confidence: ConfidenceScore,
        details: Dict[str, Any],
    ) -> str:
        """
        Format a message for HIL task creation.

        This message will be shown to the human reviewer.

        Args:
            action_type: Type of action requiring approval
            summary: Brief summary of the action
            confidence: Confidence score for the decision
            details: Additional details for review

        Returns:
            Formatted message string
        """
        message = f"""
## Solicitacao de Aprovacao: {action_type.upper()}

### Resumo
{summary}

### Confianca da IA
- **Score Geral**: {confidence.overall:.0%}
- **Nivel de Risco**: {confidence.risk_level.upper()}
- **Fatores**: {', '.join(confidence.factors) if confidence.factors else 'Nenhum'}

### Detalhes
"""
        for key, value in details.items():
            # Format keys nicely
            display_key = key.replace("_", " ").title()
            message += f"- **{display_key}**: {value}\n"

        message += """
### Acoes Disponiveis
- **Aprovar**: Executar a acao conforme proposto
- **Rejeitar**: Cancelar a acao
- **Modificar**: Ajustar parametros antes de executar
"""
        return message
