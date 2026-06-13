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
| API Style | REST calls / GraphQL / none (static) |
| Messaging/Async | none (SPA has no messaging) |
| Serialisation | JSON always |
| Schema | OpenAPI from backend / none |
| Data Store | none (frontend has no DB) |
| Data Cache | none / localStorage / redux-persist |
| DB Migration | none |
| Configuration | env vars (.env files) |
| Secrets | env vars — never in bundle |
| Resilience | none / retry on fetch |
| Observability | error tracking (Sentry etc) / none |
| Logging | console structured / error boundary |
| Testing | jest / vitest + Testing Library |
| Coverage Gate | extract from context or default 80% |
| Quality/Security | eslint + SAST / none |
| Orchestration | vercel / netlify / docker/nginx / s3 |
| CI/CD | github-actions / gitlab-ci / jenkins / none |

Core Principles → derive from domain:
  Component-First, Accessible, Performant
  + Specification First, Test First, Traceability

Domain Rules → from UX/business rules in context
Never Do → from constraints + add: API calls in components,
           inline styles, console.log in prod, any type

Save constitution.md (Part 1 unchanged)
Report: "Constitution Part 2 generated — review Tech Stack table"

## ACTION 2 — Generate spec documents per scope

pilot:  brd → srd → analyze → hld (component diagram) → ux-flow
mvp+:   + lld → component-spec → accessibility

For each: read matching template → derive from context
Save: {doc}.md + {doc}.summary.md
Templates to use:
  hld → hld-template.md (use component diagram, NOT sequence diagram)
  ux-flow → ux-flow-template.md
  component-spec → component-spec-template.md
  Do NOT use: api-spec-template, data-model-template, resilience-template

List generated + skipped. State: ready for /analyze
