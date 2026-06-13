# SDD Prompt Guide — 9 Commands
# Claude Code Desktop + GitHub Copilot

---

## Command Overview

> **Claude Code users**: every command below is a native slash command —
> type it directly (e.g. `/specify`), exactly like Copilot. No copy/paste
> needed. These come from `.claude/commands/*.md` (committed to the repo)
> and each one reads its full instructions from the matching
> `.github/prompts/<name>.prompt.md` file. See "Claude Code Native Slash
> Commands" below for setup details.

| Command | Claude Code | Copilot | Does |
|---|---|---|---|
| `/create-context` (optional) | `/create-context` | `/create-context` | Turn informal notes into context.md |
| Startup | `/start` | Step 0 | Read files + confirm |
| `/specify` | `/specify` | `/specify` | Constitution + spec docs |
| `/analyze` | `/analyze` | `/analyze` | Risks + complexity |
| `/clarify` | `/clarify` | `/clarify` | Questions → you answer |
| `/plan-arch` | `/plan-arch` | `/plan-arch` | Architecture + plan |
| `/plan-hld` | `/plan-hld` | `/plan-hld` | HLD + diagrams |
| `/plan-lld` | `/plan-lld` | `/plan-lld` | LLD (mvp+ only) |
| `/plan-adr` | `/plan-adr` | `/plan-adr` | ADRs (mvp+ only) |
| `/task` | `/task` | `/task` | Stories + Tasks + Jira |
| `/implement` | `/implement TASK-NNN` | `/implement TASK-NNN` | Code one task |

---

## Claude Code Native Slash Commands (setup, once)

This pack ships a `.claude/commands/` directory with one Markdown file per
command (`create-context.md`, `start.md`, `specify.md`, `analyze.md`,
`clarify.md`, `plan-arch.md`, `plan-hld.md`, `plan-lld.md`, `plan-adr.md`,
`task.md`, `implement.md`). Claude Code auto-discovers these — nothing to
install or configure.

- Type `/start` at the beginning of every session — equivalent to STEP 0
  below (reads CLAUDE.md, manifest, constitution, summary-rules,
  change-rules).
- Type `/specify`, `/analyze`, `/clarify`, `/plan-arch`, `/plan-hld`,
  `/plan-lld`, `/plan-adr`, `/task` to run each command — Claude reads the
  matching `.github/prompts/<name>.prompt.md` and executes it.
- `/implement TASK-NNN` passes the task ID through to the implement prompt.
- `/create-context` is the optional pre-phase — see below.

GitHub Copilot users: the same `.github/prompts/*.prompt.md` files power
Copilot's native `/specify` etc. — no setup needed either.

---

## /create-context — Optional Pre-Phase (before SPECIFY)

Skip this if you already have a structured `.specify/contexts/{feature}.md`
written per `.specify/contexts/CONTEXT-GUIDE.md` — go straight to STEP 0.

If you don't (or aren't sure how to write one), run `/create-context`:

```
Paste whatever you have — rough notes, an email, a requirements doc, bullet
points, even half-formed thoughts. Any format. Cover backend and frontend
if you can, but partial info for either side is OK.
```

The agent:
1. Maps your input onto context-template.md's sections (What This Does,
   Actors, Key Flows, Endpoints, Integrations, Business Rules, NFRs,
   Constraints, Out of Scope, Open Questions, Tech Stack — Backend /
   Frontend / Shared).
2. Fills in what it can infer, marks the rest `[MISSING — ask user]`.
3. Gives you a plain-language "Missing Information" checklist.
4. You answer what you can — "not sure" is fine for technical questions
   (the architect decides later at /plan-arch).
5. Repeat until you say "good enough, proceed" or nothing is missing.
6. Saves `.specify/contexts/{feature}.md` — the file /specify reads.

Optionally keeps your original notes at
`.specify/contexts/{feature}.raw.md` (reference only, never read by any
other command) so you can re-run `/create-context` later with more detail —
e.g. when scope upgrades from pilot to mvp/full and new sections need
filling in.

---

## STEP 0 — Startup (Every Session)

```
Read CLAUDE.md
Read .specify/manifest.yml
Read .specify/memory/constitution.md
Read .specify/memory/summary-rules.md
Read .specify/memory/change-rules.md

Confirm:
  Project name: {value}
  Scope: {pilot | mvp | full}
  Feature: {value}
  Context file: {value}
  Constitution Part 2: generated? yes / no
  Commands for this scope: {list}
  PR rules: max {N} lines, {N} files

State which command ready to run.
```

---

## /specify — Constitution + Spec Docs

```
Read .specify/manifest.yml
Read .specify/memory/constitution.md + summary-rules.md
Read .specify/contexts/{manifest.project.context_file}
Read all templates needed per scope

ACTION 1 — Generate constitution.md Part 2:
  Extract from context and fill:

  Tech Stack (extract each concern):
  Language, Framework, Build Tool, API Style,
  Messaging/Async, Serialisation, Schema,
  Data Store, Data Cache, DB Migration,
  Configuration, Secrets, Resilience,
  Observability, Logging, Testing,
  Coverage Gate, Quality/Security,
  Orchestration, CI/CD

  If concern not in context → use sensible default
  If critical concern missing → mark [MISSING — ask user]

  Core Principles → derive from domain type
  Domain Rules → extract from business rules section
  Never Do → extract from constraints section

  Save constitution.md (Part 1 unchanged, Part 2 filled)
  Report: "Constitution Part 2 generated — review Tech Stack table"

ACTION 2 — Generate spec documents per scope:
  pilot: brd → srd → analyze → hld
  mvp+:  + lld + api_spec + data_model
  full:  + resilience + investigation + security_design

  For each: read template → derive from context
  Save: {doc}.md + {doc}.summary.md
  Mark assumptions: [ASSUMPTION: ...]
  FR IDs: FR-NNN | NFR IDs: NFR-NNN

List generated + skipped.
State: "SPECIFY complete — ready for /analyze"
```

---

## /analyze — Risk + Complexity

```
Read constitution.md + summary-rules.md
Read .specify/features/{feature}/srd.summary.md
Read .specify/features/{feature}/brd.summary.md
Read analyze-template.md

Produce:
  RISKS: every integration + flow + NFR
    Each: likelihood (L/M/H) + impact (L/M/H/Critical) + mitigation

  DEPENDENCIES: internal + external + timeline
    Each: blocking/non-blocking + owner + risk

  COMPLEXITY: by feature area + by FR
    Each: LOW/MEDIUM/HIGH + reason
    Flag HIGH → these need SPLIT tasks later

  NFR IMPACT: design constraints from NFRs
    Which NFRs force architectural decisions?

  UNKNOWNS: items needing spike before design

  RECOMMENDATION:
    Suggested approach
    Items to raise in /clarify
    Tasks likely needing SPLIT

Save: analyze.md + analyze.summary.md
Wait for review before /clarify.
```

---

## /clarify — Surface + Resolve Ambiguities

### Step A — Generate Questions
```
Read constitution.md + all spec summaries + analyze.md
Read clarify-template.md

Find and document:
  AMB-NNN: two valid interpretations
  GAP-NNN: needed info missing from context
  CON-NNN: contradicting requirements
  ASM-NNN: agent assumed — needs confirmation
  OQ-NNN:  human decision needed
  HR-NNN:  high risk from analyze.md needing clarity

Each item: unique ID + where found + why it matters
Prioritise HIGH risk items from analyze.md

Save: .specify/features/{feature}/clarify.md
Present report. WAIT for answers. Do NOT proceed.
```

### Step B — You Fill the Answers
```
Open clarify.md
Fill every "Your answer" field
Update STATUS TABLE to RESOLVED / CONFIRMED / DECIDED
Tell agent: "clarify.md answered"
```

### Step C — Update Spec
```
Read clarify.md with answers
Update affected spec docs → mark: <!-- Clarified: {ID} -->
Regenerate .summary.md for each updated doc
Write clarify.summary.md — all items RESOLVED
State: "CLARIFY complete — ready for /plan-arch"
```

---

## /plan-arch — Architecture + Plan

```
Read constitution.md + summary-rules.md
Read clarify.summary.md (MUST exist — stop if missing)
Read analyze.summary.md + all spec summaries
Read arch-template.md + plan-template.md

ARCHITECTURE:
  Pattern from constitution tech stack
  Layers + responsibilities
  All ports + adapters
  Integration mapping
  Cross-cutting concerns (auth, logging, error handling)
  Risk mitigations from analyze.md applied

IMPLEMENTATION PLAN:
  Layer-by-layer breakdown
  Class/component names per layer
  Key method signatures
  Implementation order
  Test strategy per layer
  DB migration plan (if applicable)

Save: arch.md + arch.summary.md
Save: plan.md + plan.summary.md

State: "PLAN-ARCH complete — review arch.md + plan.md"
Wait for approval before /plan-hld.
```

---

## /plan-hld — High Level Design + Diagrams

```
Read constitution.md + summary-rules.md
Read arch.summary.md + analyze.summary.md
Read hld-template.md

VERIFY: arch.md exists and reviewed. Stop if not.

Generate HLD — ALL diagrams in Mermaid:

  ALWAYS:
    System context (C4 L1) — graph TD
    Container/component (C4 L2) — graph TD
    Happy path sequence — sequenceDiagram
    State machine (if states exist) — stateDiagram-v2

  IF APPLICABLE:
    Screen flow (mobile) — graph TD
    Component tree (frontend) — graph TD
    Event flow (messaging) — sequenceDiagram
    Deployment diagram — graph TD

  SCOPE RULES:
    pilot: happy path only
    mvp+:  all flows including unhappy paths

Save: docs/hld/hld.md + hld.summary.md

If scope = pilot:
  State: "PLAN-HLD complete — SKIP /plan-lld and /plan-adr
          Scope is pilot. Ready for /task after review."
Else:
  State: "PLAN-HLD complete — review hld.md
          Run /plan-lld next."
Wait for review.
```

---

## /plan-lld — Low Level Design (mvp+ only)

```
Read constitution.md + summary-rules.md
Read plan.summary.md + arch.summary.md
Read lld-template.md

SCOPE CHECK:
  If scope = pilot → STOP.
  State: "/plan-lld skipped — pilot scope.
          Run /plan-adr or proceed to /task."

VERIFY: arch.md + hld.md exist. Stop if not.

Generate LLD — all diagrams in Mermaid:

  Package/folder structure — full tree
  Class diagram (backend) — classDiagram
  Component diagram (frontend) — graph TD or classDiagram
  Detailed sequence per key flow — sequenceDiagram
    Include error handling paths
  ERD (if database) — erDiagram
  Key method signatures — per layer
  DTO/record definitions

Save: docs/lld/lld.md + lld.summary.md
State: "PLAN-LLD complete — review lld.md"
Wait for review.
```

---

## /plan-adr — Architecture Decision Records (mvp+ only)

```
Read constitution.md
Read arch.summary.md + analyze.summary.md
Read adr-template.md

SCOPE CHECK:
  If scope = pilot → STOP.
  State: "/plan-adr skipped — pilot scope. Proceed to /task."

VERIFY: arch.md exists. Stop if not.

One ADR per key decision:
  Pattern choice (hexagonal, layered, event-driven)
  Technology choice where alternatives existed
  Integration approach (sync vs async)
  Data store choice
  Deployment + security approach
  Any HIGH risk item from analyze.md

Each ADR format:
  Context → Options Considered → Decision → Consequences

Save: docs/architecture/adr/ADR-{NNN}-{title}.md
Save: docs/architecture/decisions.md (index)
State: "/plan-adr complete — {N} ADRs. Ready for /task."
```

---

## /task — Feature → Story → Task + Jira

```
Read constitution.md + summary-rules.md
Read plan.summary.md + analyze.summary.md + clarify.summary.md
Read feature-story-template.md + tasks-template.md + jira-export-template.md

VERIFY: hld.md exists and reviewed. Stop if not.

1. FEATURE + STORIES:
   FEATURE: business capability from BRD
   Each story: As {actor} I want {X} so that {Y}
   Linked to FR-NNN from SRD
   Story points: 1/2/3/5/8
   Sprint assignment
   Acceptance criteria (testable)
   HIGH complexity from analyze.md → higher story points

   Save: stories.md + stories.summary.md

2. TASK LIST:
   Each task mapped to a story (STORY-NNN)
   Estimated lines
   PR strategy: single or SPLIT A/B/C
   Files that change
   Acceptance criteria linked to FR/NFR
   Auto-split any task > max_lines_per_pr
   Pre-flag HIGH complexity items from analyze.md

   Save: tasks.md

3. JIRA CSV:
   Epic → Story → Task hierarchy
   Story points, sprint, acceptance criteria
   Save: docs/jira/stories.md + docs/jira/jira-import.csv

List all stories + tasks + PR strategy.
State: "TASK complete — review stories.md AND tasks.md
        BOTH must be approved before /implement"
Wait for approval of both.
```

---

## /implement — Code One Task at a Time

```
Read constitution.md
Read .specify/features/{feature}/tasks.md

VERIFY: tasks.md approved. Stop if not.

For TASK-{NNN}: {title}

BEFORE CODING:
  1. State task details
  2. Estimate total lines
  3. If > max_lines_per_pr:
     Show SPLIT: TASK-{NNN}-A, B, C...
     Each sub-task: what it covers + estimated lines
     WAIT for confirmation
  4. If within limit:
     State: "Estimated {N} lines — proceeding"

WHILE CODING:
  Follow constitution Part 1 universal rules
  Follow constitution Part 2 tech stack + domain rules
  Write paired test alongside — never after
  No class/component over constitution size limit

AFTER CODING:
  List every file changed
  State total lines added
  Confirm each criterion: ✅ {criterion}
  State: "PR ready — {N} lines, {N} files"
  WAIT for "go" before next task

AFTER ALL TASKS:
  Generate delivery per scope:
    openapi   → docs/openapi.yaml
    qa_cases  → docs/qa/functional-test-cases.md
    runbook   → docs/runbook/local-setup.md
```

---

## Recovery Prompts

### Lost Context
```
Re-read CLAUDE.md + manifest.yml + constitution.md
Project: {name} | Feature: {feature} | Last command: /{cmd}
Continue from here.
```

### Regenerate a Document
```
Discard .specify/features/{feature}/{doc}.md
Re-read template + context
Regenerate → save same path + summary
```

### Fix Failing Test
```
Failing test: {paste error}
Read failing class. Fix → re-run → confirm green.
Do not move to next task until passing.
```

### PR Too Large
```
TASK-{NNN} produced {N} lines — exceeds limit.
Split before committing. Show plan. Wait for confirmation.
```

### Change Summary Limit
```
summary-rules.md updated: SUMMARY_MAX_LINES = {N}
Re-read .specify/memory/summary-rules.md.
Apply to all future summaries.
```

### Scope Upgrade
```
manifest.yml updated: scope = {new}
Re-read manifest.yml.
Run /plan-lld and /plan-adr (now enabled).
Then update /task with new tasks.
```
