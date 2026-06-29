# CLAUDE.md — Universal SDD Pack
# Works for any project type: backend, frontend, mobile, fullstack,
# CLI, data/ML, serverless, library, IaC, desktop
# Command flow:
# SPECIFY → [GATE-1: constitution finalized] → VALIDATE → ANALYZE → CLARIFY
# → PLAN-DESIGN → PLAN-LLD (mvp+) → TASK → IMPLEMENT → RELEASE

## CREATE-CONTEXT — Optional Pre-Phase (before SPECIFY)
If `.specify/contexts/{feature}.md` does not exist yet, or is empty/a
placeholder, offer `/create-context`: the user pastes informal notes (any
format), the agent drafts context.md against context-template.md, lists a
plain-language "Missing Information" checklist, and iterates with the user
until it's ready. See .github/prompts/create-context.prompt.md and
.specify/contexts/CONTEXT-GUIDE.md. Skip this entirely if the user already
has a structured context.md.

## Startup (every session)
1. Read .specify/manifest.yml
2. Read project_type from manifest.yml (or note it is "auto" — resolved during /specify)
3. Read .specify/memory/constitution.md
4. Read .specify/memory/summary-rules.md
5. Read .specify/memory/change-rules.md
6. Read .specify/memory/roles.yml
7. Read .github/instructions/*.instructions.md if any exist — apply each
   file's `applyTo` glob to any file you create or edit that matches it,
   exactly as GitHub Copilot does (AI-7: Claude Code ≡ Copilot parity).
8. Confirm: project.name, scope, feature, context_file, project_type
   - If project_type is "auto" or missing: STOP — state "project_type is not
     resolved. Run /specify first so the correct tech stack and doc set can be
     selected." No other command may proceed until project_type is set.
9. If constitution Part 2 not generated → remind user to run /specify first
10. If constitution Part 2 generated but NOT finalized (GATE-1 open) →
    remind user to review + finalize it before /validate can run

## AI-2 — Summary-First Rule (token economy)
For every command AFTER /specify, read `.summary.md` files for prior
documents. Behaviour is governed by `reading_mode` (set in manifest.yml,
default `auto` from summary-rules.md):
- auto (default): use summary if present; fall back to full doc +
  auto-generate summary if missing
- summary: always use summary; warn if missing (strict token economy)
- full: always read full .md (debugging / initial migration only)
/implement always reads `tasks.md` (current task only) + `constitution.md`
in full regardless of reading_mode.
See .specify/memory/summary-rules.md → AI-2 Reading Mode Decision Tree.

## SPECIFY — Five Sub-Commands

`/specify` generates the constitution only. Spec documents are generated
**one at a time** using dedicated sub-commands — same pattern as `/plan-*`.

| Command | What it generates | Gate |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) + project type | — |
| `/specify-brd` | Business Requirements Document | GATE-1 passed |
| `/specify-uc` | Use Case Specification (Actors + UC-NNN with MP/AP/EP) | BRD approved |
| `/specify-srd` | Software Requirements Document | Use Cases approved |
| `/specify-doc {name}` | Any extended doc (security, api-spec, data-model, component-spec, ux-flow, screen-spec, resilience, investigation) | SRD approved |

> **Note for non-interactive project types** (data-pipeline, cli-tool, batch-processor):
> `/specify-uc` is still required but produces a simplified document — system actors only
> (ACT-NNN type = System or Operator), with Main Path describing the data/command flow rather
> than user interactions. Exception Paths cover failure modes (timeout, data error, partial run).
> Do not force a UI-centric template onto a non-interactive project.

**`/specify` (constitution):**
  Resolve project_type (auto-detect if "auto" or unset)
  Fill Tech Stack table for the detected project_type
  Extract Core Principles, Domain Rules, Never Do
  Save constitution.md Part 2 as DRAFT
  State: "Constitution Part 2 generated — DRAFT. Review and finalize
  every row (GATE-1), then run /specify-brd."

**`/specify-brd` → `brd.md`** — gate: GATE-1 passed
**`/specify-srd` → `srd.md`** — gate: BRD approved
**`/specify-doc security`** → `security-design.md` — gate: SRD approved
**`/specify-doc api-spec`** → `api-spec.md` (mvp+) — gate: SRD approved
**`/specify-doc data-model`** → `data-model.md` (mvp+) — gate: SRD approved
**`/specify-doc {name}`** → any other extended doc — gate: SRD approved

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)
After Action 1, constitution.md Part 2 is a DRAFT.
STOP — the user reviews every row (Tech Stack, Core Principles, Domain
Rules, Never Do), resolves any `[MISSING — ask user]` markers, and may
edit directly. Manual edits are AUTHORITATIVE. The user then tells the
agent: "Constitution Part 2 finalized."
A later /specify re-run must propose changes for review — never silently
overwrite a finalized Part 2.
No /validate, /analyze, or any later command may run until this gate passes.

## Upgrading Scope

To upgrade `pilot → mvp` or `mvp → full` after initial delivery:
1. Update `manifest.yml` → `scope: mvp` (or `full`)
2. Run `sdd review status` to see newly required documents
3. Generate newly required spec docs: `/specify-doc {name}` for each (e.g. data-model, resilience)
4. Generate `/plan-lld` if upgrading from pilot (skipped previously)
5. Append new `CHG-NNN` tasks to `tasks.md` under a new Change Set heading
6. All new documents go through the same review gates as the original spec

Scope upgrade is a **Major amendment** to constitution Part 2 (version bump X.0).

<!-- shared:scope-reference:start -->
## Scope Reference — What Each Scope Produces

| Document / Command | pilot | mvp | full |
|---|---|---|---|
| BRD, Use Cases, SRD | ✅ | ✅ | ✅ |
| `/checklist` | Optional | **Mandatory** | **Mandatory** |
| Security Design | §1 only | §1–2 | §1–4 |
| API Spec (`api-spec.md`) | — | ✅ | ✅ |
| Data Model (`data-model.md`) | — | ✅ | ✅ |
| Resilience (`resilience.md`) | — | — | ✅ |
| Investigation (`investigation.md`) | — | — | ✅ |
| `/plan-lld` | **SKIPPED** | ✅ | ✅ |
| QA Test Cases (`qa-testcases.md`) | **SKIPPED** | ✅ | ✅ |
| Runbook (`runbook.md`) | — | ✅ | ✅ |

**Key skips at `pilot` scope:**
- `/plan-lld` — skipped; go directly from `/plan-design` to `/task`
- QA test cases — `/task` generates stories + tasks only (no `qa-testcases.md`)
- `/checklist` — optional (run for extra quality assurance or skip)
- Security Design stops at §1 (Threat Assessment only; no OWASP/STRIDE/DAST)
- Extended docs (API Spec, Data Model, Resilience, Investigation) — not generated
<!-- shared:scope-reference:end -->

<!-- shared:team-routing:start -->
## Virtual Team — Address by Name

You can address any team member by name — no slash command needed.
They read your message, check the pipeline state, and run the right step automatically.

| Name | Role | Handles |
|---|---|---|
| **Maya** | Business Analyst | BRD, Use Cases, Validate, Context, Change Request |
| **Rex** | Requirements Engineer | SRD, Clarify |
| **Ava** | Software Architect | Analyze, Design, Security, API Spec, Data Model, Resilience |
| **Leo** | Lead Developer | LLD, Implement, Pre-review, Address review, Bug assess, Bug fix |
| **Kai** | Engineering Manager | Tasks, Stories, Export to Jira / GitHub Issues |
| **Quinn** | QA Lead | Spec quality checklist |
| **Riley** | Release Manager | Release planning and go-live |
| **Morgan** | Delivery Manager | Full pipeline orchestration |

**Works three ways — all equivalent:**

```
/maya                                   ← slash command (Claude Code + Copilot)
Maya, create BRD for payments           ← natural language (any AI tool)
"Hey Ava, I need a design for auth"     ← conversational (any AI tool)
```

**Routing rule:** When a name appears at the start of a message or is addressed
directly (e.g. "Maya, …" / "Hey Ava" / "Can Rex clarify"), read and follow
`.github/prompts/{name}.prompt.md` exactly. The prompt file handles context
detection and routes to the correct underlying command automatically.
<!-- shared:team-routing:end -->

## Command Gates
- SPECIFY → [GATE-1] → VALIDATE → ANALYZE → CLARIFY → PLAN-DESIGN
  → PLAN-LLD (mvp+) → TASK → IMPLEMENT → RELEASE
- Each gate requires the previous step complete and reviewed.

## PR Contract
- Estimate before every task.
- If > max_lines_per_pr → SPLIT A/B/C → confirm → one at a time.
- After task: state files + lines + "PR ready" → wait for go.
- If `manifest.workflow_mode = local`: instead of "PR ready", run
  build/test/lint/coverage locally → report ✅/❌ per check → state
  files + lines + "Task accepted" → wait for go.

## Summary
After every doc: write .summary.md (max SUMMARY_MAX_LINES). See AI-2 above.

## Never Do
- Never run /validate before constitution Part 2 finalized (GATE-1)
- Never run /analyze without validate.summary.md
- Never run /plan-design without clarify.summary.md
- Never run /plan-design while any spec doc has an unresolved
  `[ASSUMPTION-NNN]` marker (AI-8)
- Never run /implement without TASK (stories.md + tasks.md) approved
- Never run /release before all tasks are "PR ready" and merged
- Never code before context.md updated
- Never hardcode any value
- Never skip paired test
- Never implement before project_type is resolved in manifest.yml

## PLAN Sub-Commands

PLAN adapts to your `plan_mode` setting in `manifest.yml` (set during `setup.sh`).

**Unified mode (`plan_mode: unified`)** — one combined document, one review gate:
- **`/plan-design`** → `design.md`: Architecture + Diagrams + API Design + ADR entries
  - Gate: clarify.summary.md exists, all RESOLVED; no unresolved [ASSUMPTION-NNN] (AI-8)
  - Review: architect + tech lead + stakeholders
  - Scope: all scopes (pilot, mvp, full)

**Separate mode (`plan_mode: separate`)** — three focused documents, reviewed individually:
- **`/plan-arch`** → `arch.md`: Architecture pattern, layers, key decisions — Step 1 of 3
  - Gate: clarify.summary.md exists, all RESOLVED; no unresolved [ASSUMPTION-NNN] (AI-8)
- **`/plan-hld`** → `hld.md`: System diagrams (C4 context, sequence, state machine) — Step 2 of 3
  - Gate: arch.md approved
- **`/plan-adr`** → `adr.md`: Architecture Decision Records — Step 3 of 3 (mvp+ only; skipped at pilot)
  - Gate: hld.md approved

**Both modes:**
- **`/plan-lld`** → Detailed technical design: class/sequence/package diagrams (mvp+ only; SKIP if pilot)
  - Unified gate: design.md approved
  - Separate gate: adr.md approved (mvp+) or hld.md approved (pilot)

## /checklist — Optional Spec-Quality Gate (after GATE-1, before /validate)

**Mandatory for `mvp` and `full` scope. Optional for `pilot`.**
Run `/checklist` after `/specify` + GATE-1 to catch spec quality issues
before the business sign-off:
- CRITICAL: unresolved [NEEDS CLARIFICATION], unmeasured NFRs, FRs without
  acceptance scenarios — these block /validate
- HIGH: vague adjectives (fast/scalable/secure without a number), UCs without
  Independent Test
- MEDIUM: terminology drift, missing Out of Scope items
Saves to: `.specify/features/{feature}/checklists/{feature}-spec-quality.md`
All CRITICAL items must be resolved before /validate can proceed.

## Document Review Gates (sdd review)

Each SDD document has a Jira-backed review gate. The next document in the phase
cannot be submitted until the current one is approved.

| Phase | Sequence | Reviewer |
|---|---|---|
| specify | BRD → Use Cases → SRD → Design | PO → BA + PO → BA → Architect |
| planning | LLD | Tech Lead |
| tasks | Tasks | Scrum Master |
| release | Runbook → Release | DevOps → Release Manager |

After generating each document, submit it for review:
```bash
sdd review submit --doc brd      # push to Confluence + create Jira review task
sdd review check  --doc brd      # poll: exit 0=approved 1=needs-revision 2=pending
sdd review apply  --doc brd      # re-push after addressing reviewer comments
sdd review status                # full dashboard for all documents
```

When `sdd review check` exits 1 (NEEDS REVISION): read reviewer comments, update
the document, then run `sdd review apply` and ask reviewer to re-review.
Configure reviewers in `.specify/integrations.yml` — see `integrations.yml.example`.

## IMPLEMENT — Code Review Gate

For each task in the `/implement` phase:

1. Write and commit the implementation
2. **Pre-review** (if `code_review.pre_review: true` in integrations.yml — default):
   - Run `/pre-review [TASK-ID]`
   - Agent analyses the diff (correctness, security, quality, performance)
   - Numbered checklist presented — pick which findings to fix
   - Agent applies selected fixes and commits
   - Pre-review summary saved to `.specify/features/{feature}/.pre-review-{task}.md`
3. **Create PR**: `sdd pr create --task TASK-ID`
   - Pre-review summary is included in the PR body automatically
   - If `code_review.pre_review: false`: PR is created directly without pre-review
4. **Human review**: reviewer approves or adds inline comments on the PR
5. **Address comments** (if reviewer requests changes):
   - Run `/address-review [PR-number]`
   - Agent shows unresolved comment threads as a numbered checklist
   - Pick which to fix — agent applies fixes, pushes, replies to threads, requests re-review
   - Repeat per review round until PR is approved
6. PR merged → task complete

## VALIDATE and RELEASE — Bookends

- **`/validate`** → Business sign-off on brd.md + srd.md
  - Gate: GATE-1 (constitution Part 2 finalized)
  - Review: product owner + business analyst
  - Run after: /specify (Action 2) | Gate before: /analyze

- **`/release`** → UAT plan, deployment plan, go-live gate, BO closure
  - Gate: all tasks complete — "PR ready" + merged (github mode) or
    "Task accepted" (local mode)
  - Review: qa lead, product owner, tech lead, devops/sre
  - Run after: /implement (all tasks) | Gate before: go-live

## /orchestrate — Full Pipeline (optional)
Run `/orchestrate` to drive the entire pipeline in one command.
Supports `--list` (status dashboard), `--from STEP` (resume), `--to STEP` (stop early).
Works in CLI (single-session) and multi-agent SDK modes.
See `.github/prompts/orchestrate.prompt.md` for full reference.

## Command Order
/orchestrate  ← runs everything below automatically

— or step by step —
/specify → [GATE-1] → /specify-brd → /specify-uc → /specify-srd → /specify-doc {name}... → /checklist (mandatory mvp+, optional pilot)
→ /validate → /analyze → /clarify → /plan-design
→ /plan-lld (mvp+) → /task → /implement → /release
