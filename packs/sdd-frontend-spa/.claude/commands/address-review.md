# /address-review

Read all unresolved human review comments from a GitHub PR, present them as a
checklist, apply the developer's chosen fixes, reply to each thread, and
request re-review.

Repeatable — run once per review round until the PR is approved.

## Usage

```
/address-review           # infer PR number from current branch
/address-review 42        # explicit PR number
```

## Step 1 — Find the PR number

If not provided:
```bash
gh pr view --json number --jq '.number'
```

If that fails, ask: "What is the PR number?"

## Step 2 — Fetch unresolved review comments

```bash
gh pr view {number} --json reviews,reviewRequests,comments
gh api repos/{owner}/{repo}/pulls/{number}/comments
```

Collect all comment threads that are **not** resolved.
Group inline comments by file + line.
Include general (non-inline) PR review comments.

If no unresolved comments:
> No open review comments on PR #{number}. PR is ready to approve.
Stop here.

## Step 3 — Present checklist

Print numbered list of unresolved comments grouped by reviewer:

```
  ─────────────────────────────────────────────────────────
  Review Comments — PR #{number}   (@{reviewer}, {date})
  ─────────────────────────────────────────────────────────
  [1] src/auth/login.ts:42  —  @jane
      "This still needs a null check before accessing profile"

  [2] src/auth/login.ts:89  —  @jane
      "Dead variable retryCount is still present"

  [3] General comment  —  @jane
      "Missing unit test for the error path"
  ─────────────────────────────────────────────────────────
  3 comment(s) from @jane

  Which should I fix? Enter numbers (e.g. 1,3), 'all', or 'none':
```

## Step 4 — Apply selected fixes

Wait for developer input. Accept:
- `all`  → fix every comment
- `none` → acknowledge all, fix nothing
- `1,3`  → fix items 1 and 3; acknowledge the rest

For each selected item:
- Read the referenced file at the referenced line
- Apply the fix the reviewer requested
- No per-fix confirmation needed

Commit all fixes together:
```bash
git add <changed files>
git commit -m "fix(review): address PR #{number} review comments"
```

Push to the same branch (PR updates automatically):
```bash
git push
```

## Step 5 — Reply to comment threads

For each **fixed** item, post a reply on the GitHub comment thread:
```bash
gh api repos/{owner}/{repo}/pulls/comments/{comment_id}/replies \
  -f body="Fixed in $(git rev-parse --short HEAD) — {one-line description of the change}"
```

For each **acknowledged** (not fixed) item:
```bash
gh api repos/{owner}/{repo}/pulls/comments/{comment_id}/replies \
  -f body="Acknowledged — will address in a follow-up."
```

## Step 6 — Resolve threads

For each fixed item, resolve the thread so the reviewer sees a clean diff:
```bash
gh api graphql -f query='
  mutation {
    resolveReviewThread(input: {threadId: "{thread_id}"}) {
      thread { isResolved }
    }
  }'
```

If the thread ID is not available from the previous API call, skip resolution —
the reviewer can resolve manually after seeing the reply.

## Step 7 — Request re-review

```bash
gh pr edit {number} --add-reviewer {reviewer_login}
```

If the reviewer login is not known, find it from the comment author field in
Step 2.

Print:
```
  ✓  Fixes committed and pushed.
     Replied to {N} thread(s).
     Re-review requested from @{reviewer}.

  Run /address-review again after they respond.
```
