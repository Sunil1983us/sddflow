# Pre-Review

Run a one-time code pre-review on the current task's implementation, present a
checklist of findings, apply the developer's chosen fixes, then create the PR.

Runs ONCE per task — do not re-run after fixes are applied.

## Input

Optional: task ID (e.g. TASK-001). If omitted, infer from the current branch name.

## Steps

### 0 — Check config

Read `.specify/integrations.yml`.

If `code_review.enabled: false` or `code_review.pre_review: false`:
> Pre-review is disabled. Running `sdd pr create` directly.

Run `sdd pr create --task {task}` and stop.

### 1 — Identify the task

Extract from branch name if not given (e.g. `feature/task-001-jwt-validation` → `TASK-001`).

### 2 — Get the diff

```bash
git diff $(git merge-base HEAD origin/main)...HEAD
git diff HEAD
```

Read the full content of any file with more than 3 changed hunks.

### 3 — Analyse (6 angles, ≤ 10 findings)

**A Correctness [HIGH]** — null deref, off-by-one, inverted condition, missing
await, wrong variable in copy-paste, error swallowed, falsy-zero misread.

**B Removed behaviour [HIGH]** — for every deleted line name the invariant it
enforced and verify the new code re-establishes it. Deleted guard = candidate.

**C Security [HIGH]** — hardcoded secrets, injection (SQL/cmd/path), unvalidated
input in query or shell, auth check removed, sensitive data logged.

**D Cross-file impact [MEDIUM]** — grep callers of changed signatures; check
for broken call sites, unsatisfied preconditions, unhandled return type changes.

**E Quality [LOW]** — copy-paste with variation, dead code, deeply nested logic,
derivable state stored explicitly.

**F Performance [LOW]** — N+1 query in loop, redundant per-call computation,
blocking I/O on hot path, large closure capturing full enclosing scope.

Drop any finding without a concrete failure scenario. Maximum 10 total.

### 4 — Present checklist

If no findings: "No issues found. Proceeding to PR creation." → skip to step 7.

Otherwise show numbered list with severity, category, file:line, description,
and suggested fix. Ask:

> Which should I fix? Enter numbers (e.g. 1,3), 'all', or 'none':

### 5 — Apply selected fixes

Accept: `all`, `none`, or comma-separated numbers.
Apply all selected fixes at once, then commit:
```
fix(pre-review): address pre-review findings for {TASK-ID}
```

### 6 — Save pre-review summary

Write to `.specify/features/{feature}/.pre-review-{task-id-lowercase}.md`:

```
## Pre-Review Summary — {TASK-ID}

Fixed:
- [1] HIGH bug: <description> (<file>:<line>)

Acknowledged (not fixed):
- [2] MED quality: <description> (<file>:<line>)
```

### 7 — Create the PR

```bash
sdd pr create --task {TASK-ID}
```

The CLI reads the summary file and includes it in the PR body automatically.
