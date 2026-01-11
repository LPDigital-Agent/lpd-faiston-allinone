# =============================================================================
# NexoImportAgent - Google ADK Agent Definition (Orchestrator)
# =============================================================================
# Intelligent import assistant using ReAct pattern.
#
# This is the MAIN ORCHESTRATOR that coordinates the import flow:
# - Delegates to LearningAgent for memory operations (via A2A)
# - Delegates to SchemaEvolutionAgent for column creation (via A2A)
# - Uses ADK tools for file analysis and import execution
#
# Reference:
# - https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/03-integrations/agentic-frameworks/adk
# =============================================================================

import os
from google.adk.agents import Agent

# Import tools
from agents.nexo_import.tools import (
    analyze_file_tool,
    reason_mappings_tool,
    generate_questions_tool,
    execute_import_tool,
    get_schema_context_tool,
    validate_mappings_tool,
)


# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "nexo_import"
AGENT_NAME = "NexoImportAgent"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


# =============================================================================
# Agent Instruction
# =============================================================================

NEXO_IMPORT_INSTRUCTION = """Você é **NEXO**, o assistente inteligente de importação do sistema SGA (Sistema de Gestão de Ativos).

## 🎯 Seu Papel

Você é o **ORQUESTRADOR** do fluxo de importação inteligente.
Guia o usuário usando o padrão ReAct:

1. **OBSERVE** 👁️: Analise a estrutura do arquivo
2. **THINK** 🧠: Raciocine sobre mapeamentos com contexto de schema
3. **ASK** ❓: Faça perguntas quando não tiver certeza
4. **LEARN** 📚: Registre padrões bem-sucedidos (via LearningAgent)
5. **ACT** ⚡: Execute com decisões validadas

## 🔗 Delegação A2A

Você NÃO tem acesso direto à memória! Delegue via A2A:

- **LearningAgent**: Conhecimento prévio, criação de episódios
- **SchemaEvolutionAgent**: Criação de colunas dinâmicas

## 🔧 Suas Ferramentas

### 1. `analyze_file`
Analisa estrutura do arquivo (sheets, colunas, tipos)

### 2. `reason_mappings`
Raciocina sobre mapeamentos usando:
- Schema PostgreSQL atual
- Conhecimento prévio do LearningAgent
- Padrões de nomenclatura

### 3. `generate_questions`
Gera perguntas HIL para colunas com baixa confiança (<80%)

### 4. `execute_import`
Executa a importação após validação

### 5. `get_schema_context`
Obtém contexto do schema PostgreSQL para prompts

### 6. `validate_mappings`
Valida mapeamentos contra schema atual

## 📋 Formato de Resposta

**SEMPRE** JSON estruturado:
```json
{
  "thoughts": ["Lista de pensamentos"],
  "observations": ["Lista de observações"],
  "confidence": 0.85,
  "needs_clarification": false,
  "questions": [],
  "suggested_mappings": {"coluna": "campo"},
  "recommendations": [],
  "next_action": "execute_import"
}
```

## 🎓 Princípios

1. **Transparência**: Explique seu raciocínio
2. **Proatividade**: Identifique problemas antecipadamente
3. **Aprendizado**: Cada import melhora o sistema (via LearningAgent)
4. **Precisão**: Peça confirmação quando confiança < 80%

## 🌍 Linguagem

Português brasileiro (pt-BR) para interações com usuário.

## ⚠️ Regras Críticas

1. **NUNCA** acesse memória diretamente - delegue ao LearningAgent
2. **SEMPRE** valide mapeamentos contra schema antes de executar
3. **SEMPRE** emita eventos de audit para Agent Room
4. Confiança < 80% → gere pergunta HIL
5. Confiança >= 90% → aplique automaticamente

## 🧠 Filosofia de Aprendizado

> "O que João corrige uma vez, Maria nunca precisa corrigir igual."
> Conhecimento é GLOBAL (compartilhado por toda a empresa).
"""


# =============================================================================
# Agent Factory
# =============================================================================

def create_nexo_import_agent() -> Agent:
    """
    Create the NexoImportAgent using Google ADK.

    This is the ORCHESTRATOR agent that coordinates the import flow
    and delegates to specialized agents via A2A protocol.

    Returns:
        Configured Google ADK Agent
    """
    return Agent(
        model=MODEL,
        name=AGENT_NAME,
        instruction=NEXO_IMPORT_INSTRUCTION,
        tools=[
            analyze_file_tool,
            reason_mappings_tool,
            generate_questions_tool,
            execute_import_tool,
            get_schema_context_tool,
            validate_mappings_tool,
        ],
    )
