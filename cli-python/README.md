# sdd-init (Python) — SDD Framework CLI

Python CLI for the SDD (Spec-Driven Development) Framework.  
Mirrors the Node.js CLI exactly and adds Jira + Confluence integration.

## Install

```bash
# Run without installing (recommended for first use)
pipx run sdd-init init

# Or install globally
pip install sdd-init
sdd init

# Or with pipx
pipx install sdd-init
sdd init
```

**Requirements:** Python ≥ 3.9

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
