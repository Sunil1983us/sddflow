# /pre-review

Run a one-time code pre-review on the current task's implementation, present a
checklist of findings, apply the developer's chosen fixes, then create the PR.

Runs ONCE per task — do not re-run after fixes are applied.

## Usage

```
/pre-review              # infer task from branch name
/pre-review TASK-001     # explicit task ID
```

## Step 0 — Check config

Read `.specify/integrations.yml`:

- If `code_review.enabled: false` **or** `code_review.pre_review: false`:
  > Pre-review is disabled (`code_review.pre_review: false`).
  > Running `sdd pr create` directly.

  Run `sdd pr create --task {task}` and stop.

## Step 1 — Identify the task

If no task ID was given, extract from the current branch name:
```bash
git branch --show-current
```
Pattern: `feature/{task-id}-{slug}` → task ID is the segment before the first `-`
after `feature/` up to and including the issue number (e.g. `task-001` → `TASK-001`).

If still unclear, ask: "Which task is this for? (e.g. TASK-001)"

## Step 2 — Get the diff

```bash
git diff $(git merge-base HEAD origin/main)...HEAD
git diff HEAD
```

For any file with more than 3 changed hunks, read the full file — partial
context misses bugs in unchanged lines adjacent to the diff.

## Step 3 — Analyse (6 angles, ≤ 10 findings total)

### A — Correctness  [HIGH]
Off-by-one, null/undefined deref before check, inverted condition, missing
`await`, wrong variable in copy-paste, error swallowed in catch, falsy-zero
treated as "not set".

### B — Removed behaviour  [HIGH]
For every deleted or replaced line: name the invariant it enforced, then
check whether the new code re-establishes it. Deleted guard = candidate.

### C — Security  [HIGH]
Hardcoded secrets or tokens, SQL/command/path injection, unvalidated external
input used in a query or shell call, auth check removed or bypassed, sensitive
data written to logs.

### D — Cross-file impact  [MEDIUM]
For changed function signatures, grep callers. Does any call site break?
New precondition not satisfied? Changed return type not handled upstream?

### E — Quality  [LOW]
Copy-paste with slight variation, dead code left behind, deeply nested logic
that could be flattened, state that is derivable rather than stored.

### F — Performance  [LOW]
N+1 query inside a loop, redundant computation per call, blocking I/O on a
hot path, large closure that captures the full enclosing scope.

Drop any finding without a concrete failure scenario.

## Step 4 — Present checklist

If no findings:
> No issues found. Proceeding to PR creation.
Skip to Step 7.

Otherwise print:

```
  ─────────────────────────────────────────────────────
  Pre-Review — {TASK-ID}
  ─────────────────────────────────────────────────────
  [1] HIGH  bug       src/auth/login.ts:42
      Null deref: user.profile accessed before null check
      Fix: add  if (!user.profile) return res.status(400)...

  [2] HIGH  security  src/auth/login.ts:67
      SQL injection: query built with string concat
      Fix: use parameterised query  db.query('...', [input])

  [3] MED   quality   src/auth/login.ts:89
      Dead variable: retryCount set but never read
      Fix: remove the variable

  [4] LOW   perf      src/users/list.ts:23
      N+1 query: findUser() called inside a loop
      Fix: batch with  findUsers([ids])
  ─────────────────────────────────────────────────────
  4 finding(s) — 2 high · 1 medium · 1 low

  Which should I fix? Enter numbers (e.g. 1,3), 'all', or 'none':
```

## Step 5 — Apply selected fixes

Wait for developer input. Accept:
- `all`   → fix every finding
- `none`  → acknowledge all, fix nothing
- `1,3`   → fix items 1 and 3; acknowledge the rest

Apply all selected fixes at once — no per-fix confirmation needed.

Commit:
```bash
git add <changed files>
git commit -m "fix(pre-review): address pre-review findings for {TASK-ID}"
```

## Step 6 — Save pre-review summary

Read feature name from `.specify/manifest.yml` → `project.feature`.
Write to `.specify/features/{feature}/.pre-review-{task-id-lowercase}.md`:

```markdown
## Pre-Review Summary — {TASK-ID}

Fixed:
- [1] HIGH bug: null deref on user.profile (login.ts:42)
- [2] HIGH security: SQL injection via string concat (login.ts:67)

Acknowledged (not fixed):
- [3] MED quality: dead variable `retryCount` (login.ts:89)
- [4] LOW perf: N+1 query in user list (list.ts:23)
```

If developer chose `none`: list all under "Acknowledged (not fixed)".
If no findings: write `No issues found in pre-review.`

## Step 7 — Create the PR

```bash
sdd pr create --task {TASK-ID}
```

The CLI reads the summary file and includes it in the PR body automatically.
