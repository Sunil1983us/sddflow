# Changelog

All notable changes to the SDD Framework are documented here.

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
