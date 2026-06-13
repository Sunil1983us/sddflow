# CLAUDE.md — Mobile Pack
# React Native / Flutter — iOS + Android
# 6-Verb: SPECIFY→ANALYZE→CLARIFY→PLAN→TASK→IMPLEMENT

## Startup
1. Read .specify/manifest.yml
2. Read .specify/memory/constitution.md
3. Read .specify/memory/summary-rules.md
4. Read .specify/memory/change-rules.md
4. Confirm: project.name, scope, feature, context_file

## SPECIFY — Two Actions in Order

Action 1 — Generate constitution.md Part 2 from context:
  Extract tech stack (Language, Framework, Navigation,
  State, Offline Storage, API Style, Testing, Deployment, CI/CD)
  Note: Data Store = device storage, DB Migration = none,
  Orchestration = app store distribution
  Extract Core Principles (offline-first, accessible, performant)
  Extract Domain Rules from mobile UX/business context
  Save updated constitution.md

Action 2 — Generate spec documents per scope:
  pilot:  brd, srd, analyze, hld, ux-flow, screen-spec, plan, tasks, stories, jira
  mvp:    + lld, navigation-spec, adr, qa_cases
  full:   + accessibility, performance-spec

## Mobile Rules (always applied)
Max screen lines: 200
No API calls in screens — service layer only
Assume offline first — sync when connected
Request permissions at point of use — not on startup
Test iOS + Android both

## 6-Verb Gates + PR Contract
Same as all packs — see PROMPT-GUIDE.md

## PLAN Sub-Commands

PLAN is split into 4 sub-commands — each has its own review gate:

/plan-arch  → Architecture decisions + plan.md
              Gate: clarify.summary.md must exist
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

## Command Order
SPECIFY → ANALYZE → CLARIFY → PLAN-ARCH → PLAN-HLD
→ PLAN-LLD (mvp+) → PLAN-ADR (mvp+) → TASK → IMPLEMENT
