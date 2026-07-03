# sddflow (Python) — SDD Framework CLI

Python CLI for the SDD (Spec-Driven Development) Framework.  
Mirrors the Node.js CLI exactly and adds Jira + Confluence integration.

## Install

```bash
pip install sddflow
sdd init
```

**Requirements:** Python ≥ 3.9

For development / contributors:

```bash
git clone https://github.com/sunil1983us/universalguide.git
pip install -e ./universalguide/cli-python
```

---

## Commands

### `sdd init`

Initialize an SDD pack in the current project directory.  
Replaces `bash setup.sh` / `.\setup.ps1`.

```bash
# Interactive (recommended)
sdd init

# Non-interactive
sdd init --project "my-payments-api" \
         --feature "user-authentication" \
         --scope   pilot \
         --type    backend-service
```

| Flag | Description | Default |
|---|---|---|
| `-p, --project <name>` | Project name | prompted |
| `-f, --feature <name>` | First feature name | prompted |
| `-s, --scope <scope>` | `pilot` \| `mvp` \| `full` | prompted |
| `-t, --type <type>` | Project type (auto-detected if omitted) | auto |

---

### `sdd upgrade`

Migrate an existing project's `manifest.yml` to the current pack version.

```bash
sdd upgrade
```

---

### `sdd config init`

Interactive setup wizard — creates `~/.sdd/config.yml` (auth profile) and
`.specify/integrations.yml` (project field mappings).

```bash
sdd config init
```

Walks through:
1. Profile name (e.g. `work-cloud`, `on-prem`)
2. Atlassian base URL
3. Auth mode — see [Auth Modes](#auth-modes) below
4. Credential env var names (never the values themselves)
5. Optionally scaffolds `.specify/integrations.yml`

---

### `sdd config test`

Ping Jira and Confluence to verify credentials are working.

```bash
sdd config test
sdd config test --profile on-prem
```

Output:
```
  ✓  Jira       — connected as Jane Smith
  ✓  Confluence — connected as Jane Smith
```

---

### `sdd config fields`

List all Jira custom field IDs for your instance.  
Use this to find the right IDs for `integrations.yml → custom_fields`.

```bash
sdd config fields
sdd config fields --project MYPROJ
```

Output:
```
  ID                             Name                                     Type
  ─────────────────────────────  ───────────────────────────────────────  ────────────
  customfield_10016              Story Points                             number
  customfield_10021              Acceptance Criteria                      string
  customfield_10100              Team                                     string
```

---

### `sdd jira push`

Create or update Jira issues from `stories.md` and `tasks.md`.  
Hierarchy: **Feature → Story → Task** (configurable issue type names).

> Need Epic and Stories created earlier — before tasks even exist, right after
> BRD/Use Case/SRD approval? Use the agent's `/jira-push` slash command instead
> (per-pack `.specify/scripts/jira-push.py`, config in `.specify/jira-config.yml`).
> It pushes progressively at each SDLC gate (Epic → Story → Task → CHG) rather
> than all at once. See each pack's `HOW-TO-USE.md → Jira & Confluence
> Integration` for a side-by-side comparison.

```bash
sdd jira push
sdd jira push --dry-run          # print plan, no API calls
sdd jira push --feature auth     # override feature name
sdd jira push --profile on-prem  # use a specific auth profile
```

**Dry-run output:**
```
  Would create:
  ┌── [Feature] user-authentication
  │   ├── [Story] STORY-001 — Login with email  (must-have  3sp)
  │   │   └── [Task] TASK-001 — JWT validation
  │   │   └── [Task] TASK-002 — POST /auth/login endpoint
  │   ├── [Story] STORY-002 — Password reset  (should-have  2sp)
  │   │   └── [Task] TASK-003 — Email service integration
```

**Idempotency:** Re-running never creates duplicates. Each issue is tagged
`sdd:STORY-001` / `sdd:TASK-001` as a unique label. On re-run, push searches
by that label — updates if found, creates if not.

**MoSCoW → Jira priority mapping** (configurable in `integrations.yml`):

| SDD MoSCoW | Default Jira priority |
|---|---|
| Must Have | High |
| Should Have | Medium |
| Could Have | Low |
| Won't Have | Lowest |

---

### `sdd jira sync`

Pull Jira issue statuses back and display alongside task IDs.

```bash
sdd jira sync
```

Output:
```
  TASK ID      Jira Key       Status
  ────────────  ──────────────  ────────────────────
  TASK-001      MYPROJ-42      In Progress
  TASK-002      MYPROJ-43      To Do
  TASK-003      —              not pushed
```

---

### `sdd confluence push`

Publish SDD documents to Confluence pages (create or update).

```bash
sdd confluence push                      # push all docs found
sdd confluence push --doc hld            # push one doc only
sdd confluence push --dry-run            # print page titles, no API calls
sdd confluence push --feature auth       # override feature name
sdd confluence push --profile on-prem    # use a specific auth profile
```

**Which docs get pushed:**  
Any `.md` file in `.specify/features/{feature}/` that has a matching key in
`integrations.yml → confluence.page_map`. Missing docs are skipped with a
message.

**Dry-run output:**
```
  would push  Todo API — High-Level Design       ← .specify/features/task-management/hld.md
  would push  Todo API — Architecture Overview   ← .specify/features/task-management/arch.md
  ·  lld.md not found — skipped
```

**Idempotency:** Pages are matched by title in the Confluence space. If a page
with that title already exists, it is updated (version incremented). If not,
it is created under the configured parent page.

---

### `sdd review submit`

Push a document to Confluence and create a Jira review task assigned to the
configured reviewer.

```bash
sdd review submit --doc brd
sdd review submit --doc hld
sdd review submit --doc adr --feature auth
```

What it does:
1. Reads `.specify/features/{feature}/{doc}.md`
2. Converts Markdown → Confluence Storage Format, creates or updates the page
3. Creates (or updates) a Jira task with the label `sdd-doc:{doc}`, assigned to
   the configured reviewer

**Sequence enforcement:** Within each phase, a document cannot be submitted
until its predecessor is approved (e.g. BRD must be approved before SRD can be
submitted). The CLI refuses with a clear message if the predecessor is not yet
approved.

---

### `sdd review check`

Check the review status of a submitted document. Exits with a code the agent
uses to decide the next step.

```bash
sdd review check --doc brd
sdd review check --doc srd --profile on-prem
```

**Exit codes:**

| Code | Meaning | Agent action |
|---|---|---|
| `0` | Approved | Advance to next document / phase |
| `1` | Needs revision | Print comments; agent edits doc, then calls `sdd review apply` |
| `2` | Pending | Waiting for reviewer — do not advance |
| `3` | Not submitted | Run `sdd review submit` first |

**Approval detection:** A document is approved when the Jira task status is in
`approved_statuses` (default: `Done`, `Approved`) **or** any comment contains
a keyword from `approved_keywords` (default: `approved`, `lgtm`, `looks good`,
`go ahead`, `confirmed`).

---

### `sdd review apply`

After the agent addresses reviewer comments, re-push the updated document to
Confluence and notify the reviewer in Jira with a comment.

```bash
sdd review apply --doc brd
```

Typical agent workflow:
```
sdd review check --doc brd          # exit 1: NEEDS_REVISION
# (agent edits .specify/features/{feature}/brd.md)
sdd review apply --doc brd          # re-push + notify reviewer
sdd review check --doc brd          # poll again after reviewer re-reviews
```

---

### `sdd review approve` (no-Jira / chat approvals)

Record an approval locally when Jira is not configured — the agent runs this
automatically after the user says "approved" in chat.

```bash
sdd review approve --doc brd --local --by "Product Owner" --note "approved in chat"
```

What it does:
1. Writes an audit record to `.specify/.local-approvals.yml`
   (`sdd review check` then returns exit 0 for this document)
2. Flips the document header `Status: Draft` → `Status: Approved` if the agent
   has not already done so
3. If a `confluence:` section exists in `.specify/integrations.yml`, updates the
   document's existing Confluence page so it matches the approved `.md`
   (skip with `--no-confluence`; a Confluence failure never blocks the approval —
   re-try with `sdd confluence push --doc {name}`)

The `Status: Approved` header in the `.md` is the authoritative gate in every
mode — Jira and Confluence are integrations on top of it, never a prerequisite.

---

### `sdd review status`

Show the review state of every document in all phases at a glance.

```bash
sdd review status
```

Output:
```
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Review Status
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  SPECIFY phase
    ✓  BRD        Approved            Product Owner
    ✓  SRD        Approved            Business Analyst
    ⏳  ARCH       Pending             Architect
    🔒  HLD        Blocked             Architect

  PLANNING phase
    ·  LLD        Not Submitted       Tech Lead
    ·  ADR        Not Submitted       Architect
```

Blocked = predecessor in the same phase is not yet approved.

---

### `sdd pr create`

Create a git branch and a PR for a task, linked back to its Jira issue — on
**GitHub, GitLab, Bitbucket, or Azure DevOps**. The host is auto-detected from
`git remote get-url origin`; nothing to configure to pick one.

```bash
sdd pr create --task TASK-001
sdd pr create --task TASK-002 --base develop
sdd pr create --task TASK-003 --feature auth
```

What it does:
1. Looks up `TASK-001` in `.specify/features/{feature}/tasks.md`
2. Searches Jira for the issue with label `sdd:TASK-001` (if Jira is configured)
3. Creates and pushes a git branch using `branch_pattern` from `integrations.yml`
4. Detects the git host and creates a PR there with the task description and
   acceptance criteria in the body, linked to the Jira issue:
   - **GitHub** — via the `gh` CLI
   - **GitLab** — via the `glab` CLI, or the REST API if you set `GITLAB_TOKEN`
     instead of installing glab
   - **Bitbucket** — via the REST API, using `BITBUCKET_USERNAME` +
     `BITBUCKET_APP_PASSWORD` (Bitbucket has no CLI as ubiquitous as gh/glab)
   - **Azure DevOps** — via the `az` CLI (`azure-devops` extension)
5. Posts the PR URL as a comment on the Jira task

**Branch / PR title patterns** (configurable in `integrations.yml`, apply to
every host the same way):

| Config key | Default | Example output |
|---|---|---|
| `branch_pattern` | `feature/{task_id}-{slug}` | `feature/task-001-jwt-validation` |
| `pr_title_pattern` | `feat({task_id}): {title}` | `feat(TASK-001): JWT validation` |

**Fallback:** If the detected host's CLI/token isn't set up (or the host isn't
recognized — e.g. self-hosted git), the branch is still created and pushed;
the PR title + body are printed so you can paste them in manually.

**CI on other hosts:** `.github/workflows/quality-gate.yml` (GitHub Actions)
is the reference implementation of the PR-size / TASK-NNN-reference /
build-test-coverage / secret-scan / SCA rules. Each pack also ships
`bitbucket-pipelines.yml`, `.gitlab-ci.yml`, and `azure-pipelines.yml` at the
repo root, mirroring the same rules in that host's native syntax — only the
file matching your actual host is ever read; the others are inert. These are
starter templates like the GitHub one: adjust build/test commands for your
Tech Stack, and verify once against your real pipeline before relying on it.

---

### `/pre-review` (agent command)

Run a one-time code pre-review on the current task before the PR is created.
Controlled by `code_review.pre_review` in `integrations.yml`.

```
/pre-review              # infer task from current branch
/pre-review TASK-001     # explicit task ID
```

**What it does:**
1. Checks `code_review.pre_review` — if `false`, skips and calls `sdd pr create` directly
2. Reads the diff (`git diff main...HEAD`)
3. Analyses for: correctness bugs, removed behaviour, security issues, cross-file impact, quality, performance
4. Presents a numbered checklist to the developer
5. Developer picks which items to fix (`all`, `none`, or `1,3`)
6. Agent applies selected fixes and commits
7. Saves pre-review summary to `.specify/features/{feature}/.pre-review-{task}.md`
8. Calls `sdd pr create --task {task}` — summary is included in the PR body automatically

**Runs once per task** — do not re-run after fixes are applied.

---

### `/address-review` (agent command)

Read unresolved human review comments from a PR, apply developer-selected fixes,
reply to threads, and request re-review. Repeatable — run once per review round.
Works on **GitHub, GitLab, Bitbucket, and Azure DevOps** — same host
auto-detection as `sdd pr create`.

```
/address-review          # infer PR from current branch
/address-review 42       # explicit PR number
```

**What it does:**
1. `sdd pr comments` fetches all unresolved comment threads from the PR
2. Presents them as a numbered checklist
3. Developer picks which to fix
4. Agent applies fixes, commits, pushes to the same branch (PR auto-updates)
5. `sdd pr reply` posts a reply on each thread: "Fixed in {commit}" or "Acknowledged"
6. `sdd pr resolve` resolves fixed threads so reviewer sees a clean diff
7. `sdd pr request-review` requests re-review from the original reviewer

**Run again** after the reviewer adds a new round of comments.
When there are no unresolved comments: "PR is ready to approve."

**Per-host notes:**
- **GitHub** — uses `gh`/GraphQL; unchanged from the original GitHub-only implementation
- **GitLab** — REST API via `GITLAB_TOKEN` (Discussions API)
- **Bitbucket** — REST API via `BITBUCKET_USERNAME`/`BITBUCKET_APP_PASSWORD`.
  Bitbucket has no API-level thread resolution — `sdd pr resolve` posts the
  reply and prints a warning asking the reviewer to resolve it manually in
  the UI; this is expected, not a failure
- **Azure DevOps** — `az` CLI + `az rest` (Threads API)
- **Unrecognized/self-hosted host** — no automated comment handling; address
  review comments directly in the host's web UI

**Underlying commands** (what the prompt calls — usable standalone too):
```bash
sdd pr comments [--pr-id N]
sdd pr reply --comment-id ID --body "..." [--pr-id N]
sdd pr resolve --comment-id ID [--pr-id N]
sdd pr request-review --reviewer LOGIN [--pr-id N]
```

---

## Code Review Configuration

```yaml
# .specify/integrations.yml
code_review:
  enabled:    true
  pre_review: true    # false = skip pre-review, go straight to human review
```

| Setting | Behaviour |
|---|---|
| `pre_review: true` | Agent runs `/pre-review` before creating the PR. PR body includes pre-review summary. |
| `pre_review: false` | PR created immediately. Human reviewer is the first reviewer of the code. |

`/address-review` is always available regardless of `pre_review` setting.

---

## Auth Modes

Credentials are **never stored in config files** — only the name of the
environment variable that holds them.

### `basic` — Atlassian Cloud (email + API token)

```bash
export JIRA_API_TOKEN="your-api-token-here"
```

`~/.sdd/config.yml`:
```yaml
profiles:
  work-cloud:
    auth_mode: basic
    base_url: https://myco.atlassian.net
    email: user@myco.com
    api_token_env: JIRA_API_TOKEN
```

Get your API token: <https://id.atlassian.com/manage-profile/security/api-tokens>

---

### `pat` — Jira/Confluence Server 8.14+ or Data Centre

```bash
export JIRA_PAT="your-personal-access-token"
```

`~/.sdd/config.yml`:
```yaml
profiles:
  on-prem:
    auth_mode: pat
    base_url: https://jira.internal.myco.com
    pat_env: JIRA_PAT
```

---

### `oauth2` — Cloud CI/CD pipelines

```bash
export JIRA_ACCESS_TOKEN="your-oauth2-bearer-token"
```

`~/.sdd/config.yml`:
```yaml
profiles:
  ci:
    auth_mode: oauth2
    base_url: https://myco.atlassian.net
    access_token_env: JIRA_ACCESS_TOKEN
```

---

## Configuration Files

### `~/.sdd/config.yml` — global, machine-level, never commit

Holds named auth profiles. Multiple profiles supported (e.g. one per Atlassian instance).

```yaml
version: "1"
default_profile: work-cloud
profiles:
  work-cloud:
    auth_mode: basic
    base_url: https://myco.atlassian.net
    email: user@myco.com
    api_token_env: JIRA_API_TOKEN
  on-prem:
    auth_mode: pat
    base_url: https://jira.internal.myco.com
    pat_env: JIRA_PAT
```

---

### `.specify/integrations.yml` — project-level, safe to commit

Wires SDD fields to your Jira project and Confluence space.  
Copy from `.specify/integrations.yml.example` and fill in your values.

```yaml
profile: work-cloud     # references a profile in ~/.sdd/config.yml

jira:
  project_key: MYPROJ
  issue_hierarchy:
    feature: Feature    # or "Epic" if your project has no Feature type
    story: Story
    task: Task
  parent_field: parent  # "parent" for next-gen; "customfield_10014" for classic
  base_fields:
    priority_map:
      must-have:   High
      should-have: Medium
      could-have:  Low
      wont-have:   Lowest
    labels: [sdd-generated]
  custom_fields:
    story_points: customfield_10016   # run "sdd config fields" to find yours

confluence:
  space_key: ENG
  parent_page_id: "123456"
  page_map:
    brd:     "My Project — Business Requirements"
    hld:     "My Project — High-Level Design"
    runbook: "My Project — Runbook"
```

Full reference: see `.specify/integrations.yml.example`.

---

## Supported Project Types

Auto-detected by `sdd init` from files in the current directory.

| Type | Detected from |
|---|---|
| `backend-service` | `pom.xml`, `build.gradle`, `go.mod`, Python files |
| `frontend-spa` | `package.json` + react/vue/svelte/angular/next/nuxt |
| `mobile` | `pubspec.yaml`, or `package.json` + react-native/expo |
| `fullstack` | `package.json` + `pom.xml`/`build.gradle`/`go.mod` |
| `cli` | `Cargo.toml` with `[[bin]]`, or `go.mod` + `cmd/` dir |
| `data-ml` | `requirements.txt` with pandas/torch/sklearn/keras/jax |
| `serverless` | `serverless.yml`, or `template.yaml` with AWSTemplateFormatVersion |
| `library` | `Cargo.toml` without `[[bin]]`, or Python lib structure |
| `iac` | `*.tf` files, `Pulumi.yaml`, `cdk.json` |
| `desktop` | `package.json` + electron, or `tauri.conf.json` |

Detection order matches `setup.sh` and `specify.prompt.md` Step 0 — mobile
is always checked before fullstack.
