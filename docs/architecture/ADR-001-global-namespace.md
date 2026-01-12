# ADR-001: GLOBAL Namespace Design for Agent Memory

**Status:** Accepted
**Date:** January 2026
**Decision Makers:** Architecture Team
**Context:** NEXO Memory Architecture Audit

---

## Summary

We will use a **GLOBAL namespace** (`/strategy/import/company`) for all agent memory operations instead of per-user namespaces.

---

## Context

When designing the NEXO agent memory architecture, we had to decide how to organize memory namespaces in AWS Bedrock AgentCore Memory. The two primary options were:

1. **Per-User Namespace**: `/strategy/import/user/{user_id}`
2. **Global Namespace**: `/strategy/import/company`

### Background

NEXO's LearningAgent captures import experiences (episodes) to improve future import accuracy. These episodes include:
- File structure patterns
- Column mappings learned
- User corrections
- Success/failure outcomes

---

## Decision

We chose **GLOBAL namespace** (`/strategy/import/company`) for all agent memory operations.

```python
# From: server/agentcore-inventory/dist/learning/tools/create_episode.py
MEMORY_NAMESPACE = "/strategy/import/company"  # GLOBAL!
```

---

## Rationale

### 1. Collective Learning Benefit

The primary business value is **company-wide knowledge sharing**:

| Scenario | Per-User | GLOBAL (Chosen) |
|----------|----------|-----------------|
| João maps "SERIAL_NUMBER" → "serial_number" | Only João benefits | Maria auto-applies same mapping |
| 10 users import similar files | Each learns independently | All benefit from aggregated patterns |
| New employee joins | Starts from zero | Inherits company knowledge |

### 2. Pattern Aggregation

The `retrieve_prior_knowledge_tool` uses **voting-based aggregation**:

```python
# Multiple episodes vote on correct mapping
for episode, similarity in episodes:
    for column, field in episode["column_mappings"].items():
        mapping_votes[column][field] += similarity
```

GLOBAL namespace provides more data points for confident decisions.

### 3. Schema Evolution Awareness

GLOBAL namespace combined with schema versioning ensures:
- Mappings to non-existent columns are filtered
- Schema evolution doesn't break cross-user learning

```python
# From: retrieve_prior_knowledge.py:158-170
def _filter_stale_mappings(mappings, target_table):
    """Filter out mappings that reference non-existent columns."""
    for column, mapping_info in mappings.items():
        if _validate_column_exists(target_table, target_field):
            filtered[column] = mapping_info
```

---

## Alternatives Considered

### Alternative 1: Per-User Namespace

```python
MEMORY_NAMESPACE = f"/strategy/import/user/{user_id}"
```

**Pros:**
- User-specific learning
- No cross-user contamination
- Privacy by design

**Cons:**
- Each user learns independently (slower)
- Duplicate learning effort
- Less data for pattern aggregation

**Rejected because:** Business value of collective learning outweighs individual isolation.

### Alternative 2: Hybrid (Per-User + Global Read)

```python
# Write to user namespace
await create_event(namespace=f"/user/{user_id}")
# Read from both
results = await query(namespaces=[f"/user/{user_id}", "/company"])
```

**Pros:**
- User preferences preserved
- Global patterns available

**Cons:**
- Implementation complexity
- Query performance impact
- Conflict resolution logic needed

**Rejected because:** Complexity not justified for current use case.

---

## Consequences

### Positive

1. **Faster learning curve**: New patterns propagate to all users immediately
2. **Higher confidence**: More data points for mapping decisions
3. **Reduced HIL**: Auto-apply threshold (0.85) reached faster with aggregated data
4. **Simpler architecture**: Single namespace to manage

### Negative

1. **No per-user customization**: User A's preference doesn't override User B's correction
2. **Privacy consideration**: All users can theoretically query each other's patterns
3. **Bad pattern propagation**: Incorrect mapping could spread (mitigated by success weighting)

### Mitigations

| Risk | Mitigation |
|------|------------|
| Bad pattern propagation | Success-weighted voting (failed imports weight = 0) |
| Privacy | Episodes don't contain PII (only structural patterns) |
| Conflicts | Confidence threshold prevents low-confidence auto-apply |

---

## Implementation

### Code References

| File | Purpose |
|------|---------|
| `dist/learning/tools/create_episode.py` | Namespace constant + event creation |
| `dist/learning/tools/retrieve_prior_knowledge.py` | Namespace constant + query logic |

> **Note:** Agent code resides in `server/agentcore-inventory/dist/` folder.

### Configuration

```yaml
# .bedrock_agentcore.yaml
memory:
  mode: STM_AND_LTM
  memory_id: nexo_agent_mem-Z5uQr8CDGf
  event_expiry_days: 30
  # Namespace managed at application level
```

---

## Related ADRs

- **ADR-002**: [Self-Managed Strategy Pattern](./ADR-002-self-managed-strategy.md)
- **ADR-003**: [Gemini 3.0 Model Selection](./ADR-003-gemini-model-selection.md)

---

## Review

| Date | Reviewer | Status |
|------|----------|--------|
| Jan 2026 | Memory Architecture Audit | Validated |

---

*This ADR documents an intentional architectural decision. Changes require team review.*
