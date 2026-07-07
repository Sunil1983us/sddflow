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
| `/specify` | `/specify` | `/specify` | Constitution Part 2 (DRAFT) only |
| — GATE-1 — | Manual | Manual | You review + finalize constitution Part 2 |
| `/specify-brd` | `/specify-brd` | `/specify-brd` | Business Requirements Document |
| `/specify-uc` | `/specify-uc` | `/specify-uc` | Use Case Specification (Actors + MP/AP/EP) |
| `/specify-srd` | `/specify-srd` | `/specify-srd` | Software Requirements Document |
| `/specify-doc {name}` | `/specify-doc {name}` | `/specify-doc {name}` | One extended doc per invocation (security, data-model, resilience, investigation) |
| `/checklist` (optional) | `/checklist` | `/checklist` | Spec-quality validation (CHK-NNN) |
| `/validate` | `/validate` | `/validate` | Business sign-off on BRD/Use Cases/SRD |
| `/analyze` | `/analyze` | `/analyze` | Risks + complexity |
| `/clarify` | `/clarify` | `/clarify` | Questions → you answer |
| `/plan-design` (unified) — or `/plan-arch` → `/plan-hld` → `/plan-adr` (separate) | same | same | Architecture + Diagrams + API Design + ADRs, per `plan_mode` |
| `/plan-lld` | `/plan-lld` | `/plan-lld` | LLD (mvp+ only) |
| `/task` | `/task` | `/task` | Stories + Tasks + Jira |
| `/implement` | `/implement TASK-NNN` | `/implement TASK-NNN` | Code one task |
| `/release` | `/release` | `/release` | UAT + deployment + go-live gate |
| `/orchestrate` | `/orchestrate` | `/orchestrate` | Drive full pipeline automatically (CLI + multi-agent) — `--list`, `--from STEP`, `--to STEP` |

`plan_mode` (set in `manifest.yml`) picks between a **unified** `/plan-design`
document and a **separate** three-step `/plan-arch` → `/plan-hld` → `/plan-adr`
flow. See "PLAN Sub-Commands" below for both.

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
command — `create-context.md`, `start.md`, `specify.md`, `specify-brd.md`,
`specify-uc.md`, `specify-srd.md`, `specify-doc.md`, `checklist.md`,
`validate.md`, `analyze.md`, `clarify.md`, `plan-design.md`, `plan-arch.md`,
`plan-hld.md`, `plan-adr.md`, `plan-lld.md`, `task.md`, `implement.md`,
`release.md`, plus `change.md`, `orchestrate.md`, and the virtual-team
persona commands (`maya.md`, `rex.md`, `ava.md`, `leo.md`, `kai.md`,
`quinn.md`, `riley.md`, `morgan.md`). Claude Code auto-discovers these —
nothing to install or configure.

- Type `/start` at the beginning of every session — equivalent to STEP 0
  below (reads CLAUDE.md, manifest, constitution, summary-rules,
  change-rules, roles.yml, instructions).
- Type `/specify`, `/specify-brd`, `/specify-uc`, `/specify-srd`,
  `/specify-doc {name}`, `/checklist`, `/validate`, `/analyze`, `/clarify`,
  `/plan-design` (or `/plan-arch`/`/plan-hld`/`/plan-adr`), `/plan-lld`,
  `/task`, `/release` to run each command — Claude reads the matching
  `.github/prompts/<name>.prompt.md` and executes it.
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
2. **Step 1.5 — Feature Size Check:** before drafting, checks whether the
   pasted notes actually describe one feature-sized slice or 2+
   independently-shippable capabilities (separately usable actor+goal
   clusters, barely-overlapping actor sets, unrelated resource domains, or
   epic-style "and also" language). If only one cluster is found, this is
   silent and drafting proceeds as normal. If 2+ clusters are found, the
   agent STOPS and asks whether to build one feature at a time — reply
   "all" to keep everything as one feature, or pick a cluster to build
   first. Any deferred cluster's raw notes are saved to
   `.specify/contexts/{other-slug}.raw.md` for a later `/create-context`
   run — nothing is discarded.
3. Fills in what it can infer, marks the rest `[MISSING — ask user]`.
4. Gives you a plain-language "Missing Information" checklist.
5. You answer what you can — "not sure" is fine for technical questions
   (the architect decides later at `/plan-design`).
6. Repeat until you say "good enough, proceed" or nothing is missing.
7. Saves `.specify/contexts/{feature}.md` — the file `/specify` reads.

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
  (AI-7 — apply each file's applyTo glob to matching files you touch.
  These model the Java/Spring reference stack — if constitution Part 2
  → Language/Framework differs, apply each rule's intent using that
  language's idioms and conventions, don't skip it.)

Confirm:
  Project name: {value}
  Scope: {pilot | mvp | full}
  Feature: {value}
  Context file: {value}
  Workflow mode: {github | local}
  Plan mode: {unified | separate}
  Constitution Part 2: generated? yes/no
  Constitution Part 2 finalized (GATE-1)? yes/no
  Commands for this scope: {list}
  PR rules: max {N} lines, {N} files

State which command is ready to run.
If Part 2 generated but not finalized → remind: complete GATE-1 before
/specify-brd.
```

---

## Living Documents — Service-Level, Not Per-Feature

Three documents describe something singular for the **whole service**, not
one feature. They live at `.specify/service/` instead of
`.specify/features/{feature}/`, are generated once by whichever feature
reaches them first, and are then **extended/amended by every later
feature** — never regenerated from a blank template:

| Document | Generated by | Lives at |
|---|---|---|
| Data Model | `/specify-doc data-model` | `.specify/service/data-model.md` |
| Security Design | `/specify-doc security` | `.specify/service/security-design.md` |
| API Design | `/plan-design` §3 (extracted — see PLAN Sub-Commands) | `.specify/service/api-spec.md` |

When one of these already exists, the generating command **walks it**
instead of regenerating it — one logical unit at a time (one entity, one
threat entry, one endpoint), classified SKIP / ADD-unit / UPDATE-unit, shown
as a delta only, one approval before saving. This is the same discipline
`/change` uses for document updates. A per-feature document that touches
one of these (e.g. `design.md` §3) never restates the full content — it
contains only a pointer plus this feature's new/changed units.

`docs/runbook/local-setup.md` and `docs/openapi.yaml` (both generated by
`/implement`, not `/specify-doc`) are living artifacts too, for the same
reason — see the `/implement` section below.

**Other cross-feature reuse mechanisms (not living documents, but the same
"don't re-derive what's already established" spirit):**
- **Service NFR Baseline** — `constitution.md` Part 2 has an NFR Baseline
  row, left `[MISSING — ask user]` until the first feature's
  `/specify-srd` run fills it retroactively from its own NFR-NNN values.
  Every later feature's `srd.md` references the baseline ("applies to this
  feature too, no change") instead of restating the numbers, and only adds
  its own NFR-NNN row for something genuinely stricter or new.
- **Actor Registry reuse** — `/specify-uc` checks whether an actor it's
  about to derive already exists in another feature's `use-cases.md` (same
  real-world role). If so, it reuses that actor's Name/Type/Description
  verbatim instead of re-deriving them, noting "(same as {prior-feature}'s
  ACT-NNN)". The ACT-NNN identifier itself is still local to this
  feature's own file.
- **Architecture-shell reuse** — the Architecture Pattern, Layer
  Responsibilities, Cross-Cutting Concerns, and the System Context /
  Container diagrams are established once by the first feature to reach
  `/plan-design` (or `/plan-arch` / `/plan-hld` in separate mode) and
  referenced by later features as "unchanged from {feature}, see there" —
  only expanded with a delta if a later feature genuinely needs to change
  them (new layer, new external system).

---

## Document Inventory by Scope/Command (canonical — single source of truth)

| Command | Pilot | MVP | Full |
|---|---|---|---|
| `/specify` | constitution Part 2 (DRAFT) — all scopes |||
| GATE-1 (manual) | constitution Part 2 finalized — all scopes |||
| `/specify-brd` | brd.md — all scopes |||
| `/specify-uc` | use-cases.md — all scopes |||
| `/specify-srd` | srd.md — all scopes |||
| `/specify-doc security` | security-design.md §1 (living, `.specify/service/`) | §1–2 | §1–4 |
| `/specify-doc data-model` | skip | data-model.md (living, `.specify/service/`) | data-model.md (living) |
| `/specify-doc resilience` | skip | skip | resilience.md |
| `/specify-doc investigation` | skip | skip | investigation.md |
| `/checklist` | optional | mandatory | mandatory |
| `/validate` | validate.md — all scopes |||
| `/analyze` | analyze.md — all scopes |||
| `/clarify` | clarify.md — all scopes |||
| `/plan-design` (unified) or `/plan-arch`→`/plan-hld`→`/plan-adr` (separate) | design.md/arch.md+hld.md (ADR skipped) — API Design §3 extracted into living `.specify/service/api-spec.md` | + adr.md | + adr.md |
| `/plan-lld` | skip | lld.md | lld.md |
| `/task` | stories.md, tasks.md, jira, smoke-tests.md (≤10 cases, replaces qa-testcases.md) | + qa-testcases.md | + qa-testcases.md |
| `/implement` | code + paired tests | + qa_cases, runbook (living) | + qa_cases, runbook (living), openapi (living) |
| `/release` | release.md — all scopes |||

Notes:
- **`api-spec.md` is never a `/specify` or `/specify-doc` target.** It does
  not exist until `/plan-design` (or the separate-mode equivalent) extracts
  it from §3 API Design — see "PLAN Sub-Commands" below.
- **`data-model.md` and `security-design.md` are living, service-level
  documents available from `mvp` scope** (data-model) **and all scopes**
  (security-design, section-scaled) — not per-feature files, and not
  gated to `full` only.
- If any other document in this pack lists a different mapping, this table
  wins — fix the other document.

---

## /specify — Constitution Part 2 Only

`/specify` no longer generates spec documents. It generates **only**
constitution Part 2 (DRAFT); every spec document is produced by its own
dedicated sub-command afterward — same pattern as `/plan-*`.

```
Read .specify/manifest.yml
Read .specify/memory/constitution.md + summary-rules.md
Read .specify/contexts/{manifest.project.context_file}

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

  Service NFR Baseline: leave [MISSING — ask user] on first /specify run
  — the first feature's /specify-srd fills it retroactively; later
  features never overwrite it except via an explicit Constitution
  Amendment (see "Living Documents" above)

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
  every row (GATE-1), then run /specify-brd."
```

After GATE-1 passes, generate spec documents **one at a time** via their
own sub-commands, reviewing and approving each before the next runs:

| Command | Document | Gate |
|---|---|---|
| `/specify-brd` | Business Requirements Document | GATE-1 passed |
| `/specify-uc` | Use Case Specification (Actors + UC-NNN with MP/AP/EP) | BRD approved |
| `/specify-srd` | Software Requirements Document | Use Cases approved |
| `/specify-doc {name}` | Any extended doc (security, data-model, resilience, investigation) | SRD approved |

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
- No `/specify-brd`, or any later command, runs until this gate passes.
- A later `/specify` re-run must propose changes for review — it must
  never silently overwrite a finalized Part 2.
- Re-run on finalized Part 2 → produce a Constitution Amendment Summary:
  `{Row}: {old} → {new}` per changed row, cross-referenced against
  change-rules.md's Change Impact Matrix for downstream docs, plus the
  version bump (v{X.Y} → v{X.Y+1}). WAIT for confirmation before applying.

---

## /specify-brd — Business Requirements Document

```
Read manifest.yml + constitution.md + roles.yml
Read .specify/contexts/{feature}.md
Read brd-template.md

GATE: constitution Part 2 finalized (GATE-1 passed)?
  If not — STOP. State: "SPECIFY-BRD blocked — finalize constitution
  Part 2 first (GATE-1)."

Generate brd.md:
  §3 Stakeholders — fill Name/Team from roles.yml; leave ACT-ID column
  "_(set by /specify-uc)_" until actors are defined
  Every business goal: BG-NNN
  Every NFR: NFR-NNN with a measurable target
  Marker discipline: [ASSUMPTION-NNN] / [NEEDS CLARIFICATION: {question}]

Save: brd.md + brd.summary.md

Stakeholder review (Confluence draft if configured → Jira submit → approval
→ Status: Approved + Approvals table + Version History).

Progressive Jira: after approval, write docs/jira/epic.md (Stage:
after-brd) with Business Objectives and Epic Done Condition.

State: "BRD generated. Review, then run /specify-uc."
```

---

## /specify-uc — Use Case Specification

```
Read manifest.yml + constitution.md
Read brd.summary.md (or brd.md, per reading_mode)
Read use-cases-template.md

GATE: brd.md approved? (sdd review check --doc brd, or ask user to confirm)
  If not — STOP.

Generate use-cases.md:
  Every actor: ACT-NNN (Primary / Secondary / System)
    Actor Registry reuse: before deriving an actor from scratch, check
    whether it already appears in another feature's use-cases.md in this
    service (same real-world role). If so, reuse its Name/Type/
    Description verbatim and note "(same as {prior-feature}'s ACT-NNN)" —
    only the description is reused, the ACT-NNN identifier stays local to
    this feature's file
  Every use case: UC-NNN — Trigger, Preconditions, Postconditions
    (success/failure), Main Path (MP, actor/action/system response),
    ≥1 Alternate Path (AP-NNN-X), ≥1 Exception Path (EP-NNN-X)
  §4 Use Case Relationships — Mermaid graph LR (includes/extends)
  §5 Traceability — UC-NNN → BR-NNN
  Marker discipline: [ASSUMPTION-NNN] / [NEEDS CLARIFICATION]

Back-fill brd.md §3 Stakeholders — replace "_(set by /specify-uc)_" with
the assigned ACT-NNN per role; re-save brd.md + brd.summary.md.

Save: use-cases.md + use-cases.summary.md

Stakeholder review + approval (same Confluence/Jira/chat flow as BRD).

Progressive Jira: docs/jira/stories-draft.md — one draft Story per UC-NNN.

State: "Use Cases generated. Review, then run /specify-srd."
```

---

## /specify-srd — Software Requirements Document

```
Read manifest.yml + constitution.md
Read brd.summary.md + use-cases.summary.md
Read srd-template.md

GATE: use-cases.md approved? (implies brd.md already approved)
  If not — STOP.

Generate srd.md:
  Every FR-NNN traces to a UC-NNN (Main/Alternate/Exception Path steps →
  FR-NNN)
  NFRs refine BRD NFRs with technical targets

  Service NFR Baseline mechanism (constitution.md's NFR Baseline row):
    If [MISSING — ask user] (first feature to reach /specify-srd): derive
    this pack's baseline categories from this feature's own NFRs, fill
    the constitution row(s), note in srd.md §3: "Establishes the NFR
    baseline — see constitution.md."
    If already filled (a later feature): srd.md §3 states "Baseline
    (constitution.md → NFR Baseline): {values} — applies to this feature
    too, no change" and adds its own NFR-NNN row only for something
    stricter/new. A stricter/different baseline is a Constitution
    Amendment, not a silent overwrite.

  Marker discipline: [ASSUMPTION-NNN] / [NEEDS CLARIFICATION]

Back-fill use-cases.md: replace "_(filled by /specify-srd)_" in §2 index
and §3 per-UC "Linked FR-NNN" with the derived FR-NNN list; re-save
use-cases.md + use-cases.summary.md.

Save: srd.md + srd.summary.md

Stakeholder review + approval (same flow).

Progressive Jira: docs/jira/stories-refined.md — FR-NNN links + MoSCoW
priority added to each draft story.

State: "SRD generated. Review, then run /specify-doc {next-doc} — remaining
for this scope: {list}."
```

---

## /specify-doc {name} — Extended Documents (one at a time)

```
Input: document name — security | data-model | resilience | investigation
  (this pack's set; NOT api-spec — that moved to /plan-design §3)

Read manifest.yml + constitution.md
Read brd.summary.md + use-cases.summary.md + srd.summary.md
Read {doc}-template.md

GATE 1: srd.md approved?
  If not — STOP.
GATE 2: is {doc} in scope for manifest.project.scope?
  If not — State: "{DOC} is not in scope for {scope}. Skipping."

Generate {doc}.md:
  Derive from brd/srd/constitution; flag (don't silently resolve) any
  contradiction with an already-approved decision
  Marker discipline: [ASSUMPTION-NNN] / [NEEDS CLARIFICATION]
```

**`data-model` and `security` are living, service-level documents** — see
"Living Documents" above. For these two only:
- Save to `.specify/service/{doc}.md` (NOT under `.specify/features/`)
- If `.specify/service/{doc}.md` does **not** exist yet: generate fresh —
  this becomes the service's living reference; future features extend it.
- If it **already exists**: walk it one unit at a time (one entity, one
  threat entry) — SKIP / ADD-unit (show only the new unit + why) /
  UPDATE-unit (BEFORE/AFTER for only that unit + why). STOP and wait for
  approval before saving anything. On approval: merge, bump version header,
  append a Version History row naming the triggering feature, regenerate
  `.specify/service/{doc}.summary.md`.

**`security` scope-scaling:** pilot → §1 only (Threat Assessment); mvp →
§1–2 (+ OWASP Top 10 + STRIDE); full → §1–4 (+ DAST + pentest scope). STRIDE
threats rated with DREAD; score ≥10 Critical, 7–9 High — mitigations
required for High/Critical before `/plan-design`.

**Every other document (`resilience`, `investigation`) stays per-feature:**
save to `.specify/features/{feature}/{doc}.md` + `.summary.md` as normal.

Each run ends: "{DOC} generated. Review, then run /specify-doc
{next-doc}." or, once all are done: "all spec documents complete. Run
/validate."

---

## /checklist — Spec-Quality Validation (Optional, after GATE-1)

Run this between the last `/specify-doc` and `/validate` to catch spec
quality issues early — before the business sign-off meeting.

**Mandatory for `mvp` and `full` scope. Optional for `pilot`.**

```
Read manifest.yml + constitution.md
Read brd.summary.md + use-cases.summary.md + srd.summary.md
Read checklist-template.md

Checks (in order):
  CRITICAL (block /validate):
    Unresolved [NEEDS CLARIFICATION] markers in brd/srd
    NFR-NNN without numeric threshold
    FR-NNN with no UC-NNN coverage
    UC-NNN with no Main Path, or missing an AP-NNN-X/EP-NNN-X

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

If CRITICAL items: State "Fix CRITICAL items in the spec docs directly,
re-run /checklist to confirm all CRITICAL items closed."
If no CRITICAL: State "Spec quality gate passed — ready for /validate"
```

---

## /validate — Business Sign-Off (runs after all spec docs approved)

```
Read manifest.yml + constitution.md + roles.yml
Read brd.summary.md + use-cases.summary.md + srd.summary.md
Read validate-template.md

GATE-1 CHECK: constitution Part 2 finalized?
  If not — STOP. State: "GATE-1 open — finalize constitution Part 2
  before /validate."

Produce:
  0. CHECKLIST GATE (advisory) — warn if open CRITICAL CHK-NNN items exist
  1. BUSINESS OBJECTIVE TRACE — every BO-NNN → FR-NNN(s) that address it.
     Flag any BO-NNN with no FR.
  2. BUSINESS REQUIREMENTS REVIEW — every BR-NNN correctly reflected in
     srd.md? Flag mismatches.
  3. ASSUMPTIONS SIGN-OFF — every [ASSUMPTION-NNN] in brd/srd for the
     business owner to confirm or reject.
  3a. NEEDS CLARIFICATION SCAN — scan brd/use-cases/srd for [NEEDS
      CLARIFICATION] markers; these are BLOCKING — must be resolved
      before sign-off.
  4. SCOPE CONFIRMATION — in-scope / out-of-scope items from brd.md.
  4a. SECURITY DESIGN SIGN-OFF (mvp+) — if security-design.md exists and
      is not yet signed off, block /analyze until the Security Officer
      approves it.
  4b. INDICATIVE EFFORT (T-shirt) — S/M/L/XL per FR-NNN; indicative only,
      story points come at /task.
  5. SIGN-OFF — Product Owner + Business Analyst (names from roles.yml):
     Approved / Changes Requested.

Save: validate.md + validate.summary.md
Present report. WAIT for sign-off.

If approved:
  State: "VALIDATE complete — ready for /analyze."
Else:
  State: "VALIDATE incomplete — {N} items need changes. Update the
  relevant spec docs, re-run /validate."
  Do NOT proceed to /analyze.
```

---

## /analyze — Risk + Complexity

```
Read constitution.md + summary-rules.md
Read validate.summary.md + brd.summary.md + use-cases.summary.md
+ srd.summary.md
Read analyze-template.md

GATE CHECK: validate.summary.md states "VALIDATE complete"?
  If not — STOP. State: "ANALYZE blocked — run /validate first."

Produce:
  RISKS: every integration + flow + NFR
    Each: likelihood (L/M/H) + impact (L/M/H/Critical) + mitigation

  DEPENDENCIES: internal + external + timeline
    Each: blocking/non-blocking + owner + risk

  COMPLEXITY: by feature area + by FR
    Each: LOW/MEDIUM/HIGH + reason
    Flag HIGH → these need SPLIT tasks later

  NFR IMPACT: design constraints from NFRs

  UNKNOWNS: items needing spike before design

  CONSISTENCY: cross-artifact audit (CF-NNN items)
    DUPLICATION, AMBIGUITY, COVERAGE GAPS, TERMINOLOGY DRIFT,
    CONSTITUTION CONFLICTS (CRITICAL → block /clarify until resolved)

  RECOMMENDATION:
    Suggested approach, items for /clarify, tasks likely needing SPLIT

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
State: "CLARIFY complete — ready for the PLAN phase"
```

---

## PLAN Sub-Commands

PLAN adapts to your `plan_mode` setting in `manifest.yml` (set during
`setup.sh`, switchable mid-project by replying "unified"/"separate" when
prompted).

### Unified mode (`plan_mode: unified`) — one combined document, one review gate

**`/plan-design`** → `design.md`: Architecture + Diagrams + API Design + ADR entries, all in one document.

```
Read constitution.md + summary-rules.md
Read clarify.summary.md (MUST exist, all RESOLVED — stop if missing)
Read analyze.summary.md + all spec summaries (brd, use-cases, srd, security)
Read design-template.md

AI-8 GATE CHECK: scan brd.md, use-cases.md, srd.md, security-design.md for
any [ASSUMPTION-NNN] without a matching <!-- Clarified: {ID} --> note.
  If any remain — STOP. State: "PLAN-DESIGN blocked — unresolved
  assumptions {list}. Run /clarify first."

§1 ARCHITECTURE OVERVIEW:
  Pattern, layers, and cross-cutting concerns describe the whole service,
  not this feature — established once by the first feature to reach here,
  referenced by later features as "unchanged from {feature}/design.md §1,
  see there" (only expanded with a delta if genuinely changed).
  DEC-NNN key decisions + NFR → decision mapping are always feature-specific.

§2 DIAGRAMS:
  System Context (C4 L1) and Container Diagram (C4 L2) describe the whole
  service's topology — same reuse rule as §1.
  Always fresh: Component Diagram (C4 L3), Happy Path Sequence, Error/
  Failure Paths (from EP-NNN-X), State Machine (if applicable).

§3 API DESIGN:
  The API surface is living, service-level — .specify/service/api-spec.md,
  not inline in design.md. Check whether it already exists:
    Does NOT exist yet: generate fresh at .specify/service/api-spec.md
    (method, path, request/response schema, error codes, FR/UC trace,
    error envelope, async contracts). Write api-spec.summary.md alongside.
    Already exists: walk it one endpoint/schema at a time — SKIP / new
    endpoint (show only the new definition) / changed endpoint (BEFORE/
    AFTER) — same format as /change, one approval, then merge + bump
    version + Version History row + regenerate summary.
  design.md §3 itself never contains the full API — only a pointer to
  api-spec.md plus this feature's new/changed endpoints.
  (Skip §3 for iac/library/desktop-with-no-backend project types. For
  frontend-spa/mobile, §3 documents the consumer view directly in
  design.md, per-feature — the living-doc treatment applies only when
  this service provides the API.)

§4 ARCHITECTURE DECISIONS (ADR): one ADR per DEC-NNN from §1 — pilot:
  minimum 2 for the most impactful; mvp+: one per DEC-NNN.

Diagram self-check (node/edge consistency, balanced brackets, consistent
participant names) before saving.

Save: design.md + design.summary.md

pilot scope → "run /task next"
mvp+ scope → "run /plan-lld next"
```

### Separate mode (`plan_mode: separate`) — three focused documents, reviewed individually

| Step | Command | Document | Gate |
|---|---|---|---|
| 1 of 3 | `/plan-arch` | `arch.md` — pattern, layers, DEC-NNN, NFR mapping, cross-cutting concerns | clarify.summary.md RESOLVED + no unresolved [ASSUMPTION-NNN] (AI-8) |
| 2 of 3 | `/plan-hld` | `hld.md` — C4 context/container, happy-path sequence, state machine (Mermaid) | `arch.md` `Status: Approved` |
| 3 of 3 | `/plan-adr` | `adr.md` — one ADR per DEC-NNN (mvp+ only; skipped at pilot) | `hld.md` `Status: Approved` |

- `arch.md` §1 (Architecture Overview), §3 (Layer Responsibilities), and §6
  (Cross-Cutting Concerns) are the whole-service shell — reused via
  "unchanged from {prior-feature}/arch.md §{N}, see there" once a prior
  feature has established them. §2 Component Structure and §4 Key Design
  Decisions (DEC-NNN) are always feature-specific.
- `hld.md` Diagrams 1–2 (System Context, Container) reuse the same way;
  diagrams 3–4 (sequence, state machine) are always fresh per feature.
- **API Design has no separate-mode command** — in both modes it is
  extracted the same way, at the point `/plan-design` §3 would run; in
  separate mode this pack still routes API extraction through
  `/plan-design` §3's logic (see unified mode above) even though
  architecture/diagrams/ADRs are split. Check `plan-design.prompt.md` if
  your session needs it in separate mode — the living-document mechanism
  for `api-spec.md` is identical either way.
- pilot scope: `/plan-adr` is skipped — after `hld.md` approval, go
  directly to `/task`.

### Both modes

**`/plan-lld`** → detailed technical design: package/folder structure,
class diagrams, component diagrams, detailed sequence diagrams (incl.
error handling), ERD, key method signatures, DTO/record definitions.
- mvp+ only; **SKIP if pilot** — state the skip and proceed to `/task`.
- Unified gate: `design.md` `Status: Approved`.
- Separate gate: `adr.md` approved (mvp+) — pilot never reaches `/plan-lld`
  since it's also skipped there.

---

## /task — Feature → Story → Task + Jira

```
Read constitution.md + summary-rules.md
Read analyze.summary.md + clarify.summary.md + srd.summary.md
+ use-cases.summary.md (for EP-NNN exception paths — must not be skipped)
Unified mode: design.summary.md
Separate mode: lld.summary.md (mvp+) or hld.summary.md (pilot)
If present: data-model.summary.md (entity names) + api-spec.summary.md
  (living, .specify/service/ — endpoint names for file/task derivation)
Read feature-story-template.md + tasks-template.md + jira-export-template.md
+ qa-testcases-template.md

VERIFY: unified — design.md approved. Separate — hld.md approved (pilot) or
lld.md reviewed (mvp+). Stop if not.

1. QA TEST CASES:
   pilot: skip full qa-testcases.md — generate smoke-tests.md instead
     (≤10 cases: one per UC Main Path + one per EP-NNN-X, Given/When/Then).
     tasks.md uses "Verifies: TBD — link at /implement".
   mvp+: for each FR-NNN / endpoint, TC-NNN covering happy path,
     validation, auth, unhappy path, performance; one TC-NNN per EP-NNN-X;
     boundary-value TC-NNN for numeric/bounded inputs; PERF-NNN task per
     measurable NFR.
   Save: qa-testcases.md + qa-testcases.summary.md (mvp+) or
   smoke-tests.md (pilot)

2. FEATURE + STORIES:
   Each story: As {actor} I want {X} so that {Y}, linked to FR-NNN, story
   points, sprint, MoSCoW priority, acceptance criteria.
   Traceability: Story → FR → Task → TC-NNN (mvp+) → EP-NNN → R-NNN
   Save: stories.md + stories.summary.md

3. TASK LIST:
   Each task: Story, Satisfies (FR/NFR), Verifies (TC-NNN or TBD at
   pilot), Risk (R-NNN if flagged), estimated lines, PR strategy, files
   (derived from constitution's Stack Reference, never hardcoded),
   acceptance criteria.
   Auto-split any task > max_lines_per_pr.
   Save: tasks.md

4. JIRA CSV:
   Tasks-only CSV if Epic/Story keys already exist (docs/jira/keys.yml);
   full hierarchy otherwise.
   Save: docs/jira/stories.md + docs/jira/jira-import.csv

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
  Write paired test alongside — never after (or per manifest.testing_style:
  tdd / bdd — see implement.prompt.md)
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
  Generate delivery per scope. docs/runbook/local-setup.md and
  docs/openapi.yaml are living, service-level artifacts — check whether
  each already exists before writing:
    qa_cases  → docs/qa/functional-test-cases.md (mvp+) — finalize
                qa-testcases.md with pass/fail results
    runbook   → docs/runbook/local-setup.md (mvp+). If it already exists
                (a prior feature created it): Local Setup, Profiles,
                Common Operations, Rollback rarely change — leave as-is;
                only add this feature's new Troubleshooting entries, env
                vars, or alert mappings. Never regenerate the whole file.
    openapi   → docs/openapi.yaml (full, from api-spec.summary.md). If it
                already exists: merge in only this feature's new/changed
                paths — regenerating from scratch would drop every prior
                feature's endpoints.
  State: "IMPLEMENT complete — all tasks merged. Ready for /release."
```

---

## /release — UAT + Deployment + Go-Live Gate

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
  2. UAT PLAN — one row per UC-NNN from use-cases.md: scenario, tester
     (from roles.yml), environment, result
  3. DEPLOYMENT PLAN — the deployment strategy and rollback steps are
     standard for this service, not re-derived per release: pull them
     from docs/runbook/local-setup.md (living, established once) and
     constitution.md's Orchestration row. Write "Standard deployment —
     see docs/runbook/local-setup.md §{N}" rather than re-describing the
     strategy. Fill in only what's specific to this release: DB migration
     version(s), any new feature flag, owner, and confirmation the
     standard steps still apply (or a note on what's different this time).
  4. POST-DEPLOY SMOKE TEST — the checks themselves are standard, pulled
     from docs/runbook/local-setup.md. Fill in only this release's
     specific happy-path endpoint and NFR target.
  5. GO-LIVE GATE — Tech Lead / Product Owner / Ops-SRE: Go / No-Go
  6. BUSINESS OBJECTIVE CLOSURE — every BO-NNN: metric, measured result
     or "measure after N days", met? yes/pending
  7. ROLLBACK PLAN — summary, points to docs/runbook/local-setup.md §6

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
Tell agent "Constitution Part 2 finalized" to unblock /specify-brd.
```

### Regenerate a Document

**Per-feature documents** (brd, use-cases, srd, resilience, investigation,
design/arch/hld/adr, lld, tasks, etc.):
```
Discard .specify/features/{feature}/{doc}.md
Re-read template + context
Regenerate → save same path + summary
```

**Living documents — NEVER do the above.** `data-model.md`,
`security-design.md`, and `api-spec.md` at `.specify/service/` are shared
across every feature in this service. Discarding and regenerating one from
a blank template destroys every other feature's contributions (their
entities, endpoints, threat entries). Always extend a living document via
its command's SKIP / ADD-unit / UPDATE-unit walk instead (see "Living
Documents" above) — never regenerate it wholesale, even to fix a mistake;
fix the mistake as a targeted UPDATE-unit on just the affected unit.

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
Generate newly required /specify-doc {name} documents (e.g. data-model
at mvp, resilience/investigation at full).
Run /plan-adr (separate mode, now enabled at mvp+) and /plan-lld (now
enabled) — both were skipped previously at pilot.
Then update /task with new tasks.
```
