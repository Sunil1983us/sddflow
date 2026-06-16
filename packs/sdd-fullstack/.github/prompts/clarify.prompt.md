---
mode: agent
description: CLARIFY — Surface ambiguities and get human answers
---

## Before Starting
Read .specify/manifest.yml
Read .specify/memory/constitution.md
Read .specify/memory/summary-rules.md
Read all .specify/features/{manifest.project.feature}/*.summary.md
Read .specify/features/{manifest.project.feature}/analyze.md
Read .specify/templates/clarify-template.md

## Your Task — Generate Questions
Review all spec documents and analysis. Find and document:

AMB-NNN: Ambiguities — anything with two valid interpretations
GAP-NNN: Gaps — information needed for design but not in spec
CON-NNN: Conflicts — two requirements that contradict
ASM-NNN: Assumptions — agent assumed something, needs confirmation
OQ-NNN:  Open questions — human decision needed before design
HR-NNN:  High risks — from analyze.md needing clarification

Rules:
- Every item: unique ID + where found + why it matters for design
- Prioritise HIGH risk items from analyze.md
- Over-clarify is better than under-clarify
- Do NOT start designing — questions only

Save to: .specify/features/{manifest.project.feature}/clarify.md
Present the report. WAIT for human answers.
Do NOT proceed to PLAN until all items answered.

## After Human Fills Answers
Read clarify.md with answers filled in.
Update affected spec documents:
  - Mark changes: <!-- Clarified: {ID} -->
  - Regenerate .summary.md for each updated doc
Write clarify.summary.md — confirm all items RESOLVED.
State: CLARIFY complete — ready for PLAN.
