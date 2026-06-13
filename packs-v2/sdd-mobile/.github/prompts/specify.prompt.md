---
mode: agent
description: SPECIFY — Generate constitution Part 2 then all spec documents (Mobile)
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
| Language | typescript (RN) / dart (Flutter) |
| Framework | react-native / flutter |
| Build Tool | metro / flutter build |
| API Style | REST / GraphQL — consumed not owned |
| Messaging/Async | push notifications / websocket / none |
| Serialisation | JSON always |
| Schema | OpenAPI from backend / none |
| Data Store | async-storage / hive / sqflite / realm / none |
| Data Cache | in-memory / device storage |
| DB Migration | none (device storage) |
| Configuration | env vars / .env / app.config.js |
| Secrets | secure storage — never in bundle |
| Resilience | retry on network failure / offline queue |
| Observability | crash reporting (Sentry/Crashlytics) |
| Logging | structured — no sensitive data |
| Testing | jest + detox (RN) / flutter_test + integration_test |
| Coverage Gate | extract from context or default 80% |
| Quality/Security | eslint / dart analyze + SAST |
| Orchestration | app-store / play-store / expo / testflight |
| CI/CD | github-actions / fastlane / bitrise / none |

Core Principles → derive from domain:
  Offline-First, Accessible, Cross-Platform, Performant
  + Specification First, Test First, Traceability

Domain Rules → from mobile UX/business rules in context
Never Do → from constraints + add: API calls in screens,
           hardcode platform checks, permissions on startup,
           any type (RN), mutable state in widgets (Flutter)

Save constitution.md (Part 1 unchanged)
Report: "Constitution Part 2 generated — review Tech Stack table"

## ACTION 2 — Generate spec documents per scope

pilot:  brd → srd → analyze → hld (screen flow) → ux-flow → screen-spec
mvp+:   + lld → navigation-spec → accessibility

For each: read matching template → derive from context
Templates to use:
  hld → hld-template.md (use screen flow diagram, NOT service sequence)
  ux-flow → ux-flow-template.md
  screen-spec → screen-spec-template.md
  Do NOT use: api-spec-template, data-model-template,
              arch-template (no hexagonal for mobile), resilience-template

List generated + skipped. State: ready for /analyze
