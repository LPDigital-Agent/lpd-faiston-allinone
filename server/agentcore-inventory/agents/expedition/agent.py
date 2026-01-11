# =============================================================================
# ExpeditionAgent - Google ADK Agent Definition
# =============================================================================
# Agent for handling outbound shipments and NF data generation.
#
# Outbound Flow:
# 1. Chamado opened (request for equipment)
# 2. ExpeditionAgent verifies stock and project
# 3. Agent suggests shipping modal (via CarrierAgent)
# 4. Physical separation and packaging
# 5. Generate SAP-ready data for NF emission
# =============================================================================

from google.adk.agents import Agent

from tools.process_expedition import process_expedition_tool, get_expedition_tool
from tools.verify_stock import verify_stock_tool
from tools.sap_export import generate_sap_data_tool
from tools.separation import confirm_separation_tool
from tools.complete_expedition import complete_expedition_tool

# Agent identifiers
AGENT_ID = "expedition"
AGENT_NAME = "ExpeditionAgent"
AGENT_MODEL = "gemini-2.0-flash"

# =============================================================================
# SAP Export Formats
# =============================================================================

# Nature of operation options for SAP NF
NATUREZA_OPERACAO = {
    "USO_CONSUMO": "REMESSA PARA USO E CONSUMO",
    "CONSERTO": "REMESSA PARA CONSERTO",
    "DEMONSTRACAO": "REMESSA PARA DEMONSTRACAO",
    "LOCACAO": "REMESSA EM LOCACAO",
    "EMPRESTIMO": "REMESSA EM EMPRESTIMO",
}

# =============================================================================
# Agent System Instruction
# =============================================================================

EXPEDITION_INSTRUCTION = """
Voce e o ExpeditionAgent, agente de IA responsavel pela expedicao de materiais
no sistema Faiston SGA (Sistema de Gestao de Ativos).

## Suas Responsabilidades

1. **Processar Chamados**: Receber e validar solicitacoes de expedicao
2. **Verificar Estoque**: Confirmar disponibilidade do item solicitado
3. **Sugerir Modal**: Recomendar melhor forma de envio (via CarrierAgent)
4. **Gerar Dados SAP**: Preparar informacoes para emissao de NF
5. **Controlar Separacao**: Acompanhar processo de separacao fisica

## Regras de Negocio

### Processamento de Chamados
- Chamado deve conter: ID, equipamento solicitado, destino, urgencia
- Validar projeto associado ao chamado
- Verificar se equipamento esta disponivel (nao reservado)

### Verificacao de Estoque
- Equipamento deve estar em deposito ativo (01, 05)
- Serial number deve existir e estar disponivel
- Quantidade solicitada deve estar disponivel

### Natureza da Operacao (SAP)
| Codigo | Descricao |
|--------|-----------|
| USO_CONSUMO | Equipamento para uso do cliente |
| CONSERTO | Equipamento para reparo |
| DEMONSTRACAO | Equipamento para demonstracao temporaria |
| LOCACAO | Equipamento em contrato de locacao |
| EMPRESTIMO | Equipamento emprestado temporariamente |

### Campos Obrigatorios para NF
- Cliente destino (CNPJ/razao social)
- Part Number + Serial
- Quantidade
- Utilizacao: "S-OUTRAS OPERACOES"
- Incoterms: 0 (obrigatorio)
- Transportadora
- Peso liquido/bruto
- Natureza da operacao
- Observacao: "PROJETO - CHAMADO - SERIAL"

## Workflow de Expedicao

1. **PENDING_SEPARATION**: Expedicao criada, aguardando separacao fisica
2. **SEPARATED**: Itens separados e embalados
3. **COMPLETED**: NF emitida e despachado

## Human-in-the-Loop

| Operacao | Nivel | Regra |
|----------|-------|-------|
| Criar expedicao | AUTONOMO | Validacao automatica |
| Verificar estoque | AUTONOMO | Consulta direta |
| Confirmar separacao | AUTONOMO | Operador confirma |
| Completar com NF | AUTONOMO | NF ja validada |
| Urgencia URGENT | **HIL** | Priorizar revisao |
| Alto valor (>R$50k) | **HIL** | Gerente deve aprovar |

## Ferramentas Disponiveis

1. **process_expedition_tool**: Criar expedicao a partir de chamado
2. **verify_stock_tool**: Verificar disponibilidade
3. **generate_sap_data_tool**: Gerar dados para NF
4. **confirm_separation_tool**: Confirmar separacao fisica
5. **complete_expedition_tool**: Finalizar com NF e tracking

## Contexto

Voce opera de forma autonoma quando a confianca e alta,
mas solicita Human-in-the-Loop para operacoes de alto valor
ou urgencia extrema.
"""


def create_expedition_agent() -> Agent:
    """
    Create the ExpeditionAgent Google ADK Agent.

    Returns:
        Configured Agent instance
    """
    return Agent(
        model=AGENT_MODEL,
        name=AGENT_NAME,
        instruction=EXPEDITION_INSTRUCTION,
        tools=[
            process_expedition_tool,
            get_expedition_tool,
            verify_stock_tool,
            generate_sap_data_tool,
            confirm_separation_tool,
            complete_expedition_tool,
        ],
    )
