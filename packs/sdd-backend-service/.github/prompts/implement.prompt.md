---
mode: agent
description: IMPLEMENT — Execute one task at a time with PR rules enforced
---

## Before Starting
- Read .specify/manifest.yml
- Read .specify/memory/constitution.md
- Read .specify/features/{manifest.project.feature}/tasks.md

## Verify Gate
Confirm tasks.md and stories.md have been approved.
If not — STOP and ask for TASK approval first.

## Your Task
Execute ONE task at a time. Never batch.

### Before Writing Any Code
1. State the task: TASK-{NNN} — {title}
2. Estimate total lines
3. If estimate > manifest.pr_rules.max_lines_per_pr:
   - Show SPLIT plan: TASK-{NNN}-A, B, C...
   - State what each sub-task covers + estimated lines
   - WAIT for confirmation before starting
4. If within limit:
   - State: "Estimated {N} lines — within limit — proceeding"

### While Writing
- Follow constitution Part 1 (universal rules)
- Follow constitution Part 2 (tech stack + domain rules)
- No class / component over max_class_lines
- Apply testing style from manifest.testing_style (default: paired):

  **paired** — Write test and implementation together; neither goes first.
  Both must be in the same PR. Never defer tests to a later task.

  **tdd** — Red-Green-Refactor per acceptance criterion:
  1. Write a failing test that captures the criterion exactly.
  2. Run it — confirm it fails for the right reason.
  3. Write minimum code to make it pass — no more.
  4. Run again — confirm green.
  5. Refactor only while tests stay green.
  Never write implementation before a failing test exists.

  **bdd** — Given/When/Then per acceptance criterion:
  1. Write a Given/When/Then spec using domain language from srd.md.
  2. Translate spec into a runnable test — confirm it fails.
  3. Implement exactly what the spec describes — no more.
  4. Confirm test passes.
  Spec language must match FR-NNN wording in srd.md.

### After Writing
- List every file changed
- State total lines added
- Confirm each acceptance criterion: ✅ {criterion text}
- If manifest.workflow_mode == "local":
  - Run build + test + lint + coverage commands locally (per
    constitution Part 2 Tech Stack) — report ✅/❌ for each
  - State: "Task accepted — {N} lines, {N} files"
- Else (github):
  - State: "PR ready — {N} lines, {N} files"
- WAIT for "go" before starting next task

### After All Tasks
Generate delivery artifacts per manifest.project.scope:
- qa_cases (mvp+) → docs/qa/functional-test-cases.md — finalize
  .specify/features/{manifest.project.feature}/qa-testcases.md (per
  qa-testcases-template.md) with pass/fail results from the paired tests
- runbook (mvp+) → docs/runbook/local-setup.md (per runbook-template.md)
- openapi (full) → docs/openapi.yaml (per openapi-template.md, from
  api-spec.summary.md)
