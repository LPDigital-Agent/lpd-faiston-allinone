# =============================================================================
# ObservationAgent - Google ADK Agent Definition
# =============================================================================
# AI agent that observes import data and generates intelligent commentary.
# Follows the "Observe → Learn → Act" pattern for AI-assisted decisions.
#
# Pattern:
#   OBSERVE: Analyze incoming import data (items, values, supplier)
#   LEARN: Identify patterns and compare with historical data
#   ACT: Generate confidence scores and recommendations
# =============================================================================

from google.adk.agents import Agent

# Centralized model configuration (MANDATORY - Gemini 3.0 Flash)
from agents.utils import get_model

from tools.analyze_import import analyze_import_tool

# Agent identifiers
AGENT_ID = "observation"
AGENT_NAME = "ObservationAgent"
AGENT_MODEL = get_model(AGENT_ID)  # gemini-3.0-flash (operational agent)

# =============================================================================
# Risk Levels
# =============================================================================

RISK_LEVELS = {
    "low": {"threshold": 75, "description": "Baixo risco - pode prosseguir"},
    "medium": {"threshold": 50, "description": "Risco médio - revisar alertas"},
    "high": {"threshold": 0, "description": "Alto risco - requer aprovação"},
}

# =============================================================================
# Agent System Instruction
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

## Formato de Resposta
Responda sempre em portugues brasileiro, de forma clara e profissional.

## Fatores de Confianca
| Fator | Peso | Descricao |
|-------|------|-----------|
| data_completeness | 30% | Campos obrigatorios preenchidos |
| format_consistency | 30% | Consistencia do formato dos dados |
| value_validation | 40% | Valores dentro de faixas esperadas |

## Niveis de Risco
| Nivel | Confianca | Acao |
|-------|-----------|------|
| LOW | >= 75% | Pode prosseguir |
| MEDIUM | 50-74% | Revisar alertas |
| HIGH | < 50% | Requer aprovacao |

## Ferramentas Disponiveis

1. **analyze_import_tool**: Analisa dados de importacao e gera observacoes

## Regras
- Sempre responda em portugues brasileiro
- Mantenha tom profissional mas acessivel
- Nunca inclua dados sensiveis na resposta
- Se dados estiverem incompletos, ainda gere observacoes uteis
- Gere insights que possam ser armazenados na memoria para aprendizado
"""


def create_observation_agent() -> Agent:
    """
    Create the ObservationAgent Google ADK Agent.

    Returns:
        Configured Agent instance
    """
    return Agent(
        model=AGENT_MODEL,
        name=AGENT_NAME,
        instruction=OBSERVATION_INSTRUCTION,
        tools=[
            analyze_import_tool,
        ],
    )
