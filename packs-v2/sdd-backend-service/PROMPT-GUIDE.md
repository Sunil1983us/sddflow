# SDD Prompt Guide — 6 Verbs
# Claude Code + GitHub Copilot

## STEP 0 — Startup (Every Session)
```
Read CLAUDE.md + .specify/manifest.yml + constitution.md + summary-rules.md
Confirm: project name, scope, feature, context file
Report: constitution Part 2 generated? yes/no
State which verb ready to execute.
```

## VERB 1 — SPECIFY
### Claude Code
```
Read .specify/manifest.yml
Read .specify/contexts/{context_file}
Read .specify/memory/constitution.md + summary-rules.md

Execute SPECIFY — two actions:

ACTION 1 — Generate constitution.md Part 2:
  Extract tech stack from context → fill Tech Stack table (20 concerns)
  Extract principles → fill Core Principles
  Extract business rules → fill Domain Rules
  Extract constraints → fill Never Do
  Save constitution.md (Part 1 unchanged)
  Report: "Constitution Part 2 generated"

ACTION 2 — Generate spec documents:
  Read updated constitution.md
  Read each template before generating its document
  Generate per scope (pilot/mvp/full)
  Save each: {doc}.md + {doc}.summary.md
  Mark assumptions: [ASSUMPTION: ...]

List generated + skipped. State: ready for ANALYZE.
```
### Copilot: `/specify #file:.specify/contexts/{feature}.md`

---

## VERB 2 — ANALYZE
### Claude Code
```
Read constitution.md + summary-rules.md
Read .specify/features/{f}/srd.summary.md + brd.summary.md
Read .specify/templates/analyze-template.md

Produce analysis:
  RISKS: likelihood + impact + mitigation
  DEPENDENCIES: internal + external + timeline
  COMPLEXITY: by feature area + by FR
  NFR IMPACT: design constraints
  UNKNOWNS: items needing spike

Save: analyze.md + analyze.summary.md
Wait for review before CLARIFY.
```
### Copilot: `@workspace /analyze`

---

## VERB 3 — CLARIFY
### Claude Code — Generate Questions
```
Read constitution.md + all spec summaries + analyze.md
Read clarify-template.md

Find: AMB (ambiguities) GAP (missing info) CON (conflicts)
      ASM (assumptions) OQ (open questions) HR (high risks)

Save: .specify/features/{f}/clarify.md
Wait for your answers. Do NOT proceed to PLAN.
```
### You — Fill Answers
```
Open clarify.md → fill every answer → update STATUS to RESOLVED
Tell agent: "clarify.md answered — update spec and write summary"
```
### Claude Code — After Answers
```
Read clarify.md with answers
Update affected spec docs → mark: <!-- Clarified: {ID} -->
Write clarify.summary.md — all items RESOLVED
State: ready for PLAN
```
### Copilot: `@workspace /clarify` then fill answers then `@workspace update spec`

---

## VERB 4 — PLAN
### Claude Code
```
Read constitution.md + clarify.summary.md + all spec summaries

Confirm clarify.summary.md exists — stop if missing.

Generate per scope (skip where false):
  arch → arch.md + summary
  hld  → hld.md + summary (Mermaid diagrams)
  lld  → lld.md + summary (mvp+)
  plan → plan.md + summary

State: ready for TASK after your review.
```
### Copilot: `@workspace /plan`

---

## VERB 5 — TASK
### Claude Code
```
Read constitution.md + plan.summary.md + analyze.summary.md

Generate:
1. Feature → Story → Task hierarchy
   As {actor} I want {X} so that {Y}
   Acceptance criteria linked to FRs
   Story points (1/2/3/5/8) + Sprint assignment
   → stories.md + stories.summary.md

2. Task list
   Each task: estimated lines + PR strategy + acceptance criteria
   Auto-split any task > max_lines_per_pr
   → tasks.md

3. Jira CSV
   Epic → Story → Task hierarchy with all fields
   → docs/jira/stories.md + jira-import.csv

List all tasks + PR strategy. Wait for approval of both
stories.md AND tasks.md before IMPLEMENT.
```
### Copilot: `@workspace /task`

---

## VERB 6 — IMPLEMENT (per task)
### Claude Code
```
Read constitution.md + tasks.md

Execute TASK-{NNN}: {title}

Before writing:
  State estimated lines
  If > max_lines_per_pr → show SPLIT plan → wait for go

While writing:
  Follow constitution Part 1 + Part 2
  Write paired test alongside — never after

After writing:
  List files + lines
  Confirm each criterion: ✅ {criterion}
  State: "PR ready — {N} lines, {N} files"
  Wait for go before next task
```
### Copilot: `@workspace /implement TASK-{NNN}`

---

## DELIVERY — After All Tasks
```
Read constitution.md + all summaries
Generate per scope:
  openapi → docs/openapi.yaml
  qa_cases → docs/qa/functional-test-cases.md
  runbook → docs/runbook/local-setup.md
```

---

## CHANGE MANAGEMENT
```
SPECIFY: update context.md + CHANGELOG → re-run SPECIFY for affected docs
ANALYZE: re-run if risk profile changed
CLARIFY: re-run for new ambiguities
PLAN:    update if structural change
TASK:    append CHG-NNN tasks
IMPLEMENT: execute CHG tasks (same PR rules)
```

---

## RECOVERY
```
Lost context:
  Re-read CLAUDE.md + manifest.yml + constitution.md
  Project: {name} | Feature: {feature} | Current: {verb/task}
  Continue from here.

Regenerate doc:
  Discard {doc}.md
  Re-read template + context
  Regenerate → save same path + summary

Fix test:
  {paste error}
  Fix → re-run → confirm green before next task.
```

## PLAN — 4 Sub-Commands

PLAN is split into 4 sub-commands.
Each has its own review gate. Run in order.
Pilot scope: only PLAN-ARCH and PLAN-HLD required.

---

### /plan-arch — Architecture + Implementation Plan
#### Claude Code
```
Read .specify/manifest.yml + constitution.md + summary-rules.md
Read .specify/features/{feature}/clarify.summary.md (must exist)
Read .specify/features/{feature}/analyze.summary.md
Read all spec summaries

Execute PLAN-ARCH:
  1. Generate arch.md — architecture decisions, layers,
     ports/adapters, integrations, cross-cutting concerns
     Apply risk mitigations from analyze.md
     Save: arch.md + arch.summary.md

  2. Generate plan.md — layer breakdown, class names,
     method signatures, implementation order, test strategy
     Save: plan.md + plan.summary.md

Review arch.md + plan.md before running PLAN-HLD.
```
#### Copilot: `/plan-arch`

---

### /plan-hld — High Level Design + Diagrams
#### Claude Code
```
Read arch.summary.md + analyze.summary.md
Read hld-template.md

Execute PLAN-HLD (all diagrams in Mermaid):
  - System context diagram (C4 Level 1)
  - Container/component diagram (C4 Level 2)
  - Happy path sequence diagram
  - Status/state machine (if applicable)
  - Screen flow (mobile) / Component tree (frontend)

Save: docs/hld/hld.md + hld.summary.md

If scope = pilot → state: "Skip PLAN-LLD + PLAN-ADR → ready for TASK"
```
#### Copilot: `/plan-hld`

---

### /plan-lld — Low Level Design (mvp+ only)
#### Claude Code
```
Read plan.summary.md + arch.summary.md
Read lld-template.md

If scope = pilot → STOP: "Skipped — pilot scope. Proceed to PLAN-ADR or TASK."

Execute PLAN-LLD:
  - Package/folder structure
  - Class diagram (backend) or Component diagram (frontend)
  - Detailed sequence diagrams per key flow
  - ERD (if database)
  - Key method signatures
  - DTO/record definitions

Save: docs/lld/lld.md + lld.summary.md
```
#### Copilot: `/plan-lld`

---

### /plan-adr — Architecture Decision Records (mvp+ only)
#### Claude Code
```
Read arch.summary.md + analyze.summary.md
Read adr-template.md

If scope = pilot → STOP: "Skipped — pilot scope. Proceed to TASK."

Execute PLAN-ADR:
  One ADR per key decision:
  - Pattern choice, tech choice, integration approach
  - Data store, deployment, security, HIGH risk items from analyze
  Each ADR: Context → Options → Decision → Consequences

Save: docs/architecture/adr/ADR-{NNN}-{title}.md
Save: docs/architecture/decisions.md (index)
```
#### Copilot: `/plan-adr`

