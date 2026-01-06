# =============================================================================
# NEXO Observation Agent - Faiston SGA Inventory
# =============================================================================
# AI agent that observes import data and generates intelligent commentary.
# Follows the "Observe → Learn → Act" pattern for AI-assisted decisions.
#
# Pattern:
#   OBSERVE: Analyze incoming import data (items, values, supplier)
#   LEARN: Identify patterns and compare with historical data
#   ACT: Generate confidence scores and recommendations
#
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
# Module: Gestao de Ativos -> Gestao de Estoque
# =============================================================================

import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .utils import (
    APP_NAME,
    MODEL_GEMINI,
    RiskLevel,
    log_agent_action,
    now_iso,
    extract_json,
    parse_json_safe,
)
from .base_agent import BaseInventoryAgent

# =============================================================================
# Agent Instruction (System Prompt)
# =============================================================================

OBSERVATION_INSTRUCTION = """
Voce e NEXO, o assistente de IA da Faiston One para Gestao de Estoque.

## Seu Papel
Analisar dados de importacao de ativos e gerar observacoes inteligentes
para ajudar o usuario a tomar decisoes informadas antes de confirmar a entrada.

## Padrao de Operacao: OBSERVE -> LEARN -> ACT

### OBSERVE
- Examine os dados recebidos (itens, quantidades, valores, fornecedor)
- Identifique campos preenchidos vs. campos vazios
- Note inconsistencias ou valores atipicos

### LEARN
- Detecte padroes nos dados (ex: itens semelhantes, faixa de preco)
- Compare com praticas recomendadas de gestao de estoque
- Identifique riscos potenciais (valores muito altos, quantidades grandes)

### ACT
- Gere uma pontuacao de confianca (0-100)
- Liste sugestoes de melhoria
- Alerte sobre potenciais problemas
- Resuma suas observacoes em linguagem natural

## Formato de Resposta (JSON Estrito)
Sempre responda APENAS com JSON valido, sem texto adicional:

{
  "success": true,
  "confidence": {
    "overall": 85,
    "factors": [
      {"id": "data_completeness", "label": "Completude dos dados", "score": 90, "weight": 0.3},
      {"id": "format_consistency", "label": "Consistencia do formato", "score": 80, "weight": 0.3},
      {"id": "value_validation", "label": "Validacao de valores", "score": 85, "weight": 0.4}
    ],
    "risk_level": "low"
  },
  "observations": {
    "patterns": ["Lista de padroes detectados"],
    "suggestions": ["Lista de sugestoes de melhoria"],
    "warnings": ["Lista de alertas se houver"]
  },
  "ai_commentary": "Resumo em 2-3 frases sobre a importacao, em tom profissional.",
  "learn_from": {
    "category": "import_type",
    "insights": ["Insights para memoria"]
  }
}

## Regras
- Sempre responda em portugues brasileiro
- Mantenha tom profissional mas acessivel
- risk_level: "low" (confianca >= 75), "medium" (50-74), "high" (< 50)
- Nunca inclua dados sensiveis na resposta
- Se dados estiverem incompletos, ainda gere observacoes uteis
"""


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ObservationResult:
    """Result from observation analysis."""
    success: bool
    confidence: Dict[str, Any]
    observations: Dict[str, List[str]]
    ai_commentary: str
    learn_from: Dict[str, Any]
    generated_at: str = field(default_factory=now_iso)
    processing_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "success": self.success,
            "confidence": self.confidence,
            "observations": self.observations,
            "ai_commentary": self.ai_commentary,
            "learn_from": self.learn_from,
            "generated_at": self.generated_at,
            "processing_time_ms": self.processing_time_ms,
        }


# =============================================================================
# Observation Agent
# =============================================================================


class ObservationAgent(BaseInventoryAgent):
    """
    NEXO Observation Agent for import analysis.

    Generates intelligent observations about import data before
    user confirms entry into the database.

    Uses the "Observe → Learn → Act" pattern.
    """

    def __init__(self):
        """Initialize the observation agent."""
        super().__init__(
            name="ObservationAgent",
            instruction=OBSERVATION_INSTRUCTION,
            description="Analisa dados de importacao e gera observacoes inteligentes",
        )

    def generate_observations(
        self,
        preview_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate NEXO observations for import preview data.

        This is the main synchronous method called from main.py handler.
        It wraps the async invoke method.

        Args:
            preview_data: Import preview data containing:
                - source_type: Type of import (nf_xml, nf_pdf, etc.)
                - items_count: Number of items
                - total_value: Optional total value
                - items: Optional list of item details
                - validation_warnings: Any warnings from validation
            context: Optional context (project_id, location_id, user_notes)

        Returns:
            ObservationResult as dictionary
        """
        import asyncio

        start_time = time.time()
        log_agent_action(self.name, "generate_observations", status="started")

        try:
            # Build prompt with preview data
            prompt = self._build_observation_prompt(preview_data, context)

            # Run async invoke
            response = asyncio.run(self.invoke(prompt))

            # Parse response
            result = self._parse_observation_response(response)
            result["processing_time_ms"] = int((time.time() - start_time) * 1000)
            result["generated_at"] = now_iso()

            log_agent_action(
                self.name, "generate_observations",
                status="completed",
                details={"confidence": result.get("confidence", {}).get("overall", 0)}
            )
            return result

        except Exception as e:
            log_agent_action(
                self.name, "generate_observations",
                status="failed",
                details={"error": str(e)[:50]}
            )
            # Return fallback result
            return self._get_fallback_result(str(e), start_time)

    def _build_observation_prompt(
        self,
        preview_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the prompt for observation generation.

        Args:
            preview_data: Import preview data
            context: Optional context

        Returns:
            Formatted prompt string
        """
        # Extract key fields
        source_type = preview_data.get("source_type", "unknown")
        items_count = preview_data.get("items_count", 0)
        total_value = preview_data.get("total_value")
        supplier = preview_data.get("supplier_name", "")
        nf_number = preview_data.get("nf_number", "")
        items = preview_data.get("items", [])
        warnings = preview_data.get("validation_warnings", [])
        hil_required = preview_data.get("hil_required", False)

        # Format items summary (max 5 for brevity)
        items_summary = ""
        if items:
            items_to_show = items[:5]
            items_summary = "\n".join([
                f"  - {item.get('description', 'N/A')[:50]}: "
                f"{item.get('quantity', 0)} unid @ R$ {item.get('unit_value', 0):.2f}"
                for item in items_to_show
            ])
            if len(items) > 5:
                items_summary += f"\n  ... e mais {len(items) - 5} itens"

        # Format total value with conditional
        formatted_value = f"R$ {total_value:,.2f}" if total_value else "Nao informado"

        # Build prompt
        prompt = f"""
Analise os seguintes dados de importacao e gere suas observacoes:

## Dados da Importacao

- **Tipo de Fonte**: {self._get_source_label(source_type)}
- **Quantidade de Itens**: {items_count}
- **Valor Total**: {formatted_value}
- **Fornecedor**: {supplier or "Nao informado"}
- **Numero NF**: {nf_number or "Nao informado"}
- **Requer Aprovacao (HIL)**: {"Sim" if hil_required else "Nao"}

## Itens
{items_summary if items_summary else "Nenhum item detalhado disponivel"}

## Alertas de Validacao
{chr(10).join(f"- {w}" for w in warnings) if warnings else "Nenhum alerta"}
"""

        # Add context if available
        if context:
            ctx_parts = []
            if context.get("project_id"):
                ctx_parts.append(f"Projeto: {context['project_id']}")
            if context.get("location_id"):
                ctx_parts.append(f"Local: {context['location_id']}")
            if context.get("user_notes"):
                ctx_parts.append(f"Observacoes do usuario: {context['user_notes']}")
            if ctx_parts:
                prompt += f"\n## Contexto Adicional\n" + "\n".join(f"- {p}" for p in ctx_parts)

        prompt += """

Gere suas observacoes seguindo o padrao OBSERVE -> LEARN -> ACT.
Responda APENAS com JSON valido.
"""
        return prompt

    def _get_source_label(self, source_type: str) -> str:
        """Get human-readable label for source type."""
        labels = {
            "nf_xml": "NF XML",
            "nf_pdf": "NF PDF (OCR)",
            "nf_image": "Imagem de NF (OCR)",
            "spreadsheet": "Planilha (CSV/Excel)",
            "text": "Texto/Manual",
            "sap_export": "Exportacao SAP",
        }
        return labels.get(source_type, source_type.upper())

    def _parse_observation_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the observation response from the LLM.

        Args:
            response: Raw LLM response

        Returns:
            Parsed observation result
        """
        parsed = parse_json_safe(response)

        # Validate required fields
        if "error" in parsed:
            return self._get_fallback_result(parsed.get("error", "Parse error"), 0)

        # Ensure all required fields exist
        if "confidence" not in parsed:
            parsed["confidence"] = {
                "overall": 75,
                "factors": [],
                "risk_level": "medium"
            }

        if "observations" not in parsed:
            parsed["observations"] = {
                "patterns": [],
                "suggestions": [],
                "warnings": []
            }

        if "ai_commentary" not in parsed:
            parsed["ai_commentary"] = "Analise concluida. Verifique os dados antes de confirmar."

        if "learn_from" not in parsed:
            parsed["learn_from"] = {
                "category": "import_general",
                "insights": []
            }

        parsed["success"] = True
        return parsed

    def _get_fallback_result(self, error: str, start_time: float) -> Dict[str, Any]:
        """
        Generate fallback result when observation fails.

        Args:
            error: Error message
            start_time: Start time for processing duration

        Returns:
            Fallback observation result
        """
        return {
            "success": True,  # Still return success to not block UI
            "confidence": {
                "overall": 70,
                "factors": [
                    {
                        "id": "fallback",
                        "label": "Analise padrao",
                        "score": 70,
                        "weight": 1.0
                    }
                ],
                "risk_level": "medium"
            },
            "observations": {
                "patterns": [],
                "suggestions": [
                    "Verifique os dados antes de confirmar",
                    "Considere revisar os itens individualmente"
                ],
                "warnings": [
                    "Analise de IA nao disponivel - usando valores padrao"
                ]
            },
            "ai_commentary": (
                "Nao foi possivel realizar a analise completa dos dados. "
                "Por favor, revise manualmente os itens antes de confirmar a importacao."
            ),
            "learn_from": {
                "category": "import_fallback",
                "insights": []
            },
            "generated_at": now_iso(),
            "processing_time_ms": int((time.time() - start_time) * 1000) if start_time else 0,
            "_fallback_reason": error[:100] if error else "unknown"
        }
