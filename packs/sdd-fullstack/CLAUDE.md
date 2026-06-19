# CLAUDE.md — Full Stack Pack
# Backend + Frontend together
# Command flow:
# SPECIFY → [GATE-1: constitution finalized] → VALIDATE → ANALYZE → CLARIFY
# → PLAN-DESIGN → PLAN-LLD (mvp+) → TASK → IMPLEMENT → RELEASE

## CREATE-CONTEXT — Optional Pre-Phase (before SPECIFY)
If `.specify/contexts/{feature}.md` does not exist yet, or is empty/a
placeholder, offer `/create-context`: the user pastes informal notes (any
format, covering backend and/or frontend), the agent drafts context.md
against context-template.md (including the Backend / Frontend / Shared
Tech Stack tables), lists a plain-language "Missing Information" checklist,
and iterates with the user until it's ready. See
.github/prompts/create-context.prompt.md and
.specify/contexts/CONTEXT-GUIDE.md. Skip this entirely if the user already
has a structured context.md.

## Startup (every session)
1. Read .specify/manifest.yml
2. Read .specify/memory/constitution.md
3. Read .specify/memory/summary-rules.md
4. Read .specify/memory/change-rules.md
5. Read .specify/memory/roles.yml
<!-- shared:startup-instructions:start -->
6. Read .github/instructions/*.instructions.md — apply each file's
   `applyTo` glob to any file you create or edit that matches it,
   exactly as GitHub Copilot does (AI-7: Claude Code ≡ Copilot parity).
<!-- shared:startup-instructions:end -->
   These model the reference stacks for both layers (constitution Part 2
   → Backend/Frontend Language & Framework rows) — if your stack differs,
   apply each rule's intent using that language's idioms and
   conventions, don't skip it.
7. Confirm: project.name, scope, feature, context_file
<!-- shared:gate1-reminders:start -->
8. If constitution Part 2 not generated → remind user to run /specify first
9. If constitution Part 2 generated but NOT finalized (GATE-1 open) →
   remind user to review + finalize it before /validate can run
<!-- shared:gate1-reminders:end -->

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

## SPECIFY — Four Sub-Commands

`/specify` generates the constitution only. Spec documents are generated
**one at a time** using dedicated sub-commands — same pattern as `/plan-*`.

| Command | What it generates | Gate |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) | — |
| `/specify-brd` | Business Requirements Document | GATE-1 passed |
| `/specify-srd` | Software Requirements Document | BRD approved |
| `/specify-doc {name}` | Any extended doc (security, component-spec, ux-flow, data-model, resilience, investigation) | SRD approved |

**`/specify` (constitution):**
  Extract FULL tech stack for both layers — see constitution.md Part 2
  Tech Stack table (Backend / Frontend / Shared):
  Backend:  Language, Framework, Build Tool, Messaging/Async, Schema,
            Data Store, Data Cache, DB Migration, Resilience, Testing,
            Coverage Gate
  Frontend: Language, Framework, Build Tool, State Management, Component
            Library/Design System, Routing, API Client, Data Cache,
            Testing, Coverage Gate, Accessibility
  Shared:   API Style, Serialisation, Configuration, Secrets,
            Observability, Logging, Quality/Security, Orchestration,
            CI/CD
  Extract Core Principles (API-contract-first, test-first, traceable)
  Extract Domain Rules covering both layers
  Extract Never Do from stated constraints
  Save updated constitution.md — Part 1 unchanged, Part 2 is a DRAFT
  State: "Constitution Part 2 generated — DRAFT. Review and finalize
  every row (GATE-1), then run /specify-brd."

**`/specify-brd` → `brd.md`** — gate: GATE-1 passed
**`/specify-srd` → `srd.md`** — gate: BRD approved
**`/specify-doc component-spec`** → `component-spec.md` (mvp+) — gate: SRD approved
**`/specify-doc ux-flow`** → `ux-flow.md` (mvp+) — gate: SRD approved
**`/specify-doc data-model`** → `data-model.md` (mvp+) — gate: SRD approved
**`/specify-doc security`** → `security-design.md` — gate: SRD approved
**`/specify-doc resilience`** → `resilience.md` (full) — gate: SRD approved
**`/specify-doc investigation`** → `investigation.md` (full) — gate: SRD approved

## Full Stack Rules (always applied)
API contract is source of truth — backend and frontend aligned
API Design locked at /plan-design — design.md (§3 API Design) is source of truth throughout /implement
Backend class max: 200 lines
Frontend component max: 150 lines
Both layers tested independently + E2E together

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)
After Action 1, constitution.md Part 2 is a DRAFT.
STOP — the user reviews every row (Tech Stack, Core Principles, Domain
Rules, Never Do), resolves any `[MISSING — ask user]` markers, and may
edit directly. Manual edits are AUTHORITATIVE. The user then tells the
agent: "Constitution Part 2 finalized."
A later /specify re-run must propose changes for review — never silently
overwrite a finalized Part 2.
No /validate, /analyze, or any later command may run until this gate passes.

## Command Gates
<!-- shared:command-gates:start -->
- SPECIFY → [GATE-1] → VALIDATE → ANALYZE → CLARIFY → PLAN-DESIGN
  → PLAN-LLD (mvp+) → TASK → IMPLEMENT → RELEASE
- Each gate requires the previous step complete and reviewed.
<!-- shared:command-gates:end -->

## PR Contract
<!-- shared:pr-contract:start -->
- Estimate before every task.
- If > max_lines_per_pr → SPLIT A/B/C → confirm → one at a time.
- After task: state files + lines + "PR ready" → wait for go.
<!-- shared:pr-contract:end -->

## Summary
After every doc: write .summary.md (max SUMMARY_MAX_LINES). See AI-2 above.

## Never Do
<!-- shared:never-do-core:start -->
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
<!-- shared:never-do-core:end -->
- Never let backend or frontend implementation diverge from the agreed
  API contract — design.md (§3 API Design) is source of truth
- Never exceed class/component size limits (backend 200 lines, frontend
  150 lines) without splitting
- Never ship a cross-layer feature without E2E tests covering both
  layers together

## PLAN Sub-Commands

PLAN is split into 2 sub-commands — each has its own review gate:

- **`/plan-design`** → Single design document: Architecture + Diagrams + API Design + ADR entries
  - Gate: clarify.summary.md exists, all RESOLVED
  - Gate: no unresolved [ASSUMPTION-NNN] in any spec doc (AI-8)
  - Review: tech lead + architect + stakeholders
  - Scope: all scopes (pilot, mvp, full)

- **`/plan-lld`** → Detailed technical design: class/sequence diagrams (both layers)
  - Gate: design.md reviewed
  - Scope check: SKIP if pilot — state skip reason
  - Review: senior developer

> `design.md` replaces the former arch.md, hld.md, api-spec.md, and adr.md.
> `/plan-arch`, `/plan-hld`, `/plan-adr` redirect to `/plan-design` for backwards compatibility.

## /checklist — Optional Spec-Quality Gate (after GATE-1, before /validate)

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
| specify | BRD → SRD → Arch → HLD | PO → BA → Architect → Architect |
| planning | LLD → ADR | Tech Lead → Architect |
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

/validate   → Business sign-off on brd.md + srd.md
              Gate: GATE-1 (constitution Part 2 finalized)
              Review: product owner + business analyst
              Run after: /specify (Action 2) | Gate before: /analyze

/release    → UAT plan, deployment plan, go-live gate, BO closure
              Gate: all tasks "PR ready" and merged
              Review: qa lead, product owner, tech lead, devops/sre
              Run after: /implement (all tasks) | Gate before: go-live

## Command Order
/specify → [GATE-1] → /specify-brd → /specify-srd → /specify-doc {name}... → /checklist (optional)
→ /validate → /analyze → /clarify → /plan-design
→ /plan-lld (mvp+) → /task → /implement → /release
