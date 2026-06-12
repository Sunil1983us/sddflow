---
mode: agent
description: PLAN-ARCH — Architecture decisions and implementation plan
---

## Before Starting
Read .specify/manifest.yml
Read .specify/memory/constitution.md
Read .specify/memory/summary-rules.md
Read .specify/features/{manifest.project.feature}/clarify.summary.md
Read .specify/features/{manifest.project.feature}/analyze.summary.md
Read all spec .summary.md files
Read .specify/templates/arch-template.md
Read .specify/templates/plan-template.md

## Verify Gate
clarify.summary.md must exist with all items RESOLVED.
If missing — STOP. Ask for CLARIFY to complete first.

## Your Task

### Architecture Document
From context + constitution Part 2 + analyze.md:
- Choose architecture pattern (derived from tech stack)
- Define layers and responsibilities
- Define all ports and adapters
- Map integrations to outbound ports
- List key design decisions with rationale
- Identify cross-cutting concerns (auth, logging, error handling)
- Risk mitigations from analyze.md applied to design

Save: .specify/features/{manifest.project.feature}/arch.md
Save: .specify/features/{manifest.project.feature}/arch.summary.md

### Implementation Plan
From arch.md:
- Layer by layer breakdown
- Class/component names per layer
- Key method signatures
- Implementation order
- Test strategy per layer
- DB migration plan (if applicable)

Save: .specify/features/{manifest.project.feature}/plan.md
Save: .specify/features/{manifest.project.feature}/plan.summary.md

After both saved:
State: "PLAN-ARCH complete — review arch.md + plan.md before PLAN-HLD"
Wait for review.
