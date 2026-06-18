# Changelog

All notable changes to the SDD Framework are documented here.

---

## [2.2.0] — 2026-06-18

### Added

#### Code review gate (`/pre-review` + `/address-review`)
- `/pre-review` — one-time pre-PR code review: agent analyses diff across 6 angles
  (correctness, removed behaviour, security, cross-file impact, quality, performance),
  presents numbered checklist, developer picks which to fix, agent applies fixes,
  saves summary, then calls `sdd pr create`
- `/address-review` — handles human PR review comments: fetches unresolved threads,
  checklist to developer, applies fixes, replies to threads, resolves them, requests
  re-review; repeatable until PR is approved
- `code_review.pre_review` config flag — `true` = run pre-review before PR creation;
  `false` = skip pre-review, go straight to PR + human review
- `sdd pr create` now reads `.pre-review-{task}.md` summary file and injects it into
  the PR body under a "Pre-Review" section when pre-review was run
- New commands distributed to all 5 packs (3 locations each: `.claude/commands/`,
  `.github/prompts/`)

#### Config
- `code_review:` section added to `integrations.yml.example` with `enabled` and
  `pre_review` fields

---

## [2.1.0] — 2026-06-18

### Added

#### Document-level review gates (`sdd review`)
- `sdd review submit --doc <key>` — push document to Confluence + create Jira review task assigned to the configured reviewer
- `sdd review check --doc <key>` — poll review outcome; exit codes 0=approved 1=needs-revision 2=pending 3=not-submitted
- `sdd review apply --doc <key>` — re-push updated document + notify reviewer via Jira comment
- `sdd review status` — show all documents grouped by phase with approval state
- Sequence enforcement: BRD must be approved before SRD, SRD before Arch, Arch before HLD (same pattern for planning/release phases)
- Approval detection: Jira task status in `approved_statuses` **or** comment containing a keyword from `approved_keywords`
- ADF-aware comment parsing: handles both Jira Cloud (ADF JSON) and Server/DC (plain string) comment bodies

#### PR automation (`sdd pr create`)
- `sdd pr create --task TASK-001` — create git branch + GitHub PR linked to the Jira task
- Branch name and PR title generated from configurable patterns (`branch_pattern`, `pr_title_pattern`)
- PR body includes task description, acceptance criteria, and Jira link (traceability)
- Posts PR URL back to Jira as a comment on the task issue
- Falls back to printing PR title + body if `gh` CLI is not installed

#### Agent slash commands
- `/submit-review <doc>` — Claude Code command wrapping `sdd review submit`
- `/check-review [doc]` — Claude Code command wrapping `sdd review check`; decision tree built into prompt
- `.github/prompts/submit-review.prompt.md` — portable Copilot/Cursor equivalent
- `.github/prompts/check-review.prompt.md` — portable Copilot/Cursor equivalent

#### Configuration
- `document_reviews` section in `.specify/integrations.yml.example` — 9 docs pre-configured with reviewer roles, phases, sequence numbers
- `approved_statuses` and `approved_keywords` lists
- `pr_automation` block: `enabled`, `branch_pattern`, `pr_title_pattern`

---

## [2.0.0] — 2026-06-18

### Added

#### Python CLI (`pip install sdd-init` / `pipx run sdd-init`)
- `sdd init` — replaces `setup.sh` / `setup.ps1`; writes manifest via PyYAML (no injection)
- `sdd upgrade` — migration table; adds `sdd_version` to pre-v2 manifests
- `sdd config init` — interactive setup of `~/.sdd/config.yml` and `.specify/integrations.yml`
- `sdd config test` — pings Jira + Confluence to verify credentials
- `sdd config fields` — lists Jira custom field IDs for your instance
- `sdd jira push` — pushes Feature → Story → Task to Jira (idempotent)
- `sdd jira push --dry-run` — prints push plan without API calls
- `sdd jira sync` — pulls Jira issue statuses back alongside task IDs
- `sdd confluence push` — publishes SDD documents to Confluence pages
- `sdd confluence push --doc <key>` — pushes a single document
- `sdd confluence push --dry-run` — prints page titles without API calls

#### Atlassian auth layer
- Three auth modes: `basic` (Cloud email + API token), `pat` (Server/DC), `oauth2` (CI/CD Bearer)
- Credentials stored as env var names only — never values — in `~/.sdd/config.yml`
- Multiple named profiles supported (e.g. one per Atlassian instance)

#### Jira integration
- Feature → Story → Task hierarchy (all three issue type names configurable)
- Idempotency via `sdd:STORY-NNN` / `sdd:TASK-NNN` labels — re-runs update, never duplicate
- MoSCoW priority mapped to Jira priority via `integrations.yml priority_map`
- Custom fields supported: story points, acceptance criteria, team, any custom field ID
- `parent_field` config handles both next-gen (`parent`) and classic (`customfield_10014`) projects

#### Confluence integration
- Pushes any SDD document (brd, srd, hld, lld, arch, adr, runbook) to a Confluence page
- Markdown converted to Confluence Storage Format (XHTML) — works on Cloud, Server, DC
- Pages matched by title — create if absent, update version if present
- `page_map` in `integrations.yml` controls page titles (supports `{project}` token)

#### Node.js CLI (`npx sdd-init`)
- `sdd init` — cross-platform replacement for setup scripts; writes manifest via js-yaml
- `sdd upgrade` — same migration table as Python CLI

#### Pack versioning
- `sdd_version: "2.0.0"` field added to all five pack `manifest.yml` files
- `sdd upgrade` reads this field and applies the migration table

#### Community registry
- `PACK-SPEC.md` — specification for building community packs
- `packs/CATALOG.md` — official pack catalog with decision tree

#### Regression harness
- `packs/_shared/tests/test-setup.sh` — 15 smoke tests for setup scripts
- `packs/_shared/tests/assert-output.sh` — 31 structural assertions on SDD output
- `examples/todo-api/` — complete worked example (TypeScript/Express/PostgreSQL)

### Fixed

- `setup.sh` injection bugs: quoted heredoc `<<'PYEOF'` + `SDD_*` env vars
- `re.sub` replacement strings: switched to lambda form to prevent `\t`/`\n` escape expansion
- sed delimiter collision: replaced `sed s/PLACEHOLDER/…/` with `python3 str.replace()`
- PowerShell `-replace` metacharacter expansion: switched to `.Replace()` (literal)
- Mobile detection order: `pubspec.yaml` and `react-native` now checked before fullstack in
  all three locations (`setup.sh`, `setup.ps1`, `specify.prompt.md`)
- Input validation: project/feature names containing `"` rejected early with a clear message

### Changed

- `setup.sh` rewritten to use Python for all manifest and file substitution (no sed/awk)
- `setup.ps1` rewritten with full `Detect-ProjectType` function and input validation
- `taskstoissues.prompt.md` updated: adds `priority:wont-have` label, concrete `gh issue create` examples

---

## [1.x] — pre-versioning

Initial release. No `sdd_version` field in manifest. Run `sdd upgrade` to migrate.
