# CLAUDE.md — Mobile Pack
# React Native / Flutter — iOS + Android
# 11-Command flow:
# SPECIFY → [GATE-1: constitution finalized] → VALIDATE → ANALYZE → CLARIFY
# → PLAN-ARCH → PLAN-HLD → PLAN-LLD (mvp+) → PLAN-ADR (mvp+) → TASK
# → IMPLEMENT → RELEASE

## Startup (every session)
1. Read .specify/manifest.yml
2. Read .specify/memory/constitution.md
3. Read .specify/memory/summary-rules.md
4. Read .specify/memory/change-rules.md
5. Read .specify/memory/roles.yml
6. Read .github/instructions/*.instructions.md — apply each file's
   `applyTo` glob to any file you create or edit that matches it,
   exactly as GitHub Copilot does (AI-7: Claude Code ≡ Copilot parity)
7. Confirm: project.name, scope, feature, context_file
8. If constitution Part 2 not generated → remind user to run /specify first
9. If constitution Part 2 generated but NOT finalized (GATE-1 open) →
   remind user to review + finalize it before /validate can run

## AI-2 — Summary-First Rule (token economy)
For every command AFTER /specify, read ONLY `.summary.md` files for prior
documents — never re-read full `.md` docs. The one exception is
/implement, which reads `tasks.md` (current task only) + `constitution.md`
in full. See .specify/memory/summary-rules.md.

## SPECIFY — Two Actions in Order

Action 1 — Generate constitution.md Part 2 from context (DRAFT):
  Read context file → extract all tech decisions
  Fill Tech Stack table (Language/Framework, Navigation,
  State Management, Local Storage/DB, API Client, Push
  Notifications, Crash/Analytics, Build Tool, Testing,
  Coverage Gate, Quality/Security, CI/CD, App Store Distribution,
  plus the remaining backend-style concerns adapted for mobile —
  see constitution.md Part 2 Tech Stack table)
  Extract Core Principles from domain constraints
  (Offline-First, Accessible, Cross-Platform, Performant)
  Extract Domain Rules from mobile UX/business rules
  Extract Never Do from stated constraints
  Save updated constitution.md — Part 1 unchanged, Part 2 is a DRAFT
  State: "Constitution Part 2 generated — DRAFT. Review and finalize
  every row (GATE-1) before running /validate."

Action 2 — Generate spec documents per scope:
  pilot:  brd, srd, security-design (§1 — pilot checklist only)
  mvp:    + screen-spec, ux-flow, api-spec (Backend API Contract —
          Consumer), security-design (§1-2)
  full:   + data-model (Local Data & Cache Model), resilience (Mobile
          Resilience), investigation (Crash & Incident Triage),
          security-design (§1-4 — STRIDE + MASVS)

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
SPECIFY → [GATE-1] → VALIDATE → ANALYZE → CLARIFY → PLAN-ARCH → PLAN-HLD
→ PLAN-LLD (mvp+) → PLAN-ADR (mvp+) → TASK → IMPLEMENT → RELEASE
Each gate requires the previous step complete and reviewed.

## PR Contract
Estimate before every task.
If > max_lines_per_pr → SPLIT A/B/C → confirm → one at a time.
After task: state files + lines + "PR ready" → wait for go.

## Summary
After every doc: write .summary.md (max SUMMARY_MAX_LINES). See AI-2 above.

## Never Do
Never run /validate before constitution Part 2 finalized (GATE-1)
Never run /analyze without validate.summary.md
Never run /plan-arch without clarify.summary.md
Never run /plan-arch while any spec doc has an unresolved
  `[ASSUMPTION-NNN]` marker (AI-8)
Never run /implement without TASK (stories.md + tasks.md) approved
Never run /release before all tasks are "PR ready" and merged
Never code before context.md updated
Never hardcode any value
Never skip paired test
Never make API calls directly in screens — service layer only
Never assume connectivity — assume offline first, sync when connected
Never request permissions on startup — request at point of use

## PLAN Sub-Commands

PLAN is split into 4 sub-commands — each has its own review gate:

/plan-arch  → Screen/app architecture decisions + plan.md
              Gate: clarify.summary.md exists, all RESOLVED
              Gate: no unresolved [ASSUMPTION-NNN] in any spec doc (AI-8)
              Also generates (now that arch.md exists): screen-spec.md,
              ux-flow.md, api-spec.md (mvp+), data-model.md (full),
              security-design.md refinement, resilience.md +
              investigation.md (full)
              Review: tech lead approves arch + plan

/plan-hld   → HLD + all Mermaid diagrams (screen flow + navigation)
              Gate: arch.md reviewed
              Review: stakeholders + tech lead + ux lead
              Pilot: always run | MVP+: always run

/plan-lld   → LLD + class/component + sequence diagrams
              Gate: hld.md reviewed
              Scope check: SKIP if pilot — state skip reason
              Review: senior developer (mobile)

/plan-adr   → Architecture Decision Records
              Gate: arch.md reviewed
              Scope check: SKIP if pilot — state skip reason
              Review: architect

### Refine Scope-Scaled Documents (at /plan-arch)
screen-spec.md and ux-flow.md are drafted at /specify from
srd.summary.md, then refined at /plan-arch using arch.summary.md
(navigation structure, state architecture, offline strategy).
api-spec.md (mvp+) and data-model.md (full) follow the same
draft-then-refine pattern.

## VALIDATE and RELEASE — Bookends

/validate   → Business sign-off on brd.md + srd.md
              Gate: GATE-1 (constitution Part 2 finalized)
              Review: product owner + business analyst
              Run after: /specify (Action 2) | Gate before: /analyze

/release    → UAT plan, store-release plan, go-live gate, BO closure
              Gate: all tasks "PR ready" and merged
              Review: qa lead, product owner, tech lead, devops/sre
              Run after: /implement (all tasks) | Gate before: go-live

## Command Order
SPECIFY → [GATE-1] → VALIDATE → ANALYZE → CLARIFY → PLAN-ARCH → PLAN-HLD
→ PLAN-LLD (mvp+) → PLAN-ADR (mvp+) → TASK → IMPLEMENT → RELEASE
