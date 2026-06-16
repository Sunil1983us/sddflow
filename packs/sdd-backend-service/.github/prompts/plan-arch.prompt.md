---
mode: agent
description: PLAN-ARCH — Architecture decisions and implementation plan
---

## Before Starting
- Read .specify/manifest.yml
- Read .specify/memory/constitution.md
- Read .specify/memory/summary-rules.md
- Read .specify/features/{manifest.project.feature}/clarify.summary.md
- Read .specify/features/{manifest.project.feature}/analyze.summary.md
- Read all spec .summary.md files
- Read .specify/templates/arch-template.md
- Read .specify/templates/plan-template.md

## Verify Gate
clarify.summary.md must exist with all items RESOLVED.
If missing — STOP. Ask for CLARIFY to complete first.

AI-8 check: scan brd.md, srd.md, api-spec.md, data-model.md, and
security-design.md for any remaining `[ASSUMPTION-NNN]` marker without a
matching `<!-- Clarified: {ID} -->` note. If any remain — STOP. State:
"PLAN-ARCH blocked — unresolved assumptions {list}. Run /clarify first."

## Your Task

### Architecture Document
From context + constitution Part 2 + analyze.summary.md:
- Choose architecture pattern (derived from tech stack)
- Define layers and responsibilities
- Define all ports and adapters
- Map integrations to outbound ports
- List key design decisions with rationale
- Identify cross-cutting concerns (auth, logging, error handling)
- Risk mitigations from analyze.summary.md applied to design

- Save: .specify/features/{manifest.project.feature}/arch.md
- Save: .specify/features/{manifest.project.feature}/arch.summary.md

### Implementation Plan
From arch.md:
- Layer by layer breakdown
- Class/component names per layer
- Key method signatures
- Implementation order
- Test strategy per layer
- DB migration plan (if applicable)

- Save: .specify/features/{manifest.project.feature}/plan.md
- Save: .specify/features/{manifest.project.feature}/plan.summary.md

### Refine Scope-Scaled Documents (now that arch.md exists)
These were drafted at /specify from context + srd only; refine them using
arch.md (ports/adapters, integration mapping, data architecture):

- mvp+: api-spec.md, data-model.md — align with port/adapter contracts
  and entity design in arch.md
- all: security-design.md — align controls with arch.md cross-cutting
  concerns section
- full: resilience.md — align with arch.md integration list
- full: investigation.md — align with arch.md flows

Re-save each updated doc + its .summary.md.

After all saved:
- State: "PLAN-ARCH complete — review arch.md + plan.md (and refined
  api-spec/data-model/security-design/resilience/investigation) before
  PLAN-HLD"
- Wait for review.
