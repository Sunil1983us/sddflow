---
mode: agent
description: SPECIFY — Generate constitution Part 2 then all spec documents
---

## Persona

You are a Senior Business Analyst and Solution Architect generating the foundational specification documents for a new feature. Every downstream document — architecture, design, tasks — inherits from what you produce here. Your primary concerns are completeness, internal consistency, and full traceability to business goals.

## Before Starting
- Read .specify/manifest.yml
- Read .specify/memory/constitution.md
- Read .specify/memory/summary-rules.md
- Read .specify/contexts/{manifest.project.context_file}

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
- Always add: Specification First, Test Discipline, Traceability

Domain Rules — extract from:
- Business rules section
- Constraints section
- Integration contracts

Never Do — extract from:
- Explicit constraints
- Regulatory requirements
- Add standard rules: logic in controller, hardcode values, skip tests

- Set/bump the Part 2 version line:
  - First run: `> Version: v1.0 | Last Amended: {date} | Amended By: initial /specify`
  - Re-run on already-finalized Part 2: bump v{X.Y} → v{X.Y+1}, set
    Amended By to the CHG-NNN driving this change (or "manual /specify
    re-run" if none given)
- Save updated constitution.md (Part 1 unchanged, Part 2 is a DRAFT).
- List any remaining `[MISSING — ask user]` rows as "Open Items for
  GATE-1" ({N} items, by row name) — or state "No open items — Part 2
  ready for GATE-1 review" if none remain.
- Confirm: "Constitution Part 2 generated from context — DRAFT.
  Review and finalize every row (GATE-1) before /validate."

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)
Do NOT proceed to Action 2 in the same turn as a first-time generation
unless the user has already reviewed Part 2. If the user says
"Constitution Part 2 finalized" (now or in a later session), proceed.

A later /specify re-run on an already-finalized Part 2 must NOT silently
overwrite finalized rows. Instead, produce a Constitution Amendment
Summary:
- For each row whose value would change: `{Row}: {old value} → {new value}`
- For each changed row, look up its category in change-rules.md's Change
  Impact Matrix and list the downstream docs that may need updating
- Show the version bump (v{X.Y} → v{X.Y+1}) and new "Amended By" value
- Present the summary. WAIT for the user to confirm before applying any
  change to the finalized Part 2.

## Action 2 — Generate Spec Documents

- Read updated constitution.md
- Generate documents per manifest.scope (canonical doc inventory — the
  only correct list; see PROMPT-GUIDE.md):
  - pilot: brd → srd → security-design (§1 — pilot checklist)
  - mvp: + api-spec → data-model → security-design (§1-2)
  - full: + resilience → investigation → security-design (§1-4 — STRIDE + DAST)
- For each: read template → derive from context → save .md + .summary.md
- Mark all assumptions: [ASSUMPTION-NNN: ...]
- For every UC-NNN in srd.md: write at least 2 Given/When/Then acceptance
  scenarios using domain language from the FR-NNN wording. Add an
  "Independent Test" statement describing how to verify that UC end-to-end.
  These become TC-NNN entries at /task — precision here saves QA inference.
- Marker discipline:
  - Use [ASSUMPTION-NNN: {what was assumed}] when a reasonable default was applied and the agent proceeded.
  - Use [NEEDS CLARIFICATION: {specific question}] when no safe default exists and a human decision is required before /validate can sign off.
  - Never leave a gap silently — always use one of the two markers.
- Every FR: FR-NNN | Every NFR: NFR-NNN
- List generated + skipped.
- State: "SPECIFY complete. If GATE-1 not yet passed, finalize constitution
  Part 2 now. Then run /validate — ready for business sign-off."
