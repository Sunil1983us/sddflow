# CLAUDE.md — Full Stack Pack
# Backend + Frontend together
# 6-Verb: SPECIFY→ANALYZE→CLARIFY→PLAN→TASK→IMPLEMENT

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

## Startup
1. Read .specify/manifest.yml
2. Read .specify/memory/constitution.md
3. Read .specify/memory/summary-rules.md
4. Read .specify/memory/change-rules.md
4. Confirm: project.name, scope, feature, context_file

## SPECIFY — Two Actions in Order

Action 1 — Generate constitution.md Part 2 from context:
  Extract FULL tech stack for both layers:
  Backend: Language, Framework, Data Store, Cache, Messaging,
           DB Migration, Resilience, CI/CD, Deployment
  Frontend: UI Framework, Styling, State, Testing, E2E
  Shared: API Style, Serialisation, Observability, Secrets
  Extract Core Principles (API-contract-first, test-first, traceable)
  Extract Domain Rules covering both layers
  Save updated constitution.md

Action 2 — Generate spec documents:
  pilot:  brd, srd, analyze, arch, hld, data-model, api-spec,
          ux-flow, plan, tasks, stories, jira, openapi
  mvp:    + lld, component-spec, adr, qa_cases, runbook
  full:   + resilience, security-design, accessibility

## Full Stack Rules (always applied)
API contract is source of truth — backend and frontend aligned
OpenAPI spec generated at DELIVER — not after
Backend class max: 200 lines
Frontend component max: 150 lines
Both layers tested independently + E2E together

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
