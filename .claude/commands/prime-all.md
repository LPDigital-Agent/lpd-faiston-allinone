---
name: prime-all
description: Load ALL modular rules from .claude/rules/ into context (full memory reload)
allowed-tools: Read, Bash, Glob
---

# Prime All Rules — Full Memory Reload

Purpose: Load **ALL** modular rules from `.claude/rules/` into active context when memory drifts mid-session.

Use this command when:
- Context has drifted and Claude is forgetting rules
- You need to force a full rules reload without `/clear`
- Starting a complex task that needs all policies active

---

## Phase 1: Core CLAUDE.md (Source of Truth)

```bash
echo "📚 LOADING: CLAUDE.md (Source of Truth)"
cat CLAUDE.md
```

---

## Phase 2: Global Rules (Always Active)

These rules apply to ALL files regardless of what you're working on.

### 2.1 Core Immutable Policies

```bash
echo ""
echo "🔒 LOADING: Core Immutable Rules"
cat .claude/rules/00-core-immutable.md
```

### 2.2 Execution Discipline

```bash
echo ""
echo "⚙️ LOADING: Execution Discipline"
cat .claude/rules/workflow/execution-discipline.md
```

### 2.3 Ralph Wiggum Loop Strategy

```bash
echo ""
echo "🔄 LOADING: Ralph Wiggum Loop"
cat .claude/rules/workflow/ralph-wiggum-loop.md
```

### 2.4 Context Engineering

```bash
echo ""
echo "🧠 LOADING: Context Engineering"
cat .claude/rules/workflow/context-engineering.md
```

### 2.5 Ultrathink Mode

```bash
echo ""
echo "💡 LOADING: Ultrathink Mode"
cat .claude/rules/workflow/ultrathink.md
```

### 2.6 Context Awareness & Impact Analysis

```bash
echo ""
echo "🎯 LOADING: Context Awareness"
cat .claude/rules/workflow/context-awareness.md
```

---

## Phase 3: Agent Rules (Strands + NEXO)

### 3.1 AWS Strands Framework

```bash
echo ""
echo "🤖 LOADING: Strands Framework Rules"
cat .claude/rules/agents/strands-framework.md
```

### 3.2 NEXO AGI Behavior

```bash
echo ""
echo "🧬 LOADING: NEXO AGI Rules"
cat .claude/rules/agents/nexo-agi.md
```

---

## Phase 4: Infrastructure Rules

### 4.1 AWS Configuration

```bash
echo ""
echo "☁️ LOADING: AWS Configuration"
cat .claude/rules/infrastructure/aws-config.md
```

### 4.2 Terraform Policies

```bash
echo ""
echo "🏗️ LOADING: Terraform Rules"
cat .claude/rules/infrastructure/terraform.md
```

### 4.3 Python/Lambda Standards

```bash
echo ""
echo "🐍 LOADING: Python/Lambda Rules"
cat .claude/rules/infrastructure/python-lambda.md
```

### 4.4 Frontend Rules

```bash
echo ""
echo "🖥️ LOADING: Frontend Rules"
cat .claude/rules/infrastructure/frontend.md
```

---

## Phase 5: Verification

```bash
echo ""
echo "✅ PRIME-ALL COMPLETE"
echo ""
echo "Loaded rules:"
find .claude/rules -name "*.md" -type f | wc -l
echo "rule files from .claude/rules/"
echo ""
echo "Memory is now fully primed with all policies."
```

---

## Post-Prime Checklist

After running `/prime-all`, you MUST:

1. ✅ Acknowledge the rules have been loaded
2. ✅ State the key constraints that apply to the current task
3. ✅ Confirm understanding of the AI-FIRST architecture
4. ✅ Proceed with the task following all loaded policies

---

## When to Use Each Prime Command

| Command | Use Case |
|---------|----------|
| `/prime` | After `/clear` - lightweight context + product orientation |
| `/prime-all` | Mid-session memory refresh - loads ALL rules without clearing |
| `/sync-project` | Before `/compact` - persist state to docs |

---

## Rule Summary (Quick Reference)

After loading, these are the active policy categories:

| Category | Key Points |
|----------|------------|
| **Core** | AI-First, HIL mandatory, no speculation, plan before code |
| **Agents** | Strands SDK, Gemini 2.5, AgentCore Memory, OBSERVE→THINK→LEARN→ACT |
| **NEXO** | Multi-round HIL, 80% confidence threshold, learning loop |
| **AWS** | Account 377311924364, us-east-2, profile faiston-aio |
| **Infra** | Terraform only, no CloudFormation, Aurora PostgreSQL |
| **Workflow** | Ralph Wiggum loop, SubAgents mandatory, ultrathink |
