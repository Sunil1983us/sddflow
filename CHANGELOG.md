# Changelog

All notable changes to the SDD Framework are documented here.

---

## [2.7.0] — 2026-07-02

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
