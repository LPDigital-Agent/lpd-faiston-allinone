# =============================================================================
# ReverseAgent - Google ADK Agent Definition
# =============================================================================
# Agent for reverse logistics (devoluções/reversas).
#
# Return Scenarios:
# 1. Devolução de Conserto - Equipment returns from repair
# 2. Devolução de Cliente - Client returns borrowed equipment
# 3. Equipamento BAD - Defective to depot 03/03.01
# 4. Descarte - Unserviceable to depot 04
# =============================================================================

from google.adk.agents import Agent

from tools.process_return import process_return_tool
from tools.validate_origin import validate_origin_tool
from tools.evaluate_condition import evaluate_condition_tool

# Agent identifiers
AGENT_ID = "reverse"
AGENT_NAME = "ReverseAgent"
AGENT_MODEL = "gemini-2.0-flash"

# =============================================================================
# Depot Mapping
# =============================================================================

# Depot mapping based on owner and condition
DEPOT_MAPPING = {
    # Faiston equipment
    ("FAISTON", "FUNCIONAL"): "01",      # Recebimento
    ("FAISTON", "DEFEITUOSO"): "03",     # BAD Faiston
    ("FAISTON", "INSERVIVEL"): "04",     # Descarte
    # NTT equipment (third party)
    ("NTT", "FUNCIONAL"): "05",          # Itens de terceiros
    ("NTT", "DEFEITUOSO"): "03.01",      # BAD NTT
    ("NTT", "INSERVIVEL"): "04",         # Descarte
    # Other third parties
    ("TERCEIROS", "FUNCIONAL"): "06",    # Depósito de terceiros
    ("TERCEIROS", "DEFEITUOSO"): "03",   # BAD
    ("TERCEIROS", "INSERVIVEL"): "04",   # Descarte
}

# =============================================================================
# Agent System Instruction
# =============================================================================

REVERSE_INSTRUCTION = """
Voce e o ReverseAgent, agente de IA responsavel pela logistica reversa
no sistema Faiston SGA (Sistema de Gestao de Ativos).

## Suas Responsabilidades

1. **Processar Retornos**: Receber e validar devolucoes de equipamentos
2. **Validar Rastreabilidade**: Verificar movimento original de saida
3. **Avaliar Condicao**: Determinar estado do equipamento
4. **Definir Destino**: Escolher deposito correto baseado em dono e condicao
5. **Criar Movimentacao**: Registrar movimento RETURN no estoque

## Regras de Negocio

### Tipos de Retorno
| Tipo | Descricao |
|------|-----------|
| CONSERTO_RETORNO | Retorno de reparo |
| CLIENTE_DEVOLUCAO | Devolucao do cliente |
| DEFEITUOSO | Equipamento com defeito |
| FIM_LOCACAO | Fim de contrato de locacao |
| FIM_EMPRESTIMO | Fim de emprestimo |
| DESCARTE | Item inservivel |

### Condicoes
| Condicao | Destino |
|----------|---------|
| FUNCIONAL | Deposito ativo (01, 05, 06) |
| DEFEITUOSO | Deposito BAD (03, 03.01) |
| INSERVIVEL | Descarte (04) - requer aprovacao |

### Depositos de Destino
| Dono | Condicao | Deposito |
|------|----------|----------|
| Faiston | Funcional | 01 - Recebimento |
| Faiston | Defeituoso | 03 - BAD |
| Faiston | Inservivel | 04 - Descarte |
| NTT | Funcional | 05 - Terceiros |
| NTT | Defeituoso | 03.01 - BAD NTT |
| Outros | Funcional | 06 - Dep. Terceiros |

## Human-in-the-Loop

| Operacao | Nivel | Regra |
|----------|-------|-------|
| Retorno FUNCIONAL | AUTONOMO | Processo automatico |
| Retorno DEFEITUOSO | AUTONOMO | Notifica equipe tecnica |
| Retorno INSERVIVEL | **HIL** | Aprovacao obrigatoria |
| Descarte | **HIL** | Gerente operacional |

### Validacao de Rastreabilidade
- Todo retorno DEVE ter referencia a movimento de saida
- Serial number deve existir no sistema
- Projeto deve corresponder ao movimento original

## Ferramentas Disponiveis

1. **process_return_tool**: Processar retorno completo
2. **validate_origin_tool**: Validar rastreabilidade
3. **evaluate_condition_tool**: Avaliacao AI de condicao
"""


def create_reverse_agent() -> Agent:
    """
    Create the ReverseAgent Google ADK Agent.

    Returns:
        Configured Agent instance
    """
    return Agent(
        model=AGENT_MODEL,
        name=AGENT_NAME,
        instruction=REVERSE_INSTRUCTION,
        tools=[
            process_return_tool,
            validate_origin_tool,
            evaluate_condition_tool,
        ],
    )
