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

    PADRÃO: Delega ao LearningAgent via A2A (JSON-RPC 2.0).
    LearningAgent usa MemoryClient.create_event() internamente.
    """
    # A2A delegation to LearningAgent (single point of memory management)
    from shared.a2a_client import a2a_invoke

    episode_data = {
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

    # Delegate to LearningAgent via A2A
    await a2a_invoke(
        agent="learning",
        tool="create_episode_tool",
        params={
            "user_id": session.user_id,
            "filename": session.filename,
            "file_analysis": session.file_analysis,
            "column_mappings": {file_column: answer},
            "user_corrections": {},
            "import_result": {"session_id": session.session_id, "success": True},
        },
    )
```

#### Consultar Respostas Similares

```python
async def _recall_similar_answer(
    self,
    file_column: str,
    file_type: str,
    user_id: str,
    file_analysis: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Consulta memória por respostas similares anteriores.
    Simula memória episódica humana - lembrar de experiências passadas.

    PADRÃO: Delega ao LearningAgent via A2A (JSON-RPC 2.0).
    LearningAgent usa MemoryClient.query() + agregação customizada.
    """
    # A2A delegation to LearningAgent (single point of memory management)
    from shared.a2a_client import a2a_invoke

    result = await a2a_invoke(
        agent="learning",
        tool="retrieve_prior_knowledge_tool",
        params={
            "user_id": user_id,
            "filename": f"query_{file_column}_{file_type}",
            "file_analysis": file_analysis,
            "target_table": "pending_entry_items",
        },
    )

    if result and result.get("suggested_mappings"):
        mappings = result["suggested_mappings"]
        if file_column in mappings:
            mapping = mappings[file_column]
            return {
                "answer": mapping["field"],
                "confidence": mapping["confidence"],
                "source_episode": mapping.get("source_episode", "aggregated"),
            }

    return None
```

### 3.3 AgentCore Memory Configuration

**Technical Details:**

```
Memory ID: nexo_agent_mem-Z5uQr8CDGf
Namespace: /strategy/import/company (GLOBAL)
Scope: Company-wide (not per-user)
Strategy: Self-managed (custom consolidation)
```

**Rationale:**
- **GLOBAL namespace** enables collective learning across all company users (see ADR-001)
- **Self-managed strategy** provides full control over consolidation logic (see ADR-002)
- **Single memory ID** ensures consistent knowledge base across all import sessions

### 3.4 Integração com AgentCore Memory

NEXO utiliza as APIs **oficiais** do AWS Bedrock AgentCore Memory SDK:

```python
from bedrock_agentcore.memory import MemoryClient

# Initialize client with memory ID
memory_client = MemoryClient(memory_id="nexo_agent_mem-Z5uQr8CDGf")

# =============================================================================
# CreateEvent - A ÚNICA API para armazenar memória
# =============================================================================
# CRITICAL: NÃO EXISTEM APIs store_short_term() ou store_long_term()!
# O CreateEvent armazena em STM automaticamente. A estratégia configurada
# (built-in ou self-managed) determina como os eventos são consolidados em LTM.

await memory_client.create_event(
    event_type="import_completed",          # Tipo do evento
    data=episode_data,                       # Dados do episódio
    namespace="/strategy/import/company",   # GLOBAL namespace!
    role="TOOL",                             # Quem criou (USER, AGENT, TOOL)
)

# =============================================================================
# Query - Busca semântica na memória
# =============================================================================
results = await memory_client.query(
    query="import file similar to inventory_report",  # Natural language
    namespace="/strategy/import/company",
    top_k=20,                                          # Máximo de resultados
)

# Iterar sobre resultados
for result in results:
    data = result.data        # Dados do evento
    score = result.score      # Similaridade semântica

# =============================================================================
# GetReflections - Recuperar padrões consolidados (LTM)
# =============================================================================
reflections = await memory_client.get_reflections(
    namespace="/strategy/import/company",
    query="column mapping patterns",
)

for ref in reflections:
    pattern = ref.text              # Padrão identificado
    confidence = ref.confidence     # Confiança do padrão
```

### 3.5 LLM Model Selection for Memory Operations

**Gemini 3.0 Family Configuration (per ADR-003):**

Memory operations use appropriate Gemini 3.0 models with extended reasoning capabilities:

| Agent | Model | Thinking Mode | Use Case |
|-------|-------|---------------|----------|
| **LearningAgent** | `gemini-3.0-pro` | HIGH | Memory consolidation, pattern extraction, schema evolution |
| **NexoImportAgent** | `gemini-3.0-pro` | HIGH | Recall operations, mapping decisions, confidence scoring |

**Why Thinking Mode for Memory?**

Thinking mode enhances memory operations through:
- **Deep reasoning** for pattern extraction from multiple episodes
- **Chain-of-thought** for complex mapping decisions (e.g., ambiguous column names)
- **Better confidence scoring** via step-by-step similarity analysis
- **Reduced hallucination** when aggregating historical data

Example: When consolidating 20 past import episodes, Thinking mode allows the LearningAgent to:
1. Identify common patterns across file structures
2. Detect edge cases and exceptions
3. Assign confidence scores based on consistency
4. Generate actionable reflections with reasoning traces

**Reference:** [ADR-003: Gemini Model Selection](./ADR-003-gemini-model-selection.md)

**Thinking Mode Integration in Memory Workflows:**

```python
# LearningAgent: Memory Consolidation with Thinking
from strands_agents import LLM

llm = LLM(
    model="gemini-3.0-pro",
    thinking={
        "mode": "HIGH",  # Extended reasoning for pattern extraction
        "budget": "medium",  # Balance speed vs. depth
    }
)

# Example: Consolidating 20 import episodes
# Thinking mode enables:
# 1. Multi-step pattern recognition across episodes
# 2. Confidence scoring via reasoning chains
# 3. Detection of conflicting mappings with explanations
# 4. Generation of actionable reflections with justifications
```

**Practical Impact:**

Without Thinking mode:
- Simple similarity matching (embeddings only)
- Confidence scores based on frequency
- May miss context-dependent patterns

With Thinking mode:
- Reasoning chains analyze WHY patterns succeed/fail
- Confidence includes context similarity + success rate + edge cases
- Auto-detects schema evolution and filters stale mappings

### 3.6 Arquitetura de Memória: Self-Managed Strategy

NEXO implementa um **self-managed strategy pattern** para controle total sobre a consolidação de memória:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SELF-MANAGED STRATEGY                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐│
│  │  CreateEvent │────►│  AgentCore STM   │────►│  Raw Events  ││
│  │  (Tool)      │     │  (Automatic)     │     │  Storage     ││
│  └──────────────┘     └──────────────────┘     └──────────────┘│
│                                                       │         │
│                              CUSTOM EXTRACTION        │         │
│                              (generate_reflection)    ▼         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LearningAgent Tools (Custom)                 │  │
│  │  • create_episode_tool: Captura experiências completas   │  │
│  │  • retrieve_prior_knowledge_tool: Busca + agregação      │  │
│  │  • generate_reflection_tool: Consolida padrões           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ✅ Benefits:                                                    │
│  • Full control over what gets extracted to LTM                 │
│  • Custom similarity scoring with file signatures               │
│  • Schema-aware validation (filter stale mappings)              │
│  • Voting-based aggregation for confidence calculation          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Por que Self-Managed?**

| Aspecto | Built-in Strategy | Self-Managed (NEXO) |
|---------|-------------------|---------------------|
| Extração | Automática (LLM genérico) | **Custom** (ImportEpisode schema) |
| Consolidação | Período fixo | **On-demand** (após cada import) |
| Validação | Nenhuma | **Schema-aware** (filtra mappings obsoletos) |
| Similaridade | Embeddings genéricos | **File signature + pattern matching** |

**Namespace Strategy: GLOBAL**

```python
MEMORY_NAMESPACE = "/strategy/import/company"  # GLOBAL!
```

- **Design Intencional**: Aprendizado coletivo da empresa
- O que João aprende, Maria pode usar automaticamente
- Decisão documentada em: `docs/architecture/ADR-001-global-namespace.md`

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
- [ADR-001: GLOBAL Namespace](./ADR-001-global-namespace.md)
- [ADR-002: Self-Managed Strategy](./ADR-002-self-managed-strategy.md)
- [ADR-003: Gemini Model Selection](./ADR-003-gemini-model-selection.md)

### 6.3 Implementation Files

- **NexoImportAgent**: `server/agentcore-inventory/dist/nexo_import/agent.py`
- **LearningAgent**: `server/agentcore-inventory/dist/learning/agent.py`
- **Create Episode Tool**: `server/agentcore-inventory/dist/learning/tools/create_episode.py`
- **Retrieve Prior Knowledge**: `server/agentcore-inventory/dist/learning/tools/retrieve_prior_knowledge.py`
- **Generate Reflection Tool**: `server/agentcore-inventory/dist/learning/tools/generate_reflection.py`

> **Note:** All agent implementations now live in `dist/` (build artifacts) following the Strands A2A migration. Source files are no longer maintained in `agents/`.

### 6.4 Architecture Decision Records (ADRs)

- **ADR-001**: [GLOBAL Namespace Design](./ADR-001-global-namespace.md)
- **ADR-002**: [Self-Managed Strategy Pattern](./ADR-002-self-managed-strategy.md)
- **ADR-003**: [Gemini 3.0 Model Selection + Thinking](./ADR-003-gemini-model-selection.md)

---

*Last updated: January 2026*
*Author: Claude Code with prompt-engineer optimization*
*Reviewed: Memory Architecture Audit (January 2026)*
