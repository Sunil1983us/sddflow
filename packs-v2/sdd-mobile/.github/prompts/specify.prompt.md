---
mode: agent
description: SPECIFY — Generate constitution Part 2 then all spec documents
---

## Before Starting
Read .specify/manifest.yml
Read .specify/memory/constitution.md
Read .specify/memory/summary-rules.md
Read .specify/contexts/{manifest.project.context_file}

## Action 1 — Generate Constitution Part 2

Extract from context and fill constitution.md Part 2:

Tech Stack table — extract every concern:
| Concern | Look for in context | If not found |
|---|---|---|
| Language | explicit mention | ask |
| Framework | explicit mention | ask |
| Build Tool | derive from language | Maven(java)/npm(ts)/pip(py) |
| API Style | endpoint formats mentioned | REST if not stated |
| Messaging/Async | integration section | none if not stated |
| Serialisation | message formats | JSON if not stated |
| Schema | ISO/OpenAPI/Proto refs | derive from API style |
| Data Store | database mentioned | ask if not found |
| Data Cache | cache mentioned | none if not stated |
| DB Migration | derive from framework | Flyway(spring)/Alembic(py) |
| Configuration | config server mentioned | env vars if not stated |
| Secrets | secrets approach mentioned | env vars if not stated |
| Resilience | retry/CB mentioned | none (pilot) if not stated |
| Observability | metrics/tracing mentioned | structured logs minimum |
| Logging | log format mentioned | structured JSON |
| Testing | test framework mentioned | derive from language |
| Coverage Gate | NFR section | 80% if not stated |
| Quality/Security | pipeline section | SAST+SCA if not stated |
| Orchestration | deployment mentioned | derive from deployment |
| CI/CD | pipeline mentioned | none if not stated |

Core Principles — derive from domain:
- If payments domain → "Idempotency First"
- If regulated domain → "Compliance First"
- If real-time domain → "Latency Budget"
- Always add: Specification First, Test First, Traceability

Domain Rules — extract from:
- Business rules section
- Constraints section
- Integration contracts

Never Do — extract from:
- Explicit constraints
- Regulatory requirements
- Add standard rules: logic in controller, hardcode values, skip tests

Save updated constitution.md (Part 1 unchanged, Part 2 filled).
Confirm: "Constitution Part 2 generated from context"

## Action 2 — Generate Spec Documents

Read updated constitution.md
Generate documents per manifest.scope:

pilot:  brd → srd → analyze → hld → plan → tasks → stories
mvp:    + lld → adr → qa_cases
full:   + resilience → investigation → security_design

For each: read template → derive from context → save .md + .summary.md
Mark all assumptions: [ASSUMPTION: ...]
Every FR: FR-NNN | Every NFR: NFR-NNN

List generated + skipped. State: ready for ANALYZE.
