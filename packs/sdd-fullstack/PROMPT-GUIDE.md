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
| `/create-context` (optional) | `/create-context` | `/create-context` | Turn informal notes into context.md (backend + frontend), with a Feature Size Check if the notes describe more than one feature |
| Startup | `/start` | Step 0 | Read files + confirm |
| `/specify` | `/specify` | `/specify` | Constitution Part 2 (DRAFT, both layers) — spec docs are generated separately |
| **GATE-1** | Manual | Manual | You review + finalize constitution Part 2 |
| `/specify-brd` | `/specify-brd` | `/specify-brd` | Business Requirements Document |
| `/specify-uc` | `/specify-uc` | `/specify-uc` | Use Case Specification (Actors + UC-NNN with MP/AP/EP) |
| `/specify-srd` | `/specify-srd` | `/specify-srd` | Software Requirements Document |
| `/specify-doc {name}` | `/specify-doc {name}` | `/specify-doc {name}` | One extended doc at a time (security, component-spec, ux-flow, data-model, resilience, investigation) |
| `/checklist` (optional) | `/checklist` | `/checklist` | Spec-quality validation (CHK-NNN) |
| `/validate` | `/validate` | `/validate` | Business sign-off on BRD/Use Cases/SRD |
| `/analyze` | `/analyze` | `/analyze` | Risks + complexity |
| `/clarify` | `/clarify` | `/clarify` | Questions → you answer |
| `/plan-design` (unified) | `/plan-design` | `/plan-design` | Architecture + Diagrams + API Design + ADRs, one document |
| `/plan-arch` → `/plan-hld` → `/plan-adr` (separate) | same | same | Same content, three focused documents reviewed individually |
| `/plan-lld` | `/plan-lld` | `/plan-lld` | LLD (mvp+ only) |
| `/task` | `/task` | `/task` | Stories + Tasks + Jira |
| `/implement` | `/implement TASK-NNN` | `/implement TASK-NNN` | Code one task |
| `/release` | `/release` | `/release` | UAT + deployment + go-live gate |
| `/orchestrate` | `/orchestrate` | `/orchestrate` | Drive full pipeline automatically (CLI + multi-agent) — `--list`, `--from STEP`, `--to STEP` |

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
command — including `create-context.md`, `start.md`, `specify.md`,
`specify-brd.md`, `specify-uc.md`, `specify-srd.md`, `specify-doc.md`,
`checklist.md`, `validate.md`, `analyze.md`, `clarify.md`, `plan-design.md`,
`plan-arch.md`, `plan-hld.md`, `plan-adr.md`, `plan-lld.md`, `task.md`,
`implement.md`, `release.md`, `change.md`, and the virtual-team names
(`maya.md`, `rex.md`, `ava.md`, `leo.md`, `kai.md`, `quinn.md`, `riley.md`,
`morgan.md`). Claude Code auto-discovers these — nothing to install or
configure.

- Type `/start` at the beginning of every session — equivalent to STEP 0
  below (reads CLAUDE.md, manifest, constitution, summary-rules,
  change-rules, roles.yml, instructions).
- Type `/specify`, `/specify-brd`, `/specify-uc`, `/specify-srd`,
  `/specify-doc {name}`, `/validate`, `/analyze`, `/clarify`,
  `/plan-design` (or `/plan-arch`/`/plan-hld`/`/plan-adr` in separate
  mode), `/plan-lld`, `/task`, `/release` to run each command — Claude
  reads the matching `.github/prompts/<name>.prompt.md` and executes it.
- `/implement TASK-NNN` passes the task ID through to the implement prompt.
- Editing a `.github/prompts/<name>.prompt.md` file (as described in
  CHANGE-GUIDE.md) automatically updates the matching slash command — the
  command files only delegate, they don't duplicate instructions.

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
1. **Feature Size Check (Step 1.5):** before mapping the input onto the
   template, checks whether the notes actually describe ONE feature-sized
   slice or several independently-shippable ones (clustered by
   "actor + goal" — separate actor sets, no shared entity, epic-style
   phrasing). If 2+ clusters are found, it STOPS and asks whether to build
   them as **one feature** ("all") or **split and build one at a time**
   (pick a cluster, or "custom: {grouping}"). If you split, every other
   cluster's raw notes are saved to `.specify/contexts/{other-slug}.raw.md`
   for later — never silently discarded. If only one cluster is found,
   this step is silent and doesn't interrupt you.
2. Maps your input onto context-template.md's sections (What This Service
   Does, Actors, Key Flows, Endpoints, Integrations, Business Rules, NFRs,
   Constraints, Out of Scope, Open Questions, Tech Stack — Backend /
   Frontend / Shared sub-tables).
3. Fills in what it can infer, marks the rest `[MISSING — ask user]`. If
   you only described one layer, the other layer's Tech Stack sub-table is
   marked `[MISSING — ask user]` rather than guessed. For Endpoints and
   NFRs specifically, it may instead propose a scope-appropriate
   `(SUGGESTED DEFAULT — edit or confirm)` starting point rather than a
   blank marker.
4. Gives you a plain-language "Missing Information" checklist, split into
   defaults to confirm/override and gaps that still need your input.
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
/specify-brd.
```

---

## Document Inventory by Scope/Command (canonical — single source of truth)

`/specify` generates the constitution only. Spec documents are generated
one at a time by dedicated sub-commands — the table below shows what each
command produces per scope.

| Command | Pilot | MVP | Full |
|---|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) — all scopes |||
| GATE-1 (manual) | constitution Part 2 finalized — all scopes |||
| `/specify-brd` | brd.md — all scopes |||
| `/specify-uc` | use-cases.md — all scopes |||
| `/specify-srd` | srd.md — all scopes |||
| `/specify-doc security` | security-design.md §1 (living — `.specify/service/security-design.md`) | + §1-2 | + §1-4 |
| `/specify-doc component-spec` | skip | component-spec.md (its "Shared Components Used" section is living — `.specify/service/component-library.md`) | same |
| `/specify-doc ux-flow` | skip | ux-flow.md | same |
| `/specify-doc data-model` | skip | data-model.md (living — `.specify/service/data-model.md`) | same |
| `/specify-doc resilience` | skip | skip | resilience.md |
| `/specify-doc investigation` | skip | skip | investigation.md |
| `/checklist` (manual gate) | optional | mandatory | mandatory |
| `/validate` | validate.md — all scopes |||
| `/analyze` | analyze.md — all scopes |||
| `/clarify` | clarify.md — all scopes |||
| PLAN — unified `/plan-design` or separate `/plan-arch`→`/plan-hld`→`/plan-adr` | design.md (or arch.md + hld.md; ADR skipped) — API Design (§3) documented inline, no living file yet | + adr.md / design.md §4 — API Design (§3) extracted into living `.specify/service/api-spec.md` | same |
| `/plan-lld` | skip | lld.md | lld.md |
| `/task` | stories.md, tasks.md, jira, smoke-tests.md (≤10 cases) | stories.md, tasks.md, jira, qa-testcases.md | same |
| `/implement` | code + paired tests + openapi.yaml | + qa_cases, runbook | + qa_cases, runbook |
| `/release` | release.md — all scopes |||

**Notes:**
- `api-spec.md` is **not** a `/specify-doc` target — it does not exist as a
  standalone generation command. It is extracted from `design.md` §3
  during the PLAN phase and lives as a **living, service-level document**
  at `.specify/service/api-spec.md` (mvp+), shared across every feature in
  this service. At pilot scope, `design.md` §3 documents the API inline —
  no living file is created.
- `data-model.md` is available at **mvp+** (not full-only) — same tier as
  `component-spec` and `ux-flow`.
- `component-library.md` is a **living document** at
  `.specify/service/component-library.md`, populated by `/specify-doc
  component-spec` whenever a feature contributes a shared/reusable
  component — it is not a separate command.

If any other document in this pack lists a different mapping, this table
wins — fix the other document.

---

## /specify — Constitution Part 2 Only

`/specify` generates the constitution **only**. Spec documents are
generated one at a time using dedicated sub-commands — see the sections
below.

```
Read .specify/manifest.yml
Read .specify/memory/constitution.md + summary-rules.md
Read .specify/contexts/{manifest.project.context_file}
Read all templates needed per scope

ACTION 1 — Generate constitution.md Part 2 (DRAFT):
  Extract from context and fill — split Backend / Frontend / Shared
  (this pack covers both layers — fill Backend AND Frontend; Shared
  applies to both):

  Backend Tech Stack: Language, Framework, Build Tool, Messaging/Async,
    Schema, Data Store, Data Cache, DB Migration, Resilience, Testing,
    Coverage Gate

  Frontend Tech Stack: Language, Framework, Build Tool, State Management,
    Component Library/Design System, Routing, API Client, Data Cache,
    Testing, Coverage Gate, Accessibility

  Shared Tech Stack: API Style, Serialisation, Configuration, Secrets,
    Observability, Logging, Quality/Security, Orchestration, CI/CD

  Service NFR Baseline — split Backend (Performance, Availability,
    Throughput, Data Retention) / Frontend (Load Time, Bundle Size,
    Interactivity). If context.md states values, fill them; if not,
    leave as [MISSING — ask user] — the first feature's /specify-srd
    run fills this retroactively from its own NFR-NNN rows once
    approved. This baseline is filled ONCE per service — later features
    reference it in srd.md rather than restating it.

  If concern not in context → use sensible default
  If critical concern missing → mark [MISSING — ask user]

  Core Principles → derive from domain:
    payments domain → "Idempotency First"
    regulated domain → "Compliance First"
    real-time domain → "Latency Budget"
    Always add: Specification First, Test Discipline, Traceability

  Domain Rules → extract from business rules / constraints / integration
    contracts (both layers)
  Never Do → extract from stated constraints + regulatory requirements

  Save constitution.md (Part 1 unchanged, Part 2 = DRAFT)
  Report: "Constitution Part 2 generated — DRAFT. Review and finalize
  every row (GATE-1), then run /specify-brd."

GATE-1: Do NOT proceed to spec-doc generation in the same turn as a
first-time generation unless the user has already reviewed Part 2. A
later /specify re-run on an already-finalized Part 2 must propose changes
for review — never silently overwrite finalized rows.
```

State: "Constitution Part 2 generated — DRAFT. Review and finalize every
row (GATE-1), then run **/specify-brd**."

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

```
Open .specify/memory/constitution.md → Part 2 (DRAFT from /specify)

Review every row:
  - Tech Stack — Backend, Frontend, and Shared tables
  - Service NFR Baseline — Backend, Frontend
  - Core Principles
  - Domain Rules
  - Never Do

Resolve any [MISSING — ask user] markers — fill the value yourself
Edit directly anything that is wrong — manual edits are AUTHORITATIVE

Tell the agent: "Constitution Part 2 finalized"
```

Rules:
- No `/specify-brd`, `/validate`, `/analyze`, or any later command runs
  until this gate passes.
- A later `/specify` re-run must propose changes for review — it must
  never silently overwrite a finalized Part 2.

---

## /specify-brd — Business Requirements Document

```
Read manifest.yml + constitution.md + roles.yml (owners for §3 Stakeholders)
Read .specify/contexts/{feature}
Read brd-template.md

GATE CHECK: constitution.md Part 2 finalized (no "DRAFT" in version line)?
  If not — STOP. State: "SPECIFY-BRD blocked — finalize constitution
  Part 2 first (GATE-1)."

Generate brd.md:
  Every business goal → BG-NNN
  Every NFR → NFR-NNN with a measurable target (e.g. "< 200ms p99")
  §3 Stakeholders — Name/Team from roles.yml; ACT-ID column left as
    "_(set by /specify-uc)_" until actors are defined
  Marker discipline: [ASSUMPTION-NNN] / [NEEDS CLARIFICATION: {question}]

Save: brd.md + brd.summary.md
Stakeholder review → approval flips Status: Draft → Approved
Generate docs/jira/{feature}/epic.md (progressive Jira export)
```

State: "**BRD generated.** Review and approve, then run **/specify-uc**."

---

## /specify-uc — Use Case Specification

```
Read manifest.yml + constitution.md + brd.summary.md (or brd.md)
Read use-cases-template.md

GATE CHECK: brd.md approved?
  If not — STOP. State: "SPECIFY-UC blocked — BRD is not yet approved."

Generate use-cases.md:
  Every actor → ACT-NNN (Primary/Secondary/System)
    Before deriving an actor from scratch, check whether it already
    appears in another feature's use-cases.md in this service (same
    real-world role). If so, REUSE its Name/Type/Description verbatim —
    note "(same as {prior-feature}'s ACT-NNN)" — rather than re-deriving
    it. ACT-NNN numbering stays local to this feature's own file.
  Every use case → UC-NNN: Trigger, Preconditions, Postconditions
    (Success/Failure), Main Path (MP), ≥1 Alternate Path (AP-NNN-X),
    ≥1 Exception Path (EP-NNN-X), Business Rules Applied, Non-Functional
    Constraints
    "Linked FR-NNN" left as "_(filled by /specify-srd)_"
  §4 Use Case Relationships — Mermaid graph LR (includes/extends)
  §5 Traceability Matrix — UC-NNN → BR-NNN

Back-fill brd.md §3 Stakeholders with the assigned ACT-NNN values.

Save: use-cases.md + use-cases.summary.md
Stakeholder review → approval flips Status
Generate docs/jira/{feature}/stories-draft.md (progressive Jira export)
```

State: "**Use Cases generated.** Review and approve, then run
**/specify-srd**."

---

## /specify-srd — Software Requirements Document

```
Read manifest.yml + constitution.md + brd.summary.md + use-cases.summary.md
Read srd-template.md

GATE CHECK: use-cases.md approved (implies brd.md already approved)?
  If not — STOP. State: "SPECIFY-SRD blocked — Use Cases are not yet
  approved."

Generate srd.md:
  Every FR-NNN traces to a UC-NNN (Main/Alternate/Exception Path steps)
  NFRs refine BRD NFRs with technical targets

  Service NFR Baseline check — read constitution.md's NFR Baseline
  section:
    If [MISSING — ask user] (first feature to reach /specify-srd):
      derive the baseline categories from this feature's own NFRs, fill
      constitution.md's row(s), note in srd.md §3: "Establishes the NFR
      baseline — see constitution.md."
    If already filled (a later feature):
      srd.md §3 states "Baseline (constitution.md): {values} — applies
      to this feature too, no change" and only adds its own NFR-NNN row
      for something genuinely different from the baseline. Never
      silently restate the baseline as freshly derived. A stricter/
      different baseline requirement is a Constitution Amendment, not a
      silent overwrite.

  Marker discipline: same as BRD

Back-fill use-cases.md — every UC-NNN's "Linked FR-NNN" and §2 index's
"FR Traces (SRD)" column, replacing the "_(filled by /specify-srd)_"
placeholder.

Save: srd.md + srd.summary.md
Stakeholder review → approval flips Status
Generate docs/jira/{feature}/stories-refined.md (FR-NNN links + MoSCoW priority)
```

State: "**SRD generated.** Review and approve, then run **/specify-doc
{next-doc}**. Remaining for this scope: {list}."

---

## /specify-doc {name} — Extended Spec Documents

One document per invocation — `security`, `component-spec`, `ux-flow`,
`data-model`, `resilience`, or `investigation` (see the Document Inventory
table above for which are in scope at each scope level). `api-spec` is
**not** a valid target here — it is extracted from `design.md` §3 during
the PLAN phase instead (see "Living Documents" below).

```
Read manifest.yml + constitution.md
Read brd.summary.md + use-cases.summary.md + srd.summary.md
Read {doc}-template.md

GATE CHECK: srd.md approved?
  If not — STOP. State: "SPECIFY-DOC blocked — SRD is not yet approved."
SCOPE CHECK: this document required for manifest.scope/project_type?
  If not — State: "{DOC} is not in scope for {scope}. Skipping."

Generate {doc}.md — derive from brd/use-cases/srd; flag any contradiction
with an already-approved decision rather than silently resolving it.
Marker discipline: same as BRD/SRD.
```

**`data-model` and `security` are living, service-level documents** —
they describe the one schema and one security baseline for the whole
service, not this feature's slice of it:
- Save to `.specify/service/{doc}.md` (NOT under `.specify/features/`)
- `security-design.md` scope-based sections: pilot → §1 only; mvp → §1-2
  (+ OWASP Top 10, STRIDE); full → §1-4 (+ DAST, pen-test scope). STRIDE
  threat enumeration + DREAD scoring apply at mvp+; mitigations required
  for all High/Critical threats before `/plan-design`.

**Every other `/specify-doc` target** (`resilience`, `investigation`,
`component-spec`, `ux-flow`) stays per-feature at
`.specify/features/{feature}/{doc}.md` — **except** `component-spec`'s
"Shared Components Used" section, which is living at
`.specify/service/component-library.md` for any component this feature
intends other features to reuse (this feature's own page/container
components stay per-feature as normal).

**Updating an existing living document (data-model, security-design,
component-library):** if `.specify/service/{file}.md` already exists,
never regenerate it from the template. Read it, walk it unit by unit
(one entity/threat-entry/component), and classify each:
- **unchanged** — no user input needed
- **ADDITION PROPOSED** — show only the new unit's content + a 1-sentence
  reason
- **UPDATE PROPOSED** — show BEFORE/AFTER for only the affected unit

Stop and wait for approval ("approved" / "modify: {text}" / "skip:
{unit}") before saving anything. On approval: merge only the
approved units, bump the version header, append a `## Version History`
row naming the feature that triggered the change, regenerate the
`.summary.md`. This is the same one-approval-at-a-time discipline
`/change` uses for document updates.

Save `.specify/features/{feature}/{doc}.summary.md` (or
`.specify/service/{doc}.summary.md` for the living docs).

Check what remains ungenerated for this scope:
  If more remain → "**{DOC} generated.** Run /specify-doc {next-doc}."
  If none remain → "**{DOC} generated** — all spec documents complete.
  Run /validate."
```

---

## Living Documents — Service-Level, Not Per-Feature

Four documents describe something singular for the whole service, not one
feature — they live at `.specify/service/` instead of
`.specify/features/{feature}/`, are generated once, then
**extended/amended by every later feature**, never regenerated from a
blank template:

| Document | Generated by | Lives at |
|---|---|---|
| Data Model | `/specify-doc data-model` | `.specify/service/data-model.md` |
| Security Design | `/specify-doc security` | `.specify/service/security-design.md` |
| API Design | `/plan-design` §3 (extracted) | `.specify/service/api-spec.md` |
| Component Library (shared frontend components) | `/specify-doc component-spec` | `.specify/service/component-library.md` |

When one of these already exists, the generating command walks it —
SKIP / ADD-unit / UPDATE-unit, showing only the delta, one approval — the
same discipline `/change` already uses for document updates. `design.md`
§3 (per-feature) never contains the full API design; it's a short pointer
to `api-spec.md` plus this feature's new/changed endpoints only. A
feature's own `component-spec.md` never restates a shared component's
full prop/event spec; it points to `component-library.md` and lists only
its own usage.

**Reuse beyond the four living documents:** the Actor Registry (an actor
already defined in another feature's `use-cases.md` is reused by
description, not re-derived — see `/specify-uc` above) and the
architecture shell (Architecture Pattern, Layer Responsibilities,
Cross-Cutting Concerns, and System Context/Container diagrams are
established once by the first feature to reach the PLAN phase, and later
features write "unchanged from {feature}, see there" instead of
re-deriving them — see PLAN Sub-Commands below) follow the same
established-once-reused-after pattern, even though they aren't separate
files under `.specify/service/`.

**Cross-feature impact on change:** because these documents are shared, a
`/change` CR raised against one feature can touch a unit (an endpoint, a
table, a threat entry, a shared component) that a different feature also
depends on. Before approving an UPDATE/RERUN to a living document,
`/change` reads its `## Version History` to see which feature last
touched that unit — if it's a different feature than the one raising the
CR, it surfaces a cross-feature warning as part of the same approval
prompt (advisory, not a hard block — the human reviewer decides whether
the sibling feature needs its own CR). See
`.specify/memory/change-rules.md` → "Living Documents & Cross-Feature
Impact".

---

## /checklist — Spec-Quality Validation (Optional, after GATE-1)

Run this between SRD/extended docs and `/validate` to catch spec quality
issues early — before the business sign-off meeting.

```
Read manifest.yml + constitution.md
Read brd.summary.md + use-cases.summary.md + srd.summary.md
Read checklist-template.md

Checks (in order):
  CRITICAL (block /validate):
    Unresolved [NEEDS CLARIFICATION] markers in brd/srd
    NFR-NNN without numeric threshold
    FR-NNN with no UC-NNN coverage
    UC-NNN missing a Main Path, or with < 1 AP-NNN-X / EP-NNN-X

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

If CRITICAL items: State "Fix CRITICAL items → re-run the affected
/specify-* command → re-run /checklist"
If no CRITICAL: State "Spec quality gate passed — ready for /validate"
```

---

## /validate — Business Sign-Off

```
Read .specify/manifest.yml + constitution.md + roles.yml
Read brd.summary.md + use-cases.summary.md + srd.summary.md
Read validate-template.md

GATE-1 CHECK: constitution Part 2 finalized?
  If not — STOP. State: "GATE-1 open — finalize constitution Part 2
  before /validate."

Produce:
  0. CHECKLIST GATE (advisory) — warn if open CRITICAL CHK-NNN items
     remain from /checklist; does not block.
  1. BUSINESS OBJECTIVE TRACE — every BO-NNN → FR-NNN(s) that address it
     (backend FRs and frontend/UX FRs alike). Flag any BO-NNN with no FR.
  2. BUSINESS REQUIREMENTS REVIEW — every BR-NNN correctly reflected in
     srd.md? Flag mismatches.
  3. ASSUMPTIONS SIGN-OFF — every [ASSUMPTION-NNN] in brd/srd for the
     business owner to confirm or reject.
  3a. NEEDS CLARIFICATION SCAN — scan brd.md, use-cases.md, and srd.md
      for [NEEDS CLARIFICATION] markers; these are BLOCKING — must be
      resolved before sign-off.
  4. SCOPE CONFIRMATION — in-scope / out-of-scope items from brd.md.
  4a. SECURITY DESIGN SIGN-OFF (mvp+ only) — check for a Security
      Officer sign-off marker in security-design.md; if pending, block
      /analyze until it's signed.
  4b. INDICATIVE EFFORT (T-shirt) — size each FR-NNN, indicative only.
  5. SIGN-OFF — Product Owner + Business Analyst (names from roles.yml):
     Approved / Changes Requested.

Save: validate.md + validate.summary.md
Present report. WAIT for sign-off.

If approved:
  State: "VALIDATE complete — ready for /analyze."
Else:
  State: "VALIDATE incomplete — {N} items need changes. Update
  context.md, re-run the affected /specify-* command, re-run /validate."
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
  If not — STOP. State: "ANALYZE blocked — run /validate first
  (business sign-off required)."

Produce:
  RISKS: every integration + flow + NFR (both layers)
    Each: likelihood (L/M/H) + impact (L/M/H/Critical) + mitigation

  DEPENDENCIES: internal + external + timeline
    Each: blocking/non-blocking + owner + risk

  COMPLEXITY: by feature area + by FR
    Each: LOW/MEDIUM/HIGH + reason
    Flag HIGH → these need SPLIT tasks later

  NFR IMPACT: design constraints from NFRs
    Which NFRs force architectural decisions (backend and/or frontend)?

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
Tell agent: "clarify.md answered" (or "best guess" to let the agent
decide every unanswered item)
```

### Step C — Update Spec
```
Read clarify.md with answers
Update affected spec docs → mark: <!-- Clarified: {ID} -->
Regenerate .summary.md for each updated doc
Write clarify.summary.md — all items RESOLVED
State: "CLARIFY complete — ready for PLAN"
```

---

## PLAN Sub-Commands — Architecture, Diagrams, API Design, ADRs

PLAN adapts to your `plan_mode` setting in `manifest.yml` (set during
`setup.sh`, changeable in-session by replying "unified"/"separate" when
prompted).

### Unified mode (`plan_mode: unified`) — one document, one review gate

```
/plan-design → design.md
```
```
Read constitution.md + summary-rules.md
Read clarify.summary.md (MUST exist, all RESOLVED — stop if missing)
Read analyze.summary.md + all spec summaries (brd, use-cases, srd, security)
Read design-template.md

AI-8 GATE CHECK: scan brd.md, use-cases.md, srd.md, and security-design.md
(whichever exist for this scope) for any remaining [ASSUMPTION-NNN]
without a matching <!-- Clarified: {ID} --> note.
  If any remain — STOP. State: "PLAN-DESIGN blocked — unresolved
  assumptions {list}. Run /clarify first."

§1 ARCHITECTURE OVERVIEW:
  Architecture pattern, system layers, and cross-cutting concerns
  describe the WHOLE SERVICE, not this feature — established once by
  the first feature to reach /plan-design, reused by later features
  ("unchanged from {prior-feature}/design.md §1, see there") unless this
  feature genuinely needs a change (shown as a delta, not a restatement).
  DEC-NNN decisions + NFR→decision mapping are always feature-specific.

§2 DIAGRAMS:
  System Context (C4 L1) and Container Diagram (C4 L2) describe the
  service's static topology — same reuse rule as §1. Component Diagram
  (C4 L3), Happy Path Sequence, Error/Failure Paths, and State Machine
  are always fresh and feature-specific.

§3 API DESIGN — see "Living Documents" above:
  Skip for iac/library/desktop-with-no-backend-calls. For frontend-spa/
  mobile-style consumer-only components, write the consumer-view contract
  directly into design.md §3, per-feature — no living file.
  For services that PROVIDE an API: check whether
  .specify/service/api-spec.md exists.
    Not yet → generate fresh, using api-spec-template.md; every endpoint
      complete (request/response schema, all error/status codes),
      traced to FR-NNN/UC-NNN.
    Already exists → walk it endpoint-by-endpoint: unchanged / new
      endpoint / changed endpoint, same BEFORE/AFTER-one-approval
      discipline as /change. On approval: merge, bump version, append
      Version History row naming this feature.
  design.md §3 itself then contains ONLY a pointer to api-spec.md plus
  this feature's new/changed endpoints — never the full API surface.

§4 ARCHITECTURE DECISIONS (ADR): one ADR per DEC-NNN from §1.
  Pilot: minimum 2 ADRs for the most impactful decisions.
  MVP+: one ADR per DEC-NNN.

Diagram self-check (node IDs defined, brackets balanced, participant
names consistent, no empty labels) before saving.

Save: design.md + design.summary.md
```
State: "**design.md generated.** Review, then run **/plan-lld** (mvp+) or
**/task** (pilot)."

### Separate mode (`plan_mode: separate`) — three focused documents

```
Step 1 of 3 — /plan-arch → arch.md
```
Same §1/§3/§6-equivalent reuse rule as unified mode: Architecture
Overview, Layer Responsibilities, and Cross-Cutting Concerns are
established once by the first feature and referenced by later ones
("unchanged from {prior-feature}/arch.md §{N}, see there"); Component
Structure and DEC-NNN decisions are always feature-specific. Gate:
clarify.summary.md all RESOLVED, no unresolved [ASSUMPTION-NNN]. Saves
`arch.md` + `arch.summary.md`. Next: `/plan-hld`.

```
Step 2 of 3 — /plan-hld → hld.md
```
All diagrams in Mermaid, real names only. System Context and Container
Diagram reuse the same established-once rule (redrawn only if this
feature adds a new actor/system/datastore). Happy Path Sequence and State
Machine are always fresh. Gate: `arch.md` approved. Saves `hld.md` +
`hld.summary.md`. Next: `/plan-adr` (mvp+) or `/task` (pilot).

```
Step 3 of 3 — /plan-adr → adr.md  (mvp+ only — skipped at pilot)
```
One ADR per DEC-NNN from `arch.md` §4, plus one per HIGH-risk item from
`analyze.summary.md` not already covered (full scope). Gate: `hld.md`
approved. Saves `adr.md` + `adr.summary.md`. Next: `/plan-lld`.

**API Design in separate mode:** the living `.specify/service/api-spec.md`
extraction happens in unified mode's `/plan-design` §3 only — this pack's
separate-mode chain (`arch.md`→`hld.md`→`adr.md`) does not itself extract
the API surface; consult `plan-design.prompt.md` if your project switches
modes mid-flow.

**Switching modes:** replying "unified" during `/plan-arch`/`/plan-hld`/
`/plan-adr`'s startup prompt (or "separate" during `/plan-design`'s)
updates `manifest.yml → plan_mode` and switches immediately.

---

## /plan-lld — Low Level Design (mvp+ only, both modes)

```
Read constitution.md + summary-rules.md
Unified: read design.summary.md | Separate: read adr.summary.md + hld.summary.md
Read lld-template.md

SCOPE CHECK:
  If scope = pilot → STOP.
  State: "/plan-lld skipped — pilot scope. Proceed to /task."

VERIFY:
  Unified: design.md Status: Approved
  Separate: hld.md AND adr.md (mvp+) Status: Approved

Generate LLD — all diagrams in Mermaid:
  Package/folder structure — full tree (both layers)
  Class diagram (backend) — classDiagram
    Include: fields, key methods, implements/extends
  Component diagram (frontend) — graph TD or classDiagram
    All components + props + events
  Detailed sequence per key flow — sequenceDiagram
    Controller → Service → Port → Adapter (backend)
    Component → Service → API client (frontend)
    Include error handling paths
  ERD (if database) — erDiagram
  Key method signatures — per layer
  DTO/record definitions — backend request/response + frontend types

Save: lld.md + lld.summary.md
State: "PLAN-LLD complete — review lld.md, then run /task"
```

---

## /task — Feature → Story → Task + Jira

```
Read constitution.md + summary-rules.md
Unified: read design.summary.md | Separate: read lld.summary.md (mvp+) or hld.summary.md (pilot)
Read analyze.summary.md + clarify.summary.md + srd.summary.md
  + use-cases.summary.md (for EP-NNN — never skipped)
Read .specify/service/data-model.summary.md and
  .specify/service/api-spec.summary.md if present (living documents —
  entity/endpoint names drive file names)
Read feature-story-template.md + tasks-template.md + jira-export-template.md

Derive Stack Context FIRST from constitution.md Part 2 (Language,
Framework, Testing, Build Tool, Data Store, DB Migration, Orchestration) —
every file name/test/build command in tasks.md comes from these rows,
never hardcoded.

VERIFY: design.md (unified) or lld.md/hld.md (separate) approved. Stop if not.

1. QA TEST CASES:
   Pilot → smoke-tests.md (≤10 cases: one per UC Main Path + EP-NNN)
   MVP+ → qa-testcases.md: one TC-NNN per FR-NNN (happy/validation/auth/
     unhappy/perf categories), one per EP-NNN-X, boundary-value cases for
     numeric FRs, one PERF-NNN task per measurable NFR

2. FEATURE + STORIES:
   Each story: As {actor} I want {X} so that {Y}
   Linked to FR-NNN from SRD; MoSCoW priority; story points: 1/2/3/5/8
   HIGH complexity from analyze.md → higher story points
   Save: stories.md + stories.summary.md

3. TASK LIST:
   Stack Reference table at top, filled from constitution.md
   Phases A (Foundation) → B (Test Doubles) → C (Feature Impl) →
     D (API/Presentation) → E (Integration) → F (Infra) → G (Performance)
   Each task: Story, Satisfies (FR/NFR), Verifies (TC-NNN), Risk (R-NNN),
     estimated lines, PR strategy, files, acceptance criteria
   Auto-split any task > max_lines_per_pr
   Save: tasks.md

4. JIRA CSV:
   Epic → Story → Task hierarchy (or Tasks-only if Epic/Story keys
   already exist in docs/jira/{feature}/keys.yml)
   Save: docs/jira/{feature}/stories.md + docs/jira/{feature}/jira-import.csv

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

VERIFY: tasks.md (and stories.md) approved. Stop if not.

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
  Follow constitution Part 2 tech stack + domain rules (both layers)
  Apply .github/instructions/*.instructions.md for matching files (AI-7)
  Write paired test alongside — never after (or apply manifest's
    testing_style: paired/tdd/bdd)
  No class/component over constitution size limit (backend 200 lines,
    frontend 150 lines)

AFTER CODING:
  List every file changed
  State total lines added
  Confirm each criterion: ✅ {criterion}
  State: "PR ready — {N} lines, {N} files"
  WAIT for "go" before next task

Code Review Gate (per task, if code_review.pre_review: true in
integrations.yml — default): /pre-review [TASK-ID] → sdd pr create →
human review → /address-review [PR-number] if changes requested → merge.

AFTER ALL TASKS:
  Generate delivery per scope:
    openapi   → docs/openapi.yaml
    qa_cases  → docs/qa/functional-test-cases.md (mvp+)
    runbook   → docs/runbook/local-setup.md (mvp+)
  State: "IMPLEMENT complete — all tasks merged. Ready for /release."
```

---

## /release — UAT + Deployment + Go-Live Gate

```
Read constitution.md + roles.yml
Read tasks.md + qa-testcases.summary.md (mvp+) + brd.summary.md
+ srd.summary.md + docs/runbook/local-setup.md (mvp+)
Read release-template.md

VERIFY GATE: every task in tasks.md is "PR ready" and merged.
  If not — STOP. State: "RELEASE blocked — {N} tasks not yet merged."

Produce:
  1. PRE-RELEASE CHECKLIST — all tasks complete + merged, PRs reference
     TASK-NNN/CHG-NNN, backend + frontend test suites green, coverage
     ≥ gate (constitution Part 2), security checklist passed
     (security-design.md §1, +§2 mvp+, covering both server-side and
     client-side controls), traceability complete
  2. UAT PLAN — one row per UC-NNN from use-cases.md: scenario, tester
     role (from roles.yml), environment, result — covering both backend
     (API/data) and frontend (screen/component) scenarios
  3. DEPLOYMENT PLAN — the deployment strategy is standard for this
     service, not re-derived per release. Reference
     docs/runbook/local-setup.md §6 (backend) and §6a (frontend) for the
     standard steps (DB migrations, backend app deploy, frontend build +
     static asset deploy / CDN invalidation, feature flag / traffic
     shift) — fill in only what's specific to THIS release: migration
     version(s), any new feature flag, owner, confirmation the standard
     steps still apply
  4. POST-DEPLOY SMOKE TEST — the checks themselves are standard (pull
     from docs/runbook/local-setup.md); fill in only this release's
     specific happy-path endpoint/screen and NFR target: backend health
     check, key happy-path endpoint, frontend app loads + key screen
     renders, log check, key NFR check
  5. GO-LIVE GATE — Tech Lead / Product Owner / Ops-SRE: Go / No-Go
  6. BUSINESS OBJECTIVE CLOSURE — every BO-NNN: success metric, measured
     result or "measure after N days", met? yes/pending
  7. ROLLBACK PLAN — summary, points to docs/runbook/local-setup.md §6
     (backend) and §6a (frontend) for full detail

Save: release.md + release.summary.md
Present report. WAIT for go-live sign-off (section 5).

If approved:
  State: "RELEASE complete — go-live approved. Proceed with deployment
  plan section 3."
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
Re-read .specify/memory/constitution.md Part 2 — review every row
(Backend, Frontend, and Shared Tech Stack tables, Service NFR Baseline,
Core Principles, Domain Rules, Never Do), resolve [MISSING — ask user]
markers, edit anything wrong.
Tell agent "Constitution Part 2 finalized" to unblock /specify-brd.
```

### Regenerate a Document
```
Discard .specify/features/{feature}/{doc}.md
Re-read template + context
Regenerate → save same path + summary
```
**Living documents are the exception.** Never discard-and-regenerate
`data-model.md`, `security-design.md`, `api-spec.md`, or
`component-library.md` at `.specify/service/` — a wholesale regeneration
destroys every other feature's contributions to that file. Always extend
them via the SKIP / ADD-unit / UPDATE-unit walk described under
"Living Documents" above, even when the request is "just regenerate it."

### Fix Failing Test
```
Failing test: {paste error}
Read failing class/component (backend or frontend). Fix → re-run →
confirm green.
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
Generate newly required /specify-doc {name} documents for the new scope.
Run /plan-lld (now enabled, if upgrading from pilot).
Then update /task with new tasks.
```
