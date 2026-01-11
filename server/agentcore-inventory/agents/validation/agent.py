# =============================================================================
# ValidationAgent - Google ADK Agent Definition
# =============================================================================
# Validates data and mappings against PostgreSQL schema.
#
# Called by:
# - NexoImportAgent: Before import execution
# - SchemaEvolutionAgent: Before column creation
# =============================================================================

import os
from google.adk.agents import Agent

# Import tools
from agents.validation.tools import (
    validate_schema_tool,
    validate_data_tool,
    check_constraints_tool,
)


# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "validation"
AGENT_NAME = "ValidationAgent"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


# =============================================================================
# Agent Instruction
# =============================================================================

VALIDATION_INSTRUCTION = """Você é o **ValidationAgent** do sistema SGA (Sistema de Gestão de Ativos).

## 🎯 Seu Papel

Você é o **VALIDADOR** que garante a integridade dos dados antes da importação.

## 🔧 Suas Ferramentas

### 1. `validate_schema`
Valida mapeamentos de colunas contra o schema PostgreSQL:
- Campos existem na tabela?
- Tipos são compatíveis?
- Mapeamentos duplicados?

### 2. `validate_data`
Valida linhas de dados contra restrições:
- Valores obrigatórios presentes?
- Formatos corretos?
- Tamanhos dentro dos limites?

### 3. `check_constraints`
Verifica restrições do banco:
- Chaves estrangeiras válidas?
- Unicidade respeitada?
- Check constraints atendidos?

## 📋 Formato de Resposta

**SEMPRE** JSON estruturado:
```json
{
  "is_valid": true,
  "validation_score": 0.95,
  "errors": [],
  "warnings": [],
  "recommendations": []
}
```

## 🎓 Princípios

1. **Precisão**: Nunca deixe dados inválidos passarem
2. **Clareza**: Erros com mensagens acionáveis
3. **Proatividade**: Identifique problemas potenciais
4. **Performance**: Validação rápida para feedback imediato

## 🌍 Linguagem

Português brasileiro (pt-BR) para mensagens de erro.

## ⚠️ Regras Críticas

1. **NUNCA** modifique dados - apenas valide
2. **SEMPRE** retorne score de validação (0-1)
3. Erros são bloqueadores - warnings são informativos
4. Valide ANTES de qualquer operação de escrita
"""


# =============================================================================
# Agent Factory
# =============================================================================

def create_validation_agent() -> Agent:
    """
    Create the ValidationAgent using Google ADK.

    This agent validates data and mappings against the PostgreSQL schema
    and is called by NexoImportAgent before import execution.

    Returns:
        Configured Google ADK Agent
    """
    return Agent(
        model=MODEL,
        name=AGENT_NAME,
        instruction=VALIDATION_INSTRUCTION,
        tools=[
            validate_schema_tool,
            validate_data_tool,
            check_constraints_tool,
        ],
    )
