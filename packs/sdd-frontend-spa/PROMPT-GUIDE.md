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
| **GATE-1** | Manual | Manual | You review + finalize constitution Part 2 |
| `/specify-brd` | `/specify-brd` | `/specify-brd` | Business Requirements Document |
| `/specify-uc` | `/specify-uc` | `/specify-uc` | Use Case Specification (Actors + MP/AP/EP) |
| `/specify-srd` | `/specify-srd` | `/specify-srd` | Software Requirements Document |
| `/specify-doc {name}` | `/specify-doc {name}` | `/specify-doc {name}` | One extended doc per run: security, component-spec, ux-flow, data-model, resilience, investigation |
| `/checklist` (optional) | `/checklist` | `/checklist` | Spec-quality validation (CHK-NNN) |
| `/validate` | `/validate` | `/validate` | Business sign-off on BRD/Use Cases/SRD |
| `/analyze` | `/analyze` | `/analyze` | Risks + complexity |
| `/clarify` | `/clarify` | `/clarify` | Questions → you answer |
| `/plan-design` (unified mode) | `/plan-design` | `/plan-design` | Architecture + diagrams + API contribution note + ADRs — one document |
| `/plan-arch` → `/plan-hld` → `/plan-adr` (separate mode) | same | same | Same content as `/plan-design`, split into three reviewed-individually documents |
| `/plan-lld` | `/plan-lld` | `/plan-lld` | LLD — class/sequence diagrams (mvp+ only) |
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
command, including `create-context.md`, `start.md`, `specify.md`,
`specify-brd.md`, `specify-uc.md`, `specify-srd.md`, `specify-doc.md`,
`checklist.md`, `validate.md`, `analyze.md`, `clarify.md`, `plan-design.md`,
`plan-arch.md`, `plan-hld.md`, `plan-adr.md`, `plan-lld.md`, `task.md`,
`implement.md`, `release.md` (plus team-member and utility commands such as
`maya.md`, `change.md`, `pre-review.md`). Claude Code auto-discovers these —
nothing to install or configure.

- Type `/start` at the beginning of every session — equivalent to STEP 0
  below (reads CLAUDE.md, manifest, constitution, summary-rules,
  change-rules, roles.yml, instructions).
- Type `/specify` to generate constitution Part 2 only, then — after
  GATE-1 — `/specify-brd`, `/specify-uc`, `/specify-srd`, and
  `/specify-doc {name}` (once per extended document) to generate the spec
  documents one at a time.
- Type `/checklist`, `/validate`, `/analyze`, `/clarify` to run each gate.
- Type `/plan-design` in unified mode, or `/plan-arch` → `/plan-hld` →
  `/plan-adr` in separate mode (see "PLAN Sub-Commands" below), then
  `/plan-lld` (mvp+).
- Type `/task`, `/release` to run each command — Claude reads the matching
  `.github/prompts/<name>.prompt.md` and executes it.
- `/implement TASK-NNN` passes the task ID through to the implement prompt.
- `/specify-doc {name}` passes the document name through (e.g.
  `/specify-doc data-model`) — same pattern.
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
2. **Feature Size Check (Step 1.5):** before drafting, checks whether the
   pasted notes actually describe 2+ independently-shippable features
   (barely-overlapping actor sets, clusters usable/testable on their own,
   epic-style "and also" language). If only one feature is found, this
   step is silent. If 2+ are found, the agent STOPS and asks whether to
   build them as "one feature" (proceed with everything) or split and
   build one at a time — reserved clusters have their raw notes saved to
   `.specify/contexts/{other-slug}.raw.md` for a later `/create-context`
   run, never discarded.
3. Fills in what it can infer, marks the rest `[MISSING — ask user]`; for
   Endpoints/NFRs specifically, proposes a scope-appropriate
   `(SUGGESTED DEFAULT — edit or confirm)` starting point instead of a
   blank.
4. Gives you a plain-language "Missing Information" checklist, split into
   Group A (confirm/edit suggested defaults) and Group B (still need your
   input).
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
/validate.
```

---

## Document Inventory by Scope/Command (canonical — single source of truth)

| Command | Pilot | MVP | Full |
|---|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) only — all scopes |||
| GATE-1 (manual) | constitution Part 2 finalized — all scopes |||
| `/specify-brd` | brd.md — all scopes |||
| `/specify-uc` | use-cases.md — all scopes |||
| `/specify-srd` | srd.md (+ security-design.md §1, via SRD) | same | same |
| `/specify-doc security` | — (§1 already covered in SRD) | security-design.md §1-2 (living, `.specify/service/`) | security-design.md §1-4 (living, `.specify/service/`) |
| `/specify-doc component-spec` | — | component-spec.md (+ living "Shared Components Used" → `.specify/service/component-library.md`) | same |
| `/specify-doc ux-flow` | — | ux-flow.md | ux-flow.md |
| `/specify-doc data-model` | — | data-model.md — Frontend State & Storage Model (living, `.specify/service/data-model.md`) | same |
| `/specify-doc resilience` | — | — | resilience.md |
| `/specify-doc investigation` | — | — | investigation.md |
| API contract (consumer view) | design.md §3, per-feature (**not** a `/specify-doc` output, **not** living) — all scopes |||
| `/checklist` | Optional | Mandatory | Mandatory |
| `/validate` | validate.md — all scopes |||
| `/analyze` | analyze.md — all scopes |||
| `/clarify` | clarify.md — all scopes |||
| `/plan-design` (unified) or `/plan-arch`→`/plan-hld`→`/plan-adr` (separate) | design.md, or arch.md+hld.md (ADRs skipped) | + ADRs (adr.md or design.md §4) | same as mvp |
| `/plan-lld` | skip | lld.md | lld.md |
| `/task` | stories.md, tasks.md, jira — all scopes |||
| `/implement` | code + paired tests | + qa_cases, runbook (`docs/runbook/local-setup.md`) | + qa_cases, runbook |
| `/release` | release.md — all scopes |||

If any other document in this pack lists a different mapping, this table
wins — fix the other document.

**Notes:**
- `data-model` and `security-design` are **living, app-level** documents at
  `.specify/service/` — available from **mvp scope up** (mvp and full),
  not full-only. They are generated once by the first feature that needs
  them and extended (never regenerated) by every later feature.
- `component-library.md` (`.specify/service/component-library.md`) is a
  third living document — it catalogs shared/reusable UI components. It is
  populated as a side effect of `/specify-doc component-spec` whenever a
  feature introduces a component meant to be reused by others.
- This pack only **consumes** an API (it does not provide one) — the API
  contract lives per-feature inside `design.md` §3, following the shape of
  `api-spec-template.md`'s "Backend API Contract (Consumer)" structure. It
  is never a `/specify` or `/specify-doc` output and never lives at
  `.specify/service/`.

---

## SPECIFY — Five Sub-Commands

`/specify` generates the constitution only. Spec documents are generated
**one at a time** using dedicated sub-commands — same pattern as the PLAN
sub-commands.

| Command | What it generates | Gate |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) | — |
| `/specify-brd` | Business Requirements Document | GATE-1 passed |
| `/specify-uc` | Use Case Specification (Actors + UC-NNN with MP/AP/EP) | BRD approved |
| `/specify-srd` | Software Requirements Document | Use Cases approved |
| `/specify-doc {name}` | Any extended doc — `security`, `component-spec`, `ux-flow`, `data-model`, `resilience`, `investigation` | SRD approved |

### `/specify` — Constitution Part 2 Only

```
Read .specify/manifest.yml
Read .specify/memory/constitution.md + summary-rules.md
Read .specify/contexts/{manifest.project.context_file}

Generate constitution.md Part 2 (DRAFT):
  Fill Tech Stack table (Language, Framework, Build Tool, State
  Management, Component Library/Design System, Routing, API Client,
  Bundler, Data Cache, Configuration, Secrets, Resilience, Observability,
  Logging, Testing, Coverage Gate, Linting/Formatting, Accessibility,
  CI/CD, Hosting/CDN)

  If concern not in context → use sensible default
  If critical concern missing → mark [MISSING — ask user]

  App NFR Baseline — extract from context.md's NFR section if stated
  (Load Time, Bundle Size, Interactivity, Accessibility). If not stated,
  leave [MISSING — ask user]: the first feature's /specify-srd run fills
  it retroactively once its own NFR-NNN rows are approved — never
  regenerate this row from a later feature's numbers without an explicit
  Constitution Amendment.

  Core Principles → derive from domain (Component-First, Accessible,
    Performant + Specification First, Test Discipline, Traceability)
  Domain Rules → extract from UX/business rules in context
  Never Do → extract from constraints + add: API calls in components,
    inline styles, console.log in prod, any type

  Save constitution.md (Part 1 unchanged, Part 2 is a DRAFT)
  State: "Constitution Part 2 generated — DRAFT. Review and finalize
  every row (GATE-1), then run /specify-brd."
```

Do NOT proceed to spec documents in the same turn as a first-time
generation unless the user has already reviewed Part 2. A later `/specify`
re-run on an already-finalized Part 2 must propose changes for review —
never silently overwrite finalized rows.

### `/specify-brd` → `brd.md` — gate: GATE-1 passed

Generates the Business Requirements Document (BG-NNN business goals,
measurable NFR-NNN targets, §3 Stakeholders filled from `roles.yml` with
ACT-ID cells left for `/specify-uc` to back-fill). Stakeholder review
(Confluence draft + Jira submit, or chat approval), then Progressive Jira
Epic export. Ends: "Run **/specify-uc** to generate the Use Case
Specification."

### `/specify-uc` → `use-cases.md` — gate: BRD approved

Generates Actors (ACT-NNN) and Use Cases (UC-NNN) with Main Path,
Alternate Paths (≥1), and Exception Paths (≥1) per UC.

**Actor Registry reuse:** before deriving an actor from scratch, checks
whether it already appears in another feature's `use-cases.md` in this
service (same real-world role). If so, reuses its Name/Type/Description
verbatim instead of re-deriving it, noting "(same as {prior-feature}'s
ACT-NNN)" — the ACT-NNN identifier itself is still assigned locally to
this feature's own file.

Back-fills BRD §3 Stakeholders with the newly assigned ACT-NNN values.
Ends: "Run **/specify-srd** to continue."

### `/specify-srd` → `srd.md` — gate: Use Cases approved

Generates FR-NNN (traced to UC-NNN) and NFR-NNN (refining BRD NFRs with
technical targets).

**App NFR Baseline mechanism:** reads constitution.md's NFR Baseline
row(s). If still `[MISSING — ask user]` (this is the first feature to
reach `/specify-srd`), derives the baseline categories from this feature's
own NFRs and fills the constitution row — `srd.md` §3 states "Establishes
the NFR baseline — see constitution.md." If already filled (a later
feature), `srd.md` §3 states "Baseline (constitution.md → NFR Baseline):
{values} — applies to this feature too, no change" and only adds its own
NFR-NNN row for something genuinely different from the baseline — never
restates the baseline numbers as freshly derived. A stricter/different
baseline requirement is a Constitution Amendment, not a silent overwrite.

Back-fills `use-cases.md` with FR-NNN trace links. Ends: "Run
**/specify-doc {next-doc}**" — the next document is determined from the
Document Inventory table above.

### `/specify-doc {name}` — gate: SRD approved

One document per invocation — `security`, `component-spec`, `ux-flow`,
`data-model`, `resilience`, `investigation`. **`api-spec` is not a valid
argument here** — this pack's API contract is written per-feature into
`design.md` §3 during `/plan-design` (consumer view), not generated by
`/specify-doc`.

**Living/app-level documents — extended, never regenerated:**

| Document | Lives at | Mechanism |
|---|---|---|
| `data-model` (Frontend State & Storage Model) | `.specify/service/data-model.md` | SKIP / ADD-unit / UPDATE-unit walk |
| `security` (security-design.md) | `.specify/service/security-design.md` | SKIP / ADD-unit / UPDATE-unit walk |
| `component-spec`'s "Shared Components Used" section | `.specify/service/component-library.md` | SKIP / ADD-unit / UPDATE-unit walk, per shared component |

For these, `/specify-doc` first checks whether the file already exists.
**If not** (first feature in the service to need it): generates it fresh
and states it is now the service's living reference. **If it already
exists:** reads the full current file, walks it one logical unit at a
time (one entity, one threat entry, one shared component), and classifies
each as **no change needed** / **new addition** (show only the proposed
new unit) / **modification** (show BEFORE/AFTER for only that unit) — the
same before/after, one-approval discipline `/change` uses. Never discards
or regenerates the whole file from a blank template — that would destroy
other features' contributions. On approval: merges the delta, bumps the
version header, appends a `## Version History` row naming this feature,
regenerates the `.summary.md`.

The rest of `component-spec.md` (this feature's own component hierarchy)
stays per-feature as normal, at `.specify/features/{feature}/component-spec.md`.

**Every other extended doc** (`ux-flow`, `resilience`, `investigation`,
and the per-feature parts of `component-spec`) stays per-feature:
`.specify/features/{feature}/{doc}.md` + `.summary.md`.

**For `security` specifically:** scope-based sections (pilot §1 only,
mvp §1-2 + OWASP/STRIDE, full §1-4 + DAST/pentest scope), STRIDE threat
enumeration with DREAD scoring, sign-off marker inserted above Approvals.

Stakeholder review (Confluence + Jira, or chat). Ends: "Run
**/specify-doc {next-doc}**" until none remain, then: "Run **/validate**
for business sign-off."

---

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)

```
Open .specify/memory/constitution.md → Part 2 (DRAFT from /specify)

Review every row:
  - Tech Stack (Framework, State Management, Routing, API Client,
    Accessibility, Hosting/CDN, and remaining concerns)
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

## /checklist — Spec-Quality Validation (Optional for pilot, Mandatory for mvp+, after all `/specify-doc` runs)

Run this between the last `/specify-doc` and `/validate` to catch spec
quality issues early — before the business sign-off meeting.

```
Read manifest.yml + constitution.md
Read brd.summary.md + use-cases.summary.md + srd.summary.md
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

If CRITICAL items: State "Fix CRITICAL items → re-run affected /specify-*
command → re-run /checklist"
If no CRITICAL: State "Spec quality gate passed — ready for /validate"
```

---

## /validate — Business Sign-Off (runs after GATE-1 + all spec docs approved)

```
Read .specify/manifest.yml + constitution.md + roles.yml
Read brd.summary.md + use-cases.summary.md + srd.summary.md
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
  State: "VALIDATE incomplete — {N} items need changes. Update the
  relevant spec doc(s), re-run /validate."
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
State: "CLARIFY complete — ready for PLAN"
```

---

## PLAN Sub-Commands

PLAN adapts to your `plan_mode` setting in `manifest.yml` (set during
`setup.sh`, switchable in-session by replying "unified"/"separate" when
prompted).

### Unified mode (`plan_mode: unified`, default) — one document, one review gate

**`/plan-design`** → `design.md`: Architecture Overview + Diagrams + API
Design (§3) + Architecture Decisions (§4, ADRs), all in one file.

- **Gate:** `clarify.summary.md` exists, all RESOLVED; no unresolved
  `[ASSUMPTION-NNN]` across brd/use-cases/srd/security-design (AI-8)
- **§1 Architecture Overview & §2 System Context/Container diagrams:**
  established once by the first feature to reach `/plan-design` and
  **reused** by later features — write "unchanged from
  {prior-feature}/design.md §1/§2, see there" instead of re-deriving,
  unless this feature genuinely adds something (new layer, new external
  system) — show only that delta. DEC-NNN decisions and the rest of §2's
  diagrams (component diagram, sequence, state machine) are always
  feature-specific.
- **§3 API Design:** for this pack (consumer-only), the API contract this
  feature consumes is written **directly into `design.md` §3, per-feature**
  — using `api-spec-template.md`'s "Backend API Contract (Consumer)"
  structure. This is **not** a living document and is **not**
  `.specify/service/api-spec.md` — that living-doc treatment applies only
  to services that *provide* an API (backend-service, fullstack backend,
  universal), not to this pack.
- **§4 ADRs:** one per DEC-NNN from §1; pilot scope needs a minimum of 2.
- Review: tech lead + architect + stakeholders
- Scope: all scopes (pilot, mvp, full) — pilot skips nothing in §1-4, only
  `/plan-lld` afterward is skipped

### Separate mode (`plan_mode: separate`) — three focused documents, reviewed individually

- **`/plan-arch`** → `arch.md`: Architecture pattern, layers, cross-cutting
  concerns, key decisions (DEC-NNN), NFR→decision mapping — Step 1 of 3
  - Gate: `clarify.summary.md` exists, all RESOLVED; no unresolved
    `[ASSUMPTION-NNN]` (AI-8)
  - §1 pattern/layers/§3 layer table/§6 cross-cutting concerns: reused
    from a prior feature's approved `arch.md` if one exists, same
    unchanged/delta rule as unified mode's §1
- **`/plan-hld`** → `hld.md`: System diagrams — C4 context, container,
  happy-path sequence, state machine — Step 2 of 3
  - Gate: `arch.md` approved
  - Diagrams 1-2 (System Context, Container): reused from a prior
    feature's `hld.md` if unchanged, same rule as above
- **`/plan-adr`** → `adr.md`: Architecture Decision Records, one per
  DEC-NNN from `arch.md` §4 — Step 3 of 3 (mvp+ only; **skipped at pilot**
  — pilot's ADRs live inside `arch.md` §4 itself, no separate file)
  - Gate: `hld.md` approved

> Note: this pack's API contract (consumer view) is written into
> `design.md` §3 only in **unified** mode. In **separate** mode there is no
> dedicated API document either — the per-feature consumer contract is
> still authored alongside the design work (see `plan-design.prompt.md`'s
> consumer-view branch); `arch.md`/`hld.md`/`adr.md` cover architecture,
> diagrams, and decisions only.

### Both modes

- **`/plan-lld`** → `lld.md`: Detailed technical design — folder/module
  structure, component/class diagrams, per-flow sequence diagrams
  (including error/retry paths), prop/interface signatures (mvp+ only;
  SKIP if pilot)
  - Unified gate: `design.md` approved
  - Separate gate: `adr.md` approved (mvp+) — pilot scope also skips
    `/plan-lld` entirely, going straight to `/task` after `hld.md`

### Diagram Self-Check (all diagram-producing commands)

Before saving, verify every Mermaid diagram: every node ID used in an edge
is defined; parentheses/brackets/braces are balanced; sequence participant
names are consistent; no empty node labels. Fix any error found before
saving, then state "Diagram self-check passed — {N} diagrams verified."

---

## /task — Feature → Story → Task + Jira

```
Read constitution.md + summary-rules.md
Read plan.summary.md (or design.summary.md/arch.summary.md) + analyze.summary.md + clarify.summary.md
Read feature-story-template.md + tasks-template.md + jira-export-template.md
Read qa-testcases.summary.md (mvp+, if already generated)

VERIFY: design.md (unified) or adr.md/hld.md (separate, per scope) exists
and reviewed. Stop if not.

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
  No component over constitution size limit
  Run axe-core accessibility check for every new/changed component

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
    runbook   → docs/runbook/local-setup.md (mvp+, living/continuity
                artifact — reused by /release, not re-derived per release)
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
  1. PRE-RELEASE CHECKLIST — tasks merged, PRs reference TASK-NNN/CHG-NNN,
     tests green, coverage ≥ gate, accessibility checks passed,
     security checklist passed (security-design.md §1, +§2 mvp+),
     traceability complete
  2. UAT PLAN — one row per UC-NNN from srd.md/use-cases.md: scenario,
     tester (from roles.yml), environment/browser-matrix, result
  3. DEPLOYMENT PLAN — the deploy strategy and rollback steps are
     standard for this app, not re-derived per release: pulled from
     docs/runbook/local-setup.md (living/continuity document, established
     once) and constitution.md's Hosting/CDN row. States "Standard deploy
     — see docs/runbook/local-setup.md §{N}" and fills in only what's
     specific to this release (new feature flag(s), owner, confirmation
     the standard steps still apply, or what's different this time)
  4. POST-DEPLOY SMOKE TEST — the checks themselves are standard, pulled
     from docs/runbook/local-setup.md; fills in only this release's
     specific happy-path screen flow and NFR target (app loads, key
     route renders, key API call succeeds, Core Web Vitals within budget,
     error-tracking SDK live)
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
```
Discard .specify/features/{feature}/{doc}.md
Re-read template + context
Regenerate → save same path + summary
```

> **Living documents are the exception.** `data-model.md`,
> `security-design.md`, and `component-library.md` at `.specify/service/`
> must **never** be discarded or regenerated wholesale — doing so destroys
> every other feature's contribution to that shared file. To fix or extend
> one of these, re-run the owning command (`/specify-doc data-model`,
> `/specify-doc security`, or `/specify-doc component-spec`) and go through
> its SKIP / ADD-unit / UPDATE-unit walk instead, or raise a `/change` CR
> if the edit originates from a change request.

### Fix Failing Test
```
Failing test: {paste error}
Read failing class/component. Fix → re-run → confirm green.
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
Run sdd review status to see newly required documents.
Generate newly required /specify-doc {name} docs (data-model,
resilience, etc. — living docs extend via their SKIP/ADD-unit/
UPDATE-unit walk, not regeneration).
Run /plan-lld if upgrading from pilot (now enabled).
Then update /task with new tasks.
```
