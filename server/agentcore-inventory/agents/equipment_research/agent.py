# =============================================================================
# EquipmentResearchAgent - Google ADK Agent Definition
# =============================================================================
# AI-First agent that researches equipment documentation after imports.
# Uses Gemini with google_search grounding to find official manuals,
# datasheets, and specifications from manufacturer websites.
#
# Philosophy: OBSERVE → THINK → ACT → ORGANIZE
#
# Module: Gestao de Ativos -> Gestao de Estoque -> Knowledge Base
# =============================================================================

from google.adk.agents import Agent

from tools.research_equipment import research_equipment_tool
from tools.generate_queries import generate_queries_tool

# Agent identifiers
AGENT_ID = "equipment_research"
AGENT_NAME = "EquipmentResearchAgent"
AGENT_MODEL = "gemini-2.0-flash"

# =============================================================================
# Constants
# =============================================================================

# Google Search daily quota limit
DAILY_SEARCH_QUOTA = 5000

# Maximum documents to download per equipment
MAX_DOCS_PER_EQUIPMENT = 5

# Minimum confidence for document relevance
MIN_RELEVANCE_CONFIDENCE = 0.7

# Research statuses
RESEARCH_STATUSES = {
    "PENDING": "Aguardando pesquisa",
    "IN_PROGRESS": "Em andamento",
    "COMPLETED": "Concluído",
    "NO_DOCS_FOUND": "Nenhum documento encontrado",
    "FAILED": "Falhou",
    "RATE_LIMITED": "Quota excedida",
}

# Trusted domains for equipment documentation
TRUSTED_DOMAINS = [
    "dell.com", "hp.com", "lenovo.com", "cisco.com", "intel.com",
    "samsung.com", "lg.com", "acer.com", "asus.com", "microsoft.com",
    "apple.com", "ibm.com", "oracle.com", "vmware.com", "nvidia.com",
    "amd.com", "seagate.com", "westerndigital.com", "crucial.com",
    "kingston.com", "netgear.com", "tplink.com", "ubiquiti.com",
    "schneider-electric.com", "apc.com", "eaton.com", "vertiv.com",
    "fortinet.com", "paloaltonetworks.com", "juniper.net",
    # Brazilian manufacturers/distributors
    "positivo.com.br", "multilaser.com.br", "intelbras.com.br",
]

# =============================================================================
# Agent System Instruction
# =============================================================================

EQUIPMENT_RESEARCH_INSTRUCTION = """
Voce e um agente especializado em pesquisar documentacao tecnica de equipamentos.

## Seu Papel

Quando receber informacoes sobre um equipamento (part number, descricao, fabricante), voce deve:

1. **OBSERVE**: Analisar as informacoes fornecidas e identificar o tipo de equipamento
2. **THINK**: Gerar queries de busca otimizadas para encontrar documentacao oficial
3. **ACT**: Avaliar os resultados da busca e identificar documentos relevantes
4. **ORGANIZE**: Estruturar as informacoes encontradas e fazer upload para S3

## Tipos de Documentos Prioritarios

| Prioridade | Tipo | Descricao |
|------------|------|-----------|
| 1 | Manual do Usuario | Instrucoes de operacao e uso |
| 2 | Datasheet | Especificacoes tecnicas completas |
| 3 | Quick Start Guide | Guia de inicio rapido |
| 4 | Service Manual | Manual de manutencao/reparo |
| 5 | Especificacoes | Sheets de especificacao tecnica |

## Dominios Confiaveis

Priorize documentos de fabricantes oficiais:
- Dell, HP, Lenovo, Cisco, Intel, Samsung, LG
- Apple, IBM, Oracle, VMware, NVIDIA, AMD
- Netgear, TP-Link, Ubiquiti, Fortinet
- Positivo, Multilaser, Intelbras (Brasil)

## Formatos de Arquivo Permitidos

- PDF (preferido)
- DOC, DOCX
- XLS, XLSX
- TXT

## Ferramentas Disponiveis

1. **research_equipment_tool**: Pesquisa documentacao completa para um equipamento
2. **generate_queries_tool**: Gera queries de busca otimizadas

## Seguranca

- NUNCA inclua informacoes pessoais nas queries
- Priorize sites oficiais de fabricantes
- Evite sites de terceiros desconhecidos
- Valide URLs antes de download

## Human-in-the-Loop

| Operacao | Nivel | Regra |
|----------|-------|-------|
| Pesquisa normal | AUTONOMO | Ate 5 docs por equipment |
| Quota excedida | **NOTIFICA** | Alerta equipe |
| Download grande (>50MB) | **HIL** | Aprovacao necessaria |
"""


def create_equipment_research_agent() -> Agent:
    """
    Create the EquipmentResearchAgent Google ADK Agent.

    Returns:
        Configured Agent instance
    """
    return Agent(
        model=AGENT_MODEL,
        name=AGENT_NAME,
        instruction=EQUIPMENT_RESEARCH_INSTRUCTION,
        tools=[
            research_equipment_tool,
            generate_queries_tool,
        ],
    )
