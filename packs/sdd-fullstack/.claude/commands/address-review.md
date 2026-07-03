# /address-review

Read all unresolved human review comments on the current PR, present them as a
checklist, apply the developer's chosen fixes, reply to each thread, and
request re-review. Works on GitHub, GitLab, Bitbucket, and Azure DevOps — the
`sdd pr` commands below auto-detect which host this repo is on.

Repeatable — run once per review round until the PR is approved.

## Usage

```
/address-review           # infer PR number from current branch
/address-review 42        # explicit PR number
```

## Step 1 — Fetch unresolved review comments

```bash
sdd pr comments [--pr-id {number}]
```

This prints a numbered checklist directly — grouped implicitly by file:line,
with each comment's author, text, and the `comment_id` needed for later steps.

If it fails (missing host credentials, or a host with no automated listing),
the error message names exactly what's missing (e.g. `GITLAB_TOKEN`,
`BITBUCKET_USERNAME`/`BITBUCKET_APP_PASSWORD`). Tell the user, then offer to
continue manually: read the comments from the host's web UI and proceed from
Step 3 using whatever ids that UI shows.

If no unresolved comments:
> No open review comments on PR #{number}. PR is ready to approve.
Stop here.

## Step 2 — Present checklist

Relay the checklist `sdd pr comments` printed, e.g.:

```
  ─────────────────────────────────────────────────────────
  Review Comments — PR #{number}   (GitHub)
  ─────────────────────────────────────────────────────────
  [1] src/auth/login.ts:42  —  @jane  (comment_id=123)
      "This still needs a null check before accessing profile"

  [2] src/auth/login.ts:89  —  @jane  (comment_id=124)
      "Dead variable retryCount is still present"

  [3] General comment  —  @jane  (comment_id=125)
      "Missing unit test for the error path"
  ─────────────────────────────────────────────────────────
  3 comment(s)

  Which should I fix? Enter numbers (e.g. 1,3), 'all', or 'none':
```

## Step 3 — Apply selected fixes

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

## Step 4 — Reply to comment threads

For each **fixed** item (using its `comment_id` from Step 1):
```bash
sdd pr reply --comment-id {comment_id} \
  --body "Fixed in $(git rev-parse --short HEAD) — {one-line description of the change}"
```

For each **acknowledged** (not fixed) item:
```bash
sdd pr reply --comment-id {comment_id} \
  --body "Acknowledged — will address in a follow-up."
```

## Step 5 — Resolve threads

For each fixed item:
```bash
sdd pr resolve --comment-id {comment_id}
```

Bitbucket has no API-level thread resolution today — the command prints a
warning and the reviewer resolves it manually after seeing the reply. Treat
that warning as expected, not a failure to retry.

## Step 6 — Request re-review

```bash
sdd pr request-review --reviewer {reviewer_login}
```

If the reviewer's login isn't known, use the comment author field from Step 1.

Print:
```
  ✓  Fixes committed and pushed.
     Replied to {N} thread(s).
     Re-review requested from @{reviewer}.

  Run /address-review again after they respond.
```
