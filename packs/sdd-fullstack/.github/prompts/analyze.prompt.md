---
mode: agent
description: ANALYZE — Risk, dependency, and complexity analysis
---

## Before Starting
Read .specify/manifest.yml
Read .specify/memory/constitution.md
Read .specify/memory/summary-rules.md
Read .specify/features/{manifest.project.feature}/validate.summary.md
Read .specify/features/{manifest.project.feature}/srd.summary.md
Read .specify/features/{manifest.project.feature}/brd.summary.md
Read .specify/templates/analyze-template.md

## Verify Gate
validate.summary.md must exist and state "VALIDATE complete".
If missing or incomplete — STOP. State: "ANALYZE blocked — run /validate
first (business sign-off required)."

## Your Task
Produce a full analysis covering:

RISKS — for every integration, flow, and NFR:
  - Likelihood: Low/Medium/High
  - Impact: Low/Medium/High/Critical
  - Mitigation: concrete action

DEPENDENCIES — internal + external + timeline:
  - What depends on what
  - Which teams own what
  - Blocking vs non-blocking

COMPLEXITY — by feature area and by FR:
  - LOW / MEDIUM / HIGH rating
  - Flag HIGH items — they need SPLIT tasks later

NFR IMPACT — design constraints from NFRs:
  - Which NFRs force architectural decisions
  - SLA budgets, throughput, availability targets

UNKNOWNS — items needing spike work before design:
  - What is not yet known
  - Impact if assumption is wrong

RECOMMENDATION:
  - Suggested approach
  - Items to raise in CLARIFY
  - Tasks likely needing SPLIT (from complexity)

Save to: .specify/features/{manifest.project.feature}/analyze.md
Save summary to: analyze.summary.md (max SUMMARY_MAX_LINES)
Wait for review before CLARIFY.
