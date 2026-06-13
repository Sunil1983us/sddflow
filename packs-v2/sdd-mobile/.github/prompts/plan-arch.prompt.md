---
mode: agent
description: PLAN-ARCH — Screen architecture + implementation plan (Mobile)
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

### Screen Architecture (NOT hexagonal — mobile pattern)
From context + constitution Part 2 + analyze.md:
- Screen hierarchy and ownership
- Navigation structure (stack / tab / drawer)
- State architecture (global vs local per screen)
- Service layer (API calls + offline sync)
- Offline strategy (queue / cache / conflict resolution)
- Permission request flow
- Platform abstraction layer (iOS vs Android differences)
- Push notification handling

Save: arch.md + arch.summary.md

### Implementation Plan
From arch.md:
- Feature folder structure
- Screen naming conventions
- Navigation setup
- API service functions
- Offline storage design
- Test strategy (unit → screen → E2E with Detox/integration_test)
- Platform-specific implementation plan

Save: plan.md + plan.summary.md

State: "PLAN-ARCH complete — review arch.md + plan.md before /plan-hld"
Wait for review.
