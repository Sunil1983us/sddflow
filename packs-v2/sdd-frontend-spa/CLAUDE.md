# CLAUDE.md — Frontend SPA Pack
# React / Vue / Angular — Single Page Applications
# 6-Verb: SPECIFY→ANALYZE→CLARIFY→PLAN→TASK→IMPLEMENT

## Startup
1. Read .specify/manifest.yml
2. Read .specify/memory/constitution.md
3. Read .specify/memory/summary-rules.md
4. Confirm: project.name, scope, feature, context_file
5. If constitution Part 2 not generated → remind user to run SPECIFY first

## SPECIFY — Two Actions in Order

Action 1 — Generate constitution.md Part 2 from context:
  Extract tech stack (Language, Framework, Build Tool,
  Styling, State Management, Testing, E2E, Deployment, CI/CD)
  Note: API Style = component events, Messaging = none,
  Data Store = none (frontend), DB Migration = none
  Extract Core Principles (component-first, accessible, performant)
  Extract Domain Rules from UX/business rules in context
  Save updated constitution.md

Action 2 — Generate spec documents per scope:
  pilot:  brd, srd, analyze, hld, ux-flow, plan, tasks, stories, jira
  mvp:    + lld, component-spec, accessibility, adr, qa_cases
  full:   + storybook-spec, openapi (if BFF)

## Component Rules (always applied)
Max component lines: 150
No API calls in components — service layer only
No inline styles — use project styling solution
Every component has paired test

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
