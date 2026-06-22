# SDD Prompt Guide — Command Reference
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
| **GATE-1** | Manual | Manual | You review + finalize constitution Part 2 |
| `/checklist` (optional) | `/checklist` | `/checklist` | Spec-quality validation (CHK-NNN) |
| `/validate` | `/validate` | `/validate` | Business sign-off on BRD/SRD |
| `/analyze` | `/analyze` | `/analyze` | Risks + complexity |
| `/clarify` | `/clarify` | `/clarify` | Questions → you answer |
| `/plan-design` | `/plan-design` | `/plan-design` | Screen/app architecture + plan + refine scope docs |
| `/plan-design` | `/plan-design` | `/plan-design` | HLD + diagrams (screen flow + navigation) |
| `/plan-lld` | `/plan-lld` | `/plan-lld` | LLD (mvp+ only) |
| `/plan-design` | `/plan-design` | `/plan-design` | ADRs (mvp+ only) |
| `/task` | `/task` | `/task` | Stories + Tasks + Jira |
| `/implement` | `/implement TASK-NNN` | `/implement TASK-NNN` | Code one task |
| `/release` | `/release` | `/release` | UAT + store-release plan + go-live gate |

---

## Tool Compatibility

| AI Tool | How to Use | Auto-Setup File |
|---|---|---|
| **Claude Code** | Type `/specify`, `/validate`, etc. | `.claude/commands/` (auto-discovered) |
| **GitHub Copilot** | Type `/specify`, `/validate`, etc. | `.github/prompts/` (auto-discovered) |
| **Cursor** | In chat: `Read and follow .github/prompts/specify.prompt.md exactly` | `.cursor/rules/sdd-framework.mdc` (auto-loaded) |
| **Windsurf** | In chat: `Run specify` or `Follow specify prompt` | `.windsurfrules` (auto-loaded) |
| **Any AI** | Copy-paste contents of `.github/prompts/{command}.prompt.md` into chat | No setup needed — prompts are self-contained |

**For any AI tool:** The `.github/prompts/` files are written as self-contained instructions. Any AI that can read a markdown file can execute any SDD command — just paste the file contents into the chat.

**First time?** Run `bash setup.sh` (Mac/Linux) or `.\setup.ps1` (Windows) to initialize your project. See [QUICKSTART.md](QUICKSTART.md).

---

## Claude Code Native Slash Commands (setup, once)

This pack ships a `.claude/commands/` directory with one Markdown file per
command (`create-context.md`, `start.md`, `specify.md`, `validate.md`,
`analyze.md`, `clarify.md`, `plan-design.md`, `plan-design.md`, `plan-lld.md`,
`plan-adr.md`, `task.md`, `implement.md`, `release.md`). Claude Code
auto-discovers these — nothing to install or configure.

- Type `/start` at the beginning of every session — equivalent to STEP 0
  below (reads CLAUDE.md, manifest, constitution, summary-rules,
  change-rules, roles.yml, instructions).
- Type `/specify`, `/validate`, `/analyze`, `/clarify`, `/plan-design`,
  `/plan-design`, `/plan-lld`, `/plan-design`, `/task`, `/release` to run each
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
3. Gives you a plain-language "Missing Information" checklist (e.g. "What
   state management library?", "Offline support needed?", "Push
   notifications provider?", "Target: iOS only, Android only, or both?").
4. You answer what you can — "not sure" is fine for technical questions
   (the architect decides later at /plan-design).
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
  (AI-7 — apply each file's applyTo glob to matching files you touch,
  exactly as GitHub Copilot does)

Confirm:
  Project name: {value}
  Scope: {pilot | mvp | full}
  Feature: {value}
  Context file: {value}
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
| `/specify` | brd, srd, security-design (§1) | + screen-spec, ux-flow, api-spec (Backend API Contract — Consumer), security-design (§1-2) | + data-model (Local Data & Cache Model), resilience (Mobile Resilience), investigation (Crash & Incident Triage), security-design (§1-4) |
| GATE-1 (manual) | constitution Part 2 finalized — all scopes |||
| `/validate` | validate.md — all scopes |||
| `/analyze` | analyze.md — all scopes |||
| `/clarify` | clarify.md — all scopes |||
| `/plan-design` | design.md, plan.md + refine the scope-scaled docs above | same | same |
| `/plan-design` | design.md — all scopes |||
| `/plan-lld` | skip | lld.md | lld.md |
| `/plan-design` | skip | ADRs | ADRs |
| `/task` | stories.md, tasks.md, jira — all scopes |||
| `/implement` | code + paired tests | + qa_cases, runbook | + qa_cases, runbook |
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
  Language/Framework, Navigation, State Management, Local Storage/DB,
  API Client, Build Tool, Push Notifications, Crash/Analytics,
  Data Cache, Offline Sync, Configuration, Secrets, Resilience,
  Observability, Logging, Testing, Coverage Gate, Quality/Security,
  CI/CD, App Store Distribution

  If concern not in context → use sensible default
  If critical concern missing → mark [MISSING — ask user]

  Core Principles → derive from domain type (Offline-First,
    Accessible, Cross-Platform, Performant + Specification First,
    Test First, Traceability)
  Domain Rules → extract from business/UX rules section
  Never Do → extract from constraints section

  Save constitution.md (Part 1 unchanged, Part 2 = DRAFT)
  Report: "Constitution Part 2 generated — DRAFT. Review and finalize
  every row (GATE-1) before /validate."

ACTION 2 — Generate spec documents per scope (canonical table above):
  pilot: brd → srd → security-design (§1 — pilot checklist)
  mvp:   + screen-spec → ux-flow → api-spec (Backend API Contract —
         Consumer) → security-design (§1-2)
  full:  + data-model (Local Data & Cache Model) →
         resilience (Mobile Resilience) →
         investigation (Crash & Incident Triage) →
         security-design (§1-4 — STRIDE + MASVS)

  For each: read template → derive from context → save .md + .summary.md
  Mark assumptions: [ASSUMPTION-NNN: ...]
  FR IDs: FR-NNN | NFR IDs: NFR-NNN
  For every UC-NNN: at least 2 Given/When/Then acceptance scenarios
  + "Independent Test" statement (these become TC-NNN at /task)
  Marker discipline:
    [ASSUMPTION-NNN] → reasonable default applied; confirm at /validate
    [NEEDS CLARIFICATION: {question}] → no safe default; must be answered
    before /validate can proceed — never leave a gap silently

List generated + skipped.
State: "SPECIFY complete. If GATE-1 not yet passed, finalize constitution
Part 2 now (see GATE-1 prompt below). Then run /validate."
```

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

```
Open .specify/memory/constitution.md → Part 2 (DRAFT from /specify)

Review every row:
  - Tech Stack (Language/Framework, Navigation, State Management, Local
    Storage/DB, API Client, Push Notifications, Crash/Analytics,
    App Store Distribution, and remaining concerns)
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

---

## /checklist — Spec-Quality Validation (Optional, after GATE-1)

Run this between GATE-1 and /validate to catch spec quality issues early —
before the business sign-off meeting.

```
Read manifest.yml + constitution.md
Read brd.summary.md + srd.summary.md
Read checklist-template.md

Checks (in order):
  CRITICAL (block /validate):
    Unresolved [NEEDS CLARIFICATION] markers in brd/srd
    NFR-NNN without numeric threshold
    FR-NNN with no UC-NNN coverage
    UC-NNN with < 2 Given/When/Then acceptance scenarios

  HIGH (fix before /validate):
    Vague adjectives without measurable values
    UC-NNN missing "Independent Test" field
    FR-NNN missing BR-NNN source link

  MEDIUM (fix before /plan-design):
    Terminology drift between brd.md and srd.md
    Missing Out of Scope section
    Unconfirmed ASSUMPTION-NNN markers

  CONSISTENCY:
    Duplicate FR-NNN entries

Save: .specify/features/{feature}/checklists/{feature}-spec-quality.md
Present findings table. State count by severity.

If CRITICAL items: State "Fix CRITICAL items → re-run /specify → re-run /checklist"
If no CRITICAL: State "Spec quality gate passed — ready for /validate"
```

---

## /validate — Business Sign-Off (runs after GATE-1)

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
  3a. NEEDS CLARIFICATION SCAN — scan brd/srd for [NEEDS CLARIFICATION]
      markers; these are BLOCKING — must be resolved before sign-off
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
  CONSISTENCY: cross-artifact audit (CF-NNN items)
    DUPLICATION: near-duplicate BR/FR entries
    AMBIGUITY: vague FRs without measurable values
    COVERAGE GAPS: FR-NNN with no UC, FR-NNN with no task
    TERMINOLOGY DRIFT: same concept named differently in brd vs srd
    CONSTITUTION CONFLICTS: FR/NFR violating constitution MUST rules
    → CRITICAL conflicts block /clarify until resolved

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
State: "CLARIFY complete — ready for /plan-design"
```

---

## /plan-design — Screen/App Architecture + Plan + Refine Scope Docs

```
Read constitution.md + summary-rules.md
Read clarify.summary.md (MUST exist, all RESOLVED — stop if missing)
Read analyze.summary.md + all spec summaries
Read arch-template.md + plan-template.md

AI-8 GATE CHECK: scan brd.md, srd.md, screen-spec.md, ux-flow.md,
api-spec.md, data-model.md, security-design.md for any
[ASSUMPTION-NNN] without a matching <!-- Clarified: {ID} --> note.
  If any remain — STOP. State: "PLAN-DESIGN blocked — unresolved
  assumptions {list}. Run /clarify first."

ARCHITECTURE:
  Pattern from constitution tech stack (feature-module, screens +
    view-model/state + navigation per feature)
  Screen tree + responsibilities
  Navigation structure (stack/tab/drawer, deep links)
  State management design (store/slices/view-models)
  Local data & cache model (offline-first strategy, sync queue)
  Service/API client layer (ports + adapters to backend APIs)
  Cross-cutting concerns (auth, permissions, error boundaries, logging,
    accessibility)
  Risk mitigations from analyze.md applied
  NFR → Decision mapping (arch-template §4a) for every NFR in
  analyze.md §5

IMPLEMENTATION PLAN:
  Layer-by-layer breakdown (screens, view-models/hooks, services, store,
    local storage/DB)
  Screen/module names per layer
  Key prop/interface signatures
  Implementation order
  Test strategy per layer (unit, screen/widget, e2e)

Save: design.md + arch.summary.md
Save: plan.md + plan.summary.md

REFINE SCOPE-SCALED DOCS (now that design.md exists):
  mvp+: screen-spec.md, ux-flow.md, api-spec.md — align with screen tree +
        navigation structure + service layer design in design.md
  all:  security-design.md — align controls with design.md cross-cutting
        concerns section
  full: data-model.md — align with design.md local data & cache model
  full: resilience.md — align with design.md integration list + offline
        strategy
  full: investigation.md — align with design.md flows
  Re-save each refined doc + its .summary.md.

State: "PLAN-DESIGN complete — review design.md + plan.md (+ refined scope
docs) before PLAN-DESIGN"
Wait for approval before /plan-design.
```

---

## /plan-design — High Level Design + Diagrams

```
Read constitution.md + summary-rules.md
Read arch.summary.md + analyze.summary.md
Read hld-template.md

VERIFY: design.md exists and reviewed. Stop if not.

Generate HLD — ALL diagrams in Mermaid:

  ALWAYS:
    System context (C4 L1) — graph TD
    Screen/container diagram (C4 L2) — graph TD
    Happy path sequence — sequenceDiagram
    State machine (if states exist) — stateDiagram-v2

  IF APPLICABLE:
    Screen flow + navigation diagram — graph TD
    Screen tree (detailed) — graph TD
    Event flow (e.g. push notification/real-time sync) — sequenceDiagram
    Deployment diagram (CI build + app store pipeline — OPS-7) — graph TD

  SCOPE RULES:
    pilot: happy path only
    mvp+:  all flows including unhappy paths

Save: docs/hld/design.md + hld.summary.md

If scope = pilot:
  State: "PLAN-DESIGN complete — SKIP /plan-lld and /plan-design
          Scope is pilot. Ready for /task after review."
Else:
  State: "PLAN-DESIGN complete — review design.md
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
          Run /plan-design or proceed to /task."

VERIFY: design.md + design.md exist. Stop if not.

Generate LLD — all diagrams in Mermaid:

  Folder/module structure — full tree
  Screen/component diagram — classDiagram or graph TD
  Detailed sequence per key flow — sequenceDiagram
    Include error handling + retry/offline-queue paths (resilience.md,
    full)
  Local data shape diagram (if applicable) — classDiagram or erDiagram
  Key prop/interface signatures — per screen/component
  View-model/hook/service signatures

Save: docs/lld/lld.md + lld.summary.md
State: "PLAN-LLD complete — review lld.md"
Wait for review.
```

---

## /plan-design — Architecture Decision Records (mvp+ only)

```
Read constitution.md
Read arch.summary.md + analyze.summary.md
Read adr-template.md

SCOPE CHECK:
  If scope = pilot → STOP.
  State: "/plan-design skipped — pilot scope. Proceed to /task."

VERIFY: design.md exists. Stop if not.

One ADR per key decision (design.md §4 DEC-NNN rows):
  Pattern choice (feature-module architecture, state management
    approach)
  Technology choice where alternatives existed (framework, navigation
    library, local storage/DB)
  Integration approach (API client, polling vs push notifications,
    offline sync strategy)
  Local storage/DB choice (data-model.md, full)
  App store distribution + release pipeline approach (OPS-7)
  Any HIGH risk item from analyze.md

Each ADR format:
  Context → Options Considered → Decision → Consequences

Save: docs/architecture/adr/ADR-{NNN}-{title}.md
Save: docs/architecture/decisions.md (index)
Update design.md §4 — fill ADR column for each DEC-NNN now covered.
State: "/plan-design complete — {N} ADRs. Ready for /task."
```

---

## /task — Feature → Story → Task + Jira

```
Read constitution.md + summary-rules.md
Read plan.summary.md + analyze.summary.md + clarify.summary.md
Read feature-story-template.md + tasks-template.md + jira-export-template.md
Read qa-testcases.summary.md (mvp+, if already generated)

VERIFY: design.md exists and reviewed. Stop if not.

1. FEATURE + STORIES:
   FEATURE: business capability from BRD
   Each story: As {actor} I want {X} so that {Y}
   Linked to FR-NNN from SRD
   Story points: 1/2/3/5/8
   Sprint assignment
   Acceptance criteria (testable)
   HIGH complexity from analyze.md → higher story points
   Traceability matrix: Story → FR → Task → TC-NNN → R-NNN (QA-1)

   Save: stories.md + stories.summary.md

2. TASK LIST:
   Each task mapped to a story (STORY-NNN)
   Satisfies: FR-NNN / NFR-NNN
   Verifies: TC-NNN (mvp+; "TBD — link at /implement" if not yet generated)
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
  Apply .github/instructions/*.instructions.md for matching files (AI-7)
  Write paired test alongside — never after
  No screen/component over constitution size limit
  Assume offline first — sync when connected
  Request permissions at point of use — never on startup

AFTER CODING:
  List every file changed
  State total lines added
  Confirm each criterion: ✅ {criterion}
  Confirm Verifies: TC-{NNN} now covered by the paired test
  State: "PR ready — {N} lines, {N} files"
  WAIT for "go" before next task

AFTER ALL TASKS:
  Generate delivery per scope:
    qa_cases  → docs/qa/functional-test-cases.md (mvp+)
    runbook   → docs/runbook/local-setup.md (mvp+)
  State: "IMPLEMENT complete — all tasks merged. Ready for /release."
```

---

## /release — UAT + Store-Release Plan + Go-Live Gate

```
Read constitution.md + roles.yml
Read tasks.md + qa-testcases.summary.md (mvp+) + brd.summary.md
+ srd.summary.md + docs/runbook/local-setup.md (mvp+)
Read release-template.md

VERIFY GATE: every task in tasks.md is "PR ready" and merged.
  If not — STOP. State: "RELEASE blocked — {N} tasks not yet merged."

Produce:
  1. PRE-RELEASE CHECKLIST — tasks merged, PRs reference TASK-NNN/CHG-NNN,
     tests green, coverage ≥ gate, accessibility checks passed,
     security checklist passed (security-design.md §1, +§2 mvp+),
     traceability complete
  2. UAT PLAN — one row per UC-NNN from srd.md: scenario, tester (from
     roles.yml), device/OS target + environment (staging/TestFlight/
     internal track), result
  3. STORE RELEASE PLAN — build + sign release artifact (CI build
     container §OPS-7) → upload to TestFlight / Play Console internal
     track → staged rollout (e.g. 10% → 50% → 100%) → OTA update push
     (CodePush/EAS, if applicable) → smoke test on real device — owner +
     rollback-if-fails per step
  4. POST-RELEASE SMOKE TEST — app launch/cold start, key happy-path flow,
     key API call succeeds, crash-free rate target, error-tracking SDK live
  5. GO-LIVE GATE — Tech Lead / Product Owner / Ops-SRE: Go / No-Go
  6. BUSINESS OBJECTIVE CLOSURE — every BO-NNN: metric, measured result
     or "measure after N days", met? yes/pending
  7. ROLLBACK PLAN — summary, points to runbook §6 (staged rollout halt,
     OTA rollback, store-listing rollback)

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
Read failing class/screen/component. Fix → re-run → confirm green.
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
Run /plan-lld and /plan-design (now enabled).
Then update /task with new tasks.
```
