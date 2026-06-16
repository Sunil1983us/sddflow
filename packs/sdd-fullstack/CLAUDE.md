# CLAUDE.md — Full Stack Pack
# Backend + Frontend together
# 11-Command flow:
# SPECIFY → [GATE-1: constitution finalized] → VALIDATE → ANALYZE → CLARIFY
# → PLAN-ARCH → PLAN-HLD → PLAN-LLD (mvp+) → PLAN-ADR (mvp+) → TASK
# → IMPLEMENT → RELEASE

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
For every command AFTER /specify, read ONLY `.summary.md` files for prior
documents — never re-read full `.md` docs. The one exception is
/implement, which reads `tasks.md` (current task only) + `constitution.md`
in full. See .specify/memory/summary-rules.md.

## SPECIFY — Two Actions in Order

Action 1 — Generate constitution.md Part 2 from context (DRAFT):
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
  every row (GATE-1) before running /validate."

Action 2 — Generate spec documents per scope (canonical doc inventory —
see PROMPT-GUIDE.md):
  pilot:  brd, srd, security-design (§1 — pilot checklist)
  mvp:    + api-spec (Shared API Contract), component-spec, ux-flow,
          data-model (Backend Schema & Persistence Model),
          security-design (§1-2)
  full:   + resilience, investigation, security-design (§1-4)

## Full Stack Rules (always applied)
API contract is source of truth — backend and frontend aligned
OpenAPI spec generated at DELIVER — not after
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

## 11-Command Gates
<!-- shared:command-gates:start -->
- SPECIFY → [GATE-1] → VALIDATE → ANALYZE → CLARIFY → PLAN-ARCH → PLAN-HLD
  → PLAN-LLD (mvp+) → PLAN-ADR (mvp+) → TASK → IMPLEMENT → RELEASE
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
- Never run /plan-arch without clarify.summary.md
- Never run /plan-arch while any spec doc has an unresolved
  `[ASSUMPTION-NNN]` marker (AI-8)
- Never run /implement without TASK (stories.md + tasks.md) approved
- Never run /release before all tasks are "PR ready" and merged
- Never code before context.md updated
- Never hardcode any value
- Never skip paired test
<!-- shared:never-do-core:end -->
- Never let backend or frontend implementation diverge from the agreed
  API contract — api-spec.md is source of truth
- Never exceed class/component size limits (backend 200 lines, frontend
  150 lines) without splitting
- Never ship a cross-layer feature without E2E tests covering both
  layers together

## PLAN Sub-Commands

PLAN is split into 4 sub-commands — each has its own review gate:

/plan-arch  → Architecture decisions + plan.md
              Gate: clarify.summary.md exists, all RESOLVED
              Gate: no unresolved [ASSUMPTION-NNN] in any spec doc (AI-8)
              Also refines (now that arch.md exists): api-spec.md,
              data-model.md (mvp+), security-design.md refinement,
              resilience.md + investigation.md (full) — both layers
              Review: tech lead approves arch + plan

/plan-hld   → HLD + all Mermaid diagrams
              Gate: arch.md reviewed
              Review: stakeholders + tech lead
              Pilot: always run | MVP+: always run

/plan-lld   → LLD + class/sequence diagrams
              Gate: hld.md reviewed
              Scope check: SKIP if pilot — state skip reason
              Review: senior developer

/plan-adr   → Architecture Decision Records
              Gate: arch.md reviewed
              Scope check: SKIP if pilot — state skip reason
              Review: architect

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
SPECIFY → [GATE-1] → VALIDATE → ANALYZE → CLARIFY → PLAN-ARCH → PLAN-HLD
→ PLAN-LLD (mvp+) → PLAN-ADR (mvp+) → TASK → IMPLEMENT → RELEASE
