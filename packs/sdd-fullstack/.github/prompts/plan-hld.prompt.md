---
mode: agent
description: PLAN-HLD — High Level Design with Mermaid diagrams
---

## Before Starting
Read .specify/manifest.yml
Read .specify/memory/constitution.md
Read .specify/memory/summary-rules.md
Read .specify/features/{manifest.project.feature}/arch.summary.md
Read .specify/features/{manifest.project.feature}/analyze.summary.md
Read .specify/templates/hld-template.md

## Verify Gate
arch.md must exist and be reviewed.
If missing — STOP. Run PLAN-ARCH first.

## Your Task
Generate HLD with ALL diagrams in Mermaid.

### Always Include
System Context diagram (C4 Level 1):
  All actors + systems + this service — graph TD

Container/Component diagram (C4 Level 2):
  Internal structure + dependencies — graph TD

Happy Path Sequence diagram:
  Full flow from entry to outcome — sequenceDiagram
  Every service call shown

Status/State Machine (if applicable):
  All states + transitions — stateDiagram-v2

### Include If Applicable
- Component hierarchy (frontend)
- Screen/route flow diagram (frontend)
- Event flow diagram (messaging)
- Deployment diagram (if complex)

### Rules
- Every diagram: Mermaid only — no image files
- Every diagram: title above it
- Happy path only for pilot scope
- All flows for mvp+ scope

Save: docs/hld/hld.md
Save: docs/hld/hld.summary.md (max SUMMARY_MAX_LINES)

State: "PLAN-HLD complete — review hld.md before PLAN-LLD or TASK"
If scope = pilot → state: "Skip PLAN-LLD and PLAN-ADR — proceed to TASK"
Wait for review.
