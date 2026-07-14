# SDD Prompt Guide — Universal Pack
# Works with any project type · Claude Code · Copilot · Cursor · Windsurf · Any AI

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
| `/specify` | `/specify` | `/specify` | Resolve project_type + Constitution Part 2 (DRAFT) only |
| — GATE-1 — | Manual | Manual | You review + finalize constitution Part 2 |
| `/specify-brd` | `/specify-brd` | `/specify-brd` | Business Requirements Document |
| `/specify-uc` | `/specify-uc` | `/specify-uc` | Use Case Specification (Actors + UC-NNN with MP/AP/EP) |
| `/specify-srd` | `/specify-srd` | `/specify-srd` | Software Requirements Document |
| `/specify-doc {name}` | `/specify-doc {name}` | `/specify-doc {name}` | One extended doc at a time (varies by project_type — never `api-spec`) |
| `/checklist` (optional pilot / mandatory mvp+) | `/checklist` | `/checklist` | Spec-quality validation (CHK-NNN) |
| `/validate` | `/validate` | `/validate` | Business sign-off on BRD/Use Cases/SRD |
| `/analyze` | `/analyze` | `/analyze` | Risks + complexity |
| `/clarify` | `/clarify` | `/clarify` | Questions → you answer |
| `/plan-design` (unified) — or — `/plan-arch`→`/plan-hld`→`/plan-adr` (separate) | same | same | Architecture + Diagrams + API Design + ADRs |
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

**First time?** Run `bash setup.sh` (Mac/Linux) or `.\setup.ps1` (Windows) — auto-detects project type and fills manifest.yml. See [QUICKSTART.md](QUICKSTART.md).

---

## Supported Project Types

`setup.sh` detects your type from project files. Override with `--type <type>` or set `project_type` in manifest.yml. `/specify` re-detects the same way if `project_type: auto` at that point (same order — mobile checked before fullstack in setup.sh, setup.ps1, and specify.prompt.md Step 0, always kept in sync).

| Type | When to use | Auto-detected from |
|---|---|---|
| `backend-service` | REST APIs, microservices, gRPC | `pom.xml`, `build.gradle`, `go.mod`, `requirements.txt` |
| `frontend-spa` | React, Vue, Angular, Svelte web apps | `package.json` with react/vue/angular/svelte |
| `mobile` | React Native, Flutter, Expo | `package.json` with react-native/expo, `pubspec.yaml` |
| `fullstack` | Backend + Frontend in one repo | Both backend + frontend files present |
| `cli` | Command-line tools | `Cargo.toml` [[bin]], `go.mod` + `cmd/`, Click/Cobra/clap usage |
| `data-ml` | ML models, data pipelines, notebooks | `requirements.txt` with pandas/torch/sklearn/tensorflow |
| `serverless` | AWS Lambda, Cloud Functions, SAM | `serverless.yml`, `template.yaml` with AWSTemplateFormatVersion |
| `library` | npm/PyPI/Maven packages, SDKs | `setup.py` with install_requires, library-only structure |
| `iac` | Terraform, Pulumi, CDK, CloudFormation | `.tf` files, `Pulumi.yaml`, `cdk.json` |
| `desktop` | Electron, Tauri, native desktop | `package.json` with electron, `tauri.conf.json` |

Not sure? Leave `project_type: auto` in manifest.yml — `/specify` detects it automatically.

> **Non-interactive project types** (`cli`, `data-ml`, `serverless`, `library`, `iac`): `/specify-uc` still runs, but produces a simplified Use Case Specification — system actors only (ACT-NNN type = System or Operator), Main Path describing the data/command flow rather than user interaction, Exception Paths covering failure modes (timeout, data error, partial run). Don't force a UI-centric template onto these types.

---

## Claude Code Native Slash Commands (setup, once)

This pack ships a `.claude/commands/` directory with one Markdown file per
command: `create-context.md`, `start.md`, `specify.md`, `specify-brd.md`,
`specify-uc.md`, `specify-srd.md`, `specify-doc.md`, `checklist.md`,
`validate.md`, `analyze.md`, `clarify.md`, `plan-design.md`, `plan-arch.md`,
`plan-hld.md`, `plan-adr.md`, `plan-lld.md`, `task.md`, `implement.md`,
`release.md` (plus the virtual-team and utility commands — `change.md`,
`orchestrate.md`, `jira-push.md`, `pre-review.md`, `address-review.md`,
and the named-teammate commands `maya.md`/`rex.md`/`ava.md`/`leo.md`/
`kai.md`/`quinn.md`/`riley.md`/`morgan.md`). Claude Code auto-discovers
these — nothing to install or configure.

- Type `/start` at the beginning of every session — equivalent to STEP 0
  below (reads CLAUDE.md, manifest, constitution, summary-rules,
  change-rules, roles.yml, instructions).
- Type `/specify`, `/specify-brd`, `/specify-uc`, `/specify-srd`,
  `/specify-doc {name}`, `/validate`, `/analyze`, `/clarify`,
  `/plan-design` (or `/plan-arch` / `/plan-hld` / `/plan-adr`), `/plan-lld`,
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
   independently-shippable features (clusters that don't block each other,
   barely-overlapping actor sets, separate resource domains, epic-style
   language). If only one cluster is found, this step is silent. If 2+ are
   found, it stops and asks whether to build them "all" as one feature or
   pick one to build first — the other cluster(s)' raw notes are saved to
   `.specify/contexts/{other-slug}.raw.md` for a later `/create-context`
   run, never silently merged into one oversized context.
3. Fills in what it can infer, marks the rest `[MISSING — ask user]`.
4. Gives you a plain-language "Missing Information" checklist.
5. You answer what you can — "not sure" is fine for technical questions
   (the architect decides later at /plan-design).
6. Repeat until you say "good enough, proceed" or nothing is missing.
7. Saves `.specify/contexts/{feature}.md` — the file /specify reads.

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
  Constitution Part 2: generated? yes/no
  Constitution Part 2 finalized (GATE-1)? yes/no
  project_type: resolved? yes/no (auto/missing blocks everything until /specify resolves it)
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
| `/specify` | project_type resolved + constitution Part 2 (DRAFT) — all scopes |||
| GATE-1 (manual) | constitution Part 2 finalized — all scopes |||
| `/specify-brd` | brd.md — all scopes |||
| `/specify-uc` | use-cases.md — all scopes |||
| `/specify-srd` | srd.md + security-design §1 (Threat Assessment) — all scopes |||
| `/specify-doc {name}` | none required | `security` (§1–2) + this project_type's mvp+ extended docs (e.g. `data-model` for backend-service/fullstack/data-ml; `component-spec`/`ux-flow` for frontend-spa/fullstack; `ux-flow`/`screen-spec` for mobile) | + `security` (§1–4) + `resilience` + `investigation` (all types) |
| `/checklist` | Optional | **Mandatory** | **Mandatory** |
| `/validate` | validate.md — all scopes |||
| `/analyze` | analyze.md — all scopes |||
| `/clarify` | clarify.md — all scopes |||
| PLAN — unified: `/plan-design` / separate: `/plan-arch`→`/plan-hld`→`/plan-adr` | design.md (or arch.md + hld.md; ADRs skipped) + API Design §3 | same + ADRs (separate mode `/plan-adr`) | same as mvp |
| `/plan-lld` | skip | lld.md | lld.md |
| `/task` | stories.md, tasks.md, jira, smoke-tests.md (≤10 cases) | + qa-testcases.md (supersedes smoke-tests.md) | + qa-testcases.md |
| `/implement` | code + paired tests | + qa results, runbook | + qa results, runbook, openapi.yaml |
| `/release` | release.md — all scopes |||

> **`api-spec` is never a `/specify-doc` target.** For project_types that
> **provide** an API (backend-service, fullstack backend, serverless), the
> API surface is extracted during `/plan-design` §3 into the **living**
> `.specify/service/api-spec.md` (mvp+ — shared across every feature,
> extended via SKIP/ADD-unit/UPDATE-unit, never regenerated from scratch).
> For project_types that only **consume** an API (frontend-spa, mobile), it
> stays per-feature inside `design.md` §3 instead — not living at all.
> `data-model` and `security-design` are also **living, service-level**
> documents at `.specify/service/` (not per-feature) for every project_type
> that generates them — same walk-and-diff discipline as `api-spec.md`.

If any other document in this pack lists a different mapping, this table
wins — fix the other document.

---

## Living Documents — Service-Level, Not Per-Feature

Some documents describe something singular for the whole service, not one
feature — they live at `.specify/service/` instead of
`.specify/features/{feature}/`, are generated once by the first feature
that needs them, and are **extended/amended by every later feature**,
never regenerated from a blank template:

| Document | Generated by | Lives at | Applies to |
|---|---|---|---|
| Data Model | `/specify-doc data-model` | `.specify/service/data-model.md` | backend-service, fullstack, data-ml (mvp+) — or this project_type's equivalent state/storage model |
| Security Design | `/specify-doc security` | `.specify/service/security-design.md` | all project_types, all scopes (§1 always; §1–2 mvp; §1–4 full) |
| API Design | `/plan-design` §3 (extracted, not `/specify-doc`) | `.specify/service/api-spec.md` | project_types that **provide** an API (backend-service, fullstack backend, serverless) — mvp+ |

When one of these already exists, the generating command walks it one
logical unit at a time — **SKIP** (unchanged) / **ADD-unit** (new entity,
endpoint, or threat entry) / **UPDATE-unit** (BEFORE/AFTER for one unit) —
showing only the delta, one approval, never the whole file. This is the
same discipline `/change` already uses for document updates. `design.md`
§3 (per-feature) never contains the full API design when it's living; it's
a short pointer to `api-spec.md` plus this feature's new/changed endpoints
only. Architecture Pattern, Layer Responsibilities, Cross-Cutting Concerns,
and the System Context/Container diagrams follow the same "established
once by the first feature, referenced by later features" rule inside
`/plan-design` (or `/plan-arch` + `/plan-hld` in separate mode) — see
"PLAN Sub-Commands" below.

An actor already defined in another feature's `use-cases.md` (same
real-world role) is reused — Name/Type/Description copied verbatim with a
"(same as {prior-feature}'s ACT-NNN)" note — rather than re-derived from
scratch, though the ACT-NNN identifier itself stays local to each
feature's own `use-cases.md`.

**Service NFR Baseline:** `constitution.md` Part 2 carries a Performance /
Availability / Throughput / Data Retention table. It's left
`[MISSING — ask user]` at `/specify` time and filled retroactively by the
**first** feature to reach `/specify-srd`, using that feature's own
NFR-NNN rows. Every later feature's `srd.md` references this baseline
("applies to this feature too, no change") instead of restating the
numbers, and only adds its own NFR-NNN row for something genuinely
stricter or new. Marked N/A for project_types with no runtime service
(library, cli, iac).

---

## /specify — Resolve project_type + Constitution Part 2 (only)

`/specify` generates **only** the constitution — it no longer generates
brd/srd/security-design/api-spec/data-model in one shot. Spec documents
are generated **one at a time** afterward using dedicated sub-commands
(`/specify-brd` → `/specify-uc` → `/specify-srd` → `/specify-doc {name}`),
same pattern as the `/plan-*` sub-commands.

```
Read .specify/manifest.yml
Read .specify/memory/constitution.md + summary-rules.md
Read .specify/contexts/{manifest.project.context_file}

STEP 0 — RESOLVE PROJECT TYPE:
  Read project_type from manifest.yml.
  If "auto" or missing → detect from root files, same order as
  setup.sh/setup.ps1 (mobile checked before fullstack). If still
  ambiguous, ask the user to choose from the 10 supported types.
  State: "Detected project type: {type}." Update manifest.yml.

ACTION 1 — Generate constitution.md Part 2 (DRAFT):
  Fill the Tech Stack table using the row set defined for the resolved
  project_type (backend-service / frontend-spa / mobile / fullstack
  [Backend + Frontend + Shared] / cli / data-ml / serverless / library /
  iac / desktop — each has its own concern list, see specify.prompt.md)

  If concern not in context → sensible default
  If critical concern missing → mark [MISSING — ask user]

  Service NFR Baseline (Performance/Availability/Throughput/Data
  Retention) → fill from context if stated, else [MISSING — ask user]
  (see "Living Documents" above); N/A for library/cli/iac.

  Core Principles → derive from domain
  Domain Rules → extract from business rules section
  Never Do → extract from constraints section + universal defaults

  Set/bump Part 2 version line:
    First run: Version v1.0 | Last Amended: {date} | Amended By: initial /specify
    Re-run (finalized Part 2): bump v{X.Y} → v{X.Y+1}, Amended By:
    CHG-NNN (or "manual /specify re-run")

  Save constitution.md (Part 1 unchanged, Part 2 = DRAFT)
  List remaining [MISSING — ask user] rows as "Open Items for GATE-1"
  ({N} items) — or "No open items — ready for GATE-1 review"

State: "Constitution Part 2 generated — DRAFT. Review and finalize
every row (GATE-1), then run /specify-brd."
```

A later `/specify` re-run on an already-finalized Part 2 must propose a
Constitution Amendment Summary (row diffs + version bump, cross-referenced
against change-rules.md's Change Impact Matrix) and WAIT for confirmation
— never silently overwrite a finalized Part 2.

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

```
Open .specify/memory/constitution.md → Part 2 (DRAFT from /specify)

Review every row:
  - Tech Stack (per project_type)
  - Service NFR Baseline (or confirm N/A)
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

Gate: GATE-1 passed (constitution.md Part 2 must NOT contain `DRAFT` in
its version line).

```
Read .specify/manifest.yml + constitution.md + roles.yml
Read .specify/contexts/{manifest.project.context_file}
Read .specify/templates/brd-template.md

Generate brd.md:
  §3 Stakeholders — fill Name/Team from roles.yml; leave ACT-ID column
    "_(set by /specify-uc)_" until actors are assigned
  Every business objective: BO-NNN
  Every business requirement: BR-NNN
  Every NFR: NFR-NNN with a measurable target (e.g. "< 200ms p99")
  Marker discipline:
    [ASSUMPTION-NNN: {what}] → safe default applied; needs sign-off
    [NEEDS CLARIFICATION: {question}] → no safe default; blocks /validate
    Never leave a gap silently

Save: brd.md + brd.summary.md
```

Review/approval: Confluence draft (if configured) → stakeholder comments →
Jira submission (if configured) → any approval signal in chat flips
`Status: Draft` → `Approved`, fills the Approvals table, appends Version
History, and records the approval (`sdd review approve --doc brd`).

After approval, an Epic definition (`docs/jira/{feature}/epic.md`) is generated for
progressive Jira export (see Document Review Gates below).

State: "BRD generated. Review, then run **/specify-uc**." — do not
generate any other document in the same turn.

---

## /specify-uc — Use Case Specification

Gate: `brd.md` approved.

```
Read brd.summary.md (or brd.md) + use-cases-template.md

Generate use-cases.md:
  Every actor: ACT-NNN (Primary / Secondary / System)
    Before deriving an actor from scratch, check whether it already
    appears in another feature's use-cases.md in this service (same
    real-world role) — reuse its Name/Type/Description verbatim with a
    "(same as {prior-feature}'s ACT-NNN)" note, rather than re-deriving it.
    ACT-NNN numbering itself stays local to this feature.
  Every use case: UC-NNN — Trigger, Preconditions, Postconditions
    (Success/Failure), Main Path (MP), ≥1 Alternate Path (AP-NNN-X),
    ≥1 Exception Path (EP-NNN-X), Business Rules Applied, Linked FR-NNN
    (left "_(filled by /specify-srd)_" for now)
  §4 Relationships — Mermaid graph LR of includes/extends
  §5 Traceability — UC-NNN → BR-NNN

Back-fill brd.md §3 Stakeholders ACT-ID column now that actors exist.

Save: use-cases.md + use-cases.summary.md
```

Same Confluence/Jira review-and-approval flow as BRD. After approval, a
draft Story definition (`docs/jira/{feature}/stories-draft.md`) is written — one
entry per UC-NNN — for progressive Jira export.

State: "Use Cases generated. Review, then run **/specify-srd**." — stop,
do not generate any further document this turn.

---

## /specify-srd — Software Requirements Document

Gate: `use-cases.md` approved (implies BRD already approved).

```
Read use-cases.summary.md + brd.summary.md + srd-template.md

Generate srd.md:
  Every FR-NNN traces to a UC-NNN (Main/Alternate/Exception Path steps
  each become their own FR-NNN — happy path, variant, error handling)
  NFRs refine BRD NFRs with technical targets (latency budget, throughput
  ceiling, SLA tier)

  Service NFR Baseline (constitution.md):
    If [MISSING — ask user] (this is the first feature to reach
    /specify-srd) → derive the baseline categories from this feature's
    own NFRs, fill the constitution row(s), note in srd.md §3:
    "Establishes the NFR baseline — see constitution.md."
    If already filled (a later feature) → srd.md §3 states "Baseline
    (constitution.md): {values} — applies to this feature too, no
    change" and gives its own NFR-NNN row only to something genuinely
    different from the baseline. A stricter/different baseline than
    what's already there is a Constitution Amendment — flag it, don't
    silently overwrite.

  Marker discipline: same as BRD

Back-fill use-cases.md: replace every "_(filled by /specify-srd)_"
(§2 index + §3 per-UC) with the actual FR-NNN list.

Save: srd.md + srd.summary.md
```

Same Confluence/Jira review-and-approval flow. After approval, story
definitions are refined with FR-NNN links + MoSCoW priority
(`docs/jira/{feature}/stories-refined.md`).

State: "SRD generated. Review, then run **/specify-doc {next-doc}**.
Remaining for this scope: {list}." — the next doc name is determined from
the Document Inventory table above, for this project_type + scope.

---

## /specify-doc {name} — Extended Documents (one at a time)

Gate: `srd.md` approved.

```
/specify-doc security       → security-design.md (living — see below)
/specify-doc data-model     → data-model.md (living — mvp+, backend-service/
                               fullstack/data-ml; or this pack's equivalent)
/specify-doc component-spec → component-spec.md (frontend-spa/fullstack, mvp+)
/specify-doc ux-flow        → ux-flow.md (frontend-spa/fullstack/mobile, mvp+)
/specify-doc screen-spec    → screen-spec.md (mobile, mvp+)
/specify-doc resilience     → resilience.md (all types, full only)
/specify-doc investigation  → investigation.md (all types, full only)
```

> **`api-spec` is NOT a valid `/specify-doc` argument.** The API surface is
> extracted from `design.md` §3 during `/plan-design` instead — see
> "Living Documents" above.

If no argument is given, the agent lists the remaining ungenerated
documents for this scope/project_type and asks which to run.

```
Read srd.summary.md + brd.summary.md + constitution.md + {doc}-template.md

Scope check: is {doc} required for this project_type + manifest.scope
per the Document Inventory table above? If not — state "not in scope,
skipping" and stop.

Generate {doc}.md, consistent with every decision already made in BRD/SRD
— flag contradictions rather than silently resolving them.
Marker discipline: same as BRD/SRD.
```

**`data-model` and `security`** are living, service-level documents (see
"Living Documents" above) — saved to `.specify/service/{doc}.md`, not
under `.specify/features/`. If `.specify/service/{doc}.md` doesn't exist
yet, generate it fresh and state it's now the service's living reference.
If it already exists, walk it unit-by-unit: **SKIP** (unchanged) /
**ADD-unit** (new entity/threat entry, shown alone) / **UPDATE-unit**
(BEFORE/AFTER for one unit only) — present every proposed change, wait for
approval, then merge, bump the version header, append a Version History
row naming this feature, and regenerate the summary.

**Security scope rules:** `pilot` → §1 only (Threat Assessment). `mvp` →
§1–2 (+ OWASP Top 10 + STRIDE threat enumeration). `full` → §1–4 (+ DAST
scope + pen-test scope). STRIDE threats are rated with DREAD (score ≥10
Critical, 7–9 High, 4–6 Medium, 1–3 Low) — mitigations required for
High/Critical before `/plan-design`.

**Every other extended doc** (`resilience`, `investigation`,
`component-spec`, `ux-flow`, `screen-spec`) stays per-feature at
`.specify/features/{feature}/{doc}.md`. Exception: `component-spec`'s
"Shared Components Used" section is living at
`.specify/service/component-library.md` for any component this feature
intends other features to reuse — same walk-and-diff discipline as
data-model/security.

Same Confluence/Jira review-and-approval flow as BRD/SRD.

State: "{DOC} generated. Review, then run **/specify-doc {next-doc}**.
Remaining: {list}." or, if none remain: "all spec documents complete. Run
**/validate**."

---

## /checklist — Spec-Quality Validation (after GATE-1, before /validate)

**Mandatory for `mvp` and `full` scope. Optional for `pilot`.**
Run `/checklist` after all `/specify-doc` commands for this scope are
done, to catch spec quality issues before the business sign-off meeting.

```
Read manifest.yml + constitution.md
Read brd.summary.md + srd.summary.md + checklist-template.md

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

## /validate — Business Sign-Off (runs after GATE-1 + all spec docs)

```
Read .specify/manifest.yml + constitution.md + roles.yml
Read brd.summary.md + use-cases.summary.md + srd.summary.md
Read validate-template.md

GATE-1 CHECK: constitution Part 2 finalized?
  If not — STOP. State: "GATE-1 open — finalize constitution Part 2
  before /validate."

Produce:
  0. CHECKLIST GATE (advisory) — warn if open CRITICAL CHK-NNN items
     remain from /checklist; does not block on its own.
  1. BUSINESS OBJECTIVE TRACE — every BO-NNN → FR-NNN(s) that address it.
     Flag any BO-NNN with no FR.
  2. BUSINESS REQUIREMENTS REVIEW — every BR-NNN correctly reflected in
     srd.md? Flag mismatches.
  3. ASSUMPTIONS SIGN-OFF — every [ASSUMPTION-NNN] in brd/srd for the
     business owner to confirm or reject.
  3a. NEEDS CLARIFICATION SCAN — scan brd/use-cases/srd for
      [NEEDS CLARIFICATION] markers; these are BLOCKING — must be
      resolved before sign-off. If document_reviews.validate is
      configured: run `sdd review pull-answers --doc validate` first
      (patches new Jira/Confluence replies into the source docs), then
      `sdd review push-questions --doc validate` for whatever's still
      open.
  4. SCOPE CONFIRMATION — in-scope / out-of-scope items from brd.md.
  4a. SECURITY DESIGN SIGN-OFF (mvp+) — flags if security-design.md has
      no Security Officer approval yet; blocks /analyze until resolved.
  4b. INDICATIVE EFFORT — T-shirt size (S/M/L/XL) per FR-NNN, informational
      only — real story points come at /task.
  5. SIGN-OFF — Product Owner + Business Analyst (names from roles.yml):
     Approved / Changes Requested.

Save: validate.md + validate.summary.md
Stakeholder review (Confluence/Jira submit if document_reviews.validate
configured, else chat approval → Status: Approved + Approvals table +
Version History).
Present report. WAIT for sign-off.

If approved:
  State: "VALIDATE complete — ready for /analyze."
Else:
  State: "VALIDATE incomplete — {N} items need changes. Update
  context.md, re-run the affected /specify-* command(s), re-run
  /validate."
  Do NOT proceed to /analyze.
```

---

## /analyze — Risk + Complexity

```
Read constitution.md + summary-rules.md
Read .specify/features/{feature}/validate.summary.md
Read .specify/features/{feature}/srd.summary.md
Read .specify/features/{feature}/use-cases.summary.md
Read .specify/features/{feature}/brd.summary.md
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
    CONSTITUTION CONFLICTS (CRITICAL — must resolve before /plan-design)

  RECOMMENDATION:
    Suggested approach, items to raise in /clarify, tasks likely
    needing SPLIT

Save: analyze.md + analyze.summary.md
Stakeholder review (Confluence/Jira submit if document_reviews.analyze
configured, else chat approval — same Confluence/Jira/chat flow as BRD).
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
Stakeholder review (Confluence/Jira submit if document_reviews.clarify
configured, else chat approval — same Confluence/Jira/chat flow as BRD).
State: "CLARIFY complete — ready for /plan-design"
```

---

## PLAN Sub-Commands

PLAN adapts to your `plan_mode` setting in `manifest.yml` (set during
`setup.sh`, changeable at any `/plan-*` prompt by replying "unified" /
"separate").

**Unified mode (`plan_mode: unified`)** — one combined document, one review gate:
- **`/plan-design`** → `design.md`: Architecture Overview + Diagrams + API
  Design (§3) + ADRs (§4), all in one document
  - Gate: clarify.summary.md exists, all RESOLVED; no unresolved
    [ASSUMPTION-NNN] (AI-8) in brd/use-cases/srd/security-design
  - §1 Architecture Overview / §2 System Context+Container diagrams:
    established once by the first feature to reach `/plan-design`,
    referenced ("unchanged from {feature}/design.md §N, see there") by
    later features unless this feature changes them
  - §3 API Design: for API-providing project_types, extracted into the
    **living** `.specify/service/api-spec.md` (walk-and-diff if it
    already exists); `design.md` §3 itself only points to it plus this
    feature's new/changed endpoints. For consumer-only types
    (frontend-spa, mobile), the full consumer-view API contract is
    written directly into `design.md` §3, per-feature, not living.
  - Review: architect + tech lead + stakeholders
  - Scope: all scopes (pilot, mvp, full)

**Separate mode (`plan_mode: separate`)** — three focused documents, reviewed individually:
- **`/plan-arch`** → `arch.md`: Architecture pattern, layers, key decisions,
  NFR mapping, cross-cutting concerns — Step 1 of 3
  - Gate: clarify.summary.md exists, all RESOLVED; no unresolved
    [ASSUMPTION-NNN] (AI-8)
  - §1 pattern/layers, §3 layer responsibilities, §6 cross-cutting
    concerns: established once by the first feature, referenced by later
    features (same reuse rule as unified mode §1)
- **`/plan-hld`** → `hld.md`: System diagrams (C4 context, container,
  happy-path sequence, state machine) — Step 2 of 3
  - Gate: arch.md `Status: Approved`
  - Diagrams 1–2 (System Context, Container): established once, reused by
    later features unless this feature adds a new actor/system/datastore
- **`/plan-adr`** → `adr.md`: Architecture Decision Records, one per
  DEC-NNN from arch.md §4 (+ any HIGH-risk item at full scope) — Step 3 of 3
  - Gate: hld.md `Status: Approved`
  - Skipped entirely at `pilot` scope — go straight from `/plan-hld` to `/task`

**Both modes:**
- **`/plan-lld`** → Detailed technical design: package structure,
  class/component diagrams, detailed sequences with error paths, ERD,
  method signatures (mvp+ only; SKIP if pilot)
  - Unified gate: design.md approved
  - Separate gate: adr.md approved (mvp+) — `/plan-lld` is not reached at
    pilot scope in separate mode either (goes hld.md → /task)

### Diagram Self-Check (both modes, every diagram-producing command)
Before saving, verify: every node ID used in an edge is defined in that
diagram; all brackets/braces/parens are balanced; sequence participant
names are consistent across all lines; no empty node labels. Fix any
error found before saving, then state "Diagram self-check passed — {N}
diagrams verified."

---

## /task — Feature → Story → Task + Jira

```
Read constitution.md + summary-rules.md
Read plan.summary.md/design.summary.md (unified) or lld.summary.md/hld.summary.md
  (separate) + analyze.summary.md + clarify.summary.md + srd.summary.md
  + use-cases.summary.md (for EP-NNN exception paths)
  + data-model.summary.md / api-spec.summary.md if present
Read feature-story-template.md + tasks-template.md + jira-export-template.md
+ qa-testcases-template.md

VERIFY: design.md (unified) or lld.md/hld.md (separate, per scope) exists
and reviewed. Stop if not.

1. QA TEST CASES:
   Pilot scope: skip the full qa-testcases.md — generate a lightweight
   smoke-tests.md instead (≤10 TC-S-NNN cases, one per UC Main Path plus
   one per Exception Path, Given/When/Then). tasks.md uses
   "Verifies: TBD — link at /implement".
   MVP+ scope: for each FR-NNN / endpoint, generate TC-NNN covering happy
   path, validation, auth, unhappy path, performance; one TC-NNN per
   EP-NNN-X exception path (highest-value, never skipped); boundary-value
   TC-NNN for numeric/bounded inputs; a PERF-NNN task per measurable NFR.
   Save: qa-testcases.md + qa-testcases.summary.md

2. FEATURE + STORIES:
   FEATURE: business capability from BRD
   Each story: As {actor} I want {X} so that {Y}
   Linked to FR-NNN from SRD
   Story points: 1/2/3/5/8
   MoSCoW priority (Must/Should/Could/Won't Have) from FR-NNN priority
   Sprint assignment
   Acceptance criteria (testable)
   HIGH complexity from analyze.summary.md → higher story points
   Traceability matrix: Story → FR → Task → TC-NNN (mvp+) → EP-NNN → R-NNN

   Save: stories.md + stories.summary.md

3. TASK LIST:
   Each task mapped to a story (STORY-NNN)
   Satisfies: FR-NNN / NFR-NNN
   Verifies: TC-NNN from qa-testcases.md (mvp+; "TBD — link at /implement"
   for pilot)
   Estimated lines
   PR strategy: single or SPLIT A/B/C
   Files that change — names derived from constitution.md Tech Stack, never hardcoded
   Acceptance criteria linked to FR/NFR
   Auto-split any task > max_lines_per_pr
   Pre-flag HIGH complexity / R-NNN high-risk items from analyze.summary.md

   Save: tasks.md

4. JIRA CSV:
   Feature → Story → Task hierarchy (or Tasks-only if Epic/Stories already
   pushed to Jira)
   Story points, sprint, MoSCoW, acceptance criteria
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

VERIFY: tasks.md AND stories.md approved. Stop if not.

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
  Apply manifest.testing_style (paired / tdd / bdd) — never defer tests
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
                the living api-spec.md — API-providing project_types only)
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
  3. DEPLOYMENT PLAN — **standard steps are not re-derived per release**:
     pull the deployment strategy and rollback steps from
     `docs/runbook/local-setup.md` (living document, established once)
     and constitution.md's Tech Stack Orchestration/CI/CD row. Write
     "Standard deployment — see docs/runbook/local-setup.md §{N}" and
     fill in only what's specific to this release: migration/artifact
     version, any new feature flag, owner, confirmation the standard
     steps still apply.
  4. POST-DEPLOY SMOKE TEST — **checks themselves are standard**, pulled
     from docs/runbook/local-setup.md. Fill in only this release's
     specific happy-path check and NFR target.
  5. GO-LIVE GATE — Tech Lead / Product Owner / Ops-SRE: Go / No-Go
     (preconditions: tasks merged, UAT passed, Rollback Plan filled,
     monitoring in place — STOP if any unmet, don't record Go)
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
> **Living documents are the exception.** Never discard/regenerate
> `data-model.md`, `security-design.md`, or (API-providing project_types)
> `api-spec.md` at `.specify/service/` from scratch — that destroys every
> other feature's contribution to the shared schema/security
> baseline/API surface. Extend them via the SKIP/ADD-unit/UPDATE-unit walk
> described in "Living Documents" above instead, even in a recovery
> scenario.

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
Generate newly required /specify-doc {name} documents for the new scope.
Run /plan-lld (now enabled, if upgrading from pilot) and, in separate
plan_mode, /plan-adr (now enabled, if upgrading from pilot).
Then update /task with new tasks.
```
