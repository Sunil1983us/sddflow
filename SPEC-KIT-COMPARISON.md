# SDD Framework (packs-v2) vs. GitHub spec-kit

> A side-by-side comparison of our Spec-Driven Development framework
> (`packs-v2/sdd-*`) against GitHub's open-source `spec-kit` project —
> for evaluating which fits an enterprise SDLC.

---

## TL;DR

| | **GitHub spec-kit** | **packs-v2 SDD Framework** |
|---|---|---|
| Designed for | Individual developer / small team, tool-agnostic | Enterprise teams with formal sign-off chains |
| Commands | 7 (`/speckit.constitution` → `implement`) | 9–11 (`/specify` → `/release`) |
| Spec artifacts per feature | spec.md, plan.md, research.md, data-model.md, tasks.md, checklists/ | BRD, SRD, Security-Design, API Spec, Data Model, Resilience, Arch, HLD, LLD, ADR, Stories, Tasks, QA Cases, Runbook, Release |
| Tech stack capture | Per-feature, inside plan.md | Once, in constitution.md Part 2 (20-concern table), GATE-1 finalized |
| Governance / RACI | None | `roles.yml` — every gate has a named accountable role |
| Hard gates | 2 (Constitution Check in plan.md, checklist completeness in implement.md) | Gate at every command transition (GATE-1, validate, AI-8 assumptions, clarify, etc.) |
| Business sign-off | Not modeled | `/validate` — Product Owner + Business Analyst sign-off on BRD/SRD |
| Traceability | On-demand report (`/speckit.analyze` → FR/SC → task coverage table) | Persistent matrix: Story → FR/NFR → Task → TC-NNN → R-NNN |
| PR / CI governance | Left to the team's normal git workflow | Built-in `pr_rules` (max lines/files, SPLIT A/B/C), `quality-gate.yml`, and a configurable `workflow_mode: github \| local` |
| Portability | Designed to run identically across many AI coding tools | Per-IDE prompt mirrors (`.github/prompts/`, `.claude/commands/`) |

**Bottom line:** spec-kit is a lean, portable scaffold that turns "vibe
coding" into structured, requirement-driven development for a single
developer. packs-v2 SDD is that same idea taken further — it adds the
governance layer (sign-offs, RACI, audit trail, PR/CI rules) that an
enterprise team needs to run AI-assisted delivery as a *process*, not just
a prompt template.

---

## 1. Directory & Artifact Structure

### spec-kit
```
.specify/
  memory/constitution.md          # principles + governance only
  templates/                       # spec, plan, tasks, checklist templates
  templates/commands/*.md          # one prompt file per slash command
  scripts/{bash,powershell}/
specs/
  001-feature-name/
    spec.md          # WHAT/WHY — user scenarios, FR-###, SC-###
    plan.md           # HOW — tech stack, Constitution Check, project structure
    research.md
    data-model.md
    contracts/
    tasks.md          # T001.. with [P]/[US1] tags
    checklists/
```

### packs-v2/sdd-backend-service
```
.specify/
  memory/
    constitution.md   # Part 1 (framework, fixed) + Part 2 (20-concern Tech
                       # Stack table + Principles + Domain Rules, GATE-1)
    roles.yml          # RACI — who is accountable at each gate
  manifest.yml          # project info, scope, pr_rules, workflow_mode
  contexts/{feature}.md
  templates/            # one template per document type
  output/{feature}/
    brd.md, srd.md, security-design.md, api-spec.md, data-model.md,
    resilience.md, arch.md, hld.md, lld.md, adr.md,
    stories.md, tasks.md, qa-cases.md, runbook.md, release.md
.github/prompts/*.prompt.md   # Copilot
.claude/commands/*.md          # Claude Code
.github/workflows/quality-gate.yml
```

**Takeaway:** spec-kit produces one cohesive feature folder; packs-v2
produces a *document set per feature* mirroring how a regulated SDLC
already separates BRD/SRD/security/architecture/QA — useful when those
documents need to be reviewed by different people or fed into existing
enterprise tooling (Confluence, Jira, audit systems).

---

## 2. How Detailed Is the Spec Itself?

**spec-kit's `spec.md`** is deliberately WHAT/WHY only, with a tight,
testable structure:
- User Scenarios grouped by priority (P1/P2/P3), each with
  Given/When/Then acceptance scenarios
- Edge Cases as an explicit checklist
- `FR-###` functional requirements (atomic, numbered)
- `SC-###` measurable success criteria (e.g. "95% of requests complete
  under 200ms")
- Key Entities
- `[NEEDS CLARIFICATION]` inline markers for anything ambiguous — the
  spec is allowed to ship with these, resolved later by `/speckit.clarify`

**packs-v2's BRD/SRD** spread the same information across two documents:
- BRD: Business Objectives (`BO-NNN`) and Business Requirements (`BR-NNN`)
- SRD: Functional/Non-Functional Requirements (`FR-NNN`/`NFR-NNN`),
  `[ASSUMPTION-NNN]` markers (must all be resolved before `/plan-arch`,
  enforced by the AI-8 gate)

**Takeaway:** spec-kit's single spec.md is *sharper per requirement* —
every FR has Given/When/Then test scenarios baked in from the start.
packs-v2 traces the same ideas (BO → BR → FR/NFR) but separates
"why we're building this" (business) from "what it must do"
(functional/non-functional) into documents a Product Owner and a Tech
Lead can review independently — which maps onto how most enterprises
already split business vs. technical sign-off.

---

## 3. Commands & Flow

| Step | spec-kit | packs-v2 (pilot scope) |
|---|---|---|
| 1 | `/speckit.constitution` | `/specify` (also drafts Part 2 of constitution) |
| — | | **GATE-1** — manual review/finalize constitution |
| 2 | `/speckit.specify` | `/validate` — business sign-off |
| 3 | `/speckit.clarify` | `/analyze` — risk/complexity |
| 4 | `/speckit.plan` | `/clarify` — resolve open questions |
| 5 | `/speckit.tasks` | `/plan-arch` — architecture + plan |
| 6 | `/speckit.analyze` (optional) | `/plan-hld` — HLD + diagrams |
| 7 | `/speckit.implement` | (`/plan-lld`, `/plan-adr` — MVP+ only) |
| 8 | | `/task` — Feature → Story → Task + Jira CSV |
| 9 | | `/implement` — one task at a time, PR rules enforced |
| 10 | | `/release` — UAT + deployment + go-live gate |

**Takeaway:** spec-kit gets a developer from idea to code in ~6 steps with
minimal ceremony. packs-v2 adds the steps an enterprise actually performs
around code — business validation, risk analysis, architecture review,
and a formal release/go-live gate — each with a named owner.

---

## 4. Gates: Advisory vs. Mandatory

**spec-kit** has exactly two *hard* stops:
1. `plan.md`'s "Constitution Check" — re-verified after design, fails the
   run with an `ERROR` if violated.
2. `implement.md` refuses to proceed if items in `checklists/` are
   unresolved.

Everything else (`/speckit.clarify`, `/speckit.analyze`) is recommended
but skippable — there's no concept of "who" approves a step.

**packs-v2** treats *every* command transition as a gate, each mapped to
a role in `roles.yml`:
- **GATE-1**: Tech Lead finalizes constitution Part 2 — nothing proceeds
  until done
- **AI-8**: no unresolved `[ASSUMPTION-NNN]` anywhere before `/plan-arch`
- **/validate**: Product Owner + Business Analyst sign-off before
  `/analyze`
- **/clarify**: all items answered, `clarify.summary.md` confirmed
- **/implement**: per-task PR-size check, paired test, "PR ready"
  (github mode) or "Task accepted" (local mode) — wait for human "go"
- **/release**: all tasks merged/accepted, UAT sign-off, go-live
  Go/No-Go across Tech Lead / Product Owner / Ops-SRE

**Takeaway:** This is the single biggest differentiator. spec-kit assumes
one person is driving and trusts them to read the docs. packs-v2 assumes
a *team* with separation of duties — and encodes that separation directly
into the agent's gate logic, so the agent itself enforces "don't proceed
without sign-off," not just a human reviewer after the fact.

---

## 5. Traceability

**spec-kit**: traceability is a *report you generate on demand*.
`/speckit.analyze` produces a "Coverage Summary Table" mapping each
`FR-###`/`SC-###` to the task IDs that implement it (tasks are tagged
`[US1]`, `[US2]`, `[P]` for parallelizable). It's a snapshot, regenerated
whenever you ask.

**packs-v2**: traceability is a *persistent matrix* maintained throughout
the lifecycle: `Story → FR/NFR → Task → TC-NNN (test case) → R-NNN
(risk)`. Every task declares `Satisfies: FR-NNN/NFR-NNN` and `Verifies:
TC-NNN` up front, and `/release` checks these are all closed before
go-live.

**Takeaway:** spec-kit's traceability is great for "show me what's covered
right now." packs-v2's is built for audit — answering "prove every
business requirement maps to a tested, released change" at any point in
the lifecycle, which is what compliance/audit teams typically ask for.

---

## 6. PR & CI Governance

**spec-kit** doesn't model this at all — PR size, review process, and CI
are left entirely to the team's existing git conventions.

**packs-v2** bakes this in:
- `pr_rules` in `manifest.yml`: `max_lines_per_pr` (400),
  `max_files_per_pr` (5) — agent estimates *before* coding and splits
  oversized tasks (SPLIT A/B/C) automatically
- `.github/workflows/quality-gate.yml` — enforces PR size, TASK-NNN/CHG-NNN
  references, build/test/coverage, secret scanning, and SCA on every PR
- **New**: `workflow_mode: github | local` — for teams without GitHub
  access, the agent runs the *same* checks locally and reports
  ✅/❌ per check, ending each task with "Task accepted" instead of
  "PR ready," so the governance model works identically whether or not
  git hosting is available

**Takeaway:** spec-kit assumes you already have PR/CI discipline. packs-v2
provides it out of the box and adapts to teams that don't even have
GitHub access (e.g., business stakeholders working from a shared OneDrive
folder via Claude Desktop).

---

## 7. Where spec-kit Has the Edge

To be fair, a few things spec-kit does better:
- **Portability** — one set of templates designed to behave identically
  across Claude, Copilot, Cursor, Windsurf, etc., with bash/PowerShell
  helper scripts.
- **Lower ceremony** — a solo developer can go idea → working code in
  under an hour with 7 commands and no role setup.
- **`[NEEDS CLARIFICATION]` inline markers** — lighter-weight than a
  separate clarify document; ambiguity is flagged exactly where it occurs
  in the spec.
- **Given/When/Then acceptance scenarios embedded in the spec itself**,
  not deferred to a separate QA-cases document.

These are reasonable enhancements we could selectively borrow into
packs-v2's `srd.md` (FR-### with embedded Given/When/Then,
`[NEEDS CLARIFICATION]` as a complement to `[ASSUMPTION-NNN]`) without
giving up the governance/RACI layer — worth a future, low-risk iteration.

---

## 8. The Pitch

If the audience is **individual developers or small startup teams**:
spec-kit's simplicity is a genuine strength — fewer steps, no roles to
configure, works everywhere.

If the audience is **an enterprise team that needs AI-assisted delivery to
slot into an existing SDLC** — with business sign-off, security review,
named accountable owners, audit-ready traceability, and PR/CI governance
that adapts to teams with or without GitHub access — packs-v2 SDD covers
everything spec-kit does (constitution-driven generation, structured
specs, task breakdown, implementation) *and* adds the governance scaffold
that turns "an AI that writes code from a spec" into "a process an
enterprise can actually adopt and audit."
