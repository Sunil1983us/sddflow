---
mode: agent
description: IMPLEMENT — Execute one task at a time with PR rules enforced
---

## Before Starting
Read .specify/manifest.yml
Read .specify/memory/constitution.md
Read .specify/features/{manifest.project.feature}/tasks.md

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
- Write paired test alongside implementation — never after
- No class / component over max_class_lines

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
Generate delivery artifacts per manifest.scope:
  openapi   → docs/openapi.yaml
  qa_cases  → docs/qa/functional-test-cases.md
  runbook   → docs/runbook/local-setup.md
