# SDD Full Stack Pack
## Backend + Frontend Together
## Stacks: Any backend + Any frontend

---

## What Is This?

Spec-Driven Development framework for full stack applications.
You write what your system does — agent generates everything else.
Constitution Part 2 is auto-generated from your context as a DRAFT —
you review and finalize it (GATE-1) before work continues.

---

## The 3 Files You Need

### 1. contexts/{feature}.md — Your system description (15-30 min)
Include a Tech Stack section covering Backend, Frontend, AND Shared —
agent extracts it for constitution. Use CONTEXT-GUIDE.md as your guide.

### 2. manifest.yml — 4 fields only (2 min)
```yaml
project:
  name: "Your Service"
  scope: "pilot"
  feature: "your-feature"
  context_file: "your-feature.md"
```

### 3. constitution.md Part 2 — Generated (draft) by /specify, finalized by you
Agent reads your context → fills Tech Stack (Backend / Frontend / Shared)
+ Principles + Rules as a DRAFT. You review every row and confirm
"Constitution Part 2 finalized" (GATE-1) before /validate runs.

---

## The 11 Commands

```
/specify    → Constitution Part 2 (DRAFT, both layers) + spec documents
[GATE-1]    → You review + finalize constitution Part 2 (manual)
/validate   → Business sign-off on BRD/SRD
/analyze    → Risks + dependencies + complexity
/clarify    → Questions → you answer them
/plan-arch  → Architecture decisions + plan + refine scope docs (both layers)
/plan-hld   → HLD + all Mermaid diagrams
/plan-lld   → Low Level Design (mvp+ only)
/plan-adr   → Architecture Decision Records (mvp+ only)
/task       → Feature → Story → Task + Jira CSV
/implement  → Code one task at a time, PR rules enforced (both layers)
/release    → UAT + deployment plan + go-live gate
```

### Pilot Flow (9 commands + GATE-1)
```
/specify → [GATE-1] → /validate → /analyze → /clarify
→ /plan-arch → /plan-hld → /task → /implement → /release
```

### MVP+ Flow (11 commands + GATE-1)
```
/specify → [GATE-1] → /validate → /analyze → /clarify
→ /plan-arch → /plan-hld → /plan-lld → /plan-adr
→ /task → /implement → /release
```

---

## What /specify Does

Two actions automatically:
1. Reads context → fills constitution Part 2 (DRAFT) — split Backend /
   Frontend / Shared:
   Backend:  Language, Framework, Build Tool, Messaging/Async, Schema,
             Data Store, Data Cache, DB Migration, Resilience, Testing,
             Coverage Gate
   Frontend: Language, Framework, Build Tool, State Management, Component
             Library/Design System, Routing, API Client, Data Cache,
             Testing, Coverage Gate, Accessibility
   Shared:   API Style, Serialisation, Configuration, Secrets,
             Observability, Logging, Quality/Security, Orchestration,
             CI/CD
   + Core Principles + Domain Rules + Never Do

2. Generates spec documents per scope (see table below).

**GATE-1:** the constitution Part 2 is a DRAFT until you review every row
and tell the agent "Constitution Part 2 finalized". Manual edits after
that point are authoritative.

---

## PLAN — 4 Sub-Commands, Each Reviewed Separately

| Command | Generates | Reviewer (see roles.yml) |
|---|---|---|
| /plan-arch | Architecture + plan.md + refine api-spec/component-spec/ux-flow/data-model/security-design/resilience/investigation (both layers) | Tech lead |
| /plan-hld | HLD + all Mermaid diagrams | Stakeholders + tech lead |
| /plan-lld | LLD + class/component diagrams (mvp+) | Senior developer |
| /plan-adr | ADRs (mvp+) | Architect |

---

## Document Inventory by Scope/Command (canonical)

| Command | Pilot | MVP | Full |
|---|---|---|---|
| /specify | BRD, SRD, Security-Design (§1) | + API Spec (Shared API Contract), Component-Spec, UX-Flow, Data Model (Backend Schema & Persistence Model), Security-Design (§1-2) | + Resilience, Investigation, Security-Design (§1-4) |
| GATE-1 | Constitution Part 2 finalized — all scopes |||
| /validate | validate.md — all scopes |||
| /analyze | analyze.md — all scopes |||
| /clarify | clarify.md — all scopes |||
| /plan-arch | arch.md + plan.md (+ refine the scope-scaled docs above) — all scopes |||
| /plan-hld | hld.md — all scopes |||
| /plan-lld | ❌ | lld.md | lld.md |
| /plan-adr | ❌ | ADRs | ADRs |
| /task | stories.md, tasks.md, jira CSV — all scopes |||
| /implement | code + tests + openapi.yaml | + qa_cases, runbook | + qa_cases, runbook |
| /release | release.md — all scopes |||

---

## Quick Start

```bash
unzip sdd-fullstack-v2.zip -d my-service
cd my-service
git init
# Write .specify/contexts/my-feature.md (or run /create-context if you'd
# rather paste rough notes — backend, frontend, or both — and let the
# agent draft it for you)
# Fill .specify/manifest.yml (4 fields)
# Fill .specify/memory/roles.yml (RACI owners — optional but recommended)
claude    # Claude Code Desktop — type /start, then /specify, /clarify, etc.
# OR open VS Code + Copilot Chat — type /specify, /clarify, etc.
```

No structured context.md yet? Run `/create-context` first — paste any
notes you have (backend, frontend, or both) and the agent drafts it with
you (see PROMPT-GUIDE.md).

Otherwise, run `/start` (Claude Code) or follow Step 0 (Copilot) from
PROMPT-GUIDE.md → then run the 11 commands as native slash commands (no
copy/paste needed — see "Claude Code Native Slash Commands" in
PROMPT-GUIDE.md).

---

## Read Next

| File | Purpose |
|---|---|
| GETTING-STARTED.md | 5 steps to first run |
| PROMPT-GUIDE.md | All 11 commands — native `/specify` etc. in Claude Code & Copilot |
| HOW-TO-USE.md | Scope presets + command table |
| SDLC-COMPLETE-GUIDE.md | Full lifecycle reference + checklist |
| CHANGE-GUIDE.md | Making changes later |
| docs/SUMMARY-GUIDE.md | How summaries work |
