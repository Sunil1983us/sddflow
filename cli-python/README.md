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

**This only ever touches `manifest.yml`'s `sdd_version` field.** Fixes made
to prompt file *content* (`.github/prompts/*.md`, `.claude/commands/*.md`)
after your project was scaffolded do **not** reach an existing project just
by running `sdd upgrade` or upgrading the `sddflow` package — those files
were copied into your project once, at `sdd init` time, and nothing
re-syncs them automatically. For that, use `--sync-prompts`:

```bash
sdd upgrade --sync-prompts              # preview + confirm, then re-copy
sdd upgrade --sync-prompts --yes        # skip the confirmation prompt
sdd upgrade --sync-prompts --pack sdd-backend-service   # override pack detection
```

Which pack to sync from is resolved, in order: `--pack` flag →
`manifest.yml`'s `pack` field (written automatically by `sdd init` on
every new project) → inferred from `project_type` → `sdd-universal` as a
last resort. If it had to guess, it says so and tells you to pass `--pack`
if the guess is wrong — projects scaffolded before this field existed
won't have `pack` recorded, so double-check the inference on those.

Every file about to be overwritten is shown first (and left alone if you
say no); anything actually overwritten is backed up to
`.specify/.prompt-sync-backups/{timestamp}/` first, so a project with
hand-edited prompt files never just loses those edits silently. Only
`.github/prompts/` and `.claude/commands/` are touched — nothing under
`.specify/` (templates, constitution, your generated docs) is ever synced
by this command.

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
4. **Credential storage** — system keychain (recommended) or environment
   variable, see [Credential Storage](#credential-storage) below
5. Optionally scaffolds `.specify/integrations.yml`

---

### `sdd config set-secret`

Store or rotate a credential in the system keychain for a profile that
already uses `credential_store: keyring`.

```bash
sdd config set-secret --profile work-cloud
```

Prompts for the new value (masked input) and updates the keychain entry —
no need to re-run the whole `sdd config init` wizard just to rotate a
token. For env-var profiles, just export the new value in your shell
instead; this command only touches keychain-stored credentials.

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

Create or update Jira issues from `brd.md`, `stories.md`, and `tasks.md`.  
Hierarchy: **Feature/Epic → Story → Task** (configurable issue type names).

By default pushes everything at once. Use `--level` to push progressively at
each SDLC gate instead — Epic right after `/specify` (the `epic-bootstrap-step`
in `specify.prompt.md` already runs this automatically, before any spec doc
exists), Stories after Use Case/SRD approval, Tasks after `/task`, CHG tasks
after `/change` — matching what the agent's `/jira-push` slash command does
(it's a thin wrapper around this same command). Parent links for a level
pushed on its own are found live via Jira labels, so there's no strict
ordering requirement.

```bash
sdd jira push                          # push Feature/Epic + Story + Task
sdd jira push --level epic             # normally already run by /specify
sdd jira push --level uc-draft         # normally already run by /specify-uc
sdd jira push --level story            # after /specify-uc or /specify-srd
sdd jira push --level task             # after /task
sdd jira push --level chg --cr CR-001  # after /change
sdd jira push --dry-run          # print plan, no API calls
sdd jira push --feature auth     # override feature name
sdd jira push --profile on-prem  # use a specific auth profile
```

**`--level uc-draft`** creates one lightweight placeholder Story per
`UC-NNN` in `use-cases.md` — issue type Story (not Task), parented to the
Epic — right after `/specify-uc`, before `stories.md` exists. It's
separate from `--level all`/`--level story`, not part of either: a later
`--level story` push finalizes the *same* issue in place for any story
whose `**Derived from:** UC-NNN` field names one of these drafts (same
idempotency label, `sdd:{feature}:UC-NNN`), instead of creating a second,
separate issue for the same use case. Stories with no single-UC origin
just get a normal new Story issue, exactly as before this existed.

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
with a feature-qualified label (`sdd:{feature}:STORY-001`, `sdd-feature:{feature}`
for the top-level Feature/Epic) — feature-qualified so two features' STORY-001
never collide on a multi-feature project. On re-run, push searches by that
label — updates if found, creates if not.

**Keys tracking:** each push also writes a best-effort, human-readable summary
to `docs/jira/{feature}/keys.yml` — for reference only; it is never read back
by `sdd jira push` itself, since parent-linking and idempotency are always
re-derived live from the Jira labels above.

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

**Page hierarchy:** every page nests under `parent_page_id` → a Project page
(named after `manifest.yml`'s project name) → a Feature page (named after
the active feature) — both created automatically and idempotently the first
time any doc is pushed. Living/service-level docs (`data-model`,
`security-design`, `api-spec`, `component-library`, `runbook`) nest directly
under the Project page instead, since they're shared across every feature.

This nesting is purely a navigation convenience, not a namespace — Confluence
enforces page-title uniqueness **per space**, not per parent page, so two
features' same-titled pages would still collide even nested under different
Feature pages. That's why `page_map`/`document_reviews.confluence_page`
templates keep `{feature}` in the title text; don't remove it just because
nesting exists.

---

### `sdd review submit`

Push a document to Confluence and create a Jira review story (issue type
Story, parented to the feature's Epic — same hierarchy level as dev
Stories) assigned to the configured reviewer.

```bash
sdd review submit --doc brd
sdd review submit --doc hld
sdd review submit --doc adr --feature auth
```

What it does:
1. Reads `.specify/features/{feature}/{doc}.md`
2. Converts Markdown → Confluence Storage Format, creates or updates the page
3. Ensures a Feature/Epic issue exists for the project — normally already
   created by `/specify` before any spec document exists (see `sdd jira push
   --level epic` below); self-bootstrapped here too as a fallback, refreshed
   with the BRD's Business Objectives if they weren't available yet — and
   creates (or updates) a Jira **Story** with the label
   `sdd-doc:{feature}:{doc}`, parented under that Epic and assigned to the
   configured reviewer

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

**No `jira:` section configured?** `sdd review check` falls back to
dashboard-left comments (`.specify/.dashboard-comments.json`, written by
`sdd dashboard`'s comment box) instead of returning "not submitted" outright —
any not-yet-acknowledged comment for that doc is printed and the command
exits `1`, exactly like the Jira NEEDS REVISION path. This is the only way
review feedback reaches the agent in pure local mode: a dashboard comment has
no Jira ticket to poll, and (unlike Confluence-configured setups where it
mirrors to Jira automatically) there's nothing else watching for it.

---

### `sdd review apply`

After the agent addresses reviewer comments, re-push the updated document to
Confluence and notify the reviewer in Jira with a comment — or, in pure local
mode (neither `jira:` nor `confluence:` configured), acknowledge the
dashboard comments that triggered the edit so `sdd review check` stops
repeating them.

```bash
sdd review apply --doc brd
```

Typical agent workflow:
```
sdd review check --doc brd          # exit 1: NEEDS_REVISION
# (agent edits .specify/features/{feature}/brd.md)
sdd review apply --doc brd          # re-push + notify reviewer (or: ack local comments)
sdd review check --doc brd          # poll again after reviewer re-reviews
```

---

### `sdd review comments`

Read or acknowledge dashboard-left comments directly, without going through
the full check/apply cycle. `sdd review check`/`sdd review apply` already
call into this in pure local mode (see above) — this command exists for
explicit/manual use.

```bash
sdd review comments --doc brd              # list unacknowledged comments (exit 1 if any, 0 if none)
sdd review comments --doc brd --ack        # mark every current comment as addressed
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
    ⏳  ARCH       Pending             Architect         · ask Ava
    🔒  HLD        Blocked             Architect

  PLANNING phase
    ·  LLD        Not Submitted       Tech Lead          · ask Leo
    ·  ADR        Not Submitted       Architect          · ask Ava
```

Blocked = predecessor in the same phase is not yet approved. Any row that
isn't Approved or Blocked gets a `· ask {name}` hint naming the Virtual
Team member who owns that doc type (same roster the dashboard uses) — a
doc key with no mapped persona (rare — only the handful outside
`CLAUDE.md`'s "Virtual Team" table) just omits the hint.
**Requires Jira** (`integrations.yml` with a `jira:` section) — for a
status view that works with any review mode (chat, local, or jira), see
`sdd dashboard` below.

---

### `sdd dashboard`

A local, read-only web UI over the current project's `.specify/` —
pipeline progress per feature, task completion, and token usage. Unlike
`sdd review status`, it needs no Jira/Confluence configuration: it reads
the `Status:` headers already written into each doc's `.md` file, which
are the authoritative gate in every review mode.

```bash
sdd dashboard                  # starts a local server, opens your browser
sdd dashboard --port 5050      # use a different port
sdd dashboard --no-open        # don't auto-open a browser tab
sdd dashboard --host 0.0.0.0   # let teammates on the same network reach it (see below)
```

Shows, per feature under `.specify/features/`:
- **Full Pipeline** — the *complete* command sequence for this project's
  scope and plan mode (`/specify` → `GATE-1` → `/specify-brd` → ... →
  `/release`), not just the docs generated so far. Every step is shown,
  including ones this scope/plan mode skips (struck through, hover for
  why — e.g. "skipped — pilot scope"), so you can see the whole shape of
  the workflow up front. Each step is marked **✓ done**, **● current**
  (either awaiting review or in progress), or **○ upcoming**, and a
  highlighted **Next** box below the stepper spells out exactly what to
  run next in plain language (e.g. "Run `/specify-uc` to generate the Use
  Case Specification" or `"BRD" is generated and waiting on review — check
  with sdd review check --doc brd`). This is derived purely from
  `manifest.yml` (`scope`, `plan_mode`) and each doc's `Status:` header —
  no extra configuration needed.
  - **Virtual Team persona hints.** Any step owned by a named team member
    (see CLAUDE.md's "Virtual Team — Address by Name" table: Maya, Rex,
    Ava, Leo, Kai, Quinn, Riley) shows that name as a small badge on the
    step and in its hover tooltip, and the **Next** box adds a second
    line with a ready-to-type natural-language ask —
    e.g. `💬 Or just say: "Maya, write the use cases for checkout"
    (Maya — Business Analyst)` — so you don't need to look up which
    slash command a step maps to. Steps that run before any persona
    takes over (`/specify`, `GATE-1`) or that are a byproduct of another
    command (the runbook, generated by `/implement`) have no persona
    badge. A doc that already exists and is just awaiting review skips
    the ask too — the phrasing is always creation-oriented ("create the
    BRD"), which would misleadingly suggest the doc doesn't exist yet.
    sdd-micro has no Virtual Team, so none of this ever appears there.
- **Documents** — every generated doc and its `Status:` (Draft/Approved/etc.), with a best-effort "what's next" guess, including the same persona ask shown on the Full Pipeline's Next box when the next doc has an owner. Each doc has a **View** button that reads the raw `.md` straight from disk into the page — no need to leave the browser to check content.
- **Tasks** — parsed from `tasks.md` (works with both the full packs' checkbox-based tasks and sdd-micro's `**Status:**` field)
- **Token Usage** — the running totals from `token-usage.md`, if token usage logging is enabled for that feature
- **Jira Export** — the Epic/Story/Task links from the progressive export (`docs/jira/{feature}/keys.yml`), if you've run `/jira-push` or `sdd jira push`

It's a viewer only — nothing here writes to `.specify/`. The page polls
`/api/status` every 5 seconds, so it reflects new commands as the agent
runs them. Task/PR status reflects `tasks.md`, not live PR state on your
git host (that would require its own credentials/API calls per host —
out of scope for this command).

**Jira/Confluence links** come in two tiers:
- **Local, instant, always shown** — Jira Epic/Story/Task links (from
  `docs/jira/{feature}/keys.yml`) and Confluence page links for docs
  pushed via `sdd confluence push`/`draft` (from
  `.specify/.confluence-drafts.json`). Pure file reads, no network call.
- **Live, on demand** — click **"🔄 Check Jira/Confluence review links"**
  on a feature to look up that feature's `sdd review submit` tickets
  (these aren't cached anywhere locally, unlike the progressive export).
  This one call uses your existing `~/.sdd/config.yml` profile and
  `.specify/integrations.yml` — same credentials as `sdd review status`,
  and only fires when you click the button, never on the automatic poll.
  The same check also surfaces each document's review status — a
  color-coded **APPROVED / NEEDS REVISION / PENDING** badge next to its
  Jira pill, using the exact same classification `sdd review check --doc`
  uses — and, if the reviewer left any, their Jira comments show up in
  that document's comments panel (💬), labeled separately from local
  dashboard comments. Needs `document_reviews` configured in
  `integrations.yml`, same as `sdd review check` itself.

**Approve a document, or leave a review comment** — right from the
Documents card, no need to open a CLI or Jira/Confluence yourself:
- **Approve** flips that doc's `Status:` header to `Approved` and records
  who/when/why in `.specify/.local-approvals.yml` — the exact same file
  and format `sdd review approve --local` already uses, so the CLI and
  the dashboard share one audit trail. If Confluence is configured, the
  approved doc is mirrored to its page automatically (same as the CLI
  command); if Jira is configured, a best-effort comment ("Approved via
  SDD Dashboard by {name}") is posted to that document's review-gate
  ticket. Neither Confluence nor Jira failing blocks the local approval.
- **Comments** (💬 button) save locally to
  `.specify/.dashboard-comments.json`, scoped per feature+document, and
  also post to Jira the same way, if configured. Confluence comment
  posting isn't implemented yet (only page content sync on approve).
- **Known limitation:** `.local-approvals.yml` is keyed by document name
  only, not by feature — this matches `sdd review approve`/`review
  check`'s own existing format. On a multi-feature project, approving
  "brd" doesn't distinguish which feature's BRD you meant at the
  `sdd review check` layer (dashboard comments *are* feature-scoped,
  since that's a new store with no legacy format to match).
- **Jira only gets a comment, not a status transition.** Actually moving
  the Jira ticket's workflow status (e.g. to Done) would need the Jira
  transitions API, which isn't wrapped in this codebase — approve via
  the dashboard the same way `sdd review approve --local` does: locally
  first, Jira/Confluence as a mirror, not the source of truth.

**Sharing with a team.** By default the server only listens on
`127.0.0.1` — just you. `--host 0.0.0.0` lets teammates on the same
network open it from their own browser at your machine's IP (the CLI
prints that URL). This is still one process on one machine, not a hosted
service — it stops when you close the terminal, and it's unauthenticated,
so only use it on a network you trust: it exposes your project's
`.specify/` status to anyone who can reach the port, **and** lets them
approve documents and post comments on your behalf. No credentials pass
through it either way — Jira/Confluence auth stays server-side, using
your own `~/.sdd/config.yml`.

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

## Credential Storage

Independent of which [auth mode](#auth-modes) you use, `~/.sdd/config.yml`
never contains a plaintext secret — only *where* to find one, via
`credential_store`:

| `credential_store` | Where the secret actually lives | Works from |
|---|---|---|
| `keyring` *(recommended)* | OS-native secure store — macOS Keychain, Windows Credential Manager, Linux Secret Service, via the [`keyring`](https://pypi.org/project/keyring/) package | Any terminal, any AI tool's subprocess, any new shell — no setup needed after the initial save |
| `env` | An environment variable you export yourself | Only the shell session where you exported it (and its children) |

**Why this matters in practice:** an AI coding tool (Claude Code, Copilot,
etc.) runs shell commands in its own subprocess, which does **not**
inherit an env var you exported in a different terminal tab — even a
brand-new terminal tab won't have it unless you added the `export` to a
shell startup file the tool's subprocess actually sources (which varies
by tool and isn't always `~/.zshrc`/`~/.bashrc`). This is a common source
of "Jira/Confluence not connecting" reports that turn out to be nothing
wrong with the credential itself. `credential_store: keyring` sidesteps
the whole problem — the OS keychain is a system service any process on
the machine can query, not something scoped to one shell.

`sdd config init` asks which you want and defaults to recommending
keyring. To store a credential in the keychain outside the wizard (e.g.
rotating an existing one), use `sdd config set-secret --profile {name}`.

**When to use `env` instead:** CI/CD runners and headless Linux boxes
often have no keychain backend running at all (`sdd config init` and
`sdd config set-secret` fail with a clear message if so, and suggest
switching to `env`) — in those environments, an environment variable
injected by the CI system's own secret store is the normal approach
anyway.

---

## Auth Modes

`auth_mode` controls the *authentication mechanism* (HTTP Basic vs.
Bearer token) — independent of `credential_store` above, which controls
*where the secret value is read from*. Mix and match freely: e.g. `basic`
+ `keyring` is the default recommendation for most users.

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

### Any auth mode, with `credential_store: keyring` instead

No `*_env` field at all — the secret itself was saved via `sdd config
init` (or `sdd config set-secret`) directly into the OS keychain:

```yaml
profiles:
  work-cloud:
    auth_mode: basic
    base_url: https://myco.atlassian.net
    email: user@myco.com
    credential_store: keyring
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
  # Optional: per-level overrides when Features live in one Jira project
  # and Stories/Tasks live in another. Any level not listed falls back
  # to project_key. Valid levels: feature, story, task, review, chg, cr.
  # project_keys:
  #   story: SUNT
  #   task: SUNT
  issue_hierarchy:
    feature: Feature    # or "Epic" if your project has no Feature type
    story: Story
    task: Task
  parent_field: parent  # "parent" for next-gen; "customfield_10014" for classic
  # Optional: per-level overrides for parent_field, for the same reason
  # project_keys exists -- the level here is the CHILD being linked (e.g.
  # "story" for a Story linking under its Epic).
  # parent_field_by_level:
  #   story: customfield_10014
  base_fields:
    priority_map:
      must-have:   High
      should-have: Medium
      could-have:  Low
      wont-have:   Lowest
    labels: [sdd-generated]
    # Optional: a fixed team name/ID stamped on every issue this CLI
    # creates. Requires the matching custom_fields.team entry below.
    # team: Team Phoenix
  custom_fields:
    story_points: customfield_10016   # run "sdd config fields" to find yours
    # team: customfield_10100         # pairs with base_fields.team above
  # Optional: per-level overrides for custom_fields, for the same reason
  # project_keys exists -- a level in a different Jira project usually
  # has a different custom field scheme too.
  # custom_fields_by_level:
  #   story:
  #     story_points: customfield_99001

confluence:
  space_key: ENG
  parent_page_id: "123456"
  page_map:
    brd:     "{feature} — Business Requirements"
    hld:     "{feature} — High-Level Design"
    runbook: "Runbook"   # living doc -- no {feature}, nests under the Project page
```

Full reference: see `.specify/integrations.yml.example`.

**`project_keys` cross-project caveat:** Jira's parent/Epic-Link field
generally does not support linking issues across different Jira
projects — true cross-project hierarchy needs Advanced Roadmaps (Jira
Premium), not the standard REST API this CLI uses. If you override a
level to a different project than its parent level, the child issue is
still created, and the CLI automatically falls back to a plain
**"Relates" issue link** instead — those work across projects, unlike
parent/Epic-Link. `sdd jira push` never fails silently on this: it
always prints which kind of link ended up being used (`Linked with a
"Relates" issue link instead` vs `was not linked under ...` if even that
fallback fails), so check the CLI output after pushing if you use
`project_keys`.

### Rendering diagrams in Confluence

Confluence has **no native Mermaid or PlantUML renderer**. By default, a
` ```mermaid ` or ` ```plantuml ` fenced block in your `.md` files pushes to
Confluence as plain syntax-highlighted text — the diagram source, not a
rendered diagram. Three modes fix this, configured via `confluence.diagrams`:

```yaml
confluence:
  diagrams:
    mode: local-svg   # none (default) | local-svg | mermaid-app | plantuml-macro
```

| Mode | What it needs | Notes |
|---|---|---|
| `none` (default) | Nothing | Diagrams show as text, exactly as today |
| `local-svg` | `pip install "sddflow[diagrams]"` (an optional extra — not installed by default) | Renders ` ```mermaid ` fences to SVG **entirely offline** — no Confluence app, no external network call at render time — then attaches the image to the page. The right choice if your org can't reach external services or can't install Confluence apps. Backed by [`mmdr`](https://pypi.org/project/mmdr/), a small (~18MB) Rust-based renderer with zero further dependencies — chosen after testing it against every diagram type (flowchart, sequenceDiagram, classDiagram, erDiagram) the SDD templates actually generate; a candidate that looked promising on paper (`mermaidx`) failed on flowchart stadium-shape nodes and classDiagram entirely, which is why this wasn't just picked from a package description. A missing dependency, or any single diagram that fails to render, falls back to a plain code block for that one diagram rather than failing the whole document push |
| `mermaid_app` | A Mermaid-rendering Confluence app installed (10+ compete on the Atlassian Marketplace) + its macro name | Only affects ` ```mermaid ` fences; a fence with no `macro_name` configured falls back to plain text rather than a broken macro |
| `plantuml_macro` | A PlantUML-rendering app (e.g. "PlantUML for Confluence") + its macro name | Only affects fences already written as ` ```plantuml ` — this does **not** convert Mermaid syntax to PlantUML, they're different diagram languages. Most of these apps render via the public `plantuml.com` server by default (an external network call); if your org can't reach external services, a Confluence admin needs to point the app at a self-hosted PlantUML server instead, or use `local-svg` above |

If a diagram fence still shows as a plain code block after configuring one
of these modes, the push command now prints a yellow warning naming the
exact reason (e.g. the `pip install` command if `mmdr` isn't installed, or
the actual renderer error for an invalid diagram) — it never fails silently.

A fourth mode, **`markdown-macro`** (delegate the whole page to a
whole-document Markdown-rendering app that bundles Mermaid support), is
planned but not yet implemented — these are Forge-based and use a different,
less-guessable macro reference shape than the three modes above, and needs
verified testing against a real installed app before it ships.

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
