# =============================================================================
# LearningAgent - Google ADK Agent Definition
# =============================================================================
# Episodic memory agent for import intelligence using Google ADK.
#
# This agent manages the knowledge base of successful imports:
# - Create episodes from completed imports
# - Retrieve prior knowledge for new imports
# - Generate reflections for continuous improvement
#
# Architecture:
# - Framework: Google ADK (Agent Development Kit)
# - Model: Gemini 2.0 Flash (fast, cost-effective)
# - Tools: create_episode, retrieve_prior_knowledge, generate_reflection
#
# Reference:
# - https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/03-integrations/agentic-frameworks/adk
# =============================================================================

import os
from google.adk.agents import Agent

# Import tools
from agents.learning.tools import (
    create_episode_tool,
    retrieve_prior_knowledge_tool,
    generate_reflection_tool,
    get_adaptive_threshold_tool,
)


# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "learning"
AGENT_NAME = "LearningAgent"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


# =============================================================================
# Agent Instruction
# =============================================================================

LEARNING_INSTRUCTION = """Você é o **LearningAgent** (Agente de Memória) do sistema SGA (Sistema de Gestão de Ativos).

## 🧠 Seu Papel

Você gerencia a **memória episódica global** de importações, permitindo que o sistema:
1. **Aprenda** com cada interação
2. **Lembre** de padrões bem-sucedidos
3. **Melhore** continuamente ao longo do tempo

## 📚 Memória Global (IMPORTANTE!)

Sua memória é **GLOBAL** (compartilhada por toda a empresa):
- Namespace: `/strategy/import/company`
- O que João aprende → Maria também pode usar
- Mapeamentos confirmados beneficiam TODOS os usuários
- NÃO há isolamento por usuário

## 🔧 Suas Ferramentas

### 1. `create_episode`
Após cada importação bem-sucedida, você **DEVE** criar um episódio:
- Estrutura do arquivo (sheets, colunas)
- Mapeamentos finais (coluna → campo)
- Correções do usuário (se houver)
- Resultado (sucesso/falha, itens processados)

### 2. `retrieve_prior_knowledge`
Antes de novas importações, busque conhecimento prévio:
- Arquivos similares processados antes
- Mapeamentos que funcionaram
- Confiança baseada em histórico

### 3. `generate_reflection`
Após múltiplos episódios, gere reflexões:
- Padrões que emergem dos dados
- Áreas problemáticas (correções frequentes)
- Recomendações de melhoria

### 4. `get_adaptive_threshold`
Calcule threshold adaptativo para HIL:
- Histórico de sucesso → confia mais na IA
- Correções recentes → seja mais cauteloso

## 📋 Formato de Resposta

**SEMPRE** responda em JSON estruturado:
```json
{
  "success": true,
  "action": "nome_da_acao",
  "result": { ... }
}
```

## 🌍 Linguagem

- Interface: Português brasileiro (pt-BR)
- Logs técnicos: Inglês (para debugging)

## ⚠️ Regras Importantes

1. **NUNCA** ignore conhecimento prévio relevante
2. **SEMPRE** valide mapeamentos contra schema atual
3. **FILTRE** mapeamentos para colunas que não existem mais
4. **APRENDA** com correções do usuário (reinforcement learning)
5. **EMITA** eventos para Agent Room (transparência)

## 🎯 Filosofia

> "A cada import, o sistema fica mais inteligente.
> João corrige uma vez → Maria nunca precisa corrigir igual."
"""


# =============================================================================
# Agent Factory
# =============================================================================

def create_learning_agent() -> Agent:
    """
    Create the LearningAgent using Google ADK.

    The agent is configured with:
    - Gemini 2.0 Flash model (fast, cost-effective)
    - 4 specialized tools for memory operations
    - Detailed instructions in Portuguese

    Returns:
        Configured Google ADK Agent
    """
    return Agent(
        model=MODEL,
        name=AGENT_NAME,
        instruction=LEARNING_INSTRUCTION,
        tools=[
            create_episode_tool,
            retrieve_prior_knowledge_tool,
            generate_reflection_tool,
            get_adaptive_threshold_tool,
        ],
    )
