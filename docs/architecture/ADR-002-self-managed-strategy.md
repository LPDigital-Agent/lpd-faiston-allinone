# ADR-002: Self-Managed Strategy Pattern for Agent Memory

**Status:** Accepted
**Date:** January 2026
**Decision Makers:** Architecture Team
**Context:** NEXO Memory Architecture Audit

---

## Summary

We will use a **self-managed strategy pattern** with custom tools for memory extraction and consolidation instead of AWS AgentCore built-in strategies.

---

## Context

AWS Bedrock AgentCore Memory supports three strategy types:

1. **Built-in Strategy**: AWS-managed extraction with default LLM prompts
2. **Built-in with Overrides**: AWS-managed with custom prompts/models
3. **Self-Managed Strategy**: Custom pipeline with SNS/S3/Lambda

NEXO requires specialized memory handling for file import intelligence that built-in strategies cannot provide.

---

## Decision

We chose **self-managed strategy pattern** implemented through custom LearningAgent tools.

```
┌──────────────────────────────────────────────────────────────────┐
│                    SELF-MANAGED STRATEGY (NEXO)                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Input Event                    Custom Extraction                 │
│  (CreateEvent)    ──────►       (LearningAgent Tools)            │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ LearningAgent Custom Tools:                                  │ │
│  │                                                              │ │
│  │ • create_episode_tool                                        │ │
│  │   - ImportEpisode structured schema                          │ │
│  │   - File signature computation                               │ │
│  │   - Lesson extraction                                        │ │
│  │                                                              │ │
│  │ • retrieve_prior_knowledge_tool                              │ │
│  │   - Semantic query with namespace                            │ │
│  │   - Voting-based aggregation                                 │ │
│  │   - Schema-aware filtering                                   │ │
│  │                                                              │ │
│  │ • generate_reflection_tool                                   │ │
│  │   - Cross-episode pattern detection                          │ │
│  │   - Custom consolidation logic                               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Rationale

### 1. Domain-Specific Data Structure

Built-in strategies use generic JSON. NEXO requires **ImportEpisode** schema:

```python
@dataclass
class ImportEpisode:
    episode_id: str
    filename_pattern: str      # Normalized (dates → DATE)
    file_signature: str        # Hash of column structure
    sheet_count: int
    total_rows: int
    sheets_info: List[Dict]
    column_mappings: Dict[str, str]
    user_corrections: Dict[str, Any]
    success: bool
    match_rate: float
    items_processed: int
    schema_version: str        # Track schema changes
    target_table: str
```

### 2. Custom Similarity Scoring

Built-in uses generic embeddings. NEXO uses **file signature matching**:

```python
def _compute_file_signature(file_analysis: Dict) -> str:
    """Hash based on column structure for exact matching."""
    sig_parts = []
    for sheet in file_analysis["sheets"]:
        col_names = sorted([c["name"].lower() for c in sheet["columns"][:20]])
        sig_parts.append(":".join(col_names[:10]))
    return hashlib.md5("|".join(sig_parts).encode()).hexdigest()[:16]
```

**Result**: Exact structure matches get 0.6 similarity boost.

### 3. Schema-Aware Validation

Built-in has no schema awareness. NEXO filters **stale mappings**:

```python
def _filter_stale_mappings(mappings, target_table):
    """Remove mappings to columns that no longer exist."""
    filtered = {}
    for column, mapping in mappings.items():
        if _validate_column_exists(target_table, mapping["field"]):
            filtered[column] = mapping
    return filtered
```

### 4. Voting-Based Aggregation

Built-in returns raw results. NEXO **aggregates with voting**:

```python
def _aggregate_mappings(episodes: List[Tuple[Dict, float]]) -> Dict:
    """Similarity-weighted voting across episodes."""
    for episode, similarity in episodes:
        for column, field in episode["column_mappings"].items():
            mapping_votes[column][field] += similarity
    # Winner = highest weighted vote
```

---

## Alternatives Considered

### Alternative 1: Built-in Strategy (AWS Managed)

```yaml
# .bedrock_agentcore.yaml
memory:
  strategies:
    - type: SEMANTIC_MEMORY
      prompt: "Extract import patterns..."
```

**Pros:**
- Zero custom code
- AWS-managed scaling
- Automatic consolidation

**Cons:**
- Generic extraction (no ImportEpisode)
- No file signature matching
- No schema validation
- No voting aggregation

**Rejected because:** Cannot meet domain-specific requirements.

### Alternative 2: Built-in with Prompt Overrides

```yaml
memory:
  strategies:
    - type: SEMANTIC_MEMORY
      prompt: |
        Extract ImportEpisode with schema:
        - filename_pattern
        - file_signature
        ...
```

**Pros:**
- Custom schema via prompt
- AWS-managed infrastructure

**Cons:**
- Prompt-based extraction unreliable
- No compile-time validation
- Still no schema-aware filtering
- Still no file signature matching

**Rejected because:** Prompt-only customization insufficient.

### Alternative 3: Full Self-Managed (SNS/S3/Lambda)

```yaml
memory:
  strategies:
    - type: SELF_MANAGED
      sns_topic_arn: arn:aws:sns:...
      s3_bucket: nexo-memory-raw
```

**Pros:**
- Full control
- AWS event-driven

**Cons:**
- Infrastructure overhead (SNS, S3, Lambda)
- Cold start latency
- Complex debugging

**Rejected because:** Tool-based approach simpler for current scale.

---

## Implementation

### Memory APIs Used

| API | Tool | Purpose |
|-----|------|---------|
| `MemoryClient.create_event()` | `create_episode_tool` | Store episodes |
| `MemoryClient.query()` | `retrieve_prior_knowledge_tool` | Semantic search |
| `MemoryClient.get_reflections()` | `retrieve_prior_knowledge_tool` | Get patterns |

### Code References

| File | Purpose |
|------|---------|
| `dist/learning/tools/create_episode.py` | Episode storage |
| `dist/learning/tools/retrieve_prior_knowledge.py` | Prior knowledge retrieval |
| `dist/learning/tools/generate_reflection.py` | Pattern consolidation |
| `dist/learning/agent.py` | LearningAgent entry point |

> **Note:** Agent code resides in `server/agentcore-inventory/dist/` folder.
> See [AGENT_CATALOG.md](../AGENT_CATALOG.md) for complete agent specifications.

### A2A Delegation Pattern

Other agents delegate memory operations to LearningAgent:

```python
# From NexoImportAgent (or any other agent)
from shared.a2a_client import a2a_invoke

await a2a_invoke(
    agent="learning",
    tool="create_episode_tool",
    params={...}
)
```

**Benefits:**
- Single point of memory management
- Consistent patterns across all agents
- Centralized logging and error handling

---

## Consequences

### Positive

1. **Domain-specific extraction**: ImportEpisode schema enforced
2. **High matching accuracy**: File signature + pattern matching
3. **Schema evolution safe**: Stale mappings automatically filtered
4. **Confidence calculation**: Voting provides reliable scores
5. **Full control**: Custom logic without AWS constraints

### Negative

1. **Custom code maintenance**: Tools require ongoing updates
2. **No AWS auto-scaling**: Must handle scaling ourselves
3. **Testing complexity**: More unit tests needed
4. **Documentation burden**: Must document custom patterns

### Mitigations

| Risk | Mitigation |
|------|------------|
| Code maintenance | Comprehensive test coverage |
| Scaling | AgentCore handles underlying infrastructure |
| Documentation | ADRs + inline code comments |

---

## Comparison: Strategy Types

| Aspect | Built-in | Built-in+Override | Self-Managed (NEXO) |
|--------|----------|-------------------|---------------------|
| **Extraction** | Generic LLM | Custom prompt | **Custom code** |
| **Schema** | JSON blob | JSON blob | **ImportEpisode dataclass** |
| **Similarity** | Embeddings | Embeddings | **File signature + embeddings** |
| **Validation** | None | None | **Schema-aware** |
| **Aggregation** | Raw results | Raw results | **Voting-based** |
| **Infrastructure** | AWS managed | AWS managed | **Tools (minimal)** |
| **Complexity** | Low | Medium | **High** |
| **Control** | Low | Medium | **Full** |

---

## Related ADRs

- **ADR-001**: [GLOBAL Namespace Design](./ADR-001-global-namespace.md)
- **ADR-003**: [Gemini 3.0 Model Selection](./ADR-003-gemini-model-selection.md)

---

## Review

| Date | Reviewer | Status |
|------|----------|--------|
| Jan 2026 | Memory Architecture Audit | Validated |

---

*This ADR documents an intentional architectural decision. Changes require team review.*
