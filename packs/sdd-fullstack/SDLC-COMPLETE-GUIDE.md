# Complete SDLC Guide
# SDD — Full Command Reference

---

## Overview

Write one context file (or run `/create-context` first to turn rough notes into
a structured file — the agent drafts it with you). From there, the agent generates
every specification document, the design, the task list, and the release artefacts.

Constitution Part 2 is generated as a DRAFT after `/specify` — you review and
finalize it (GATE-1) before any later command can run. All manual edits are
authoritative. `/validate` (business sign-off) and `/release` (UAT/go-live)
bookend the pipeline.

Use `/change` at any stage if a requirement changes — it reads existing documents
one by one, shows only what needs updating, and waits for your approval before
touching the next document.

---

## Command Flow

| # | Command | Does | Gate Before |
|---|---|---|---|
| 0 | `/create-context` | Turn rough notes into context.md (optional pre-phase) | None |
| 1 | `/specify` | Constitution Part 2 (DRAFT) | None |
| — | **GATE-1** | You finalize constitution Part 2 (manual, blocking) | After /specify |
| 2 | `/specify-brd` | Business Requirements Document | GATE-1 passed |
| 3 | `/specify-uc` | Use Case Specification (Actors + UC-NNN) | BRD approved |
| 4 | `/specify-srd` | Software Requirements Document | Use cases approved |
| 5 | `/specify-doc {name}` | Extended docs: security, data-model (both living, `.specify/service/`), component-spec, ux-flow, resilience… | SRD approved |
| 6 | `/checklist` | Spec quality gate (mandatory mvp+, optional pilot) | After specify docs |
| 7 | `/validate` | Business sign-off on BRD + SRD | GATE-1 passed |
| 8 | `/analyze` | Risks, dependencies, complexity | validate.summary.md exists |
| 9 | `/clarify` | Open questions → you answer | After /analyze |
| 10 | `/plan-design` | Architecture + Diagrams + API Design + ADR entries | clarify.summary.md, no unresolved [ASSUMPTION-NNN] |
| 11 | `/plan-lld` | Detailed LLD: class/sequence diagrams (mvp+ only) | design.md reviewed |
| 12 | `/task` | Stories + Tasks + Jira push | design.md reviewed |
| 13 | `/implement` | One task at a time | tasks approved |
| 14 | `/release` | UAT plan + deployment + go-live gate | all tasks merged |
| — | `/orchestrate` | Drive full pipeline automatically (CLI + multi-agent) — `--list`, `--from STEP`, `--to STEP` | Optional |
| — | `/change` | Raise a change request at ANY stage | Any stage |

---

## /create-context — Optional Pre-Phase

If you do not yet have a structured context file, run `/create-context` and paste
your rough notes (any format — email, bullet points, doc excerpt). The agent drafts
`context.md` against the template, lists missing information as plain questions, and
iterates with you until it is ready.

**Shortcut:** put this on the very first line of your notes file:
```
# specify: I am building a payment processing microservice that handles
credit card transactions for the checkout flow, integrated with Stripe
```
The agent extracts the feature name and seeds §1 "What This Service Does" from it.

**Feature Size Check (Step 1.5):** before drafting, the agent checks
whether your notes actually describe 2+ independently-shippable features
rather than one. If so, it asks whether to build them one at a time —
the chosen feature proceeds as normal, and every other feature's raw
notes are saved to `.specify/contexts/{slug}.raw.md` for a later
`/create-context` run.

---

## /specify — Five Sub-Commands

`/specify` generates the constitution only. Spec documents are generated one at a
time using dedicated sub-commands.

| Command | Generates | Gate |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) | None |
| `/specify-brd` | Business Requirements Document | GATE-1 passed |
| `/specify-uc` | Use Case Specification (Actors + UC-NNN with MP/AP/EP) | BRD approved |
| `/specify-srd` | Software Requirements Document | Use cases approved |
| `/specify-doc {name}` | security / data-model / component-spec / ux-flow / resilience / investigation — `security` and `data-model` are **living, service-level** documents at `.specify/service/`, extended by every feature after the first (SKIP/ADD-unit/UPDATE-unit), never regenerated; `component-spec`'s "Shared Components Used" section is living too, at `.specify/service/component-library.md`. `api-spec` is NOT one of these — it's extracted from `design.md` §3 during `/plan-design` instead, into the living `.specify/service/api-spec.md`. | SRD approved |

**Constitution Part 2 contents:**
Tech Stack split Backend / Frontend / Shared (Backend: Language, Framework, Build
Tool, Messaging/Async, Schema, Data Store, Data Cache, DB Migration, Resilience,
Testing, Coverage Gate; Frontend: Language, Framework, Build Tool, State Management,
Component Library/Design System, Routing, API Client, Data Cache, Testing, Coverage
Gate, Accessibility; Shared: API Style, Serialisation, Configuration, Secrets,
Observability, Logging, Quality/Security, Orchestration, CI/CD) + Service NFR
Baseline split Backend/Frontend (Backend: Performance/Availability/Throughput/Data
Retention; Frontend: Load Time/Bundle Size/Interactivity — filled once by the first
feature to reach `/specify-srd`, referenced by every later feature instead of
restating the same numbers) + Core Principles, Domain Rules, Never Do

**Spec document inventory by scope:**
```
pilot: brd → use-cases → srd → security-design (§1)
mvp:   + component-spec → ux-flow → data-model → security-design (§1-2)
       [api-spec is extracted later, at /plan-design §3]
full:  + resilience → investigation → security-design (§1-4)
```
`data-model.md`, `security-design.md`, `api-spec.md`, and
`component-library.md` are **living, service-level** documents at
`.specify/service/` — the first feature creates them, every later feature
extends them (SKIP/ADD-unit/UPDATE-unit), never regenerated from a blank
template. `/specify-uc` also reuses an actor already defined in another
feature's `use-cases.md` (same real-world role) instead of re-deriving it.

---

## GATE-1 — Finalize Constitution Part 2 (manual, blocking)

After `/specify`, Part 2 is a DRAFT. No other command runs until this is done:
1. Review every row (Tech Stack, Core Principles, Domain Rules, Never Do)
2. Resolve `[MISSING — ask user]` markers
3. Edit anything wrong — manual edits are AUTHORITATIVE
4. Tell agent: "Constitution Part 2 finalized"

A later `/specify` re-run proposes diffs for review — never silently overwrites
a finalized Part 2.

---

## /checklist — Spec Quality Gate

**Mandatory for mvp and full. Optional for pilot.**
Run after all specify sub-commands, before `/validate`.

Catches:
- **CRITICAL** (block /validate): unresolved [NEEDS CLARIFICATION], unmeasured NFRs,
  FRs with no acceptance scenario
- **HIGH**: vague adjectives without a number, UCs without Independent Test
- **MEDIUM**: terminology drift, missing Out of Scope items

Saves to: `.specify/features/{feature}/checklists/{feature}-spec-quality.md`

---

## /validate — Business Sign-Off

Reviewer: **Product Owner** (accountable) + **Business Analyst** (responsible)

- §1 Business Objective Trace: every BO-NNN → FR-NNN
- §2 Business Requirements Review: BA confirms FR mapping, PO confirms business intent
- §3 Assumptions Sign-Off: every [ASSUMPTION-NNN] confirmed or rejected
- §4 Scope Confirmation: in-scope / out-of-scope items
- §5 Sign-off
- §6 Change Requests raised during review (CR-NNN tracked here)

---

## /analyze — Risk + Complexity

Reviewer: **Tech Lead** (accountable) + **Architect** (consulted, mvp+)

- Risk register with probability × impact × FR/NFR link
- Dependency map (internal + external)
- Complexity ratings per area
- Distributed systems consistency section (mvp+)

---

## /plan-design — Architecture + Design

**Gate:** `clarify.summary.md` exists, all RESOLVED + no unresolved [ASSUMPTION-NNN]

Produces `design.md` — single document covering:
- Architecture decisions (component map, technology choices) — established
  once by the first feature; later features reference it ("unchanged from
  {feature}, see there") instead of re-deriving the same pattern/layers/
  cross-cutting concerns
- Sequence / flow diagrams (Mermaid)
- API Design (§3): this feature's new/changed endpoints only — the full,
  current API surface is extracted into the living
  `.specify/service/api-spec.md`, never restated here in full
- ADR entries (Architecture Decision Records)
- NFR → technology decision mapping

Reviewer: Architect + Tech Lead + stakeholders (all scopes)

> `design.md` replaces the former `arch.md`, `hld.md`, and `adr.md`.
> `/plan-arch`, `/plan-hld`, `/plan-adr` redirect to `/plan-design` for
> backwards compatibility. `api-spec.md` is not replaced by `design.md` —
> it's extracted from `design.md` §3 into its own living document at
> `.specify/service/api-spec.md`, shared across every feature in the
> service, extended via SKIP/ADD-unit/UPDATE-unit rather than regenerated.

---

## /plan-lld — Detailed LLD (mvp+ only)

**Gate:** `design.md` reviewed

Produces detailed technical design: class diagrams, sequence diagrams, package structure.
Agent auto-skips and states reason if scope is pilot.

Reviewer: Senior developer

---

## Pilot Flow
```
/create-context (if needed)
→ /specify → [GATE-1]
→ /specify-brd → /specify-uc → /specify-srd → /specify-doc security
→ /checklist (optional)
→ /validate → /analyze → /clarify
→ /plan-design (review)
→ /task (review) → /implement → /release
```

## MVP+ Flow
```
/create-context (if needed)
→ /specify → [GATE-1]
→ /specify-brd → /specify-uc → /specify-srd
→ /specify-doc security → /specify-doc component-spec → /specify-doc ux-flow → /specify-doc data-model
→ /checklist (mandatory)
→ /validate → /analyze → /clarify
→ /plan-design (review) → /plan-lld (review)
→ /task (review) → /implement → /release
```

---

## /task — Stories + Tasks

```
FEATURE (from BRD)
  └── STORY (As / I want / So that — linked to FRs, MoSCoW priority)
        ├── Story points + Sprint
        ├── Acceptance criteria
        └── TASK (one PR each)
              ├── Satisfies: FR/NFR | Verifies: TC-NNN
              ├── Estimated lines
              └── PR strategy: single or SPLIT A/B/C
```

Traceability: Story → FR → Task → TC-NNN.
Jira push: `sdd jira push` — import before `/implement` starts.

---

## /implement — Code + PR

Per task:
1. Agent estimates lines — if over `max_lines_per_pr` → SPLIT, confirm, one part at a time
2. Agent writes code + paired test
3. `/pre-review` — agent analyses diff, presents numbered findings, you pick which to fix
4. `sdd pr create --task TASK-NNN` — creates PR with pre-review summary in body
5. Human review — approve or add inline comments
6. `/address-review` — agent addresses unresolved threads, pushes fix, requests re-review
7. PR merged → task complete

**workflow_mode:**
- `github`: "PR ready" → wait for go
- `local`: run build/test/lint/coverage locally → report ✅/❌ → "Task accepted" → wait for go

---

## /release — UAT, Deployment, Go-Live

Runs after all tasks complete.

1. Pre-Release Checklist (tests green, coverage, security evidence, traceability)
2. UAT Plan — UC-NNN → tester → environment prerequisites → result (both backend and frontend scenarios)
3. Deployment Plan — the strategy and rollback steps are standard for
   this service, not re-derived per release: pulled from
   `docs/runbook/local-setup.md` §6 (backend) and §6a (frontend) (living
   document, established once)
4. Post-Deploy Smoke Test — the checks themselves are standard, pulled
   from the runbook; only this release's specific endpoint/screen/NFR
   target is filled in
5. Go-Live Gate — Tech Lead / Product Owner / DevOps-SRE: Go / No-Go
6. Business Objective Closure — BO-NNN → measured result → met?
7. Rollback Plan — summary, points to `docs/runbook/local-setup.md` §6
   (backend) and §6a (frontend) for full detail

---

## /change — Change Requests at Any Stage

Run `/change` whenever a requirement changes — at any point in the pipeline.

```
/change "payment gateway returns 402 for valid cards — missing retry requirement"
```

The agent:
1. Classifies the CR type (Business / Technical / Security / Data / UX / Performance / Operational / Defect)
2. Detects current stage from existing documents
3. Presents a walk plan — which documents to check, in order
4. Reads each document one at a time
5. Shows BEFORE / AFTER diff for anything that needs changing — STOPS and waits for your approval
6. Skips documents with no impact, annotates approved upstream documents
7. Creates CHG-NNN implementation tasks after all docs are resolved
8. Saves a changeset record: `.specify/features/{feature}/changesets/CR-NNN.md`

See `CHANGE-GUIDE.md` for the full CR type matrix and examples.

---

## PR Rules (enforced at /implement)

- Estimate before every task
- If > `max_lines_per_pr` → SPLIT A/B/C → confirm → one at a time
- Paired test required for every PR
- After task: "PR ready" (github mode) or "Task accepted" (local mode) → wait for go

---

## Full Checklist

### Setup
- [ ] `manifest.yml` filled (project.name, scope, feature, context_file)
- [ ] `roles.yml` filled (RACI owners per gate)
- [ ] `context.md` written (directly or via `/create-context`)
- [ ] Git initialised

### /specify
- [ ] Constitution Part 2 generated (DRAFT) — Tech Stack table complete
- [ ] `/specify-brd` — BRD reviewed by Product Owner
- [ ] `/specify-uc` — Use Cases reviewed by BA + PO
- [ ] `/specify-srd` — SRD reviewed by BA
- [ ] `/specify-doc security` — security-design reviewed by Security Officer
- [ ] Additional `/specify-doc` calls for component-spec, ux-flow, data-model (mvp+, living), resilience (full)
- [ ] api-spec extracted at `/plan-design` §3 into the living `.specify/service/api-spec.md` (mvp+)

### GATE-1
- [ ] Every Part 2 row reviewed, `[MISSING]` markers resolved
- [ ] "Constitution Part 2 finalized" confirmed

### /checklist
- [ ] All CRITICAL items resolved (blocks /validate if open)
- [ ] HIGH items reviewed

### /validate
- [ ] Every BO-NNN traced to FR-NNN
- [ ] Every BR-NNN reflected in SRD
- [ ] Every [ASSUMPTION-NNN] confirmed or rejected
- [ ] Product Owner + Business Analyst sign-off

### /analyze
- [ ] Risk register reviewed — every risk linked to FR/NFR
- [ ] Complexity hotspots noted

### /clarify
- [ ] All items answered and confirmed RESOLVED
- [ ] `clarify.summary.md` generated

### /plan-design
- [ ] AI-8: no unresolved [ASSUMPTION-NNN] anywhere
- [ ] Architecture reviewed by Tech Lead + Architect
- [ ] API Design section reviewed and locked
- [ ] ADR entries approved
- [ ] NFR → decision mapping complete

### /plan-lld (mvp+)
- [ ] Class + sequence diagrams reviewed by senior developer

### /task
- [ ] Stories make business sense (Product Owner)
- [ ] All tasks have estimated lines + Verifies: TC-NNN
- [ ] Over-limit tasks marked SPLIT
- [ ] `sdd jira push` run — Jira issues created
- [ ] `stories.md` + `tasks.md` BOTH approved

### /implement
- [ ] Each task estimated before coding
- [ ] Each PR under line + file limits
- [ ] Paired test every PR
- [ ] Pre-review run, findings addressed
- [ ] Tests passing before merge
- [ ] qa-testcases / runbook generated (mvp+), openapi (full)

### /release
- [ ] Pre-release checklist green (including monitoring/APM evidence)
- [ ] UAT plan executed, sign-off recorded
- [ ] Deployment strategy selected, steps + rollback reviewed
- [ ] Go-live gate: all roles "Go"
- [ ] Business objective closure recorded
