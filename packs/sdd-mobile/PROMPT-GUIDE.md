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
| `/specify-uc` | `/specify-uc` | `/specify-uc` | Use Case Specification (Actors + UC-NNN) |
| `/specify-srd` | `/specify-srd` | `/specify-srd` | Software Requirements Document |
| `/specify-doc {name}` | `/specify-doc {name}` | `/specify-doc {name}` | One extended doc per run — security, screen-spec, ux-flow, data-model, resilience, investigation |
| `/checklist` (mandatory mvp+, optional pilot) | `/checklist` | `/checklist` | Spec-quality validation (CHK-NNN) |
| `/validate` | `/validate` | `/validate` | Business sign-off on BRD/Use Cases/SRD |
| `/analyze` | `/analyze` | `/analyze` | Risks + complexity |
| `/clarify` | `/clarify` | `/clarify` | Questions → you answer |
| `/plan-design` (unified mode) | `/plan-design` | `/plan-design` | Architecture + Diagrams + API contract (§3, per-feature consumer view) + ADRs — one document |
| `/plan-arch` (separate mode, step 1) | `/plan-arch` | `/plan-arch` | Architecture pattern, layers, key decisions |
| `/plan-hld` (separate mode, step 2) | `/plan-hld` | `/plan-hld` | System diagrams (C4 + sequence + state) |
| `/plan-adr` (separate mode, step 3, mvp+) | `/plan-adr` | `/plan-adr` | Architecture Decision Records |
| `/plan-lld` (mvp+ only) | `/plan-lld` | `/plan-lld` | Class/component + sequence diagrams |
| `/task` | `/task` | `/task` | Stories + Tasks + Jira |
| `/implement` | `/implement TASK-NNN` | `/implement TASK-NNN` | Code one task |
| `/release` | `/release` | `/release` | UAT + store-release plan + go-live gate |
| `/orchestrate` | `/orchestrate` | `/orchestrate` | Drive full pipeline automatically (CLI + multi-agent) — `--list`, `--from STEP`, `--to STEP` |

`plan_mode` (set in `manifest.yml`) decides whether you use `/plan-design`
(unified) or `/plan-arch` → `/plan-hld` → `/plan-adr` (separate) — see
"PLAN Sub-Commands" below.

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
command (`create-context.md`, `start.md`, `specify.md`, `specify-brd.md`,
`specify-uc.md`, `specify-srd.md`, `specify-doc.md`, `checklist.md`,
`validate.md`, `analyze.md`, `clarify.md`, `plan-design.md`, `plan-arch.md`,
`plan-hld.md`, `plan-adr.md`, `plan-lld.md`, `task.md`, `implement.md`,
`release.md`). Claude Code auto-discovers these — nothing to install or
configure.

- Type `/start` at the beginning of every session — equivalent to STEP 0
  below (reads CLAUDE.md, manifest, constitution, summary-rules,
  change-rules, roles.yml, instructions).
- Type `/specify`, `/specify-brd`, `/specify-uc`, `/specify-srd`,
  `/specify-doc {name}`, `/checklist`, `/validate`, `/analyze`, `/clarify`
  to run each step of SPECIFY through CLARIFY.
- Then, depending on your `plan_mode`: either `/plan-design` alone, or
  `/plan-arch` → `/plan-hld` → `/plan-adr` (mvp+) in sequence — followed by
  `/plan-lld` (mvp+), `/task`, and `/release`. Claude reads the matching
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

**Step 1.5 — Feature Size Check:** before mapping the input further, the
agent checks whether your notes actually describe one feature-sized slice
or 2+ independently-shippable features (separate actor sets, separate
resource domains with no shared entity, epic-style "and also" language).
If only one cluster is found — the common case — this passes silently. If
2+ are found, the agent stops and asks whether to build all of it as one
feature, or split and build one at a time; deferred clusters' raw notes
are saved to `.specify/contexts/{other-slug}.raw.md` for a later
`/create-context` run. This matters here because — per this pack's
living-doc model — a second feature reuses/extends the first one's local
data model and security baseline instead of duplicating them, so smaller
independent features stay easier to review.

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
/specify-brd.
```

---

## Document Inventory by Scope/Command (canonical — single source of truth)

| Command | Pilot | MVP | Full |
|---|---|---|---|
| `/specify` | constitution Part 2 (DRAFT) — all scopes |||
| GATE-1 (manual) | constitution Part 2 finalized — all scopes |||
| `/specify-brd` | brd.md — all scopes |||
| `/specify-uc` | use-cases.md (Actors + UC-NNN with MP/AP/EP) — all scopes |||
| `/specify-srd` | srd.md (includes Security Design §1 — Threat Assessment, no separate run needed) | srd.md | srd.md |
| `/checklist` | Optional | **Mandatory** | **Mandatory** |
| `/specify-doc security` | skip (§1 already covered by SRD) | security-design.md §1-2 (**living** — `.specify/service/`) | security-design.md §1-4 (living) |
| `/specify-doc screen-spec` | skip | screen-spec.md | screen-spec.md |
| `/specify-doc ux-flow` | skip | ux-flow.md | ux-flow.md |
| `/specify-doc data-model` | skip | data-model.md — Local Data & Cache Model (**living** — `.specify/service/data-model.md`) | data-model.md (living) |
| `/specify-doc resilience` | skip | skip | resilience.md |
| `/specify-doc investigation` | skip | skip | investigation.md |
| API contract (**not a `/specify-doc` target — this pack only *consumes* an API**) | — | per-feature, in `design.md` §3 — consumer view, `api-spec-template.md`'s "Backend API Contract (Consumer)" shape, not living | same |
| `/validate` | validate.md — all scopes |||
| `/analyze` | analyze.md — all scopes |||
| `/clarify` | clarify.md — all scopes |||
| `/plan-design` (unified) — or `/plan-arch`→`/plan-hld`→`/plan-adr` (separate) | design.md / arch.md+hld.md — Architecture Pattern, Layers, Cross-Cutting Concerns, System Context/Container diagrams established once (first feature) or referenced ("unchanged from {feature}"); API contract stays per-feature §3 | + ADRs — design.md §4 (unified, min 2 at pilot too) or adr.md via `/plan-adr` (separate, mvp+ only) | same |
| `/plan-lld` | **SKIPPED** | lld.md | lld.md |
| `/task` | stories.md, tasks.md, jira — all scopes |||
| `/implement` | code + paired tests | + qa_cases, runbook | + qa_cases, runbook |
| `/release` | release.md — all scopes |||

If any other document in this pack lists a different mapping, this table
wins — fix the other document.

---

## /specify — Constitution Part 2 Only

`/specify` generates the constitution only. Spec documents are generated
**one at a time** afterwards, using dedicated sub-commands: `/specify-brd`
→ `/specify-uc` → `/specify-srd` → `/specify-doc {name}` (once per
extended doc).

```
Read .specify/manifest.yml
Read .specify/memory/constitution.md + summary-rules.md
Read .specify/contexts/{manifest.project.context_file}

ACTION — Generate constitution.md Part 2 (DRAFT):
  Extract from context and fill:

  Tech Stack (extract each concern):
  Language/Framework, Navigation, State Management, Local Storage/DB,
  API Client, Build Tool, Push Notifications, Crash/Analytics,
  Data Cache, Offline Sync, Configuration, Secrets, Resilience,
  Observability, Logging, Testing, Coverage Gate, Quality/Security,
  CI/CD, App Store Distribution

  If concern not in context → use sensible default
  If critical concern missing → mark [MISSING — ask user]

  App NFR Baseline (Cold Start Time, Offline Sync Latency, Crash-Free
  Rate, App Size) — fill from context.md's NFR section if stated, else
  leave [MISSING — ask user]. The first feature to reach /specify-srd
  fills this retroactively from its own NFR-NNN rows once approved; later
  features reference it instead of restating the numbers (a stricter or
  different baseline later is a Constitution Amendment, not a silent
  overwrite).

  Core Principles → derive from domain type (Offline-First,
    Accessible, Cross-Platform, Performant + Specification First,
    Test Discipline, Traceability)
  Domain Rules → extract from business/UX rules section
  Never Do → extract from constraints section + add: API calls in
    screens, hardcode platform checks, permissions on startup, any
    type (RN), mutable state in widgets (Flutter)

  Save constitution.md (Part 1 unchanged, Part 2 = DRAFT)
  Report: "Constitution Part 2 generated — DRAFT. Review and finalize
  every row (GATE-1), then run /specify-brd."

Marker discipline (applies to every document generated from here on):
  [ASSUMPTION-NNN: ...] → reasonable default applied; confirm at /validate
  [NEEDS CLARIFICATION: {question}] → no safe default; must be answered
  before /validate can proceed — never leave a gap silently
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
- No `/specify-brd`, `/validate`, `/analyze`, or any later command runs
  until this gate passes.
- A later `/specify` re-run must propose changes for review — it must
  never silently overwrite a finalized Part 2.

---

## /specify-brd — Business Requirements Document

Gate: GATE-1 passed.

```
Read manifest.yml + constitution.md + roles.yml + context file
Read templates/brd-template.md

VERIFY: constitution Part 2 finalized (no "DRAFT" in the version line).
  If not — STOP. State: "SPECIFY-BRD blocked — finalize constitution
  Part 2 first (GATE-1)."

Generate brd.md:
  §3 Stakeholders — fill Name/Team from roles.yml; leave the ACT-ID
    column "_(set by /specify-uc)_" until actors exist
  Every business goal: BG-NNN
  Every NFR: NFR-NNN with a measurable target (e.g. "< 200ms p99")
  Marker discipline: [ASSUMPTION-NNN] / [NEEDS CLARIFICATION]

Save: brd.md + brd.summary.md

Stakeholder review: Confluence draft (if configured) → incorporate
  comments → Jira/chat submit → on approval: Status Draft → Approved,
  Approvals table filled, Version History row appended, summary
  regenerated
Progressive Jira Epic export: docs/jira/{feature}/epic.md

State: "BRD generated. Review, then run /specify-uc."
Stop — do not generate use-cases.md or any other document in this turn.
```

---

## /specify-uc — Use Case Specification

Gate: BRD approved.

```
Read brd.summary.md (or brd.md, per reading_mode) + templates/use-cases-template.md

VERIFY: brd.md approved (`sdd review check --doc brd` exit 0, or ask user
  directly if the CLI isn't configured).

Generate use-cases.md:
  Every actor: ACT-NNN (Primary / Secondary / System)

  Actor Registry reuse: before deriving an actor from scratch, check
    whether it already appears in another feature's use-cases.md in this
    service (same real-world role, e.g. "Ops Analyst"). If so, reuse its
    Name/Type/Description verbatim — note "(same as {prior-feature}'s
    ACT-NNN)" in the Description column. Only the description content is
    reused; ACT-NNN numbering stays local to this feature's own file.

  Every use case: UC-NNN — Trigger, Preconditions, Postconditions
    (Success/Failure), Main Path (MP, actor/action/system-response rows),
    ≥1 Alternate Path (AP-NNN-X), ≥1 Exception Path (EP-NNN-X), Business
    Rules Applied (BR-NNN), Linked FR-NNN "_(filled by /specify-srd)_",
    Non-Functional Constraints
  §4 Use Case Relationships — Mermaid graph LR (includes/extends)
  §5 Traceability Matrix — UC-NNN → BR-NNN
  Marker discipline: [ASSUMPTION-NNN] / [NEEDS CLARIFICATION]

Back-fill: brd.md §3 Stakeholders — replace "_(set by /specify-uc)_" with
  the assigned ACT-NNN for each role (or "_(N/A)_" if no actor exists for
  it). Re-save brd.md + brd.summary.md.

Save: use-cases.md + use-cases.summary.md

Stakeholder review → approval (same flow as BRD)
Progressive Jira Story Draft export: docs/jira/{feature}/stories-draft.md

State: "Use Cases generated. Review and approve, then run /specify-srd."
Stop — do not generate any further document in this turn.
```

---

## /specify-srd — Software Requirements Document

Gate: Use Cases approved (implies BRD already approved).

```
Read use-cases.summary.md + brd.summary.md + templates/srd-template.md

VERIFY: use-cases.md approved (`sdd review check --doc use-cases` exit 0).

Generate srd.md:
  Every FR-NNN traces to a UC-NNN (Main/Alternate/Exception Path steps)
  NFRs refine BRD NFRs with technical targets (latency budget, throughput
    ceiling, SLA tier)

  App NFR Baseline vs. feature-specific NFRs (read constitution.md's App
  NFR Baseline section):
    If it's still [MISSING — ask user] (first feature to reach here):
      derive the baseline categories from this feature's own NFRs, fill
      the constitution row(s), note in srd.md §3: "Establishes the NFR
      baseline — see constitution.md."
    If it's already filled (a later feature): srd.md §3 states "Baseline
      (constitution.md) — {values} — applies to this feature too, no
      change" and only adds an NFR-NNN row for something genuinely
      different (a stricter target, a new category). Never restate the
      baseline numbers as if deriving them fresh. A stricter/different
      baseline requirement is a Constitution Amendment — flag it, do not
      silently overwrite the row.

  Marker discipline: [ASSUMPTION-NNN] / [NEEDS CLARIFICATION]

Back-fill: use-cases.md — replace every "_(filled by /specify-srd)_" in
  §2 Use Case Index and §3 "Linked FR-NNN" with the actual FR-NNN list.
  Re-save use-cases.md + use-cases.summary.md.

Save: srd.md + srd.summary.md

Stakeholder review → approval (same flow as BRD)
Progressive Jira Story Refinement: docs/jira/{feature}/stories-refined.md (adds
  FR-NNN links + MoSCoW priority to the draft stories)

State: "SRD generated. Review, then run /specify-doc {next-doc}.
Remaining for this scope: {list}."
Stop — do not generate any further document in this turn.
```

---

## /specify-doc {name} — Extended Documents

Gate: SRD approved. One document generated per invocation.

```
Argument: security | screen-spec | ux-flow | data-model | resilience |
investigation

  Note: api-spec is NOT generated here. This pack only *consumes* an API
  — its contract is written per-feature into design.md §3 at /plan-design
  (consumer view, per api-spec-template.md's "Backend API Contract —
  Consumer" structure), never as a /specify-doc output and never a
  living document.

If no argument given: list the remaining ungenerated documents for this
  scope and ask which to generate.

VERIFY: srd.md approved (`sdd review check --doc srd` exit 0). Verify
  this document is required for manifest.project.scope — if not, state
  "not in scope for {scope}. Skipping." and stop.

Generate {doc}.md from templates/{doc}-template.md, derived from
  brd.summary.md + srd.summary.md + constitution.md. Flag any
  contradiction with an already-approved BRD/SRD decision rather than
  silently resolving it. Marker discipline: [ASSUMPTION-NNN] /
  [NEEDS CLARIFICATION].

**data-model and security are living, app-level documents — not
per-feature.** They describe the one local data/cache model and one
security baseline for the whole app, not this feature's slice of it:
  Save to: .specify/service/{doc}.md (NOT .specify/features/)
  Write: .specify/service/{doc}.summary.md

  If .specify/service/{doc}.md does NOT exist yet (first feature that
    needs it): generate fresh from the template as normal. State clearly
    this is now the app's living reference — future features extend it,
    never recreate it.
  If it already exists (a prior feature created it): read the full file
    and walk it one logical unit at a time (one table/entity for
    data-model, one threat-model entry for security) and classify each:
      SKIP           — {unit}: unchanged, no user input needed
      ADD-unit       — show only the proposed new unit's content + why
      UPDATE-unit    — show BEFORE/AFTER for only the affected unit + why
    STOP after presenting every proposed addition/change — wait for
    approval ("approved" / "modify: {text}" / "skip: {unit}") before
    saving anything. On approval: merge only the affected units, bump
    the version header, append a Version History row naming the
    triggering feature, regenerate the .summary.md. Same one-approval-
    at-a-time discipline /change uses for document updates.

security (§ scope-scaling):
  pilot → §1 only (Threat Assessment) — already produced by
    /specify-srd; a separate /specify-doc security run is not required
  mvp   → §1-2 (+ OWASP Top 10 controls + STRIDE threat enumeration)
  full  → §1-4 (+ DAST requirements + penetration test scope)
  STRIDE + DREAD scoring at mvp+; mitigations required for every
    High/Critical threat before /plan-design. Sign-off marker appended
    above the Approvals section.

Every other document (resilience, investigation, screen-spec, ux-flow)
  stays per-feature:
  Save to: .specify/features/{manifest.project.feature}/{doc}.md
  Write: .specify/features/{manifest.project.feature}/{doc}.summary.md

Stakeholder review → approval (same flow as BRD/SRD/use-cases)

If more documents remain for this scope:
  State: "{DOC} generated. Review, then run /specify-doc {next-doc}.
  Remaining: {list}."
If none remain:
  State: "{DOC} generated — all spec documents complete. Run /validate
  for business sign-off."
Stop — do not generate the next document in this turn.
```

---

## Living Documents — App-Level, Not Per-Feature

`data-model.md` (Local Data & Cache Model) and `security-design.md`
describe something singular for the whole app, not one feature — they
live at `.specify/service/` instead of `.specify/features/{feature}/`,
generated once by the first feature that needs them, then **extended by
every later feature**, never regenerated from a blank template:

| Document | Generated by | Lives at |
|---|---|---|
| Local Data & Cache Model | `/specify-doc data-model` | `.specify/service/data-model.md` |
| Security Design | `/specify-doc security` | `.specify/service/security-design.md` |

When one of these already exists, the generating command walks it —
SKIP / ADD-unit / UPDATE-unit, showing only the delta, one approval — see
"/specify-doc {name}" above. This pack's API contract is **not** a living
document: because mobile only *consumes* an API, it stays per-feature in
`design.md` §3 (see "PLAN Sub-Commands" below).

Architecture Pattern, Layer Responsibilities, Cross-Cutting Concerns, and
the System Context / Container diagrams follow a similar (but lighter)
rule at `/plan-design` / `/plan-arch` / `/plan-hld`: established once by
the first feature to reach that command, then referenced by later
features as "unchanged from {feature}/design.md §{N}, see there" instead
of being redrawn — see "PLAN Sub-Commands" below.

---

## /checklist — Optional Spec-Quality Gate (mandatory mvp+, after GATE-1, before /validate)

Run this after all spec documents for the scope are generated and
approved, before the business sign-off meeting.

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

If CRITICAL items: State "Fix CRITICAL items → update the affected spec
doc(s) → re-run /checklist"
If no CRITICAL: State "Spec quality gate passed — ready for /validate"
```

---

## /validate — Business Sign-Off (runs after GATE-1)

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
  3a. NEEDS CLARIFICATION SCAN — scan brd/use-cases/srd for
      [NEEDS CLARIFICATION] markers; these are BLOCKING — must be
      resolved before sign-off
  4. SCOPE CONFIRMATION — in-scope / out-of-scope items from brd.md.
  4a. SECURITY DESIGN SIGN-OFF (mvp+/full, if security-design.md exists)
      — flag if not yet signed off by the Security Officer.
  5. SIGN-OFF — Product Owner + Business Analyst (names from roles.yml):
     Approved / Changes Requested.

Save: validate.md + validate.summary.md
Present report. WAIT for sign-off.

If approved:
  State: "VALIDATE complete — ready for /analyze."
Else:
  State: "VALIDATE incomplete — {N} items need changes. Update
  context.md, update the affected spec doc(s), re-run /validate."
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
`setup.sh`, changeable any time by editing the file or replying
"unified"/"separate" when a plan command asks).

### Unified mode (`plan_mode: unified`) — one document, one review gate

**`/plan-design`** → `design.md`:

```
Read constitution.md + summary-rules.md
Read clarify.summary.md (MUST exist, all RESOLVED — stop if missing)
Read analyze.summary.md + all spec summaries (brd, use-cases, srd, security)
Read design-template.md

AI-8 GATE CHECK: scan brd.md, use-cases.md, srd.md, security-design.md
for any [ASSUMPTION-NNN] without a matching <!-- Clarified: {ID} --> note.
  If any remain — STOP. State: "PLAN-DESIGN blocked — unresolved
  assumptions {list}. Run /clarify first."

§1 ARCHITECTURE OVERVIEW:
  Architecture pattern, system layers, and cross-cutting concerns (auth,
    logging, error handling, idempotency, observability) describe the
    whole app, not this feature — established once by the first feature
    to reach /plan-design, then referenced by later features as
    "unchanged from {feature}/design.md §1, see there" (expand only the
    part that genuinely changes, as a delta)
  DEC-NNN design decisions + NFR → decision mapping — always
    feature-specific, every feature, never reused

§2 DIAGRAMS (Mermaid):
  System Context (C4 L1) + Container Diagram (C4 L2) — describe the
    whole app's topology; same reuse rule as §1 ("unchanged from
    {feature}/design.md §2" unless this feature adds a new external
    system/integration)
  Always fresh, feature-specific: Component Diagram (C4 L3), Happy Path
    Sequence, Error/Failure Paths (UC Exception Paths), State Machine
    (if applicable)

§3 API DESIGN — this pack only *consumes* an API (mobile: no backend to
  provide one). Use api-spec-template.md's "Backend API Contract —
  Consumer" structure and document the contract this app *consumes*,
  per-feature, directly in design.md §3 — never in .specify/service/,
  never treated as a living document (unlike backend-service/fullstack
  packs, where a service's own API surface IS a living doc at
  .specify/service/api-spec.md).

§4 ARCHITECTURE DECISIONS (ADR): one ADR per DEC-NNN from §1 — Context,
  Decision, Rationale, Alternatives (≥2), Consequences, Review date.
  Pilot scope: minimum 2 ADRs for the most impactful decisions.
  MVP+ scope: one ADR per DEC-NNN.

DIAGRAM SELF-CHECK: every node ID used in an edge is defined; all
  brackets/parens/braces balanced; sequence participant names
  consistent; no empty node labels. Fix before saving.

Save: design.md + design.summary.md

If scope = pilot:
  State: "design.md generated — review, then run /task."
Else:
  State: "design.md generated — review, then run /plan-lld."
Wait for approval.
```

### Separate mode (`plan_mode: separate`) — three focused documents

**`/plan-arch`** → `arch.md` — Step 1 of 3
```
Gate: clarify.summary.md all RESOLVED; no unresolved [ASSUMPTION-NNN]
  in brd.md/use-cases.md/srd.md (AI-8)

§1 Architecture Overview, §3 Layer Responsibilities, §6 Cross-Cutting
  Concerns — describe the whole app; established once by the first
  feature, referenced as "unchanged from {feature}/arch.md §{N}" after
§2 Component Structure (Mermaid graph TD) — always feature-specific
§4 Key Design Decisions (DEC-NNN) — always feature-specific
§5 NFR → Architecture Decision Mapping — always feature-specific

Save: arch.md + arch.summary.md
State: "arch.md approved. Run /plan-hld next."
```

**`/plan-hld`** → `hld.md` — Step 2 of 3 (gate: arch.md `Status: Approved`)
```
Diagram 1 System Context (C4 L1) + Diagram 2 Container Diagram (C4 L2) —
  describe the whole app's topology; reuse rule same as arch.md §1/§3/§6
  ("unchanged from {feature}/hld.md Diagram 1/2" unless this feature adds
  a new actor/external system/datastore)
Diagram 3 Happy Path Sequence, Diagram 4 State Machine (if applicable) —
  always feature-specific
§5 Tech Stack Summary, §6 NFR Summary
Diagram self-check (same rules as unified mode)

Save: hld.md + hld.summary.md
mvp+ scope: "Run /plan-adr next."
pilot scope: "Run /task next." (ADRs skipped at pilot)
```

**`/plan-adr`** → `adr.md` — Step 3 of 3, **mvp+ only** (gate: hld.md
`Status: Approved`; skipped entirely at pilot scope)
```
One ADR per DEC-NNN from arch.md §4, plus one per HIGH-risk item from
  analyze.summary.md not already covered (full scope)
Each: Context, Options (≥2), Decision, Rationale, Consequences, Review Date

Save: adr.md + adr.summary.md
State: "adr.md approved. Run /plan-lld next."
```

### Both modes — `/plan-lld` (mvp+ only, skipped at pilot)

```
Gate — unified: design.md Status: Approved
Gate — separate: hld.md Status: Approved (pilot — but pilot skips
  plan-lld entirely) AND adr.md Status: Approved (mvp+)

Package/folder structure, Class Diagram (backend) or Component Diagram
  (frontend/mobile), Detailed Sequence Diagrams (happy + unhappy paths,
  include error handling/retry/offline-queue paths per resilience.md at
  full scope), ERD (if local database), Key Method Signatures,
  DTO/Record Definitions
Diagram self-check (same rules)

Save: lld.md + lld.summary.md
State: "lld.md approved. Run /task next."
```

---

## /task — Feature → Story → Task + Jira

```
Read constitution.md + summary-rules.md
Read plan_mode from manifest.yml, then:
  unified:  design.summary.md (or design.md)
  separate: lld.summary.md (mvp+) or hld.summary.md (pilot)
Read analyze.summary.md + clarify.summary.md + srd.summary.md
Read use-cases.summary.md (for EP-NNN exception paths — must not be skipped)
Read feature-story-template.md + tasks-template.md + jira-export-template.md
Read qa-testcases.summary.md (mvp+, if already generated)
Read data-model.summary.md (.specify/service/, if it exists) — entity/
  schema names used to derive file names

VERIFY GATE (per plan_mode):
  unified:  design.md exists with Status: Approved. Stop if not.
  separate: pilot → hld.md Approved (lld/adr skipped). mvp/full → lld.md
            exists and reviewed (generated after adr.md). Stop if not.

1. QA TEST CASES (mvp+; pilot generates a ≤10-case smoke-tests.md instead):
   For each FR-NNN / API endpoint consumed (design.md §3): TC-NNN covering
   happy path, validation, auth, unhappy path, performance
   For each EP-NNN-X in use-cases.md: a TC-NNN covering the error
   condition, system response, recovery outcome
   For each NFR with a measurable threshold: a PERF-NNN performance task

2. FEATURE + STORIES:
   FEATURE: business capability from BRD
   Each story: As {actor} I want {X} so that {Y}
   Linked to FR-NNN from SRD
   Story points: 1/2/3/5/8
   Sprint assignment
   MoSCoW priority (Must/Should/Could/Won't Have)
   Acceptance criteria (testable)
   HIGH complexity from analyze.md → higher story points
   Traceability matrix: Story → FR → Task → TC-NNN → EP-NNN → R-NNN

   Save: stories.md + stories.summary.md

3. TASK LIST:
   Each task mapped to a story (STORY-NNN)
   Satisfies: FR-NNN / NFR-NNN
   Verifies: TC-NNN (mvp+; "TBD — link at /implement" if pilot)
   Estimated lines
   PR strategy: single or SPLIT A/B/C
   Files that change
   Acceptance criteria linked to FR/NFR
   Auto-split any task > max_lines_per_pr
   Pre-flag HIGH complexity items from analyze.md

   Save: tasks.md

4. JIRA CSV:
   Epic → Story → Task hierarchy (or Tasks-only if Epic/Story keys
   already pushed — check docs/jira/{feature}/keys.yml)
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

VERIFY GATE (per manifest.workflow_mode):
  github: every task in tasks.md is "PR ready" and merged.
  local:  every task in tasks.md is "Task accepted".
  If not — STOP. State: "RELEASE blocked — {N} tasks not yet
  {merged|accepted}."

Produce:
  1. PRE-RELEASE CHECKLIST — tasks merged, PRs reference TASK-NNN/CHG-NNN,
     tests green, coverage ≥ gate, accessibility checks passed,
     security checklist passed (security-design.md §1, +§2 mvp+),
     traceability complete
  2. UAT PLAN — one row per UC-NNN from srd.md: scenario, tester (from
     roles.yml), device/OS target + environment (staging/TestFlight/
     internal track), result
  3. STORE RELEASE PLAN — the release strategy and rollback steps are
     **standard for this app, not re-derived per release**: pull them
     from docs/runbook/local-setup.md (living document, established
     once) and constitution.md's App Store Distribution row. Write
     "Standard release — see docs/runbook/local-setup.md §{N}" rather
     than re-describing build+sign / staged rollout / TestFlight phase /
     OTA push. Fill in only what's specific to this release: staged
     rollout percentage/schedule, owner, and confirmation the standard
     steps still apply (or a note on what's different this time, e.g. a
     native module requiring a full store review instead of OTA)
  4. POST-RELEASE SMOKE TEST — the checks themselves are standard, pulled
     from docs/runbook/local-setup.md; fill in only this release's
     specific happy-path screen flow and NFR target: app launch/cold
     start, {this release's key happy-path flow}, crash-free rate target,
     {this release's key NFR target}, error-tracking SDK live
  5. GO-LIVE GATE — Tech Lead / Product Owner / Ops-SRE: Go / No-Go
  6. BUSINESS OBJECTIVE CLOSURE — every BO-NNN: metric, measured result
     or "measure after N days", met? yes/pending
  7. ROLLBACK PLAN — summary, points to docs/runbook/local-setup.md §6
     for full detail (staged rollout halt, OTA rollback, store-listing
     rollback)

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
**Caveat — never do this for a living document.** `data-model.md` and
`security-design.md` live at `.specify/service/` and are shared across
every feature — discarding and regenerating either one from a blank
template destroys every other feature's contributions to it. For these
two, always use the SKIP / ADD-unit / UPDATE-unit walk described in
"/specify-doc {name}" above instead, never a wholesale regeneration.

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
Run /specify-doc {name} for each newly required extended doc (e.g.
  data-model, resilience).
Run /plan-lld (skipped previously at pilot). If plan_mode: separate,
  also run /plan-adr (also skipped at pilot).
Then update /task with new tasks.
```
