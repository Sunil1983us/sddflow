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
mvp:    + screen-spec → ux-flow → api-spec (Backend API Contract —
        Consumer) → security-design (§1-2)
full:   + data-model (Local Data & Cache Model) → resilience (Mobile
        Resilience) → investigation (Crash & Incident Triage) →
        security-design (§1-4 — STRIDE + MASVS)

For each: read template → derive from context → save .md + .summary.md
Mark all assumptions: [ASSUMPTION-NNN: ...]
Every FR: FR-NNN | Every NFR: NFR-NNN

Templates to use:
  screen-spec → screen-spec-template.md
  ux-flow → ux-flow-template.md
  api-spec → api-spec-template.md (Backend API Contract — Consumer)
  data-model → data-model-template.md (Local Data & Cache Model)
  resilience → resilience-template.md (Mobile Resilience)
  investigation → investigation-template.md (Crash & Incident Triage)

List generated + skipped.
State: "SPECIFY complete. If GATE-1 not yet passed, finalize constitution
Part 2 now. Then run /validate — ready for business sign-off."
