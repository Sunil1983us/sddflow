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

AI-8 check: scan brd.md, srd.md, screen-spec.md, ux-flow.md, api-spec.md,
and security-design.md (whichever exist for this scope) for any remaining
`[ASSUMPTION-NNN]` marker without a matching `<!-- Clarified: {ID} -->`
note. If any remain — STOP. State: "PLAN-ARCH blocked — unresolved
assumptions {list}. Run /clarify first."

## Your Task

### Screen Architecture (NOT hexagonal — mobile pattern)
From context + constitution Part 2 + analyze.summary.md:
- Screen hierarchy and ownership
- Navigation structure (stack / tab / drawer)
- State architecture (global vs local per screen)
- Service layer (API calls + offline sync)
- Offline strategy (queue / cache / conflict resolution)
- Permission request flow
- Platform abstraction layer (iOS vs Android differences)
- Push notification handling
- Risk mitigations from analyze.summary.md applied to design
- NFR → Decision mapping (arch-template §4a) for every NFR in
  analyze.summary.md §5

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

### Refine Scope-Scaled Documents (now that arch.md exists)
These were drafted at /specify from context + srd only; refine them using
arch.md (screen hierarchy, navigation structure, state architecture,
offline strategy):

  mvp+: screen-spec.md, ux-flow.md — align with screen hierarchy and
        navigation structure in arch.md
  mvp+: api-spec.md — align with the service layer / API client contracts
        in arch.md
  all:  security-design.md (§1-2) — align controls with arch.md
        cross-cutting concerns section
  full: data-model.md — align with the local data & cache model (on-device
        storage schema) in arch.md
  full: resilience.md — align with arch.md offline strategy + sync/retry
        approach
  full: investigation.md — align with arch.md flows
  full: security-design.md (§3-4) — align with arch.md cross-cutting
        concerns section

Re-save each updated doc + its .summary.md.

After all saved:
State: "PLAN-ARCH complete — review arch.md + plan.md (and refined
screen-spec/ux-flow/api-spec/data-model/security-design/resilience/
investigation) before PLAN-HLD"
Wait for review.
