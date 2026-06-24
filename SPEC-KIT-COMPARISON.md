# SDD Framework (SDD packs) vs. GitHub spec-kit

> A side-by-side comparison of our Spec-Driven Development framework
> (`packs/sdd-*`) against GitHub's open-source `spec-kit` project —
> for evaluating which fits an enterprise SDLC.

---

## TL;DR

| | **GitHub spec-kit** | **SDD Framework** |
|---|---|---|
| Designed for | Individual developer / small team, tool-agnostic | Enterprise teams with formal sign-off chains |
| Commands | 9 — core: `constitution → specify → plan → tasks → taskstoissues → implement`; optional: `clarify`, `analyze`, `checklist` | 13 core (`/specify` → `/release`) + optional `/orchestrate`, `/pre-review`, `/address-review` |
| Spec artifacts per feature | spec.md, plan.md, research.md, data-model.md, tasks.md, checklists/ | BRD, Use Cases, SRD, Security-Design, API Spec, Data Model, Resilience, Design (Arch+HLD+ADR), LLD, Stories, Tasks, QA Cases, Runbook, Release + checklists/{feature}-spec-quality.md |
| Tech stack capture | Per-feature, inside plan.md | Once, in constitution.md Part 2 (20-concern table), GATE-1 finalized |
| Governance / RACI | None | `roles.yml` — every gate has a named accountable role |
| Hard gates | 2 (Constitution Check in plan.md, checklist completeness in implement.md) | Gate at every command transition (GATE-1, /checklist CRITICAL items, validate, AI-8 assumptions, clarify, etc.) |
| Business sign-off | Not modeled | `/validate` — Product Owner + Business Analyst sign-off on BRD/SRD |
| Spec-quality checks | `/speckit.checklist` — on-demand "unit tests for English" for the spec (clarity/completeness/consistency) | `/checklist` — CHK-NNN spec-quality gate (clarity, completeness, consistency, measurability) runs between GATE-1 and /validate; CRITICAL items block /validate |
| Traceability | On-demand, advisory (`/speckit.analyze` — severity-ranked consistency audit across spec/plan/tasks) | Persistent matrix: Story → FR/NFR → Task → TC-NNN → R-NNN |
| Task export | `/speckit.taskstoissues` — tasks.md → GitHub Issues | `/taskstoissues` — tasks.md + stories.md → GitHub Issues markdown + `gh` shell script; `/task` → Jira CSV |
| PR / CI governance | Left to the team's normal git workflow | Built-in `pr_rules` (max lines/files, SPLIT A/B/C), `quality-gate.yml`, and a configurable `workflow_mode: github \| local` |
| Code review | None | `/pre-review` — AI reviews diff before PR (numbered findings, dev picks fixes); `/address-review` — AI addresses human PR comments, replies to threads, requests re-review |
| CLI / setup | `bash scripts/bash/setup.sh` / PowerShell equivalent | `pip install sdd-init` or `npm install -g sdd-init` — interactive wizard: project name, scope, AI tool, scaffolds pack automatically |
| AI tool selection | Tool-agnostic (same prompt works in any AI) | `sdd init` prompts for tool (Claude Code / Copilot / Cursor / Windsurf / Other); saves as `ai_tool` in `manifest.yml`; shows personalized next-step instruction |
| Jira / Confluence | None | `sdd config init/test/fields` → `sdd jira push` / `sdd confluence push`; `sdd review submit/check/apply/status` — Jira-backed stakeholder approval for every SDD document |
| Full pipeline automation | None | `/orchestrate` — drives entire pipeline from a single command; pauses at every human gate; supports `--list`, `--from STEP`, `--to STEP` |
| Portability | Designed to run identically across many AI coding tools | Claude Code (`.claude/commands/`), Copilot (`.github/copilot-instructions.md` + `.github/prompts/`), Cursor, Windsurf (`.windsurfrules`), any AI via copy-paste; `sdd init` selects AI tool interactively |
| Project types | 1 (generic) | 5 packs: backend-service, frontend-spa, mobile, fullstack + `sdd-universal` (auto-detects cli, data-ml, serverless, library, iac, desktop + all 4 above) |
| Bug management | None | `/bug-assess` (BUG-NNN with severity/root-cause/estimate) + `/bug-fix` (regression-test-first fix) |

**Bottom line:** spec-kit is a lean, portable scaffold that turns "vibe
coding" into structured, requirement-driven development for a single
developer. The SDD Framework takes that same idea further — it adds the
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

### packs/sdd-backend-service
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

**Takeaway:** spec-kit produces one cohesive feature folder; SDD packs
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

**SDD Framework's BRD/SRD** spread the same information across two documents:
- BRD: Business Objectives (`BO-NNN`) and Business Requirements (`BR-NNN`)
- SRD: Functional/Non-Functional Requirements (`FR-NNN`/`NFR-NNN`),
  `[ASSUMPTION-NNN]` markers (must all be resolved before `/plan-arch`,
  enforced by the AI-8 gate)

**Takeaway:** spec-kit's single spec.md is *sharper per requirement* —
every FR has Given/When/Then test scenarios baked in from the start.
SDD packs traces the same ideas (BO → BR → FR/NFR) but separates
"why we're building this" (business) from "what it must do"
(functional/non-functional) into documents a Product Owner and a Tech
Lead can review independently — which maps onto how most enterprises
already split business vs. technical sign-off.

---

## 3. Commands & Flow

### spec-kit — 9 commands (6 core + 3 optional)

**Core, in order:**
1. `/speckit.constitution` — generate/update constitution.md
2. `/speckit.specify` — generate spec.md (requirements + user stories)
3. `/speckit.plan` — generate plan.md (tech stack, design, Constitution Check)
4. `/speckit.tasks` — generate tasks.md (T001.., `[P]`/`[US1]` tags)
5. `/speckit.taskstoissues` — export tasks.md → GitHub Issues
6. `/speckit.implement` — execute tasks.md, respecting dependencies/hooks

**Optional, insert where useful:**
- `/speckit.clarify` — before `/plan`; up to 5 targeted questions to resolve
  `[NEEDS CLARIFICATION]` markers in spec.md
- `/speckit.analyze` — after `/tasks`, before `/implement`; read-only
  consistency audit across spec/plan/tasks (advisory)
- `/speckit.checklist` — anytime; generates domain-specific
  requirement-quality checklists (e.g. `ux.md`, `security.md`)

### SDD packs — 13 commands (pilot scope shown)

1. `/specify` — drafts constitution Part 2 (DRAFT)
   — **GATE-1** — manual review/finalize constitution Part 2
2. `/specify-brd` — Business Requirements Document
3. `/specify-uc` — Use Case Specification (Actors + MP/AP/EP)
4. `/specify-srd` — Software Requirements Document
5. `/specify-doc {name}` — extended docs: security, data-model, component-spec, ux-flow, screen-spec, resilience, investigation (scope-dependent)
6. `/checklist` — spec quality gate (mandatory mvp+, optional pilot)
7. `/validate` — business sign-off on BRD + Use Cases + SRD
8. `/analyze` — risk/complexity + consistency audit
9. `/clarify` — resolve open questions
10. `/plan-design` — Architecture + Diagrams + API Design + ADRs (all scopes)
    `/plan-lld` — detailed class/sequence design (mvp+ only)
11. `/task` — Feature → Story → Task + Jira CSV
12. `/implement` — one task at a time, PR rules enforced
    `/pre-review` — AI code review before PR; numbered findings → dev picks fixes
    `/address-review` — address human PR comments; fix, reply, resolve threads
13. `/release` — UAT + deployment + go-live gate

**Optional:** `/orchestrate` — drives the full pipeline automatically from a single command; pauses at every human gate; supports `--list`, `--from STEP`, `--to STEP`.

**Takeaway:** spec-kit's core path is 6 steps with 3 optional add-ons a
developer can skip entirely. SDD Framework's steps are *not* optional — each
maps to a phase an enterprise SDLC already requires (business validation,
risk analysis, architecture review, formal release/go-live) and each has
a named owner in `roles.yml`.

---

## 4. Gates: Advisory vs. Mandatory

**spec-kit** has exactly two *hard* stops:
1. `plan.md`'s "Constitution Check" — re-verified after design, fails the
   run with an `ERROR` if violated.
2. `implement.md` refuses to proceed if items in `checklists/` are
   unresolved.

Everything else is recommended but skippable — there's no concept of
"who" approves a step:
- `/speckit.clarify` — optional, can be skipped entirely
- `/speckit.analyze` — produces a severity-ranked findings table
  (CRITICAL/HIGH/MEDIUM/LOW); only CRITICAL findings (constitution
  violations) get a "resolve before implement" note — everything else
  the user "may proceed" past
- `/speckit.checklist` — generates quality checklists but doesn't itself
  block anything (the *items it creates* feed implement.md's checklist
  check, #2 above)

**SDD packs** treats *every* command transition as a gate, each mapped to
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
one person is driving and trusts them to read the docs. SDD packs assumes
a *team* with separation of duties — and encodes that separation directly
into the agent's gate logic, so the agent itself enforces "don't proceed
without sign-off," not just a human reviewer after the fact.

---

## 5. Traceability

**spec-kit**: traceability is a *report you generate on demand*.
`/speckit.analyze` is a read-only cross-artifact audit of
spec.md/plan.md/tasks.md — checking for duplication, ambiguity,
underspecification, constitution conflicts, coverage gaps (FR/SC not
covered by any task), and terminology drift. It produces a severity-ranked
findings table; it's a snapshot, regenerated whenever you run it, and is
not persisted as a requirement→task map. Tasks carry `[US1]`/`[US2]`/`[P]`
labels for which user story / parallelizability, which `/analyze` uses to
spot coverage gaps.

**SDD packs**: traceability is a *persistent matrix* maintained throughout
the lifecycle: `Story → FR/NFR → Task → TC-NNN (test case) → R-NNN
(risk)`. Every task declares `Satisfies: FR-NNN/NFR-NNN` and `Verifies:
TC-NNN` up front, and `/release` checks these are all closed before
go-live.

**Takeaway:** spec-kit's traceability is great for "show me what's covered
right now, and what's inconsistent." SDD Framework's is built for audit —
answering "prove every business requirement maps to a tested, released
change" at any point in the lifecycle, which is what compliance/audit
teams typically ask for.

---

## 6. PR & CI Governance

**spec-kit** doesn't model this at all — PR size, review process, and CI
are left entirely to the team's existing git conventions.

**SDD packs** bakes this in:
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

**Takeaway:** spec-kit assumes you already have PR/CI discipline. SDD packs
provides it out of the box and adapts to teams that don't even have
GitHub access (e.g., business stakeholders working from a shared OneDrive
folder via Claude Desktop).

---

## 7. CLI Setup & Enterprise Integration — Jira / Confluence

**spec-kit** has no CLI and no integration with issue tracking or documentation platforms. Setup is manual (copy templates, fill in yaml) and all artifact storage relies on the team's git workflow.

**SDD Framework** ships a full CLI (`sdd`) and an enterprise integration layer:

### Installation & Setup

```bash
pip install sdd-init          # or: npm install -g sdd-init
sdd init                      # interactive wizard: project name, scope, AI tool
                              # → copies the right pack, fills manifest.yml, done
```

`sdd init` prompts for 5 things: project name, scope (pilot/mvp/full), feature name, project type, and which AI tool you'll use (Claude Code / GitHub Copilot / Cursor / Windsurf / Other). It then scaffolds the correct pack into your project and outputs a personalized "what to do next" message matched to your AI tool.

### Jira & Confluence Connection

```bash
sdd config init               # interactive wizard → ~/.sdd/config.yml
export JIRA_API_TOKEN=...     # Cloud: email + token; Server: JIRA_PAT; CI: JIRA_ACCESS_TOKEN
sdd config test               # pings Jira + Confluence → reports ✓ or ✗ per service
sdd config fields --project MYPROJ   # discover custom field IDs
```

Auth modes: `basic` (Jira Cloud — email + API token), `pat` (Jira Server/DC — personal access token), `oauth2` (CI/CD — access token).

### Pushing Artifacts

```bash
sdd jira push                 # push stories + tasks → Jira issues
sdd jira push --dry-run       # preview without creating issues
sdd confluence push --doc brd # publish one SDD document to Confluence
sdd confluence push --all     # publish all SDD documents
```

### Stakeholder Review Workflow

After each document is generated, submit it for formal sign-off:

```bash
sdd review submit --doc brd   # push to Confluence + create Jira review task
sdd review check  --doc brd   # poll: exit 0=approved 1=needs-revision 2=pending
sdd review apply  --doc brd   # re-push after addressing reviewer comments
sdd review status             # full dashboard across all documents and phases
```

Review sequence is enforced: BRD → Use Cases → SRD → Design → LLD → Tasks → Runbook → Release. Each document must be approved before the next can be submitted. When `sdd review check` exits 1 (needs revision), the agent reads reviewer comments, updates the document, runs `sdd review apply`, and asks the reviewer to re-review.

**Takeaway:** spec-kit assumes the team already manages Jira and Confluence separately from the AI tool. SDD Framework brings the AI tool *into* that workflow — every spec doc is pushed to Confluence automatically, every review becomes a Jira task with a named reviewer, and the agent won't advance to the next phase until the current document is approved in Jira.

---

## 8. Where spec-kit Has the Edge

To be fair, a few things spec-kit does better:
- **Portability (first mover)** — one set of templates designed to behave
  identically across Claude, Copilot, Cursor, Windsurf, etc., from day one.
  SDD now matches this via `.github/prompts/` portable prompt files + `sdd init`
  AI tool selection — but spec-kit was there first.
- **Lower ceremony** — a solo developer can go idea → working code in
  under an hour with 6 core commands and no role setup.
- **`[NEEDS CLARIFICATION]` inline markers** — lighter-weight than a
  separate clarify document; ambiguity is flagged exactly where it occurs
  in the spec.
- **Given/When/Then acceptance scenarios embedded in the spec itself**,
  not deferred to a separate QA-cases document.
- **`/speckit.checklist`** — "unit tests for English": generates
  domain-specific checklists (`ux.md`, `security.md`, etc.) that test the
  *spec's* clarity/completeness/consistency before any code is written —
  catching ambiguity earlier and cheaper than a downstream review gate.
- **`/speckit.analyze`** — a one-command, severity-ranked consistency
  audit across spec/plan/tasks (duplication, ambiguity, coverage gaps,
  constitution conflicts, terminology drift) — useful as a quick health
  check at any point.
- **`/speckit.taskstoissues`** — one command to turn tasks.md into GitHub
  Issues, native to teams already living in GitHub.

All items selectively borrowed into SDD packs — now fully implemented:

**HIGH priority (implemented earlier):**
- ✅ `/checklist` — CHK-NNN spec-quality gate with Clarity/Completeness/Consistency/Measurability; CRITICAL items block /validate
- ✅ Given/When/Then acceptance scenarios — embedded in each UC in srd.md; drives TC-NNN traceability
- ✅ `[NEEDS CLARIFICATION: ...]` — lighter-weight complement to `[ASSUMPTION-NNN]`; blocks /validate if unresolved
- ✅ `/speckit.analyze` cross-artifact consistency — §8 Consistency Findings (CF-NNN) in /analyze

**MEDIUM priority (now implemented):**
- ✅ `/taskstoissues` — tasks.md + stories.md → GitHub Issues markdown + `gh` shell script
- ✅ `/bug-assess` + `/bug-fix` — structured BUG-NNN assessment + regression-test-first fix workflow
- ✅ `WHY-SDD.md` — philosophy doc in every pack (benefits, objections, who it's for)
- ✅ Story MoSCoW priority — Must/Should/Could/Won't Have grouping in stories.md output

**Phase 1 — Universal tool portability (implemented):**
- ✅ Cursor adapter (`.cursor/rules/sdd-framework.mdc`)
- ✅ Windsurf adapter (`.windsurfrules`)
- ✅ `setup.sh` / `setup.ps1` one-command initializers
- ✅ `QUICKSTART.md` per pack + Tool Compatibility table in PROMPT-GUIDE.md

**Phase 2 — Universal pack (now implemented):**
- ✅ `sdd-universal` pack — single entry point for all 10 project types
- ✅ Auto-detect project type from project files (package.json, pom.xml, Cargo.toml, *.tf, etc.)
- ✅ Per-type tech stack tables in `/specify` (10 types × complete concern rows)
- ✅ Per-type doc-set table (pilot/mvp/full × 10 types)

**Phase 3 — CLI, AI tool selection & enterprise integration (now implemented):**
- ✅ `sdd init` Python CLI (`pip install sdd-init`) + Node.js CLI (`npm install -g sdd-init`)
- ✅ AI tool selection in `sdd init` (claude-code / copilot / cursor / windsurf / other); stored as `ai_tool` in `manifest.yml`; personalized Done message per tool
- ✅ `sdd config init` / `sdd config test` / `sdd config fields` — Jira + Confluence connection wizard, connectivity test (✓/✗ per service), custom field discovery
- ✅ `sdd jira push` — push stories + tasks → Jira issues (with `--dry-run` and `--feature` flags)
- ✅ `sdd confluence push` — publish SDD documents to Confluence (`--doc`, `--all`)
- ✅ `sdd review submit/check/apply/status` — Jira-backed stakeholder approval workflow; enforces review sequence; revision handling with re-push
- ✅ `/specify-brd`, `/specify-uc`, `/specify-srd`, `/specify-doc {name}` — SPECIFY split into 5 sub-commands (one document at a time)
- ✅ `/plan-design` — replaces `/plan-arch` + `/plan-hld` + `/plan-adr` (single design document)
- ✅ `/pre-review` — AI code review before PR; numbered findings → dev picks which to fix
- ✅ `/address-review` — address human PR comments; fix, reply to threads, request re-review
- ✅ `/orchestrate` — full pipeline driver; supports `--list`, `--from STEP`, `--to STEP`; works in single-session and multi-agent SDK modes
- ✅ Per-pack HOW-TO-USE.md — tailored per pack: pack-specific templates, extended docs, tech stack, AI tool usage guide, Jira/Confluence integration steps

---

## 9. The Pitch

If the audience is **individual developers or small startup teams**:
spec-kit's simplicity is a genuine strength — fewer steps, no roles to
configure, works everywhere.

If the audience is **an enterprise team that needs AI-assisted delivery to
slot into an existing SDLC** — with business sign-off, security review,
named accountable owners, audit-ready traceability, and PR/CI governance
that adapts to teams with or without GitHub access — the SDD Framework covers
everything spec-kit does (constitution-driven generation, structured
specs, task breakdown, implementation) *and* adds the governance scaffold
that turns "an AI that writes code from a spec" into "a process an
enterprise can actually adopt and audit."
