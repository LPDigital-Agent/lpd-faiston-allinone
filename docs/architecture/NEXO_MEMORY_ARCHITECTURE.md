# NEXO Memory Architecture

> **Memória Humana para Agentes IA** - Como NEXO aprende e lembra como um ser humano

---

## Executive Summary

NEXO implementa uma arquitetura de memória inspirada na cognição humana, onde **cada decisão é armazenada imediatamente** e **cada ação consulta experiências passadas**. Não é um sistema tradicional de cache - é memória episódica, semântica e procedural que evolui com cada interação.

---

## 1. Modelo Cognitivo

### 1.1 Analogia com Memória Humana

| Memória Humana | Equivalente NEXO | Implementação |
|----------------|------------------|---------------|
| **Memória de Trabalho** | Session State | `ImportSession` object (in-memory) |
| **Memória de Curto Prazo** | Short-Term Memory (STM) | AgentCore STM API |
| **Memória de Longo Prazo** | Long-Term Memory (LTM) | AgentCore LTM + RAG |
| **Memória Episódica** | Experience Episodes | Individual interaction records |
| **Memória Semântica** | Knowledge Schemas | Learned patterns and mappings |
| **Memória Procedural** | Behavioral Patterns | Successful workflow sequences |

### 1.2 Arquitetura de Memória

```
┌─────────────────────────────────────────────────────────────┐
│                    NEXO MEMORY ARCHITECTURE                  │
│              (Baseado em Memória Humana)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ WORKING MEMORY  │◄──►│  SHORT-TERM     │                │
│  │ (Sessão Atual)  │    │  MEMORY (STM)   │                │
│  │                 │    │ AgentCore STM   │                │
│  │ - Respostas     │    │                 │                │
│  │ - Contexto      │    │ - Últimas horas │                │
│  │ - Reasoning     │    │ - Decisões      │                │
│  └────────┬────────┘    │   recentes      │                │
│           │             └────────┬────────┘                │
│           │                      │                         │
│           │    CONSOLIDAÇÃO      │                         │
│           │    (learn_from_      │                         │
│           │     import)          ▼                         │
│           │             ┌─────────────────┐                │
│           │             │   LONG-TERM     │                │
│           └────────────►│   MEMORY (LTM)  │                │
│                         │ AgentCore LTM   │                │
│                         │                 │                │
│                         │ - Episodic      │                │
│                         │   (experiências)│                │
│                         │ - Semantic      │                │
│                         │   (schemas)     │                │
│                         │ - Procedural    │                │
│                         │   (padrões)     │                │
│                         └─────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Princípios Fundamentais

### 2.1 Aprendizado Contínuo (Continuous Learning)

**REGRA**: Cada decisão do usuário DEVE ser armazenada IMEDIATAMENTE.

```python
# ❌ ERRADO: Armazenar apenas no final
def complete_import(session):
    # ... executa toda a importação ...
    learn_from_import(session)  # Só aprende no fim

# ✅ CORRETO: Armazenar cada decisão imediatamente
async def _handle_column_creation_answer(session, column, answer):
    # Processa a resposta...
    session.learned_mappings[column] = answer

    # IMEDIATAMENTE grava na memória
    await _learn_answer_immediately(
        session=session,
        question_type="column_creation",
        file_column=column,
        answer=answer,
    )
```

### 2.2 Recall Before Ask (Consultar Antes de Perguntar)

**REGRA**: Antes de gerar qualquer pergunta, consultar se existe resposta similar na memória.

```python
# ❌ ERRADO: Perguntar sem consultar memória
def generate_question(column):
    return NexoQuestion(
        topic="column_creation",
        column=column,
        question="Como mapear esta coluna?",
    )

# ✅ CORRETO: Consultar memória primeiro
async def generate_question(column, user_id):
    # Primeiro, tentar lembrar
    similar_answer = await _recall_similar_answer(
        file_column=column,
        user_id=user_id,
    )

    if similar_answer and similar_answer["confidence"] >= 0.85:
        # Auto-aplicar resposta lembrada
        return None  # Não precisa perguntar

    # Só pergunta se não lembra
    return NexoQuestion(...)
```

### 2.3 Memory-Aware ReAct Pattern

O padrão ReAct (Reason + Act) DEVE incluir consulta à memória em cada fase:

| Fase ReAct | Ação de Memória |
|------------|-----------------|
| **OBSERVE** | Recall `prior_knowledge` da LTM |
| **THINK** | Usar padrões aprendidos no raciocínio |
| **ASK** | Recall respostas similares antes de perguntar |
| **LEARN** (contínuo) | Gravar cada resposta em STM |
| **ACT** | Usar configurações que funcionaram |
| **LEARN** (final) | Consolidar STM → LTM |

---

## 3. Implementação Técnica

### 3.1 Estruturas de Dados

#### ImportSession (Working Memory)

```python
@dataclass
class ImportSession:
    """Memória de trabalho para a sessão atual."""
    session_id: str
    user_id: str
    filename: str

    # Aprendizado ativo
    learned_mappings: Dict[str, str] = field(default_factory=dict)
    requested_new_columns: List[RequestedNewColumn] = field(default_factory=list)

    # Trace de raciocínio (para explicabilidade)
    reasoning_trace: List[ReasoningStep] = field(default_factory=list)

    # Conhecimento prévio (loaded from LTM)
    prior_knowledge: Optional[Dict[str, Any]] = None
```

#### RequestedNewColumn (Pending Decision)

```python
@dataclass
class RequestedNewColumn:
    """Coluna pendente de decisão do usuário."""
    source_file_column: str
    suggested_name: str
    suggested_type: str
    sample_values: Optional[List[str]] = None
    approved: bool = False  # CRITICAL: Marcar True após resposta
```

### 3.2 Funções de Memória

#### Gravar Decisão Imediatamente

```python
async def _learn_answer_immediately(
    self,
    session: ImportSession,
    question_type: str,
    file_column: str,
    answer: str,
    context: Dict[str, Any] = None,
) -> None:
    """
    Grava imediatamente cada resposta do usuário na memória.
    Simula consolidação de memória humana - cada experiência é armazenada.

    Usa Short-Term Memory do AgentCore para acesso rápido.
    """
    from agents.learning_agent import create_learning_agent

    learning_agent = create_learning_agent()

    episode = {
        "type": "answer_decision",
        "question_type": question_type,
        "file_column": file_column,
        "answer": answer,
        "context": {
            "filename": session.filename,
            "file_type": session.file_analysis.get("detected_type") if session.file_analysis else None,
            "user_id": session.user_id,
            "timestamp": now_iso(),
            **(context or {}),
        },
    }

    await learning_agent.store_short_term(
        session_id=session.session_id,
        episode=episode,
    )
```

#### Consultar Respostas Similares

```python
async def _recall_similar_answer(
    self,
    file_column: str,
    file_type: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Consulta memória por respostas similares anteriores.
    Simula memória episódica humana - lembrar de experiências passadas.
    """
    from agents.learning_agent import create_learning_agent

    learning_agent = create_learning_agent()

    result = await learning_agent.retrieve_similar(
        query={
            "question_type": "column_creation",
            "file_column": file_column,
            "file_type": file_type,
            "user_id": user_id,
        },
        limit=5,
    )

    if result and result.get("matches"):
        best_match = result["matches"][0]
        return {
            "answer": best_match["answer"],
            "confidence": best_match["similarity_score"],
            "source_episode": best_match["episode_id"],
        }

    return None
```

### 3.3 Integração com AgentCore Memory

NEXO utiliza as APIs de memória do AWS Bedrock AgentCore:

```python
# Short-Term Memory (STM) - Decisões recentes
await agentcore.memory.store_short_term(
    session_id=session_id,
    content=episode,
    ttl_hours=24,  # Expira após 24h
)

# Long-Term Memory (LTM) - Conhecimento permanente
await agentcore.memory.store_long_term(
    user_id=user_id,
    memory_type="episodic",
    content=consolidated_knowledge,
)

# RAG Retrieval - Busca semântica
results = await agentcore.memory.retrieve(
    query=semantic_query,
    memory_type="semantic",
    limit=10,
)
```

---

## 4. Fluxo de Importação com Memória

### 4.1 Diagrama de Sequência

```
┌─────────┐     ┌────────────┐     ┌─────────────┐     ┌─────────────┐
│  User   │     │   NEXO     │     │   Memory    │     │  AgentCore  │
│ Browser │     │   Agent    │     │   Layer     │     │   LTM/STM   │
└────┬────┘     └─────┬──────┘     └──────┬──────┘     └──────┬──────┘
     │                │                    │                   │
     │  Upload File   │                    │                   │
     │───────────────►│                    │                   │
     │                │                    │                   │
     │                │  Recall Prior      │                   │
     │                │  Knowledge         │                   │
     │                │───────────────────►│                   │
     │                │                    │   Query LTM       │
     │                │                    │──────────────────►│
     │                │                    │◄──────────────────│
     │                │◄───────────────────│                   │
     │                │                    │                   │
     │                │  OBSERVE: Analyze  │                   │
     │                │  with context      │                   │
     │                │                    │                   │
     │                │  For each column:  │                   │
     │                │  ┌────────────────┐│                   │
     │                │  │Recall Similar  ││                   │
     │                │  │Answer          ││                   │
     │                │  │                ││                   │
     │                │  │Found? Auto-    ││                   │
     │                │  │apply & skip    ││                   │
     │                │  └────────────────┘│                   │
     │                │                    │                   │
     │  Question      │                    │                   │
     │◄───────────────│                    │                   │
     │                │                    │                   │
     │  Answer        │                    │                   │
     │───────────────►│                    │                   │
     │                │                    │                   │
     │                │  Store Answer      │                   │
     │                │  Immediately       │                   │
     │                │───────────────────►│                   │
     │                │                    │   Store STM       │
     │                │                    │──────────────────►│
     │                │                    │                   │
     │                │         ...        │                   │
     │                │                    │                   │
     │  Import Done   │                    │                   │
     │◄───────────────│                    │                   │
     │                │                    │                   │
     │                │  Consolidate       │                   │
     │                │  to LTM            │                   │
     │                │───────────────────►│                   │
     │                │                    │   Store LTM       │
     │                │                    │──────────────────►│
     │                │                    │                   │
```

### 4.2 Passo a Passo

1. **Upload do Arquivo**
   - Usuário envia arquivo (CSV, XLSX)
   - NEXO cria `ImportSession`

2. **Recall Prior Knowledge** (OBSERVE)
   - Consulta LTM: mapeamentos anteriores deste usuário
   - Consulta LTM: schemas conhecidos para este tipo de arquivo
   - Carrega em `session.prior_knowledge`

3. **Análise com Contexto** (THINK)
   - Gemini analisa arquivo COM conhecimento prévio
   - Confiança aumenta se padrões conhecidos são detectados

4. **Para Cada Coluna Nova** (ASK com Memory)
   - **Recall**: Busca resposta similar em STM/LTM
   - Se `confidence >= 0.85`: Auto-aplica resposta, não pergunta
   - Se `confidence < 0.85`: Gera pergunta para usuário

5. **Processa Resposta** (LEARN contínuo)
   - Aplica resposta na sessão
   - **IMEDIATAMENTE** grava em STM
   - Marca `approved = True` para evitar repetição

6. **Executa Importação** (ACT)
   - Usa mapeamentos confirmados
   - Insere dados no PostgreSQL

7. **Consolida Memória** (LEARN final)
   - Converte experiências STM → LTM
   - Atualiza schemas semânticos
   - Registra padrões procedurais

---

## 5. Guidelines para Desenvolvimento

### 5.1 OBRIGATÓRIO (MANDATORY)

- [ ] **Toda resposta do usuário DEVE ser gravada imediatamente** em STM
- [ ] **Toda pergunta DEVE consultar memória** antes de ser gerada
- [ ] **Flags de estado (`approved`, `processed`)** DEVEM ser marcados em TODAS as branches
- [ ] **Prior knowledge DEVE ser carregado** no início de cada sessão
- [ ] **Consolidação LTM DEVE ocorrer** ao final de cada fluxo bem-sucedido

### 5.2 PROIBIDO (FORBIDDEN)

- [ ] ❌ Gerar perguntas sem consultar memória
- [ ] ❌ Armazenar aprendizado apenas no final do fluxo
- [ ] ❌ Ignorar respostas similares de alta confiança
- [ ] ❌ Implementar cache manual fora do AgentCore Memory
- [ ] ❌ Esquecer de marcar flags de estado após processar respostas

### 5.3 Checklist de Implementação

Ao criar novos agentes ou features que usam memória:

```markdown
## Memory Integration Checklist

- [ ] Carrega prior_knowledge no início da sessão
- [ ] Consulta STM antes de gerar cada pergunta
- [ ] Grava cada decisão do usuário imediatamente em STM
- [ ] Marca flags de estado (approved, processed) em todas as branches
- [ ] Consolida aprendizado em LTM ao final do fluxo
- [ ] Trata erros de memória graciosamente (fallback, não crash)
- [ ] Logs incluem [MEMORY] prefix para debug
```

---

## 6. Referências

### 6.1 AWS AgentCore Memory Documentation

- [Memory Overview](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html)
- [Memory Terminology](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-terminology.html)
- [Memory Types](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-types.html)
- [Memory Strategies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-strategies.html)
- [Built-in Strategies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/built-in-strategies.html)
- [Custom Strategies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-custom-strategy.html)
- [LTM with RAG](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-ltm-rag.html)

### 6.2 Related Architecture Documents

- [SGA Estoque Architecture](./SGA_ESTOQUE_ARCHITECTURE.md)
- [AgentCore Implementation Guide](../AgentCore/IMPLEMENTATION_GUIDE.md)
- [Agent Catalog](../AGENT_CATALOG.md)

### 6.3 Implementation Files

- **NexoImportAgent**: `server/agentcore-inventory/agents/nexo_import_agent.py`
- **LearningAgent**: `server/agentcore-inventory/agents/learning_agent.py`
- **Memory Tools**: `server/agentcore-inventory/tools/memory_tools.py`

---

*Last updated: January 2026*
*Author: Claude Code with prompt-engineer optimization*
