# SDD Prompt Guide — 11 Commands
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
| `/specify` | `/specify` | `/specify` | Constitution Part 2 (DRAFT) + spec docs |
| — GATE-1 — | Manual | Manual | You review + finalize constitution Part 2 |
| `/validate` | `/validate` | `/validate` | Business sign-off on BRD/SRD |
| `/analyze` | `/analyze` | `/analyze` | Risks + complexity |
| `/clarify` | `/clarify` | `/clarify` | Questions → you answer |
| `/plan-arch` | `/plan-arch` | `/plan-arch` | Architecture + plan + refine scope docs |
| `/plan-hld` | `/plan-hld` | `/plan-hld` | HLD + diagrams |
| `/plan-lld` | `/plan-lld` | `/plan-lld` | LLD (mvp+ only) |
| `/plan-adr` | `/plan-adr` | `/plan-adr` | ADRs (mvp+ only) |
| `/task` | `/task` | `/task` | Stories + Tasks + Jira |
| `/implement` | `/implement TASK-NNN` | `/implement TASK-NNN` | Code one task |
| `/release` | `/release` | `/release` | UAT + deployment + go-live gate |

---

## Claude Code Native Slash Commands (setup, once)

This pack ships a `.claude/commands/` directory with one Markdown file per
command (`create-context.md`, `start.md`, `specify.md`, `validate.md`,
`analyze.md`, `clarify.md`, `plan-arch.md`, `plan-hld.md`, `plan-lld.md`,
`plan-adr.md`, `task.md`, `implement.md`, `release.md`). Claude Code
auto-discovers these — nothing to install or configure.

- Type `/start` at the beginning of every session — equivalent to STEP 0
  below (reads CLAUDE.md, manifest, constitution, summary-rules,
  change-rules, roles.yml, instructions).
- Type `/specify`, `/validate`, `/analyze`, `/clarify`, `/plan-arch`,
  `/plan-hld`, `/plan-lld`, `/plan-adr`, `/task`, `/release` to run each
  command — Claude reads the matching `.github/prompts/<name>.prompt.md` and
  executes it.
- `/implement TASK-NNN` passes the task ID through to the implement prompt.
- Editing a `.github/prompts/<name>.prompt.md` file (as described in
  CHANGE-GUIDE.md) automatically updates the matching slash command — the
  command files only delegate, they don't duplicate instructions.

---

## /create-context — Optional Pre-Phase (before SPECIFY)

Skip this if you already have a structured `.specify/contexts/{feature}.md`
written per `.specify/contexts/CONTEXT-GUIDE.md` — go straight to STEP 0.

If you don't (or aren't sure how to write one), run `/create-context`:

```
Paste whatever you have — rough notes, an email, a requirements doc, bullet
points, even half-formed thoughts. Any format.
```

The agent:
1. Maps your input onto context-template.md's sections (What This Does,
   Actors, Key Flows, Endpoints, Integrations, Business Rules, NFRs,
   Constraints, Out of Scope, Open Questions, Tech Stack).
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
Read .specify/memory/roles.yml
Read .github/instructions/*.instructions.md
  (AI-7 — apply each file's applyTo glob to matching files you touch)

Confirm:
  Project name: {value}
  Scope: {pilot | mvp | full}
  Feature: {value}
  Context file: {value}
  Workflow mode: {github | local}
  Constitution Part 2: generated? yes/no
  Constitution Part 2 finalized (GATE-1)? yes/no
  Commands for this scope: {list}
  PR rules: max {N} lines, {N} files

State which command is ready to run.
If Part 2 generated but not finalized → remind: complete GATE-1 before
/validate.
```

---

## Document Inventory by Scope/Command (canonical — single source of truth)

| Command | Pilot | MVP | Full |
|---|---|---|---|
| `/specify` | brd, srd, security-design (§1) | + api-spec, data-model, security-design (§1-2) | + resilience, investigation, security-design (§1-4) |
| GATE-1 (manual) | constitution Part 2 finalized — all scopes |||
| `/validate` | validate.md — all scopes |||
| `/analyze` | analyze.md — all scopes |||
| `/clarify` | clarify.md — all scopes |||
| `/plan-arch` | arch.md, plan.md + refine the scope-scaled docs above | same | same |
| `/plan-hld` | hld.md — all scopes |||
| `/plan-lld` | skip | lld.md | lld.md |
| `/plan-adr` | skip | ADRs | ADRs |
| `/task` | stories.md, tasks.md, jira — all scopes |||
| `/implement` | code + paired tests | + qa_cases, runbook | + qa_cases, runbook, openapi |
| `/release` | release.md — all scopes |||

If any other document in this pack lists a different mapping, this table
wins — fix the other document.

---

## /specify — Constitution + Spec Docs

```
Read .specify/manifest.yml
Read .specify/memory/constitution.md + summary-rules.md
Read .specify/contexts/{manifest.project.context_file}
Read all templates needed per scope

ACTION 1 — Generate constitution.md Part 2 (DRAFT):
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

  Set/bump Part 2 version line:
    First run: Version v1.0 | Last Amended: {date} | Amended By: initial /specify
    Re-run (finalized Part 2): bump v{X.Y} → v{X.Y+1}, Amended By:
    CHG-NNN (or "manual /specify re-run")

  Save constitution.md (Part 1 unchanged, Part 2 = DRAFT)
  List remaining [MISSING — ask user] rows as "Open Items for GATE-1"
  ({N} items) — or "No open items — ready for GATE-1 review"
  Report: "Constitution Part 2 generated — DRAFT. Review and finalize
  every row (GATE-1) before /validate."

ACTION 2 — Generate spec documents per scope (canonical table above):
  pilot: brd → srd → security-design (§1 — pilot checklist)
  mvp:   + api-spec → data-model → security-design (§1-2)
  full:  + resilience → investigation → security-design (§1-4)

  For each: read template → derive from context → save .md + .summary.md
  Mark assumptions: [ASSUMPTION-NNN: ...]
  FR IDs: FR-NNN | NFR IDs: NFR-NNN

List generated + skipped.
State: "SPECIFY complete. If GATE-1 not yet passed, finalize constitution
Part 2 now (see GATE-1 prompt below). Then run /validate."
```

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

```
Open .specify/memory/constitution.md → Part 2 (DRAFT from /specify)

Review every row:
  - Tech Stack (20 concerns)
  - Core Principles
  - Domain Rules
  - Never Do

Resolve any [MISSING — ask user] markers — fill the value yourself
Edit directly anything that is wrong — manual edits are AUTHORITATIVE

Tell the agent: "Constitution Part 2 finalized"
```

Rules:
- No `/validate`, `/analyze`, or any later command runs until this gate
  passes.
- A later `/specify` re-run must propose changes for review — it must
  never silently overwrite a finalized Part 2.
- Re-run on finalized Part 2 → produce a Constitution Amendment Summary:
  `{Row}: {old} → {new}` per changed row, cross-referenced against
  change-rules.md's Change Impact Matrix for downstream docs, plus the
  version bump (v{X.Y} → v{X.Y+1}). WAIT for confirmation before applying.

---

## /validate — Business Sign-Off (NEW — runs after GATE-1)

```
Read .specify/manifest.yml + constitution.md + roles.yml
Read brd.summary.md + srd.summary.md
Read validate-template.md

GATE-1 CHECK: constitution Part 2 finalized?
  If not — STOP. State: "GATE-1 open — finalize constitution Part 2
  before /validate."

Produce:
  1. BUSINESS OBJECTIVE TRACE — every BO-NNN → FR-NNN(s) that address it.
     Flag any BO-NNN with no FR.
  2. BUSINESS REQUIREMENTS REVIEW — every BR-NNN correctly reflected in
     srd.md? Flag mismatches.
  3. ASSUMPTIONS SIGN-OFF — every [ASSUMPTION-NNN] in brd/srd for the
     business owner to confirm or reject.
  4. SCOPE CONFIRMATION — in-scope / out-of-scope items from brd.md.
  5. SIGN-OFF — Product Owner + Business Analyst (names from roles.yml):
     Approved / Changes Requested.

Save: validate.md + validate.summary.md
Present report. WAIT for sign-off.

If approved:
  State: "VALIDATE complete — ready for /analyze."
Else:
  State: "VALIDATE incomplete — {N} items need changes. Update
  context.md, re-run /specify for affected docs, re-run /validate."
  Do NOT proceed to /analyze.
```

---

## /analyze — Risk + Complexity

```
Read constitution.md + summary-rules.md
Read .specify/features/{feature}/validate.summary.md
Read .specify/features/{feature}/srd.summary.md
Read .specify/features/{feature}/brd.summary.md
Read analyze-template.md

GATE CHECK: validate.summary.md states "VALIDATE complete"?
  If not — STOP. State: "ANALYZE blocked — run /validate first."

Produce:
  RISKS: every integration + flow + NFR
    Each: likelihood (L/M/H) + impact (L/M/H/Critical)
    + linked FR-NNN / NFR-NNN (AR-3) + mitigation

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
Read constitution.md + all spec summaries + analyze.summary.md
Read clarify-template.md

Find and document:
  AMB-NNN: two valid interpretations
  GAP-NNN: needed info missing from context
  CON-NNN: contradicting requirements
  ASM-NNN: agent assumed — needs confirmation
  OQ-NNN:  human decision needed
  R-NNN (High/Critical): high/critical risk from analyze.summary.md §2

Each item: unique ID + where found + why it matters
Prioritise HIGH/CRITICAL risk items (R-NNN) from analyze.summary.md §2

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

## /plan-arch — Architecture + Plan + Refine Scope Docs

```
Read constitution.md + summary-rules.md
Read clarify.summary.md (MUST exist, all RESOLVED — stop if missing)
Read analyze.summary.md + all spec summaries
Read arch-template.md + plan-template.md

AI-8 GATE CHECK: scan brd.md, srd.md, api-spec.md, data-model.md,
security-design.md for any [ASSUMPTION-NNN] without a matching
<!-- Clarified: {ID} --> note.
  If any remain — STOP. State: "PLAN-ARCH blocked — unresolved
  assumptions {list}. Run /clarify first."

ARCHITECTURE:
  Pattern from constitution tech stack
  Layers + responsibilities
  All ports + adapters
  Integration mapping
  Cross-cutting concerns (auth, logging, error handling)
  Risk mitigations from analyze.md applied
  NFR → Decision mapping (arch-template §4a) for every NFR in
  analyze.md §5

IMPLEMENTATION PLAN:
  Layer-by-layer breakdown
  Class/component names per layer
  Key method signatures
  Implementation order
  Test strategy per layer
  DB migration plan (if applicable)

Save: arch.md + arch.summary.md
Save: plan.md + plan.summary.md

REFINE SCOPE-SCALED DOCS (now that arch.md exists):
  mvp+: api-spec.md, data-model.md — align with ports/adapters + entity
        design in arch.md
  all:  security-design.md — align controls with arch.md cross-cutting
        concerns section
  full: resilience.md — align with arch.md integration list
  full: investigation.md — align with arch.md flows
  Re-save each refined doc + its .summary.md.

State: "PLAN-ARCH complete — review arch.md + plan.md (+ refined scope
docs) before PLAN-HLD"
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

One ADR per key decision (arch.md §4 DEC-NNN rows):
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
Update arch.md §4 — fill ADR column for each DEC-NNN now covered.
State: "/plan-adr complete — {N} ADRs. Ready for /task."
```

---

## /task — Feature → Story → Task + Jira

```
Read constitution.md + summary-rules.md
Read plan.summary.md + analyze.summary.md + clarify.summary.md
+ srd.summary.md + api-spec.summary.md (mvp+)
Read feature-story-template.md + tasks-template.md + jira-export-template.md
+ qa-testcases-template.md

VERIFY: hld.md exists and reviewed. Stop if not.

0. QA TEST CASES (mvp+; skip for pilot):
   For each FR-NNN (srd.summary.md) / endpoint (api-spec.summary.md):
   TC-NNN covering happy path, validation, auth, unhappy path,
   performance (qa-testcases-template.md categories)

   Save: qa-testcases.md + qa-testcases.summary.md

1. FEATURE + STORIES:
   FEATURE: business capability from BRD
   Each story: As {actor} I want {X} so that {Y}
   Linked to FR-NNN from SRD
   Story points: 1/2/3/5/8
   Sprint assignment
   Acceptance criteria (testable)
   HIGH complexity from analyze.md → higher story points
   Traceability matrix: Story → FR → Task → TC-NNN (from qa-testcases.md,
   mvp+) → R-NNN (QA-1)

   Save: stories.md + stories.summary.md

2. TASK LIST:
   Each task mapped to a story (STORY-NNN)
   Satisfies: FR-NNN / NFR-NNN
   Verifies: TC-NNN from qa-testcases.md (mvp+; "TBD — link at /implement"
   for pilot)
   Estimated lines
   PR strategy: single or SPLIT A/B/C
   Files that change
   Acceptance criteria linked to FR/NFR
   Auto-split any task > max_lines_per_pr
   Pre-flag HIGH complexity items from analyze.md

   Save: tasks.md

3. JIRA CSV:
   Feature → Story → Task hierarchy
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
  Apply .github/instructions/*.instructions.md for matching files (AI-7)
  Write paired test alongside — never after
  No class/component over constitution size limit

AFTER CODING:
  List every file changed
  State total lines added
  Confirm each criterion: ✅ {criterion}
  Confirm Verifies: TC-{NNN} now covered by the paired test

  If manifest.workflow_mode == "local":
    Run build + test + lint + coverage commands locally (per
    constitution Part 2 Tech Stack) — report ✅/❌ for each
    State: "Task accepted — {N} lines, {N} files"
  Else (github):
    State: "PR ready — {N} lines, {N} files"

  WAIT for "go" before next task

AFTER ALL TASKS:
  Generate delivery per scope:
    qa_cases  → docs/qa/functional-test-cases.md (mvp+) — finalize
                qa-testcases.md (per qa-testcases-template.md) with
                pass/fail results from the paired tests
    runbook   → docs/runbook/local-setup.md (mvp+, per runbook-template.md)
    openapi   → docs/openapi.yaml (full, per openapi-template.md, from
                api-spec.summary.md)
  State: "IMPLEMENT complete — all tasks merged. Ready for /release."
```

---

## /release — UAT + Deployment + Go-Live Gate (NEW)

```
Read constitution.md + roles.yml
Read tasks.md + qa-testcases.summary.md (mvp+) + brd.summary.md
+ srd.summary.md + docs/runbook/local-setup.md (mvp+)
Read release-template.md

VERIFY GATE (per manifest.workflow_mode):
  github: every task in tasks.md is "PR ready" and merged.
  local:  every task in tasks.md is "Task accepted".
  If not — STOP. State: "RELEASE blocked — {N} tasks not yet
  {merged|accepted}."

Produce:
  1. PRE-RELEASE CHECKLIST — tasks merged, PRs reference TASK-NNN/CHG-NNN,
     tests green, coverage ≥ gate, security checklist passed
     (security-design.md §1, +§2 mvp+), traceability complete
  2. UAT PLAN — one row per UC-NNN from srd.md: scenario, tester (from
     roles.yml), environment, result
  3. DEPLOYMENT PLAN — DB migrations, deploy strategy, smoke test,
     feature flag/traffic shift — owner + rollback-if-fails per step
  4. POST-DEPLOY SMOKE TEST — health check, key endpoint, logs, key NFR
  5. GO-LIVE GATE — Tech Lead / Product Owner / Ops-SRE: Go / No-Go
  6. BUSINESS OBJECTIVE CLOSURE — every BO-NNN: metric, measured result
     or "measure after N days", met? yes/pending
  7. ROLLBACK PLAN — summary, points to runbook §6

Save: release.md + release.summary.md
Present report. WAIT for go-live sign-off (section 5).

If approved:
  State: "RELEASE complete — go-live approved."
Else:
  State: "RELEASE incomplete — go-live NOT approved. {N} items blocking."
```

---

## Recovery Prompts

### Lost Context
```
Re-read CLAUDE.md + manifest.yml + constitution.md
Project: {name} | Feature: {feature} | Last command: /{cmd}
Continue from here.
```

### GATE-1 Reminder
```
Constitution Part 2 was generated as DRAFT but not yet finalized.
Re-read .specify/memory/constitution.md Part 2 — review every row,
resolve [MISSING — ask user] markers, edit anything wrong.
Tell agent "Constitution Part 2 finalized" to unblock /validate.
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
