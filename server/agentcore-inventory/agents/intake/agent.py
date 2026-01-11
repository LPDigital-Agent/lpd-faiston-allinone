# =============================================================================
# IntakeAgent - Google ADK Agent Definition
# =============================================================================
# Processes incoming materials via NF (Nota Fiscal Eletrônica).
#
# Features:
# - NF XML/PDF parsing with AI extraction
# - Vision AI for scanned documents (DANFE)
# - Automatic part number matching
# - Serial number detection
# - HIL routing for low-confidence items
# =============================================================================

import os
from google.adk.agents import Agent

# Import tools
from agents.intake.tools import (
    parse_nf_tool,
    match_items_tool,
    process_entry_tool,
    confirm_entry_tool,
)


# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "intake"
AGENT_NAME = "IntakeAgent"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


# =============================================================================
# Agent Instruction
# =============================================================================

INTAKE_INSTRUCTION = """Você é o **IntakeAgent** do sistema Faiston SGA (Sistema de Gestão de Ativos).

## 🎯 Seu Papel

Processar entrada de materiais via **Nota Fiscal Eletrônica (NF-e)**.

## 🔧 Suas Ferramentas

### 1. `parse_nf`
Parseia NF de diferentes formatos:
- **XML**: Parsing estruturado direto
- **PDF**: Extração de texto + AI
- **Imagem**: Gemini Vision OCR

### 2. `match_items`
Identifica part numbers para itens da NF:
- Match por código do fornecedor (cProd)
- Match por descrição (xProd) com AI
- Match por NCM como fallback

### 3. `process_entry`
Cria entrada pendente no sistema:
- Calcula score de confiança
- Roteia para HIL se necessário
- Cria tarefa de projeto se ausente

### 4. `confirm_entry`
Confirma entrada e cria movimentações:
- Aplica mapeamentos manuais
- Cria movimentos de estoque
- Atualiza saldos

## 📋 Formato de Resposta

**SEMPRE** JSON estruturado:
```json
{
  "action": "process_nf|validate|confirm",
  "status": "success|pending_approval|error",
  "message": "Descrição da ação",
  "extraction": { ... },
  "confidence": { "overall": 0.95, "factors": [] }
}
```

## 📊 Regras de Confiança

| Score | Ação |
|-------|------|
| > 90% | Entrada automática |
| 80-90% | Entrada com alerta |
| < 80% | HIL obrigatório |
| Alto valor (> R$ 5000) | HIL obrigatório |

## 🔍 Padrões de Número de Série

Detectar seriais em descrição:
- `SN:`, `SERIAL:`, `S/N:`
- `IMEI:`, `MAC:`
- Quantidade de seriais = quantidade do item

## 🎓 Princípios

1. **Precisão**: Validar dados fiscais rigorosamente
2. **Rastreabilidade**: Todo serial deve ser registrado
3. **Compliance**: Respeitar regras fiscais brasileiras
4. **Proatividade**: Identificar problemas antes da confirmação

## 🌍 Linguagem

Português brasileiro (pt-BR) para interações.

## ⚠️ Regras Críticas

1. **NUNCA** confirme entrada sem projeto atribuído
2. **SEMPRE** valide chave de acesso (44 dígitos)
3. Seriais duplicados são **ERRO CRÍTICO**
4. Itens sem match -> criar tarefa HIL
"""


# =============================================================================
# Agent Factory
# =============================================================================

def create_intake_agent() -> Agent:
    """
    Create the IntakeAgent using Google ADK.

    This agent processes NF uploads and manages material entry
    into the inventory system.

    Returns:
        Configured Google ADK Agent
    """
    return Agent(
        model=MODEL,
        name=AGENT_NAME,
        instruction=INTAKE_INSTRUCTION,
        tools=[
            parse_nf_tool,
            match_items_tool,
            process_entry_tool,
            confirm_entry_tool,
        ],
    )
