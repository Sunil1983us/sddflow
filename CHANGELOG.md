# Changelog

All notable changes to the SDD Framework are documented here.

---

## [3.7.2] — 2026-08-28 (Fix: sdd confluence push --doc constitution wrongly warned about a collision)

`sdd confluence push --doc constitution` (and other PROJECT_SCOPED_DOCS:
`runbook`, `data-model`, `security-design`, `api-spec`) wrongly warned
about overwriting another feature's page in a multi-feature project and
refused to push without `--force`. `feature_collision_warning()` only
checked "does the title contain the feature name" — which project-scoped
docs' titles never do on purpose, since they're deliberately one shared
page across every feature — so it always flagged them as a collision
risk, even though there's no other feature's page to actually collide
with. Reported live: a user saw an AI agent's own reasoning trace get
confused by this warning mid-session and skip pushing the constitution
entirely.

### Fixed

- `feature_collision_warning()` gained a `doc` parameter and
  short-circuits to "no warning" when `doc` is one of the
  `PROJECT_SCOPED_DOCS`, before the feature-name check even runs.

### Verified

- cli-python pytest 1149/1149 (1146 unchanged + 3 new — confirmed all 3
  actually fail against the pre-fix code, reproducing the exact warning
  text the user saw, and pass against the fix); ruff check/format clean;
  mypy clean; bandit 0 issues.

---

## [3.7.1] — 2026-08-28 (Fix: unencoded file I/O mangled non-ASCII content on Windows)

A user reported an em-dash in a `/create-context`-generated `context.md`
coming out as mojibake (`â€"`) once pushed to Confluence via `sdd
confluence push`. Root cause: `Path.read_text()`/`write_text()` and
`open()`/`os.fdopen()` in text mode all default to
`locale.getpreferredencoding(False)` when `encoding=` is omitted — cp1252
on many Windows setups, not UTF-8. Each UTF-8 byte of the em-dash got
reinterpreted as a separate cp1252 character.

### Fixed

- Every `read_text()`/`write_text()` call and the one `os.fdopen()` call
  across the entire `cli-python` codebase now pass `encoding="utf-8"`
  explicitly — ~20 files, including the shared `atomic_write_text()`
  utility used by nearly every write site in the codebase.
- One f-string quote collision found along the way (can't reuse double
  quotes inside a double-quoted f-string pre-3.12) fixed by switching
  that one site to single quotes.
- Checked the Node CLI for the equivalent gap — none exists; Node's
  `fs.writeFileSync` defaults to `'utf8'` for string writes regardless of
  OS locale, and every `readFileSync` call already passed `'utf8'`.

### Added

- `cli-python/tests/test_utf8_encoding_everywhere.py` — a static AST scan
  asserting every text-mode file I/O call in the codebase specifies
  `encoding=`, so this can't silently regress.

### Verified

- cli-python pytest 1146/1146 (1144 unchanged + 2 new); ruff check/format
  clean; mypy clean; bandit 0 issues.

---

## [3.7.0] — 2026-08-26 (/clarify: spec-kit-style questions with pre-reasoned recommended answers)

3.6.0 made `/clarify`'s live-chat path push back on a vague answer with
one narrower follow-up before falling to best guess. Checked
[github/spec-kit](https://github.com/github/spec-kit)'s own `clarify.md`
template directly for a second opinion — it asks one question at a time
(capped at 5), each with a pre-reasoned recommended/suggested default the
human can accept with "yes" instead of typing an answer, drawn from a
9-category taxonomy that inherently balances technical and business
angles. Adopted that shape.

### Changed

- Every question now states **Recommended: Option X** (multiple-choice,
  lettered table) or **Suggested:** (open-ended), reasoned from something
  real in this project's own docs (`context.md`, `constitution.md`'s Tech
  Stack/Domain Rules, `brd.md`'s stated business objectives) — never a
  generic justification.
- Asks through at least 5-6 items when that many are open, picked across
  item types (not just severity) so it doesn't ask five near-identical
  AMB items back to back while a real GAP/OQ item sits unasked.
- The 3.6.0 push-back mechanic is gone — with a recommended default
  always on offer, "make it reasonable"-style non-answers are rarer to
  begin with. A reply that doesn't engage at all gets one check-in
  referencing the already-offered default, then resolves via that
  default as agent-best-guess rather than looping.
- The other three intake paths (direct file-edit + "done", "best
  guess"/"continue", async Jira/Confluence comment) are unchanged.

### Verified

- `sync-blocks.sh` run twice consecutively with zero unexpected drift
  (only the 5 intentionally-edited `clarify.prompt.md` files changed);
  `check-cross-references.py` clean across all 6 packs; `test-setup.sh`
  19/19 passed.

---

## [3.6.1] — 2026-08-26 (Security: status.py path-injection hardening flagged by CodeQL)

GitHub's code-scanning (CodeQL) flagged `status.py`'s `_local_jira_links()`
for `py/path-injection`: it built `docs/jira/{feature}/keys.yml` by string
concatenation, with no traversal check of its own. Every current caller
already validated `feature` before calling in (the dashboard's
`/api/review-links` endpoint via an allowlist regex; the CLI `sdd status`
path, same trust level as a user's own `manifest.yml`), so this was never
actually reachable with an attacker-controlled value — but the function
itself provided no guarantee, only its callers happened to.

### Fixed

- `_local_jira_links()` now routes the feature name through
  `safe_feature_path()` (the same traversal check every other doc-path
  resolution in this codebase already uses) before building the path. A
  feature name that tries to escape `docs/jira/` now returns the same
  empty result as "no keys file found," instead of reading whatever's at
  the escaped path.

### Verified

- cli-python pytest 1144/1144 (1143 unchanged + 1 new); ruff check/format
  clean; mypy clean; bandit 0 issues.

---

## [3.6.0] — 2026-08-26 (/clarify: live one-at-a-time interview, pushes back on vague answers)

Previously `/clarify` wrote every open item to `clarify.md`, presented the
full report, and then just waited — whatever came back in chat was mapped
to an item's ID and accepted as-is, even a non-answer like "make it
reasonable" or "whatever's best." The item still got marked RESOLVED, and
the same ambiguity could resurface unnoticed at `/plan-design`.

### Changed

- `/clarify` still presents the full report once, but the live-chat answer
  path now interviews one item at a time — CRITICAL/HIGH first — instead
  of just waiting for whatever comes back.
- If an answer is vague, it's not accepted: the agent asks one specific
  follow-up aimed at getting something `/plan-design` can actually build
  against. Pushes back at most twice per item; a third vague answer
  resolves by best guess instead of looping forever.
- A human who pastes answers for several items at once is still accepted
  immediately — the one-at-a-time cadence is the default, not a hard rule.
- The other three intake paths are unchanged: editing `clarify.md`
  directly and saying "done," "best guess"/"continue," and an async
  Jira/Confluence comment reply all still bypass the interview entirely.

### Verified

- `sync-blocks.sh` run twice consecutively with zero unexpected drift
  (only the 5 intentionally-edited `clarify.prompt.md` files changed);
  `check-cross-references.py` clean across all 6 packs; `test-setup.sh`
  19/19 passed.

---

## [3.5.0] — 2026-08-26 (Confluence push-drift detection: sdd confluence verify, --force-overwrite)

`sdd confluence push` used to overwrite a page's body unconditionally,
using Confluence's optimistic-locking version number purely to avoid a
409 — never to detect that someone had edited the live page in between.
A reviewer fixing a typo or adding a clarification directly on Confluence
had that edit silently discarded the next time anyone re-pushed the doc,
with no warning it had ever existed.

### Added

- `docs/confluence/push-log.yml` (new, auto-generated) — records what
  sddflow itself last wrote to each page: `{page_id: {doc, title,
  pushed_version}}`, updated after every successful `push`/`draft`/`pull`.
- `sdd confluence push` now checks each page's live version against the
  push log before overwriting it. If the page moved since sddflow's last
  push, it prints who edited it and when, and skips that doc — pass the
  new `--force-overwrite` flag to push anyway. (Separate from the
  existing `--force`, which governs a different warning about
  title/feature collisions.)
- `sdd confluence draft`/`pull` record the push-log entry but never warn
  — draft/pull's whole point is inviting a human to edit the page
  directly, so flagging that as drift would be a constant false alarm.
- New `sdd confluence verify` command: read-only, reports
  up-to-date/drifted/missing for every tracked page without pushing or
  pulling anything — for checking drift on demand, not just at the next
  push.

### Verified

- cli-python pytest 1143/1143 (1120 unchanged + 23 new); ruff
  check/format clean; mypy clean (38 source files); bandit 0 issues.

---

## [3.4.3] — 2026-08-19 (Security: fix host-spoofable substring checks flagged by CodeQL)

GitHub's code-scanning (CodeQL) flagged `sdd/utils/git_host.py`'s host
detection — the logic behind `sdd pr create` that decides which git host
(GitHub/Bitbucket/GitLab/Azure DevOps) a repo's origin remote points at —
for a classic substring-sanitization bug: `"github.com" in host` and
similar checks accept any host containing that substring anywhere, not
just github.com itself or a real subdomain of it (e.g. `notgithub.com`
or `github.com.evil.example` would both incorrectly match).

### Fixed

- `parse_remote()`'s 5 substring checks replaced with real host-boundary
  comparisons: `_host_is()` (exact match or `.`-subdomain, via
  `str.endswith(f".{domain}")`) for the four hosts pinned to one real
  domain — github.com, bitbucket.org, dev.azure.com, visualstudio.com.
- `gitlab`'s check — deliberately broader than the other four, to catch
  arbitrary self-hosted instances like `gitlab.mycompany.internal` —
  moved from an anywhere-substring check to `_host_has_label()`,
  requiring `"gitlab"` to be a full dot/hyphen-separated hostname label.
  Closes `notgitlab.io`/`gitlabish.io` false-accepts while still
  detecting genuine self-hosted installs like `gitlab.corp.io` and
  `code-gitlab.corp.io`.

Practical exploitability was narrow — `host` comes from the local git
remote URL, which only decides which provider CLI (`gh`/`glab`/`az`)
gets shelled out to, not a network-facing trust boundary — but the fix
is free and the old behavior was genuinely incorrect regardless.

### Verified

- cli-python pytest 1120/1120 (1108 unchanged + 12 new: 8 cases
  confirming the substring bypass is rejected across all 4 pinned
  hosts, 2 confirming the gitlab label-bypass is rejected, 2 confirming
  genuine self-hosted GitLab detection still works unchanged).
- ruff check/format clean; mypy clean; bandit 0 issues.

---

## [3.4.2] — 2026-08-17 (Fix: Jira/Confluence Server & Data Center support)

Direct follow-up to 3.4.1, from the same user report. After 3.4.1 fixed
`sdd config test`'s crash, the user tested the underlying connection by
hand with curl/`Invoke-RestMethod` against two real Jira/Confluence Data
Center servers — Jira's `/rest/api/2/myself` worked, `/rest/api/3` did
not; Confluence's `/rest/api/user/current` worked, with no `/wiki`
prefix. That confirmed the real root cause: this CLI's Jira/Confluence
clients were hardcoded to Cloud-only conventions.

### Fixed

- Jira Server/Data Center does not support REST API v3 at all — only
  v2. Confluence Server/Data Center's REST API sits directly at
  `/rest/api`, with no Cloud's `/wiki` prefix. `JiraClient`/
  `ConfluenceClient` hardcoded the Cloud-only paths unconditionally
  before this — every request against a Server/DC instance failed, not
  always with a clean error.
- Added `Profile.deployment` (`'server'` for `auth_mode: pat` — a
  Server/DC-only auth feature — `'cloud'` otherwise). Both clients gained
  an optional `deployment=` keyword (default `'cloud'`, so existing
  Cloud profiles are unaffected) that switches v3→v2 and drops the
  `/wiki` prefix for Server/DC. Threaded through all 24 call sites
  across 8 command files.

### Verified

- cli-python pytest 1108/1108 (1098 unchanged + 10 new, including one
  end-to-end test using the real client classes confirming a `pat`
  profile requests exactly the URLs the reporting user verified by
  hand); ruff check/format clean; mypy clean (37 source files); bandit 0
  issues.

---

## [3.4.1] — 2026-08-17 (Fix: `sdd config test` no longer crashes on a non-JSON response)

Reported by a real user testing PAT auth against two separate Jira/
Confluence Data Center servers: `sdd config test` crashed with a raw
`json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`
traceback instead of a clean per-service status line.

### Fixed

- `response.json()` raises this when a server answers 200 with a
  non-JSON body — most commonly an SSO/login-page redirect, or
  `base_url` pointing at the wrong path entirely. `except
  requests.HTTPError` never caught it, since `JSONDecodeError` is a
  `RequestException` *sibling*, not a subclass of `HTTPError`.
- `sdd/commands/config.py`'s duplicated Jira/Confluence probe logic is
  now one `_probe_service()` helper with three distinct failure modes:
  an HTTP error (shows status + body), a non-JSON response (shows an
  actionable message about `base_url`/SSO/token validity instead of a
  raw parse error — caught both as the bare stdlib exception class,
  matching what the reporting user's traceback showed, and as modern
  `requests`' own wrapped subclass), and any other connection-level
  failure (requests' own message is clear enough on its own).

### Verified

- cli-python pytest 1098/1098 (1094 unchanged + 4 new covering all
  three failure modes, including a direct reproduction of the reported
  bug); ruff check/format clean; mypy clean (37 source files); bandit 0
  issues; manually confirmed end-to-end through the full CLI invocation
  path, not just the unit tests.

---

## [3.4.0] — 2026-08-13 (New: `sdd upgrade --apply-files` actually applies pack updates)

Completes the effort `sdd doctor` (3.2.0) and the `pack:` field (3.3.0)
were building toward. `sdd upgrade` used to only ever patch
`manifest.yml`'s `sdd_version` field — it never touched the actual
template/prompt/command/instruction/setup-script files a project was
scaffolded with. `--apply-files` now actually applies safe updates
instead of just reporting them.

### Added

- **`sdd upgrade --apply-files`** — brings every framework-managed file
  (the same set `sdd doctor` checks) in line with the currently installed
  pack. New files and files that still match their last recorded
  baseline are applied automatically; files that were hand-edited, or
  have no recorded baseline to tell an update apart from an edit, are
  left alone and listed unless `--force` is also passed. Every
  overwritten file is backed up first to
  `.specify/.managed-files-backups/{timestamp}/`. A fresh baseline is
  written after every run — including no-op runs, so a project that's
  already current the first time this flag is used still gets a baseline
  recorded immediately rather than only after its first divergence.
- **`--force`** — with `--apply-files`, also overwrites locally-modified
  files and files with no recorded baseline (still backed up first).
- New `sdd/utils/managed_files.py` functions: `apply_managed_files()`,
  `write_baseline()`.
- README.md gained a full `--apply-files` walkthrough and a `sdd doctor`
  section, which had never been documented there since it shipped in
  3.2.0.

### Changed

- `--sync-prompts` is kept, unchanged, for backward compatibility —
  `--apply-files` is the recommended flag going forward (broader scope,
  conflict-aware).
- `sdd doctor`'s closing note now points at `sdd upgrade --apply-files`
  instead of saying nothing applies pack updates yet.

### Verified

- cli-python pytest 1055/1055 (1035 unchanged + 20 new); ruff
  check/format clean; mypy clean (37 source files); bandit 0 issues; node
  test 28/28; manually verified end-to-end against a real
  freshly-scaffolded project — baseline correctly written on a no-op run,
  a hand-edited file correctly classified as modified locally by `sdd
  doctor`, correctly left alone by `--apply-files` without `--force`,
  and correctly overwritten-with-backup by `--apply-files --force`.

---

## [3.3.0] — 2026-08-13 (Fix: `manifest.yml` now records an explicit `pack:` field)

Direct follow-up to 3.2.0. That release could only *detect* the
pack-identity gap it found while dogfooding `sdd doctor` — a project
without a stored pack identity has to be inferred from `project_type`,
which silently names the wrong pack for any `sdd-universal`-scaffolded
project (it serves all 10 project types from one shared file set rather
than becoming a type-specific pack). This release fixes it at the source.

### Added

- Every pack's own `.specify/manifest.yml` template (`sdd-backend-service`,
  `sdd-frontend-spa`, `sdd-fullstack`, `sdd-mobile`, `sdd-universal`, and
  `sdd-micro` outside the version lockstep) now bakes in a static
  `pack: "sdd-..."` line right after `sdd_version` — the same pattern
  already used for `sdd_version`'s own static default. No template
  substitution needed in `setup.sh`/`setup.ps1`; the value is simply
  correct for every project scaffolded from that pack.
- `PACK-SPEC.md`'s documented manifest schema updated to list `pack:` as
  a required field, so community pack authors include it from day one.

### Changed

- `_resolve_pack()` already prioritized a stored `manifest.get('pack')`
  above inference (added alongside 3.2.0) — this release is what actually
  makes that branch fire for `setup.sh`/`setup.ps1`-scaffolded projects.
  `sdd init`-scaffolded projects were already unaffected, since `init` has
  stamped this field since before this phased effort started.

### Verified

- cli-python pytest 1035/1035 (unaffected — manifest-only change); all 6
  packs' `manifest.yml` confirmed to parse as valid YAML with the new
  field; `check-cross-references.py` clean across all 6 packs;
  `test-setup.sh` 19/19 and `test-setup-micro.sh` 12/12 passed; two real
  functional scaffolds re-confirmed the fix end-to-end — a fresh
  `sdd-backend-service` scaffold now resolves via `manifest.yml 'pack'
  field` with no warning, and a fresh `sdd-universal` scaffold
  (`setup.sh --type backend-service`) now correctly resolves to
  `sdd-universal` instead of the previously-mis-inferred
  `sdd-backend-service`.

---

## [3.2.0] — 2026-08-10 (New: `sdd doctor` — read-only pack-drift report)

An external code review of this repo (ChatGPT) found, among other things,
that `sdd upgrade` has only ever stamped `manifest.yml`'s `sdd_version`
field — it never actually syncs a project's templates, prompts, commands,
instructions, setup scripts, or (confirmed while investigating this)
workflow/`.cursor`/`.vscode` files forward to match the pack content
bundled with whatever CLI version is currently installed. A project could
report itself "upgraded" while every one of those files still matched
whatever version it was originally scaffolded with. The review's numbers
were verified independently before acting on any of it — radon complexity
figures and coverage percentages matched exactly when re-run.

`sdd doctor` is the first, deliberately read-only step of closing that
gap: it reports drift without applying anything, so it's safe to ship and
use immediately, well ahead of the larger `sdd upgrade` rewrite that will
actually apply fixes.

### Added

- **`sdd doctor`** — SHA-256-hashes every framework-managed file (under
  `.specify/templates/`, `.claude/commands/`, `.github/prompts/`,
  `.github/instructions/`, `.github/workflows/`, `.cursor/rules/`,
  `.vscode/`, plus `setup.sh`/`setup.ps1`) against the pack bundled with
  the currently installed CLI, and classifies each as up-to-date /
  missing / needs-update / user-modified / differs-for-unknown-reason
  (the honest fallback for any project scaffolded before this existed —
  no recorded baseline means it can't tell a pack update from a hand
  edit, and doesn't guess). `--pack` to override detection, `--quiet` to
  only show non-clean files. Exit code 0/1, scriptable.

### Fixed (discovered while building this, not from the review)

- Dogfooding `sdd doctor` against a real freshly-scaffolded project
  surfaced a real, pre-existing gap: `_resolve_pack()`'s project_type
  inference can silently name the wrong pack for any sdd-universal-
  scaffolded project, since sdd-universal serves every project_type from
  one shared set of files rather than becoming a type-specific pack, and
  `manifest.yml` has never recorded an explicit `pack:` field to tell the
  two apart. Not fixed here — `sdd doctor` now detects when its pack
  identity came from inference rather than a stored field and prints a
  prominent warning rather than silently trusting a guess. A real fix
  belongs with the `pack_version`/manifest-schema split planned next in
  this effort.

### Verified

- cli-python pytest 1035/1035 (1012 unchanged + 23 new); manually
  verified end-to-end against a real freshly-scaffolded project — 113/113
  files correctly up to date with the correct pack, a hand-edit and a
  deletion both caught precisely with nothing else flagged; ruff
  check/format clean; mypy clean (37 source files, up from 35); bandit 0
  issues.

---

## [3.1.1] — 2026-08-10 (URL fix: repo renamed universalguide → sddflow)

The GitHub repo was renamed to `sddflow` to match the actual product
branding — that's already the PyPI package name, the npm package name,
and the CLI binary name; `universalguide` never matched any of them.
GitHub's redirect keeps old links working indefinitely, but the links
this project ships itself should say what's actually true rather than
lean on a redirect forever.

### Fixed

- `sdd --help`'s epilog and the dashboard's footer link (both new in
  v3.1.0) now point at `github.com/sunil1983us/sddflow/issues`.
- Every other reference across the repo swept to match: `README.md`,
  `CONTRIBUTING.md`, `SECURITY.md`, `pyproject.toml`/`package.json`
  project URLs, the issue templates, and each pack's
  `README.md`/`QUICKSTART.md`/`FLOW-ROLES-GATES.md`.
- Deliberately left alone: a local-filesystem-path test fixture that
  coincidentally shared the old name, and an older CHANGELOG entry
  documenting a past release's clone example (historical record).

### Verified

- cli-python pytest 1013/1013; ruff check/format clean; mypy clean
  (35 source files); bandit 0 issues; node 28/28; grep sweep confirms
  zero remaining `universalguide` references outside the two
  intentionally-excluded files.

---

## [3.1.0] — 2026-08-10 (`--help` and the dashboard now point to where to report issues)

The repo went public and got GitHub Issues templates, `CONTRIBUTING.md`,
and `SECURITY.md` set up earlier the same day — but that only helps
someone who actually browses to the GitHub repo page. Most `sddflow`
users interact purely through `pip install` + the CLI/dashboard and may
never visit GitHub directly. This closes that gap: the two places users
actually spend time now both link to where to file a bug or request a
feature.

### Added

- **`sdd --help`** — new epilog: "Found a bug or have a feature request?
  https://github.com/sunil1983us/sddflow/issues"
- **Dashboard footer** — same link, rendered outside `#root` in
  `page.html` so it survives the 5s poll's `innerHTML` rebuild without
  needing any `app.js` changes.
- **`CODE_OF_CONDUCT.md`** (Contributor Covenant v2.1) and
  **`.github/PULL_REQUEST_TEMPLATE.md`** — closes the same community-health
  gap visible on GitHub's own `spec-kit` repo's sidebar (Code of conduct,
  Contributing, Security policy all showing there, only two of three
  present here before this). Prose/governance files — no version bump
  needed for these two on their own.

### Verified

- cli-python pytest 1013/1013 (unchanged — no test asserts `--help`/footer
  output verbatim); ruff check/format clean; mypy clean (35 source files);
  `sdd --help` manually confirmed to show the new epilog; dashboard test
  suite (`test_dashboard.py`, `test_dashboard_http.py`,
  `test_dashboard_comments.py`) 68/68 passed.

---

## [3.0.2] — 2026-08-09 (New: `sdd hooks` — deterministic per-commit token logging)

Direct follow-up to v3.0.1. The prompt fix there wasn't enough — the user
confirmed it: even after pulling the update and manually catching up with
`sdd token-log --command implement` (which worked correctly), the agent
still wasn't calling it automatically per task during a live batched
`/implement` run. Explicit ask: "I need for each task." A prompt
instruction is followed probabilistically, not enforced — the only way to
make this actually deterministic is code, not more prose.

### Added

- **`sdd hooks install`** — writes a git `post-commit` hook that runs
  `sdd token-log --command implement` after every commit, independent of
  whether the AI agent remembers to. Silent and best-effort: does nothing
  if `sdd` isn't on `PATH`, `token-pricing.yml` isn't configured, or
  there's nothing new since the last logged row — and it can never fail
  the commit it's attached to.
- **`sdd hooks status`** / **`sdd hooks uninstall`** for symmetry.
  `install` refuses to overwrite a pre-existing hook it didn't create
  unless `--force` is passed; `uninstall` never touches a hook it didn't
  write.

Deliberately opt-in — not wired into `sdd init`/`sdd upgrade`, since
installing a git hook is a real side effect on your repository and
shouldn't happen without being asked, same principle as
`token-pricing.yml` itself.

### Verified

- `cli-python` pytest 1013/1013 (1000 unchanged + 13 new tests); ruff
  check/format clean; mypy clean; bandit 0 issues.
- `check-cross-references.py` clean across all 6 packs; `sync-blocks.sh`
  run twice consecutively with zero drift; `test-setup.sh` 19/19 passed;
  `test-setup-micro.sh` 12/12 passed.

---

## [3.0.1] — 2026-08-09 (Fixed: Token Usage Logging silently skipped during batched /implement)

Found via a live user report: they told the agent to run every `/implement`
task back-to-back without stopping for the usual per-task "go" — and Token
Usage Logging quietly stopped happening for the rest of the run, even
though `token-pricing.yml` was already configured and other commands
(`specify-brd`, `validate`, etc.) had logged fine earlier in the same
project.

### Fixed

The Token Usage Logging step sits immediately next to the "WAIT for go"
instruction in every prompt that has it, and nothing said the two were
independent. An agent asked to "proceed without stopping" could reasonably
read that as license to skip the adjacent housekeeping step too, since
nothing told it otherwise.

Added a clarifying paragraph to `packs/_shared/blocks/token-usage-log-step.md`
(synced to 19 prompt files × 5 packs): "proceed without stopping" /
"skip confirmation" instructions waive the *pause* between steps, not the
logging step — it still runs after every single task/command execution,
even mid-way through a whole batch.

Pure prompt-instruction content — no CLI code touched.

### Verified

- `check-cross-references.py` clean across all 6 packs.
- `sync-blocks.sh` run three times consecutively, zero drift after the
  first sync.
- `test-setup.sh` 19/19 passed; `test-setup-micro.sh` 12/12 passed
  (`sdd-micro` has no such block — unaffected, by design).

---

## [3.0.0] — 2026-08-09 (Fixed: Spec Quality Checklist could never show done)

**Version note:** the jump to `3.0.0` is the capped-counter carry rule
firing (`2.9.24` was at both the patch and minor cap simultaneously) — see
`.claude/skills/version-bump/SKILL.md`. It is not a semver breaking-change
signal; nothing about this release requires action beyond a normal upgrade.

Found via direct user report, then confirmed against the user's own real
filesystem path: `/checklist` genuinely ran — the checklist file existed —
but the dashboard's "Spec Quality Checklist" pipeline step stayed stuck on
"upcoming" and "Next: Run `/checklist`" never went away, no matter how many
times it was re-run.

### Fixed

Two compounding bugs in `sdd/utils/status.py`:

1. Document discovery only scanned `.md` files directly inside
   `.specify/features/{feature}/`. `/checklist` actually saves to
   `.specify/features/{feature}/checklists/{feature}-spec-quality.md` — a
   subdirectory, with a filename that doesn't even match the `checklist`
   key — so it was structurally invisible regardless of how many times it
   ran.
2. Even discovered, the checklist file has no `Status: Draft/Approved`
   header like every other spec document — it's a self-contained audit
   report (a findings table + a checkbox summary), not something with a
   review-gated lifecycle. The generic "does the status say approved"
   check could never have matched it either.

Fixed with a dedicated code path: a new `_checklist_info()` looks up the
real path and counts open CRITICAL findings; the pipeline step gained its
own `checklist` kind with accurate `done`/`current`/`upcoming` states and
next-action messaging, instead of being forced into the generic
document-review model it never actually fit.

### Verified

- `cli-python` pytest 1000/1000 (993 unchanged + 7 new regression tests),
  including one that reproduces the exact reported scenario end-to-end
  with a real file on disk at the real nested path.
- `ruff check`/`format` clean; `mypy` clean.

---

## [2.9.24] — 2026-08-09 (Dashboard: task pagination, more toggles, a real persistence bug fix)

Direct follow-up to v2.9.23, after the user pushed back: "do you have the
toggle for other sections also, like Tasks — if it has 100 tasks the page
will be very high, so we can have a limit and click next button, same
Documents section also toggle... review all the design... think as a UX
designer for dashboard."

### Changed

- **Tasks pagination.** A real project's `tasks.md` can run to 50–200+
  entries. `renderTasks()` now paginates at 20 rows/page with Prev/Next
  buttons and a "Showing X–Y of N · page P/C" indicator — the aggregate
  progress bar above the table always reflects the *full* list, not just
  the current page. Position is kept per-feature so switching tabs doesn't
  lose your place.
- **Documents and Business Objectives (per-feature)** are now collapsible,
  matching the project-wide sections from v2.9.23. Documents defaults open
  (bounded list); Business Objectives defaults open only at ≤8 BOs,
  auto-collapsing past that — the same smart threshold was retrofitted onto
  the existing project-wide BO Overview, which previously always defaulted
  open regardless of size.
- **Jira Export's** Stories/Tasks lists now truncate at 12 items with a
  "+N more" / "show less" toggle — a comma-joined list of ~100 ticket keys
  was still a wall of wrapped links even though it isn't a table.

### Fixed

- **Real bug, found while reviewing the whole design end-to-end**: none of
  v2.9.23's collapsible sections actually survived the dashboard's 5-second
  poll. `#root` is rebuilt wholesale on every poll, so any manual
  open/close toggle silently snapped back to its hardcoded default every 5
  seconds. Fixed with an explicit `state.collapsed` map plus a
  capture-phase `toggle` listener (native `toggle` events don't bubble, so
  capture phase is required for delegation to reach them) — a user's choice
  now persists across every poll, and only falls back to the smart default
  when they haven't chosen yet.

### Verified

- `cli-python` pytest 993/993 (992 unchanged + 1 updated for
  `renderJiraExport()`'s new parameter); `ruff check`/`format` clean;
  `mypy` clean; `node --check app.js` valid syntax.
- Manually verified end-to-end with a real HTTP server against a synthetic
  87-task/14-BO/87-Jira-key fixture, screenshotted via Playwright/Chromium:
  pagination transitions correctly, the 14-BO section auto-collapsed as
  designed, the Jira Export toggle works — and the persistence fix was
  directly verified by opening a collapsed section, calling the app's own
  `refresh()` to simulate a poll, and confirming it stayed open (it would
  have silently reverted before this fix).

---

## [2.9.23] — 2026-08-09 (Dashboard: feature tabs, collapsible sections, stat widgets)

Requested directly by a user who attached a real dashboard PDF snapshot and
pointed out the obvious problem: on a multi-feature project, the page just
kept growing — every feature's full block (Full Pipeline, Documents,
Business Objectives, Timeline, Tasks, Token Usage, Jira Export) stacked one
after another, with no way to jump around or collapse anything.

### Changed

- **Feature tab strip.** Only the *active* feature's full block renders now.
  A compact tab strip (one pill per feature, showing stage + tasks%)
  replaces both the old always-stacked layout and the old static "Features
  Overview" table — it's the quick-compare view and the navigation control
  in one. Single-feature projects are unaffected; tabs only appear once
  there are 2+ features, same threshold the old overview table used.
- **Collapsible sections.** Living Documents and the project-wide Business
  Objectives Overview are now collapsible (open by default, same chevron
  treatment as the existing "Where this data comes from" box) — measured a
  ~22% page-height reduction when collapsed on a 3-feature/9-BO test
  fixture.
- **Stat-tile widgets.** A 3-tile row (Tasks %, Business Objectives
  outcomes-met, Documents approved) now sits at the top of the active
  feature's block — no more scanning three separate cards further down.
  Business Objectives rows also gained a thin inline progress bar instead
  of plain "67% (2/3)" text.

Pure client-side change (`dashboard_static/app.js` + `style.css`, served
verbatim by `dashboard.py`) — no server-side or API changes.

### Verified

- `cli-python` pytest 993/993 (no `.py` files touched); `ruff check`/
  `format` clean; `mypy` clean; `node --check app.js` valid syntax.
- Manually verified end-to-end: a real HTTP server against a synthetic
  3-feature fixture with the full BO→BR→FR→Task rollup chain wired,
  screenshotted via Playwright/Chromium in light and dark theme — tab
  switching, stat tiles, BO progress bars, and the collapse toggle all
  confirmed working; dark mode colors adapt correctly through the existing
  CSS variable system.

---

## [2.9.22] — 2026-08-09 (`/checklist` now actually blocks at mvp/full scope)

Found via a live dashboard report: "Next: Run `/checklist`" was still
showing even though Validate, Analyze, Clarify, Design, LLD, and Stories
were all already approved for an `mvp`-scope feature. The dashboard turned
out to be right the whole time — `/checklist` really was never run — but
the framework never actually enforced its own documented policy.

`CLAUDE.md`'s Scope Reference table and `/checklist` section both say
`/checklist` is **Mandatory for `mvp` and `full` scope** and that "All
CRITICAL items must be resolved before `/validate` can proceed." But every
pack's `validate.prompt.md` Step 0 ("CHECKLIST GATE (advisory)") was
hard-coded to never block, regardless of scope — a project could sail
straight from SRD through `/validate` → `/analyze` → `/clarify` →
`/plan-design` → `/plan-lld` → `/task`, all approved, without `/checklist`
ever running.

### Fixed

- All 5 packs' `.github/prompts/validate.prompt.md` Step 0 is now
  scope-aware: `pilot` stays advisory (warns, doesn't block); `mvp`/`full`
  now genuinely **block** `/validate` when `checklists/` is missing (never
  run) or still has open CRITICAL items. `sdd-micro` excluded — it has no
  `/checklist` step at all, by design.
- All 5 packs' `CLAUDE.md` — fixed the self-contradictory section heading
  "`/checklist` — Optional Spec-Quality Gate" (it directly contradicted
  the very next line, "Mandatory for `mvp` and `full` scope") to just
  "`/checklist` — Spec-Quality Gate".

### Verified

- `check-cross-references.py` clean across all 6 packs.
- `sync-blocks.sh` run twice consecutively, zero unexpected drift.
- `test-setup.sh` 19/19 passed.
- No `.py`/`.js` files touched — pure prompt/`CLAUDE.md` content, so no
  pytest/`node --test` re-run needed for this specific change.

**Note for existing `mvp`/`full`-scope projects:** if `/checklist` was
skipped, your next `/validate` run will now block until it's run and any
CRITICAL findings are resolved. That's the intended fix, not a
regression — it's catching up on a gate that should have applied all
along.

---

## [2.9.21] — 2026-08-09 (Docs: `--feature` added to every CR example)

Direct follow-up: "does the CR resolve based on manifest feature?" —
confirmed via code that `sdd cr submit`/`sdd cr check` resolve
`feature_name = --feature or manifest.project.feature`, same as every
other command — but no CR example anywhere in the docs actually showed
`--feature`, exactly the drift risk this session's Feature Drift Check
work has been guarding against elsewhere.

### Changed

- `packs/_shared/full/.github/prompts/change.prompt.md` (canonical
  source) — Step 7's "Submit for Stakeholder Review" now runs `sdd cr
  submit --cr CR-{NNN} --feature {feature}` (was bare), with a note
  explaining why: CR numbering restarts per feature (each has its own
  `changesets/` folder), so an implicit resolution risks acting on the
  wrong feature's CR after a Feature Drift Check-class scenario. Same fix
  applied to both `sdd cr check` mentions. Synced to all 5 packs.
- The pre-existing `/jira-push chg CR-001` example (a different command)
  also gained `--feature`, same reasoning.

### Added

- A "Change Requests (CR) — Submit for Review" subsection to all 5
  packs' `HOW-TO-USE.md`.
- A `### sdd cr` entry to `cli-python/README.md`'s CLI command
  reference — this command had no entry there at all before now.

### Verified

- `cli-python` pytest: 993/993 (no `.py` files touched, pure prompt/doc
  content). `check-cross-references.py`: clean across all 6 packs.
  `sync-blocks.sh`: idempotent across two consecutive runs.
  `test-setup.sh`: 19/19.

---

## [2.9.20] — 2026-08-09 (New: `sdd feature list` / `sdd feature status`)

Follow-up on two direct requests: "let us have feature list" (after
recommending against a `manifest.yml` `project.features` list — the
filesystem is already the source of truth, and a manifest list would be a
second, driftable copy of it — a lightweight generated CLI command was
proposed instead and accepted), and "is there a sdd to check the status
of a feature ... what is approved and what is pending and who ... what we
show in dashboard" — there wasn't one that works without Jira.

`sdd review status` already existed but requires `jira:` configured and
only shows Jira-tracked document reviews. The dashboard's own data
(`build_project_status`/`build_feature_status` in `status.py`) already
works in every review mode — chat, local, jira — by reading each
document's `Status:` header and `## Approvals` table directly, but was
only ever exposed via the dashboard's HTTP handler, with no terminal
equivalent.

### Added

- `sdd feature list` — every feature folder under `.specify/features/`,
  each with its current pipeline stage and a `(current)` marker.
- `sdd feature status [--feature NAME]` — full pipeline (done/current/
  upcoming/skipped steps with who-to-ask-next hints), per-document
  Approvals-table detail (who's approved, who's pending, by role), task
  progress, and Business Objective rollup — the same picture `sdd
  dashboard` renders for one feature, as terminal text, with zero
  `integrations.yml`/Jira requirement.

Both call `build_project_status()`/`build_feature_status()` directly — no
new data model, no `manifest.yml` schema change, nothing that could drift
from what the dashboard shows.

### Changed

- Promoted `status.py`'s private `_list_feature_names()` to a public
  `list_feature_names()` (kept as an internal alias too, so no existing
  call site changed) — `sdd feature` and the dashboard now share the one
  canonical directory scan.

### Verified

- `cli-python` pytest: 993/993 (983 pre-existing + 10 new).
- `ruff check`/`format`: clean. `mypy`: zero new errors.
- Manually smoke-tested end-to-end against a hand-built 2-feature
  project.

---

## [2.9.19] — 2026-08-09 (Fix: multi-feature Confluence page overwrites and Jira ticket-identity collisions)

Prompted by a direct request to actually test whether multi-feature support
works "all over the project — every prompt, jira, confluence." It didn't,
fully. Tracing every `project_name`/`feature_name` usage through the real
CLI code (not just prompts) and running `_resolve_page_title` against the
actual default config confirmed: two features pushing the same doc type
(brd, use-cases, srd, ...) would silently overwrite each other's Confluence
page, since page lookup is by title and the default title had no
`{feature}` in it anywhere.

### Fixed

- `config.py`'s `_integrations_template()` (what `sdd config init` actually
  scaffolds) had **no `{feature}` placeholder at all** for any per-feature
  doc key. Fixed to match the already-correct `integrations.yml.example`
  ("feature-first" convention) — that fix had landed there in an earlier
  round but never made it into this scaffold.
- `integrations.py`'s `_DEFAULT_PAGE_MAP` fallback, and the generic inline
  fallbacks in `confluence.py`/`review.py` (a doc key with no page_map
  entry at all) — same gap, fixed.
- `review.py`'s Jira review Story summary and Open Questions summary
  omitted the feature name — ticket *lookup* was already feature-safe
  (label-scoped), but two features' tickets showed identical summary text,
  indistinguishable in Jira's own UI.
- `cr.py`'s CR (Change Request) Jira idempotency label was **worse** — a
  real functional bug, not just display: no feature qualifier at all, and
  `CHG-NNN` numbering is per-feature, not globally unique, so two
  features' own "CHG-001" resolved to the **same** Jira ticket — one
  feature's CR review silently reusing/overwriting an unrelated feature's
  ticket. `cr check` (which had no `--feature` resolution at all) fixed to
  match.

### Added

- `feature_collision_warning()` in `confluence.py` — a safety net for
  **existing** projects whose `integrations.yml` already has an explicit
  title predating this fix (an explicit entry is never silently rewritten
  by `sdd upgrade`). Wired into `sdd confluence push`/`draft` as a hard
  block with a new `--force` flag to override; wired into `review.py`'s
  push paths as a non-blocking warning where there's no CLI flag surface
  to gate on (including the dashboard's HTTP approve endpoint).

No `manifest.yml` schema changes — this is CLI code and a scaffold
template. An already-scaffolded project's `integrations.yml` is never
rewritten by `sdd upgrade`; add `{feature}` to its `page_map` entries by
hand, or rely on the new warning in the meantime.

### Verified

- `cli-python` pytest: 983/983 (968 pre-existing + 15 new).
- `ruff check`/`format`: clean. `mypy`: no new error classes.
- Manually confirmed the actual collision before/after the fix — COLLISION
  → distinct titles for brd/use-cases/srd.

---

## [2.9.18] — 2026-08-09 (Fix: cross-feature naming collision in `{Feature Name}` — new `project.feature_display_name` field)

Direct follow-up from the `sdd project-type migrate` work: `{Feature Name}`
(used in every document header, Confluence page title, and Jira Epic
Summary) previously resolved only from `project.name` — one project-wide
field. On a project with more than one feature — exactly the scenario the
prior two rounds this session were built to support — every feature's
documents would carry the *same* `{Feature Name}`, and Confluence page
titles/Jira Epic summaries would collide (Confluence page lookup is by
title).

### Added

- `project.feature_display_name` — new optional `manifest.yml` field.
  When present and non-empty, it fills `{Feature Name}` instead of
  `project.name`. Empty by default, so every existing single-feature
  project needs zero changes (falls straight back to `project.name`).
  Added to all 5 packs' `.specify/manifest.yml` template, right after
  `feature`.

### Changed

- `packs/_shared/blocks/feature-name-convention.md` — new resolution
  order: `project.feature_display_name` → `project.name` →
  `project.feature`. Synced into all 5 packs' `CLAUDE.md`.
- `packs/_shared/full/.github/prompts/specify-brd.prompt.md`'s Jira Epic
  Summary line updated to match.
- `packs/_shared/blocks/feature-drift-check.md` — clarified that an
  intentional `project.feature` switch should also move
  `project.context_file` and (on a multi-feature project)
  `project.feature_display_name` together, not just `project.feature`
  alone.
- All 5 packs' `HOW-TO-USE.md` "Working on Multiple Features" section —
  corrected to mention `feature_display_name` explicitly, superseding a
  weaker version from the previous round that undersold the actual
  Confluence/Jira title-collision risk.

### Verified

- `cli-python` pytest: 968/968 (unaffected — pure prompt/template
  content, no Python code touched).
- `check-cross-references.py`: clean across all 6 packs. `sync-blocks.sh`
  run three times consecutively with zero drift (after fixing a
  real staleness bug caught mid-implementation — see commit for detail).
- `test-setup.sh`: 19/19. `test-setup-micro.sh`: 12/12.
- All 5 packs' `manifest.yml` template manually confirmed to parse as
  valid YAML with `feature_display_name` present and empty by default.

---

## [2.9.17] — 2026-08-09 (New: `sdd project-type migrate` — guided project_type migration for sdd-universal)

Prompted directly by live-testing: a user's real project (a `validation-service`
backend on `sdd-universal`, `project_type: backend-service`) needed a second
feature of a genuinely different kind — an admin UI to manage its rules. After
working through why that calls for `project_type: fullstack` rather than a
per-feature type field (`constitution.md` is one document for the whole
project, not per-feature — see the discussion that led here), the user asked
for a real, guided migration path instead of "hand-edit `project_type` and
remember to separately run `/change`" with no guardrails at all.

### Added

- `cli-python/sdd/utils/project_type.py` — `EXTENDED_DOCS_BY_TYPE` (which of
  `component-spec`/`ux-flow`/`screen-spec` each `project_type` uses —
  promoted out of `sdd/utils/status.py`, which now imports it instead of
  keeping its own private copy, so the two can never drift), plus
  `classify_migration()`, which compares two `project_type`s' extended-doc
  applicability and flags a migration "lossy" if it would drop a doc type
  already in use.
- `cli-python/sdd/commands/project_type.py` — `sdd project-type show` and
  `sdd project-type migrate --to <type>`. Dry-run by default: prints the
  compatibility report and writes nothing. `--apply` writes
  `manifest.yml`'s `project_type`; on a lossy migration it refuses unless
  `--force` is also passed. Deliberately never touches `constitution.md` —
  Tech Stack row compatibility can't be determined mechanically, so
  extending the constitution for the new type is always left to `/change`
  (change type Technical), which the command's own output points to.
- "Migrating project_type" section in `packs/sdd-universal/CLAUDE.md`
  (right after "Upgrading Scope") with the full 4-step guided procedure,
  and a matching short section in `HOW-TO-USE.md`. sdd-universal-only —
  the other 4 packs each have one fixed tech stack baked into their own
  constitution and no `project_type` field to migrate at all.
- `### sdd project-type` entry in `cli-python/README.md`'s CLI command
  reference.

### Verified

- `cli-python` pytest: 968/968 (945 pre-existing + 23 new).
- `ruff check`/`format`: clean. `mypy --ignore-missing-imports sdd/`:
  error count unchanged before/after (same 15 pre-existing errors,
  confirmed via diff against a stashed baseline).
- Manually smoke-tested the CLI end-to-end: dry-run doesn't write;
  `--apply` on a safe migration writes; `--apply` on a lossy migration
  without `--force` refuses (exit 1); `--apply --force` writes; an
  invalid target type is rejected (exit 2).
- `check-cross-references.py`: clean across all 6 packs. `sync-blocks.sh`:
  confirmed only `sdd-universal`'s own `CLAUDE.md`/`HOW-TO-USE.md`
  changed. `test-setup.sh`: 19/19.

---

## [2.9.16] — 2026-08-09 (New: Feature Drift Check — guards against two chat sessions sharing one project.feature)

Prompted by a live-testing question: a user running two chat sessions
against the same project folder, one per feature, asked how a single
`manifest.project.feature` field could possibly work for both at once.
It can't, mechanically — every command's own "Before Starting" step
re-reads `manifest.yml` fresh and substitutes `{manifest.project.feature}`
directly into every save/read path, with no per-chat-session isolation.
Whichever chat last changed the field "wins"; the other chat's next
command silently follows the new value instead of the feature it had
actually been working on — no error, no warning, just a silently wrong
target folder.

### Added

- `packs/_shared/blocks/feature-drift-check.md` — new shared block,
  inserted into all 5 packs' `CLAUDE.md` right after "Startup (every
  session)": once a conversation has established which feature it's
  working on, compare that against `project.feature` every time a
  command re-reads `manifest.yml`; if they now disagree, STOP before
  reading/writing anything and ask the user to confirm which feature to
  use, rather than silently following the changed value. No effect on a
  fresh conversation's first command — nothing yet to contradict.
- A "Working on Multiple Features (or Multiple Chat Sessions)" section in
  all 5 packs' `HOW-TO-USE.md` (before "File Ownership"): documents the
  existing multi-feature-per-project model (each feature already gets
  its own `.specify/features/{feature}/` folder; `sdd dashboard` already
  shows every feature regardless of which is "current" — this was
  already true, just previously undocumented), explains the new drift
  check, and recommends `git worktree add` (a separate `manifest.yml`
  per worktree) as the clean way to actually parallelize two chats on
  two features, instead of sharing one `manifest.yml`.

`sdd-micro` is intentionally excluded — its own `CLAUDE.md` already
documents it as single-purpose by design, with no multi-feature split,
so this concern doesn't apply there.

### Verified

- `check-cross-references.py --verbose`: all cross-references resolve
  across 6 packs.
- `test-setup.sh`: 19/19 passed. `test-setup-micro.sh`: 12/12 passed.
- `sync-blocks.sh` run twice consecutively: only the intended 5
  `CLAUDE.md` + 5 `HOW-TO-USE.md` + 1 new block file changed, no further
  drift on the second run (idempotent).
- `cli-python` pytest: 934/934.

---

## [2.8.40] — 2026-08-08 (Audit: Jira/Confluence review-flow consistency across every prompt in all 5 packs)

Requested audit, following the prior round of live-testing fixes: check
every prompt for deviations, confirm where Confluence/Jira checks happen,
and verify approval correctly falls back to local chat or the dashboard
when neither is configured. Found and fixed 4 findings — two real
functional gaps in standalone utility commands, two documentation-accuracy
gaps in the canonical shared blocks themselves.

### Fixed

**1. `/submit-review` had no confluence-only branch at all.** It was a
third, independently hand-written "submit for review" implementation,
never synced from the canonical `submit-for-review-step` block — it
branched only on `jira:` presence. In a confluence-only project, running
`/submit-review` directly skipped straight to chat mode; the document
never reached Confluence. Fixed by rewriting it to delegate directly to
the same shared blocks every document-generation command already uses.

**2. `/check-review` bypassed the CLI's own graceful no-Jira handling,
losing dashboard comments.** Its "No-Jira fallback" explicitly skipped
calling `sdd review check` when `jira:` was absent — but that command
already handles the no-Jira case gracefully, surfacing unacknowledged
dashboard comments even with zero Jira/Confluence configured. Fixed with
a precisely-targeted change: always call the CLI; only fall back to a
hand-written local check when the `sdd` tool itself isn't installed.

**3. `review-decision-step`'s own prose understated dashboard-comment
capability**, saying comments surface "when Jira is configured" when
they actually surface in pure-local mode too. Rewrote the exit-code
branches to state this correctly.

**4. `submit-for-review-step`'s three branch headings didn't literally
enumerate a jira-only (no confluence:) configuration** — the correct
outcome (fall to chat) was only reachable by inference. Added an explicit
fourth branch naming this case directly.

### Verified

- cli-python pytest 934/934 (no Python code touched, only markdown/prompt
  files)
- `check-cross-references.py` clean across all 6 packs
- `test-setup.sh` (19/19) and `test-setup-micro.sh` (12/12) both pass
- `assert-output.sh` clean against `examples/todo-api` (33/33)
- `sync-blocks.sh` confirmed idempotent

---

## [2.8.39] — 2026-08-08 (Fix: Confluence page push could get stuck on a 409 Conflict, even after a manual retry)

A user hit a `409 Conflict` while `/plan-lld` pushed a 19-diagram
`lld.md` to Confluence, then hit the *identical* 409 again on a manual
retry — correctly diagnosing it as a real bug, not a transient blip.

### Fixed

`ConfluenceClient.upsert_page()` read a page's version once, then wrote
`version + 1` with no handling for Confluence rejecting that write
because the page had already moved past it (a real, observed race:
`sdd review submit` pushes the same page twice in one run — the initial
push, then again right after to stamp the Jira ticket's status banner
on, with a burst of diagram-attachment uploads in between — and
Confluence Cloud's read path can lag slightly behind its own
just-completed write in that window). The existing generic HTTP retry
layer (429/5xx, added in an earlier fix) deliberately doesn't cover 409
for good reason: resending the exact same request with the exact same
stale version number just reproduces the exact same 409 — precisely
what happened when the user retried by hand.

`upsert_page()` now catches a 409, re-fetches the page's actual current
version, and retries the write with the corrected number — up to 3
attempts. Any other error, or a 409 on the final attempt, still raises
immediately. Fixes all 4 call sites that share this method in one
change.

### Verified

- cli-python pytest 934/934 (930 pre-existing + 4 new)
- ruff check/format clean; mypy clean on the changed file
- `check-cross-references.py` clean across all 6 packs
- `test-setup.sh` (19/19) passes

---

## [2.8.38] — 2026-08-08 (Fix: the Approvals-table flip has never matched a single real document — plus role-scoped approval evidence)

A user shared a live `design.md` approval transcript: an agent
blanket-approved all three Approvals-table roles (Architect/Tech
Lead/Stakeholder) off one Jira ticket assigned only to Architect, then
self-corrected mid-session. Asked to make that discipline consistent
across all documents, not luck-of-the-draw. Implementing that surfaced a
much bigger, already-live bug.

### Fixed

**1. The Approvals-table `Pending → Approved` flip has never matched a
single real document, on any template, ever.** Its regex expected a
3-column `Role | Pending | Date` row shape. Every one of the 20 templates
that have an `## Approvals` section is actually 4 columns — `Role |
Approver | Status | Date`. Tested the regex against real rows from real
templates: zero matches. The dashboard's Approve button calls this
function directly, with no LLM pre-editing the file — so every
dashboard-driven approval has flipped the `Status:` header correctly but
left the Approvals table stuck on `Pending` underneath it, silently,
this whole time. The bug never showed up in the normal chat-driven flow
only because the agent edits the table text itself before this
now-fixed CLI call runs (as a no-op safety net with nothing left to do).
The existing unit test used the same wrong 3-column fixture, so nothing
ever caught it.

**2. The Approver column was never filled by the CLI path either.**
`sdd review approve --by "..."` never actually passed that name through
to the flip function — same gap in the dashboard's approve handler.

**3. Added role-scoped evidence for Jira-driven approvals.** When a
Jira ticket approves a document, that only speaks for its one assigned
reviewer — not every role a multi-role Approvals table lists. A new
`sdd review approve --role` flag (and matching logic in
`review-decision-step`, the shared block every review-gated document
uses) now flips only the Approvals-table row matching that reviewer's
role when the approval came from Jira, leaving other RACI rows `Pending`
— falling back to the old blanket-flip on a role/wording mismatch, and
unchanged for pure chat/local approvals, which have no per-role signal
to scope to in the first place.

### Verified

- cli-python pytest 930/930 (922 pre-existing + 8 new)
- ruff check/format clean on all changed files
- `check-cross-references.py` clean across all 6 packs
- `test-setup.sh` (19/19) and `test-setup-micro.sh` (12/12) both pass
- `sync-blocks.sh` confirmed idempotent

---

## [2.8.37] — 2026-08-08 (Fix: `sdd review apply` never reverted a document's Approved status, and could never reopen a closed Jira ticket)

A user asked how post-approval revisions actually work — does the status
change, does it create a new Jira ticket, does a closed ticket get
reopened? Tracing the actual code (not assuming) surfaced two real gaps,
which the user then asked to have fixed.

### Fixed

**1. The document's own `Status: Approved` header was never reverted.**
When `/clarify` (or reviewer feedback) patches an already-Approved
document, only the version history got a new row — the header still
claimed `Approved`. Added `_mark_md_needs_revision()`, the direct
counterpart to the existing `_mark_md_approved()`: reverts `Status:
Approved` back to `Draft` (or `Proposed` for `adr.md`), scoped to the
document's front matter only, same corruption-safety reasoning as its
counterpart. No-op for a document that was never Approved. Wired into
`sdd review apply` unconditionally — fires the same way in every
integration mode, including pure chat/local with no Jira/Confluence at
all.

**2. `JiraClient` had no way to reopen a ticket.** There was literally no
transition/workflow-status capability in the codebase — a ticket already
moved to Done/Closed stayed there forever; `sdd review apply` could only
ever post a comment on it. Added `get_transitions()` and
`transition_issue()` (the real Jira REST transitions API), wired into
`sdd review apply`: after the existing re-review comment, it now attempts
a transition to a new opt-in `reopen_status` setting in
`integrations.yml` (unset by default — workflow status names vary too
much across orgs to guess safely). Silently a no-op if the ticket's
already there or the workflow has no path to it — never blocks the rest
of the command.

Documented the full actual behavior — what `sdd review apply` does to an
Approved document, step by step — in the review-gates shared block
(`CLAUDE.md`, all 5 packs), replacing what had only ever been described
at the "push/notify" level.

### Verified

- cli-python pytest 922/922 (904 pre-existing + 18 new)
- `check-cross-references.py` clean across all 6 packs
- `test-setup.sh` (19/19) and `test-setup-micro.sh` (12/12) both pass
- `sync-blocks.sh` confirmed idempotent

---

## [2.8.36] — 2026-08-08 (Fix: brd.md's ACT-NNN stakeholder IDs never got back-filled by `/specify-uc`)

Found by a user: after the BRD is created and `/specify-uc` runs, `brd.md`
§3 Stakeholders table still showed `_(set by /specify-uc)_` placeholders
instead of real `ACT-NNN` values.

### Fixed

`specify-uc.prompt.md`'s instruction to back-fill `brd.md` §3 existed and
was in the right place, but had almost no structural weight — a single
bolded inline paragraph with no heading, sandwiched between the
"Save to:"/"Write:" bullets and the "Draft Jira Stories" paragraph, never
referenced again in the command's own completion message. Nothing in the
command's output confirmed whether the back-fill had actually happened —
the same failure mode as v2.8.34's `brd.md` Build Effort field, which was
fixed the same way there.

Promoted it to its own `### Back-fill BRD Stakeholders (mandatory — do
not skip)` heading with explicit numbered steps (match each remaining
placeholder row to its actor by role, resolve every cell to a real
`ACT-NNN` or `_(N/A)_`, save + regenerate `brd.summary.md`), and added a
line to the completion message confirming it happened by name.

### Verified

- cli-python pytest 904/904
- `check-cross-references.py` clean across all 6 packs
- `test-setup.sh` (19/19) and `test-setup-micro.sh` (12/12) both pass
- `sync-blocks.sh` confirmed idempotent

---

## [2.8.35] — 2026-08-08 (Audit: review-gate consistency across every living and feature document — 2 behavioural gaps + 1 sync-tooling bug)

Requested audit: check that every living document (Data Model, Security
Design, API Spec) and feature document creates a review ticket, pushes to
Confluence, and pulls review from Jira/Confluence the same way when
either is configured — falling back to chat otherwise. Found two real
behavioural gaps, and a third issue in the sync tooling itself while
fixing one of them.

### Fixed

**1. `validate`/`analyze`/`clarify` skipped the Confluence-only fallback.**
These three documents only ever called `sdd review submit` (which
requires both `jira:` and `confluence:` configured, confirmed in the
CLI) and fell straight to pure chat mode if it failed. Every other
reviewed document falls through to `sdd confluence draft` first when
only Confluence is configured. In a Confluence-only project, these three
documents silently never reached Confluence — contradicting the
project's own "Confluence stays in sync in every mode" claim. Fixed by
switching them onto the same shared submission/approval blocks the
other 12 review-gated commands already use, preserving each document's
own approval-scope caveat as trailing prose.

**2. `api-spec.md`'s first version never got a review ticket.** Unlike
its sibling living documents (Data Model, Security Design), the API
Spec — generated inside `/plan-design` on the first service-providing
feature — had no submission step on first creation. It only reached
Confluence/Jira later, when a subsequent feature updated it. Fixed by
adding the same shared submission block right after first-time
generation, independent of `design.md`'s own approval.

**3. `sync-blocks.sh` ran its two sync passes in the wrong order.** Ten
`.github/prompts/` files that are synced whole-file from `_shared/full/`
(`specify-brd`, `specify-uc`, `specify-srd`, `specify-doc`, `plan-arch`,
`plan-hld`, `plan-adr`, `plan-design`, `plan-lld`, `task`) also embed the
shared submission/approval block markers — but the full-file sync ran
*after* the marker-fill pass, so every run silently overwrote the
just-refreshed marker content with whatever stale copy was baked into
`_shared/full/`'s own file. Confirmed live: `validate.prompt.md` (never
full-file-synced) had the current approval logic; `specify-brd.prompt.md`
(full-file-synced) was missing a step added to the canonical block since
these files were last hand-synced — same pack, same sync run. Fixed by
reordering the two passes so the marker-fill pass always runs last, and
refreshed the 10 files' own stale embedded copies. Added a rule to
`packs/_shared/README.md` documenting the gotcha.

### Verified

- cli-python pytest 904/904
- `check-cross-references.py` clean across all 6 packs
- `test-setup.sh` (19/19) and `test-setup-micro.sh` (12/12) both pass
- `assert-output.sh` clean against `examples/todo-api` (33/33)
- Three consecutive `sync-blocks.sh` runs confirmed idempotent (zero
  diffs after the first)

---

## [2.8.34] — 2026-08-08 (Fix: two sequencing bugs found during real `/checklist` testing — one a genuine framework logic conflict)

Found by a user running the framework end-to-end: after approving the last
extended document, then running `/checklist`.

### Fixed

**1. `/specify-doc` chat message skipped the mandatory `/checklist` gate.**
The dashboard correctly showed "Spec Quality Checklist" as the next step at
mvp+/full scope, but the "all documents complete" chat message named
`/validate` unconditionally — a pure prompt-text bug with zero awareness
that `/checklist` is mandatory (not optional) at that scope. Fixed
`specify-doc.prompt.md`'s "none remain" branch to check
`manifest.project.scope`: mvp/full now names `/checklist` (mandatory) as
the next command; pilot still offers it as optional before `/validate`.

**2. `brd.md` generated an unresolvable `[NEEDS CLARIFICATION]` marker by
design.** `brd-template.md` §9's "Build effort (T-shirt)" row was written
as "Derived from analyze.md (filled after /analyze)" under a blanket rule
that marks any unfilled Investment Summary item `[NEEDS CLARIFICATION]` —
but `analyze.md` doesn't exist until `/analyze` runs, which is *after*
`/validate` in the pipeline order (SPECIFY → GATE-1 → VALIDATE → ANALYZE),
and `checklist.prompt.md`'s CRITICAL rule blocks `/validate` on any
unresolved marker with no per-field exception. A user's own `/checklist`
run surfaced this exact conflict. Three-part fix:
- `brd-template.md` §9 now writes plain deferred text — "Pending —
  estimated after /analyze" — for this field, never a
  `[NEEDS CLARIFICATION]` marker.
- `analyze.prompt.md` gained a new "Update BRD Build Effort" step that
  actually implements the template's own long-standing but
  never-implemented promise: derives a T-shirt size from the COMPLEXITY
  ratings `/analyze` just produced and writes it back into `brd.md` §9.
- `checklist.prompt.md`'s CRITICAL rule #1 gained an explicit
  known-exception carve-out for this field, as a defensive safety net for
  any `brd.md` generated before this fix.

`specify-doc.prompt.md`, `brd-template.md`, and `checklist.prompt.md` are
`_shared/full/` sources — edited once, synced to all 5 packs.
`analyze.prompt.md` is authored per-pack — the same "Update BRD Build
Effort" step was added individually to all 5 packs, verified identical.

### Verified

- cli-python pytest 904/904 (no Python code touched, only markdown/prompt
  files)
- `check-cross-references.py` clean across all 6 packs
- `test-setup.sh` (19/19) and `test-setup-micro.sh` (12/12) both pass
- `assert-output.sh` clean against `examples/todo-api` (33/33)

---

## [2.8.33] — 2026-08-08 (Fix: 4 real bugs found during a living-document review cycle — one a genuine data-corruption bug)

Found by a user actually testing the framework — approving a Data Model
document, then generating and reviewing a Security Design document.

### Fixed

**1. Document corruption in `sdd review approve --local`.** The Status-header
flip used an unanchored regex-replace across the **entire** document, not
just the real header. `data-model.md`'s own template (unlike every other
spec template) had no `Status: Draft` header field at all, so the regex's
first — and only — match was a §3 enum field written as `RuleVersionStatus:
DRAFT, SUBMITTED, PUBLISHED, RETIRED`, silently mangled into
`RuleVersionStatus: Approved, SUBMITTED, PUBLISHED, RETIRED`. Fixed by
scoping the flip to the document's front matter (before the first `## `
heading). Root cause addressed too: added a missing `Status: Draft` header
field to `data-model-template.md` and `security-design-template.md` across
all 5 packs, restoring correct Draft/Approved tracking for these two living
docs.

**2. Severe Confluence-pull data loss.** `cf_to_md.py`'s "strip remaining
`ac:*` elements" cleanup paired an opening `ac:` tag with the *next* `ac:`
closing tag of any name, not necessarily its own. A page with a `local-svg`
diagram, followed later by another unhandled/nested `ac:` element, had
everything between them silently deleted — 6 tables and an entire numbered
section, in the reporting user's case. Fixed with a backreference so a
match can only ever span exactly one element's own content.

**3. HTML comments mangled on both push and pull.** A comment like
`specify-doc.prompt.md`'s required `<!-- security-sign-off: ... -->` marker
fell through to the paragraph branch on push, HTML-escaping it into
*visible* garbage text on the actual Confluence page, then got deleted
outright by the generic tag-stripper on pull. Fixed on both sides.

**4. `security` vs `security-design` doc-key inconsistency.** `specify-doc.prompt.md`'s
own prose calls it `/specify-doc security`, but `sdd review submit --doc
security` and `sdd confluence draft --doc security` both fail — every `sdd`
command actually requires `security-design`. Added an explicit resolution
rule right after the command's Input section.

### Verified

- `cli-python` pytest 904/904 (892 pre-existing + 12 new regression tests
  covering all four bugs, including the exact reported corruption/data-loss
  shapes).
- `ruff check`/`ruff format` and `mypy --ignore-missing-imports` (matching
  CI's exact invocation) both clean.
- `check-cross-references.py` clean across all 6 packs; `test-setup.sh`
  (19/19) and `test-setup-micro.sh` (12/12) both pass.

---

## [2.8.32] — 2026-08-08 (Add: project-level "Living Documents" dashboard section)

Reported by a user: they couldn't find **Data Model** on the dashboard at
all, and after generating it its status stuck showing "waiting for
review." The second part turned out to be correct — a Draft document is
genuinely awaiting approval — but the first part was a real gap.

Data Model and Security Design are living/service-level documents: one
shared file for the *whole project* (`.specify/service/{key}.md`), not
per-feature. But the dashboard only ever inserted them as ordinary steps
inside each **feature's own** pipeline card — meaning on a multi-feature
project the same document showed up duplicated once per feature card,
each computed from the identical underlying file, and neither instance
had the Approve button, Confluence/Jira links, or Details panel every
per-feature document already gets (the per-feature Documents table only
ever scanned `.specify/features/{feature}/`, never `.specify/service/`).

### Added

- New project-level **"Living Documents"** dashboard section, shown once
  between the Project/Constitution cards and the Features Overview table —
  not nested inside any one feature. Full functionality: status badge,
  Approve button, Confluence/Jira links, and the same Details panel
  (Content/Approvals/Comments) every per-feature document has.
- `_service_level_docs()` in `status.py`, exposed as `living_documents` /
  `living_local_links` in the dashboard's JSON.

### Fixed

- Removed the duplicated Data Model / Security Design steps from every
  feature's own pipeline — they now appear exactly once, at the project
  level, regardless of how many features exist.

### Known follow-up

- `api-spec` and `component-library` (also living/service-level docs) are
  **not** included in this section yet — `api-spec` has no standalone
  `/specify-doc` command to link to (it's produced by `/plan-design §3`),
  and neither has dashboard tracking to build on. Real gap, separate scope.

### Verified

- `cli-python` pytest 892/892 (889 pre-existing, net +3 — 5 tests
  rewritten against the new function, 3 new end-to-end tests added,
  including the exact reported multi-feature duplication scenario).
- `ruff check`/`ruff format` and `mypy --ignore-missing-imports` (matching
  CI's exact invocation) both clean; `node --check` on `app.js` clean.

---

## [2.8.31] — 2026-08-08 (Fix: re-pushing a local-svg diagram to Confluence a second time always failed)

Reported by a user during testing: pushed a page with a `local-svg` diagram
once successfully, then re-pushed it (no content change) — the SVG
attachment upload failed **every single time** with:

```
BadRequestException: Cannot add a new attachment with same file name as
an existing attachment: diagram-1.svg
```

The page body itself still updated fine, so the failure was easy to miss
unless you were watching stderr — but the diagram attachment silently
never got its new content.

`confluence_client.py`'s `upload_attachment()` always POSTed to
Confluence's *create*-a-new-attachment endpoint. Its own docstring claimed
Confluence auto-versions an existing same-named attachment the way page
updates do — **that claim was simply wrong**. Confluence Cloud rejects a
second create with an already-existing filename outright. Updating an
existing attachment's content requires a different endpoint entirely
(`POST .../child/attachment/{attachmentId}/data`), which needs the
attachment's ID first.

### Fixed

- New `get_attachment_by_filename()` lookup (Confluence's attachment-list
  endpoint supports filtering by filename server-side — one extra call, not
  a fetch-all-and-scan). `upload_attachment()` now checks for an existing
  same-named attachment first and routes to the update-data endpoint when
  one exists, the create endpoint otherwise. A page's first push (no
  existing attachment) behaves identically to before; only the
  second-and-later push of the same diagram was affected — exactly what
  was broken.

### Verified

- `cli-python` pytest 889/889 (882 pre-existing + 7 new: `TestGetAttachmentByFilename`
  and `TestUploadAttachmentUpdatesExisting`, covering the lookup and both
  the create and update-data code paths — including the exact reported
  collision scenario).
- `ruff check`/`ruff format` and `mypy --ignore-missing-imports` (matching
  CI's exact invocation) both clean on the changed files.

---

## [2.8.30] — 2026-08-08 (Add: document_reviews examples for living/service-level docs)

Follow-up to the previous round's `issue_hierarchy`/`page_map` audit: a user
asked to double-check `data-model`, `security-design`, `api-spec`, and
`component-library` were fully documented in `integrations.yml.example`.
They had a `page_map` entry (Confluence) each, but no `document_reviews`
entry (Jira) anywhere in the shipped example — confirmed as by-design
(`specify-doc.prompt.md`'s documented fallback: `sdd review submit` fails
with no `document_reviews` entry, falls through to `sdd confluence draft`
instead of silently dropping to chat mode), but a team that *does* want a
formal Jira gate on one of these had nothing to copy from.

### Added

- Commented-out `document_reviews` example entries for all four living/
  service-level docs. Each gets its **own single-entry phase** (e.g.
  `phase: data-model, sequence: 1`) rather than sharing one with each other
  or with `design` — they're independent (any order, no dependency between
  them), and the predecessor check gates strictly on matching phase +
  `sequence - 1`, so sharing a phase would wrongly block one doc on
  another's approval.

All four entries stay fully commented out by default — active
`document_reviews`/`page_map` keys, and every existing project's behavior,
are completely unaffected.

### Verified

- `cli-python` pytest 882/882 (no change — inert commented content); the
  file still parses as valid YAML and the active key sets are unchanged.
- `check-cross-references.py` clean across all 6 packs; `test-setup.sh`
  (19/19) and `test-setup-micro.sh` (12/12) both pass.

---

## [2.8.29] — 2026-08-08 (Fix: bare Confluence push missing the context.md page)

Prompted by a user asking to double-check `integrations.yml.example`
documented everything discussed in the previous round. Re-reading it end to
end turned up a real gap: **`context` was missing entirely** — not in
`page_map`, not in the code's default page map — the exact same bug class
fixed for `constitution` back in v2.8.23, just never caught for `context.md`
at the time.

`confluence.py` special-cases `"context"` to always resolve to `"{feature}
— Context"` regardless of `page_map`, so `sdd confluence draft --doc
context` (what `/create-context` actually calls) always worked fine on its
own. But a bare `sdd confluence push` (no `--doc`) iterates
`page_map.keys()`, and `"context"` was never in that set — so a bulk push
silently never attempted the context page.

### Fixed

- Added `"context"` to `_DEFAULT_PAGE_MAP` (`sdd/utils/integrations.py`),
  the wizard's minimal fallback template (`_integrations_template()` in
  `sdd/commands/config.py`), and `integrations.yml.example`'s `page_map`
  (with the same "value is ignored, only presence matters" comment already
  on the `constitution` entry).

### Verified

- `cli-python` pytest 882/882 (880 pre-existing + 2 new:
  `TestConfluencePushIncludesContextByDefault`, mirroring the existing
  constitution regression test class).
- `ruff check`/`ruff format` and `mypy --ignore-missing-imports` (matching
  CI's exact invocation) both clean on the changed files.
- `check-cross-references.py` clean across all 6 packs; `test-setup.sh`
  (19/19) and `test-setup-micro.sh` (12/12) both pass.

---

## [2.8.28] — 2026-08-08 (Jira issue-type overrides, CR parent linking, constitution draft push)

Prompted by a user request: `project_keys` already lets you override the
Jira **project** per level (`feature`/`story`/`task`/`review`/`chg`/`cr`) —
they asked for the same on the Jira **issue type**, plus a clear explanation
of the parent-child hierarchy and what distinguishes `chg` from `cr`.

Investigating found the issue-type overrides didn't actually work at all:
`load_integrations()` built the Jira config with only `feature`/`story`/
`task` hardcoded, silently dropping any `review`/`chg`/`cr` entry written
under `issue_hierarchy:` — even though the per-call-site fallback code
implied it was supported. Also found, while tracing the hierarchy: `sdd cr
submit`'s Change Request review ticket was the only Jira issue type this
CLI ever created with **no parent link at all** — every other type (Epic,
Story, Task, review tickets) nests under the Epic; CR review tickets just
sat standalone.

### Added

- `JiraConfig.issue_type_for(level)` — resolves the Jira issue type for
  `feature`/`story`/`task`/`review`/`chg`/`cr` (plus the `epic` alias for
  `feature`), honoring `issue_hierarchy:` overrides. Every issue-creation
  call site in `jira.py`/`review.py`/`cr.py` now routes through it.
- `sdd cr submit` now self-bootstraps the Epic and links the CR review
  ticket under it, matching every other issue type.
- Documented the full parent-child hierarchy and the `cr`-vs-`chg`
  distinction directly in `integrations.yml.example`'s `issue_hierarchy`
  comment block (the canonical source synced to every pack) and in
  `cli-python/README.md`: **`cr`** is the Change Request's own approval
  ticket (one per CR-NNN); **`chg`** is an individual dev task implementing
  one line of an already-approved CR's plan (one per CHG-NNN row, parented
  to whichever Story satisfies its FR-NNN reference — not to its own `cr`
  ticket).
- `constitution.md`'s DRAFT now pushes to Confluence immediately when
  `/specify` first generates it — same as `context.md`'s own draft push in
  `/create-context` — instead of only once GATE-1 finalization pushes it.
  A reviewer can now comment on the constitution in Confluence before
  finalizing, not only after.

### Fixed

- `issue_hierarchy: {review: ..., chg: ..., cr: ...}` overrides in
  `integrations.yml` are no longer silently discarded.

### Verified

- `cli-python` pytest 880/880 (874 pre-existing + 6 new: `TestIssueTypeFor`
  covering defaults, independent review/chg/cr overrides, and the epic
  alias; `TestCrSubmitParentLink` verifying the Epic self-bootstrap +
  parent link).
- `ruff check`/`ruff format` and `mypy --ignore-missing-imports` (matching
  CI's exact invocation) both clean on the changed files.
- `check-cross-references.py` clean across all 6 packs; `test-setup.sh`
  (19/19) and `test-setup-micro.sh` (12/12) both pass.

---

## [2.8.27] — 2026-08-08 (Fix: {Feature Name} document header had no defined source)

Reported by a user: a generated BRD's `# Feature: {Feature Name}` header
showed "NIPE Validation Service" while `manifest.yml` said `name:
Validation` — the two had silently diverged.

`{Feature Name}` is used as a header placeholder in ~20 templates across
every pack (BRD, SRD, use-cases, design, tasks, release, etc.), but only
**one** place in any prompt file ever explicitly defined what it should
resolve to (the Jira Epic Summary line in `specify-brd.prompt.md`). Every
document-header instance was left to each session's judgment, so it could
silently drift to `context.md`'s own free-text title instead of
`manifest.yml` — and could even differ document-to-document within the same
project.

### Added

- New shared block `_shared/blocks/feature-name-convention.md`, inserted
  into each pack's `CLAUDE.md` right after the "Confirm: project.name,
  scope, feature, context_file" startup step (read at the start of every
  session, before any document is generated). States explicitly:
  `{Feature Name}` = `manifest.yml` `project.name` (falling back to
  `project.feature`), never `context.md`'s title.
- Applied to all 5 lockstep packs (backend-service, frontend-spa, fullstack,
  mobile, universal). `sdd-micro` is intentionally excluded — it's outside
  the shared-block sync system and has no BRD/SRD/etc. templates using this
  placeholder.

### Verified

- `python3 packs/_shared/tests/check-cross-references.py --verbose` clean
  across all 6 packs.
- `packs/_shared/tests/test-setup.sh` (19/19) and `test-setup-micro.sh`
  (12/12) both pass.
- Manually confirmed identical shared-block content across all 5 packs'
  `CLAUDE.md`.

---

## [2.8.26] — 2026-08-08 (Fix: "Error loading the extension!" on Confluence after Jira approval)

Reported by a user right after approving a BRD: its Confluence page showed
**"Error loading the extension!"** where the "Jira review: VALT-1 —
Approved" status banner should have been.

`review.py`'s `_jira_status_banner()` maps review status to a Confluence
panel macro name — `{"APPROVED": "success", "NEEDS_REVISION": "warning"}`,
default `"info"`. Confluence's built-in panel macros are only `info`, `tip`,
`note`, and `warning` — **there is no `success` macro** — so the page tried
to render an unregistered extension. This was invisible until now because
`PENDING` (the only status a fresh review ticket starts in) correctly used
`info`; the bug only fires once a real document reaches `APPROVED`.

### Fixed

- `APPROVED` now maps to `tip` (a real Confluence panel macro, renders as a
  green highlighted box) instead of the nonexistent `success`.

### Verified

- `cli-python` pytest 874/874 — updated `test_banner_for_approved_status` to
  assert the real macro name and that the invalid one is gone.
- `ruff check`/`ruff format` and `mypy --ignore-missing-imports` (matching
  CI's exact invocation) both clean on the changed files.

---

## [2.8.25] — 2026-08-08 (Fix: dashboard "not set in roles.yml" false negative)

Reported by a user right after filling in `roles.yml` with real names for
every role: the dashboard's Approvals detail panel still showed nothing for
any pending row — as if `roles.yml` were empty, when it wasn't.

`status.py` normalizes a document's Approvals-table **Role** cell text to
`roles.yml`'s snake_case key convention (`"Product Owner"` → `product_owner`)
to match the two up. But every shipped template's actual Role cell carries a
RACI annotation in parentheses — e.g. `brd-template.md`'s real text is
`"Product Owner (accountable — business objectives sign-off)"`, never the
bare role name. Normalizing the full string (including the parenthetical)
never matched any `roles.yml` key — **a 100% miss rate**, across every role,
every document, every project, no matter how completely `roles.yml` was
filled in. Pre-existing tests never caught this because they only ever
exercised bare role labels, not the real template shape.

### Fixed

- `sdd/utils/status.py`'s `_normalize_role_key()` now strips everything from
  the first `(` onward before normalizing, so `"Product Owner (accountable —
  ...)"` and `"DevOps/SRE (consulted — ...)"` resolve exactly like their bare
  forms always did.

### Verified

- `cli-python` pytest 874/874 (871 pre-existing + 3 new: a unit-level test
  covering every real Role-cell shape from the shipped templates, a resolver
  test, and an end-to-end test through `build_feature_status` with a real
  `roles.yml` and a real BRD-shaped Approvals table — the exact reported
  scenario).
- `ruff check`/`ruff format` and `mypy --ignore-missing-imports` (matching
  CI's exact invocation) both clean on the changed files.

---

## [2.8.24] — 2026-08-08 (Fix: dashboard GATE-1 false positive)

Found via real user testing, right after the 2.8.23 fixes: the dashboard
showed a checkmark next to **"GATE-1 — Constitution Finalized"** immediately
after `/specify` generated the constitution DRAFT — before the user had ever
told the agent "Constitution Part 2 finalized" in chat.

`constitution.md` has no machine-readable Draft/Finalized flag by design
(GATE-1 confirmation happens in chat, not in the file), so the dashboard
infers GATE-1 status from whether any real downstream spec doc already
exists in `.specify/features/{feature}/` — since the workflow can't produce
BRD/use-cases/SRD/etc. before GATE-1 passes. But `token-usage.md` lives in
that same directory and is appended to by `/specify` itself (and even
`/create-context`, which runs before `/specify`) whenever
`token-pricing.yml` is configured — both commands run *before* GATE-1 can
possibly pass. The inference's exclusion list only ever accounted for
`tasks.md` and `*.summary.md`, so any project with token logging enabled
hit this false positive on every single run.

### Fixed

- `sdd/utils/status.py`'s `_constitution_status()`: `token-usage.md` now
  joins `tasks.md` in the set of filenames excluded from the
  `any_downstream` check that infers `gate1_inferred`.

### Verified

- `cli-python` pytest 871/871 (869 pre-existing + 2 new regression tests:
  one reproducing the exact false positive — `token-usage.md` alone in the
  feature directory — and one confirming a real downstream doc still
  correctly reports `passed` alongside it).
- `ruff check`/`ruff format` and `mypy --ignore-missing-imports` (matching
  CI's exact invocation) both clean on the changed files.

---

## [2.8.23] — 2026-08-08 (Fix: Jira config resolution crash + Confluence bulk push missing the Constitution page)

**Two bug fixes**, both found via real user testing.

**1. `sdd jira push --level epic` crashed with a raw `AttributeError`.**
Root-caused by the reporting user: a hand-edited `integrations.yml` had a
second `project_key:` block under `jira:` that should have been
`project_keys:` (plural, for the per-level override section right below
it). YAML silently keeps only the *last* occurrence of a duplicate mapping
key, so the plain string from the first block was clobbered by a dict from
the second — and `jira.project_key` resolved to a dict, which then crashed
`jira_client.py`'s `find_by_label()` three call frames away with `'dict'
object has no attribute 'replace'`.

### Fixed

- `load_integrations()` now parses `integrations.yml` with a custom PyYAML
  loader that rejects a duplicate mapping key anywhere in the file at parse
  time — naming the exact line number, and suggesting the fix when the key
  is `project_key` specifically.
- `JiraConfig.key_for()`/`parent_field_for()` now validate the resolved
  value is actually a string, raising a new `JiraConfigError` that names
  the exact bad YAML key, instead of letting a malformed value silently
  propagate into a low-level HTTP helper.
- **Related gap found during investigation:** the CLI's own `--level epic`
  flag has no relationship to the config-facing level key `feature` used
  throughout `project_keys`/`custom_fields_by_level`/`parent_field_by_level`
  — so a user writing `project_keys: {epic: SUN}` (the natural thing to
  write, matching the CLI's own terminology) was silently ignored with no
  error at all. `epic` is now accepted as a bidirectional alias for
  `feature` everywhere a level name is resolved.
- Every `load_integrations()` call site (jira.py, confluence.py, cr.py,
  review.py, pr.py, dashboard.py, config.py, status.py) updated to catch
  the new `IntegrationsConfigError` alongside the existing
  `FileNotFoundError` handling.

**2. A bare `sdd confluence push` (no `--doc`) never included the
Constitution page.** `sdd confluence draft --doc constitution` worked fine
on its own (its title/path resolution is fully special-cased), but a bulk
push iterates the configured `page_map` — and both the code's default
`page_map` fallback and the `sdd config init` wizard's generated template
omitted the `constitution` key entirely, even though the full
`integrations.yml.example` reference file already had it (with a comment
explaining exactly this). A clean drift bug: the `.example` file was
updated for this reason at some point; the other two definitions of the
default doc set never were.

### Fixed

- Added `constitution` to `_DEFAULT_PAGE_MAP`
  (`sdd/utils/integrations.py`) and to the wizard template's `page_map`
  block (`sdd/commands/config.py`'s `_integrations_template()`).

### Added

- 11 new tests: 9 in `tests/test_config_and_integrations.py`
  (`TestJiraConfigRobustness`) covering duplicate-key detection (including
  the exact reported shape), wrong-shape `project_key`/`parent_field`
  values, the `epic`/`feature` alias in both directions, and a well-formed
  file loading completely unaffected by the stricter loader; 2 in
  `tests/test_confluence_push_cli.py` confirming a bare push now creates
  the Constitution page and that explicit `--doc constitution` continues
  to work.

### Verified

- `cli-python` pytest 869/869 (858 pre-existing + 11 new)
- ruff check/format clean
- `mypy --ignore-missing-imports` (matching CI's exact invocation) clean
  with no issues in 31 source files
- Manually reproduced the exact reported duplicate-key YAML shape and
  confirmed it now raises a clear error instead of crashing

---

## [2.8.22] — 2026-08-08 (Fix: `sdd confluence pull` flattened every markdown table into one run-on line)

**Bug fix.** Reported by a user testing the Confluence review round-trip on
a real project: create a draft via `sdd confluence draft`, edit it in
Confluence, then `sdd confluence pull` to bring the edits back. Every
markdown table in the pulled-back document came back as a single run-on
line with no row or column structure — silently corrupting any table-heavy
doc (the Tech Stack table in `context.md`, and BRD/SRD/design docs
generally, since `/specify` parses the Tech Stack table specifically).

### Fixed

- `cli-python/sdd/utils/cf_to_md.py` (the Confluence-storage-format-to-
  Markdown converter behind `sdd confluence pull`) had no `<table>`
  handling at all — Confluence storage format renders a table as an
  unbroken `<table><tbody><tr><th>...</th></tr>...</tbody></table>` string
  with no whitespace between tags, and with no table-aware step, the
  converter's final "strip any remaining HTML tags" pass just deleted the
  table/row/cell tags and left the cell text jammed together.
- Added a `_table_to_md()` converter: reconstructs a GFM pipe table from
  the Confluence markup — header row, an alignment-marker separator row
  from any `style="text-align:..."` on the header cells, body rows padded
  to the header's column count, and literal `|` characters in cell text
  re-escaped to `\|` so they aren't mistaken for a column boundary.
- This is the same bug class the *push* direction (`md_to_cf.py`) already
  had fixed once before — the *pull* direction just never got the
  equivalent treatment, and there was no test file for `cf_to_md.py` at
  all before this fix to have caught it.

### Added

- `cli-python/tests/test_cf_to_md.py` (new file, 10 tests) — full
  `md_to_storage()` → `cf_to_md()` round-trip coverage: simple tables, wide
  multi-row tables (the exact shape reported broken), alignment markers,
  inline formatting inside cells, an escaped literal pipe in a cell, a
  ragged body row shorter than the header, a table followed by a
  paragraph, a heading before a table, two tables in one document, and a
  table-free document (regression guard against the new table regex
  misfiring on unrelated content).

### Verified

- `cli-python` pytest 858/858 (848 pre-existing + 10 new)
- ruff check/format and mypy all clean
- Manual round-trip test through the real `md_to_storage()`/`cf_to_md()`
  pair confirmed byte-for-byte table fidelity including alignment, inline
  code, bold, links, and an escaped literal pipe

---

## [2.8.21] — 2026-08-07 (Fix severe Node CLI bug: `sdd init` crashed on every interactive run)

**Bug fix — severe, affects the already-published npm package.** The Node
CLI's `inquirer` dependency was bumped by Dependabot from `9.2.0` to
`14.0.2` (merged via an earlier PR), which dropped the legacy `'list'`
prompt type in favor of `'select'`. Every `inquirer.prompt()` call in this
codebase still used `type: 'list'`, so `inquirer.prompt()` threw
`UnknownPromptTypeError` at runtime — breaking every interactive `sdd init`
(and the AI-tool prompt in `sdd upgrade`) for anyone not passing every
single CLI flag. There's no flag to skip the AI-tool prompt, so this hit
essentially all interactive users of `@sunil1983us/sddflow@2.8.20`.

Found by actually running a real interactive `sdd init` against a clean
install of the live, published npm package — none of the existing
automated tests caught it, since they only exercised migration-chain
logic, never a real inquirer prompt call.

### Fixed

- `cli/src/commands/init.js` (5 sites) and `cli/src/commands/upgrade.js`
  (1 site): `type: 'list'` → `type: 'select'`.
- A silent secondary bug in `init.js`'s scope prompt: the new
  `@inquirer/select` prompt's `default` option is compared against the
  choice's *value*, not an index into the choices array like the old
  `'list'` type did — `SCOPES.indexOf(...)` replaced with the actual
  default scope value.

### Added

- `cli/tests/inquirer-prompt-types.test.js` — a regression test that scans
  every `inquirer.prompt()` call in `src/commands/*.js`, extracts each
  `type: '...'` string used, and asserts it's a member of the installed
  `inquirer` package's own currently-registered prompt types (read live,
  not hardcoded) — a future `inquirer` upgrade that renames or drops a
  type this codebase depends on now fails this test immediately instead of
  only surfacing as a crash for a real user.

### Verified

- Real clean install of the fixed CLI, real PTY-based interactive
  `sdd init` run (piped stdin doesn't work against modern `@inquirer/*`
  prompts, which require raw-mode TTY input) confirmed the full flow
  completes and writes a correct `manifest.yml`
- `node --test` 28/28 (27 pre-existing + 1 new)
- `cli-python` pytest 848/848 (unaffected — Python CLI never used
  `inquirer`)

---

## [2.8.20] — 2026-08-07 (Drop Python 3.9 support — requires-python is now >=3.10)

**Breaking change.** Python 3.9 reached end-of-life in October 2025 (no
more security patches from CPython upstream). A deliberate maintainer
decision to stop supporting it.

### Changed

- `requires-python` bumped from `>=3.9` to `>=3.10` in `pyproject.toml`;
  the `3.9` classifier and CI matrix entry removed. `pip install sddflow`
  (or any upgrade) now refuses outright on Python 3.9 — verified by
  inspecting the built wheel's `METADATA` directly (`Requires-Python:
  >=3.10`, which is what pip checks before installing, on any Python
  version).
- `ruff`'s `target-version` bumped from `py39` to `py310`, which surfaced
  two real modernization findings ruff couldn't previously suggest:
  `typing.Callable` → `collections.abc.Callable` in `upgrade.py`, and a
  manual `zip(chain, chain[1:])` → `itertools.pairwise()` in
  `test_upgrade.py`. Both fixed.

The `from __future__ import annotations` guards added in `v2.8.11` (for
the Python 3.9 crash fix) were left in place rather than removed — they're
harmless no-ops on 3.10+ and removing them would be pure churn.

### Verified

- `cli-python` pytest: 848/848 on both a real Python 3.10.20 interpreter
  (the new floor) and a real Python 3.13.12 interpreter
- ruff check/format, mypy, and bandit all clean
- Wheel `METADATA` inspected directly to confirm the `Requires-Python`
  constraint took effect

---

## [2.8.19] — 2026-08-07 (Add Python 3.13 and 3.14 to the tested/declared version range)

CI's `python-cli-sanity` matrix only covered Python 3.9–3.12, but
pypistats.org's own download breakdown for `sddflow` showed real installs
already happening on Python 3.14 — with zero CI coverage for it.

### Added

- **Python 3.13 and 3.14** added to `python-cli-sanity`'s CI matrix and to
  `pyproject.toml`'s classifiers. No code changes were needed — the
  codebase already builds cleanly on 3.13 (verified with a real
  Python 3.13.12 interpreter: clean install, byte-compile, `--help` smoke
  test, full pytest suite). Python 3.14 has no local interpreter available
  to verify directly; CI's `actions/setup-python` is the first real
  verification for it.

### Verified

- `cli-python` pytest: 848/848, under both the default interpreter and a
  real Python 3.13.12 venv
- ruff check/format, mypy, and bandit all clean

---

## [2.8.18] — 2026-08-02 (Fix two real project-type misdetection bugs; add cross-implementation fixture tests)

The final item from the second external review round: building a shared
fixture-test suite across all four project-type detection implementations
(`cli-python/sdd/utils/detect.py`, `cli/src/utils/detect.js`,
`packs/sdd-universal/setup.sh`, `packs/sdd-universal/setup.ps1`) surfaced
two real, previously-unnoticed bugs, fixed alongside the new tests.

### Fixed

- **`setup.sh`/`setup.ps1`: `react-native-web` was misdetected as
  `mobile`.** A plain substring/word-boundary check on the `react-native`
  dependency name also matched `react-native-web` — a real, common npm
  package for running React Native components on the web, not a mobile
  project. Fixed with a space-padded whole-token match instead.
  `detect.py`/`detect.js` already did exact list/array membership and
  never had this bug.
- **`detect.py`/`detect.js`: modern Angular projects were never
  detected at all.** The Angular check used `startswith('angular')` /
  `startsWith('angular')`, which no real Angular 2+ project satisfies —
  they depend on scoped packages like `@angular/core`, which start with
  `@`, not `angular`. Only ancient AngularJS 1.x used the bare `angular`
  package name. Fixed by switching to a substring check, matching
  `setup.sh`/`setup.ps1`'s existing (correct) behavior.

### Added

- `cli-python/tests/test_detect.py`, `cli/tests/detect.test.js`
  (extended), and `packs/_shared/tests/test-detect-fixtures.sh` (new,
  wired into the `setup-smoke-tests` CI job) all assert the same ~20
  synthetic project fixtures against their respective implementation —
  there was no dedicated detection test coverage at all before this in
  any of the three.

Scoped down from the original review suggestion of making `detect.py`
canonical and having `setup.sh`/`setup.ps1` shell out to it: that would
make Python a hard runtime dependency of pack setup scripts (currently
only a soft dependency, for `package.json` parsing). Keeping four
independent implementations in sync via identical fixture tests achieves
the same goal — catching divergence — without that new dependency.

### Verified

- `cli-python` pytest: 848/848 (825 pre-existing + 23 new)
- ruff check/format, mypy, and bandit all clean
- `cli` `node --test`: 27/27
- `bash test-detect-fixtures.sh`: 23/23
- sync-drift check and cross-reference checker both clean
- `setup.ps1`'s fix was verified by direct code inspection, not an
  automated fixture loop (no `pwsh` available in this session's test
  environment) — PowerShell's `-match` has the same non-anchored
  substring semantics as bash's `grep -E`, so the identical fix applies

---

## [2.8.17] — 2026-08-02 (Widen js-yaml's range; friendly dashboard port-conflict error; lazy page assembly)

A batch of three small, independently-verified fixes from the second
external review round's final tier.

### Changed

- **Widened `js-yaml`'s declared range** in `cli/package.json` from
  `^4.1.0` (effectively `<5.0.0`) to `>=4.1.0 <6.0.0`. An earlier fix
  (`import * as yaml from 'js-yaml'` instead of the default export)
  already made the code work correctly under js-yaml 5.x — verified again
  here by installing `js-yaml@5.2.3` and re-running the full test suite.
  The old range was needlessly holding users back from picking up
  js-yaml's own security/bug fixes.
- **`sdd dashboard`'s page HTML is now assembled lazily.** `_load_page()`
  used to run at import time — and `dashboard.py` is imported
  unconditionally by every `sdd` invocation (`sdd --help`, `sdd init`,
  anything), so every command paid the cost of reading and concatenating
  4 static files even when nowhere near the dashboard. Now
  `@lru_cache`'d and only assembled on the first request that actually
  needs it.

### Fixed

- **`sdd dashboard` binding to a port already in use no longer crashes
  with a raw traceback.** `ThreadingHTTPServer(...)`'s bind is now
  wrapped in a `try/except OSError` that prints a clear message and,
  specifically for "address already in use," suggests `--port` as the
  way out, then exits cleanly.

### Verified

- `cli-python` pytest: 825/825 (824 pre-existing + 1 new port-conflict
  test)
- ruff check/format, mypy, and bandit all clean
- `cli` `node --test`, `npm test`, and the `--help` smoke test all pass
  under js-yaml 5.2.3

---

## [2.8.16] — 2026-08-02 (Fix a silent detect.js bug: Terraform projects were never detected as iac)

`cli/src/utils/detect.js`'s Terraform-file check called
`require('fs').readdirSync(...)` inside a try/catch — but this file is
loaded as an ES module (`"type": "module"` in `cli/package.json`), where
`require` is not defined at all. The resulting `ReferenceError` was
silently swallowed by the catch, so this branch always returned `false`: a
pure-Terraform project with no `Pulumi.yaml` or `cdk.json` was never
detected as `iac` by the Node CLI's project-type auto-detection.

### Fixed

- Imported `readdirSync` at the top of `detect.js` alongside the module's
  other `fs` calls, instead of a runtime `require()`. Verified both the
  bug and the fix directly: `require('fs')` throws `require is not
  defined` in a real ESM context, and a scratch directory containing only
  a `.tf` file now correctly detects as `iac` where it previously fell
  through to `null`.

### Added

- `cli/tests/detect.test.js` — the Node CLI had no `detect.js` test
  coverage at all before this.

### Verified

- `cli-python` pytest: 824/824 unaffected (Python's own `detect.py` does
  exact dependency-key matching, no shell-out, no `require()`, and was
  never affected by this bug)
- `cli` `node --test`: 6/6 (4 pre-existing + 2 new), `npm test`, and the
  `--help` smoke test all pass

---

## [2.8.15] — 2026-08-02 (CI now proves a clean pip install actually works; sdd init gets an --ai-tool flag)

A second external review round flagged that CI never verifies the packaging
path end to end: `sdd/packs/` is gitignored and only populated by
`publish.sh`'s manual bundling step right before a real PyPI upload. This
was proven to be a live, currently-undetected bug — a wheel built the way
CI already builds it (`pip install ./cli-python`, no `publish.sh`),
installed into a venv outside the repo, and run via `sdd init` from a real
project directory, failed with `SDD pack files not found.` `scaffold.py`'s
dev-fallback (walk up to a git checkout's `packs/` directory) silently
masked this in every environment that still had the full repo checked out
— which was every CI job and every dev machine, until now.

### Added

- **New `package-verify` CI job.** Bundles packs the same way `publish.sh`
  does, builds sdist+wheel via `python -m build`, asserts both archives
  contain `sdd/packs/sdd-universal/setup.sh`, installs the wheel into a
  clean venv, and runs a full `sdd init` from a scratch directory outside
  the repo — the exact reproduction that first surfaced the bug, now
  guarded permanently in CI.
- The same assertion now also runs inside `publish.sh` itself, between the
  build and upload steps, so a manual publish run outside CI can't ship a
  broken package either.
- **`sdd init --ai-tool`** (`claude-code | copilot | cursor | windsurf |
  other`). Running `sdd init` fully non-interactively for the CI job above
  surfaced a real, separate gap: every other interactive prompt (project
  type, scope, plan mode, reading mode) already had a CLI flag override,
  but "Which AI tool will you use?" did not — the one prompt with no way
  to skip, so any fully unattended `sdd init` would hang or abort on a
  non-interactive stdin.

### Verified

- `cli-python` pytest: 819/819 (817 pre-existing + 2 new `--ai-tool`
  tests)
- ruff check/format, mypy, and bandit all clean
- The full package-verify sequence (bundle → build → assert contents →
  clean venv install → `sdd init` from outside the repo) was run manually
  end to end before adding it to CI, confirming both the failure it
  catches and the fix

---

## [2.8.14] — 2026-08-02 (Dashboard: gate /api/review-links behind the token in read-only share mode)

A second external review round found a real gap in the dashboard
hardening shipped earlier: read-only `--share` mode (no `--write`) already
blocked the write endpoints without a token, but `GET /api/review-links`
was never gated at all. That endpoint makes a *live* call to Jira/
Confluence using the credentials stored on the machine running
`sdd dashboard`, for whatever `--feature` the caller names — "read-only"
only ever meant "no local file writes," it never meant "no outbound calls
made under this machine's credentials."

### Fixed

- **`/api/review-links` now requires the session token even in read-only
  `--share` mode.** Token generation happens for any non-local bind
  (previously only when `--write` was also passed); a new
  `_check_review_links_access()` helper reuses the existing Origin+token
  check and gates the endpoint, skipped only when the bind is local.
  Approve/comment endpoints are unchanged.
- Console output and the in-page info banner reworded to state plainly
  that "Check Jira/Confluence status" is not affected by read-only mode
  and always requires the token.

### Verified

- `cli-python` pytest: 817/817 (812 pre-existing + 5 new access-control
  tests for `/api/review-links`)
- ruff check/format, mypy, and bandit all clean

---

## [2.8.13] — 2026-08-02 (Add lean/standard/regulated as friendly scope aliases)

An external review flagged that `examples/todo-api` (a real `pilot`-scope
run) generates exactly 12 documents, yet "pilot" reads as a small,
informal effort until a team actually sees that count. A full rename of
the scope vocabulary would be a breaking change to `manifest.yml`'s schema
and every pack's scope-gating logic, so this ships a smaller, safe version
instead.

### Added

- **`lean`/`standard`/`regulated` accepted as friendlier aliases** for
  `pilot`/`mvp`/`full` wherever scope is set: `setup.sh`/`setup.ps1`'s
  `--scope`, and `sdd init`'s `-s`/`--scope`. Resolved to the canonical
  name before anything is written — `manifest.yml`'s own `scope:` field,
  and every gate/command that reads it, never sees the aliases.
- **Real input validation that didn't exist before.** An unrecognized
  `--scope` value (a typo, or anything outside the 6 accepted spellings)
  is now rejected with a clear error instead of being silently written
  into `manifest.yml` as-is.

### Verified

- `cli-python` pytest: 797/797 (793 pre-existing + 4 new)
- ruff check/format, mypy, and bandit all clean; coverage still 79%
- `setup.sh` smoke suite extended with 3 alias-resolution cases + 1
  invalid-scope rejection case (19/19 passing)
- Cross-reference checker and sync-drift check both clean across all 6
  packs
- Direct manual run against a synced pack confirming both the happy path
  (`--scope lean` → `scope: "pilot"`) and the rejection path end to end

---

## [2.8.12] — 2026-08-02 (Dashboard: confirm before approving; HTML/CSS/JS moved to real files)

### Added

- **Dashboard Approve now requires confirmation.** Previously fired
  straight to the server after two `window.prompt()` calls (name, optional
  note). Now shows a `window.confirm()` summarizing the document, feature,
  approver, and note before the request goes out, and does nothing at all
  if declined — guards against an accidental click by an already-
  authorized user. (The bigger risk, an *unauthorized* person approving,
  was already closed by the session-token work shipped a few versions
  back.)

### Changed

- **Dashboard HTML/CSS/JS extracted from a single Python string into real
  files** under `cli-python/sdd/commands/dashboard_static/` (`style.css`,
  `theme.js`, `app.js`, `page.html`) — editor syntax highlighting and
  linting now work on them, and diffs to the UI are readable instead of
  one 1050-line string blob. No behavior change: verified byte-identical
  output against the previous version, and confirmed the new files ship
  correctly in a real built-and-installed wheel (they needed an explicit
  entry in `pyproject.toml`'s packaging config, same as the existing pack
  files).

### Verified

- `cli-python` pytest: 793/793 (789 pre-existing + 4 new)
- ruff check/format, mypy, and bandit all clean; coverage still 79%
  (above the 77% CI floor)
- A real `python -m build --wheel` + clean-venv install, confirming the
  dashboard's static files are present and the page renders correctly

---

## [2.8.11] — 2026-08-02 (Fix a real Python 3.9 import crash; add ruff to CI)

Found while wiring `ruff` into CI (task #32 in the review-tracker): a real
installability bug, not a lint nitpick.

### Fixed

- **7 modules would crash on import under Python 3.9.** `init.py`,
  `upgrade.py`, `detect.py`, `manifest.py`, `scaffold.py`, `validate.py`, and
  one test file used `str | None` / `dict | None` union syntax directly in
  function signatures with no `from __future__ import annotations` at the
  top of the file. PEP 604's `X | Y` union syntax is only evaluable at
  runtime from Python 3.10 onward — on 3.9 (which `pyproject.toml`'s own
  `requires-python = ">=3.9"` and classifiers claim to support), importing
  any of these modules raised `TypeError: unsupported operand type(s) for |`
  at function-definition time, before any of the CLI's own logic ran. Fixed
  by adding the missing `from __future__ import annotations` to each file.
  This would have been caught immediately by the Python 3.9 CI matrix job
  added the round before this one (v2.8.10's sibling PR) — that job would
  have failed on `sdd --help` alone.

### Added

- **`ruff` added to CI** (`ruff check .` + `ruff format --check .`),
  configured in `cli-python/pyproject.toml`'s new `[tool.ruff]` section. A
  full pass fixed or `noqa`'d (with a reason comment) everything ruff's
  default ruleset flagged except two deliberately-ignored rules: `ISC004`
  (674 hits — this codebase's own style of writing long prose as adjacent
  string literals in lists, not a bug) and `BLE001` (67 hits —
  `except Exception:`, flagged for a dedicated manual triage pass, tracked
  separately rather than blanket-suppressed or blanket-narrowed blind).
- `ruff format` applied across the whole `cli-python` package in its own
  prior isolated commit (formatting only, verified with identical test
  results before and after) so this change's diff isn't dominated by
  reformatting noise.

### Verified

- `cli-python` pytest: 789/789 (unchanged pass count throughout this round)
- `ruff check .` and `ruff format --check .` both clean
- The specific Python 3.9 fix confirmed via `ruff check . --select FA102`
  going from 11 hits to 0

---

## [2.8.10] — 2026-08-02 (manifest.py atomic writes + corrupt-file handling; Jira/Confluence HTTP timeout + retry/backoff)

Next tier from the same ChatGPT-review verification pass — two more real gaps
found while checking the review's claims against the actual code, not
hypothetical ones.

### Fixed

- **`manifest.py` writes are now atomic.** `write_manifest()` previously
  wrote directly to `.specify/manifest.yml` with `write_text()` — a process
  killed mid-write (e.g. an interrupted `sdd upgrade`) could leave a
  truncated file, and every command reads this file, so a truncated manifest
  broke the whole project. Now writes to a temp file in the same directory
  and `os.replace()`s it into place, atomic on both POSIX and Windows.
- **`manifest.py` now fails loudly on a corrupt manifest.** `read_manifest()`
  previously let a corrupt YAML file raise a raw `yaml.YAMLError`. Now raises
  a new `ManifestError` with an actionable message (fix by hand, restore from
  git, or delete and re-run `sdd init`). A *missing* manifest still returns
  `None` as before — a corrupt one means the project clearly exists, so
  treating it the same as absent risked a caller re-scaffolding over it or
  silently dropping real config.
- **Jira/Confluence HTTP calls now have a timeout and retry with backoff.**
  Previously a flaky network blip or an Atlassian rate limit surfaced as a
  raw unhandled stack trace mid-workflow. Fixed once, centrally, via a custom
  `HTTPAdapter` mounted on the shared `requests.Session` in
  `atlassian_auth.py`'s `build_session()` — covers all ~25 call sites across
  `jira_client.py` and `confluence_client.py` from one place. 20-second
  default timeout; 3 retries with exponential backoff on connection errors
  and on 429/500/502/503/504 responses, honoring a 429's `Retry-After`
  header. Retries apply to POST/PUT too — this codebase's writes already
  lean on label-based find-before-create idempotency, and a connection blip
  silently aborting an approval push partway through is worse than the small
  remaining risk of an occasional duplicate retry.

### Verified

- `cli-python` pytest: 789/789 (773 pre-existing + 11 new `manifest.py`
  tests + 5 new `atlassian_auth.py` resilience tests)
- Atomicity proven via a monkeypatched `os.replace()` asserting the
  destination still holds old content and the temp source holds new content
  at replace-time; cleanup-on-failure proven the same way
- Retry logic proven against a real flaky local HTTP server (fails twice
  with 503, then succeeds), plus a control-case test showing a plain session
  without the adapter genuinely fails on the same server

---

## [2.8.9] — 2026-08-02 (Dashboard security hardening: session token, Origin check, read-only sharing, and a real concurrent-write bug fix)

The highest-priority item from a comprehensive verification pass against an
external (ChatGPT) architecture review. This closes real, live gaps — dashboard
write endpoints had zero authentication over the network, and there was an
unguarded concurrent-write race that could silently drop a comment.

### Fixed

- **Dashboard write endpoints now require authentication when shared over a
  network.** Previously, binding `sdd dashboard --host 0.0.0.0` only printed a
  console warning — anyone reachable on the network could approve documents
  and post comments. New `--share` (shortcut for `--host 0.0.0.0`) and
  `--write` flags: `sdd dashboard` (unchanged, local, writes on, no token),
  `sdd dashboard --share` (network, **read-only**), `sdd dashboard --share
  --write` (network, writes gated by a session token).
- **Session token doubles as CSRF protection.** Delivered via a custom
  `X-SDD-Token` header rather than a cookie — a cookie is sent automatically
  by the browser on any cross-origin request (the CSRF attack vector); a
  custom header only goes out on requests this page's own JS explicitly
  builds. Generated with `secrets.token_urlsafe(24)`, handed to the browser
  once via the auto-opened URL's `?token=` param, then stripped from the
  visible URL.
- **Origin/Host header check** as defense in depth on top of the token,
  checked first so a mismatched `Origin` is rejected even if a token leaked.
- **In-page network-sharing banner** and hidden/disabled write controls in
  read-only mode, via a new `GET /api/dashboard-info` endpoint — the previous
  console-only warning was invisible to anyone using the dashboard from a
  different machine.
- **Fixed a real concurrent-write data-loss bug**: `.dashboard-comments.json`
  had no lock around its read-modify-write cycle despite the dashboard
  running on `ThreadingHTTPServer` (one thread per request) — two
  near-simultaneous comment submissions could race and silently drop one.
  Verified with a 12-thread concurrency test that reliably fails without a
  lock and reliably passes with one.

### Verified

- `cli-python` pytest: 773/773 (765 pre-existing + 8 new)
- All 49 pre-existing dashboard tests pass unchanged — the default
  `sdd dashboard` invocation (no flags) is completely unaffected
- Three live end-to-end smoke tests against a real running server, all three
  modes, confirming the printed token works and wrong/missing tokens are
  rejected
- Concurrency test independently verified to catch the regression: fails
  5/5 with the lock removed, passes reliably with it restored

---

## [2.8.8] — 2026-08-01 (Root README "60-Second Overview" — first-time-visitor orientation)

An external (ChatGPT) review flagged that a newcomer to the maintainer
repo's root README can't quickly answer 7 orientation questions: which
pack, which CLI, the smallest useful workflow, how many documents get
generated, whether Jira/Confluence is required, the first 3 commands to
run, and whether this is for solo devs or teams. Checked the claim
against the actual repo — most were partially answered already, just
buried rather than absent.

### Added

- **"60-Second Overview"** — a new section at the top of the root
  `README.md`, right after the intro paragraph: one audience line
  ("Built for teams that need audit trails and structured sign-offs...")
  plus a 4-row table covering CLI choice + Jira/Confluence optionality,
  the first 3 commands to run, document count, and a pointer to
  `packs/CATALOG.md`'s existing pack-decision tree.
- **Document count, verified not guessed** — 12 documents at `pilot`
  scope, counted directly from the real `examples/todo-api` file
  listing. An initial draft said "~13"; corrected against the actual
  file count before shipping.
- **Pack-catalog pointer on every pack's own README** — a one-line "not
  sure this is the right pack? see the catalog" note (absolute GitHub
  URL, matching the `sdd-micro`/`examples` redirect pattern from earlier
  rounds) at the top of the "Start Here" section in all 5 full packs, so
  a visitor who lands directly on one pack's page — not the root — still
  gets routed to the decision tree.

### Verified

- `cli-python` pytest: 765/765 (unchanged — no code touched)
- Cross-reference linter: clean across all 6 packs
- Both setup smoke-test suites: 15 + 12 passed

---

## [2.8.7] — 2026-08-01 (Removed IMPROVEMENT-BACKLOG.md from every pack — it was leaking maintainer-only content into real user projects)

A user shared a photo of their own project directory (created via `sdd
init`) showing `IMPROVEMENT-BACKLOG.md` sitting right there alongside
`README.md`/`QUICKSTART.md`/etc. — confirming a real bug, not a
hypothetical one.

### Fixed

- **`IMPROVEMENT-BACKLOG.md` no longer ships with any pack.** It existed
  in `sdd-backend-service`, `sdd-frontend-spa`, `sdd-mobile`, and
  `sdd-universal` (`sdd-fullstack` never had it) as the *maintainer's
  own* internal notes about deferred pack-template work — e.g. "Add an
  `observability-template.md` if this pack is used for services with
  formal SLOs." Nothing about it concerned an end user's own project.
  Root cause: `scaffold_pack()` (`cli-python/sdd/utils/scaffold.py`)
  copies a pack's entire folder into a user's project with zero
  exclusion filter — unlike `package.sh`'s zip builder, which already
  excludes `.git/` and `CLAUDE.local.md`.
- Deleted the file from all 4 packs, removed its row from each pack's
  `README.md` "Start Here" table, and consolidated the actual content —
  deduped, `sdd-backend-service` and `sdd-universal` were byte-identical
  — into this maintainer repo's own `OWNER-GUIDE.md` as a new section,
  "8. Deferred Improvement Items."

### Verified

- `cli-python` pytest: 765/765 (unchanged — no code touched)
- Cross-reference linter: clean across all 6 packs
- Both setup smoke-test suites: 15 + 12 passed
- Live smoke test: ran `sdd init` end-to-end, confirmed the scaffolded
  output no longer includes `IMPROVEMENT-BACKLOG.md`

---

## [2.8.6] — 2026-08-01 (Dashboard: per-stage duration, review-round count, and an overall feature Timeline)

`sdd dashboard` showed each document's status but not how long each stage
took, how many review rounds it went through, or an overall feature
start/end. All of that turned out to already be latent in data the
framework was writing anyway — it just wasn't being read back out.

### Added

- **Per-document Created date, Approved date, duration, and revision
  rounds** — computed from the document's own `## Version History` table
  (already written by the shared review-decision-step block on every
  `/specify-*`, `/plan-*`, and `/task` command). The first row is the
  creation date; once `Status:` says Approved, the last row is always the
  approval event. `revision_rounds` counts actual version bumps — content
  edits made in response to review feedback — not every review check; a
  pure re-read-and-approve with no edit doesn't bump the version and
  isn't counted.
- **Feature-level Timeline card** — overall `start_date` (earliest
  document's created date, normally `brd.md`), `end_date` (`release.md`'s
  approved date, falling back to its own Approvals-table Date column
  since it has no Version History table), and duration in days once both
  resolve.
- **`{date}` standardized to `{date: YYYY-MM-DD}`** across every document
  template (shared and per-pack) so dates are machine-parseable. Old
  documents, or any hand-edited date that isn't ISO 8601, simply don't
  show duration/rounds — silent degradation, no warning badge, by
  explicit choice this round rather than assumption. `sdd-micro` was
  deliberately left untouched (outside the shared-block/version-lockstep
  system).

### Verified

- `cli-python` pytest: 765/765 (753 pre-existing + 12 new)
- Cross-reference linter: clean across all 6 packs
- Both setup smoke-test suites: 15 + 12 passed
- `assert-output.sh`'s 33 structural assertions: still pass
- Embedded dashboard JS: re-verified with `node --check` after extraction
- Live end-to-end smoke test: the actual `sdd dashboard` HTTP server
  against a synthetic project, confirming `/api/status` returns correct
  `timing`/`timeline` JSON and the rendered page includes the new
  Timeline card

---

## [2.8.5] — 2026-08-01 (Surface the worked examples to real users; implement TASK-001/002/003 of examples/todo-api for real)

Two fixes shipped together, closing the remaining gap from the 2.8.3/2.8.4
onboarding-friction rounds: the framework's worked examples were
well-built but invisible to a real end user, and — even if found — proved
only that the framework could produce specs, not working code.

### Added

- **"See a finished example" callout** — added to all 5 full packs'
  `README.md` and `QUICKSTART.md`, linking to `examples/` on GitHub.
  Previously `examples/todo-api` and `examples/habit-tracker-web` were
  referenced from nowhere a real user running `sdd init` would ever see
  them — only from this maintainer repo's own root `README.md` and the
  CI regression harness (`assert-output.sh`).
- **`examples/todo-api` now has real, passing implementation code** for
  TASK-001 (Prisma schema + migration), TASK-002 (user-scope Prisma
  extension, FR-007), and TASK-003 (`POST /tasks` endpoint, UC-001) — 3
  of the 10 tasks in `tasks.md`. Actual TypeScript/Express/Prisma/
  PostgreSQL 16 code, run against a live local Postgres 16 instance, 13
  tests passing (5 unit + 8 integration), `tsc --noEmit` clean.
  `tasks.md`'s acceptance-criteria checkboxes for those 3 tasks are now
  `[x]`, each pointing at the implementing files. TASK-004 through
  TASK-010 remain spec-only, unchanged.
- **`examples/todo-api/IMPLEMENTATION.md`** — documents exactly what's
  implemented, two deliberate simplifications (HS256 shared-secret JWT
  instead of the RS256-from-env scheme `context.md` specifies; no
  partial indexes in the Prisma schema DSL, since Prisma's declarative
  schema can't express `hld.md`'s `WHERE` predicates without an unstable
  preview feature), and how to run it locally.

### Not done (called out explicitly, not silently skipped)

- TASK-007 (full auth middleware wiring — RS256, expired-JWT handling)
  is **not** marked done. Making TASK-003 testable end-to-end required
  pulling forward a minimal HS256 stand-in for `auth.middleware.ts` and
  `user-scope.middleware.ts`, but that stand-in doesn't satisfy
  TASK-007's own acceptance criteria.
- No simulated `/pre-review` or `/address-review` round — there's no
  real reviewer for a maintainer-repo example, and simulating one would
  read as staged rather than as proof.
- TASK-004 through TASK-010 (GET/PATCH/DELETE, pagination, purge cron)
  remain spec-only.

### Verified

- `cli-python` pytest: 753/753 (unchanged — no `cli-python` code touched)
- Cross-reference linter: clean across all 6 packs
- Both setup smoke-test suites: 15 + 12 passed
- `assert-output.sh`'s 33 structural assertions: still pass against the
  edited `tasks.md`
- `examples/todo-api`'s own test suite: 13/13 passing (`jest
  --testPathPattern user-scope` 5/5, `jest --testPathPattern
  tasks.routes` 8/8), `tsc --noEmit` clean, `prisma migrate dev` applied
  clean against a freshly created PostgreSQL 16 database

---

## [2.8.4] — 2026-08-01 (Doc-navigation fixes from a third end-user feedback review)

A user shared a third, more detailed end-user feedback review (same theme
as the 2.8.3 round, different reviewer): 11 top-level docs in each pack
with no stated reading order, the self-approval-risk disclosure buried
inside `CLAUDE.md` (agent-facing only, never surfaced to the human who
actually needs to know it), and no signal at all about the token/cost
footprint of running the full document-heavy pipeline.

### Added

- **"Start Here" doc map** — a table at the top of every full pack's
  `README.md` listing the 3 files to read in order (`QUICKSTART.md` →
  `README.md` → `HOW-TO-USE.md`), with the remaining reference files
  listed separately as "skip on first pass, come back when you need it."
  `sdd-fullstack`'s table omits the `IMPROVEMENT-BACKLOG.md` row since
  that pack has only 10 root `.md` files, not 11 like the other 4.
- **Self-approval-risk callout** — added to every pack's `QUICKSTART.md`,
  right after the "review gates work out of the box" paragraph: default
  chat-mode approval only checks that someone typed "approved" in the
  same conversation that wrote the doc, with no independent identity
  check. Points to `CLAUDE.md`'s existing "Self-approval risk" section
  for the full explanation instead of duplicating it.
- **Token/cost footprint callout** — added to every pack's
  `QUICKSTART.md` intro, describing the pipeline's actual command
  cadence (one agent command per phase, each reading/writing at least
  one document) rather than a fabricated dollar figure — there is no
  real token-usage data anywhere in this repo to cite
  (`token-pricing.yml.example` ships with all rates `null`). Points to
  enabling `token-pricing.yml` for a real per-command log instead.

### Verified

- `cli-python` pytest: 753/753 (unchanged — doc-only round)
- Cross-reference linter: clean across all 6 packs
- Both setup smoke-test suites: 15 + 12 passed

---

## [2.8.3] — 2026-08-01 (Onboarding-friction fixes from an end-user feedback review)

A user shared an end-user feedback review (from another chat session)
that pointed out real onboarding friction: heavy reading load, an
8-persona team-routing system with no signal it's optional, and — the
sharpest finding — no redirect toward `sdd-micro` for solo/prototype
users until they'd already committed real time to a full pack's docs.

### Added

- **`sdd-micro` redirect** — a callout in all 5 full packs' `README.md`
  and `QUICKSTART.md` intro sections: *"Building something small, solo,
  or just prototyping? ... use `sdd-micro` instead."* This previously
  only existed in the maintainer repo's own root `README.md` — a user
  who copied a single pack into their own project (the documented
  deployment model) never saw it.
- **Optional-persona note** — one line before the Virtual Team
  (Maya/Rex/Ava/etc.) table in all 5 packs' `README.md`: *"Optional —
  you can use plain `/specify`, `/validate`, etc. throughout without
  ever addressing the team by name."*
- **`"private": true`** in `cli/package.json` — `CLAUDE.md` already
  documents this package as "unpublished, from source," but nothing
  enforced that; an accidental `npm publish` would have succeeded.

### Fixed

- **QUICKSTART.md's self-contradicting headline**, all 5 packs: *"5
  minutes to your first spec"* was directly contradicted by a "15-30
  min" context-writing step 30 lines later in the same file. Reframed:
  *"5 minutes to get set up. Your first full feature spec takes longer
  — budget half a day for a first pass."*

### Note

- Caught and fixed a self-introduced bug while implementing the
  `sdd-micro` redirect: the first draft used a relative link
  (`../sdd-micro/`), which only resolves inside this maintainer repo
  where packs are siblings under `packs/` — broken once a user has
  copied a single pack out on its own. Fixed to an absolute GitHub URL.
- Not changed: the migration-table duplication between the two CLIs —
  already test-covered on both sides from a prior round, and the review
  itself downgraded this to "not urgent."

### Verified

- Documentation/config-only — no functional code touched, no
  `manifest.yml` schema change, no CLI behavior differs.
- `cli-python` pytest 753/753 (unchanged), cross-reference linter clean
  across all 6 packs, `package.json` parses.

---

## [2.8.2] — 2026-08-01 (`sdd upgrade` converges in one run instead of one invocation per pending migration)

An external code review (point #3) flagged that `upgrade_command()`/
`upgradeCommand()` in both CLIs only ever found and applied a single
migration hop per run — a plain match on `MIGRATIONS` entries whose
`from` equals the current version, which structurally never matched more
than one entry even though it was looped over. A project many versions
behind needed one `sdd upgrade` invocation per pending migration to catch
up. The user confirmed this was actively painful — they're shipping new
versions every 30–40 minutes right now.

### Added

- New `_pending_migrations()`/`pendingMigrations()` walks the full linear
  `MIGRATIONS` chain from the current version to `SDD_VERSION`, returning
  every pending hop in order instead of just the next one.
- With more than one migration pending, a real interactive terminal is
  now asked whether to jump straight to the latest version (apply
  everything now) or step through one at a time. A non-interactive
  invocation (CI, piped stdin, scripts) skips the prompt and defaults to
  jumping straight to latest — automation never needs N reruns.
- New flags in both CLIs: `--to-latest` (force jump, skip prompt),
  `--step` (force one-hop-then-stop — the original behavior, skip
  prompt), `-y`/`--yes` (skip prompt, defaults to jump-to-latest —
  extends the Python side's existing `--yes` flag, previously only for
  the `--sync-prompts` confirmation).

### Changed

- TTY detection is broken out into a small `_stdin_is_interactive()`/
  `_stdinIsInteractive()` helper rather than a bare
  `sys.stdin.isatty()`/`process.stdin.isTTY` check — Click's `CliRunner`
  reassigns `sys.stdin` during `invoke()`, which silently defeats a naive
  `patch()` set up before the call; the helper makes this reliably
  mockable in tests.
- `cli-python/README.md` and `cli/README.md`'s `sdd upgrade` sections
  document the new prompt and flags.

### Verified

- `cli-python` pytest 753/753 (742 pre-existing + 11 new).
- `node --test` 4/4 in `cli/` (2 pre-existing + 2 new — full
  `CliRunner`-equivalent interactive-prompt coverage wasn't ported to the
  Node side, a deliberate scope limit matching this CLI's existing
  lighter test investment, not an oversight).
- Manually smoke-tested the real CLI: `--to-latest` jumps `v2.0.0 →
  v2.8.1` in one call, `--step` applies exactly one hop and prints the
  rerun hint, and plain non-interactive stdin also jumps straight to
  latest by default.
- No `manifest.yml` schema change.

---

## [2.8.1] — 2026-08-01 (Node CLI gets its first automated tests — migration-chain-integrity, ported from cli-python)

An external code review pointed out that the Node CLI (`cli/`) had zero
automated tests — no `test` script, no test files, and the
`node-cli-sanity` CI job only ran `node bin/sdd.js --help`. Both CLIs
hand-mirror the same ~100-entry `MIGRATIONS` table on every release, and
until now only the Python side had a test that would catch a broken
`from`/`to` link — a typo on the Node side would go undetected by CI
until a real user's `sdd upgrade` hit "No migration path found."

### Added

- `MIGRATIONS` is now exported from `cli/src/commands/upgrade.js` (was
  module-private).
- New `cli/tests/upgrade.test.js`, ported from `cli-python`'s
  chain-integrity tests: the migration table forms a connected chain
  ending at `SDD_VERSION`, and every entry's `migrate()` stamps its own
  `to` version. Uses Node's built-in `node:test`/`node:assert` — zero new
  dependencies.
- New `"test": "node --test"` script in `cli/package.json`; the
  `node-cli-sanity` CI job now runs `npm test` before the existing
  `--help` smoke test.

### Verified

- `node --test` — 2/2 passing.
- No functional CLI behavior change, no `manifest.yml` schema change —
  purely closing a test-coverage gap.
- `cli-python` pytest 742/742 (unchanged), `ast.parse` on `upgrade.py`,
  `node --check` on `upgrade.js`.

---

## [2.8.0] — 2026-08-01 (Versioning scheme change: capped major.minor.patch, one-time reset off the runaway 2.7.100)

The old scheme just incremented the patch number forever — it had reached
`2.7.100` (a hundred patch releases within one minor version), which a
user pointed out was an awkward, hard-to-reason-about number.

### Changed

- `sdd_version` now uses a **capped** major.minor.patch counter: patch
  (Z) ranges 0–24, minor (Y) ranges 0–9. Bumping patch past 24 instead
  increments minor and resets patch to 0; bumping minor past 9 instead
  increments major and resets minor to 0. Equivalent to treating the
  version as one running integer `N = X*250 + Y*25 + Z`, adding 1, and
  reconstituting `X/Y/Z` via `divmod(N, 250)` then `divmod(rem, 25)`.
- This specific bump (`2.7.100 → 2.8.0`) is a **manual, one-time reset**,
  not the general divmod rule applied retroactively — the user explicitly
  chose not to divmod the old scheme's runaway patch count (which would
  have landed on `3.1.0`). Every bump from `2.8.0` onward uses the plain
  capped rule with no further special-casing.
- New `.claude/skills/version-bump/SKILL.md` in this repo encodes the
  full bump procedure (compute next version, update all 9 lockstep
  files, append matching migration entries to both `upgrade.py` and
  `upgrade.js`, add the CHANGELOG entry, run verification) so future
  bumps apply the rule consistently instead of being computed ad hoc.

### Verified

- Purely a versioning/process change — no functional CLI behavior
  differs, no `manifest.yml` schema change.
- `cli-python` pytest 742/742 (unchanged — no code touched), `ast.parse`
  on `upgrade.py`, `node --check` on `upgrade.js`.

---

## [2.7.100] — 2026-08-01 (`sdd init` now asks plan_mode and reading_mode, matching setup.sh)

A user ran `sdd init` (the pip-installed CLI) and asked when
`reading_mode` gets asked — it never was. `init.py` only ever asked
project type, project name, feature name, scope, and AI tool;
`plan_mode`/`reading_mode` silently stayed at the pack's shipped default
(`unified`/`auto`). This README already documents `sdd init` as
"Replaces `bash setup.sh` / `.\setup.ps1`" — but `setup.sh` has asked both
interactively since v2.7.92 (reading_mode) and earlier (plan_mode), so
this was a real parity gap between the two scaffolding entry points.

### Added

- `sdd init` now asks "Plan document style:" (unified/separate) and
  "Document reading mode:" (auto/summary/full) right after scope, using
  the same option wording as `setup.sh`'s prompts.
- New `--plan-mode`/`--reading-mode` flags skip the prompts
  non-interactively, matching `--scope`/`--type`'s existing pattern.
- `sdd-micro` is exempt — its `manifest.yml` template has neither field.

### Verified

- New tests: interactive selection written to manifest, CLI flags skip
  both prompts, `sdd-micro` never prompts for either.
- Full suite: `cli-python` pytest 742/742 (739 pre-existing + 3 new).
- No `manifest.yml` schema change — both fields already existed, this
  just makes them reachable from `sdd init` the same way they're
  reachable from `setup.sh`.

---

## [2.7.99] — 2026-08-01 (PyPI/npm package Summary and keywords rewritten for discoverability)

A user looked at the sddflow PyPI page and pointed out the Summary
("SDD Framework CLI — initialize and upgrade Spec-Driven Development
packs") undersold what the CLI actually does now — it read like a plain
scaffolding tool, with no mention of Jira/Confluence sync, multi-host PR
automation, or the live dashboard.

### Changed

- `cli-python/pyproject.toml`'s `description` (PyPI's "Summary") is now:
  *"Spec-Driven Development CLI for AI coding agents — SDLC workflows with
  Jira/Confluence sync, multi-host PR automation, and live progress
  dashboards."* `keywords` gained `jira`, `confluence`, `atlassian`,
  `pull-request`, `code-review`, `requirements`, `ai-agent`,
  `claude-code`.
- `cli/package.json`'s `description` was written separately, not copied
  verbatim — the Node CLI doesn't have Jira/Confluence integration, PR
  automation, or a dashboard (those are `cli-python`-only), so it now
  reads: *"CLI for the Spec-Driven Development (SDD) Framework —
  initialize and upgrade AI-agent SDLC packs (Claude Code, GitHub
  Copilot, and any AI coding tool)."*

### Note

- "Author: None" on the PyPI page (also raised) is expected, not a bug —
  PEP 621's `authors = [{name, email}]` maps to the combined
  `Author-email` Core Metadata field per spec, leaving the legacy
  `Author` field blank; there's no separate name-only field to populate
  instead.
- Packaging metadata only — no manifest.yml effect, no CLI behavior
  change. Publishing to PyPI so the new Summary is actually visible still
  requires the maintainer's own `python -m build && twine upload` (or
  equivalent CI step); this repo has no publish automation.

---

## [2.7.98] — 2026-08-01 (Jira Feature/Epic gains Business Objectives, Success Criteria, and a Confluence link)

Follow-up to 2.7.97's structured description template (Problem Statement /
Business Hypothesis / Description / Out of Scope / NFR) — asked what else
was worth adding to a business-level Epic. Added the three recommended
sections.

### Added

- **Success Criteria** — `brd.md` §8's checklist items, closing the loop
  the Business Hypothesis opens ("we'll know this is true when X").
- **Business Objectives** — brought back as its own compact section
  (`BO-NNN: {objective} — {success metric}` per row from `brd.md` §2),
  distinct from the free-text Description/Hypothesis prose.
- **Full Document (Confluence link)** — if `brd.md` has already been
  pushed to Confluence, the Epic description links straight to the page
  instead of only carrying an excerpt. Read from the local
  `.specify/.confluence-drafts.json` cache — no network call, silently
  omitted if Confluence isn't configured or `brd.md` hasn't been pushed
  yet.

### Verified

- New tests for both parsers, the link resolution, and end-to-end through
  `feature_extra_fields()`/`sdd review submit`'s Epic self-bootstrap.
- Full suite: `cli-python` pytest 739/739 (721 pre-existing + 18 new),
  cross-reference linter clean, setup smoke tests clean.
- No `manifest.yml` schema change — every existing Epic picks up the new
  sections and link on its next push (idempotent upsert).

---

## [2.7.97] — 2026-08-01 (Jira Feature/Epic description now uses a structured template)

A user asked for a specific description template on the Jira Feature/Epic
issue: Problem Statement, Business Hypothesis, Description, Out of Scope,
NFR. The previous description was a single "Business Objectives:" bullet
list pulled from `brd.md`'s `BO-NNN` rows — useful, but not the shape
being asked for.

### Added

- `brd-template.md` gains a new "### Business Hypothesis" field under §4
  Business Context, right after Problem Statement — a testable belief
  statement ("We believe that X for Y will result in Z; we'll know this
  is true when..."), distinct from the Problem Statement it sits next to.
  `specify-brd.prompt.md` instructs the agent to fill it.
- New `jira.py` parsers pull Problem Statement / Business Hypothesis /
  Description from `brd.md` §4/§1, Out of Scope from `brd.md` §4's bullet
  list, and NFR from `srd.md` §3's NFR-NNN table.
- New `adf_sections()` builder renders each as its own heading + body,
  omitting a section entirely (no empty heading) when its source doc
  doesn't exist yet or is still unfilled template text — e.g. NFR is
  silently absent until `/specify-srd` runs. Falls back to a single
  placeholder paragraph only when every section is empty.

### Changed

- `sdd review submit`'s Epic self-bootstrap picks up the new template
  automatically (it reuses the same `feature_extra_fields()`), no
  separate change needed.
- Every existing Epic gets the new description shape on its next push —
  create-or-update is idempotent, no manual migration step.

### Verified

- Full suite: `cli-python` pytest 721/721 (713 pre-existing + 8 new),
  cross-reference linter clean, `assert-output.sh` clean against
  `examples/todo-api`, setup smoke tests clean.

---

## [2.7.96] — 2026-08-01 (`sdd config test` now verifies Jira and Confluence independently)

While auditing docs for the recent `config init` changes, found that
`sdd config test` still resolved exactly **one** `Profile` and pinged both
Jira and Confluence against its `base_url` — even though 2.7.93 let them
use separate profiles. Testing the split with `sdd config test --profile
confluence-dc` (exactly what the wizard's own closing message told you to
run) would try to hit Jira at Confluence's URL and vice versa — a silent
false failure for whichever service didn't match the flag.

### Fixed

- Without `--profile`, Jira and Confluence are now each resolved through
  `integrations.yml`'s `jira.profile`/`confluence.profile` independently —
  each service is pinged against its own `base_url` and credential. When
  they resolve to the same profile (the common case), output is unchanged
  from before. When they differ, the command prints which profile backs
  which service before testing.
- An explicit `--profile` still tests that one profile against both
  services, unchanged — for sanity-checking a profile before it's wired
  into `integrations.yml`.
- `sdd config init`'s closing message no longer suggests
  `sdd config test --profile X` per service when `integrations.yml` was
  scaffolded (that flag can't isolate a single service — see above); it
  now says `Run sdd config test to verify both`. If scaffolding was
  declined, the old two-command guidance is kept, now with an explicit
  caveat about what it actually tests.

### Verified

- New tests: single-profile pings once, split-profile pings each service
  against its own `base_url`, explicit `--profile` overrides the split, an
  unknown `confluence.profile` reports which service's config failed, and
  both `config init` closing-message variants.
- Full suite: `cli-python` pytest 713/713 (707 pre-existing + 6 new).

---

## [2.7.95] — 2026-08-01 (Confluence parent-page prompt now accepts a pasted URL, not just the raw ID)

A user pointed out that when `sdd config init` asks for the Confluence
parent page, most people have the page open in a browser tab, not its raw
numeric ID memorized — the wizard only accepted the bare ID, forcing a
manual trip through Confluence's Page Information panel to extract it
first.

### Added

- `parse_confluence_page_id()` — recognizes a bare numeric ID unchanged, a
  Cloud page URL (`.../pages/123456/Title`), or a Server/Data Center URL
  (`...?pageId=123456`), and extracts just the numeric ID from either. A
  Confluence "tiny link" (`/x/AbCdEf`) isn't a page ID and can't be
  resolved without an API call — it's returned unchanged with a wizard
  warning telling the user to paste the full URL instead.
- Wired into both the `sdd config init` prompt and `load_integrations()`
  itself, so a hand-edited `integrations.yml` with a pasted URL for
  `parent_page_id` also resolves correctly at push time.
- `integrations.yml.example`'s `parent_page_id` comment updated to
  document that either form works.

### Verified

- New tests: `parse_confluence_page_id()` parametrized over bare ID /
  Cloud URL / Server-DC URL / blank / tiny-link fallback,
  `load_integrations()` resolving a pasted URL from YAML, and an
  end-to-end `config init` wizard test.
- Full suite: `cli-python` pytest 707/707 (697 pre-existing + 10 new).

---

## [2.7.94] — 2026-07-31 ('sdd config init' now offers separate Jira/Confluence profiles upfront)

2.7.93 let Jira and Confluence use separate `~/.sdd/config.yml` profiles via
`jira.profile`/`confluence.profile` in `integrations.yml`, but a follow-up
question exposed a gap: did `sdd config init` itself actually offer this?
It didn't — the wizard was still single-profile only, so using the split
meant running `init` twice and hand-editing the commented-out override
lines in `integrations.yml` afterward. The user clarified what "profile"
must mean here: not just a server URL, but the entire authentication set —
`base_url` + `auth_mode` + credential — so two profiles are never assumed
to share anything, even a coincidentally identical URL.

### Added

- `config_init()` now opens with "Do Jira and Confluence share the same
  site and credentials?" — **Yes** keeps the original single-profile flow
  unchanged; **No** runs the full credential round (profile name,
  `base_url`, auth mode, credential storage) twice, once per service.
- `_collect_and_save_profile()` — the credential-collection logic extracted
  into a reusable helper so both the "same" and "different" paths share
  identical prompts and validation, avoiding drift between them.
- "Different" mode wires the result automatically: the top-level
  `profile:` becomes Jira's, and `confluence.profile:` is filled with the
  Confluence profile name in the generated `integrations.yml` — no manual
  editing step required.

### Verified

- New tests: `test_different_profiles_creates_both_in_config_yml` (both
  profiles saved with distinct `base_url`/`auth_mode`/`credential_store`)
  and `test_different_profiles_wires_confluence_override_into_integrations_yml`
  (end-to-end: the generated `integrations.yml` actually contains the
  override, not just two orphaned `config.yml` profiles).
- 5 pre-existing `config init` tests updated for the new opening question.
- Full suite: `cli-python` pytest 697/697 (695 pre-existing + 2 new).
- No `manifest.yml` or `integrations.yml` schema change — 2.7.93 already
  added the fields; this just makes them reachable from the wizard.

---

## [2.7.93] — 2026-07-31 (Jira and Confluence can now use separate ~/.sdd/config.yml profiles)

A user asked directly: their organization runs Jira and Confluence as
separate Data Center servers, each with its own auth token. Was that
accounted for? It wasn't — every command that talks to both services
(reviewed all call sites across `config.py`, `confluence.py`, `cr.py`,
`dashboard.py`, `jira.py`, `pr.py`, `review.py`) resolved exactly **one**
`Profile` (one `base_url`, one credential) from `integrations.yml`'s single
top-level `profile:` field, then handed the same authenticated session to
both `JiraClient` and `ConfluenceClient`. Correct only when both live on
the same Atlassian Cloud site — silently wrong the moment they're separate
servers.

### Added

- `jira.profile` / `confluence.profile` — optional per-service overrides in
  `integrations.yml`, each falling back to the existing top-level
  `profile:` when unset. Existing projects with one `profile:` line need
  no changes at all.
- `atlassian_auth.load_jira_session()` / `load_confluence_session()` —
  resolve each service's `Profile` + authenticated `Session`
  independently, replacing the shared `load_profile()`+`build_session()`
  pair at every call site. A command's own `--profile` flag still wins
  over both, matching prior precedence.
- `integrations.yml.example` documents both new fields with guidance on
  when to use them (Data Center, not the common Cloud case).

### Verified

- `cr_submit` and the dashboard's review-links fetch resolve each session
  *conditionally* — only for a service that's actually configured — since
  resolving both unconditionally would require credentials for a service
  the user never configured for that command (caught this in an early
  draft via a test that only configured `jira:`, no `confluence:`).
- New tests: 4 in `test_config_and_integrations.py` (profile fallback,
  independent override, one-service override, missing-section tolerance)
  + 3 in `test_atlassian_auth.py` (different base URLs resolve
  independently, same profile when unset, explicit override still wins).
- Full suite: `cli-python` pytest 695/695 (688 pre-existing + 7 new,
  including updating ~13 existing tests that mocked the old
  `load_profile`/`build_session` pair directly).

---

## [2.7.92] — 2026-07-27 (setup.sh/setup.ps1 now ask for reading_mode instead of silently defaulting to "auto")

A user asked where `reading_mode` (the AI-2 token-economy switch —
auto/summary/full) actually gets set, then asked directly whether setup
could ask for it and offer a choice. Grepping `setup.sh`/`setup.ps1`
confirmed it wasn't part of the interactive flow at all — only `name`,
`scope`, `feature`, and `plan_mode` were ever asked; every new project
silently got `"auto"` baked into `manifest.yml` from the static template,
with no chance to pick `summary` or `full` at init time.

### Added

- **`--reading-mode` flag / interactive prompt** (`-ReadingMode` in
  PowerShell) in `setup.sh` and `setup.ps1`, mirroring the existing
  `plan_mode` prompt pattern exactly — same three-option explanation
  already documented in `summary-rules.md`, same env-var-safe
  substitution in `sdd-universal/setup.sh` (project/feature names can
  contain special characters), same regex substitution in the shared
  `_shared/full/setup.sh` used by the other 4 non-micro packs.
- `sdd-micro` intentionally excluded — confirmed via grep it has no
  `reading_mode` field in its manifest at all (no BRD/UC/SRD documents to
  summarize, so the token-economy switch doesn't apply there).

### Verified

- Real pty test (piped stdin forces non-interactive mode by the script's
  own design and would give a false pass): prompt renders, accepts
  `summary`, writes `reading_mode: "summary"` into `manifest.yml`.
- `--reading-mode full`/`summary` flags verified directly against
  `sdd-backend-service`, `sdd-frontend-spa`, and `sdd-universal`'s
  separate `setup.sh`.
- No manifest.yml schema change for existing projects — the field already
  existed; only new-project setup behavior changed.
- `cli-python` pytest 688/688 (unaffected), `test-setup.sh` 15/15,
  `test-setup-micro.sh` 12/12, `assert-output.sh` clean on both worked
  examples.

---

## [2.7.91] — 2026-07-23 (Add cross-reference linter — catches dead "Action N" / "§N" prompt pointers in CI)

Asked for an honest, code-verified assessment of the project so far. The
top recommendation: both real bugs found this session (v2.7.88, v2.7.89)
share a root cause — something read as correct in isolated review but was
never exercised end-to-end, and both were only found because a user asked
a pointed question, not because any test caught them. This closes that
gap for the first bug class.

### Added

- **`packs/_shared/tests/check-cross-references.py`** — scans every
  pack's `.github/prompts/*.md` and `CLAUDE.md` for two patterns:
  `specify.prompt.md ... (Action N)` and `{doc}.md §N`, then verifies the
  referenced heading actually exists — `## Action N` in that pack's own
  `specify.prompt.md`, or a top-level `## N. ...` heading in that doc's
  own `*-template.md`. Each pack is checked against its own copies, not a
  shared assumption, since packs can diverge.
  - Deliberately skips `*.summary.md §N` references — AI-2 summaries are
    a compressed digest with no guaranteed section numbering, so checking
    them would produce false positives rather than real findings.
  - A `.md` reference to a doc key with no matching template is reported
    as a note, not a failure — usually means the reference wasn't to a
    real document at all.
- New CI job `cross-reference-check` (`.github/workflows/ci.yml`), and a
  new section in the root `CLAUDE.md`'s "Testing Setup Scripts" alongside
  the other two harnesses.

### Verified

- Confirmed the linter actually works, not just that it runs clean: it
  caught two real bugs in **itself** during development —
  - a `Path.parents[]` off-by-one that made it silently scan a
    nonexistent directory (always reported success regardless of input);
  - a heading-number regex that matched subsection numbers too (`### 3.1`
    still contributed `3` to the set even after the real `## 3. ...`
    heading was renamed), so a renamed top-level section went undetected
    as long as any `N.x` subsection survived.
- After both fixes: passes clean on the current repo (50 real references
  checked across 6 packs, confirmed with `--verbose`); deliberately
  renaming a real `## Action 2` heading and a real `## 3.` heading in
  scratch tests both produced a clear `file:line` failure, then passed
  again once reverted.
- `cli-python` `pytest tests/ -q`: 688/688 (unaffected — new standalone
  script, no existing code touched).
- `assert-output.sh` clean on both worked examples, `test-setup.sh`
  15/15, `test-setup-micro.sh` 12/12.

---

## [2.7.90] — 2026-07-23 (Fix: dashboard listed security before data-model, backwards from the recommended order)

### Fixed

- The extended-docs dashboard steps listed `security-design` before
  `data-model`. Neither depends on the other, so this was never a
  correctness bug — but `next_action` picks the first non-done step in
  list order, so at `mvp+` scope with nothing generated yet, the
  dashboard told users to run `/specify-doc security` before ever
  mentioning `data-model`, backwards from the recommended sequence
  (data-model → security → component-spec/ux-flow if applicable).
- Swapped the order. At `pilot` scope this has no visible effect
  (`data-model` is skipped there regardless); at `mvp+` the dashboard's
  next action now correctly says `/specify-doc data-model` first.

### Verified

- `cli-python` `pytest tests/ -q`: 688/688 passed (unaffected — no test
  asserted ordering between these two steps).
- Live `build_pipeline()` run at `mvp` scope confirmed the corrected
  order.

---

## [2.7.89] — 2026-07-23 (Fix: dashboard's collapsed "Extended Specs" row hid missing docs)

Asked directly whether the dashboard tells someone when they forgot to
run `/specify-doc` for a required extended doc. It didn't — checked the
real code instead of assuming.

### Fixed

- **`status.py`'s single "Extended Specs (Data Model, Security, ...)"
  dashboard row** was backed by a bare existence check — "does at least
  one `.md` file exist under `.specify/service/`?" — so generating just
  `security-design.md` already flipped the *entire* row to done, silently
  hiding that `data-model.md` (or `component-spec.md`/`ux-flow.md` for
  frontend-type projects) was still missing.
- The same collapsed step was also skipped entirely at `pilot` scope,
  contradicting CLAUDE.md's own Scope Reference table —
  `security-design.md` is required at every scope (pilot gets Threat
  Assessment / §1 only, never zero).

### Added

- Each extended doc now gets its **own** dashboard step, tracked
  independently: `security-design` and `data-model` check their own file
  under `.specify/service/` via a new `_service_doc_info()` helper;
  `component-spec`, `ux-flow`, `screen-spec`, `resilience`, and
  `investigation` are now ordinary per-feature steps (they already had
  per-file tracking, they just weren't wired into the pipeline at all).
- Type-specific docs (`component-spec`/`ux-flow`/`screen-spec`) only
  appear as dashboard steps when the project's type actually uses them —
  detected via template-file presence under `.specify/templates/` for the
  4 single-type packs, or `manifest.yml`'s `project_type` field for
  `sdd-universal` (which ships every template regardless of type, so
  presence-detection alone can't distinguish there). `cli`/`library`/`iac`
  deliberately show none of the three rather than guessing.
- Corrected scope gating: `security-design` is never scope-skipped;
  `data-model`/`component-spec`/`ux-flow`/`screen-spec` stay `mvp+`;
  `resilience`/`investigation` stay `full`-only — each with its own reason
  instead of one shared skip for the whole block.

### Verified

- `cli-python` `pytest tests/ -q`: 688/688 passed (6 new regression tests
  — independent per-doc tracking, corrected pilot-scope gating, and
  type-specific applicability).
- Live `build_project_status()` run against `examples/todo-api` and
  `examples/habit-tracker-web` confirmed `security-design`/`data-model`
  now track independently and `component-spec`/`ux-flow` correctly appear
  only for the frontend-type example.
- `assert-output.sh` clean on both worked examples, 33/33.
- Dashboard frontend (`dashboard.py`) needed no changes — it already
  renders every step generically from `label`/`state`/`skip`/`command`.

---

## [2.7.88] — 2026-07-23 (Fix: dead "Action 2 doc-set table" pointer broke /specify-doc discoverability)

Asked how an end user is supposed to know which `/specify-doc {name}` to
run, given something like a database schema is needed by almost every
project. Checked the real files instead of trusting memory — the answer
turned out to be a genuine bug, not just a UX gap.

### Fixed

- **`specify-doc.prompt.md`, `specify-srd.prompt.md`, and
  `orchestrate.prompt.md`** (all three fully shared, byte-identical
  across all 5 packs) repeatedly pointed at "the doc-set table in
  `specify.prompt.md` (Action 2)" for two jobs: listing what's left to
  generate when `/specify-doc` runs with no argument, and gate-checking
  whether a doc applies to the project's scope/`project_type`. That table
  didn't exist — `grep '^## Action'` across every pack's
  `specify.prompt.md` found only `Action 1` (Constitution Part 2)
  anywhere. Dead pointer in all 5 packs.
- The gap was invisible in Claude Code specifically because each pack's
  own `CLAUDE.md` (auto-loaded at session start) already lists the real
  doc names and their scope gates, so the agent quietly fell back on
  that. It isn't invisible for tools that enter through
  `copilot-instructions.md` instead, and `sdd-universal`'s own
  `CLAUDE.md` didn't have a working fallback either — it punted with
  "any other extended doc" instead of saying which of
  `component-spec`/`ux-flow`/`screen-spec`/`resilience`/`investigation`
  apply to which of its 10 `project_type`s.

### Added

- A real `## Action 2 — Extended Document Set` table in `specify.prompt.md`
  for `sdd-backend-service`, `sdd-frontend-spa`, `sdd-mobile`, and
  `sdd-fullstack`, each sourced from that pack's own `CLAUDE.md` so the
  two stay consistent.
- A project_type-grouped Action 2 matrix for `sdd-universal`
  (consumer-view / mobile / server-service / no-runtime-service) instead
  of a false-precision 10-type table — the framework doesn't itself
  define per-type applicability for `cli`/`library`/`iac` cleanly, so
  those are marked ask-the-user-first rather than a guessed yes/no.
- `specify-doc.prompt.md`'s no-argument behavior now explicitly reads
  the Action 2 table (filtered by scope/`project_type`), diffs it
  against what already exists on disk, and lists only what's missing —
  instead of vaguely "listing remaining documents" with nothing concrete
  to check against.
- `sdd-universal CLAUDE.md`'s vague `/specify-doc {name} → any other
  extended doc` line now points at the Action 2 table instead of leaving
  it to guesswork.

### Verified

- Every `Action 2` reference across all 5 packs now resolves to a real
  heading (grepped and confirmed after the fix).
- `specify-doc.prompt.md` confirmed byte-identical across `_shared/full`
  and all 5 packs via `md5sum` after `sync-blocks.sh`.
- `cli-python` `pytest tests/ -q`: 682/682 passed (unaffected —
  prompt/doc-only change).
- `assert-output.sh` clean on both worked examples (`todo-api`,
  `habit-tracker-web`), 33/33.

---

## [2.7.87] — 2026-07-22 (Fix: specify-doc's living-doc walk never re-synced Confluence)

Asked directly whether *all* living-document updates get pushed to
Confluence. They didn't.

### Fixed

- **`specify-doc.prompt.md`'s own SKIP/ADD-unit/UPDATE-unit walk** — the
  path a later feature normally takes to extend `data-model.md`,
  `security-design.md`, or `component-library.md` on its own, not via a
  formal Change Request — merged the approved unit, bumped the version
  header, appended Version History, and regenerated the `.summary.md`,
  but never re-pushed the change to Confluence or Jira.
  `change.prompt.md`'s own living-doc handling already did this correctly
  (`sdd review apply --doc {doc-key}`, confirmed at 3 separate spots) —
  `specify-doc.prompt.md`'s native walk never got the same fix. Practical
  effect: a second feature adding a new entity to an already-reviewed
  `data-model.md` through the normal `/specify-doc data-model` walk would
  merge correctly on disk but leave the Confluence page silently stale.

### Added

- Step 5 in the living-doc "On approval" list: `sdd review apply --doc
  {doc}` — re-pushes to Confluence and posts a re-review comment on Jira
  if either is configured, skips silently otherwise. Fixes `data-model`,
  `security-design`, and `component-library` in one shared-file edit.

### Verified

- Prompt-only change — no manifest.yml field changes, no CLI behavior
  change. `cli-python` pytest 682/682 (unaffected), `assert-output.sh`
  clean.

---

## [2.7.86] — 2026-07-22 (Fix: separate plan_mode had no API Design path at all)

Asked directly whether unified `design.md` and separate `arch.md`/`hld.md`/
`adr.md` actually cover the same ground. They didn't — separate mode was
silently missing an entire pipeline stage, not just a formatting gap.
Findings were verified against the real template/prompt files (not
memory) before fixing, after an initial pass wrongly claimed
`design-template.md` needed "promoting" into the shared-sync system — it
was already there, confirmed by re-checking with `md5sum` across
`_shared/full` and all 5 packs.

### Fixed

- **Separate `plan_mode` (`/plan-arch` → `/plan-hld` → `/plan-adr`) never
  generated `.specify/service/api-spec.md` at all.** No mention of "API
  Design" or "api-spec" existed anywhere in `arch-template.md`,
  `hld-template.md`, `adr-template.md`, or their three prompts.
  `task.prompt.md`'s QA-endpoint-source line, `lld-template.md`'s
  References table, and `ava.prompt.md`'s "api spec" routing row all
  hardcoded `design.md`/`design.summary.md` with zero `plan_mode`
  branching — even though every other read in those same files correctly
  branched. `ava.prompt.md` even routed to `specify-doc.prompt.md`, which
  explicitly refuses to generate `api-spec` ("has moved to
  `/plan-design`"). Net effect: a `backend-service`/`fullstack`/
  `universal` project on `plan_mode: separate` never produced a working
  API design at all — `openapi.yaml` generation (which reads
  `api-spec.summary.md`) would come up empty too.
- **`hld-template.md` had no Error/Failure Paths diagram**, despite
  `design.md` §2.5 generating one unconditionally today, across all 5
  packs, for every unified-mode feature.
- **Structural columns had drifted between the two modes**:
  `design.md`'s Key Design Decisions table had no "Alternatives
  Rejected" column, its System Layers table had no "what it must NOT
  do" boundary column, and its NFR mapping had no `Decision (DEC-NNN)`
  traceability link — `arch-template.md` (separate mode's equivalent)
  already had all three. `design.md`'s ADR block used a compact bullet
  list while `adr-template.md` used a full Options A/B/C + pros/cons
  structure.
- **`plan-hld.prompt.md`'s own NFR Summary instruction only listed 2
  columns** (`NFR-NNN | Target`) while its own template defines 4
  (`NFR-NNN | Category | Target | Component budget allocation`).
- **`adr-template.md` had a dead `*ADR Index: docs/architecture/
  decisions.md*` pointer** — no command ever generated that file.

### Added

- `hld-template.md` gained `## 6. API Design` (ported from `design.md`
  §3, including its skip-list and provides/consumes branch — the same
  guard logic already proven safe across all 10 `sdd-universal` project
  types) and `## 4. Error / Failure Paths`; sections renumbered
  accordingly (Technology Stack → 7, NFR Summary → 8).
- `plan-hld.prompt.md` gained matching Diagram 4 and Section 6
  instructions, including the full living-doc `api-spec.md` walk logic
  ported from `plan-design.prompt.md` §3.
- `design-template.md` §1.2/§1.3/§1.4 gained the three missing columns;
  §4 ADR block expanded to Options A/B/C depth. `plan-design.prompt.md`
  §1 and §4 instructions updated to match.
- All 5 packs' `CLAUDE.md` "PLAN Sub-Commands" section updated to note
  `hld.md` now also covers API design.

### Verified

- Every edited file confirmed byte-identical across `_shared/full` and
  all 5 packs via `md5sum` after `sync-blocks.sh`.
- Template/prompt-only change — no manifest.yml field changes, no CLI
  behavior change. `cli-python` pytest 682/682 (unaffected),
  `assert-output.sh` clean on both worked examples, `test-setup.sh` 15/15.

---

## [2.7.85] — 2026-07-22 (Fix batch: template/parser audit — 11 fixes across the pipeline)

A full audit of all 31 templates in `sdd-backend-service` (representative of
the 5 non-micro packs) asked two questions per document: what's written but
never read downstream, and what's read but never actually generated. Found
20+ issues; this release fixes the 7 critical (Tier 1) and 4 follow-up
(Tier 2) items.

### Fixed — Tier 1 (critical)

- **`/implement` never flipped `tasks.md`'s own checkboxes.** It reported
  completion in chat but left every `- [ ]` unchanged — `sdd dashboard`'s
  task progress and Business Objectives rollup are computed purely by
  counting checked boxes, so a task could ship and still read as
  "Not Started" forever. `implement.prompt.md` (all 5 packs) now instructs
  flipping the acceptance-criteria checkboxes for the task just confirmed.
- **`CHG-NNN` tasks were invisible to the task-completion parser.**
  `_TASK_HEADING_RE` in both `status.py` and `sdd_parser.py` only matched
  `TASK-NNN`/`PERF-NNN` headings — `status.py` was additionally missing
  `PERF-NNN` outright (an inconsistency between the two regex locations).
  Widened both to `TASK-NNN|PERF-NNN|CHG-NNN`. Also found mid-fix:
  `change.prompt.md`'s own CHG-NNN generation template used a
  colon/indented format with no markdown heading at all — the regex
  widening alone would have been a no-op, so the template was rewritten to
  match `tasks-template.md`'s real `###` heading-block shape.
- **`validate.prompt.md`'s own step numbering collided with its
  template.** The blocking "3a. NEEDS CLARIFICATION SCAN" step shared a
  number with the template's real "§3a Use Case Business Review" section.
  Renumbered to "0a" (right after the existing "0. CHECKLIST GATE"
  pre-flight), and `validate-template.md` gained the missing
  `## 0a. Needs Clarification Scan` table it never actually had.
- **`use-cases-template.md` had no Independent Test field**, despite
  `/checklist`'s own spec-quality rubric checking for "UCs without
  Independent Test." Added the field to both UC blocks;
  `specify-uc.prompt.md` fills it.
- **`security-design-template.md` mixed CVSS scoring into a threat table
  that always intended DREAD** (per `specify-doc.prompt.md`'s own 5-factor
  rubric), with a mismatched `/release`-time gate instead of the intended
  `/plan-design`-time gate. Reconciled to DREAD everywhere, corrected the
  gate, fixed the STRIDE section's scope gating (`mvp+`, with DAST/Pen
  Test explicitly `full` only), and added a new OWASP Top 10 Controls
  Mapping table to §2 (mobile's existing OWASP MASVS table was moved into
  scope rather than duplicated).
- **CF-NNN (Consistency Findings) never reached `/clarify`'s gate**,
  despite `analyze.prompt.md`'s own severity guide already saying
  "CRITICAL — block /clarify." Added a CF-NNN section + STATUS TABLE row
  to `clarify-template.md`, an instruction to `clarify.prompt.md` to
  include every CRITICAL finding, and widened `review.py`'s
  `_CLARIFY_ITEM_CODE` regex to recognize the `CF` prefix end-to-end
  (parse, patch, push-questions/pull-answers).
- **`constitution-amendment-template.md` was entirely dead** — referenced
  only as "the save location" by `change-rules.md`, nothing ever generated
  it. Wired into every pack's `/specify` GATE-1 re-run flow: confirming a
  proposed amendment now saves a record to
  `.specify/memory/constitution-amendments/CA-{NNN}.md`.

### Fixed — Tier 2 (follow-up)

- **`release.md`'s §6 Business Objective Closure had no way to record "not
  met"** — only `[ ] Yes [ ] Pending`. Added `[ ] No` across all 5 packs,
  and `status.py` gained `_parse_release_bo_closure()` wired into
  `build_bo_rollup()` as new `outcome`/`measured_result` fields —
  additive, alongside (not replacing) the existing task-completion-derived
  `status` field. `sdd dashboard`'s Business Objectives table gained a
  Business Outcome column showing Met/Not Met/Pending once `/release` has
  run.
- **`qa-testcases.md`'s `UAT Relevant: Yes` rows never reached the UAT
  plan** — `/release`'s UAT Plan step derived scenarios purely from
  `use-cases.md`, with no link to which TC-NNN actually gets executed for
  sign-off. `release-template.md`'s UAT Plan table gained a TC-NNN column
  (all 5 packs, adapted per pack's existing column set), and
  `release.prompt.md` now pairs each UC-NNN row with its
  `qa-testcases.md` TC-NNN(s) at mvp+, or `smoke-tests.md`'s TC-S-NNN at
  pilot.
- **`jira-export-template.md`'s manual-import CSV had no test-case
  traceability** — FR/UC references were carried into the CSV fallback
  path, but TC-NNN wasn't. Added a TC Reference column (Task rows only) to
  both CSV samples and the manual-mapping instructions.
- **`jira.py`'s `parse_changeset()` silently dropped the PR and Status
  columns** from a changeset's §4 `CHG-NNN Implementation Tasks` table —
  only `sdd_id`/`description`/`satisfies`/`est_lines` were ever captured.
  Rewritten to a tolerant per-line cell parser that captures both
  (`pr`/`status` default to `None` for older 4-column rows, never
  dropping the row), and surfaces them in the pushed CHG issue's
  description.

### Added

- New pytest coverage for every fix above: task-heading PERF/CHG counting,
  CF-NNN parse/patch round-trip, `_parse_release_bo_closure`
  (met/not_met/pending/unfilled-placeholder), `build_bo_rollup` outcome
  wiring, and `parse_changeset`'s PR/Status/legacy-4-column/placeholder-row
  handling.

### Verified

- `cli-python` pytest 682/682 (was 672 before this batch).
- `packs/_shared/tests/assert-output.sh` clean on both worked examples
  (`examples/todo-api`, `examples/habit-tracker-web`).

---

## [2.7.84] — 2026-07-18 (Docs: HOW-TO-USE.md Phase 0 never mentioned `sdd config init`)

Asked directly, right after the v2.7.83 `sdd config init` fix: "is that all
document in how to use?"

### Fixed

- **`HOW-TO-USE.md`'s "Phase 0 — Setup (before any command)" section listed
  `/create-context` and `sdd init`/`setup.sh`, but never mentioned `sdd
  config init`/`sdd config test` at all.** A reader following that section
  top to bottom for the full pre-flight checklist would not discover
  Jira/Confluence setup exists until a much later, unrelated section
  mentioned it in passing (e.g. "Configure reviewers... Run `sdd config
  init`" inside Document Review Gates).

### Added

- A new `#### Jira/Confluence integration — sdd config init (optional)`
  subsection, immediately after the existing `sdd init`/`setup.sh`
  subsection in Phase 0, in all 5 non-micro packs' `HOW-TO-USE.md`. States
  it's optional and skippable for chat-mode approvals, shows `sdd config
  init` + `sdd config test`, and notes it can be run at any later point,
  not just here.

### Verified

- Docs-only change — cli-python pytest 670/670 (unaffected).

---

## [2.7.83] — 2026-07-18 (Fix: `sdd config init` scaffold missing most of integrations.yml)

Reported directly: "while creating integration file, it does not fill the
full information ... we have made many changes to integrations.yml file."

### Fixed

- **`sdd config init`'s `.specify/integrations.yml` scaffold was built
  from a small hand-maintained template string** in `cli-python/sdd/
  commands/config.py` that had drifted far behind the real
  `integrations.yml.example`. Confirmed: the wizard's template only ever
  produced `profile` + a 9-key `page_map` + `jira.custom_fields.
  story_points` — every section added to `integrations.yml.example` over
  the life of this project (`project_keys`, `parent_field_by_level`,
  `custom_fields_by_level`, `diagrams`, `document_reviews`,
  `pr_automation`, `code_review`) was never ported into the wizard's own
  template. Root cause: two independent sources of truth for the same file
  shape, nothing enforcing they stay in sync.

### Changed

- `sdd config init` now fills `profile`/`project_key`/`space_key`/
  `parent_page_id` into the project's own shipped `.specify/
  integrations.yml.example` (present in every project since `sdd init`)
  instead of a separate template string — every section the current pack
  version documents is present in the scaffolded file, most left commented
  out exactly as the `.example` ships them. Falls back to the old minimal
  built-in template only if no `.example` file exists in the project.
- `document_reviews:` carries the example's placeholder Jira accountIds
  verbatim — the wizard now prints an explicit warning to replace them
  with real reviewers (or delete entries you don't want routed through
  Jira) before `sdd review submit`.

### Verified

- 6 new pytest cases: placeholder substitution, every optional section
  present, blank `parent_page_id` stays commented, `{feature}`/`{project}`
  template vars left untouched, and two end-to-end CliRunner tests
  (`.example` present / absent).
- cli-python pytest 670/670.

---

## [2.7.82] — 2026-07-18 (Feature: Business Objectives traceability + dashboard rollup)

`brd.md`'s Business Objectives (§2) and Business Requirements (§5) were
previously unlinked siblings — nothing in the SDD chain actually connected
"why we're building this" to "what implements it." Requested directly: "can
we have BO and mapped use case and show in the dashboard? What is
implemented under which feature and which status are we in?"

### Added

- **`brd-template.md` §5 gets a "Serves BO" column** (all 5 non-micro
  packs) — every `BR-NNN` must now cite which `BO-NNN` from §2 it serves.
  `specify-brd.prompt.md` updated with fill instructions: an unlinked BR
  is either scope creep or a missing objective, and either way it should
  be surfaced, not left blank.
- **`status.py` traceability parsers** — `_parse_brd_bo` (brd.md §2/§5,
  tolerant of 3- or 4-column Business Objectives tables and legacy
  `Satisfies` column headers seen in real generated docs),
  `_parse_uc_traces` (use-cases.md's Use Case Index table, falling back
  to scanning narrative `### UC-NNN` sections' `**Trace:**`/`**BR
  Traces:**` lines when no Index table exists), `_parse_srd_fr` (srd.md's
  Functional Requirements table, tolerant of the 5-column canonical shape
  and a 4-column `Satisfies` variant, plus §4 Use Case Coverage as a
  UC-link fallback).
- **`build_bo_rollup()`** chains BO → BR (brd.md "Serves BO") → FR
  (srd.md "Source"/"Satisfies" — the reliable bridge, since
  use-cases.md's FR Traces column is only backfilled by a manual
  `/specify-srd` re-run and is often skipped in practice) → TASK
  (tasks.md "Satisfies:" field + completion status). UC-NNN is gathered
  from both use-cases.md and srd.md for display; status/percent-done is
  computed from the BR→FR→TASK bridge. Status: task completion 0% → Not
  Started, partial → In Progress, 100% → Done (not `release.md`'s BO
  closure field, so the dashboard reflects live task state).
- **Dashboard "Business Objectives" card** — a cross-feature rollup
  (BO, Objective, Feature, Use Cases, Status, Progress) above the
  per-feature blocks, plus a per-feature card inside each feature's
  block.

### Verified

- End-to-end against `examples/todo-api`'s real
  brd.md/use-cases.md/srd.md/tasks.md (which deviate from the raw
  templates in exactly the ways the tolerant parsing above accounts for)
  via the dashboard's live HTTP server, screenshotted in both light and
  dark mode.
- 20 new pytest cases covering 3-vs-4-column BO tables, legacy
  `Satisfies` headers, unfilled template placeholders, the Use Case Index
  fallback, orphaned BRs, and the flattened cross-feature rollup.
- `sync-blocks.sh` clean, cli-python pytest 664/664.

---

## [2.7.81] — 2026-07-17 (Fix: sdd-micro/setup.sh had zero CI test coverage)

Found during a full end-to-end review of the `sdd-micro` pack.

### Fixed

- **`sdd-micro/setup.sh` was never exercised by any test.**
  `packs/_shared/tests/test-setup.sh`'s own header says "Smoke tests for
  sdd-universal/setup.sh" and hardcodes `PACK_DIR=packs/sdd-universal` —
  `sdd-micro/setup.sh` (a materially different script: `--project`/
  `--feature` only, no `--type`/`--scope`, its own non-interactive
  default fallback to `"untitled-project"`/`"main"`) has never been run
  by CI, despite root `CLAUDE.md` describing the smoke-test suite as
  covering "injection-class names, all project types, and
  non-interactive execution" in a way that read as a blanket guarantee.

### Added

- `packs/_shared/tests/test-setup-micro.sh` — mirrors `test-setup.sh`'s
  `ok()`/`nok()` structure, covering the same injection classes (single
  quote, double quote, backslash, ampersand, slash, unicode) plus two
  cases specific to this script: the no-args non-interactive default
  path, and "unknown option" rejection (`sdd-micro`'s `setup.sh` has no
  `--type` flag, unlike `sdd-universal`'s). Wired into
  `.github/workflows/ci.yml`'s existing `setup-smoke-tests` job as a
  second step, and documented in root `CLAUDE.md`'s "Testing Setup
  Scripts" section.

### Verified

- Confirmed the new suite has teeth: temporarily disabled
  `sdd-micro/setup.sh`'s double-quote validation guard, confirmed the 2
  double-quote-rejection test cases failed as expected (exit 1), then
  restored the original file (`git diff` clean) and re-ran clean
  (12/12).
- `test-setup.sh`: 15/15, `test-setup-micro.sh`: 12/12,
  `assert-output.sh`: 33/33, `cli-python` pytest: 648/648 — all passed.
- `sdd-micro`'s own `manifest.yml` `sdd_version` deliberately left
  untouched (still `2.7.41`) — this fix only adds test/CI
  infrastructure in this repo; it changes nothing `sdd-micro` itself
  ships to a user's project via `sdd init --pack sdd-micro`.

---

## [2.7.80] — 2026-07-16 (Fix: data-model-template.md Version History gap in 3 packs, STRIDE column wording drift in sdd-universal)

Found while independently re-verifying the v2.7.79 fix batch's own
cross-pack consistency (requested review, not a new bug report).

### Fixed

- **`data-model-template.md` was missing `## Version History`** in
  `sdd-frontend-spa`, `sdd-mobile`, and `sdd-fullstack` — only
  `sdd-backend-service` and (as of v2.7.79) `sdd-universal` had it. Caught
  because `sdd-universal`'s new `data-model-template-frontend.md`/
  `-mobile.md` flavor files (copied verbatim from those packs' own
  templates) diffed non-empty against their source — the source packs
  were missing content the copies had. Added Version History to all
  three.
- **`security-design-template.md`'s STRIDE threat table column header was
  inconsistent** — `Threat (STRIDE)` in `sdd-universal`, `Threat (STRIDE
  category)` in the other four packs. Pre-existing wording drift, not
  something the v2.7.79 CVSS-column fix introduced. Normalized
  `sdd-universal` to match.

### Verified

- `sync-blocks.sh` clean
- `cli-python` pytest: 648/648 passed
- `assert-output.sh`: 33/33 passed
- Every pack-specific prompt's `.specify/templates/{doc}-template.md`
  references checked against actual files on disk — zero broken
  references found across all 5 packs

---

## [2.7.79] — 2026-07-16 (Fix: runbook-template.md living-doc framing, security-design/data-model/api-spec drift, release-template.md pilot-scope rollback gap, sdd-universal template flavor branching)

Full follow-up on the v2.7.78 pass's "Known gaps not fixed in this pass"
list, plus one new correctness bug (`runbook-template.md`) found
independently while re-reviewing every template in every pack.

### Fixed

- **`runbook-template.md` was missing its living-document framing in 4 of
  5 packs.** `sdd-backend-service`'s copy correctly opens with a
  "**Living artifact**" paragraph explaining that `docs/runbook/local-setup.md`
  describes the whole service and should be extended, not regenerated —
  `sdd-frontend-spa`, `sdd-mobile`, `sdd-fullstack`, and `sdd-universal`
  had none of that text, and used `# Feature: {Feature Name}` instead of
  `# Service:`/`# App:` in the header. This directly contradicted each
  pack's own `CLAUDE.md`, which lists Runbook as a living document for
  every pack. An agent following the template literally would have
  treated the runbook as a fresh per-feature doc, silently dropping a
  prior feature's Troubleshooting/Environment Variable/On-Call additions.
  Fixed all four.
- **`security-design-template.md` was inconsistently developed across
  packs.** Only `sdd-backend-service` had a `## Version History` table;
  only `sdd-universal` had the CVSS scoring column in its §3 threat
  model and the 2-row Security Officer/Tech Lead `## Approvals` table
  (the other four packs had one generic placeholder row). Reconciled all
  five packs to have all three — the CVSS column, the named Approvals
  rows, and Version History.
- **`data-model-template.md` and `api-spec-template.md` were missing
  `## Version History` tables** in `sdd-universal` (both docs) and
  `sdd-fullstack` (api-spec only). Added. Also fixed a stale/incorrect
  `## References` row in `sdd-universal`'s `api-spec-template.md` that
  cited `arch.summary.md ... refined at /plan-arch: ports/adapters` —
  leftover text that didn't match how `api-spec.md` is actually fed
  (per `plan-design.prompt.md` §3: `design.summary.md`, which feature
  added/changed which endpoints).
- **`release-template.md` §7 Rollback Plan had a broken reference at
  pilot scope** in `sdd-backend-service`, `sdd-frontend-spa`,
  `sdd-mobile`, and `sdd-fullstack` — it pointed to
  `docs/runbook/local-setup.md §6`, but the runbook is never generated
  at pilot scope (per each pack's own Scope Reference table), so the
  pointer was dead. `sdd-universal`'s copy already had the fix: a
  pilot-scope fallback rollback table used when the runbook doesn't
  exist. Backported that pattern, plus two extra Post-Deploy Smoke Test
  monitoring rows `sdd-universal` already had, to the other four packs.
- **`sdd-universal` had no project-type branching for
  data-model/security-design/runbook template flavor.** Its
  `specify-doc.prompt.md` and `implement.prompt.md` always read the
  default (server-side/DB-schema) template regardless of the detected
  `project_type` — a `frontend-spa` or `mobile` project would get
  server-side schema/threat-model content instead of client
  state/storage-model or local-cache-model content. Added `project_type`
  branching (`frontend-spa`/`desktop` → `*-template-frontend.md`,
  `mobile` → `*-template-mobile.md`, else → the existing default) to the
  **shared** `specify-doc.prompt.md` source (a safe no-op for the other
  four packs, which have no `project_type` field) and to `sdd-universal`'s
  own `implement.prompt.md` for runbook generation. Shipped the new
  frontend/mobile flavor template files:
  `data-model-template-{frontend,mobile}.md`,
  `security-design-template-{frontend,mobile}.md`,
  `runbook-template-{frontend,mobile}.md`.

### Verified

- `sync-blocks.sh` clean after the shared `specify-doc.prompt.md` change
  propagated correctly to all 5 packs
- `cli-python` pytest: 648/648 passed
- `assert-output.sh`: 33/33 passed (both worked examples)
- `test-setup.sh`: 15/15 passed
- Migration-chain tests (`test_migration_table_is_a_connected_chain_ending_at_current`,
  `test_each_migration_stamps_its_own_to_version`): both passed

---

## [2.7.78] — 2026-07-16 (Fix: sdd-universal missing UI templates, brd-template.md drift, design-template.md numbering gap)

### Fixed

- **`sdd-universal` was missing four template files its own prompt
  documents as valid.** `specify-doc.prompt.md` lists `/specify-doc
  component-spec | ux-flow | screen-spec` as commands and reads
  `.specify/templates/{doc}-template.md` directly with no fallback —
  but `sdd-universal/.specify/templates/` had none of
  `ux-flow-template.md`, `screen-spec-template.md`,
  `component-spec-template.md`, or `component-library-template.md`.
  Since `sdd-universal` is the pack that auto-detects mobile/frontend
  project types, this broke exactly for the types it claims to
  support. Added all four; `specify-doc.prompt.md`'s pack list for
  `component-spec-template.md` now includes `sdd-universal`.
- **`ux-flow-template.md`, `screen-spec-template.md`, and
  `component-spec-template.md` had no ID scheme or `Version History`
  table** — every other template in the system has both. Added
  `FLOW-NNN`/`ERR-NNN`/`EDGE-NNN` IDs to `ux-flow-template.md`,
  `SCR-NNN` to `screen-spec-template.md`, `COMP-NNN` to
  `component-spec-template.md`, plus `Version History` to all three.
  Since these three were already byte-identical across every pack
  that ships them, enrolled them into `_shared/full/` so they're
  sync-governed going forward.
- **`brd-template.md` had drifted uncoordinated, not deliberately.**
  `sdd-universal`'s copy had gained a `§9 Investment Summary` section
  and domain-aware regulation pre-seeding (PCI/HIPAA/GDPR signal
  detection) that the other four packs — byte-identical to each
  other — never received. `brd-template.md` was not part of
  `_shared/full/` despite BRD content having no legitimate reason to
  vary by project type (unlike `api-spec`/`data-model`/
  `security-design`/`runbook`, which correctly do). Enrolled into
  `_shared/full/` using `sdd-universal`'s fuller version as canonical.
- **`design-template.md` §3 skipped from 3.2 to 3.5** with no §3.3/
  §3.4 content anywhere in the file — a leftover from prior editing,
  not intentional. Renumbered to §3.3.

### Known gaps not fixed in this pass

- `sdd-universal`'s `specify-doc.prompt.md` has no project-type
  branching for which *flavor* of `data-model-template.md`/
  `security-design-template.md` to use — a detected frontend/mobile
  project would currently get the DB-schema/server-side flavor
  instead of a state-storage/client-side one. Needs prompt-level
  type branching, not a file copy — scoping separately.
- `sdd-universal`'s copies of `api-spec-template.md`,
  `data-model-template.md`, `runbook-template.md`, and
  `openapi-template.md` are each missing "Living artifact" callouts
  or `Version History` tables that `sdd-backend-service`'s
  same-flavor copies already have.
- `security-design-template.md`: `sdd-backend-service` is missing the
  CVSS-scoring column `sdd-universal` has; `sdd-universal` is missing
  the `Version History` table `sdd-backend-service` has. Content
  should stay pack-specific; structure should not.
- `release-template.md`: `sdd-universal` has deploy-health alerting
  checks and an expanded pilot-scope rollback section never
  backported to the other packs.

## [2.7.77] — 2026-07-15 (Fix: self-approval risk undocumented, coverage gate was a bare echo, no test caught either)

### Fixed

- **Verified an external review with grep instead of accepting it (or my
  own prior response to it) on faith.** An external agent reviewed the
  sdd_parser.py and release.md/runbook fixes above and raised several
  concerns. Re-checked every claim against the actual repo: some held up
  (self-approval risk, the fake coverage gate), some didn't (a cited
  "245 tests" figure was stale — actual count was 592; the two-CLI and
  onboarding-path concerns turned out to already be addressed in the
  README/`CATALOG.md`). Three confirmed, real gaps were fixed:
  - **Self-approval risk was undocumented.** `review-gates.md` now
    explicitly states that nothing in chat mode stops the same
    conversation that drafted a document from also being the one that
    approves it — there is no independent reviewer identity check, only
    the human typing the word "approved". Previously this was only
    implicit in the scope-based mode guidance (pilot → chat, mvp →
    local, full → jira).
  - **The coverage gate was a bare `echo`, not a real check.** Reading
    the actual `quality-gate.yml` in every pack confirmed the "Enforce
    coverage gate" CI step always printed a success-sounding message
    regardless of whether coverage was configured at all — worse than
    "inert template," since it looked like a real pass. Replaced with a
    genuine tripwire: the step now greps `pom.xml` for
    `jacoco-maven-plugin`'s `<rules>` block (Java packs) or
    `vitest.config`/`jest.config`/`package.json` for
    `coverageThreshold`/`thresholds` (Node packs), and fails the CI job
    with actionable guidance if that configuration is missing — across
    all 5 packs, including `sdd-fullstack`'s separate backend and
    frontend jobs.
  - **No test would have caught the release.md/runbook gap that just
    shipped.** New `test_prompt_review_coverage.py`: for every doc key
    with an active `document_reviews` entry in the shipped
    `integrations.yml.example`, asserts the owning `.prompt.md` file
    actually contains a `sdd review submit --doc {key}` call, across all
    5 packs (56 cases). This is the buildable version of "run the
    pipeline against a mocked Jira/Confluence" — prompts are AI
    instructions, not executable code, so a structural presence check is
    what's actually feasible in CI. Verified the test has teeth by
    temporarily reverting `release.prompt.md` to its pre-fix state and
    confirming it fails exactly where the real bug was, then passes
    again once restored.

---

## [2.7.76] — 2026-07-15 (Fix: /release and /implement's runbook never went through Jira/Confluence review)

### Fixed

- **A full pipeline audit** (requested after the sdd_parser.py fix
  below — "in each step we should have jira and confluence") checked
  every command that's supposed to push to Jira/Confluence against what
  it actually does, and found two real gaps:
  - **`release.md` had zero Jira/Confluence wiring.** `release.prompt.md`
    only ever asked for an informal chat sign-off — regardless of
    `integrations.yml` — even though CLAUDE.md's own Jira-mode sequence
    table documents `release phase: Runbook → Release, reviewer: DevOps
    → Release Manager`, and the shipped `integrations.yml.example`
    already configures both `document_reviews.runbook` and `.release`
    with sequence numbers.
  - **The runbook (`docs/runbook/local-setup.md`) was never submitted
    for review at all** — not even chat-mode approval —
    `implement.prompt.md` generated/updated it and just left it there.
  - Both now go through the same Submit-for-Review + review-decision
    flow every other document in the pipeline uses, across all 5 packs.
  - **Backend bug found in the same sweep:** `resolve_doc_path()` had no
    case for `"runbook"` — `sdd review submit --doc runbook` would have
    resolved to the nonexistent `.specify/features/{feature}/runbook.md`
    instead of the real `docs/runbook/local-setup.md`. Confluence page
    nesting/title logic also didn't treat `runbook` as project-scoped
    (living) the way `data-model`/`security-design`/`api-spec`/
    `constitution` already are. New `PROJECT_SCOPED_DOCS` constant in
    `validate.py` fixes both, with regression tests locking in the
    correct path, page nesting, and page title behavior.
  - `integrations.yml.example`'s `page_map.release` entry was also
    commented out by default even though `document_reviews.release` was
    already active — a user copying the example as-is would have hit a
    missing-page_map-entry error the first time this new wiring ran.
    Uncommented to match `runbook`'s existing active entry.

---

## [2.7.75] — 2026-07-15 (Fix: sdd jira push and sdd pr create --task silently found zero stories/tasks)

### Fixed

- **`sdd_parser.py` never matched the actual shipped templates.** Found
  while helping a user debug why `sdd jira push` created nothing in Jira
  even after fixing their Jira/Confluence credentials — traced it to
  `sdd_parser.py`'s regexes expecting a heading/field format
  (`### STORY-NNN — Title` with an em-dash, `**As a**`/`**Satisfies:**`
  bold fields, `## TASK-NNN` at H2) that the shipped
  `feature-story-template.md`/`tasks-template.md` have not used for some
  time — they generate `### STORY-NNN: Title` (colon), `**As**`/
  `**Linked FRs:**` for stories, and `### TASK-NNN` (H3) with entirely
  plain, unbolded fields for tasks. `parse_stories()`/`parse_tasks()`
  returned an **empty list** for every correctly-generated document.
  - This silently broke `sdd jira push --level story/task` (reported
    "No stories or tasks found") and `sdd pr create --task TASK-NNN`
    (reported "TASK-NNN not found in tasks.md") — both on the
    framework's golden path, for every project using the current
    templates.
  - `sdd_parser.py` rewritten to match the current templates while
    still accepting the older em-dash/bold-field style found in this
    repo's own worked examples, so already-generated docs in either
    style parse correctly.
  - Also fixed: `_normalize_moscow()` required an exact `"must have"`
    string match, but the shipped template's bucket headers are
    `"Must Have Stories"` (trailing word) — every story silently fell
    through to the `could-have` default, mapping every pushed Jira
    Story to Low priority regardless of its actual MoSCoW bucket.
  - New golden-template tests parse the actual shipped
    `feature-story-template.md`/`tasks-template.md` files directly
    (not just hand-written fixtures), so a future template edit that
    breaks the parser fails CI instead of shipping silently broken
    again.

---

## [2.7.74] — 2026-07-15 (Enhance: dashboard shows live Jira ticket status for review-gate and Export tickets)

### Added

- **Live Jira ticket status, not just links.** The user asked directly:
  "do we show the Jira status also?" Investigation found the raw Jira
  status was already fetched but unused for review-gate tickets, and
  never fetched at all for Jira Export (Epic/Story/Task) tickets. Both
  gaps are now closed:
  - **Review-gate tickets**: each Jira pill now shows the ticket's raw
    Jira workflow status (e.g. `(In Review)`) as a suffix, alongside —
    not merged with — SDD's own `APPROVED`/`PENDING`/`NEEDS_REVISION`
    `review_status` badge. The two are legitimately different concepts
    (SDD's approval classification vs. the ticket's actual Jira
    workflow state) and are shown side by side.
  - **Jira Export tickets**: a new `_fetch_export_ticket_statuses()`
    (`dashboard.py`) reads the Epic/Story/Task keys from
    `docs/jira/{feature}/keys.yml` and resolves their live status with
    a single batched JQL `key in (...)` query, instead of one lookup
    per ticket. Keys are validated against `_JIRA_KEY_RE` before being
    interpolated into the JQL string — keys normally come from Jira's
    own API, but `keys.yml` is a plain file a user could hand-edit, and
    JQL has no parameterized-query binding.
  - `_fetch_review_links()`'s guard relaxed: previously required
    `document_reviews` to be configured before running at all, which
    would have blocked the new export-status fetch for a project using
    Jira only for progressive export (no review gates). Now requires
    only `jira:` or `confluence:` to be configured.
  - The dashboard's "🔄 Check Jira/Confluence review links" button is
    renamed to "🔄 Check Jira/Confluence status", since it now
    refreshes ticket status too — reusing the existing on-demand +
    5-minute auto-refresh mechanism rather than adding a second
    control.
  - Verified live (simulated API response, no live Jira instance in the
    sandbox): a review-gate pill correctly showed `Jira PROJ-9 (In
    Review)` next to its separate `PENDING` badge, and the Jira Export
    card correctly showed each Epic/Story/Task with its live status,
    e.g. `PROJ-2 (Done)`, `PROJ-3 (To Do)`.

---

## [2.7.73] — 2026-07-15 (Fix: dashboard stale approver name after a document reverts to Draft)

### Fixed

- **The Approve pill could keep showing a stale approver's name.**
  Flagged as a known, pre-existing edge case during the previous review;
  the user then asked how to fix it, so it's fixed now. `approvalMode()`
  and `approvedRowInfo()` (`dashboard.py`) previously trusted
  `d.local_approval` unconditionally — once a document had been approved
  once, its Approve pill kept showing that approver's name even after the
  document was regenerated back to `Draft`, since `.local-approvals.yml`
  isn't cleared just because a doc's content changed. Both functions now
  check the document's live `Status:` header first — the same
  authoritative-source rule the status badge itself already follows (see
  CLAUDE.md "Document Review Gates") — and only consult
  `local_approval`/the Jira review status/the doc's own Approvals table
  once the header actually says `Approved`. Verified live: a doc with a
  stale local-approval record but `Status: Draft` now correctly shows the
  **Approve** button and its Approvals tab says "Not yet approved."

---

## [2.7.72] — 2026-07-15 (Fix: dashboard badge color bug + stale "View" copy, found in a second UX review pass)

### Fixed

- **Constitution and Token Usage status badges silently lost their
  color.** A second dashboard UX review (the user asked for another full
  pass after the Details-panel consolidation) turned up two verified
  regressions, confirmed with a live headless-browser check of computed
  CSS/DOM before and after each fix:
  - `.kv span:first-child { color: var(--muted) }` used a descendant
    combinator, so it also matched a badge/pill nested inside a `.kv`
    row's value column whenever that badge was the value span's only
    child — a badge counts as `:first-child` of its own parent too. This
    silently forced the Constitution card's gate-1 badge and the Token
    Usage card's Real/Est "Source mix" badges to plain gray instead of
    their intended green, losing the color cue exactly where it
    mattered. Fixed with a child combinator (`.kv > span:first-child`),
    which only ever matches the row's own direct label span.
  - The info box's "Where this data comes from" text still said `"View"
    reads the raw .md file from disk` — a leftover from before the
    View/Approvals/Comments toggles were consolidated into one Details
    panel with tabs (2.7.71). Updated to reference the Content tab.

---

## [2.7.71] — 2026-07-15 (Enhance: dashboard Documents row consolidated into a tabbed Details panel)

### Changed

- **UX cleanup of the Documents row**, following a dashboard UX review
  the user asked for. Across this release cycle the Links cell had
  accumulated View, 👤 Approvals, 💬 Comments, a Jira pill, a Confluence
  pill, and a review-status badge — up to 7 elements in one cell, and
  opening View + Approvals + Comments together stacked three separate
  panels below the row.
  - Replaced the three independent expand-toggles with a single
    **Details** button that opens one panel with a **Content / Approvals
    / Comments** tab strip — only the active tab renders. The row is
    typically down to `[Approve] [Details] [Jira pill] [Confluence pill]`.
  - Posting a comment now opens the panel directly on the Comments tab.
  - Verified with Playwright: button count before/after, tab switching,
    comment-then-auto-switch, and that only one panel renders per
    document at a time (previously up to three could stack).

---

## [2.7.70] — 2026-07-15 (Enhance: dashboard per-document approver detail)

### Added

- **Documents card now answers "who should approve this, and who did."**
  The user asked: for a pending document, who should approve it (role
  and name, not just a role label)? For an approved one, who approved
  it, and was that via Jira or a manual/chat approval?
  - New `status.py._parse_approvals_table()` parses each document's own
    `## Approvals` table — present in every template and filled in
    identically regardless of review mode (chat/local/jira), so it's the
    one source of truth that works the same way everywhere. Handles both
    the current 4-column format (`Role | Approver | Status | Date`) and
    the older 3-column one from before the `Approver` column existed.
  - New `status.py._resolve_expected_approver()` normalizes a document's
    human-readable Role cell (`Product Owner`, `DevOps/SRE`) to
    `roles.yml`'s snake_case key convention and looks up the name
    already filled in there — a pending document now names the actual
    person, not just their role.
  - Each Documents row shows a compact one-line summary under the Status
    badge (`👤 Awaiting Product Owner: Jane Smith`, or the approver's
    name once approved) with no click required, plus a new `👤` toggle —
    matching the existing `💬` comments pattern — that expands the full
    Role/Approver/Status/Date table and states which mode recorded the
    approval (Local / Jira / Chat only — no audit file).
  - Fixed a related inconsistency along the way: the Approve pill next
    to the Approve button previously only showed a name in local mode —
    a Jira- or chat-approved document still showed a bare "Approve"
    button even though its Status header already said Approved. It now
    resolves the approver's name for every mode.
  - Verified end-to-end with Playwright across a pending single-approver
    doc, an approved doc via each of the three name sources, and a
    multi-row pending doc (two stakeholders, two different names).

---

## [2.7.69] — 2026-07-15 (Enhance: dashboard token badge, features overview, auto-refreshing review links)

### Added

- **Real/Estimated token badge.** The Token Usage card now shows a
  "Source mix" row — `Real N` / `Est. N` badges tallied from the
  Per-Command Log's `Source` column, so it's obvious at a glance how much
  of a feature's total is measured (Claude Code's own transcript, via
  `sdd token-log`) versus the character-count approximation. Legacy
  `token-usage.md` files from before the `Source` column existed still
  parse correctly — every row in those counts as Estimated.
- **Features Overview table**, shown once a project has 2+ features
  (skipped for one — it would just duplicate the block below it). Lists
  every feature's current pipeline step, task progress, and next action
  in a single table, with each row linking down to that feature's full
  detail block — useful for scanning a multi-feature project without
  scrolling past every full pipeline diagram first.
- **Auto-refreshing Jira/Confluence review links.** The "Check
  Jira/Confluence review links" button is still the only way to make the
  *first* live call for a feature — that opt-in stays intact — but once
  a feature has been checked once, the dashboard now quietly re-checks
  it every 5 minutes so the pills don't go stale without a manual
  re-click. A transient failure during auto-refresh keeps the last
  known-good result instead of flashing an error over data that was fine
  a moment ago.

---

## [2.7.68] — 2026-07-15 (Enhance: dashboard theme toggle + usability)

### Fixed / Added

- **`sdd dashboard` dark/light mode "not working".** The dashboard only
  ever followed the browser's `prefers-color-scheme` media query — some
  browsers/embedded webviews never report that signal reliably, so the
  page could get stuck on one theme regardless of the OS setting.
  - Added an explicit **☀️ Light / 🌙 Dark / 🖥️ Auto** toggle (top right).
    Light/Dark set `data-theme` on `<html>`, which CSS gives higher
    specificity than the `prefers-color-scheme` media query, so a manual
    pick always wins; Auto returns to following the OS/browser signal.
    The choice is saved to `localStorage` and survives reloads.
  - Verified with Playwright across all states: OS=dark + Auto, forced
    Light while OS=dark, forced Dark, back to Auto, OS=light + Auto, and
    reload-persistence — each produced the expected background color.
- **Usability pass**, prompted by a user question about where dashboard
  data comes from:
  - Added a collapsible **"ℹ️ Where this data comes from"** box near the
    top of the page — previously this explanation was one long paragraph
    buried at the bottom, easy to miss. It now clearly distinguishes the
    local-file-only cards (everything, on every 5s poll) from the single
    on-demand live network call (the "Check Jira/Confluence review
    links" button).
  - The "no features yet" empty state now names the actual next command
    (`/specify` or `sdd specify`) instead of just stating the absence.

---

## [2.7.67] — 2026-07-15 (Fix: dashboard Token Usage card broken by the 2.7.66 label rename)

### Fixed

- **`sdd dashboard`'s Token Usage card showed `—` for every total on any
  `token-usage.md` written after 2.7.66.** Found while investigating a
  user question about where dashboard data comes from. Root cause: 2.7.66
  renamed `token-usage-template.md`'s Running Totals labels from `Total
  Est. Input Tokens` etc. to `Total Input Tokens` (dropping the `Est.`
  prefix, since a row can now be Real or Estimated), but two consumers of
  that label text were never updated to match:
  - `status.py`'s `_RUNNING_TOTAL_ROW_RE` regex only matched the old
    `Total Est. X` label, so `_parse_token_usage()` returned `None` for
    input/output/cost on any file using the new labels.
  - `dashboard.py`'s `renderTokenUsage()` JS still hardcoded the old
    `Total Est. X` label text in its rendered HTML.
  - Fixed both to accept and render the current label text, while still
    parsing the old `Total Est. X` label for any `token-usage.md` written
    before 2.7.66 — no existing file needs to be touched.
  - Added a regression test (`test_token_usage_parsed_from_legacy_est_labels`)
    covering the pre-2.7.66 label format so this drift can't recur silently.

---

## [2.7.66] — 2026-07-14 (Add: real Claude Code token usage via `sdd token-log`, instead of the char/4 estimate)

### Added

- **`sdd token-log` — real, measured token usage, not an estimate, when
  running under Claude Code.** Following up on 2.7.65's explanation of
  why the estimate reads low, the user asked if anything more could be
  done. Verified: Claude Code writes a local session transcript
  (`~/.claude/projects/{project}/{session-id}.jsonl`, plus one file per
  spawned subagent under `{session-id}/subagents/`) where every
  assistant turn carries the actual `usage` object the Anthropic API
  returned — real `input_tokens`, `output_tokens`,
  `cache_creation_input_tokens`, `cache_read_input_tokens`.
  - New `sdd/utils/claude_code_transcript.py` locates the current
    session's transcript (and its subagent transcripts) and sums real
    usage per model since a given timestamp.
  - New `sdd token-log --command {name}` CLI command: resolves the
    window to sum (since the last logged row's timestamp, or the whole
    session for the first command logged for a feature), creates
    `token-usage.md` from the template if needed, appends one row per
    model, and updates Running Totals — no agent hand-arithmetic. Exit
    codes distinguish success (`0`), the opt-in gate being off (`2`,
    `token-pricing.yml` missing), and no transcript found (`3`, not
    Claude Code or no session has touched this project yet — the normal
    fall-back case) from an actual error (`1`).
  - This is **Claude Code-only** by nature — the transcript path/format
    is undocumented and reverse-engineered, not a published API, with no
    equivalent under any other AI tool this framework supports. The
    shared `token-usage-logging.md` CLAUDE.md block now tries `sdd
    token-log` first and falls back to the existing char/4 estimate
    whenever it's unavailable or exits non-zero — GitHub Copilot,
    Cursor, Windsurf, and copy-paste "any AI" are completely unaffected,
    still estimate-only.
  - `token-usage-template.md`'s Per-Command Log table gained a `Source`
    column (`Real (Claude Code)` | `Estimated`) so the two measurement
    kinds are never silently compared to each other. A pre-existing
    `token-usage.md` from before this column existed (7-column rows) is
    never rewritten — new rows are only ever appended; old rows are
    parsed generically for the Running Totals sum but left
    byte-for-byte untouched.

---

## [2.7.65] — 2026-07-14 (Fix: /task never pushed to Jira/Confluence; diagram 400s hid the reason; constitution.md pushable; Approver names in Approvals)

### Fixed

- **`/task`'s entire Jira/Confluence sync was broken.** User reported 4
  issues: (1) the placeholder Jira Story created at `/specify-uc` time
  never got finalized/updated, (2) Tasks were never created in Jira or
  linked to their Story, (3) no Confluence page (with Jira link + status)
  was ever created for `tasks.md`, (4) no `/task` document reached
  Confluence at all. Root cause: `task.prompt.md`'s Section 4 only
  generated an offline CSV export and told the user to manually run a
  retired `/jira-push` slash command — it never called the `sdd` CLI at
  all, unlike every other command in this pipeline.
  - `task.prompt.md` (all 5 packs) rewritten: new Section 4 auto-runs
    `sdd jira push --level story` then `--level task` — finalizes
    UC-derived draft Stories in place, creates real Tasks linked to their
    parent Story. New Section 5 pushes `stories.md`/`qa-testcases.md`
    directly to Confluence and routes `tasks.md` through the same
    Submit-for-Review + review-decision discipline every other reviewed
    document uses (`tasks.md` has a real `document_reviews` gate,
    reviewed by the Scrum Master). The old CSV export is kept as an
    explicitly-labelled offline fallback (Section 6).
  - Added missing `stories`/`smoke-tests` `page_map` entries (same
    cross-feature collision risk as an earlier fix) and fixed
    `document_reviews.tasks.confluence_page` ("Task Breakdown")
    diverging from `page_map.tasks` ("Tasks") — they must agree, or
    `review submit`/`apply` and a direct `confluence push` land on two
    different pages for the same document.
- **Diagram attachment 400 errors hid the actual reason.** `sdd review
  check --doc design` failing on a sequence diagram only ever showed a
  bare `400 Client Error: Bad Request for url: ...` — Confluence's real
  error message lives in the response body, which was never surfaced.
  `upload_diagram_attachments` now parses it out. `_render_local_svg`
  also now guards against the renderer returning non-SVG output for
  certain diagrams without raising, which previously reached Confluence
  as malformed bytes and produced an opaque 400.
- **Audited `plan-arch`/`plan-hld`/`plan-adr`/`plan-lld`** for the same
  "document updated locally but never re-published" bug fixed for
  api-spec.md and `/change` in 2.7.63 — confirmed they're already wired
  correctly via the shared `submit-for-review-step`/`review-decision-step`
  blocks; no bug found there.

### Added

- **`constitution.md` can now be pushed to Confluence** — the one
  document that had no way to reach it at all. `resolve_doc_path`,
  `_resolve_page_title`, `resolve_doc_parent_id`, and `_push_doc_page`
  now special-case `"constitution"` as a project-wide page (like a
  living doc, but at `.specify/memory/` rather than `.specify/service/`).
  `specify.prompt.md` (all 5 packs) auto-pushes it right after GATE-1
  finalizes, and again after any later confirmed amendment.
- **Approver name in every document's Approvals table.** Previously only
  the accountable *role* was recorded (`| Role | Status | Date |`) — the
  actual approver was only ever asked about in chat, with nowhere to
  record it. Every template's `## Approvals` table (132 files across
  `_shared/` and all 5 packs) gained an `Approver` column. The
  `review-decision-step` shared block now resolves the approver's name
  from `roles.yml`'s `roles:` map (filled in once per project) first,
  asking the user directly only if that entry is still empty — either
  way the resolved name is written into the document itself.

### Changed

- `token-usage-template.md`'s notes section now explains specifically
  *why* the estimate reads far lower than a provider's real usage/billing
  dashboard (it's scoped only to the SDD documents a command
  intentionally read or wrote — it excludes system prompt, tool
  definitions, and prior conversation turns, which are frequently the
  majority of a turn's real cost) and points to the AI tool's own native
  usage reporting (e.g. Claude Code's `/cost`, the Anthropic Console, or
  GitHub Copilot's usage dashboard) as the authoritative source. There is
  no API a prompt-driven framework can call to get a real number from
  inside a session — this is a platform limitation, not something a
  better formula can fix.

---

## [2.7.64] — 2026-07-14 (Fix: local-svg diagrams render too small in Confluence — set ac:width)

### Fixed

- **User reported that Mermaid diagrams pushed via `diagrams.mode:
  local-svg` showed up very small on the Confluence page, requiring the
  reader to open and zoom.**
  - Root cause: `_render_local_svg()` in `md_to_cf.py` emitted
    `<ac:image>` with no `ac:width` attribute, so Confluence displayed the
    image at the SVG's own intrinsic size — Mermaid's renderer typically
    emits a few hundred pixels.
  - New `DiagramsConfig.local_svg_width` field (default `900`), configured
    via a nested `diagrams.local_svg.width` key in `integrations.yml`,
    matching the existing `mermaid_app`/`plantuml_macro` nested-dict
    convention.
  - `_render_local_svg()` now emits `<ac:image ac:width="{width}">` —
    Confluence scales height to match, preserving aspect ratio.
  - `integrations.yml.example` (all 5 packs) documents the new option in
    place of the old "no options today" placeholder comment.

---

## [2.7.63] — 2026-07-14 (Fix: plan-design's api-spec.md merge and change.prompt.md's full document walk re-sync to Confluence/Jira)

### Fixed

- **Same root cause as 2.7.62's clarify fix, found in two more places
  during a follow-up check the user asked for.**
  - `plan-design.prompt.md` §3 merges endpoint changes into the living
    `.specify/service/api-spec.md` (bump version, Version History,
    regenerate summary) but never re-pushed it to Confluence or notified
    its Jira reviewer — now runs `sdd review apply --doc api-spec`
    immediately after the merge, before `design.md` §3's own summary text.
  - `change.prompt.md`'s Step 5 document walk can UPDATE, RERUN, or
    ANNOTATE **any** of the 14 document types in the pipeline (brd through
    tasks) with the identical local-only pattern — the biggest instance of
    this gap, since `/change` can touch every document type. All three
    action branches (ANNOTATE, UPDATE including 'modify', RERUN) now run
    `sdd review apply --doc {doc-key}` as their last step, for every
    document except `constitution.md` (not resolvable via
    `resolve_doc_path` — it lives outside `.specify/features/`/
    `.specify/service/` and is never pushed). A doc-key convention note
    (filename minus `.md`) was added once near the walk order line.
  - No CLI changes needed — both reuse `sdd review apply` exactly as
    fixed/relaxed in 2.7.62.

---

## [2.7.62] — 2026-07-14 (Fix: clarify.md re-syncs affected documents to Confluence/Jira; sdd review apply no longer requires both integrations; new confluence push --summary)

### Fixed

- **User found that when `/clarify` applies an answer to another spec
  document (brd/srd/use-cases, Step 4), that document was updated locally
  and its `.summary.md` regenerated, but the change never reached
  Confluence or notified that document's own Jira reviewer — only
  `clarify.md` itself was ever kept in sync.**
  - `clarify.prompt.md` (all 5 packs) Step 4 now runs
    `sdd review apply --doc {doc}` for each affected document right after
    bumping its version — this re-pushes the updated content to that
    document's **own** Confluence page and posts a "please re-review"
    comment on its **own** Jira ticket, independent of `clarify.md`'s
    ticket. Skips silently if not configured.
  - `sdd review apply` no longer hard-requires both `jira:` and
    `confluence:` sections (it previously errored out entirely on a
    confluence-only or jira-only project) — it now does whichever half is
    actually configured, matching the rest of the framework's
    confluence-is-independently-optional design.

### Added

- **User also asked to push `.summary.md` files to Confluence under their
  own document, not just the full `.md`.**
  - New `sdd confluence push --doc {doc} --summary` pushes `{doc}.summary.md`
    (if it exists) to a separate page titled "… — Summary", leaving the
    full document's own page untouched.
  - `clarify.prompt.md` Step 5 now auto-runs this for `clarify.summary.md`
    when `confluence:` is configured.
- 10 new tests: confluence-only and jira-only `review apply` paths, and 4
  covering the `--summary` flag (push, full-doc-unaffected, missing-file
  skip, dry-run).

---

## [2.7.61] — 2026-07-14 (Fix: /clarify auto-pushes to Jira/Confluence on generation, auto-pulls on re-run — matching /validate)

### Fixed

- **The 2.7.60 clarify Jira-answers feature only wired the CLI
  (`push-questions`/`pull-answers`) to understand `clarify.md`'s STATUS
  TABLE — it left `clarify.prompt.md` requiring the user to explicitly ask
  for the Jira push every time, unlike `validate.prompt.md`'s §3a, which
  pushes automatically the moment it detects open items and pulls
  automatically at the start of every re-run.**
  - `clarify.prompt.md` (all 5 packs) now: at the top of "Your Task", if
    `clarify.md` already exists, runs `pull-answers` first and skips
    straight to "After Human Fills Answers" if everything is now resolved;
    and right after saving a freshly generated `clarify.md`, auto-runs
    `sdd review push-questions --doc clarify` when
    `document_reviews.clarify` is configured, before presenting the report.
  - "Accepted reply forms" simplified accordingly — Jira/Confluence
    answers are now just another accepted reply form (pulled in
    automatically), not a separate manual opt-in step.

---

## [2.7.60] — 2026-07-14 (Feature: clarify.md's own open items can be answered via Jira/Confluence, same as validate.md)

### Added

- **User pointed out that `/validate`'s open questions could already be
  answered via Jira (`push-questions`/`pull-answers`), but `/clarify`'s
  8-item report (AMB/GAP/CON/ASM/OQ/R) had no such path — `push-questions`
  silently found nothing to push, since it only ever recognized the
  `{doc}:NC-{NNN}` bracketed-marker scheme used by brd/srd/use-cases/
  validate, not clarify.md's own STATUS TABLE.**
  - Added a parallel parse/patch path scoped to `--doc clarify`:
    `_parse_clarify_open_items` reads OPEN STATUS TABLE rows (posting each
    item's full section — Found in / Option A / Option B / etc — as the
    Jira question text), `_parse_clarify_answers` reads
    `clarify:AMB-001: <answer>`-style replies, and `_patch_clarify_item`
    fills the item's `{FILL...}` placeholder and flips its STATUS TABLE
    row to the terminal status for its type: `RESOLVED` for AMB/GAP/R,
    `CORRECTED` for CON, `DECIDED` for OQ, and `CONFIRMED`/`CORRECTED` for
    ASM depending on whether the answer starts with "yes".
  - `sdd review push-questions`/`pull-answers` branch on `doc == "clarify"`
    for parsing/patching only — Jira ticket creation, idempotency-label
    reuse (same ticket `sdd review submit` will later find), and the
    Confluence re-push are unchanged and fully shared with the existing
    NC-NNN path.
  - `clarify.prompt.md` (all 5 packs) documents this under "Accepted reply
    forms"; `review-gates.md`'s shared block gained a matching paragraph,
    synced into every pack's `CLAUDE.md`.
- 16 new tests: STATUS TABLE parsing (including skipping already-resolved
  rows), answer-line parsing, placeholder fill + per-type status flip (all
  5 terminal statuses, including both ASM branches), and end-to-end
  push-questions/pull-answers CLI coverage including the Confluence
  re-push.

---

## [2.7.59] — 2026-07-14 (Feature: Confluence pages now show a live Jira link + status banner; page_map covers every generated doc type)

### Added

- **User asked why a document pushed to Jira for review didn't also get its
  Confluence page updated with the Jira link and status, so a reviewer could
  check progress without leaving Confluence — the two pushes previously
  happened in unrelated code paths, so the Confluence page only ever
  mirrored the `.md` content, never the Jira ticket's state.**
  - `sdd review submit` / `check` / `apply` now prepend a small info /
    success / warning panel to the top of the document's Confluence page:
    the Jira ticket key (linked), its live status (Pending review / Needs
    Revision / Approved), and the assigned reviewer role.
  - The banner is refreshed every time the CLI touches that document's
    review state — `submit` re-pushes once the ticket exists (the first
    push, before the ticket exists, can't include it yet), `check`
    refreshes it to match whatever status was just polled, and `apply`
    picks it up automatically as part of its existing re-push.
  - Only applies to doc keys with a `document_reviews` entry (i.e. actually
    under Jira review) — a doc pushed via the `page_map` fallback alone (no
    Jira gate configured for it) still gets a plain page, unchanged.
- **User also asked for a Confluence page for "QA test case etc — whatever
  there in local md file" — not every generated document had a `page_map`
  entry at all.**
  - `integrations.yml.example`'s `page_map` now also covers `qa-testcases`,
    `tasks`, `checklist`, and the 4 living/service-level docs (`data-model`,
    `security-design`, `api-spec`, `component-library`) — `sdd confluence
    push --doc <key>` (or the auto-push on approval) now works for all of
    them, not just the phase-gated documents.
  - These new entries are `page_map`-only (no `document_reviews`) unless a
    team adds their own reviewer config — a Confluence page doesn't require
    a Jira review gate.
- 6 new tests covering the banner HTML per status, `submit` stamping a
  Pending banner once the ticket exists, `check` refreshing an existing
  page to Approved, and the `page_map`-fallback path (no Jira gate) omitting
  the banner entirely.

---

## [2.7.58] — 2026-07-13 (Feature: analyze.md and clarify.md can now go through the same Jira/Confluence review gate as brd/srd/etc)

### Added

- **User asked why `/analyze` and `/clarify` never got pushed to Confluence
  or tracked in Jira the way `/validate` does — by design they were
  chat-only working documents, but nothing in `resolve_doc_path`/
  `review_submit`/`review_approve` actually required that; every doc key
  is handled generically.**
  - Added `document_reviews.validate` / `.analyze` / `.clarify` entries to
    `integrations.yml.example`, in a new `validate` phase
    (Validate → Analyze → Clarify, `sequence: 1/2/3`) — enforced by the
    same predecessor-sequence gate every other phase already uses, plus
    matching `page_map` titles.
  - `analyze.prompt.md` and `clarify.prompt.md` (all 5 packs) gained the
    same **Stakeholder Review and Approval** Step B/C section
    `validate.prompt.md` already has: `sdd review submit`/`check`/
    `approve`, the same approval-signal handling, and the same guardrail
    against inferring per-section findings as individually confirmed by
    a document-level approval (mirroring the 2.7.57 fix).
  - Each of `validate`/`analyze`/`clarify` is **optional individually** —
    add only the ones you want routed through Jira/Confluence; the rest
    stay chat-only, per `review-gates.md`.
  - Fixed `clarify-template.md`'s header, which said `Status: OPEN`
    instead of `Status: Draft` — `_mark_md_approved`'s regex only
    recognizes `Draft`/`Proposed`, so the approval flip would have
    silently never updated the header for `clarify.md` without this fix.
  - 4 new tests: generic `submit` works for `analyze`/`clarify` doc keys,
    the validate-phase sequence gate blocks `analyze` until `validate` is
    approved, and the `clarify.md` header fix is confirmed to make the
    approval flow work end-to-end.
  - No manifest schema changes.

---

## [2.7.57] — 2026-07-13 (Guardrail: validate.md approval no longer auto-checks §1–§4 per-item confirmation checkboxes)

### Changed

- **User-reported (from a live project's `/analyze` run):** a prior agent
  session, chasing `analyze.prompt.md`'s verify gate's literal
  `"VALIDATE complete"` string, bulk-checked every unchecked box in
  `validate.md`'s §1 (Reviewer Confirms), §2 (BA/PO Confirms), §3
  (assumption Correct?), §3a (UC Business Scenario Correct?), and §4
  (Scope Confirmation) — inferring itemized per-line business sign-off
  purely from the document's Jira ticket having been closed after a Q&A
  comment thread, which is not the same as a named reviewer actually
  addressing that specific item.
  - `validate.prompt.md`'s own Step C only ever specified updating the
    header (`Status: Draft → Approved`) and the §5 Approvals table — the
    §1–§4 bulk-check was never something the prompt instructed.
  - Tightened Step C across all 5 packs to explicitly forbid inferring
    §1–§4 item-level confirmations from a document-level approval signal
    (a blanket "approved" reply, a Jira status flip, or a comment thread
    that only answered `[NEEDS CLARIFICATION]` items is not itemized
    evidence), and to say what to do instead: leave the box `[ ]` with a
    note ("Approved as a whole document; items in §1–§4 were not
    itemized during review"), or check it only when pointing to the
    actual reviewer statement that confirmed that exact item.
  - Matters most for regulated/financial-transfer features, where
    §1–§4's checkboxes exist to be a traceable, defensible audit trail
    of actual line-item business review — not a formality rubber-stamped
    to satisfy a downstream gate's string match.
  - `validate.prompt.md` is not a shared/blocks file — edited
    individually in all 5 packs with identical wording.
  - No manifest schema changes.

---

## [2.7.56] — 2026-07-13 (Fix: sdd review pull-answers never refreshed BRD/SRD/UC's Confluence pages after patching them)

### Fixed

- **User-reported: after answering every open question and confirming
  `pull-answers` correctly patched `brd.md`/`srd.md`/`use-cases.md` on
  disk, those documents' Confluence pages still showed the old
  `[NEEDS CLARIFICATION]` markers.**
  - Root cause: `pull-answers` only ever pushed `validate.md`'s own
    Confluence page (via `push-questions`) — the underlying documents it
    patches were never re-pushed, even though they already had their own
    Confluence pages from their original `/specify-brd` →
    `sdd review submit` flow.
  - `review_pull_answers` now tracks the on-disk path of every document it
    successfully patches, and after the patch loop, re-pushes each one's
    Confluence page via the same `_push_doc_page()` helper
    `sdd review approve` already uses. Best-effort per document — one
    page's failure never blocks the others or the patching that already
    succeeded. Only runs when `confluence:` is configured; silently
    skipped otherwise.
  - 1 new test confirming both patched docs' Confluence pages are
    created/updated with the expected page-map titles.
  - No manifest schema changes.

---

## [2.7.55] — 2026-07-13 (Fix: sdd review pull-answers never patched markers in projects that predate NEEDS CLARIFICATION-NNN numbering)

### Fixed

- **User-reported: after answering all 7 open questions on a `push-questions`
  ticket (and confirming the 2.7.54 multi-line fix worked correctly),
  `sdd review pull-answers` still reported 0 items patched every time.**
  - Diagnosed via a sequence of live checks against the user's real project:
    the ADF text extraction, working directory, and comment-answer parsing
    were each confirmed correct in isolation, narrowing the failure to
    `_patch_marker` itself — every call returned `False`.
  - Root cause: `validate.md`'s own §3a-BLOCKING scan only **displays**
    synthesized `{doc}:NC-{NNN}` IDs for legacy unnumbered
    `[NEEDS CLARIFICATION: ...]` markers (order of appearance) — it never
    writes those numbers back into the source document, since scanning
    isn't editing. Confirmed via a live
    `grep -o "NEEDS CLARIFICATION-[0-9]*" brd.md` returning zero matches
    despite the displayed table citing `brd:NC-001` etc. `_patch_marker`'s
    exact-string search for the numbered form therefore never found
    anything to replace, in any project generated before the
    `NEEDS CLARIFICATION-NNN` numbering feature (2.7.53) shipped.
  - New `_number_legacy_markers()`: retroactively numbers any unnumbered
    `[NEEDS CLARIFICATION: ...]` marker in a source doc as
    `[NEEDS CLARIFICATION-NNN: ...]`, in order of appearance, continuing
    after the highest existing number so a doc with a mix of both forms
    doesn't collide. Wired into `review_pull_answers` to run once per
    referenced doc before any patch is attempted.
  - Secondary fix: the AI generating `validate.md`'s Locations column has,
    in practice, abbreviated `use-cases.md` as `uc` (`resolve_doc_path`'s
    real key is `use-cases`, matching the filename stem). New
    `_normalize_doc_key()` maps known abbreviations before every
    `resolve_doc_path` call sourced from a parsed location ID.
    `validate.prompt.md` (all 5 packs) tightened to require an exact
    filename stem going forward.
  - 11 new tests: legacy-marker numbering (order, zero-padding,
    mixed-state continuation, already-numbered untouched, missing file),
    doc-key alias normalization, and an end-to-end reproduction of the
    exact reported bug.
  - No manifest schema changes.

---

## [2.7.54] — 2026-07-13 (Fix: multi-line Jira replies to sdd review pull-answers were collapsed into one line)

### Fixed

- **User-reported: a reviewer answered all 7 open questions on a
  `push-questions` ticket, one item per line as instructed, but
  `sdd review pull-answers` reported "no new replies" every time.**
  - Root cause: `_extract_text()` joined every text run in the whole ADF
    comment body with a single space, with no regard for paragraph
    boundaries. Jira's rich-text comment editor stores each line a user
    types as a **separate paragraph node** in the ADF tree, not one
    paragraph with embedded newlines — so a real multi-line reply
    collapsed into one run-on line, and the per-line `^...$` answer
    parser (anchored on actual `\n` characters) then only ever found the
    first item, with the rest of the comment swallowed into its answer.
  - `_extract_text()` rewritten to walk ADF block-level nodes
    (`paragraph`, `heading`, `codeBlock`, `blockquote`, `listItem`) and
    join *those* with newlines, while text runs within a single block
    are concatenated directly (also fixes a smaller pre-existing issue:
    formatting-split text runs within one sentence previously got a
    spurious extra space). `hardBreak` nodes now also produce a newline.
  - Also used by `review_check`'s printed reviewer-comment display and
    the dashboard's Jira-comment surfacing — both benefit from the same
    fix, previously showing run-on multi-line Jira comments as one
    wrapped line.
  - 5 new tests: separate-paragraphs-become-separate-lines,
    plain-string-body unchanged, `hardBreak` handling, and an end-to-end
    reproduction of the exact reported bug (7 distinct paragraph
    answers, all 7 must parse).
  - No manifest schema changes.

---

## [2.7.53] — 2026-07-13 (Feature: blocked documents can collect answers via Jira/Confluence)

### Added

- **User-requested: a document like `validate.md` can be blocked before
  it's ever submitted for formal review** — `brd.md`/`use-cases.md`/
  `srd.md` still have unresolved `[NEEDS CLARIFICATION]` markers, so
  `/validate` refuses to proceed past its own §3a gate. There was
  previously no way to route those specific open questions through
  Jira/Confluence the way an already-submitted document's reviewer
  comments already could.
  - `[NEEDS CLARIFICATION]` markers are now numbered locally per
    document — `[NEEDS CLARIFICATION-NNN: {question}]` — matching the
    `[ASSUMPTION-NNN]` convention already in use. Every marker now has a
    stable, doc-qualified ID (`{doc}:NC-{NNN}`, e.g. `brd:NC-002`) a
    reviewer's answer can cite exactly, instead of matching against
    paraphrased question text.
  - New `sdd review push-questions --doc {doc}`: parses a blocked
    document's `| ID | Locations | Question |` table (see
    `validate.prompt.md`'s §3a-BLOCKING) and creates/updates one Jira
    ticket + Confluence page. Uses the *same* idempotency label
    `sdd review submit` looks for, so once every question is answered
    and the document unblocks, `sdd review submit` finds and evolves
    this same ticket in place (posting a transition comment) instead of
    creating a second one.
  - New `sdd review pull-answers --doc {doc}`: fetches comments from
    that ticket, matches lines like `brd:NC-002: <answer>` against the
    open items, and patches each answered `[NEEDS CLARIFICATION-NNN]`
    marker directly into its source document — bumping that document's
    `Version:` header and appending a `## Version History` row. A
    question asked in more than one document (a `Locations` column
    listing more than one ID) gets the same answer applied to every one
    of them from a single reviewer reply.
  - `validate.prompt.md` (all 5 packs — not a shared file) updated:
    §3a-BLOCKING now calls `pull-answers` before re-scanning and
    `push-questions` after detecting a block, and its table cites
    doc-qualified marker IDs instead of an ad-hoc numbering scheme.
  - `specify-brd`/`specify-uc`/`specify-srd`/`specify-doc.prompt.md`
    (shared) and the `submit-for-review-step` block updated for the new
    marker numbering and ID-based comment matching.
  - 23 new tests in `test_review_helpers.py`: table/answer parsing,
    marker patching (version bump + Version History, multi-location
    propagation, legacy/missing-marker tolerance), and the
    `push-questions` → `submit` same-ticket transition end-to-end.
  - No manifest schema changes.

---

## [2.7.52] — 2026-07-13 (Fix: dashboard "Next:" text could contradict the pipeline diagram)

### Fixed

- **User-reported: the dashboard's Full Pipeline diagram marked
  `validate` as the current step (● current), but the "Next:" text still
  said "Run `/checklist` to generate the Spec Quality Checklist".**
  `checklist` is optional at `pilot` scope, and the project genuinely
  skipped it while `validate.md` already existed and was awaiting
  review.
  - Root cause: `_step_state()` never consults a step's `optional` flag
    — an optional step whose doc file doesn't exist on disk always
    reports state `"upcoming"`, indistinguishable from "not reached
    yet." `build_pipeline()`'s main loop picked the first non-`"done"`
    step in list order as `next_action`, and `checklist` sits before
    `validate` in `PIPELINE_DOCS`, so it always won — even though each
    step's own rendered state (○ upcoming / ● current) was already
    correct in isolation.
  - Fix: new `_later_doc_step_exists()` helper in `status.py` —  when a
    later non-skipped doc-kind step already exists on disk, an earlier
    `optional` step still sitting at `"upcoming"` is treated as
    consciously bypassed and is skipped when choosing
    `next_action`/`next_step_id`/`next_persona`. The per-step `resolved`
    states that render the flow diagram itself are untouched.
  - 2 new regression tests in `test_status.py`: the bypassed-optional-
    step case from this report, and a sanity check that a genuinely
    not-yet-reached optional step is still picked as `next_action`
    normally.
  - No manifest schema changes.

---

## [2.7.51] — 2026-07-13 (Feature: dashboard Jira review pill gets a local, instant fallback)

### Added

- **User-reported: the dashboard's Confluence pill next to a document
  always showed up, but the Jira review-gate pill only appeared after
  clicking the live "Check Jira/Confluence review links" button.** This
  turned out to be a real asymmetry, not a config issue: `sdd review
  submit` creates the review-gate Jira ticket but never wrote its key
  anywhere locally — unlike Confluence, whose page ID is recorded on
  every push.
  - New `.specify/.jira-review-links.json`, written by `review.py`'s
    `_record_review_link()` — called from both `review_submit` (after
    the review Story is created/updated) and `review_apply` (when it
    finds the existing ticket to notify). Same not-feature-scoped
    limitation as `.confluence-drafts.json` by design, to keep the two
    files symmetric.
  - `status.py`'s new `_local_review_links()` reads it the same way
    `_local_confluence_links()` reads the Confluence file — no network
    call, wired into `build_feature_status()`'s `local_links.jira_review`.
  - `dashboard.py` threads `local.jira_review` through `renderFeature` →
    `renderDocs` → `renderDocRow`, used as a fallback (`reviewJira ||
    localJira`) the same way the Confluence pill already falls back to
    its local cache — the live check remains what refreshes
    status/comments and re-verifies a possibly-stale local pill.
  - 13 new/updated tests: `_record_review_link` round-trip
    (`test_review_helpers.py`), `review_submit`/`review_apply` writing
    the link end-to-end, 6 `status.py` reader tests plus a real-writer
    round-trip lock, and a `dashboard.py` source-level guard for the new
    frontend wiring.
  - Also corrected two now-stale docstrings that predated this fix:
    `_local_confluence_links()` claimed `sdd review submit` pages were
    "never cached locally the same way" — they already were, via
    `_record_confluence_draft_link()`, well before this session.

## [2.7.50] — 2026-07-13 (Fix: Confluence diagram attachment uploads rejected with HTTP 415)

### Fixed

- **User-reported (via their own diagnosis of an editable install): after
  fixing an unrelated `integrations.yml` indentation bug that was
  silently disabling `diagrams.mode` entirely, the diagram still didn't
  render — this time with a real Confluence API error:
  `diagram-1.svg — 415 Unsupported Media Type`.**
  - Root cause: `build_session()` sets a blanket `Content-Type:
    application/json` on the shared `requests.Session` for every other
    call the Confluence client makes. `upload_attachment()`'s multipart
    file POST (`files=...`) never overrode it, and `requests` only
    computes its own `multipart/form-data; boundary=...` header when no
    `Content-Type` is already present on the request — so Confluence
    received multipart bytes mislabeled as `application/json` and
    rejected the upload with 415, while the page content itself still
    saved fine (only the image attachment failed — silently, per the
    code's own defensive design, since a failed attachment upload must
    never fail the whole document push).
  - `confluence_client.py`'s `upload_attachment()` now explicitly passes
    `Content-Type: None` in the per-request headers dict — `requests`'
    documented way to remove a session-level header for one request —
    letting it compute the correct multipart boundary header itself.
    Verified against a real `requests.Session` (not just a mock) that
    this produces the expected `multipart/form-data; boundary=...`
    header.
  - 1 new test in `test_confluence_client.py` asserting `Content-Type`
    is explicitly unset in the request headers for this call.

## [2.7.49] — 2026-07-13 (Fix: silent Confluence diagram-render failures now print a warning)

### Fixed

- **User-reported: set `diagrams.mode: local-svg` in `integrations.yml`,
  re-pushed a Use Cases page containing a Mermaid relationship diagram,
  and the diagram still showed as plain text instead of an image — with
  no error or warning anywhere to explain why.**
  - Root cause: `md_to_cf.py`'s `_render_local_svg()` caught every
    renderer exception — including the most likely real-world cause,
    `pip install "sddflow[diagrams]"` never having been run so the
    optional `mmdr` package isn't installed — and silently discarded the
    reason, falling back to a plain code block. A real, fixable failure
    was indistinguishable from `diagrams.mode` simply not being
    configured at all (which is expected, documented default behavior).
  - `md_to_storage()`'s return type changed (again) from
    `tuple[str, list[Attachment]]` to
    `tuple[str, list[Attachment], list[str]]` — the third element is one
    human-readable warning per diagram fence whose *configured* mode
    failed to render. Never populated when `diagrams.mode` is `"none"`,
    since that's not a failure.
  - Same silent-fallback gap fixed for `mermaid-app`/`plantuml-macro`
    modes selected with no `macro_name` configured — previously also
    indistinguishable from an unconfigured mode.
  - All 6 call sites (`sdd confluence push`, `sdd confluence draft`,
    `sdd review submit`, `sdd review apply`, `review.py`'s internal
    `_push_doc_page`, `sdd cr submit`) now print each warning in yellow
    right after a successful page push, so a future push immediately
    names the actual problem (e.g. "Diagram failed to render (...) —
    shown as plain code instead", or the exact `pip install` command
    when `mmdr` isn't installed) instead of leaving silence to guess from.
  - 9 new/updated tests in `test_md_to_cf.py`: missing-`macro_name`
    warnings for both `mermaid-app` and `plantuml-macro`, a
    renderer-exception warning naming the actual error, a dedicated
    `MermaidRendererNotInstalled` test asserting the warning names the
    exact install fix, and confirming `mode: none` / successful renders
    never produce warnings.

## [2.7.48] — 2026-07-13 (Feature: dashboard surfaces `sdd review check --doc` status/comments)

### Added

- **User-requested: a dashboard equivalent of `sdd review check --doc`**
  to check review status and reviewer comments without leaving the
  browser. The dashboard already had a live, on-demand, button-triggered
  Jira/Confluence lookup (`"🔄 Check Jira/Confluence review links"` →
  `_fetch_review_links()`) architecturally separate from the passive,
  network-free 5-second `/api/status` poll — this extends that existing
  path rather than adding a new one.
  - `_fetch_review_links()` now calls `review.py`'s own
    `_get_review_status()` for each document, reusing the exact
    `APPROVED` / `NEEDS_REVISION` / `PENDING` classification `sdd review
    check` uses instead of re-deriving it, and fetches reviewer comments
    via `JiraClient.get_comments()`.
  - Frontend: a color-coded review-status badge (new `'review'` kind on
    the existing `badge()` renderer) appears next to each document's Jira
    pill; Jira review comments are shown in the existing per-document
    comments panel (💬), labeled separately from local dashboard
    comments so the two sources are never confused.
  - Same requirement as `sdd review check` itself — only works where
    `document_reviews` is configured in `integrations.yml`; no new gap.
  - 4 new tests in `test_dashboard.py`: real classification wiring for
    both `NEEDS_REVISION` (comment present, no approved status/keyword)
    and `APPROVED` (status in `approved_statuses`), plus two source-level
    page guards for the new badge/comments markup.

## [2.7.47] — 2026-07-13 (Feature: cross-project Jira parent-link fallback)

### Added

- **User-reported (via follow-up diagnosis): when `project_keys` routes a
  level to a different Jira project than its parent** (e.g. `story`/`task`
  under `TEMPT`, the Epic under `TEMP`) — a genuine Jira platform
  limitation, not an SDD bug — the child issue was still created, but the
  parent-child link silently never appeared in Jira; the CLI only printed
  a warning with no actual fallback.
  - New `JiraClient.link_issues()` creates a plain **"Relates" issue
    link** (Jira's default cross-issue link type, present on every
    instance) between child and parent — unlike the `parent`/Epic-Link
    field, issue links are **not** scoped to a single project.
  - `_warn_parent_link_failed()` (used by all 4 `sdd jira push` call
    sites — story, uc-draft, task, chg — and by `sdd review submit`'s
    review-ticket linking) now automatically attempts this fallback the
    moment a true parent-child link fails, and reports which kind of link
    actually landed: `"Linked with a 'Relates' issue link instead"` when
    the fallback worked, or the original troubleshooting message (now
    also noting the fallback was attempted) if even that failed.
  - Documented in `README.md` and `integrations.yml.example`'s
    `project_keys` cross-project caveat.
  - 8 new tests: `TestLinkIssues` in `test_jira_client.py` (endpoint,
    payload shape, default/custom link type, HTTP-error propagation) and
    a new `test_jira_parent_link_fallback.py` covering
    `_warn_parent_link_failed`'s fallback-attempted / fallback-succeeded /
    fallback-also-failed paths and that the original error is always
    surfaced.

## [2.7.46] — 2026-07-13 (Fix: review-submit failure silently skipped Confluence + Jira Epic refresh)

### Fixed

- **User-reported: when `sdd review submit --doc brd` failed because
  `document_reviews` wasn't configured for `brd` in `integrations.yml`
  (a separate config section from `jira:`/`confluence:` — needs a
  reviewer assigned per doc), the agent silently fell all the way back to
  plain chat-mode review — skipping the Confluence draft push entirely
  even though `confluence:` *was* configured, and never refreshing the
  Jira Epic with the BRD's real Business Objectives** (the Epic refresh
  happens as a side effect of `sdd review submit` succeeding — it never
  ran). Both silently missing was confusing: Jira/Confluence had worked
  earlier in the same session (constitution's Epic-bootstrap step), so it
  looked broken rather than just falling through a documented-but-narrow
  edge case.
  - `submit-for-review-step.md` (the shared block used by all 9
    doc-generating commands — BRD, Use Cases, SRD, extended docs, and all
    `/plan-*` commands): a failed `sdd review submit` now falls through to
    the "Confluence-only" branch (push a draft) instead of skipping
    Confluence entirely, and only drops to bare chat mode if `confluence:`
    itself is absent too.
  - `specify-brd.prompt.md` (all 5 packs) Step D: when `jira:` is
    configured but the Epic wasn't refreshed by a successful review
    submit, now explicitly runs `sdd jira push --level epic` to push the
    real Business Objectives — this only needs `jira:` configured, not
    `document_reviews`.
  - Hit the same maintenance gotcha as the 2.7.40 fix: `submit-for-
    review-step.md` is embedded in 9 prompt files that are ALSO full-file
    synced from `_shared/full/` — editing the block and running
    `sync-blocks.sh` without first patching `_shared/full/`'s own stale
    copies reverted the change back on the very next sync. Fixed by
    patching all 9 `_shared/full/.github/prompts/*.prompt.md` copies
    (plus the `specify-brd.prompt.md`-specific Step D edit) before
    re-running `sync-blocks.sh`; verified 0 diffs on two subsequent runs.
- **Also clarified (not a bug, but worth documenting)**: `constitution.md`
  is never synced to Confluence at all — it has no `page_map` entry, by
  design (it's an internal project-config artifact, not a
  stakeholder-facing spec doc). And hand-editing any `.md` file locally
  never auto-pushes to Confluence on its own — sync only happens on an
  explicit command (`sdd review submit`, `sdd confluence draft/push`, or
  as a side effect of `sdd review approve --local`). There is no
  filesystem watcher; this is a manual/command-triggered sync model by
  design, not a bug.

## [2.7.45] — 2026-07-13 (Fix: dashboard crashed reading Jira export keys)

### Fixed

- **User-reported: `sdd dashboard` crashed every poll (`AttributeError:
  'str' object has no attribute 'get'`) once a feature had a Jira
  progressive export (`docs/jira/{feature}/keys.yml`).** `status.py`'s
  `_local_jira_links()` assumed `epic` was a dict and `stories`/`tasks`
  were lists of dicts, each with a `jira_key` field — but `jira.py`'s
  actual writer (`_save_keys_summary()`) writes `epic` as a plain string
  and `stories`/`tasks` as flat `{sdd_id: jira_key}` dicts. This schema
  drifted apart when `jira.py` was rewritten (v2.7.x Phase 1) without the
  reader being updated to match, and the existing unit tests were written
  against the reader's (wrong) assumption rather than the writer's real
  output, so nothing caught it. `_local_jira_links()` now parses both the
  real (string/flat-dict) shape and the old assumed
  (dict-with-jira_key/list-of-dicts) shape defensively, with a new
  `_jira_key_from()` helper and a round-trip test that calls the real
  writer and reader together so this can't silently drift apart again.
- **Hardening**: a malformed file anywhere under `.specify/` or
  `docs/jira/` no longer takes the whole dashboard down. `/api/status`
  now catches any exception and returns a JSON `{"error": ...}` with
  status 500 instead of a bare connection reset; the frontend's poll loop
  catches fetch/parse failures and shows a visible "Couldn't load
  status… Retrying in 5s" banner instead of silently freezing on stale
  data forever.

## [2.7.44] — 2026-07-13 (Fix: dashboard showed Constitution done before /specify ran)

### Fixed

- **User-reported: the dashboard's Full Pipeline flow showed "✓ Constitution
  (Part 2)" as done on a brand-new project, before `/specify` had ever been
  run.** `constitution.md` is scaffolded by `sdd init` for *every* project —
  Part 1 boilerplate plus a Part 2 template full of `{extracted from
  context}` / `{derived}` / `{date}` placeholders — so `status.py`'s old
  check (does the file exist on disk?) was true immediately after
  scaffolding, well before Part 2 had actually been filled in.
  `_constitution_status()` now also checks whether Part 2 still contains
  unresolved `{...}` template placeholders; only once they're gone (i.e.
  `/specify` has actually run) is Part 2 reported as generated. The
  "Constitution (Part 2)" and "GATE-1" pipeline steps, and the dashboard's
  "Constitution — GATE-1" detail card (new "Part 2 generated" row), now
  correctly show upcoming/○ until `/specify` runs.
  Verified against all 5 packs' real shipped `constitution.md` templates
  (including sdd-micro) plus a live `build_project_status()` run against a
  freshly-scaffolded project directory.

## [2.7.43] — 2026-07-13 (Fix: redundant project-type prompt on scaffold)

### Fixed

- **`sdd init` no longer asks for project type a second time when you've
  already chosen a type-dedicated pack** (`sdd-backend-service`,
  `sdd-frontend-spa`, `sdd-mobile`, `sdd-fullstack`). Previously, choosing
  one of these packs from "Choose from all packs…" still triggered a
  second `detect_project_type()` call and — since detection on a
  freshly-scaffolded directory usually fails — a confusing `Project type:`
  select listing all 10 types (including irrelevant ones like `mobile`
  for a project you just said was `sdd-backend-service`). The pack choice
  now pins `project_type` directly (e.g. `sdd-backend-service` →
  `backend-service`) with no further prompt. `sdd-universal` is
  unaffected — it genuinely branches its tech-stack tables on
  `project_type`, so its detect/select flow is unchanged.
  Fixed in both `cli-python` (`sdd init`) and the Node `cli` (`sdd init`).

## [2.7.42] — 2026-07-13 (Docs consistency + test coverage)

### Fixed

- Removed the dangling `CHANGELOG.md` reference from the "Read Next" table
  in all 5 packs' `README.md` — no such file is ever scaffolded into a
  user's project, so the row pointed nowhere.
- Propagated the `workflow_mode` (github/local) wording fix to the 3 packs
  that had lagged behind `sdd-universal`/`sdd-backend-service`
  (`sdd-frontend-spa`, `sdd-mobile`, `sdd-fullstack`): `release-template.md`,
  `CLAUDE.md` (PR Contract + VALIDATE/RELEASE gate wording),
  `implement.prompt.md` ("After Writing" branch), `release.prompt.md`
  (Verify Gate), `PROMPT-GUIDE.md`, `quality-gate.yml` (starter-workflow
  comment), and `constitution.md` (PR Rules table) — these 3 packs already
  documented `workflow_mode: local` as supported in `HOW-TO-USE.md`, but
  the actual command prompts never branched on it, so local mode silently
  behaved like github mode. It now works end-to-end in all 5 packs.

### Added

- **Virtual Team — Address by Name** section added to `HOW-TO-USE.md` in
  all 5 packs (previously only documented in each pack's `CLAUDE.md`, not
  in the primary end-user-facing guide).
- **`/taskstoissues`** documented under "Optional and Utility Commands" in
  `HOW-TO-USE.md` in all 5 packs (command existed and worked; it just
  wasn't listed anywhere a user would find it).
- Real-socket HTTP tests for `sdd dashboard`'s request handler
  (`tests/test_dashboard_http.py`, 12 tests) — spins up the actual
  `ThreadingHTTPServer` on an ephemeral port and drives it with real
  requests, covering routes, status codes, and input validation that the
  existing helper-level tests didn't reach.
- Unit tests for `sdd init` (`tests/test_init.py`, 6 tests) — fill mode,
  scaffold mode, sdd-micro detection, name validation, context-file
  no-clobber behavior.
- Unit tests for `sdd pr` (`tests/test_pr.py`, 14 tests) — `create`,
  `comments`, `reply`, `resolve`, `request-review`, covering task lookup,
  branch/PR-body construction, and graceful degradation when a git host
  doesn't support an action.

## [2.7.41] — 2026-07-13 (Feature: local-mode dashboard comment discovery)

### Added

- **`sdd review check`/`sdd review apply` now work in pure local mode** (no
  `jira:` section configured at all). Previously a dashboard-left comment in
  that setup landed only in `.specify/.dashboard-comments.json`, with no way
  for the agent to discover it except the user manually relaying it in
  chat — `sdd review check` always reported "not submitted," and
  `sdd review apply` hard-required both `jira:` and `confluence:` just to
  run.
- `sdd review check` now falls back to reading unacknowledged dashboard
  comments when Jira isn't configured, printing them and exiting `1` —
  same shape as the Jira NEEDS REVISION path, so the agent's existing
  "run `sdd review check`, follow the exit code" workflow needs no changes
  to pick this up.
- `sdd review apply` now acknowledges those comments (instead of erroring)
  when neither `jira:` nor `confluence:` is configured, so
  `sdd review check` stops repeating them on the next poll.
- New **`sdd review comments --doc {doc} [--ack]`** command for
  explicit/manual use outside the check/apply cycle — lists unacknowledged
  comments, or marks them all addressed with `--ack`.
- New `.specify/.dashboard-comments-ack.json` tracks, per feature/doc, the
  timestamp cutoff below which comments are considered handled — the
  comments file itself is an append-only log with no per-entry "handled"
  flag.
- When Jira *is* configured, dashboard comments already mirror to the doc's
  Jira review ticket (unchanged) — this fallback only ever triggers when
  there's no Jira to mirror to.
- 14 new tests; verified end-to-end against a live `sdd dashboard` instance
  and the real `sdd` CLI (not just pytest mocks) — posted a comment through
  the dashboard's actual API, confirmed `sdd review check` picked it up,
  and confirmed `sdd review apply` correctly silenced it afterward.

---

## [2.7.40] — 2026-07-13 (Fix: review-driven document edits now bump Version + log Version History)

### Fixed

- **After addressing reviewer comments, the document's `Version:` header
  now actually updates.** Reported: whether feedback came via Jira, local
  mode, or the dashboard, updating a document to address it left the
  `Version:` header frozen at 1.0 forever with no record of what changed
  or when — `/change` (post-approval Change Requests) already had this
  discipline, but the earlier pre-approval review cycle never did.
- The shared `review-decision-step.md` instruction block (embedded in
  every review-gated command — BRD, Use Cases, SRD, extended docs, Design/
  Arch/HLD/ADR, LLD) now has an explicit **Revision Logging** rule: any
  content edit made in response to reviewer feedback — a Jira comment via
  `sdd review check`, a dashboard comment (which mirrors to the Jira
  ticket when Jira is configured), or feedback relayed in chat —
  increments the document's version and appends a row to its
  `## Version History` table. A pure approval with no content change does
  not bump the version.
- Also fixed a smaller, related bug: the approval-logging step's Version
  History row template hardcoded `| 1.0 | ... |` literally instead of
  referencing the document's actual current version — wrong for any doc
  past its first revision. Fixed in both `review-decision-step.md` and
  `validate.prompt.md`'s own inline copy of the same approval step.
- `review-gates.md` (CLAUDE.md's Document Review Gates summary) gained a
  one-line pointer to this rule for discoverability at session-startup
  read time.
- Prompt/template content only — no CLI code changed. Verified by reading
  the synced output across all 5 packs and re-running `sync-blocks.sh`
  twice to confirm convergence, plus the existing pytest/assert-output.sh/
  test-setup.sh regression suites.

---

## [2.7.39] — 2026-07-13 (Feature: persona hints on Documents card + review status; fix: awaiting-review ask)

### Added

- **Virtual Team persona hints extended to two more surfaces**: the
  dashboard's **Documents** card now shows the same ready-to-type ask next
  to its "what's next" line (`Next: Use Cases — or say: "Maya, write the
  use cases for checkout"`), and the terminal-only `sdd review status` adds
  a `· ask {name}` hint to every row that isn't Approved or Blocked.
- New public `status.persona_for(step_id, feature, scope)` lets callers
  outside the dashboard pipeline (like `sdd review status`, which reads
  Jira `document_reviews` keys directly) reuse the same Virtual Team
  lookup.

### Fixed

- **Awaiting-review docs no longer show a misleading persona ask.** 2.7.38
  attached a persona ask to every non-done pipeline step, but the ask
  templates are all creation-phrased ("create the BRD for X") — for a doc
  that already exists and is just waiting on a human reviewer, that
  wording wrongly implied it hadn't been created yet. The ask is now
  suppressed specifically for that state, on both the dashboard's Full
  Pipeline Next box and the Documents card; the per-step badge/tooltip is
  unaffected since it's a general "who owns this kind of work" reference,
  not a claim about one document's current state.
- 9 new tests; verified end-to-end against a live dashboard instance via
  headless-browser screenshot, confirming both the new Documents-card ask
  line and the awaiting-approval no-ask case render correctly.

---

## [2.7.38] — 2026-07-13 (Feature: Virtual Team persona hints on the dashboard)

### Added

- **`sdd dashboard`'s Full Pipeline stepper now shows who owns each step** —
  every step already documented as belonging to a named Virtual Team member
  (Maya, Rex, Ava, Leo, Kai, Quinn, Riley — see each pack's CLAUDE.md
  "Virtual Team — Address by Name" table) shows that name as a small badge
  next to its label, and the full name/role/example ask in its hover
  tooltip.
- The highlighted **Next** box gained a second line with a ready-to-type
  natural-language request instead of only the raw slash command — e.g.
  `💬 Or just say: "Maya, write the use cases for checkout" (Maya —
  Business Analyst)` — so you don't need to look up which command a step
  maps to; addressing a persona by name already works identically to
  running the command, this just surfaces it where you're looking.
- Steps that run before any persona takes over (`/specify`, `GATE-1`) or
  that are a byproduct of another command (the runbook, generated by
  `/implement`) intentionally show no persona badge. sdd-micro has no
  Virtual Team at all, so this never appears there.
- 4 new tests in `test_status.py`; verified end-to-end against a running
  `sdd dashboard` instance via headless-browser screenshot in both light
  and dark mode, not just unit tests.

---

## [2.7.37] — 2026-07-13 (Feature: Confluence local-svg diagram rendering)

### Added

- **`mode: local-svg`** — the third `confluence.diagrams:` mode, completing
  the work deferred in 2.7.36. Renders ` ```mermaid ` fences to SVG entirely
  offline — no browser, no Node.js, no network call at render time, no
  installed Confluence app required — and attaches the result to the page as
  an image via `<ac:image>`/`<ri:attachment>`.
- **Renderer choice was verified, not assumed.** Built an isolated venv,
  confirmed both PyPI candidates actually exist, extracted the real Mermaid
  diagram types SDD templates generate (flowchart, sequenceDiagram,
  classDiagram, erDiagram), and rendered each type through each candidate.
  `mermaidx`/`mmdc` (JS-engine backend) failed on flowchart stadium-shape
  nodes (`Actor(["User"])`, used in every design/hld/arch template's Actor
  node) and on `classDiagram` entirely. `mmdr` (Rust-based, ~18MB, zero
  further Python dependencies) rendered all four correctly — confirmed both
  textually and via visual PNG inspection.
- `mmdr` is an **optional dependency**, not a hard one — new
  `[project.optional-dependencies].diagrams` extra in `pyproject.toml`,
  installed with `pip install "sddflow[diagrams]"`, imported lazily only
  when `diagrams.mode: local-svg` is actually configured. A clear
  `MermaidRendererNotInstalled` error names the exact install command if
  configured but missing — never a bare `ImportError` traceback.
- New `ConfluenceClient.upload_attachment()` posts to
  `/content/{id}/child/attachment` with the `X-Atlassian-Token: nocheck`
  header multipart uploads require. Confluence auto-versions an existing
  attachment with the same filename, so no separate update path is needed.
- `md_to_storage()`'s return type changed from `str` to
  `tuple[str, list[Attachment]]` — all 6 call sites across `confluence.py`,
  `review.py`, and `cr.py` updated to unpack the tuple and upload queued
  attachments via a new shared `upload_diagram_attachments()` helper, after
  `upsert_page()`.
- **Every failure mode falls back to something safe** rather than crashing
  the whole document push: a missing dependency or invalid diagram source
  falls back to a plain code block for that one diagram; a failed
  attachment upload prints a warning but leaves the already-saved page
  content and remaining attachments unaffected.
- 17 new tests across `test_mermaid_render.py` (3),
  `test_md_to_cf.py::TestLocalSvgMode` (5), `test_confluence_client.py` (5),
  and `test_confluence_hierarchy.py::TestUploadDiagramAttachments` (4), full
  regression clean (356 tests).

---

## [2.7.36] — 2026-07-12 (Feature: Confluence diagram-macro rendering — mermaid-app, plantuml-macro)

### Added

- **`confluence.diagrams:` config block** — Confluence has no native Mermaid or
  PlantUML renderer, so a ` ```mermaid `/` ```plantuml ` fenced block pushed to
  Confluence used to always show as plain syntax-highlighted text, the
  diagram source rather than a rendered diagram. Two new modes route these
  fences through an installed Confluence app's macro instead:
  - `mode: mermaid-app` + `mermaid_app.macro_name` — routes ` ```mermaid `
    fences through the named macro of whichever Mermaid-rendering app
    (there are 10+ on the Atlassian Marketplace) the org has installed.
  - `mode: plantuml-macro` + `plantuml_macro.macro_name` — same idea for
    fences already written as ` ```plantuml ` (does **not** convert Mermaid
    syntax to PlantUML — different diagram languages). Most PlantUML apps
    render via the public `plantuml.com` server by default; orgs that can't
    reach external services need a self-hosted PlantUML render server
    instead.
  - Default (`mode: none`, or the block omitted) is exactly today's
    behavior — a diagram fence with no matching mode/macro configured
    always falls back to the plain code block, never a broken macro
    reference.
- Researched and explicitly **deferred** two more modes pending further
  work: `local-svg` (render Mermaid to SVG fully locally — no Confluence
  app, no external network call at render time — then attach as an image;
  needs a rendering-tool evaluation across the diagram types SDD templates
  generate before it ships) and `markdown-macro` (delegate the whole page
  to a whole-document Markdown-rendering Forge app; needs verified testing
  against a real installed app first — Forge macros use a different, less
  guessable reference shape than the two modes shipped here).
- 7 new tests (`test_md_to_cf.py::TestDiagramMacros`), full regression
  clean.

---

## [2.7.35] — 2026-07-12 (Feature: Confluence page hierarchy; fix: review-doc titles missing {feature})

### Added

- **Confluence pages now nest under Project → Feature container pages**,
  created automatically and idempotently the first time any doc is pushed —
  `parent_page_id` → a page named after the project → a page named after the
  feature → the doc pages themselves. Living/service-level docs (`data-model`,
  `security-design`, `api-spec`, `component-library`, `runbook`) nest directly
  under the Project page since they're shared across every feature, not
  per-feature.
- **Important caveat, verified before implementing:** Confluence enforces
  page-title uniqueness *per space*, not per parent page. Nesting is a
  navigation convenience only — it does not relax the need for `{feature}` in
  the page title text. Two features' same-titled pages would still collide
  even nested under different Feature pages, so `page_map` /
  `document_reviews.confluence_page` templates keep `{feature}` in every
  per-feature title.

### Fixed

- **`document_reviews.confluence_page` titles never substituted `{feature}`,
  only `{project}`.** This is a separate code path from `page_map` (used by
  `sdd confluence push/draft`, already fixed for this in an earlier release);
  `sdd review submit` and its two related call sites (`_push_doc_page`,
  `review_apply`) never applied the fix. Two features submitting the same doc
  type for review (e.g. both push a BRD) would silently overwrite each
  other's Confluence page. All three call sites now substitute both
  `{project}` and `{feature}`.
- 9 new tests (`test_confluence_hierarchy.py` plus a regression test proving
  two features no longer collide on the same review Confluence page), full
  regression clean.

---

## [2.7.34] — 2026-07-12 (Fix: review/CR tickets missing labels+team; per-level parent_field override)

### Fixed

- **`sdd review submit` and `sdd cr submit` were silently skipping your configured
  labels and team field.** A field-by-field audit of every Jira API call in the
  codebase found that `review_submit()` and `cr_submit()` hand-build their `fields`
  dict directly instead of routing through the same `_upsert_issue()` function
  every Epic/Story/Task/CHG issue uses — and had hardcoded their `labels` list to
  just `["sdd-review", ...]` / `["sdd-cr", ...]`, dropping `base_fields.labels`
  (e.g. the default `sdd-generated` label) entirely, and never applied
  `base_fields.team` at all. Both are fixed: review-gate Stories and CR review
  tasks now get the same labels and team stamp as every other issue type.

### Added

- **`jira.parent_field_by_level:` override**, the same pattern as `project_keys`
  and `custom_fields_by_level`: lets an org whose Story/Task Jira project needs a
  different parenting mechanism than the Epic's project (e.g. one project is
  next-gen and uses the `parent` system field, the other is classic
  company-managed and needs the Epic Link custom field) express that per level,
  instead of one `parent_field` value serving every level. `JiraConfig.parent_field_for(level)`
  resolves it; all 5 `set_parent()` call sites now use it.
- 10 new tests: `parent_field_for` default/override (2), per-level wiring at
  every `set_parent()` call site (5), a `parent_field_for` override on the
  review→Epic link (1), a full `review_submit()` end-to-end test confirming
  labels/team reach the created Story (1), and a new `test_cr.py` with the same
  assertion for `cr_submit()` (1).

---

## [2.7.33] — 2026-07-12 (Feature: per-level custom field ID overrides + team field)

### Added / Changed

- **`integrations.yml` `jira.custom_fields_by_level:` override block.** Follow-on to
  2.7.32's `project_keys`: if a hierarchy level's issues live in a
  different Jira project, that project almost always has different
  custom field IDs too — not just a different project key. `custom_fields_by_level:
  {level: {field: id}}` overrides the common `custom_fields` mapping per
  level; any `(level, field)` pair not listed falls back to the shared
  mapping, so existing configs are unaffected. `JiraConfig.fields_for(level)`
  resolves it, mirroring `key_for()`'s fallback semantics.
- **Fixed team field.** New `base_fields.team` (paired with a
  `custom_fields.team` field ID) stamps one fixed team name/ID on every
  issue this CLI creates — Epic, Story, Task, CHG, and UC-draft Story —
  via the new `_apply_team_field()` helper. It's the same value on every
  issue, not something that varies per story/task; leaving it unset
  never sends a team field, even if `custom_fields.team` happens to be
  configured.
- 8 new tests: 4 in `test_config_and_integrations.py` (`fields_for`
  default/override, `team` default/parsed) and 4 in
  `test_jira_push_levels.py` (`TestCustomFieldsAndTeam` — per-level
  override doesn't leak into other levels, team stamped across all five
  issue-creation call sites, team never sent when unset).

---

## [2.7.32] — 2026-07-12 (Feature: per-issue-type Jira project key overrides)

### Added / Changed

- **`integrations.yml` `jira.project_keys:` override block.** Some orgs keep
  their Epic/Feature in one Jira project and Stories/Tasks (or review
  tickets, CRs, CHGs) in another. `project_keys: {level: KEY}` lets each
  hierarchy level resolve to its own project key; any level left out falls
  back to the existing single `project_key` field, so projects with no
  `project_keys:` block are completely unaffected. Valid levels: `feature`,
  `story`, `task`, `review`, `chg`, `cr`.
- Every Jira-project-key call site across `jira.py`, `review.py`, `cr.py`,
  `pr.py`, and `dashboard.py` now resolves through the new
  `JiraConfig.key_for(level)` method instead of reading `project_key`
  directly. `sdd jira push`'s status header prints any configured
  `project_keys` overrides.
- Fixed a latent bug found while wiring this through: `_find_story_key`
  only ever searched by a story's `STORY-NNN` label, so a UC-derived
  story's real key could be missed entirely when `--level task` ran in a
  separate invocation from `--level story` — its tasks would get pushed
  with no parent link and no warning. It now checks the UC-derived label
  first, matching how `_push_stories()` already labels these issues.
- **Cross-project caveat (documented, not a bug):** Jira's parent/Epic-Link
  field generally does not support linking issues across different Jira
  projects on the standard REST API this CLI uses — true cross-project
  hierarchy needs Advanced Roadmaps (Jira Premium). If `project_keys` puts
  a child level in a different project than its parent, the child issue is
  still created, but the parent link may silently fail to appear in Jira.
  `sdd jira push` never fails silently on this — it always prints a `was
  not linked under ...` warning when a parent link doesn't take.
- 7 new tests: 2 in `test_config_and_integrations.py` (`key_for` defaults
  and overrides), 5 across `test_jira_push_levels.py` and
  `test_review_helpers.py` covering the call-site wiring itself.

---

## [2.7.31] — 2026-07-12 (Feature: Jira Epic/Story/Task hierarchy overhaul)

### Added / Changed

- **Epic created at `/specify`, not lazily.** The Feature/Epic issue in
  Jira is now created right after `/specify` generates the constitution —
  before any spec document exists — instead of being self-bootstrapped on
  the first `sdd review submit`. Its description starts as a placeholder
  and is automatically refreshed with real Business Objectives the next
  time an Epic-touching command runs (e.g. `/specify-brd`'s review
  submission) once `brd.md` exists.
- **Review tickets are Story issues, not Task.** BRD, Use Cases, SRD,
  Design/Arch/HLD/ADR, LLD, Tasks, Runbook, and Release review tickets now
  use issue type Story and are parented to the Epic — the same hierarchy
  level as dev Stories, so it's Epic → Story → Task throughout, review
  tickets included, not a separate shape.
- **Confluence + Jira submission happen together, immediately.** `sdd
  review submit` now pushes the document to Confluence *and* creates the
  Jira review Story in one call, right when the document is generated.
  This replaces the old two-stage flow (push a Confluence-only draft, wait
  for the user to say "done", then formally submit to Jira) in 5 command
  prompts (`specify-brd/uc/srd/doc`, `plan-design`); 4 more
  (`plan-arch/hld/adr/lld`) already worked this way and were converted to
  the same shared block for consistency. `sdd confluence pull` still works
  afterward if you want to pull in edits/comments left on the page.
- **Draft Stories per use case, finalized in place by `/task`.** A new
  `sdd jira push --level uc-draft` creates one lightweight placeholder
  Story per `UC-NNN` right after `/specify-uc` (parented to the Epic).
  When `/task` later generates `stories.md`, any story with a new
  `**Derived from:** UC-NNN` field (added only when a story traces 1:1
  back to a single use case) reuses that UC's idempotency label — Jira
  finalizes the *same* issue in place instead of creating a second one.
  Stories with no single-UC origin get a normal new Story issue, exactly
  as before this existed.
- 26 new tests across `test_jira_push_levels.py`, a new
  `test_sdd_parser.py`, and `test_review_helpers.py`.

---

## [2.7.30] — 2026-07-12 (Feature: `sdd upgrade --sync-prompts`)

### Added

- **`sdd upgrade --sync-prompts`** — re-copies `.github/prompts/` and
  `.claude/commands/` from the current pack into an already-scaffolded
  project, overwriting stale copies. Plain `sdd upgrade` only ever patches
  `manifest.yml`'s `sdd_version` field — it never touches these files, so
  fixes to prompt file *content* (like the 2.7.24/2.7.26/2.7.27 review-gate
  and token-usage-logging fixes) never reached a project that was
  scaffolded before those fixes shipped, even after upgrading the
  `sddflow` package. This closes that gap.
- Shows a preview (files to be updated/added, counts of what's already
  current) and asks for confirmation before writing anything — pass `--yes`
  to skip it. Every file about to be overwritten is backed up first to
  `.specify/.prompt-sync-backups/{timestamp}/`, so hand-edited prompt files
  are never silently lost.
- Which pack to sync from: `--pack` flag → `manifest.yml`'s new `pack`
  field (now written automatically by `sdd init` on every fresh project) →
  inferred from `project_type` → `sdd-universal` as a last resort. An
  inferred guess is always labeled as such, since projects scaffolded
  before this release have no `pack` field recorded.
- Only `.github/prompts/` and `.claude/commands/` are touched — nothing
  under `.specify/` (templates, constitution, your generated docs) is ever
  affected.
- 26 new tests (7 for the underlying `sync_pack_prompts()` helper, 19 for
  pack resolution and the CLI flag's preview/confirm/cancel/`--yes` paths);
  also verified live end-to-end against the real bundled packs.

---

## [2.7.29] — 2026-07-12 (Feature: dashboard Full Pipeline section)

### Added

- **`sdd dashboard` — Full Pipeline section.** Each feature now shows the
  *complete* command sequence for the project's scope and plan mode —
  `/specify` → `GATE-1` → `/specify-brd` → ... → `/release` (or sdd-micro's
  3-command flow) — not just the docs generated so far. Every step is
  shown, including ones this scope/plan mode skips (struck through, hover
  for why — e.g. "skipped — pilot scope", "skipped — unified plan mode"),
  mirroring CLAUDE.md's Scope Reference table exactly.
- Each step is marked **✓ done**, **● current** (you are here — either
  awaiting review or in progress), or **○ upcoming**. A doc that exists but
  isn't yet `Approved` shows as current, not done, so the review gate is
  visible directly in the stepper.
- A highlighted **Next** box spells out exactly what to do in plain
  language — e.g. "Run `/specify-uc` to generate the Use Case
  Specification" or `"BRD" is generated and waiting on review — check with
  sdd review check --doc brd`.
- Derived purely from `manifest.yml` (`scope`, `plan_mode`) and each doc's
  `Status:` header — no extra configuration needed.
- The old doc-list card is renamed **Pipeline → Documents** to avoid
  clashing with the new full-width **Full Pipeline** card.
- 12 new `status.py` tests plus 2 new `dashboard.py` source guards;
  verified live with a Playwright-driven headless Chromium session across
  two features at different pipeline positions.

---

## [2.7.28] — 2026-07-12 (Fix: dashboard comment box lost typed text; layout cramped)

### Fixed

- **`sdd dashboard` comment box** — typing a reviewer name or comment into
  the dashboard's inline comment form and pausing for even a few seconds
  would wipe the field. Root cause: the dashboard's `render()` replaces the
  entire `#root` panel on every 5-second auto-poll, regardless of whether
  the user is mid-keystroke, and the freshly-built input/textarea came back
  empty and unfocused.
- Fixed with two mechanisms: a delegated `input` listener now mirrors every
  keystroke into client-side state (keyed by feature+doc) and re-hydrates
  the fields from it on every render — this is what stops the text from
  being lost — plus a focus/selection-range restore around the periodic
  rebuild so typing feels uninterrupted. The draft clears once a comment
  successfully posts.
- Verified live with a Playwright-driven headless Chromium session against
  a real `sdd dashboard` instance: typed text survived two full poll
  cycles, focus/caret were restored, and Post Comment still worked
  end-to-end.
- **Layout** — the per-feature grid used one flat breakpoint for all four
  cards (Pipeline, Tasks, Token Usage, Jira Export), so the Pipeline card's
  Links column (View / Approve / comment count / Jira+Confluence pills)
  got visually cramped and cut off at narrower widths. The Pipeline card
  now spans the full row and the links column wraps instead of forcing
  `nowrap`. Verified with screenshots at 1200px and 900px.
- 3 new regression tests in `test_dashboard.py` guard the fix at the
  source level so a future edit can't silently drop it.

---

## [2.7.27] — 2026-07-12 (Fix: token usage logging still didn't fire — stale in-conversation context)

### Fixed

- **Token usage logging** — 2.7.26 fixed the structural placement bug
  (the log step used to sit unreachable behind multi-turn approval STOP
  points), but real testing showed the symptom persisted: the user
  confirmed via `ls -la` that `.specify/memory/token-pricing.yml`
  demonstrably existed, yet the agent still reported "No token-pricing.yml,
  so skipping usage logging" on a later command in the same conversation.
- Root cause was neither the opt-in gate (ruled out earlier) nor placement
  (fixed in 2.7.26) — it was the model relying on an earlier,
  in-conversation check performed *before* the user created the file,
  instead of re-checking fresh each time.
- `token-usage-log-step.md` now explicitly instructs agents to check with
  a fresh file read, not a memory of whether the file existed earlier in
  the conversation — an earlier "not found" does not carry forward.
- This surfaced the same `sync-blocks.sh` content-precedence gotcha noted
  in the 2.7.24 entry a second time: 13 files under
  `packs/_shared/full/.github/prompts/` have this block's content
  embedded directly (full-file sync wins over the blocks loop within a
  single run), so editing only `packs/_shared/blocks/token-usage-log-step.md`
  did not propagate to any pack until those 13 files were updated too.

---

## [2.7.26] — 2026-07-10 (Fix: token usage logging was structurally unreachable in 9 commands)

### Fixed

- **Token usage logging** (`.specify/memory/token-pricing.yml`, opt-in)
  was correctly wired into every document-generating command in 2.7.18,
  but in 9 of them — `specify-brd`, `specify-uc`, `specify-srd`,
  `specify-doc`, `plan-design`, `plan-arch`, `plan-hld`, `plan-adr`,
  `plan-lld` — the logging instruction sat at the very end of the file,
  **after** the Stakeholder Review and Approval section. That section
  contains STOP points that end the current turn and defer continuation
  until the user says "done" or "approved" — sometimes several exchanges
  later. The document itself was already fully saved and complete well
  before that point, but the logging instruction was unreachable behind
  those unrelated, later turns.
- Found via real testing: `token-pricing.yml` existed and the feature was
  correctly enabled, yet `token-usage.md` was still never being updated.
- The `token-usage-log-step` block now sits immediately after the
  document is saved (right before the review section begins) in all 9
  affected prompts, so it executes in the same turn as the actual
  generation work — no longer dependent on how many turns the subsequent
  approval flow takes.
- `task`, `checklist`, `implement`, `release`, `validate`, `analyze`, and
  `clarify` prompts were already placed correctly and needed no change.
  `create-context` and `change` intentionally log at their genuine
  completion point (after the user's iteration loop finishes) — those
  commands' output isn't final until then, so that placement is correct
  by design, not a bug.

---

## [2.7.25] — 2026-07-10 (Fix: failed Jira parent-links vanished silently)

### Fixed

- **Every Jira parent-link call site** — Story/Task/CHG under the
  Feature/Epic in `sdd jira push`, and the review ticket under the Epic
  in `sdd review submit` — was wrapped in a bare `except Exception:
  pass`. A failed link vanished with zero indication, even though the
  issue itself had already been created successfully.
- Found via real testing: a review ticket and its Epic both appeared in
  Jira but weren't linked, with no error anywhere to explain why. Root
  cause: a **company-managed (classic)** Jira project, where linking a
  Story/Task/review-Task to an Epic uses the **Epic Link custom field**,
  not the `"parent"` field team-managed (next-gen) projects use.
- All five call sites now print a warning naming the child/parent keys,
  the underlying error, and a pointer to `sdd config fields --project
  {key}` to find the right field ID for `parent_field` in
  `integrations.yml`. Still never blocks the push/submit itself — the
  issue is created either way — it just makes a failed link diagnosable
  instead of silently invisible.

---

## [2.7.24] — 2026-07-10 (Fix: review comments were never automatically read back and incorporated)

### Fixed

- **Every document-generating command** (`/specify-brd`, `/specify-uc`,
  `/specify-srd`, `/specify-doc`, `/plan-design`, `/plan-arch`,
  `/plan-hld`, `/plan-adr`, `/plan-lld`) had its own hand-duplicated "on
  approval" step that only triggered when the user literally said
  "approved", and treated any other outcome — NEEDS REVISION, PENDING —
  as a bare yes/no "proceed anyway?" prompt. It never read the reviewer's
  Jira comments back or updated the document, even though
  `check-review.prompt.md`/`submit-review.prompt.md` already implemented
  that exact read-comments-and-apply loop correctly, just as a separate,
  manually-invoked command nothing else called.
- Found via real end-to-end testing: after leaving comments on a
  submitted BRD review ticket, nothing in the `/specify-brd` flow ever
  fetched or acted on them automatically — despite CLAUDE.md's own
  `review-gates` block already documenting this as the intended
  behavior ("When `sdd review check` exits 1: read reviewer comments,
  update the document, then run `sdd review apply`").
- All 9 prompts now share one `review-decision-step` block: trigger on
  any check-in signal (not just the word "approved"), run `sdd review
  check`, and on NEEDS REVISION actually read the printed comments, edit
  the document, and run `sdd review apply` — closing the loop end to end.
- **Also fixed a real bug in `packs/_shared/sync-blocks.sh`** discovered
  while shipping this: the first time a brand-new shared block has zero
  existing matches, `grep` exits 1, and under `set -e -o pipefail` that
  silently aborted the entire sync script before the full-file-copy loop
  ever ran. Switched to process substitution so introducing a new shared
  block no longer breaks the sync tooling.

---

## [2.7.23] — 2026-07-10 (Fix: Jira search calls broken by Atlassian's endpoint deprecation)

### Fixed

- **`JiraClient.search()`** was calling `GET /rest/api/3/search`, which
  Atlassian deprecated and has now removed (returns `410 Gone`) in favor
  of `POST /rest/api/3/search/jql`. This broke every Jira issue lookup by
  label — `find_by_label()`, used by `sdd review submit`'s Feature/Epic
  self-bootstrap, `sdd jira push`'s create-or-update idempotency check,
  and `sdd review check/status/apply` — on any Jira Cloud instance
  Atlassian's rollout had already reached.
- Found via a real `sdd review submit --doc brd` failure during
  pre-publish testing: the Confluence half succeeded, the Jira half
  failed with `410 Gone`, and the review silently fell back to chat
  approval with no Jira ticket created at all.
- `search()` now POSTs to `/rest/api/3/search/jql` with `jql`/`fields`/
  `maxResults` in the JSON body, matching Atlassian's documented
  migration path. Only the first page of results is fetched — every
  caller here is an idempotency lookup expecting 0–1 matches, so
  `nextPageToken` pagination was never needed.

---

## [2.7.22] — 2026-07-10 (Fix: Markdown tables were destroyed on every Confluence push)

### Fixed

- **`md_to_cf.py`** (the Markdown → Confluence Storage Format converter
  used by `sdd confluence push`, `sdd review submit`, `sdd review approve
  --local`'s auto-mirror, and `sdd cr submit`) had **no table support at
  all**. Every `| cell | cell |` row fell through to the generic
  paragraph handler and was joined with spaces onto a single line,
  destroying all row/column structure. This affected nearly every
  document template in every pack, since most use Markdown tables (BRD
  Business Objectives, API endpoint tables, FR/NFR tables, integrations
  tables, etc.) — found while testing a real Confluence push.
- GFM pipe tables (`| ... |` header row + `|---|---|` separator row) now
  render as real Confluence `<table>` markup, including alignment
  markers (`:---`, `:---:`, `---:` → `text-align` styles) and inline
  formatting (`**bold**`, `` `code` ``, `[links]`) inside cells.
- **Action needed for any already-published Confluence page:** re-push it
  to pick up correctly-rendered tables — `sdd confluence push --doc
  {name}` (or `--all`).

---

## [2.7.21] — 2026-07-10 (Add: sdd jira push --level/--cr; retire the standalone jira-push.py script)

### Added

- **`sdd jira push --level {epic|story|task|chg|all}`** (default `all`) — the
  CLI can now push progressively at each SDLC gate: Epic right after BRD
  approval, Stories after Use Cases/SRD approval, Tasks after `/task`, CHG
  tasks after `/change` — matching what the standalone script used to do.
  A level pushed on its own finds its parent (Feature/Epic or Story) live
  via Jira labels, so there's no strict "push epic before story before
  task" ordering requirement — levels can be pushed in any order and still
  link up correctly.
- **`sdd jira push --level chg --cr CR-NNN`** — pushes a changeset's
  `§4 CHG-NNN` implementation tasks as their own Jira issues, parented to
  the Story that owns the matching FR reference (falling back to the
  Feature/Epic).
- **`docs/jira/{feature}/keys.yml`** — the CLI now writes the same
  local, human-readable summary of pushed Jira keys the old script did.
  Reference only: never read back by `sdd jira push` itself, since
  parent-linking and idempotency are always re-derived live from Jira's
  `sdd-feature:*`/`sdd:*` labels.
- Two new optional `custom_fields` keys in `.specify/integrations.yml` —
  `fr_reference` and `moscow_priority` — let Story/Task/CHG issues carry
  those as separate Jira fields (in addition to the plain-text line
  already in every issue's description).

### Removed

- **`.specify/scripts/jira-push.py`** and
  **`.specify/templates/jira-config-template.yml`** — retired from every
  pack. The `/jira-push` slash command is now a thin wrapper around
  `sdd jira push --level ...` (same command the CLI exposes directly),
  not a separate standalone script. All Jira/Confluence configuration now
  lives in one place: `.specify/integrations.yml` (set up via
  `sdd config init` or by copying `.specify/integrations.yml.example`).
  Both `/jira-push` and `sdd jira push` still run unattended from CI/CD —
  there was never an AI-session requirement, it just used to be a
  separate script rather than the CLI itself.

### Notes

- This completes the Jira/Confluence consolidation plan started in
  2.7.20 (content parity + self-bootstrapping Epic). Remaining, smaller
  items: a couple of doc/prompt corners describing the old two-path setup
  may still need a follow-up pass if anything was missed — flag it if you
  spot one.

---

## [2.7.20] — 2026-07-10 (Fix: sdd jira push content parity + self-bootstrapping Epic for review tickets)

### Fixed

- **`sdd jira push` content parity**: the CLI's Feature/Epic issue previously
  got a blank description and Task issues silently dropped their parsed
  Acceptance Criteria. Both now match the progressive `/jira-push` script:
  the Feature/Epic description is built from `brd.md`'s Business
  Objectives, and every Story/Task description includes its Acceptance
  Criteria.
- **Review-ticket label collision**: `sdd review submit`'s Jira ticket used
  an un-feature-qualified idempotency label (`sdd-doc:{doc}`), so on a
  multi-feature project a second feature's review submission for the same
  doc key (e.g. `brd`) could silently overwrite the first feature's ticket.
  Same bug class already fixed for Story/Task labels — now
  `sdd-doc:{feature}:{doc}`. `sdd review check/status/apply` and the
  dashboard's approve/comment endpoints were updated to look up the same
  qualified label.

### Added

- **Self-bootstrapping Feature/Epic**: `sdd review submit` now ensures the
  project's Feature/Epic exists (creating it from `brd.md`'s Business
  Objectives if `sdd jira push` hasn't run yet, since BRD is always the
  first document reviewed) and parents the review ticket under it — so
  review tickets and later dev Story/Task tickets from `sdd jira push`
  converge on the same Epic in Jira instead of scattering across
  unlinked issues.

### Notes

- This lands the highest-value slice of a larger Jira/Confluence
  consolidation plan. Deferred for later: staged `--level` pushes + CHG
  support in the CLI, consolidating `jira-config.yml` into
  `integrations.yml`, routing `/jira-push` through the CLI, and retiring
  the legacy standalone script.

---

## [2.7.19] — 2026-07-11 (Add: store Jira/Confluence credentials in the OS keychain)

### Added

- **`credential_store: keyring`** option for `~/.sdd/config.yml` profiles
  (alongside the existing `env` behavior, which stays the default for
  profiles written before this version). When set, `sdd config init`
  asks for the actual token and stores it via the OS-native secure
  credential store — macOS Keychain, Windows Credential Manager, Linux
  Secret Service — through the new `keyring` dependency, instead of
  asking for an environment variable name.
- **New `sdd config set-secret --profile {name}`** command to rotate a
  keychain-stored credential without re-running the whole `config init`
  wizard.
- **Why**: an environment variable exported in one terminal is invisible
  to an AI coding tool's own subprocess shell (or any other new shell) —
  this showed up as "can't connect to Jira/Confluence" even when the
  token itself was perfectly valid, and was a genuine barrier for
  non-technical users. A keychain-stored credential is readable by any
  process on the machine, not scoped to one shell session, so it works
  the same way in any terminal or any AI tool without shell setup.
- If no keychain backend is available (headless Linux, minimal
  containers), `config init`/`set-secret` fail with a clear message
  suggesting the `env` option instead of a raw traceback.
- Existing `env`-mode profiles are completely unaffected — this is
  purely additive.

---

## [2.7.18] — 2026-07-11 (Fix: token usage logging instruction was invisible to every command)

### Fixed

- **Token usage logging** (opt-in via `.specify/memory/token-pricing.yml`)
  was documented only in `CLAUDE.md`, read once at session start — no
  individual command prompt (`specify-uc.prompt.md`, `task.prompt.md`,
  etc.) ever referenced it, so the agent had to spontaneously recall a
  rule from a different, earlier-read file on every command. In practice
  this made logging unreliable even when `token-pricing.yml` existed and
  was correctly filled in. Found via manual pre-publish testing.
- A new shared block (`token-usage-log-step`) now appears near the end of
  every document-generating command prompt — `/create-context`, every
  `/specify-*`, `/plan-*`, `/task`, `/implement`, `/release`, `/change`,
  `/checklist`, `/validate`, `/analyze`, `/clarify` — right at the point
  the agent is about to finish and report, across all 5 full packs.
- This is a prompt-content fix, not a behavior change to what gets
  logged or how — the full field spec still lives in `CLAUDE.md`'s
  "Token Usage Logging" section.

---

## [2.7.17] — 2026-07-11 (Fix: Approve didn't update the doc's own Approvals table)

### Fixed

- **`sdd review approve --local` and the dashboard's Approve button** used
  to only flip a document's `Status:` header to `Approved` — the `##
  Approvals` table further down the same file (Role/Status/Date rows)
  was left showing `Pending` even after approval, so the header and the
  visible table body disagreed. Every `Pending` row inside the `##
  Approvals` section now flips to `Approved` with today's date filled
  in, scoped to that section only so a coincidental "Pending" cell
  elsewhere in the doc is never touched.
- **Self-healing**: running approve again on a doc whose header was
  already `Approved` by the old code, but whose table still says
  `Pending`, now fixes the table too — no manual edit needed for docs
  approved before this fix.
- Multi-role Approvals tables (e.g. `design.md`'s Architect / Tech Lead /
  Stakeholder rows) have every row flipped together, matching local-mode
  approval's existing single-approver-per-document model rather than
  attributing individual rows to reviewers the CLI/dashboard were never
  told about.

---

## [2.7.16] — 2026-07-10 (`sdd dashboard`: Approve + review comments)

### Added

- **"Approve" button** per document. Flips that doc's `Status:` header
  to `Approved` and records who/when/why in
  `.specify/.local-approvals.yml` — the exact same file and format
  `sdd review approve --local` already uses, so the CLI and the
  dashboard share one audit trail. Mirrors to Confluence automatically
  if configured (same as the CLI command), and posts a best-effort
  comment ("Approved via SDD Dashboard by {name}") to that document's
  review-gate Jira ticket if configured. Neither Confluence nor Jira
  failing blocks the local approval, matching the CLI's existing
  behavior.
- **Review comment box** (💬) per document. Saves locally to a new
  `.specify/.dashboard-comments.json`, scoped per feature+document (a
  new store, so — unlike the approvals file — this one is feature-scoped
  from the start), and best-effort mirrors to Jira as a comment on the
  same review-gate ticket. Confluence comment posting isn't implemented
  yet (only page content sync on approve, via the existing mechanism).

### Known limitations (documented, not silently glossed over)

- `.local-approvals.yml` stays keyed by bare document name, matching
  `sdd review approve`/`sdd review check`'s existing format exactly —
  interoperability with those CLI commands won over fixing their
  pre-existing lack of feature-scoping as a side effect of this change.
  On a multi-feature project, approving "brd" doesn't distinguish which
  feature's BRD at the `review check` layer.
- Jira only gets a comment, not a workflow status transition — Jira's
  transitions API isn't wrapped anywhere in this codebase. Approval
  stays local-first, same as the CLI's own design.
- `--host 0.0.0.0`'s printed warning now also covers write access:
  anyone reachable on the network can approve documents and post
  comments on your behalf, not just view status. No credentials pass
  through the dashboard either way.

---

## [2.7.15] — 2026-07-09 (`sdd dashboard`: Jira/Confluence links, LAN sharing, doc viewer)

### Added

- **Local Jira/Confluence links, always instant.** Each pipeline doc now
  shows an Epic/Story/Task link (from `docs/jira/{feature}/keys.yml`,
  written by the progressive Jira export) and a Confluence page link
  (from `.specify/.confluence-drafts.json`, written by `sdd confluence
  push`/`draft`), when either exists. Pure file reads, no network call —
  consistent with the dashboard's existing offline-by-default design.
- **"🔄 Check Jira/Confluence review links" button**, per feature. The
  tickets `sdd review submit` creates per document are never cached
  locally (unlike the progressive export), so resolving them needs a
  live Jira/Confluence lookup — this makes that lookup explicit and
  on-demand, using your existing `~/.sdd/config.yml` profile and
  `.specify/integrations.yml`, and never fires on the automatic 5s poll.
- **"View" button per document** reads the raw `.md` straight from disk
  into the page (new `/api/doc` endpoint) — no need to leave the browser
  to check a document's content.
- **`--host` flag** (default `127.0.0.1`). Run with `--host 0.0.0.0` on
  a shared devbox so teammates on the same network can open the
  dashboard from their own browser — the CLI prints the reachable LAN
  URL and a caution. This is still one unauthenticated process on one
  machine, not a hosted/always-on service; it stops when you close the
  terminal, and it's read-only and never sends credentials to the
  browser, but it does expose the project's `.specify/` status to
  anyone who can reach the port — only use it on a trusted network.

### Security

- The new `/api/doc` and `/api/review-links` endpoints take
  `feature`/`doc` values from HTTP query params rather than trusted
  local CLI flags — once `--host` makes the server reachable beyond
  `127.0.0.1`, that's untrusted network input. Both are validated
  against a strict `[A-Za-z0-9_-]+` pattern before ever being used to
  build a filesystem path, closing off path traversal. Verified with a
  live request containing `../../../etc` in both `feature` and `doc` —
  correctly rejected with 400 before any file access.

---

## [2.7.14] — 2026-07-09 (New `sdd dashboard` — local status UI, Python CLI)

### Added

- **`sdd dashboard`** — a local, read-only web UI over the current
  project's `.specify/`: pipeline progress per feature (every generated
  doc and its `Status:` header, plus a best-effort "what's next" guess),
  task completion (parses both the full packs' checkbox-based `tasks.md`
  and `sdd-micro`'s `**Status:**` field), and token usage (the running
  totals from `token-usage.md`, when logging is enabled). Multi-feature
  aware — every folder under `.specify/features/` gets its own section.
  `sdd dashboard [--port N] [--no-open]`.
- Unlike `sdd review status`, this needs **no Jira/Confluence
  configuration** — it reads the `Status:` header already written into
  each doc's `.md` file, which is the authoritative gate in every review
  mode (chat, local, jira) per each pack's CLAUDE.md. It's a viewer
  only — nothing it does writes to `.specify/`. The page polls
  `/api/status` every 5 seconds so it reflects new commands as the agent
  runs them.
- Implemented with the stdlib `http.server` — no new pip dependency.
  New pure-function module `sdd/utils/status.py`
  (`build_project_status`, `build_feature_status`), unit tested
  (16 new tests) independent of the HTTP layer.
- Task/PR status reflects `tasks.md` only, not live PR state on your git
  host — that would need per-host credentials/API calls and is out of
  scope for this command (see `sdd pr create`/`sdd pr comments` for
  live PR interaction instead).
- Python-CLI-only (`sddflow`) — the Node CLI stays scoped to
  init/upgrade scaffolding per its own README.

---

## [2.7.13] — 2026-07-08 (New pack — sdd-micro, for tiny/personal projects)

### Added

- **`sdd-micro`** — a 6th, standalone pack for scripts and small personal
  projects that don't need the full 11-command SDLC: a script that
  prints "Hello, world!", a small CLI utility, a weekend project. Flow
  is just `/specify → [GATE-1: confirmed] → /task → /implement` — no
  BRD, Use Cases, SRD, Validate, Analyze, Clarify, Design, or Release.
  It keeps the two things that actually prevent drift on a small
  project — a short constitution (tech stack + ground rules, confirmed
  once at GATE-1) and a flat, verified task list — and drops everything
  that exists in the bigger packs to make a multi-stakeholder, audited
  project traceable. See `packs/sdd-micro/CLAUDE.md` and `WHY-SDD.md`
  for the full reasoning, and `README.md` → "Outgrowing sdd-micro" for
  when to move to `sdd-universal`.
- `sdd init --pack sdd-micro` (or the interactive picker's "Choose from
  all packs…" option, both CLIs) now scaffolds it. Because its
  `manifest.yml` has no `scope`/`project_type` fields, `sdd init`
  detects a micro-shaped manifest (fill mode: existing manifest missing
  both keys; scaffold mode: `sdd-micro` was the chosen pack) and skips
  the scope and project-type questions for it — existing packs are
  unaffected, their manifests always carry both keys.

### Divergence note
`sdd-micro` intentionally does not follow `PACK-SPEC.md` (the full-SDLC
pack spec) or `packs/_shared/sync-blocks.sh` (no `_shared/blocks/`
markers in its files) — see the exception note added to the top of
`PACK-SPEC.md`. It is hand-maintained, not generated from `_shared/`.

---

## [2.7.12] — 2026-07-07 (Multi-feature safety fix — progressive Jira export, all 5 packs)

### Fixed — a more severe version of the bug fixed in 2.7.11

The progressive Jira export mechanism — `/specify-brd` writes
`docs/jira/epic.md`, `/specify-uc` writes `docs/jira/stories-draft.md`,
`/specify-srd` writes `docs/jira/stories-refined.md`, and `/jira-push`
(via `.specify/scripts/jira-push.py`) reads all three and writes
`docs/jira/keys.yml` — lived at one fixed global path, never scoped per
feature the way `.specify/features/{feature}/` already is.

On a multi-feature project: a second feature's BRD/UC/SRD approval
**overwrote** the first feature's staged Epic/Story export files on disk
before they were even pushed, and pushing the second feature's Epic
**overwrote** the first feature's locally-tracked Jira key in `keys.yml` —
corrupting parent-link lookups for the first feature's Stories/Tasks the
next time it was touched. Unlike the `sdd jira push`/`sdd confluence push`
bug fixed in 2.7.11 (where the Jira issues themselves were mostly
protected by title-based matching), this one had **no per-feature
isolation on the local files at all**.

All `docs/jira/` artifacts are now under `docs/jira/{feature}/` —
`epic.md`, `stories-draft.md`, `stories-refined.md`, `keys.yml`,
`stories.md`, `jira-import.csv` — mirroring
`.specify/features/{feature}/`. Verified with a direct
`load_keys`/`save_keys` round-trip for two features confirming no
cross-feature collision (no existing pytest coverage for this
standalone script, so verified by direct execution instead).

### Migration note
Re-copy the pack (or run `sdd init`/`sdd upgrade` over it) to pick up the
updated `.specify/scripts/jira-push.py` and the five
`.github/prompts/*.prompt.md` files that write/read these paths
(`specify-brd`, `specify-uc`, `specify-srd`, `task`, `jira-push`). Any
`docs/jira/*.md` or `keys.yml` files from before this upgrade are not
migrated automatically — move them into `docs/jira/{feature}/` manually
if you want to keep them.

---

## [2.7.11] — 2026-07-07 (Multi-feature safety fixes — Jira/Confluence, all 5 packs)

### Fixed — found while reviewing how multi-feature projects push to Jira/Confluence

- **`sdd confluence push/draft/pull`** built each page title from only
  `{project}`, never `{feature}`. On a multi-feature project, two
  features pushing the same per-feature doc type (`brd`, `use-cases`,
  `srd`, `design`, `lld`, etc.) upserted the identical Confluence page
  and silently overwrote each other's content. `_resolve_page_title()`
  now substitutes `{feature}` into the title whenever the `page_map`
  template includes that placeholder — opt-in, so existing configs
  without it see no title change and no page gets orphaned. Living/
  service-level documents (`data-model`, `security-design`, `api-spec`,
  `component-library`) always strip `{feature}` even if present, since
  they must stay one shared page regardless of which feature pushed them.
- **`sdd jira push`/`sdd jira sync`** keyed Story/Task idempotency labels
  on `sdd:{id}` only, not qualified by feature. Since `STORY-NNN`/
  `TASK-NNN` numbering restarts independently per feature (same as
  `CR-NNN`), two features' `STORY-001` collided and the second feature's
  push silently overwrote the first feature's Jira issue. Labels are now
  `sdd:{feature}:{id}`, matching the Feature-level label
  (`sdd-feature:{feature}`) which was already feature-safe.
- **`LIVING_SERVICE_DOCS`** was missing `"component-library"`
  (frontend-spa/fullstack's shared component catalog) — `resolve_doc_path()`
  routed it to the wrong (per-feature) path, breaking `sdd review` and
  `sdd confluence` for that one doc type.

### Added

- **`/change --feature {slug} "description"`** — targets a feature other
  than `manifest.yml`'s active one for this CR only, without editing
  `manifest.yml` (same pattern already used by `sdd jira push --feature`
  and `sdd confluence push --feature`). Errors clearly (lists the
  features it actually found) if the named feature doesn't exist. Also
  fixed a gap this surfaced: the context.md-rename special handling used
  to update `manifest.yml`'s active feature unconditionally on a rename —
  it now only does so when the renamed feature is the one `manifest.yml`
  already points to, so a `--feature`-scoped CR can't silently switch
  which feature every other command operates on.
- **Optional per-feature token/cost usage logging**
  (`.specify/features/{feature}/token-usage.md`) — off by default, turns
  on by copying `token-pricing.yml.example` to `token-pricing.yml`.
  Self-estimated (`characters ÷ 4`), not measured — no AI tool this
  framework supports exposes exact token introspection.
- Consolidated "Configuration Files (YAML)" table in every pack's
  `README.md` — `integrations.yml`, `jira-config.yml`, and the CI
  pipeline YAMLs were previously undiscoverable from the entry-point doc.

### Security

- `.specify/jira-config.yml` (legacy Jira integration path, contains
  credential placeholders) is now gitignored by default in all 5 packs —
  it wasn't before, despite its own header comment saying it should be.

### Migration note
Re-copy the pack (or run `sdd init`/`sdd upgrade` over it) to pick up the
updated `.specify/integrations.yml.example` (per-feature `page_map`
entries now include `{feature}`) and `.gitignore`. First Jira push after
upgrading creates fresh Story/Task issues under the new label rather than
finding old ones under the old label — nothing is deleted or overwritten,
but pre-upgrade issues should be manually closed if they're now
duplicates.

---

## [2.7.10] — 2026-07-06 (Bug fix — /change living-document handling, all 5 packs)

### Fixed — found via live end-to-end dogfooding of a two-feature service

Built a real two-feature scenario (an `instant-payment` service +
`payment-dashboard`, sharing one data model/API surface/security
baseline) to exercise `/create-context`'s Feature Size Check and the
living-doc mechanism end to end, then specifically stress-tested how
`/change` behaves once a service has more than one feature. This surfaced
two real bugs:

- **Stale path assumption**: `/change`'s Stage Detection (`Step 3`) scanned
  only `.specify/features/{feature}/` to determine which documents exist.
  `context.md` has always lived at `.specify/contexts/{feature}.md`, and
  `data-model.md`/`security-design.md`/`api-spec.md`/`component-library.md`
  have lived at `.specify/service/{doc}.md` since the living-document
  mechanism shipped in `2.7.6` — neither location was ever checked. A CR
  touching any of these could be reported as "not yet created" even though
  the document existed and was approved, meaning the CR's real impact was
  never assessed or shown to the reviewer.
- **No cross-feature impact awareness**: even with paths resolved
  correctly, nothing checked whether a *different* feature depends on the
  specific unit (entity, endpoint, threat, component) being changed in a
  shared living document. A CR raised against one feature that happens to
  touch a unit another feature owns could be silently approved with zero
  indication that the sibling feature is affected — because that feature's
  own `srd.md`/`design.md` are never read during a `/change` session
  scoped to the feature that raised the CR.

### Added

- `change.prompt.md` Step 3 now resolves each document's real location
  (a lookup table for the four exceptions) before concluding anything
  "does not exist yet"
- New "Special handling — when the document being walked is a living
  document" section: before proposing an UPDATE/RERUN to a living
  document, `/change` reads its `## Version History`, identifies which
  feature last touched the affected unit, and — if it's a different
  feature than the one raising this CR — includes an explicit
  cross-feature warning in the same proposal (advisory, not a hard block;
  verified this does not fire on same-feature edits — no false positives)
- `changeset-template.md` and `change-rules.md` (all 5 packs) updated to
  document the real file locations and the cross-feature impact rule
- Fixed the identical stale-path bug in `packs/_shared/tests/assert-output.sh`'s
  own `data-model.md`/`security-design.md exists` checks — this had been
  silently wrong since `2.7.6` because the only CI-exercised worked example
  (`examples/todo-api`) runs at `pilot` scope, which skips those checks
  entirely

### Verification
- Full live simulation: two features built end to end (context → BRD →
  use-cases → SRD → living data-model/security-design/api-spec → design →
  tasks), confirming Actor Registry reuse, NFR baseline reference, and
  living-doc walk-and-diff all work as designed
- `/change` cross-feature warning confirmed to fire correctly on a
  genuine cross-feature case (a status-enum change originating in one
  feature, raised as a CR from another) and confirmed *not* to fire on a
  same-feature edit
- `cli-python` pytest suite: 102/102 passed
- `packs/_shared/tests/test-setup.sh`: 15/15 passed
- `packs/_shared/tests/assert-output.sh` against `examples/todo-api`
  (pilot): 33/33 passed; against the new mvp-scope test feature: the
  fixed `data-model.md exists (living doc)` check now correctly passes

---

## [2.7.9] — 2026-07-06 (Framework content — /create-context, all 5 packs)

### Added — Feature Size Check in `/create-context`

Users pasting informal notes into `/create-context` sometimes describe
more than one feature-sized slice at once (e.g. "a payment processor,
and also a dashboard to view payment details"). Every downstream
document — use-cases.md, srd.md, design.md, tasks.md, release.md — is
authored per feature, so cramming multiple independent capabilities into
one context.md meant they all inherited an oversized, tangled spec
instead of each getting its own clean, reviewable slice.

- New **Step 1.5 — Feature Size Check**, run before the full template
  mapping: clusters the described actions by "actor + goal" and looks
  for 2+ clusters that are independently shippable (don't block or get
  blocked by each other), have non-overlapping actor sets, or span
  separate resource domains with no shared entity
- If only one cluster is found (the common case), the check is silent —
  no behavior change for a normal, single-scope input
- If 2+ clusters are found, the agent stops and asks the user directly:
  build it as **one feature** anyway, or **split it and build one at a
  time** — the user's call, not an automatic decision
- On a split: the chosen cluster continues through drafting as normal
  (with `feature-name` re-derived from that cluster, not the original
  all-encompassing description); every other cluster's raw notes are
  saved to its own `.specify/contexts/{slug}.raw.md` so nothing is lost
  and it can be picked up later with a plain `/create-context` run
  pointed at that file
- Single edit to the shared `create-context.prompt.md`, propagated to
  all 5 packs

### Verification
- `cli-python` pytest suite: 102/102 passed
- `packs/_shared/tests/test-setup.sh`: 15/15 passed
- `packs/_shared/tests/assert-output.sh` against `examples/todo-api`: 33/33 passed

---

## [2.7.8] — 2026-07-06 (Framework content — per-pack consistency audit, all 5 packs)

### Fixed — bugs introduced or surfaced by the 2.7.6/2.7.7 living-doc work

`2.7.6`/`2.7.7` built the living-document mechanism against
`sdd-backend-service` and assumed it generalized cleanly. A follow-up
per-pack audit (frontend-spa, mobile, fullstack, universal each have a
different shape — no API in frontend-spa/mobile, a split Backend/Frontend
stack in fullstack, ten auto-detected project types in universal) found
real bugs and real gaps that single-pack testing had missed:

- **Orphaned template wired in**: frontend-spa/mobile's own
  `api-spec-template.md` ("Backend API Contract — Consumer") was correctly
  written but never referenced by name in any prompt — `plan-design.prompt.md`
  §3's consumer-view branch now names it explicitly
- **Self-contradicting Scope Reference table**: the `2.7.6` edit asserted
  API Spec is living unconditionally across all packs, contradicting
  frontend-spa/mobile's own per-feature consumer-view carve-out for the
  same concept. Split into two explicit rows (provider vs consumer)
- **`runbook.md` path drift**: frontend-spa/mobile/fullstack's
  `release-template.md` said plain `runbook.md` in the References table
  and Rollback Plan text; `/implement` actually generates
  `docs/runbook/local-setup.md` in every pack — corrected
- **Stale scope marking**: frontend-spa/mobile's CLAUDE.md and
  HOW-TO-USE.md marked `data-model` as "full only", contradicting the
  Scope Reference table (mvp+) and every other pack — corrected
- **Stale command reference**: universal's CLAUDE.md/HOW-TO-USE.md still
  listed a `/specify-doc api-spec` command — api-spec moved to
  `/plan-design` §3 back in `2.7.6`, universal's docs were never updated

### Changed — living-doc treatment extended to the packs it was missing from

- **fullstack + universal**: `data-model-template.md`,
  `security-design-template.md`, `api-spec-template.md` now carry the same
  "Living document" banner/framing `sdd-backend-service` had — the
  underlying mechanism (`specify-doc.prompt.md`, `plan-design.prompt.md`)
  is shared across all 5 packs and was already active here; only the
  pack-specific template headers were missing the framing
- **fullstack + universal**: `constitution.md` gains a **Service NFR
  Baseline** table, wired into each pack's own `specify.prompt.md` —
  fullstack's is split Backend/Frontend (Performance/Availability/
  Throughput/Data Retention vs Load Time/Bundle Size/Interactivity)
- **frontend-spa + mobile**: `data-model.md` (Frontend State & Storage
  Model / Local Data & Cache Model) and `security-design.md` are now
  explicitly living/app-level documents, same mechanism as
  `sdd-backend-service`'s `data-model.md` — just describing state/storage
  and client-side security instead of a database schema
- **frontend-spa + mobile**: `constitution.md` gains an **App NFR
  Baseline** table with pack-appropriate categories (Load Time/Bundle
  Size/Interactivity/Accessibility for frontend-spa; Cold Start Time/
  Offline Sync Latency/Crash-Free Rate/App Size for mobile), wired into
  each pack's `specify.prompt.md`. The shared `specify-srd.prompt.md`
  NFR-baseline-reference logic is now pack-agnostic wording ("Service NFR
  Baseline" or "App NFR Baseline" depending on pack — same mechanism)
- **New living document — frontend-spa + fullstack**:
  `.specify/service/component-library.md` catalogs shared/reusable
  components used across multiple features. `component-spec.md`'s
  "Shared Components Used" section now lists only component name +
  this feature's usage purpose, pointing to the library for the full
  prop/event/accessibility spec — never restated per feature.
  `specify-doc.prompt.md`'s living-doc walk-and-diff mechanism now covers
  this document alongside `data-model.md`/`security-design.md`
- **frontend-spa, mobile, fullstack, universal**: `release.prompt.md`'s
  Deployment Plan and Post-Deploy Smoke Test now reference
  `docs/runbook/local-setup.md` as the standard, established-once
  strategy instead of re-describing it every release — the same pattern
  `sdd-backend-service` got in `2.7.7`

### Verification
- `cli-python` pytest suite: 102/102 passed
- `packs/_shared/tests/test-setup.sh`: 15/15 passed (all project types,
  injection-class names, non-interactive execution)
- `packs/_shared/tests/assert-output.sh` against `examples/todo-api`: 33/33
  structural assertions passed

---

## [2.7.7] — 2026-07-06 (Framework content — sdd-backend-service, propagated to all 5 packs)

### Changed — the rest of the "reduce duplication across features" audit: reference instead of re-author

Follow-up to `2.7.6`. That release solved the clearest case (data model,
security baseline, API surface — full relocation to `.specify/service/`
with a walk-and-diff mechanism). This release covers the remaining
documents flagged in the same audit as "boilerplate shell + genuinely new
content, redescribed from scratch every feature" — a cheaper fix since
none of these needed relocation, just a reference instead of a restatement:

- **`srd.md` NFRs**: `constitution.md` Part 2 gains a **Service NFR
  Baseline** table (Performance/Availability/Throughput/Data Retention).
  The first feature to reach `/specify-srd` fills it from its own
  NFR-NNN rows; every feature after that writes "Baseline (constitution.md
  → Service NFR Baseline): {values} — applies to this feature too, no
  change" instead of restating the same numbers, and only gets its own
  NFR-NNN row for something genuinely different (a stricter target on one
  specific endpoint). A feature needing a different *baseline* (not an
  addition) triggers a Constitution Amendment instead of silently
  overwriting the row
- **`use-cases.md` Actor Registry**: an actor already defined in another
  feature's `use-cases.md` (same real-world role — "Ops Analyst",
  "Settlement Engine") is now reused, not re-derived. ACT-NNN numbering
  stays local to each feature's own file (Main/Alternate/Exception Path
  steps need a local ID to reference) — only the Name/Type/Description
  content carries over, noted as "(same as {prior-feature}'s ACT-NNN)"
- **`design.md`/`arch.md`/`hld.md` architecture shell**: Architecture
  Pattern, Layer Responsibilities, Cross-Cutting Concerns (auth, logging,
  error handling, idempotency, observability), and the System
  Context/Container diagrams are established once by the first feature
  to reach `/plan-design` (or `/plan-arch`/`/plan-hld` in separate mode)
  and referenced — "unchanged from {prior-feature}/design.md §1, see
  there" — by every later feature, instead of re-derived from scratch
  each time. Component diagrams, sequence diagrams, state machines, and
  DEC-NNN decisions stay fully per-feature, since those genuinely are new
  each time
- **`tasks.md` Phase A**: the "Project Scaffold + Dependencies" task
  gained the same check-before-regenerate guidance Phase F (Docker/k8s)
  already had in `2.7.6` — it's a once-per-service task, not
  once-per-feature; a later feature only adds a genuinely new dependency,
  it doesn't regenerate the build config
- **`release.md`**: Deployment Plan and Post-Deploy Smoke Test now point
  at `docs/runbook/local-setup.md` (already living as of `2.7.6`) for the
  standard steps/strategy instead of re-deriving them each release —
  only the release-specific migration version, feature flag, and target
  endpoint get filled in fresh
- Left alone, on purpose: `validate.md`, `clarify.md`, `checklist.md`,
  `changeset-template.md`, `constitution-amendment-template.md`,
  `jira-export.md` — genuinely one-off or already correctly incremental
- `specify-srd.prompt.md`, `specify-uc.prompt.md`, `plan-design.prompt.md`,
  `plan-arch.prompt.md`, `plan-hld.prompt.md`, and `tasks-template.md` are
  full-synced across all 5 packs — edited on the canonical `_shared/full/`
  source and propagated, since the new behavior is a no-op for any
  project without a prior feature to reference. `constitution.md`,
  `specify.prompt.md`, `release.prompt.md`, and `release-template.md` are
  pack-specific and were updated directly for `sdd-backend-service`
- Verified: full pytest suite (102 passed, no CLI code changed this
  release — pure prompt/template text), setup smoke tests (15/15),
  output-assertion tests against `examples/todo-api` (33/33), a live
  simulated upgrade from `2.7.6` confirming the new migration fires, and
  a dogfooding pass extending the same instant-payment/payment-dashboard
  scratch scenario from `2.7.6`: feature 2's `srd.md` and `use-cases.md`
  came out referencing feature 1's baseline/actors correctly instead of
  restating them

---

## [2.7.6] — 2026-07-04 (Framework content — sdd-backend-service, propagated to all 5 packs)

### Changed — data-model.md, security-design.md, and API design are now living, service-level documents

- Root problem: within one microservice, a second feature (e.g. a payment
  dashboard reading data a first feature — instant payment processing —
  already modeled) had no way to *extend* the existing schema/API surface.
  `/specify-doc data-model`/`security` and `/plan-design` §3 always
  generated fresh, per-feature copies — so a second feature either
  silently duplicated the first feature's tables/endpoints (drift risk:
  two documents claiming to define the same thing) or ignored them
  entirely (an index or endpoint that should exist had nowhere correct to
  live)
- `data-model.md`, `security-design.md`, and the API design section of
  `design.md` now live at `.specify/service/{doc}.md` — parallel to
  `.specify/memory/constitution.md`, generated once, then **extended by
  every later feature** instead of regenerated. When one already exists,
  the generating command walks it one unit at a time (one table, one
  threat entry, one endpoint) — SKIP / ADD / UPDATE, showing only the
  delta, one approval — the same discipline `/change` already uses for
  document updates, applied here to "a new feature touches an existing
  shared artifact" instead of "a requirement changed"
- `design.md` §3 (still per-feature) no longer contains the full API
  design — it's a short pointer to `.specify/service/api-spec.md` plus
  this feature's new/changed endpoints only
- Also fixed: `docs/runbook/local-setup.md`, `docs/openapi.yaml`, and
  `docker-compose.yml`/k8s manifests (already correctly living outside
  any feature folder) had no "already exists?" check before regeneration
  — a later feature could silently drop an earlier feature's additions.
  All three now have explicit check-before-regenerate guidance
- `specify-doc.prompt.md`, `plan-design.prompt.md`, and `tasks-template.md`
  are shared full-synced files across all 5 packs — this change was made
  on the canonical `_shared/full/` source and propagated everywhere, since
  the new behavior is a safe no-op for any project where these documents
  don't exist yet. `data-model-template.md`, `security-design-template.md`,
  `api-spec-template.md`, `runbook-template.md`, and `openapi-template.md`
  are pack-specific and were updated directly for `sdd-backend-service`
- Migration note for existing multi-feature projects: per-feature
  `data-model.md`/`security-design.md` files from before this release are
  **not** automatically merged — the next `/specify-doc data-model` (or
  `security`) run creates a fresh `.specify/service/` copy; reconcile any
  existing per-feature versions into it manually
- Verified: full pytest suite (102 passed — 2 new tests confirming
  `resolve_doc_path()` routes living docs to `.specify/service/`
  regardless of active feature), setup smoke tests
  (15/15), output-assertion tests against `examples/todo-api` (33/33), a
  live simulated upgrade from `2.7.5` confirming the new migration fires,
  and an end-to-end dogfooding pass: simulated two real features
  (instant-payment, payment-dashboard) against the new mechanism,
  confirmed the second feature's `design.md` stays a 37-line pointer
  (mentions the shared entity once, in the pointer note) instead of
  re-describing the schema, and ran the actual `sdd review approve --doc
  data-model --local` CLI command against the resulting
  `.specify/service/data-model.md` to confirm the whole path works, not
  just the path-resolution helper in isolation

---

## [2.7.5] — 2026-07-04 (Python CLI — path traversal fix)

### Fixed — sdd confluence / sdd cr / sdd jira accepted unvalidated feature names

- Found during a security audit: `sdd pr` and `sdd review` both route the
  `feature` name (from `--feature` or `manifest.yml`'s `project.feature`)
  through `safe_feature_path()` before touching disk, which rejects `../`
  traversal. `sdd confluence`, `sdd cr`, and `sdd jira` built the same
  `.specify/features/{feature}/...` path with a plain string join and no
  check at all — an inconsistency, not a designed difference
- Impact if a `manifest.yml` value like `project.feature:
  "../../../../tmp/pwned"` reached one of these commands unnoticed:
  `sdd confluence pull` would write pulled content to an arbitrary path
  outside `.specify/features/`; `sdd cr submit` / `sdd jira push` /
  `sdd jira sync` would read whatever file existed at the traversed path
  and push its contents to Confluence/Jira — arbitrary local file
  exfiltration to an external service, gated only on a teammate running
  the command without an explicit `--feature` override
- Fix: `confluence.py`, `cr.py`, and `jira.py` now call the same
  `safe_feature_path()` helper `pr.py`/`review.py` already used, with the
  same graceful `ValueError` → clean CLI error + exit 1 handling
- Also fixed a real bug in `safe_feature_path()` itself, found while
  strengthening it: the containment check compared resolved paths with a
  raw string-prefix test (`str(resolved).startswith(str(base))`), with no
  separator boundary — so a feature name resolving to a *sibling*
  directory that merely shares a string prefix with the base (e.g.
  `features-legacy` next to `features`) incorrectly passed validation.
  Replaced with `Path.relative_to()`, which correctly requires actual
  containment
- 14 new tests: direct coverage of `safe_feature_path()` (traversal
  rejection, the sibling-prefix bypass, and the normal-name path), plus
  regression tests calling `confluence.py`'s and `cr.py`'s actual path
  helpers to lock in the fixed call chain — 100 total, up from 86
- Verified beyond unit tests: reproduced the exact exploit scenario from
  the audit — a scratch project with `project.feature` set to a
  traversal string and a configured `integrations.yml`, then ran
  `sdd jira push` for real through Click's CliRunner. Confirmed clean
  rejection (exit 1, clear error message) where the old code would have
  attempted to read from the traversed path
- Version bumped to `2.7.5` in both CLIs (this fix is Python-only — the
  Node CLI has no `confluence`/`cr`/`jira` commands — but both package
  versions move together per this project's convention; the Node CLI's
  migration entry notes explicitly that nothing in it changed)
- Also verified: full pytest suite (100 passed), setup smoke tests
  (15/15), a live simulated upgrade from `2.7.4` confirming the new
  migration fires and lands on `2.7.5`

---

## [2.7.4] — 2026-07-04 (Framework content — all 5 packs — /change)

### Added — /change recommends a feature rename when scope fundamentally changes

- Previously, `/change` would happily regenerate `context.md`'s content
  to reflect a broadened or narrowed scope (via RERUN, with a
  `.pre-CR-{NNN}.md` backup), but never touched the feature's identity —
  `manifest.project.feature`, `context_file`, and the
  `.specify/features/{feature}/` directory name stayed whatever they were
  at `sdd init` time. A feature originally scoped as a single fixed
  `pain001-pacs008-parser` conversion could get generalized via CR into a
  generic ISO 20022 parser, and the folder/manifest would still say
  `pain001-pacs008-parser` — accurate document content, stale plumbing
- `change.prompt.md` now has a new "Special handling — context.md" check:
  after a RERUN or scope-touching UPDATE is approved, it looks for two
  signals together — the new §1 description no longer contains the
  specific nouns the current feature slug was named after, AND the walk
  plan already marked `brd.md`/`use-cases.md` as PRIMARY impact (a
  detail-level CR rarely reaches that far). If both fire, it recommends
  a new slug and asks before doing anything
- On approval, performs the rename as part of the same CR: `git mv` the
  feature directory and context file(s), updates `manifest.yml`, greps
  for any leftover hardcoded references to the old slug, and notes that
  already-pushed Jira/Confluence pages stay linked under the old name
  (local rename doesn't follow them there)
- `changeset-template.md` gained a "Feature renamed" row in §1 Change
  Description (`{old-slug} → {new-slug}`, or "No") so the rename is part
  of the CR's permanent audit trail, not just a chat message
- `change.prompt.md` is now tracked in `_shared/full/` (previously
  identical across all 5 packs by coincidence, same gap `create-context`
  had before it was added to shared tracking)
- Bumped the unified version to `2.7.4` with a matching migration entry
  in both CLIs
- Verified: full pytest suite (86 passed), setup smoke tests (15/15),
  output-assertion tests against `examples/todo-api` (33/33), a live
  simulated upgrade from `2.7.3` confirming the new migration fires and
  lands on `2.7.4`, and `sdd --version` / `SDD_VERSION` both printing
  `2.7.4` in both CLIs

---

## [2.7.3] — 2026-07-04 (Both CLIs — version scheme unified)

### Changed — One version number instead of two

- Previous releases tracked two separate numbers: the installed CLI
  package version (`sdd --version`) and `SDD_VERSION` (a manifest-schema
  counter used only by `sdd upgrade`). They were allowed to differ on
  purpose — 2.7.2 (package) vs 2.7.1 (schema) — which was correct but
  reliably confusing: every manifest.yml showed a different number than
  `sdd --version` did, with no obvious reason why
- `SDD_VERSION` is no longer a separate hardcoded constant. Both CLIs now
  derive it directly from the package's own version — `manifest.py`
  imports `sdd.__version__`; `manifest.js` reads `package.json` via
  `createRequire`, the same pattern `bin/sdd.js` already used for
  `sdd --version`. One source of truth per CLI; `sdd --version` and a
  freshly generated `manifest.yml`'s `sdd_version` field can no longer
  drift apart
- Added a `2.7.1 → 2.7.3` migration entry (both `upgrade.py` and
  `upgrade.js`) so existing projects on the old two-counter scheme land
  on the unified version cleanly, with a note explaining why
- Bumped the shipped `sdd_version` default in all 5 packs' `manifest.yml`
  and the `PACK-SPEC.md` example to `2.7.3` to match
- Practical implication going forward: every release — including a pure
  prompt-wording tweak — now bumps this one number, and ships as a new
  CLI release. There's no longer a lower-ceremony "content-only" bump
  that skips a PyPI/npm publish
- Verified: full pytest suite (86 passed) — the migration-chain tests
  added in the previous release already loop-to-convergence rather than
  hardcode a step count, so they needed no changes; setup smoke tests
  (15/15); a live simulated upgrade from a `2.7.1` manifest confirming
  the new migration fires, lands on `2.7.3`, and a second `sdd upgrade`
  correctly reports "nothing to do"; confirmed `sdd --version` and
  `SDD_VERSION` both print `2.7.3` in both CLIs

---

## [SDD_VERSION 2.7.1] — 2026-07-04 (Framework content — all 5 packs — /create-context)

This bumps `SDD_VERSION` (the framework-content/manifest-schema version
tracked by `sdd upgrade`), which is a separate counter from the CLI
package version (`sddflow` on PyPI/npm, currently 2.7.2). `sdd upgrade`
now migrates existing projects from `2.7.0 → 2.7.1` and prints a note to
re-copy the pack for the updated `create-context.prompt.md`. New
`sdd init` / `setup.sh` runs are stamped `2.7.1` directly.

### Changed — /create-context now proposes defaults for Endpoints and NFRs instead of always saying MISSING

- Reported behavior: pasting raw notes into `/create-context` reliably
  produced `[MISSING — ask user]` for Endpoints and Non-Functional
  Requirements whenever the notes didn't explicitly spell them out —
  correct per the old spec, but it left the user staring at a blank
  section with nothing to react to instead of a draft to edit
- `create-context.prompt.md` Step 2 now has a third fill tier between
  "stated/implied" and "nothing to go on": for Endpoints and NFRs only, if
  nothing can be inferred, propose a generic starting point — Endpoints
  derived from action verbs in Key Flows (or one create+read pair per
  named Actor as a fallback), NFRs from the same illustrative baseline
  this pack's own templates already use as examples, scaled to
  `manifest.project.scope` (pilot vs mvp/full). Marked
  `(SUGGESTED DEFAULT — edit or confirm)` — a distinct marker from
  `(inferred — confirm)` so the user can tell a note-grounded guess apart
  from a generic placeholder
- All other sections (Actors, Business Rules, Constraints, Out of Scope,
  Open Questions, Tech Stack) are deliberately NOT given this treatment —
  there's no safe generic default for a business fact, and guessing one
  would read as fabricated rather than as a placeholder
- Step 3 (renamed Review Checklist) now splits into Group A (confirm/edit
  suggested defaults — Endpoints/NFRs) and Group B (still need your
  input — everything else), so review effort goes where it's actually
  needed instead of one undifferentiated missing-info list
- Updated Confluence and chat iteration messaging (Step 4) and the
  `Never Do` list to match; updated each pack's `HOW-TO-USE.md`
  `/create-context` description
- `create-context.prompt.md` is now tracked in `_shared/full/` (it was
  previously identical across all 5 packs by coincidence, not by sync —
  future edits should go through `_shared/full/.github/prompts/create-context.prompt.md`
  + `sync-blocks.sh` per the standard shared-file workflow)

---

## [2.7.2] — 2026-07-03 (Both CLIs — manifest header wording)

### Fixed — Manifest header conflated CLI package version with schema version

- `manifest.yml`'s generated header read `# SDD Manifest — generated by
  sddflow v{SDD_VERSION}`, where `SDD_VERSION` is a separate manifest-schema
  constant (tracks what `sdd upgrade` migrates between) — not the installed
  `sddflow` package version. After the 2.7.1 packaging fix this became
  directly visible: `sdd --version` reports `2.7.2`/`2.7.1` while every
  freshly generated manifest said "generated by sddflow v2.7.0", reading as
  a version mismatch bug even though `sdd upgrade` behavior was unaffected
- Node CLI's header also still said `generated by sdd-init v...` — a stale
  reference to the package's original pre-rename name, missed by the
  earlier `sddkit` → `sddflow` sed sweep because it's a different literal
  string
- Fix: reworded both headers to `# SDD Manifest — schema v{SDD_VERSION}
  (generated by sddflow)` — the schema version and the tool name are both
  still present, but no longer imply the tool's own release version
- No functional change — `sdd_version:` field, `sdd upgrade` migration
  logic, and manifest schema itself are untouched

---

## [2.7.1] — 2026-07-03 (Python package only — pyproject.toml / PyPI release)

### Fixed — PyPI package shipped with zero bundled packs

- `sddflow` 2.7.0 published successfully to PyPI but was silently broken:
  `sdd init` failed with "SDD pack files not found" immediately after
  `pip install sddflow`. Confirmed by downloading the live wheel and
  inspecting it directly — 28 files, none under `sdd/packs/`
- Root cause: `[tool.hatch.build.targets.sdist]` had no `artifacts`
  override, only the wheel target did. Hatchling's default file selection
  follows `.gitignore`, so the sdist step silently dropped the (gitignored,
  generated-at-publish-time) `sdd/packs/` directory. `uv build` — the tool
  `publish.sh` uses — builds the wheel *from* that sdist, inheriting its
  missing packs; the wheel target's own `artifacts` line never got a
  chance to help because the files were already gone by then
  - This is also why it passed every check during 2.7.0's own release
    prep: verification there used `python -m build --wheel`, which builds
    directly from source and skips the sdist step (and this bug) entirely
- Fix: mirror the same `artifacts = ["sdd/packs/**"]` override onto the
  sdist target
- No content changes — packs, prompts, templates, and CLI behavior are
  identical to 2.7.0; this release exists purely to ship a wheel that
  actually contains them
- Verified against the real failure: downloaded the broken 2.7.0 wheel
  from PyPI to confirm it; reproduced with the real `uv build` (sdist and
  wheel both 0 pack files); applied the fix and reproduced success with
  the same command (sdist and wheel both 689 pack files); installed the
  fixed wheel into a fresh, isolated venv with no source tree present and
  ran `sdd init` for real — scaffolded correctly

---

## [2.7.0] — 2026-07-02

### Added — multi-host /address-review (GitHub, GitLab, Bitbucket, Azure DevOps)

- `/address-review` was entirely hardcoded to the `gh` CLI/API — found by
  auditing every doc after the PR-automation work below, since PR *creation*
  had just become host-agnostic while the very next workflow step (handling
  review comments) silently hadn't. Now uses the same `detect_host()` /
  `get_provider()` dispatch as `sdd pr create`.
- `git_host.py` providers gain `get_pr_number`, `list_unresolved_comments`,
  `reply_to_comment`, `resolve_thread`, `request_review`:
  - **GitHub** — rewritten on GraphQL (`reviewThreads`) instead of the plain
    REST comments endpoint, so listing now returns real thread IDs. This
    incidentally fixes a gap in the *previous* GitHub-only implementation,
    which had no reliable way to get a thread ID and documented itself as
    "if the thread ID is not available... skip resolution" — resolution now
    works consistently. Reply and re-review-request calls are unchanged
    (`gh api .../replies`, `gh pr edit --add-reviewer`)
  - **GitLab** — REST API (Discussions) via `GITLAB_TOKEN`
  - **Bitbucket** — REST API via `BITBUCKET_USERNAME`/`BITBUCKET_APP_PASSWORD`.
    No API-level thread resolution exists for Bitbucket Cloud comments —
    `resolve_thread` raises a clear "resolve manually in the UI" message
    that the CLI treats as a warning, not a failure (the reply still posts)
  - **Azure DevOps** — `az` CLI for PR/reviewer lookup, `az rest` (the
    CLI's own OAuth token against arbitrary Azure DevOps REST endpoints)
    for replying/resolving threads, since comment-on-existing-thread
    support varies across `az repos pr` subcommand versions
  - **Unrecognized/self-hosted** — every method raises with a clear
    "no automated X available for this git host" message; the prompt falls
    back to reading/replying in the host's web UI directly
- New CLI surface: `sdd pr comments`, `sdd pr reply --comment-id ...`,
  `sdd pr resolve --comment-id ...`, `sdd pr request-review --reviewer ...`
  — `address-review.prompt.md` and `.claude/commands/address-review.md`
  (shared, all 5 packs) now call these instead of raw `gh` commands. Also
  fixed a pre-existing drift between those two files (the `.claude/commands`
  version had a documented GraphQL mutation the `.prompt.md` version lacked)
  — both are now consistent and host-agnostic
- 30 new pytest cases (`test_git_host_review.py`) covering all 4 providers'
  5 new methods plus the unknown-host raise path
- Verified end-to-end beyond mocks: a real scratch repo confirmed graceful,
  correctly-worded fallback messages against unconfigured GitLab, Bitbucket,
  Azure DevOps, and self-hosted remotes; a fake `gh` binary on PATH plus a
  mocked host-detection call confirmed `sdd pr comments/reply/resolve/
  request-review` construct and send the correct real subprocess commands
  end-to-end (not just through mocked unit tests) for the GitHub path

### Added — multi-host PR automation (GitHub, GitLab, Bitbucket, Azure DevOps)

- `sdd pr create` no longer assumes GitHub. New `sdd/utils/git_host.py`:
  `detect_host()` reads `git remote get-url origin` and classifies it
  (github/gitlab/bitbucket/azure/unknown); `get_provider()` dispatches to a
  small per-host implementation. Branch creation, PR title/body generation,
  and the Jira comment-back are unchanged and still run exactly once,
  regardless of host — only `create_pr()` differs per provider:
  - **GitHub** — `gh pr create` (unchanged behavior, byte-for-byte)
  - **GitLab** — `glab mr create`, or the REST API via `GITLAB_TOKEN` if
    `glab` isn't installed (handles nested subgroup project paths)
  - **Bitbucket** — REST API via `BITBUCKET_USERNAME` +
    `BITBUCKET_APP_PASSWORD` (Bitbucket has no CLI as ubiquitous as gh/glab)
  - **Azure DevOps** — `az repos pr create` (handles both
    `dev.azure.com/{org}/{project}/_git/{repo}` and the older
    `{org}.visualstudio.com` URL forms, plus the SSH v3 form)
  - **Unrecognized / self-hosted** — same manual fallback as the historical
    "gh not found" path: branch is created and pushed, PR title/body printed
    to paste in manually. Nothing fails silently.
- 28 new pytest cases (`test_git_host.py`) covering URL parsing for every
  host/form combination and each provider's success/failure/fallback paths
  (subprocess and HTTP calls mocked — no network in CI)
- Per-host CI templates (all 5 packs): `bitbucket-pipelines.yml`,
  `.gitlab-ci.yml`, `azure-pipelines.yml` mirror the same rules as
  `.github/workflows/quality-gate.yml` (PR size, TASK-NNN/CHG-NNN reference,
  build+test+coverage per pack's tech stack, secret scan via gitleaks,
  dependency/SCA scan) in each host's native syntax. Only the file matching
  the repo's actual host is ever read — starter templates like the GitHub
  one, YAML-validated but not exercised against a live account of each host
  (this repo's own CI is GitHub-hosted)
- Docs: `integrations.yml.example` documents per-host auth setup;
  `HOW-TO-USE.md` "Workflow Mode" (all 5 packs), `cli-python/README.md`,
  and `PACK-SPEC.md` updated — `workflow_mode: github` was named for the
  common case but was always meant to mean "hosted PR + CI flow"; the
  docs now say so explicitly instead of implying GitHub-only

### Added — no-Jira review modes, Confluence sync on approval, progressive Jira push

#### Document review gates — three modes (all 5 packs)
- New shared block `review-gates.md` — "Document Review Gates — Three Modes"
  (chat / local / jira) replaces the Jira-only section in every pack's `CLAUDE.md`
- **chat** (default, zero setup): reviewer approves in chat; the `Status:` header
  in the `.md` is the authoritative gate in every mode
- **local**: `sdd review approve --doc X --local --by "…" --note "…"` records an
  audit trail in `.specify/.local-approvals.yml`
- `sdd review approve --local` now also flips the doc header to `Status: Approved`
  (safety net) and **updates the document's existing Confluence page** when a
  `confluence:` section exists in `integrations.yml` (`--no-confluence` to skip;
  a Confluence failure warns but never blocks the approval)
- Approval steps in all spec/plan/validate prompts now ask once for the approver
  name/role + optional comment, and degrade gracefully when the CLI is absent
- `submit-review` / `check-review` prompts: "No-Jira fallback" branch — chat-mode
  review via the `roles.yml` reviewer instead of a failing CLI call
- `integrations.yml.example`: documents that `confluence:` works standalone

#### `/jira-push` — progressive Jira export (all 5 packs)
- Pushes to the Jira REST API progressively: Epic after BRD, Stories after Use
  Cases/SRD, Tasks after `/task`, CHG tasks after `/change`
- Standalone script `.specify/scripts/jira-push.py` (auto-installs PyYAML);
  field mapping in `.specify/jira-config.yml` (`jira-config-template.yml`)
- Bare shorthand (`/jira-push epic`) and flag syntax (`/jira-push --level all --dry-run`)

#### Maintainer repo
- MIT `LICENSE`
- CI workflow (`.github/workflows/ci.yml`): shared-sync drift check, YAML
  validation, Python/Node CLI sanity, and the setup smoke-test suite
- Onboarding docs consolidated; `OWNER-GUIDE.md` refreshed

### Changed — package renamed to `sddflow` (two-step: sdd-init → sddkit → sddflow)

- First renamed `sdd-init` → `sddkit` before any publish, since `sdd-init` on
  npm belongs to an unrelated third-party package and neither registry had
  been published to yet
- `sddkit` was then rejected by a live `bash publish.sh` upload: PyPI's
  anti-typosquat check flagges it as too similar to two already-registered
  packages, `sdkit` and `sdd-kit` (a same-or-one-edit-distance name is
  blocked even though `sddkit` itself was never taken — confirmed via the
  PyPI JSON API returning 200 for both). Nothing was actually published
  under `sddkit` — the upload fails before PyPI accepts anything, so no
  cleanup was needed
- Renamed again to **`sddflow`**, checked this time for both exact
  availability *and* lexical distance from anything existing, on PyPI and npm
- The command users type is **unchanged** throughout: `sdd` (like
  `pip install httpie` → `http`) — every `sdd …` reference in prompts, docs,
  and CI stays valid regardless of which package-name iteration
- Updated: pyproject.toml / package.json names, all install instructions,
  publish.sh, manifest generation header, scaffold error hints

### Fixed — npm install instructions were unsafe

- The `sdd-init` name on npm is owned by an **unrelated third-party package** —
  all 16 `npm install -g sdd-init` instructions across READMEs, HOW-TO-USE, and
  SPEC-KIT-COMPARISON replaced with from-source install
  (`npm install -g ./Universalguide/cli`) plus an explicit warning
- Root README: "not on PyPI yet" note with the git-subdirectory pip install
  fallback until the first release is published
- Publishing note: build the Python package via `cli-python/publish.sh` only —
  it bundles `packs/` into the wheel first; a bare `python -m build` produces a
  wheel without packs and a broken `sdd init`

### Added — test coverage and second worked example

- `cli-python/tests/` — 29 pytest unit tests: review approval helpers (header
  flip incl. DRAFT/Proposed/word-boundary cases, local approvals, path-escape),
  the full upgrade migration chain (connected, self-stamping, re-run hint),
  config-init template validity, and a guard that the shipped
  integrations.yml.example agrees with the CLI's doc-key vocabulary and has
  strictly increasing review sequences. Runs in CI (python-cli-sanity job)
- `examples/habit-tracker-web` — second worked example: frontend-spa, pilot,
  **unified** plan mode (design.md with Mermaid + ADRs), including the new
  pilot `smoke-tests.md` artifact — the opposite pipeline half from todo-api;
  passes all 33 output assertions and runs in CI

### Added — design-decision pass (gap review G8–G14)

- `/validate` gains §4b Indicative Effort: T-shirt size (S/M/L/XL) per FR with
  effort driver, so the PO signs off with an effort signal in view — indicative
  only, story points still come at `/task` (template + all 5 pack prompts)
- NFR budget allocation: design-template §3.5 and hld-template §6 now split each
  measurable NFR target across critical-path components into testable budgets
- `/change` cross-cutting security rule: changes touching auth, personal data,
  retention, or new integrations promote security-design.md to PRIMARY in the
  document walk regardless of CR type — TH-NNN table refreshed before tasks
- `sdd-universal` constitution Part 1: applicability-by-project-type note maps
  service-shaped rules (controllers, hexagonal, error handler) onto cli,
  library, data-ml, frontend, and mobile equivalents
- `quality-gate.yml` (all packs): documented, commented-out `perf-gate` job —
  k6 thresholds from PERF-NNN tasks, opt-in at full scope
- Node.js CLI marked **maintenance mode** in root and cli READMEs (scaffolding
  only; new features land in the Python CLI; `sdd` binary collision warning)

### Added — developer-experience pass (gap review G1–G7)

- `sdd-universal` gains `.github/instructions/` (tests, domain, entrypoints) —
  language-neutral, path-scoped coding standards; it was the only pack without them
- `manifest.yml`: `testing_style: "paired"` now ships active (was commented out)
- Release Go-Live Gate: explicit preconditions (all tasks merged, UAT passed,
  §7 Rollback Plan filled — rehearsed at mvp+, monitoring in place) checked
  before any Go decision, in both template and prompt (all 5 packs)
- TDD mode now produces test-first evidence: the failing test is committed
  separately (`test({scope}): red — {criterion}`); `/pre-review` gains angle H
  verifying the red commit when `testing_style: tdd`
- `/pre-review` gains angle G — threat-model conformance: diff checked against
  security-design.md §1 TH-NNN mitigations when the document exists
- Pilot scope now gets a QA artifact: `/task` generates a ≤10-case
  `smoke-tests.md` (TC-S-NNN from UC Main/Exception paths) instead of nothing;
  `/release` UAT scenarios draw from it
- `sdd config init` page_map updated to the plan_mode-aware doc keys
  (use-cases, design) — it was regenerating the pre-2.7.0 vocabulary

### Fixed — consistency pass (prompts, templates, review config)

- Review doc keys unified everywhere (`brd, use-cases, srd, design | arch/hld/adr, lld,
  tasks, runbook, release`): submit-review and check-review prompts and CLI help had
  three different vocabularies; `integrations.yml.example` lacked `use-cases`/`design`
  entries so `sdd review submit --doc design` failed in unified mode (the default);
  example's ADR sequence was after LLD, contradicting the prompts (arch → hld → adr → lld)
- `document_reviews` example and default Confluence `page_map` are now plan_mode-aware
  (unified active by default, separate-mode block ready to uncomment)
- `/orchestrate` now supports `plan_mode: separate` — plan-arch/plan-hld/plan-adr steps,
  mode-branched dashboard and execution (previously unified-only)
- Status headers normalized: `use-cases-template.md` now uses the standard
  `> Version | Status: Draft |` header (was bare `Status: DRAFT`); `sdd review approve`
  flips Draft/Proposed case-insensitively (covers ADR lifecycle)
- `check-review` advance tree is plan_mode- and scope-aware (was hardcoded to the
  separate chain and skipped Use Cases)
- Worked example completed: `use-cases.md` (ACT/UC/MP-AP-EP) and `security-design.md` §1
  added to `examples/todo-api`; `assert-output.sh` accepts either plan mode's documents
  and now runs in CI (`output-assertions` job) — 33/33 passing
- `qa-testcases-template.md`: non-HTTP variant (Command/Input/Call) for cli, data-ml,
  library, and pipeline project types

### Fixed

- `setup.sh` / `setup.ps1` (all 5 packs) crashed in non-interactive runs (CI,
  piped input): `read` hit EOF under `set -euo pipefail` before defaults could
  apply. Prompts are now guarded — optional values fall back to defaults
  (scope=pilot, plan_mode=unified, detected type), required ones fail fast
  naming the missing flag. Smoke tests went from 13/15 failing to 15/15 passing
  and now run in CI
- `sdd-universal` was the only pack missing `CLAUDE.local.md` — added
- Stale maintainer docs: shared-blocks lists (`CLAUDE.md`, `OWNER-GUIDE.md`,
  `PACK-SPEC.md`), template counts, repository layout, testing instructions

---

## [2.6.0] — 2026-06-22

### Added — `/change` command, stakeholder template improvements, context feature-hint

#### `/change` — Type-aware, sequential change request command (all 5 packs)
- New command `/change {description}` works at **any SDLC stage**, raised by any role
- Classifies CR into one of 8 types: Business / Technical / Security / Data / UX / Performance / Operational / Defect
- Detects current stage from documents present in `.specify/features/{feature}/`
- Walks documents in dependency order, one at a time — reads actual content before deciding
- Per document: **SKIP** (no impact), **ANNOTATE** (upstream approved), **UPDATE** (shows BEFORE/AFTER diff, stops for approval), **RERUN** (backup + regenerate, stops for confirmation), **INCORPORATE** (not yet created — built in when generated)
- After all documents: proposes CHG-NNN implementation tasks, waits for approval before appending to `tasks.md`
- Saves changeset record to `.specify/features/{feature}/changesets/CR-NNN.md`
- New `changeset-template.md` — §1 type classification, §2 15-document walk table, §3 BEFORE/AFTER diffs, §4 CHG-NNN tasks, §5 approvals
- New `change.prompt.md` (8-step prompt) and `change.md` (Claude Code command) distributed to all 5 packs + `_shared/full`
- `change-rules.md` (all 5 packs) updated — CR type table, document walk actions table, Ripple-Forward Rule, updated dependency chain

#### Stakeholder-driven template improvements — 20 fixes across all packs
- **FIX-01** — Approvals tables pre-populated with correct role names per document (from `roles.yml`)
- **FIX-02** — `analyze-template.md` — Complexity Context line added after Overall Complexity rating
- **FIX-03** — `qa-testcases-template.md` — Type (E2E/Integration/Performance/Unit) and UAT Relevant (Yes/No) fields added to every TC-NNN; Coverage Summary updated
- **FIX-04** — `release-template.md` — Environment Prerequisites column added to UAT Plan table
- **FIX-05** — `release-template.md` — Smoke test rows: APM error rate check + monitoring alert check
- **FIX-06** — `release-template.md` — Security checklist requires evidence artefact reference, not just "Yes"
- **FIX-07** — `release-template.md` — Rollback Plan expanded to full step table (usable at all scopes)
- **FIX-08** — `security-design-template.md` — Evidence column added to §1 pilot security checklist
- **FIX-09** — `security-design-template.md` — Audit Trigger Events table added in §2 seeded from UC EP-NNN
- **FIX-10** — `release-template.md` — §3 Deployment Plan: strategy selection table (rolling/blue-green/canary with NFR thresholds) + steps table
- **FIX-11** — `validate-template.md` — §2 Business Requirements Review split into two columns: BA confirms FR mapping, PO confirms business intent
- **FIX-12** — `validate-template.md` — §6 Change Requests table added (CR-NNN tracking within the validate document)
- **FIX-13** — `use-cases-template.md` — [INFERRED: {basis}] marker instruction for AI-inferred steps
- **FIX-14** — `use-cases-template.md` — §4 UC Relationships expanded with diagram + includes/extends table
- **FIX-15** — `analyze-template.md` — Risk Register gains Mitigating Tasks column
- **FIX-16** — `feature-story-template.md` — BUFFER story (10% of total SP) added to every sprint plan
- **FIX-17** — `feature-story-template.md` — Cross-Sprint Dependencies table (blocking story relationships)
- **FIX-18** — `security-design-template.md` — CVSS (qualitative) column added to §3 STRIDE table; THR ≥ 7.0 blocks /release
- **FIX-19** — `brd-template.md` — §9 Investment Summary (T-shirt sizing, estimated cost, ROI/payback, cost of inaction)
- **FIX-20** — `brd-template.md` — §6 Regulatory expanded with domain-aware seeding (PCI-DSS, HIPAA, GDPR, SOX, FedRAMP)

#### `/create-context` — Feature-hint header (all 5 packs)
- Raw notes files can now start with `# specify: {sentence describing what you are building}`
- Agent extracts feature description → seeds §1 "What This Service Does" in context.md
- Agent derives kebab-case feature-name from the sentence and confirms before saving
- No more separate feature name declaration needed in chat

#### Documentation updates
- `SDLC-COMPLETE-GUIDE.md` (all packs) — rewritten: correct 5 SPECIFY sub-commands, 2 PLAN sub-commands (`/plan-design` + `/plan-lld`), `/create-context`, `/checklist`, `/change` added; dead commands (`/plan-arch`, `/plan-hld`, `/plan-adr`) removed; full checklist updated
- `CHANGE-GUIDE.md` (all packs) — rewritten: `/change` command as primary workflow, CR types, Ripple-Forward Rule, quality check options, CHG task implementation guide
- `examples/README.md` — updated command references to current commands

---

## [2.5.0] — 2026-06-22

### Fixed — 19 SDLC review findings

#### Traceability
- `change-rules.md` — dependency chain now includes `use-cases` between `brd` and `srd`; references `design` instead of `arch`; AI-8 updated to point to `/plan-design`; new "New actor/use case" change type
- `srd-template.md` — Functional Requirements table gains `UC Trace` column; References includes `use-cases.summary.md`
- `brd-template.md` — Stakeholders table gains `ACT-ID` column populated by `/specify-uc`; Version History section added

#### Testing
- `task.prompt.md` — Exception Paths (EP-NNN-X) from `use-cases.md` now generate TC-NNN test cases; NFRs with measurable thresholds generate PERF-NNN load test tasks; boundary value analysis added
- `qa-testcases-template.md` — new §7 Boundary & Exploratory Tests section

#### Security & Analysis
- `specify-doc.prompt.md` — full STRIDE/DREAD methodology for security doc generation (STRIDE per component, DREAD scoring, Critical/High/Medium/Low classification)
- `analyze-template.md` — new §9 Distributed Systems Consistency section covering race conditions, saga failures, eventual consistency windows, at-least-once delivery

#### Governance
- `CLAUDE.md` (all packs) — `/checklist` mandatory for mvp+, optional for pilot; Document Review Gates table corrected (`BRD → Use Cases → SRD → Design`); Upgrading Scope section added
- `constitution.md` (all packs) — Definition of Done table, Contract Testing row, Environments section (dev/mock/staging/prod) added to Part 1
- New `constitution-amendment-template.md` — tracks Part 2 version bumps with diff table and impact matrix

#### Documentation
- All pack `README.md` files — rewritten with new 5 SPECIFY sub-commands, 2 PLAN sub-commands, updated document inventory table, scope upgrade guidance
- All pack `GETTING-STARTED.md` files — updated command flow, `/specify-uc` explained, pilot and mvp+ paths shown correctly

---

## [2.4.0] — 2026-06-22

### Added — `/specify-uc` Use Case Specification command

- New command `/specify-uc` inserted between `/specify-brd` and `/specify-srd` in all 5 packs
- New `use-cases-template.md` with:
  - §1 Actor Registry (ACT-NNN: Primary / Secondary / System)
  - §2 Use Case Index
  - §3 Use Case Details per UC-NNN: Trigger, Preconditions, Postconditions, Main Path (MP), Alternate Paths (AP-NNN-X), Exception Paths (EP-NNN-X), Business Rules Applied, BR traces
  - §4 Use Case Relationships (extends / includes)
  - §5 Traceability Matrix (UC → BR)
- New `specify-uc.prompt.md` and `specify-uc.md` Claude command in all 5 packs
- `specify-srd.prompt.md` updated — gate now requires `use-cases.md` approved; SRD derives FR-NNN from UC MP/AP/EP paths; back-fills FR-NNN into use-cases.md
- `validate.prompt.md` updated — reads `use-cases.summary.md` alongside BRD and SRD
- `summary-rules.md` — added `use-cases.summary.md` required fields
- All `CLAUDE.md` — SPECIFY table now shows 5 sub-commands; command order includes `/specify-uc`

---

## [2.3.0] — 2026-06-22

### Added — Explicit `reading_mode` enforcement across all prompts

- `summary-rules.md` (all 5 packs) — added PROMPT INSTRUCTION block: agents check `manifest.yml → reading_mode` every time they read this file and apply the effective mode to all feature document reads
- `manifest.yml` (all 5 packs) — `reading_mode` uncommented and set to `"auto"` with inline comment explaining options
- All prompts (`validate`, `analyze`, `clarify`, `plan-lld`, `task`, `release`, `checklist`, `implement`, `specify-srd`) — `summary-rules.md` added to Before Starting; feature doc reads use AI-2 conditional format: `auto`/`summary` → `.summary.md` | `full` → full `.md`
- `summary-rules.md` — changed `full` mode description to "better quality / richer context at cost of tokens" (was "deep debugging / initial migration only")

### Changed
- All `CLAUDE.md` — AI-2 section explains three modes explicitly; notes that `reading_mode: "full"` in manifest provides maximum quality

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

#### Python CLI (`pip install sddflow` / `pipx run sddflow`)
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

#### Node.js CLI (unpublished — from source)
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
