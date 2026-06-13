---
mode: agent
description: SPECIFY — Generate constitution Part 2 then all spec documents (Frontend SPA)
---

## Before Starting
Read .specify/manifest.yml
Read .specify/memory/constitution.md
Read .specify/memory/summary-rules.md
Read .specify/contexts/{manifest.project.context_file}

## ACTION 1 — Generate constitution.md Part 2

Extract from context and fill Tech Stack table:
| Concern | Look for in context |
|---|---|
| Language | typescript / javascript |
| Framework | react / vue / angular / svelte |
| Build Tool | vite / webpack / next / nuxt |
| State Management | redux / zustand / pinia / context API / signals |
| Component Library/Design System | mentioned UI kit or design system |
| Routing | react-router / vue-router / angular router / file-based |
| API Client | fetch / axios / react-query / apollo / rtk-query |
| Bundler | derive from Build Tool if not separately stated |
| Data Cache | none / localStorage / sessionStorage / IndexedDB / query cache |
| Configuration | env vars (.env files) / runtime config.json |
| Secrets | env vars — never in bundle |
| Resilience | retry on fetch / offline handling / none |
| Observability | error tracking (Sentry/RUM) / none |
| Logging | console structured / error boundary |
| Testing | jest / vitest + Testing Library |
| Coverage Gate | extract from context or default 80% |
| Linting/Formatting | eslint + prettier / none |
| Accessibility | axe-core + WCAG level from context |
| CI/CD | github-actions / gitlab-ci / jenkins / none |
| Hosting/CDN | vercel / netlify / docker+nginx / s3+cloudfront |

If concern not in context → use sensible default
If critical concern missing → mark [MISSING — ask user]

Core Principles — derive from domain:
  Component-First, Accessible, Performant
  + Specification First, Test First, Traceability

Domain Rules → from UX/business rules in context
Never Do → from constraints + add: API calls in components,
           inline styles, console.log in prod, any type

Save updated constitution.md (Part 1 unchanged, Part 2 is a DRAFT).
Confirm: "Constitution Part 2 generated from context — DRAFT.
Review and finalize every row (GATE-1) before /validate."

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)
Do NOT proceed to Action 2 in the same turn as a first-time generation
unless the user has already reviewed Part 2. If the user says
"Constitution Part 2 finalized" (now or in a later session), proceed.
A later /specify re-run on an already-finalized Part 2 must propose
changes for review — never silently overwrite finalized rows.

## ACTION 2 — Generate spec documents per scope

Read updated constitution.md
Generate documents per manifest.scope (canonical doc inventory —
the only correct list; see PROMPT-GUIDE.md):

pilot:  brd → srd → security-design (§1 — pilot checklist)
mvp:    + component-spec → ux-flow → api-spec (Backend API Contract —
        Consumer) → security-design (§1-2)
full:   + data-model (Frontend State & Storage Model) → resilience
        (Frontend Resilience) → investigation (Production Debugging &
        Error Tracking) → security-design (§1-4 — STRIDE + DAST)

For each: read template → derive from context → save .md + .summary.md
Mark all assumptions: [ASSUMPTION-NNN: ...]
Every FR: FR-NNN | Every NFR: NFR-NNN

Templates to use:
  component-spec → component-spec-template.md
  ux-flow → ux-flow-template.md
  api-spec → api-spec-template.md (Backend API Contract — Consumer)
  data-model → data-model-template.md (Frontend State & Storage Model)
  resilience → resilience-template.md (Frontend Resilience)
  investigation → investigation-template.md (Production Debugging &
    Error Tracking)

List generated + skipped.
State: "SPECIFY complete. If GATE-1 not yet passed, finalize constitution
Part 2 now. Then run /validate — ready for business sign-off."
