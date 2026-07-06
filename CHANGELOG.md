# Changelog

All notable changes to the SDD Framework are documented here.

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
