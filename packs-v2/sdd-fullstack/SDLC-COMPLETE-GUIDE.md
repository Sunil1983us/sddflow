# Complete SDLC Guide
# SDD — 9 Commands, Constitution Generated from Context

---

## Overview

You write one context file (or run `/create-context` first if you'd
rather paste rough notes — covering backend, frontend, or both — and have
the agent draft it with you — see .specify/contexts/CONTEXT-GUIDE.md).
Agent generates everything else.
Constitution Part 2 is auto-generated — never manually filled.
PLAN is split into 4 sub-commands — each reviewed separately.

---

## The 9 Commands

| # | Command | Does | Gate Before |
|---|---|---|---|
| 1 | `/specify` | Constitution Part 2 + spec docs | None |
| 2 | `/analyze` | Risks + dependencies + complexity | After /specify |
| 3 | `/clarify` | Questions → you answer | After /analyze |
| 4 | `/plan-arch` | Architecture + plan.md | clarify.summary.md |
| 5 | `/plan-hld` | HLD + Mermaid diagrams | arch.md reviewed |
| 6 | `/plan-lld` | LLD (mvp+ only) | hld.md reviewed |
| 7 | `/plan-adr` | ADRs (mvp+ only) | arch.md reviewed |
| 8 | `/task` | Stories + Tasks + Jira | hld.md reviewed |
| 9 | `/implement` | One task at a time | tasks approved |

---

## /specify — Two Actions

**Action 1 — Constitution Part 2:**
Reads context → fills Tech Stack, split Backend / Frontend / Shared:
Backend:  Language, Framework, Build Tool, Messaging/Async, Schema,
          Data Store, Data Cache, DB Migration, Resilience, Testing,
          Coverage Gate
Frontend: Language, Framework, Build Tool, State Management, Component
          Library/Design System, Routing, API Client, Data Cache,
          Testing, Coverage Gate, Accessibility
Shared:   API Style, Serialisation, Configuration, Secrets,
          Observability, Logging, Quality/Security, Orchestration, CI/CD

Also extracts: Core Principles, Domain Rules, Never Do

**Action 2 — Spec Documents:**
BRD → SRD → Analyze → HLD (pilot) + more per scope

---

## PLAN — 4 Sub-Commands

```
/plan-arch   Architecture decisions + plan.md
             Who reviews: Tech lead
             ↓
/plan-hld    HLD + all Mermaid diagrams
             Who reviews: Stakeholders + tech lead
             ↓
/plan-lld    LLD + class/sequence diagrams (mvp+ only)
             Who reviews: Senior developer
             ↓
/plan-adr    Architecture Decision Records (mvp+ only)
             Who reviews: Architect
```

**Pilot scope:** only /plan-arch and /plan-hld required.
Agent auto-skips /plan-lld and /plan-adr for pilot — states reason.

---

## Pilot Flow
```
/specify → /analyze → /clarify
→ /plan-arch (review) → /plan-hld (review)
→ /task (review) → /implement
```

## MVP+ Flow
```
/specify → /analyze → /clarify
→ /plan-arch (review) → /plan-hld (review)
→ /plan-lld (review) → /plan-adr (review)
→ /task (review) → /implement
```

---

## PR Rules (enforced at /implement)

Every task before coding:
1. Agent estimates lines
2. If > max_lines_per_pr → SPLIT A/B/C → confirm → one at a time
3. After task → state files + lines + "PR ready" → wait for go

---

## Feature → Story → Task (/task)

```
FEATURE (from BRD)
  └── STORY (As/I want/So that — linked to FRs)
        ├── Story points + Sprint
        ├── Acceptance criteria
        └── TASK (one PR each)
              ├── Estimated lines
              └── PR strategy: single or SPLIT
```

Jira CSV generated at /task — import before /implement starts.

---

## Change Management

Rule: context.md first — always.

```
Update context.md + CHANGELOG
→ Re-run /specify for affected docs only
→ Re-run /analyze if risk changed
→ Append CHG-NNN tasks
→ /implement CHG tasks (same PR rules)
```

---

## Full Checklist

### Setup
- [ ] manifest.yml filled (4 fields)
- [ ] context.md written with Backend + Frontend + Shared tech stack
      sections (directly, or via `/create-context` from informal notes)
- [ ] Git initialised

### /specify
- [ ] Constitution Part 2 generated — review Tech Stack table
- [ ] All spec docs generated + .summary.md
- [ ] BRD + SRD reviewed

### /analyze
- [ ] Risk register reviewed
- [ ] Complexity hotspots noted

### /clarify
- [ ] All items answered
- [ ] clarify.summary.md confirmed

### /plan-arch
- [ ] Architecture reviewed by tech lead
- [ ] plan.md reviewed

### /plan-hld
- [ ] All diagrams correct
- [ ] Stakeholders reviewed

### /plan-lld (mvp+)
- [ ] Class + sequence diagrams reviewed

### /plan-adr (mvp+)
- [ ] All key decisions captured

### /task
- [ ] Stories make business sense
- [ ] All tasks have estimated lines
- [ ] Over-limit tasks marked SPLIT
- [ ] Jira CSV imported
- [ ] stories.md + tasks.md BOTH approved

### /implement
- [ ] Each task estimated before coding
- [ ] Each PR under line + file limits
- [ ] Paired test every PR
- [ ] All criteria confirmed per task
- [ ] Tests passing before merge
