---
mode: agent
description: PLAN-ARCH — Component architecture + implementation plan (Frontend SPA)
---

## Before Starting
Read .specify/manifest.yml
Read .specify/memory/constitution.md
Read .specify/memory/summary-rules.md
Read .specify/features/{manifest.project.feature}/clarify.summary.md
Read .specify/features/{manifest.project.feature}/analyze.summary.md
Read all spec summaries
Read .specify/templates/arch-template.md
Read .specify/templates/plan-template.md

## Verify Gate
clarify.summary.md must exist with all items RESOLVED.
If missing — STOP. Ask for /clarify to complete first.

## Your Task

### Component Architecture (NOT hexagonal — frontend pattern)
From context + constitution Part 2 + analyze.md:
- Component hierarchy (Page → Container → Presentational)
- State architecture (global store vs local state boundaries)
- Service layer (API calls + data transformation)
- Routing structure
- Shared component library
- Error boundary strategy
- Performance approach (lazy loading, code splitting)

Save: arch.md + arch.summary.md

### Implementation Plan
From arch.md:
- Feature folder structure
- Component naming conventions
- State slice/store design
- API service functions
- Test strategy per layer (unit → component → E2E)

Save: plan.md + plan.summary.md

State: "PLAN-ARCH complete — review arch.md + plan.md before /plan-hld"
Wait for review.
