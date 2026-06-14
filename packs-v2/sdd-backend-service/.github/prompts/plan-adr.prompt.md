---
mode: agent
description: PLAN-ADR — Architecture Decision Records
---

## Before Starting
- Read .specify/manifest.yml
- Read .specify/memory/constitution.md
- Read .specify/features/{manifest.project.feature}/arch.summary.md
- Read .specify/features/{manifest.project.feature}/analyze.summary.md
- Read .specify/templates/adr-template.md

## Scope Check
If manifest.scope = pilot → STOP.
State: "PLAN-ADR skipped — pilot scope. Proceed to TASK."

## Verify Gate
arch.md must exist and be reviewed.

## Your Task
Generate one ADR per key architectural decision (start from arch.md §4
"Key Design Decisions" — every DEC-NNN row).

### What Qualifies as an ADR
- Pattern choice (hexagonal, layered, event-driven)
- Technology choice where alternatives existed
- Integration approach (sync vs async)
- Data store choice
- Deployment strategy
- Security approach
- Any decision from analyze.md marked HIGH risk

### Each ADR Contains
- Context: why was this decision needed?
- Options: at least 2 alternatives considered
- Decision: what was chosen and why
- Consequences: positive + negative + risks

### Naming
- ADR-001-{kebab-case-title}.md
- ADR-002-{kebab-case-title}.md
- ...

- Save each: docs/architecture/adr/ADR-{NNN}-{title}.md
- Save index: docs/architecture/decisions.md
- Update arch.md §4 — fill the ADR column for each DEC-NNN now covered.

- State: "PLAN-ADR complete — {N} ADRs generated. Ready for TASK."
- Wait for review.
