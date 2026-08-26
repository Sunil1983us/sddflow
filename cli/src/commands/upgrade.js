import { existsSync } from 'fs';
import chalk from 'chalk';
import inquirer from 'inquirer';
import { readManifest, patchManifest, MANIFEST_PATH, SDD_VERSION } from '../utils/manifest.js';

// Version migration table — describes what changed between pack versions.
// Extend this when releasing a new pack version.
// Exported (not just module-local) so tests/upgrade.test.js can assert the
// chain is connected and ends at SDD_VERSION -- this table is hand-mirrored
// from cli-python/sdd/commands/upgrade.py's MIGRATIONS on every release, and
// only that Python side ever had a test that would catch a broken from/to
// link in it.
//
// No per-entry migrate() function: every one of the 117 hops below has only
// ever stamped sdd_version (verified -- none has transformed manifest.yml
// content). migrateFn() below supplies that default; CUSTOM_MIGRATE exists
// for the rare future entry that genuinely needs to transform the manifest.
export const MIGRATIONS = [
  {
    from: null,          // null = pre-versioning (v1.x, no sdd_version field)
    to:   '2.0.0',
    description: 'Initial versioned release',
    notes: [
      'Added sdd_version field to manifest.yml for upgrade tracking',
      'setup.sh/setup.ps1 rewritten to use js-yaml — eliminates injection bugs',
      'Input validation: project/feature names with " are now rejected early',
      'Detection order fix: mobile (react-native) now checked before fullstack',
      'Cross-reference comment added to all 3 detection locations',
    ],
  },
  {
    from: '2.0.0',
    to:   '2.7.0',
    description: 'Content release — no manifest schema changes',
    notes: [
      '/change command: type-aware change requests at any SDLC stage',
      '/jira-push: progressive Jira export (Epic/Story/Task/CHG)',
      'Review gates: three modes (chat / local / jira) — Jira now optional',
      "sdd review approve --local also updates the doc's Confluence page",
      'setup.sh/setup.ps1 safe in non-interactive runs (CI, piped input)',
      'Re-copy the pack (or run sdd init over it) to pick up new prompt files',
    ],
  },
  {
    from: '2.7.0',
    to:   '2.7.1',
    description: 'Content release — no manifest schema changes',
    notes: [
      '/create-context: Endpoints and NFRs now get a proposed ' +
      'scope-appropriate starting default, marked ' +
      '(SUGGESTED DEFAULT — edit or confirm), instead of always ' +
      'falling back to [MISSING — ask user]',
      'Re-copy the pack (or run sdd init over it) to pick up the ' +
      'updated .github/prompts/create-context.prompt.md',
    ],
  },
  {
    from: '2.7.1',
    to:   '2.7.3',
    description: 'Version scheme unified — one number instead of two',
    notes: [
      'sdd_version no longer tracks a separate content/schema counter ' +
      '— it now always matches the installed sddflow package version ' +
      '(sdd --version), so this file and the CLI never show two ' +
      'different numbers again',
      'No framework content changed in this step beyond the version ' +
      'scheme itself',
    ],
  },
  {
    from: '2.7.3',
    to:   '2.7.4',
    description: 'Content release — no manifest schema changes',
    notes: [
      '/change: when a CR fundamentally broadens or narrows what a ' +
      'feature IS (not just a detail change) — e.g. a fixed ' +
      'pain.001→pacs.008 converter generalized into a generic ISO ' +
      '20022 parser — the agent now recommends renaming the feature ' +
      'slug to match, and will perform the rename (directory, ' +
      'manifest.yml, context file) if you approve',
      "changeset-template.md: added a 'Feature renamed' row to §1 " +
      'Change Description',
      'Re-copy the pack (or run sdd init over it) to pick up the ' +
      'updated .github/prompts/change.prompt.md and ' +
      'changeset-template.md',
    ],
  },
  {
    from: '2.7.4',
    to:   '2.7.5',
    description: 'Version alignment only — no Node CLI changes',
    notes: [
      'This release fixed a path-traversal gap in the Python CLI only ' +
      '(sdd confluence / sdd cr / sdd jira, which have no Node ' +
      'equivalent commands) — nothing in the Node CLI changed. Version ' +
      'bumped to keep sdd_version aligned across both CLIs.',
    ],
  },
  {
    from: '2.7.5',
    to:   '2.7.6',
    description: 'Content release — new .specify/service/ directory',
    notes: [
      'data-model.md, security-design.md, and the API design section of ' +
      'design.md are now living, service-level documents instead of being ' +
      'regenerated per feature — they live at .specify/service/{doc}.md ' +
      'and get extended/amended by every feature after the first one that ' +
      'needs them, instead of each feature getting its own independent ' +
      '(and eventually contradictory) copy',
      'docs/runbook/local-setup.md, docs/openapi.yaml, and ' +
      'docker-compose.yml/k8s manifests now have explicit ' +
      'check-before-regenerate guidance for the same reason',
      'If you already have per-feature data-model.md/security-design.md ' +
      'files from before this release, they are NOT automatically moved ' +
      'or merged — reconcile them into .specify/service/ yourself the ' +
      'next time you run /specify-doc data-model (or security)',
      'Re-copy the pack (or run sdd init over it) to pick up the updated ' +
      '.github/prompts/specify-doc.prompt.md and plan-design.prompt.md',
    ],
  },
  {
    from: '2.7.6',
    to:   '2.7.7',
    description: 'Content release — no manifest schema changes',
    notes: [
      "Constitution Part 2 gains a 'Service NFR Baseline' table — the " +
      'first feature to reach /specify-srd fills it from its own NFR-NNN ' +
      "rows; every later feature's srd.md references it instead of " +
      'restating the same performance/availability numbers, and only ' +
      'gives its own NFR-NNN row to something genuinely different from ' +
      'the baseline',
      '/specify-uc: an actor already defined in another feature\'s ' +
      'use-cases.md (same real-world role) is now reused, not ' +
      're-derived — numbering stays local per file, only the ' +
      'description content carries over',
      '/plan-design, /plan-arch, /plan-hld: architecture pattern, system ' +
      'layers, cross-cutting concerns, and the System Context/Container ' +
      "diagrams are established once by the first feature and " +
      "referenced ('unchanged from {feature}, see there') by every " +
      'later feature instead of being re-derived every time',
      'tasks.md Phase A (scaffold/dependencies) gained the same ' +
      'check-before-regenerate guidance Phase F already had',
      "release.md's Deployment Plan and Post-Deploy Smoke Test now " +
      'point at docs/runbook/local-setup.md for the standard steps ' +
      'instead of re-deriving the strategy each release',
      'Re-copy the pack (or run sdd init over it) to pick up the ' +
      'updated prompt files',
    ],
  },
  {
    from: '2.7.7',
    to:   '2.7.8',
    description: 'Content release — per-pack consistency fixes, no manifest schema changes',
    notes: [
      'Fixed: frontend-spa/mobile design.md §3 now names ' +
      'api-spec-template.md explicitly for the consumer-view branch — ' +
      'it existed but was never referenced by any prompt',
      "Fixed: CLAUDE.md Scope Reference table's API Spec row split into " +
      'provider (living, .specify/service/api-spec.md) vs consumer ' +
      '(per-feature, design.md §3) — the single unconditional row ' +
      'contradicted frontend-spa/mobile\'s own consumer-view carve-out',
      'Fixed: release-template.md in frontend-spa/mobile/fullstack said ' +
      'plain "runbook.md" — corrected to docs/runbook/local-setup.md, ' +
      'matching what /implement actually generates in every pack',
      'Fixed: frontend-spa/mobile CLAUDE.md and HOW-TO-USE.md marked ' +
      'data-model as "full only" — corrected to mvp+, matching the ' +
      'Scope Reference table and every other pack',
      'Fixed: universal CLAUDE.md/HOW-TO-USE.md referenced a stale ' +
      '/specify-doc api-spec command — api-spec moved to /plan-design §3 ' +
      'back in 2.7.6 but universal\'s docs were never updated',
      'data-model.md, security-design.md, and api-spec.md now carry the ' +
      'same living-document banners/framing in fullstack and universal ' +
      'as they already had in backend-service — the underlying ' +
      'living-doc mechanism (specify-doc.prompt.md, plan-design.prompt.md) ' +
      'was already shared/active in these packs, only the pack-specific ' +
      'template headers were missing it',
      "Added a 'Service NFR Baseline' table to fullstack (split " +
      'Backend/Frontend) and universal constitution.md, wired into each ' +
      "pack's own specify.prompt.md — same mechanism backend-service " +
      'got in 2.7.7',
      "Added an 'App NFR Baseline' table (pack-appropriate categories — " +
      'load time/bundle size for frontend-spa; cold start/offline sync ' +
      'latency for mobile) to frontend-spa/mobile constitution.md, wired ' +
      'into specify.prompt.md and the shared specify-srd.prompt.md ' +
      'NFR-baseline-reference logic (now pack-agnostic wording)',
      "Frontend-spa/mobile's data-model.md (Frontend State & Storage " +
      'Model / Local Data & Cache Model) and security-design.md are now ' +
      'explicitly living/app-level documents — same mechanism as ' +
      'backend-service\'s data-model.md, just describing state/storage ' +
      'and client-side security instead of a DB schema',
      'New living document for frontend-spa/fullstack: ' +
      '.specify/service/component-library.md catalogs shared/reusable ' +
      'components across features — component-spec.md\'s "Shared ' +
      'Components Used" section now points here instead of restating ' +
      'each shared component\'s full prop/event spec per feature',
      "release.md's Deployment Plan / Post-Deploy Smoke Test in " +
      'frontend-spa, mobile, fullstack, and universal now reference ' +
      'docs/runbook/local-setup.md as the standard, established-once ' +
      'strategy instead of re-describing it every release — the same ' +
      'pattern backend-service got in 2.7.7',
      'Re-copy the pack (or run sdd init over it) to pick up the ' +
      'updated prompt/template files',
    ],
  },
  {
    from: '2.7.8',
    to:   '2.7.9',
    description: 'Content release — no manifest schema changes',
    notes: [
      '/create-context gains a Feature Size Check (Step 1.5): before ' +
      'drafting context.md, it clusters the raw notes by actor+goal and ' +
      'flags it if 2+ independently-shippable capabilities were pasted ' +
      'in as one feature (e.g. "submit a payment" + "view a payments ' +
      'dashboard")',
      'If a split is found, the agent asks whether to treat it as one ' +
      'feature or build one slice at a time — on a split, the chosen ' +
      "slice's raw text continues through drafting as normal, and every " +
      'other slice\'s raw notes are saved to its own ' +
      '.specify/contexts/{slug}.raw.md so nothing is lost and it can be ' +
      'picked up later with /create-context',
      'Re-copy the pack (or run sdd init over it) to pick up the ' +
      'updated .github/prompts/create-context.prompt.md',
    ],
  },
  {
    from: '2.7.9',
    to:   '2.7.10',
    description: 'Bug fix — /change living-document handling, no manifest schema changes',
    notes: [
      "Fixed: /change's Stage Detection scanned only " +
      '.specify/features/{feature}/ for every document, but context.md ' +
      '(.specify/contexts/) and data-model.md/security-design.md/' +
      'api-spec.md/component-library.md (.specify/service/, living since ' +
      '2.7.6) never lived there — a CR could report all four as "not yet ' +
      'created" even when they existed and were approved, hiding the ' +
      "CR's real impact entirely",
      'Added: cross-feature impact check for living documents — before ' +
      '/change approves an UPDATE/RERUN to data-model.md/security-design.md/' +
      'api-spec.md/component-library.md, it now checks the Version History ' +
      'to see which feature last touched the specific unit being changed. ' +
      'If a different feature than the one raising the CR touched it, the ' +
      'proposal includes an explicit warning naming that feature and what ' +
      'to check — advisory, not a hard block',
      'changeset-template.md rows for the three/four living documents now ' +
      'note their real (.specify/service/) location, with a new line ' +
      'explaining how to record cross-feature impact in the walk table',
      'change-rules.md (all 5 packs) documents the same real file ' +
      'locations and the cross-feature impact rule',
      'Fixed the same stale-path bug in the test harness itself — ' +
      'packs/_shared/tests/assert-output.sh checked data-model.md/' +
      'security-design.md under the feature directory; it now checks ' +
      '.specify/service/ — this had been silently wrong since 2.7.6 ' +
      'because the only CI-exercised example runs at pilot scope, which ' +
      'skips those checks entirely',
      'Re-copy the pack (or run sdd init over it) to pick up the updated ' +
      '.github/prompts/change.prompt.md and changeset-template.md',
    ],
  },
  {
    from: '2.7.10',
    to:   '2.7.11',
    description: 'Multi-feature safety fixes for sdd jira push and sdd confluence push, plus /change --feature override, no manifest schema changes',
    notes: [
      'Fixed: LIVING_SERVICE_DOCS was missing "component-library" ' +
      "(frontend-spa/fullstack's shared component catalog) — " +
      'resolve_doc_path() routed it to .specify/features/{feature}/ ' +
      'instead of the correct .specify/service/, breaking sdd review and ' +
      'sdd confluence for that one doc type',
      'Fixed: sdd confluence push/draft/pull built a page title from only ' +
      '{project}, never {feature} — on a multi-feature project, two ' +
      'features pushing the same per-feature doc type (brd, use-cases, ' +
      'srd, design, lld, ...) upserted the SAME Confluence page and ' +
      'silently overwrote each other\'s content. _resolve_page_title() ' +
      'now substitutes {feature} into the title when the page_map ' +
      'template includes that placeholder (opt-in — existing configs ' +
      'without it see no title change, so no page gets orphaned), and ' +
      'always strips {feature} for living/service-level docs, which must ' +
      'stay ONE shared page regardless of which feature pushed them',
      'Fixed: sdd jira push/sync keyed Story/Task idempotency labels on ' +
      'sdd:{id} only, not qualified by feature — since STORY-NNN/TASK-NNN ' +
      'numbering restarts independently per feature (same as CR-NNN), two ' +
      "features' STORY-001 collided and the second feature's push " +
      "silently overwrote the first feature's Jira issue. Labels are now " +
      'sdd:{feature}:{id}, matching the Feature-level label ' +
      '(sdd-feature:{feature}) which was already feature-safe. This CLI ' +
      "(Node.js) doesn't implement sdd jira/confluence push itself — that " +
      'logic lives in cli-python only — but the manifest/pack side of ' +
      'this migration (integrations.yml.example, .gitignore) applies here too',
      'Added: /change --feature {slug} "description" — targets a feature ' +
      "other than manifest.yml's active one for this CR only, without " +
      'editing manifest.yml. Also fixed a related gap: the context.md-' +
      "rename special handling used to update manifest.yml's active " +
      'feature unconditionally on a rename — now only does so when the ' +
      "renamed feature is the one manifest.yml already points to",
      'Added: optional per-feature token/cost usage logging ' +
      '(.specify/features/{feature}/token-usage.md) — off by default, ' +
      'turns on by copying token-pricing.yml.example to token-pricing.yml',
      'jira-config.yml (legacy Jira integration path, contains credential ' +
      'placeholders) is now gitignored by default in all 5 packs',
      'Re-copy the pack (or run sdd init over it) to pick up the updated ' +
      '.specify/integrations.yml.example (per-feature page_map entries ' +
      'now include {feature}) and .gitignore',
    ],
  },
  {
    from: '2.7.11',
    to:   '2.7.12',
    description: 'Multi-feature safety fix for the progressive Jira export path (/jira-push, jira-push.py), no manifest schema changes',
    notes: [
      'Fixed: the progressive Jira export mechanism (/specify-brd, ' +
      '/specify-uc, /specify-srd writing docs/jira/epic.md, ' +
      'stories-draft.md, stories-refined.md; /jira-push and ' +
      '.specify/scripts/jira-push.py reading them and writing ' +
      'docs/jira/keys.yml) lived at one fixed global path, not scoped per ' +
      'feature like .specify/features/{feature}/ already is. On a ' +
      "multi-feature project, a second feature's BRD/UC/SRD approval " +
      "overwrote the first feature's staged Epic/Story export files on " +
      "disk, and pushing the second feature's Epic overwrote the first " +
      "feature's locally-tracked Jira key in keys.yml — corrupting " +
      "parent-link lookups for the first feature's Stories/Tasks the " +
      'next time it was touched. This is a more severe version of the ' +
      'same class of bug fixed in 2.7.11 for sdd jira push/sdd confluence ' +
      'push: there, the Jira issues themselves were protected by ' +
      'title-based matching in most cases; here, the local staging files ' +
      'had no per-feature isolation at all',
      'All docs/jira/ artifacts are now under docs/jira/{feature}/ — ' +
      'epic.md, stories-draft.md, stories-refined.md, keys.yml, ' +
      'stories.md, jira-import.csv — mirroring .specify/features/{feature}/',
      'Re-copy the pack (or run sdd init/sdd upgrade over it) to pick up ' +
      'the updated .specify/scripts/jira-push.py and the five ' +
      '.github/prompts/*.prompt.md files that write/read these paths ' +
      '(specify-brd, specify-uc, specify-srd, task, jira-push). Any ' +
      'docs/jira/*.md or keys.yml files from before this upgrade are not ' +
      'migrated automatically — move them into docs/jira/{feature}/ ' +
      'manually if you want to keep them.',
    ],
  },
  {
    from: '2.7.12',
    to:   '2.7.13',
    description: 'New sdd-micro pack for tiny/personal projects; no changes for existing packs’ manifest schema',
    notes: [
      'Added a 6th pack, sdd-micro, for scripts and small personal ' +
      "projects that don't need the full 11-command SDLC: just " +
      '/specify → [GATE-1] → /task → /implement. It intentionally ' +
      'does not follow PACK-SPEC.md (no BRD/Use Cases/SRD, no ' +
      'Validate/Analyze/Clarify/Design/Release) and is hand-maintained ' +
      'rather than wired into packs/_shared/sync-blocks.sh — see ' +
      'packs/sdd-micro/CLAUDE.md and WHY-SDD.md',
      "sdd init --pack sdd-micro (or the interactive picker's " +
      "'Choose from all packs…' option) now scaffolds it. Its " +
      'manifest.yml has no scope/project_type fields, so sdd init skips ' +
      'those two questions when it detects a micro-shaped manifest (no ' +
      'scope/project_type keys) — existing packs’ manifests are ' +
      'unaffected, they always carry both keys',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for the 5 existing packs',
    ],
  },
  {
    from: '2.7.13',
    to:   '2.7.14',
    description: 'New sdd dashboard command (Python CLI only, local status UI); no manifest schema changes',
    notes: [
      'The Python CLI (sddflow) added `sdd dashboard`: a local, ' +
      'read-only web UI over .specify/ — pipeline progress, task ' +
      'completion, and token usage per feature. Stdlib-only HTTP ' +
      'server, no new dependency. Unlike `sdd review status`, it needs ' +
      'no Jira/Confluence configuration — it reads the `Status:` header ' +
      "already written into each doc's .md file, the authoritative " +
      'gate in every review mode (chat/local/jira)',
      'This is a Python-CLI-only command — the Node CLI stays scoped to ' +
      'init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.14',
    to:   '2.7.15',
    description: 'sdd dashboard (Python CLI) gains Jira/Confluence links, LAN sharing, and an in-page doc viewer; no manifest schema changes',
    notes: [
      'The Python CLI (sddflow) dashboard now shows local Jira Epic/' +
      'Story/Task links and Confluence page links on each pipeline doc ' +
      '(no network call), plus an on-demand button to live-check ' +
      "sdd review submit's review-gate tickets (never cached locally), " +
      'and a View button that reads a doc straight from disk into the page',
      'New --host flag (default 127.0.0.1) lets teammates on the same ' +
      'network reach a shared instance via --host 0.0.0.0 — still one ' +
      'unauthenticated process on one machine, not a hosted service',
      'This is a Python-CLI-only change — the Node CLI stays scoped to ' +
      'init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.15',
    to:   '2.7.16',
    description: 'sdd dashboard (Python CLI) gains Approve + review comments (syncs to Confluence/Jira); no manifest schema changes',
    notes: [
      'New Approve button per document flips that doc\'s Status: header ' +
      'to Approved and records it in .specify/.local-approvals.yml — the ' +
      'same file/format `sdd review approve --local` already uses, ' +
      'mirrors to Confluence if configured, and posts a best-effort ' +
      'Jira comment on the review-gate ticket',
      'New comment box saves review comments locally ' +
      '(.specify/.dashboard-comments.json, feature-scoped) and ' +
      'best-effort mirrors to Jira; Confluence comment posting isn\'t ' +
      'implemented yet',
      '--host 0.0.0.0\'s warning now also covers write access — ' +
      'anyone reachable on the network can approve documents and post ' +
      'comments, not just view status',
      'This is a Python-CLI-only change — the Node CLI stays scoped to ' +
      'init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.16',
    to:   '2.7.17',
    description: 'sdd dashboard/CLI (Python CLI) Approve now also fills the doc\'s own "## Approvals" table, not just the Status: header; no manifest schema changes',
    notes: [
      'Bug fix: `sdd review approve --local` and the dashboard\'s Approve ' +
      'button previously only flipped a doc\'s Status: header to Approved ' +
      '— the "## Approvals" table further down the same file was left ' +
      'showing "Pending" even after approval',
      'Every Pending row inside the "## Approvals" section is now ' +
      'flipped to Approved with today\'s date filled in, scoped to that ' +
      'section only; running approve again also self-heals a doc whose ' +
      'header was already Approved by the old code',
      'This is a Python-CLI-only change — the Node CLI stays scoped to ' +
      'init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.17',
    to:   '2.7.18',
    description: 'Every document-generating command prompt now reminds the agent to log token usage, closing a gap where the instruction only lived in CLAUDE.md; no manifest schema changes',
    notes: [
      'Bug fix: token usage logging (opt-in via .specify/memory/' +
      'token-pricing.yml) was only documented in CLAUDE.md, read once at ' +
      'session start — no individual command prompt ever referenced it, ' +
      'so logging was unreliable even when token-pricing.yml existed',
      'New shared block token-usage-log-step now appears near the end ' +
      'of every document-generating command prompt (/create-context, ' +
      'every /specify-*, /plan-*, /task, /implement, /release, /change, ' +
      '/checklist, /validate, /analyze, /clarify) as a reminder at the ' +
      'point the agent is about to finish and report',
      'This is a prompt-content change, not a code change — it makes ' +
      'the existing token-usage-logging behavior more likely to ' +
      'actually run, it doesn\'t change what gets logged or how',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.18',
    to:   '2.7.19',
    description: '`sdd config init`/`set-secret` (Python CLI) can store Jira/Confluence credentials in the OS keychain instead of an env var; no manifest schema changes',
    notes: [
      'New credential_store option in ~/.sdd/config.yml: "keyring" ' +
      '(recommended) stores the credential in the OS-native secure ' +
      'store (macOS Keychain / Windows Credential Manager / Linux ' +
      'Secret Service); "env" is the pre-existing behavior and stays ' +
      'the default for profiles written before this version',
      'Closes a real usability gap — an env var exported in one ' +
      'terminal is invisible to an AI coding tool\'s own subprocess ' +
      'shell, which showed up as "can\'t connect to Jira/Confluence" ' +
      'even when the token itself was fine',
      'New `sdd config set-secret --profile {name}` command rotates a ' +
      'keychain-stored credential without re-running the whole wizard',
      'This is a Python-CLI-only change — the Node CLI stays scoped to ' +
      'init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.19',
    to:   '2.7.20',
    description: '`sdd jira push` (Python CLI) now matches `/jira-push`\'s content, and `sdd review submit` self-bootstraps the Feature/Epic and parents review tickets under it; no manifest schema changes',
    notes: [
      '`sdd jira push` previously created the Feature/Epic with a blank ' +
      'description and dropped Task Acceptance Criteria entirely, even ' +
      'though the parser already extracted it — both now carry real ' +
      'content, matching what the progressive `/jira-push` script ' +
      'already did',
      '`sdd review submit` now ensures the Feature/Epic exists before ' +
      'creating a document\'s review ticket (self-bootstrapping it from ' +
      'brd.md if `sdd jira push` hasn\'t run yet) and parents the review ' +
      'ticket under it, so review tickets and later dev Story/Task ' +
      'tickets converge on one Epic per feature',
      'Fixed a label collision: review-ticket idempotency labels were ' +
      'not feature-qualified (sdd-doc:{doc}), so a second feature\'s ' +
      'review submission for the same doc key could silently overwrite ' +
      'the first feature\'s ticket on a multi-feature project — now ' +
      'sdd-doc:{feature}:{doc}, matching the fix already applied to ' +
      'Story/Task labels',
      'This is a Python-CLI-only change — the Node CLI stays scoped to ' +
      'init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.20',
    to:   '2.7.21',
    description: '`sdd jira push` (Python CLI) now supports `--level` (progressive pushes) and `--cr` (CHG tasks); `/jira-push` and the standalone jira-push.py script are retired in favor of it; no manifest schema changes',
    notes: [
      '`sdd jira push` gained `--level {epic|story|task|chg|all}` (default ' +
      'all) and `--cr CR-NNN`, so it can push progressively at each SDLC ' +
      'gate exactly like the old standalone script did — Epic right ' +
      'after BRD approval, Stories after Use Cases/SRD, Tasks after ' +
      '`/task`, CHG tasks after `/change`. A level pushed on its own ' +
      'finds its parent live via Jira labels, so levels can be pushed ' +
      'in any order',
      'The `/jira-push` slash command is now a thin wrapper around this ' +
      'same CLI command instead of invoking a separate standalone ' +
      'script — `.specify/scripts/jira-push.py` and ' +
      '`.specify/templates/jira-config-template.yml` are removed from ' +
      'every pack. All Jira/Confluence configuration now lives in one ' +
      'place: `.specify/integrations.yml`',
      'This is a Python-CLI-only change — the Node CLI stays scoped to ' +
      'init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.21',
    to:   '2.7.22',
    description: 'Fix: Markdown tables (Python CLI\'s md_to_cf.py) were flattened into unreadable one-line paragraphs on every Confluence push; now render as real Confluence tables — no manifest schema changes',
    notes: [
      'md_to_cf.py (the Markdown → Confluence Storage Format converter ' +
      'used by every `sdd confluence push` / `sdd review submit` / ' +
      '`sdd review approve --local` / `sdd cr submit` call) had no table ' +
      'support at all — every "| cell | cell |" row fell through to the ' +
      'generic paragraph handler and was joined with spaces onto one ' +
      'line, destroying row/column structure. This affected nearly ' +
      'every document template, since most use Markdown tables',
      'GFM pipe tables are now parsed and rendered as real Confluence ' +
      '<table> markup, including alignment markers and inline ' +
      'formatting inside cells',
      'Re-push any already-published Confluence page to pick up ' +
      'correctly-rendered tables: `sdd confluence push --doc {name}` ' +
      '(or `--all`)',
      'This is a Python-CLI-only change — the Node CLI stays scoped to ' +
      'init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.22',
    to:   '2.7.23',
    description: 'Fix: JiraClient.search() (Python CLI) called the Jira Cloud search endpoint Atlassian removed (410 Gone), breaking every sdd review submit / sdd jira push idempotency lookup — no manifest schema changes',
    notes: [
      'Atlassian deprecated and removed GET /rest/api/3/search ' +
      '(announced Aug 2024) in favor of POST /rest/api/3/search/jql. ' +
      'Every CLI call that looks up an existing Jira issue by label — ' +
      'used by `sdd review submit`\'s Epic self-bootstrap, `sdd jira ' +
      'push`\'s upsert logic, and `sdd review check/status/apply` — went ' +
      'through the old endpoint and started failing with 410 Gone once ' +
      'Atlassian\'s rollout reached a given Jira Cloud instance',
      'Found via a real `sdd review submit` failure during pre-publish ' +
      'testing — the Confluence half succeeded but the Jira half ' +
      'failed, so the review fell back to chat approval with no Jira ' +
      'ticket created',
      '`JiraClient.search()` now POSTs to /rest/api/3/search/jql with ' +
      'jql/fields/maxResults in the JSON body, matching Atlassian\'s ' +
      'documented migration path',
      'This is a Python-CLI-only change — the Node CLI stays scoped to ' +
      'init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.23',
    to:   '2.7.24',
    description: 'Fix: document review commands never automatically read reviewer comments back and incorporated them — 9 command prompts across all 5 packs now delegate to the check/apply loop that already existed but was never wired in; no manifest schema changes',
    notes: [
      'Every document-generating command (specify-brd, specify-uc, ' +
      'specify-srd, specify-doc, plan-design, plan-arch, plan-hld, ' +
      'plan-adr, plan-lld) had its own hand-duplicated "on approval" ' +
      'step that only triggered on the user literally saying ' +
      '"approved", and treated NEEDS REVISION/PENDING as a plain yes/no ' +
      'confirmation prompt — it never read the reviewer\'s Jira comments ' +
      'back or updated the document',
      'Found via real end-to-end testing: after leaving comments on a ' +
      'submitted BRD review ticket, nothing in the /specify-brd flow ' +
      'ever fetched or acted on them automatically',
      'All 9 prompts now share one review-decision-step block: trigger ' +
      'on any check-in (not just the word "approved"), and on NEEDS ' +
      'REVISION actually read the comments, edit the document, and run ' +
      'sdd review apply',
      'Also fixes a real bug in packs/_shared/sync-blocks.sh: a ' +
      'brand-new shared block with zero existing matches aborted the ' +
      'whole sync script under set -e -o pipefail before the full-file ' +
      'copy loop ever ran',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.24',
    to:   '2.7.25',
    description: 'Fix: failed Jira parent-link calls (Python CLI) were silently swallowed with no trace — now print a diagnosable warning; no manifest schema changes',
    notes: [
      'Every set_parent() call site (Story/Task/CHG under Epic in `sdd ' +
      'jira push`, and the review ticket under the Epic in `sdd review ' +
      'submit`) was wrapped in a bare `except Exception: pass` — a ' +
      'failed parent link vanished with zero indication, even though ' +
      'the issue itself was created successfully',
      'Found via real testing: a review ticket and its Epic both ' +
      'appeared in Jira but were not linked, with no error message ' +
      'anywhere — root cause was a company-managed (classic) Jira ' +
      'project, where Story/Task-to-Epic linking uses the Epic Link ' +
      'custom field, not the "parent" field team-managed projects use',
      'All five call sites now print a warning naming the child/parent ' +
      'keys, the underlying error, and a pointer to `sdd config fields ' +
      '--project {key}` to find the right field — still never blocks ' +
      'the push/submit itself, just makes the failure visible',
      'This is a Python-CLI-only change — the Node CLI stays scoped to ' +
      'init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.25',
    to:   '2.7.26',
    description: 'Fix: token usage logging was placed after multi-turn approval-wait STOP points in 9 command prompts, so it almost never actually fired — moved to right after the document is saved; no manifest schema changes',
    notes: [
      '2.7.18 wired the token-usage-log-step reminder into every ' +
      'document-generating command, but in 9 of them (specify-brd, ' +
      'specify-uc, specify-srd, specify-doc, plan-design, plan-arch, ' +
      'plan-hld, plan-adr, plan-lld) it was placed after the ' +
      'Stakeholder Review and Approval section, which contains STOP ' +
      'points that defer continuation to a much later turn — the ' +
      'document was already fully saved well before that point, but ' +
      'the logging instruction sat unreachable behind those turns',
      'Found via real testing: token-pricing.yml existed and the ' +
      'feature was correctly enabled, but token-usage.md was still ' +
      'never being updated',
      'The block now sits immediately after the document is saved in ' +
      'all 9 affected prompts, guaranteeing it executes in the same ' +
      'turn as the actual generation work',
      'create-context.prompt.md and change.prompt.md were left as-is — ' +
      'they log at their genuine completion point after the user\'s ' +
      'iteration loop finishes, by design, since those commands aren\'t ' +
      'finished until then',
      'This is a prompt-content change, not a code change — the Node ' +
      'CLI stays scoped to init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.26',
    to:   '2.7.27',
    description: 'Fix: token usage logging still didn\'t fire even after the 2.7.26 placement fix, because agents relied on stale in-conversation memory of token-pricing.yml being absent instead of re-checking; no manifest schema changes',
    notes: [
      '2.7.26 fixed the structural/placement bug, but real testing ' +
      'showed the symptom persisted: the user confirmed via `ls -la` ' +
      'that token-pricing.yml demonstrably existed, yet the agent still ' +
      'reported "No token-pricing.yml, so skipping usage logging" on a ' +
      'later command in the same conversation',
      'Root cause was neither the opt-in gate nor placement — it was ' +
      'the model treating an earlier, in-conversation check (made ' +
      'before the user created the file) as still valid, rather than ' +
      'performing a fresh file read on each command',
      'token-usage-log-step.md now explicitly instructs: check now, ' +
      'with a fresh file read — not a memory of whether the file ' +
      'existed earlier in this conversation',
      'Hit the same content-precedence sync gotcha documented in the ' +
      '2.7.24 notes a second time: 13 files under packs/_shared/full/' +
      '.github/prompts/ have this block\'s content embedded directly, ' +
      'so editing only the block source file was not enough to ' +
      'propagate the fix to any pack',
      'This is a prompt-content change, not a code change — the Node ' +
      'CLI stays scoped to init/upgrade scaffolding, per its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.27',
    to:   '2.7.28',
    description: 'Fix: sdd dashboard (Python CLI) comment box lost typed text on the 5s auto-poll, and the per-feature grid cramped the Pipeline card\'s links column; no manifest schema changes',
    notes: [
      'User-reported via live testing: typing into the dashboard\'s ' +
      'inline comment form and pausing for a few seconds would wipe the ' +
      'field — the 5s auto-poll rebuilt the whole panel and the new DOM ' +
      'nodes came back empty and unfocused',
      'Fixed with a delegated input listener that mirrors keystrokes ' +
      'into client-side state (re-hydrated on every render) plus a ' +
      'focus/selection-range restore around the periodic DOM rebuild',
      'Also widened the per-feature grid breakpoint and let the Pipeline ' +
      'card span the full row so its links column (View/Approve/' +
      'comment-count/Jira+Confluence pills) no longer gets visually cut ' +
      'off at narrower widths',
      'Verified live with a Playwright-driven headless Chromium session ' +
      'against a real `sdd dashboard` instance, plus 3 new regression ' +
      'tests in test_dashboard.py',
      'This is a prompt/dashboard-content change, not a code change in ' +
      'this Node CLI — it stays scoped to init/upgrade scaffolding, per ' +
      'its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.28',
    to:   '2.7.29',
    description: 'Feature: sdd dashboard (Python CLI) gains a Full Pipeline section per feature -- complete command sequence, current step, and a plain-language next-action sentence; no manifest schema changes',
    notes: [
      'User-requested: the old Pipeline card only listed docs already on ' +
      'disk, with no sense of how much workflow remained, what to run ' +
      'next, or which steps were awaiting review vs. approved',
      'New status.py pipeline builder resolves the full ~20-step command ' +
      'sequence for this project\'s scope/plan_mode (or sdd-micro\'s ' +
      '3-command flow) against what\'s on disk into done/current/' +
      'upcoming/skipped per step, plus one next-action sentence',
      'Skipped steps stay visible (struck through, hover for why) instead ' +
      'of being silently omitted, mirroring CLAUDE.md\'s Scope Reference ' +
      'table; a doc awaiting review (exists but not yet Approved) shows ' +
      'as "current", not "done", so the review gate is visible in the ' +
      'stepper',
      'The old doc-list card is renamed Pipeline -> Documents to avoid ' +
      'clashing with the new full-width Full Pipeline card',
      'This is a prompt/dashboard-content change, not a code change in ' +
      'this Node CLI — it stays scoped to init/upgrade scaffolding, per ' +
      'its own README',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.29',
    to:   '2.7.30',
    description: 'Feature: sdd upgrade --sync-prompts (Python CLI) -- re-copies .github/prompts/ and .claude/commands/ from the current pack into an already-scaffolded project; sdd init now also records a `pack` manifest field',
    notes: [
      'Root cause of a real user report: prompt-content fixes shipped in ' +
      '2.7.24/2.7.26/2.7.27 never reached an already-scaffolded project, ' +
      'because sdd init copies .github/prompts/ and .claude/commands/ ' +
      'exactly once, at scaffold time, and sdd upgrade only ever patches ' +
      'manifest.yml\'s sdd_version -- it never re-syncs those files',
      'The Python CLI\'s new --sync-prompts flag diffs each file against ' +
      'the installed pack\'s current version, backs up anything it\'s ' +
      'about to overwrite to .specify/.prompt-sync-backups/{timestamp}/, ' +
      'and shows a preview + confirmation before writing',
      'This Node CLI does not yet implement --sync-prompts -- it stays ' +
      'scoped to the init/upgrade scaffolding it already covers, per its ' +
      'own README; this migration entry exists so both CLIs report the ' +
      'same sdd_version chain for a given manifest.yml',
      'New manifest.yml field: pack (string) -- written by sdd init on a ' +
      'fresh scaffold; this migration does not backfill it onto existing ' +
      'projects',
    ],
  },
  {
    from: '2.7.30',
    to:   '2.7.31',
    description: 'Feature: Jira Epic/Story/Task hierarchy overhaul (Python CLI) -- Epic at /specify, review tickets are Story issues parented to the Epic, Confluence+Jira submit together immediately, specify-uc pushes a draft Story per use case finalized by /task; no manifest schema changes',
    notes: [
      'User-requested redesign: Epic/Feature now created right after ' +
      '/specify (before any spec doc exists) instead of lazily on first ' +
      '`sdd review submit`; review tickets are issue type Story (not ' +
      'Task), parented to the Epic like dev Stories; sdd review submit ' +
      'pushes Confluence and creates the Jira Story together ' +
      'immediately, replacing the old two-stage draft-then-submit flow; ' +
      'a new `sdd jira push --level uc-draft` creates one placeholder ' +
      'Story per UC-NNN right after /specify-uc, which /task finalizes ' +
      'in place for any story that traces 1:1 back to a single use case',
      'This Node CLI does not implement any of these Jira/Confluence ' +
      'commands -- it stays scoped to init/upgrade scaffolding, per its ' +
      'own README; this migration entry exists so both CLIs report the ' +
      'same sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.31',
    to:   '2.7.32',
    description: 'Feature: per-issue-type Jira project key overrides (Python CLI) -- new integrations.yml jira.project_keys: {level: KEY} block lets an org keep its Epic/Feature in one Jira project and Stories/Tasks/reviews/CRs/CHGs in another; no manifest schema changes',
    notes: [
      'User-requested: an org can have a different Jira project key per ' +
      'issue type (e.g. Epic under "SUN", Story/Task under "SUNT"); ' +
      'JiraConfig gained project_keys: dict + a key_for(level) method ' +
      'that falls back to the single project_key for any level not ' +
      'listed, so existing integrations.yml files are unaffected',
      'Cross-project caveat (documented, not a bug): Jira\'s parent/' +
      'Epic-Link field generally does not support linking issues across ' +
      'different Jira projects on the standard REST API -- if ' +
      'project_keys puts a child level in a different project than its ' +
      'parent, the child issue is still created but the parent link may ' +
      'silently fail to appear in Jira; the CLI\'s existing ' +
      '_warn_parent_link_failed() safety net surfaces this as a warning ' +
      'rather than swallowing it',
      'This Node CLI does not implement any of these Jira/Confluence ' +
      'commands -- it stays scoped to init/upgrade scaffolding, per its ' +
      'own README; this migration entry exists so both CLIs report the ' +
      'same sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.32',
    to:   '2.7.33',
    description: 'Feature: per-level custom field ID overrides + fixed team field (Python CLI) -- new integrations.yml jira.custom_fields_by_level: {level: {field: id}} block overrides the common custom_fields mapping per level, and base_fields.team stamps a fixed team name/ID on every issue created; no manifest schema changes',
    notes: [
      'User-requested follow-on to 2.7.32\'s project_keys: a level\'s ' +
      'issues living in a different Jira project (via project_keys) ' +
      'almost always means different custom field IDs too, not just a ' +
      'different project key; JiraConfig gained custom_fields_by_level: ' +
      'dict + a fields_for(level) method that merges it over the common ' +
      'custom_fields mapping, falling back per-key -- existing ' +
      'integrations.yml files are unaffected',
      'JiraConfig also gained team: str | None (from base_fields.team) ' +
      '-- one fixed value stamped on every issue this CLI creates via ' +
      'whichever custom field "team" maps to, not something that varies ' +
      'per story/task',
      'This Node CLI does not implement any of these Jira/Confluence ' +
      'commands -- it stays scoped to init/upgrade scaffolding, per its ' +
      'own README; this migration entry exists so both CLIs report the ' +
      'same sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.33',
    to:   '2.7.34',
    description: 'Fix: sdd review submit / sdd cr submit were silently skipping base_fields.labels and the team stamp (Python CLI) + new jira.parent_field_by_level per-level override, same pattern as project_keys/custom_fields_by_level; no manifest schema changes',
    notes: [
      'A user-requested field audit across every Jira API call site ' +
      'found that review_submit() and cr_submit() hand-build their ' +
      '`fields` dict directly instead of routing through jira.py\'s ' +
      '_upsert_issue(), and had silently dropped base_fields.labels and ' +
      'never applied base_fields.team, unlike every Epic/Story/Task/CHG ' +
      'issue -- both are now fixed to apply the same labels/team logic',
      'New JiraConfig.parent_field_by_level: dict + parent_field_for(level) ' +
      'method mirrors key_for()/fields_for() from 2.7.32/2.7.33 -- lets an ' +
      'org whose Story/Task Jira project needs a different parenting ' +
      'mechanism than the Epic\'s project (e.g. next-gen "parent" field vs. ' +
      'a classic project\'s Epic Link custom field) express that per level',
      'This Node CLI does not implement any of these Jira/Confluence ' +
      'commands -- it stays scoped to init/upgrade scaffolding, per its ' +
      'own README; this migration entry exists so both CLIs report the ' +
      'same sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.34',
    to:   '2.7.35',
    description: 'Feature: Confluence page hierarchy Project -> Feature -> doc pages (Python CLI) + fix: document_reviews.confluence_page titles never had {feature} substituted, only {project}, so two features submitting the same doc type silently overwrote each other\'s Confluence page; no manifest schema changes',
    notes: [
      'User-requested nested Confluence page structure: every page now ' +
      'nests under parent_page_id -> a Project container page -> a ' +
      'Feature container page, created idempotently. Confluence enforces ' +
      'page-title uniqueness per SPACE, not per parent page, so nesting ' +
      'is a navigation convenience only -- {feature} must stay in every ' +
      'per-feature page title regardless of where it sits in the tree',
      'Real bug fixed: document_reviews.confluence_page (used by sdd ' +
      'review submit) only ever substituted {project} in its title, ' +
      'never {feature} -- two features submitting the same doc type for ' +
      'review would silently overwrite each other\'s Confluence page. ' +
      'This is the same collision class already fixed for page_map ' +
      '(used by sdd confluence push/draft), just never applied here',
      'This Node CLI does not implement any of these Jira/Confluence ' +
      'commands -- it stays scoped to init/upgrade scaffolding, per its ' +
      'own README; this migration entry exists so both CLIs report the ' +
      'same sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.35',
    to:   '2.7.36',
    description: 'Feature: Confluence diagram-macro rendering modes mermaid-app/plantuml-macro (Python CLI) -- new confluence.diagrams: config block routes ```mermaid/```plantuml fences through an installed Confluence app\'s macro instead of the plain code-block rendering; no manifest schema changes',
    notes: [
      'User-reported: Mermaid diagrams pushed to Confluence only ever ' +
      'showed as plain code text -- Confluence has no native diagram ' +
      'renderer at all, and every fenced code block (regardless of ' +
      'language) was routed through Confluence\'s built-in "code" macro',
      'New DiagramsConfig (mode: none | mermaid-app | plantuml-macro, ' +
      'each with a configurable macro_name matching whatever Confluence ' +
      'app the org has installed) -- a diagram fence with no matching ' +
      'mode/macro configured always falls back to the plain code-block ' +
      'rendering, never crashes or emits a broken macro reference',
      'Two more modes (local-svg, markdown-macro) were researched and ' +
      'explicitly deferred pending further evaluation/testing, not ' +
      'shipped in this release',
      'This Node CLI does not implement any of these Jira/Confluence ' +
      'commands -- it stays scoped to init/upgrade scaffolding, per its ' +
      'own README; this migration entry exists so both CLIs report the ' +
      'same sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.36',
    to:   '2.7.37',
    description: 'Feature: Confluence local-svg diagram mode (Python CLI) -- ```mermaid fences can now be rendered to SVG entirely offline (no browser, no Node.js, no network call, no Confluence app) and attached to the page as an image; no manifest schema changes',
    notes: [
      'Completes the local-svg mode deferred in 2.7.36 -- that release ' +
      'shipped mermaid-app/plantuml-macro, both of which require an ' +
      'installed Confluence app; this release adds the offline option ' +
      'for orgs that don\'t have or can\'t install one',
      'Backed by the optional mmdr package (Rust-based, ~18MB, zero ' +
      'further Python dependencies), verified against the real Mermaid ' +
      'diagram types SDD templates generate (flowchart, sequenceDiagram, ' +
      'classDiagram, erDiagram) before being chosen over a JS-engine ' +
      'candidate that failed on flowchart stadium-shape nodes and on ' +
      'classDiagram entirely',
      'Every failure mode (missing optional dependency, invalid diagram ' +
      'source, failed attachment upload) falls back to something safe ' +
      'rather than crashing the whole document push',
      'This Node CLI does not implement any of these Jira/Confluence ' +
      'commands -- it stays scoped to init/upgrade scaffolding, per its ' +
      'own README; this migration entry exists so both CLIs report the ' +
      'same sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.37',
    to:   '2.7.38',
    description: 'Feature: Virtual Team persona hints on the sdd dashboard Full Pipeline stepper (Python CLI) -- each step owned by a named team member (Maya, Rex, Ava, Leo, Kai, Quinn, Riley) shows a name badge and a ready-to-type natural-language ask; no manifest schema changes',
    notes: [
      'The dashboard Full Pipeline stepper showed only raw slash ' +
      'commands -- this adds a link back to the CLAUDE.md "Virtual Team ' +
      '— Address by Name" convention, where addressing a team member by ' +
      'name (e.g. "Ava, design checkout") works identically to running ' +
      'the underlying slash command',
      'sdd-micro has no Virtual Team at all, so it never gets a persona ' +
      'hint',
      'This Node CLI does not implement the dashboard -- it stays scoped ' +
      'to init/upgrade scaffolding, per its own README; this migration ' +
      'entry exists so both CLIs report the same sdd_version chain for ' +
      'a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.38',
    to:   '2.7.39',
    description: 'Feature: extend Virtual Team persona hints to the dashboard Documents card and sdd review status (Python CLI); fix: awaiting-review docs no longer show a misleading creation-phrased persona ask; no manifest schema changes',
    notes: [
      'Extends 2.7.38\'s dashboard Full Pipeline persona hints to the ' +
      'Documents card\'s "what\'s next" line and to the terminal-only ' +
      '`sdd review status` (each non-Approved, non-Blocked row gains a ' +
      '"· ask {name}" hint)',
      'Fixed a bug found while extending: a doc awaiting review isn\'t ' +
      'waiting to be *created*, but the ask templates are all ' +
      'creation-phrased -- suppressed the ask specifically for that ' +
      'state rather than showing a misleading "create the BRD" for a ' +
      'BRD that already exists',
      'This Node CLI does not implement the dashboard or review status ' +
      'commands -- it stays scoped to init/upgrade scaffolding, per its ' +
      'own README; this migration entry exists so both CLIs report the ' +
      'same sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.39',
    to:   '2.7.40',
    description: 'Fix: review-driven document edits now bump the Version header and log Version History (prompt/template content only) -- no manifest schema changes',
    notes: [
      'Reviewer feedback (Jira comment, dashboard comment, or chat ' +
      'feedback) that causes a document edit now bumps its Version ' +
      'header and appends a Version History row, matching the discipline ' +
      '/change already used for post-approval changes -- previously the ' +
      'pre-approval review cycle never did this',
      'Also fixed a hardcoded "1.0" in the approval-logging Version ' +
      'History template that should have referenced the document\'s ' +
      'actual current version',
      'This Node CLI does not implement any document-review commands -- ' +
      'it stays scoped to init/upgrade scaffolding, per its own README; ' +
      'this migration entry exists so both CLIs report the same ' +
      'sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.40',
    to:   '2.7.41',
    description: 'Feature: sdd review check/apply now discover and acknowledge dashboard-left review comments in pure local mode (Python CLI); new sdd review comments command -- no manifest schema changes',
    notes: [
      'In pure local mode (no jira: configured), a dashboard comment used ' +
      'to land only in .dashboard-comments.json with no way for the agent ' +
      'to discover it except the user manually relaying it in chat -- ' +
      'sdd review check now falls back to reading that file directly, and ' +
      'sdd review apply acknowledges it instead of hard-requiring Jira/' +
      'Confluence to even run',
      'New sdd review comments --doc {doc} [--ack] command for explicit ' +
      'use outside the check/apply cycle',
      'This Node CLI does not implement any document-review commands -- ' +
      'it stays scoped to init/upgrade scaffolding, per its own README; ' +
      'this migration entry exists so both CLIs report the same ' +
      'sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.41',
    to:   '2.7.42',
    description: 'Docs consistency (Virtual Team + /taskstoissues in HOW-TO-USE.md, dangling CHANGELOG.md reference removed, workflow_mode wording propagated to frontend-spa/mobile/fullstack) + new Python-CLI test coverage -- no manifest schema changes',
    notes: [
      'Doc-only fixes across all 5 packs: removed a dangling CHANGELOG.md ' +
      'reference from README.md, documented the existing Virtual Team ' +
      '(address-by-name) feature and /taskstoissues command in ' +
      'HOW-TO-USE.md, and propagated workflow_mode (github/local) wording ' +
      'to the 3 packs whose CLAUDE.md/prompt files had not caught up with ' +
      'the docs already promising local-mode support',
      'This Node CLI does not implement sdd dashboard, sdd init, or sdd ' +
      'pr -- it stays scoped to init/upgrade scaffolding, per its own ' +
      'README; this migration entry exists so both CLIs report the same ' +
      'sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.42',
    to:   '2.7.43',
    description: 'Fix: sdd init no longer re-asks project type after a type-dedicated pack (backend-service/frontend-spa/mobile/fullstack) is chosen -- no manifest schema changes',
    notes: [
      'Choosing a type-dedicated pack (e.g. sdd-backend-service) used to ' +
      'still trigger a second project-type detection/select right after ' +
      'scaffolding, offering irrelevant choices like mobile/desktop for a ' +
      'project already identified by the pack choice',
      'New PACK_TO_TYPE reverse map (of scaffold.js TYPE_TO_PACK) pins ' +
      'projectType directly from the chosen pack for the 4 dedicated ' +
      'packs; sdd-universal is unaffected since it genuinely branches on ' +
      'project_type',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.43',
    to:   '2.7.44',
    description: "Fix: sdd dashboard's Full Pipeline flow no longer shows 'Constitution (Part 2)' as done before /specify has actually run (Python CLI) -- no manifest schema changes",
    notes: [
      'constitution.md is scaffolded for every project by sdd init, Part 2 ' +
      'full of {extracted from context}/{derived}/{date} placeholders -- ' +
      'the dashboard used to treat the file existing on disk as Part 2 ' +
      'being generated, showing a checkmark before /specify ever ran',
      'This Node CLI does not implement sdd dashboard -- it stays scoped ' +
      'to init/upgrade scaffolding, per its own README; this migration ' +
      'entry exists so both CLIs report the same sdd_version chain for a ' +
      'given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.44',
    to:   '2.7.45',
    description: "Fix: sdd dashboard crashed on every poll once a feature had a Jira progressive export (Python CLI) -- no manifest schema changes",
    notes: [
      "status.py's _local_jira_links() assumed keys.yml's epic/stories/" +
      'tasks fields were dicts with a jira_key field, but jira.py\'s ' +
      'actual writer produces a plain string for epic and flat ' +
      '{id: jira_key} dicts for stories/tasks -- fixed to parse both ' +
      'shapes defensively',
      'This Node CLI does not implement sdd dashboard or sdd jira push -- ' +
      'it stays scoped to init/upgrade scaffolding, per its own README; ' +
      'this migration entry exists so both CLIs report the same ' +
      'sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.45',
    to:   '2.7.46',
    description: 'Fix: a failed sdd review submit silently skipped the Confluence draft push and Jira Epic Business Objectives refresh -- no manifest schema changes',
    notes: [
      'submit-for-review-step.md (shared prompt block): a failed sdd ' +
      'review submit now falls through to a Confluence-only draft push ' +
      'instead of skipping Confluence entirely, and specify-brd.prompt.md ' +
      "now explicitly refreshes the Jira Epic via 'sdd jira push --level " +
      "epic' when review submit didn't run it as a side effect",
      'This Node CLI does not implement sdd review submit or sdd jira ' +
      'push -- it stays scoped to init/upgrade scaffolding, per its own ' +
      'README; this migration entry exists so both CLIs report the same ' +
      'sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.46',
    to:   '2.7.47',
    description: "Feature: cross-project Jira parent-link fallback via a 'Relates' issue link (Python CLI) -- no manifest schema changes",
    notes: [
      'When project_keys routes a level to a different Jira project than ' +
      "its parent, the CLI now falls back to a plain 'Relates' issue link " +
      '(works across projects, unlike parent/Epic-Link) instead of just ' +
      'printing a dead-end warning',
      'This Node CLI does not implement sdd jira push or sdd review ' +
      'submit -- it stays scoped to init/upgrade scaffolding, per its own ' +
      'README; this migration entry exists so both CLIs report the same ' +
      'sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.47',
    to:   '2.7.48',
    description: "Feature: dashboard's review-links check now also surfaces sdd review check --doc classification and reviewer comments (Python CLI) -- no manifest schema changes",
    notes: [
      "The dashboard's existing on-demand 'Check Jira/Confluence review " +
      "links' button now also classifies each document APPROVED / " +
      'NEEDS_REVISION / PENDING (same logic as sdd review check --doc) ' +
      'and shows Jira reviewer comments inline',
      'This Node CLI does not implement sdd dashboard -- it stays scoped ' +
      'to init/upgrade scaffolding, per its own README; this migration ' +
      'entry exists so both CLIs report the same sdd_version chain for a ' +
      'given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.48',
    to:   '2.7.49',
    description: 'Fix: silent Confluence diagram-render failures now print a warning naming the reason (Python CLI) -- no manifest schema changes',
    notes: [
      "A ```mermaid fence whose diagrams.mode failed to render (missing " +
      "mmdr package, invalid diagram source, or an app macro mode with " +
      "no macro_name set) previously fell back to a plain code block " +
      "with zero indication anything was wrong, indistinguishable from " +
      "diagrams.mode not being configured at all -- now prints a " +
      "warning naming the actual reason",
      'This Node CLI does not implement sdd confluence push/sdd review ' +
      'submit -- it stays scoped to init/upgrade scaffolding, per its ' +
      'own README; this migration entry exists so both CLIs report the ' +
      'same sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.49',
    to:   '2.7.50',
    description: 'Fix: Confluence diagram attachment uploads rejected with HTTP 415 due to a stale multipart Content-Type header (Python CLI) -- no manifest schema changes',
    notes: [
      "confluence_client.py's upload_attachment() (diagrams.mode: " +
      "local-svg) posts a multipart file upload on a shared session " +
      "that already carries a blanket Content-Type: application/json " +
      "header -- requests only computes its own multipart/form-data; " +
      "boundary=... header when no Content-Type is already present, so " +
      "every diagram attachment was silently rejected by Confluence " +
      "with 415 while the page content itself still saved fine",
      'This Node CLI does not implement sdd confluence push -- it stays ' +
      'scoped to init/upgrade scaffolding, per its own README; this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.50',
    to:   '2.7.51',
    description: "Feature: dashboard's per-document Jira review-gate pill now has a local, instant fallback mirroring Confluence's (Python CLI) -- no manifest schema changes",
    notes: [
      "The dashboard's Confluence pill always showed up locally, but the " +
      "Jira review-gate pill only appeared after clicking the live " +
      "'Check Jira/Confluence review links' button -- sdd review submit/" +
      "apply now record the ticket key to .specify/.jira-review-links.json " +
      "the same way Confluence pages are already recorded, so the pill " +
      "shows instantly instead of staying blank",
      'This Node CLI does not implement sdd review submit/sdd dashboard ' +
      '-- it stays scoped to init/upgrade scaffolding, per its own ' +
      'README; this migration entry exists so both CLIs report the same ' +
      'sdd_version chain for a given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.51',
    to:   '2.7.52',
    description: "Fix: dashboard's Full Pipeline 'Next:' text could contradict the pipeline diagram when an optional step (e.g. checklist at pilot scope) was consciously skipped (Python CLI) -- no manifest schema changes",
    notes: [
      "The dashboard's pipeline diagram could mark 'validate' as the " +
      "current step while the 'Next:' text still said 'Run /checklist' " +
      "-- checklist is optional at pilot scope and was never run, but a " +
      "later doc (validate.md) already existed. build_pipeline() now " +
      "treats an optional+not-yet-generated step as bypassed once a " +
      "later step exists on disk, instead of always picking the first " +
      "non-done step in list order",
      'This Node CLI does not implement sdd dashboard -- it stays scoped ' +
      'to init/upgrade scaffolding, per its own README; this migration ' +
      'entry exists so both CLIs report the same sdd_version chain for a ' +
      'given manifest.yml',
      'This migration only bumps sdd_version — no manifest.yml field ' +
      'changes for any pack',
    ],
  },
  {
    from: '2.7.52',
    to:   '2.7.53',
    description: "Feature: blocked documents (e.g. validate.md, on unresolved [NEEDS CLARIFICATION-NNN] markers) can collect reviewer answers via Jira/Confluence (Python CLI) -- no manifest schema changes",
    notes: [
      "[NEEDS CLARIFICATION] markers are now numbered locally per " +
      "document -- [NEEDS CLARIFICATION-NNN: {question}] -- matching " +
      "the [ASSUMPTION-NNN] convention already in use, giving every " +
      "marker a stable, doc-qualified ID a reviewer's Jira/Confluence " +
      "answer can cite exactly (e.g. 'brd:NC-002: 90 days')",
      "New sdd review push-questions / sdd review pull-answers commands " +
      "let a blocked document (e.g. validate.md, before it's ever " +
      "submitted for formal review) route its open questions through " +
      "Jira/Confluence and have answers patched back into brd.md/" +
      "use-cases.md/srd.md automatically",
      "This Node CLI does not implement sdd review push-questions/pull-" +
      "answers -- it stays scoped to init/upgrade scaffolding, per its " +
      "own README; this migration entry exists so both CLIs report the " +
      "same sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.53',
    to:   '2.7.54',
    description: "Fix: multi-line sdd review pull-answers replies were silently collapsed into one garbled line, so only the first item ever got parsed (Python CLI) -- no manifest schema changes",
    notes: [
      "Jira's rich-text comment editor stores each line a user types as " +
      "a separate paragraph node, not one paragraph with embedded " +
      "newlines -- _extract_text() previously joined every text run in " +
      "the whole comment with a single space, collapsing a real " +
      "multi-line reply (one 'brd:NC-NNN: answer' per line) into one " +
      "run-on line before the per-line answer parser ever saw it",
      "_extract_text() rewritten to preserve paragraph/heading/listItem " +
      "boundaries as newlines; also fixes review_check's printed " +
      "reviewer-comment display and the dashboard's Jira-comment view, " +
      "which both used the same helper",
      "This Node CLI does not implement sdd review pull-answers -- it " +
      "stays scoped to init/upgrade scaffolding, per its own README; " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.54',
    to:   '2.7.55',
    description: "Fix: sdd review pull-answers never patched a marker in any project whose brd.md/use-cases.md/srd.md predate the NEEDS CLARIFICATION-NNN numbering feature (Python CLI) -- no manifest schema changes",
    notes: [
      "validate.md's own §3a-BLOCKING scan only displays synthesized " +
      "{doc}:NC-{NNN} IDs for legacy unnumbered [NEEDS CLARIFICATION: " +
      "...] markers (order of appearance) -- it never writes those " +
      "numbers back into the source document, since scanning isn't " +
      "editing, so the exact-string patch search in any pre-existing " +
      "project never found a match",
      "New _number_legacy_markers() retroactively numbers any " +
      "unnumbered marker to match the numbering convention, wired into " +
      "review_pull_answers to run once per referenced doc before any " +
      "patch is attempted; new _normalize_doc_key() also maps the " +
      "'uc' -> 'use-cases' abbreviation some model runs used in " +
      "validate.md's Locations column",
      "This Node CLI does not implement sdd review pull-answers -- it " +
      "stays scoped to init/upgrade scaffolding, per its own README; " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.55',
    to:   '2.7.56',
    description: "Fix: sdd review pull-answers patched BRD/SRD/UC locally but never refreshed their existing Confluence pages (Python CLI) -- no manifest schema changes",
    notes: [
      "pull-answers now re-pushes each patched document's own Confluence " +
      "page immediately after patching, using the same _push_doc_page() " +
      "helper sdd review approve already uses -- previously only " +
      "validate.md's own page was ever touched by push-questions/" +
      "pull-answers, leaving BRD/SRD/UC's pages showing stale pre-answer " +
      "markers",
      "This Node CLI does not implement sdd review pull-answers -- it " +
      "stays scoped to init/upgrade scaffolding, per its own README; " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.56',
    to:   '2.7.57',
    description: "Guardrail: validate.prompt.md Step C no longer lets a document-level approval auto-check per-item §1-§4 confirmation checkboxes -- no manifest schema changes",
    notes: [
      "A prior agent session, chasing the analyze.prompt.md verify " +
      "gate's literal 'VALIDATE complete' string, bulk-checked every " +
      "unchecked confirmation box in validate.md's §1-§4 purely because " +
      "the document's Jira ticket was closed -- not because a named " +
      "reviewer actually addressed each specific item",
      "validate.prompt.md's Step C only ever specified updating the " +
      "header and the §5 Approvals table on approval; this migration " +
      "tightens the wording across all 5 packs to explicitly forbid " +
      "inferring §1-§4 item-level confirmations from a document-level " +
      "approval signal, and says what to do instead",
      "This Node CLI does not implement /validate itself (prompt-only " +
      "change, no code) -- this migration entry exists so both CLIs " +
      "report the same sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.57',
    to:   '2.7.58',
    description: "Feature: analyze.md and clarify.md can now go through the same Jira/Confluence review-gate flow as brd/srd/etc, a new 'validate' phase (Python CLI) -- no manifest schema changes",
    notes: [
      "Added document_reviews.validate/.analyze/.clarify entries to " +
      "integrations.yml.example (phase: validate, sequence 1/2/3), plus " +
      "matching page_map entries and Stakeholder Review and Approval " +
      "sections in analyze.prompt.md/clarify.prompt.md (all 5 packs) -- " +
      "each of the three is optional individually",
      "Fixed clarify-template.md's header (Status: OPEN -> Draft) so " +
      "the standard approval flip works for clarify.md the same way it " +
      "does for every other document",
      "This Node CLI does not implement sdd review submit/approve -- it " +
      "stays scoped to init/upgrade scaffolding, per its own README; " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.58',
    to:   '2.7.59',
    description: "Feature: Confluence pages for documents under Jira review now show a live Jira link + status banner, and page_map covers every generated doc type (Python CLI) -- no manifest schema changes",
    notes: [
      "sdd review submit/check/apply (Python CLI) now prepend an info/" +
      "success/warning panel to the document's Confluence page showing " +
      "the Jira ticket link and live status, refreshed on every command " +
      "that touches that document's review state",
      "page_map in integrations.yml.example gained entries for " +
      "qa-testcases, tasks, checklist, and the living/service-level docs " +
      "(data-model, security-design, api-spec, component-library), so " +
      "every generated doc type has a Confluence page available even " +
      "without a Jira review gate configured for it",
      "This Node CLI does not implement sdd review submit/approve -- it " +
      "stays scoped to init/upgrade scaffolding, per its own README; " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.59',
    to:   '2.7.60',
    description: "Feature: clarify.md's own open items (AMB/GAP/CON/ASM/OQ/R) can now be pushed to Jira/Confluence for answers, the same way validate.md's markers already could (Python CLI) -- no manifest schema changes",
    notes: [
      "sdd review push-questions/pull-answers (Python CLI) now handle " +
      "clarify.md's STATUS TABLE (AMB/GAP/CON/ASM/OQ/R rows) in addition to " +
      "the existing [NEEDS CLARIFICATION-NNN] bracketed-marker scheme -- " +
      "reviewer replies as 'clarify:AMB-001: <answer>', which fills the " +
      "item's placeholder and flips its STATUS TABLE row to the correct " +
      "terminal status for its type",
      "This Node CLI does not implement sdd review submit/approve -- it " +
      "stays scoped to init/upgrade scaffolding, per its own README; " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.60',
    to:   '2.7.61',
    description: "Fix: /clarify now auto-pushes its open items to Jira/Confluence on generation and auto-pulls answers on re-run, matching /validate's existing behavior (prompt-only) -- no manifest changes",
    notes: [
      "clarify.prompt.md (all 5 packs) now auto-runs " +
      "`sdd review push-questions --doc clarify` right after generating " +
      "the report (when document_reviews.clarify is configured), and " +
      "auto-runs pull-answers first on every re-run, matching " +
      "validate.prompt.md's existing §3a pattern -- previously it required " +
      "the user to explicitly ask for the Jira push each time",
      "This Node CLI does not implement sdd review submit/approve -- it " +
      "stays scoped to init/upgrade scaffolding, per its own README; " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.61',
    to:   '2.7.62',
    description: "Fix: clarify.md's Step 4 re-syncs affected documents to Confluence/Jira; sdd review apply no longer requires both jira: and confluence:; new sdd confluence push --summary (Python CLI) -- no manifest changes",
    notes: [
      "clarify.prompt.md (all 5 packs) Step 4 now runs " +
      "`sdd review apply --doc {doc}` for each spec document an answer " +
      "was applied to, so the change reaches that document's own " +
      "Confluence page and Jira reviewer, not just the local file",
      "sdd review apply (Python CLI) no longer requires both jira: and " +
      "confluence: configured -- it does whichever half is actually set up",
      "New sdd confluence push --doc {doc} --summary (Python CLI) pushes " +
      "a doc's .summary.md to its own Confluence page",
      "This Node CLI does not implement sdd review submit/approve -- it " +
      "stays scoped to init/upgrade scaffolding, per its own README; " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.62',
    to:   '2.7.63',
    description: "Fix: plan-design's api-spec.md merge and change.prompt.md's full document walk now re-sync to Confluence/Jira after each local update (prompt-only) -- no manifest changes",
    notes: [
      "Same root cause as 2.7.62's clarify fix, found in two more places: " +
      "plan-design.prompt.md §3 (api-spec.md living-doc merge) and " +
      "change.prompt.md's Step 5 document walk (any of 14 document types, " +
      "UPDATE/RERUN/ANNOTATE branches) -- both now run `sdd review apply " +
      "--doc {doc}` after each local update, reusing the same relaxed " +
      "review apply from 2.7.62 (works with confluence-only, jira-only, " +
      "or both configured)",
      "This Node CLI does not implement sdd review submit/approve -- it " +
      "stays scoped to init/upgrade scaffolding, per its own README; " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.63',
    to:   '2.7.64',
    description: "Fix: local-svg diagrams pushed to Confluence now render at a readable width (ac:width=900 by default, configurable via diagrams.local_svg.width in the Python CLI) instead of the SVG's own tiny intrinsic size -- no manifest changes",
    notes: [
      "Root cause: the Python CLI's _render_local_svg() emitted " +
      "<ac:image> with no ac:width attribute, so Confluence displayed " +
      "the diagram at the SVG's own intrinsic size (Mermaid's renderer " +
      "typically emits a few hundred pixels), forcing the reader to " +
      "open and zoom",
      "New DiagramsConfig.local_svg_width field (default 900), " +
      "configured via diagrams.local_svg.width in integrations.yml -- " +
      "Confluence scales height to match, preserving aspect ratio",
      "integrations.yml.example (all 5 packs) documents the new " +
      "local_svg.width option in place of the old placeholder comment",
      "This Node CLI does not implement diagram rendering or Confluence " +
      "push -- it stays scoped to init/upgrade scaffolding, per its own " +
      "README; this migration entry exists so both CLIs report the " +
      "same sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.64',
    to:   '2.7.65',
    description: "Fix: /task never pushed stories/tasks to Jira or Confluence, diagram attachment 400s hid the real reason, constitution.md is now pushable; adds Approver name column to every Approvals table (Python CLI features; prompt/template changes apply to both CLIs' shared assets)",
    notes: [
      "task.prompt.md (all 5 packs) rewritten: auto-runs `sdd jira push " +
      "--level story` then `--level task` (finalizes UC-draft Stories in " +
      "place, creates real Tasks linked to their parent Story), pushes " +
      "stories.md/qa-testcases.md directly to Confluence, and routes " +
      "tasks.md through the same Submit-for-Review + review-decision " +
      "discipline every other reviewed document uses -- previously it " +
      "only generated an offline CSV and pointed at a retired manual " +
      "slash command",
      "Added missing stories/smoke-tests page_map entries and fixed a " +
      "title mismatch between document_reviews.tasks.confluence_page and " +
      "page_map.tasks that could have landed pushes on two different " +
      "Confluence pages for the same document",
      "Diagram attachment 400 errors now surface Confluence's actual " +
      "error body instead of a bare status code; malformed non-SVG " +
      "renderer output is now caught before reaching the upload call",
      "constitution.md can now be pushed to Confluence (a project-wide " +
      "page, like living docs) -- auto-pushed at GATE-1 finalization and " +
      "after confirmed amendments (Python CLI feature)",
      "Every document template gained an Approver column in its " +
      "## Approvals table (132 template files); approvals now resolve " +
      "the approver's name from roles.yml first, asking only if empty",
      "This Node CLI does not implement sdd review/jira/confluence " +
      "commands -- it stays scoped to init/upgrade scaffolding, per its " +
      "own README; this migration entry exists so both CLIs report the " +
      "same sdd_version chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.65',
    to:   '2.7.66',
    description: "Add: sdd token-log (Python CLI) reads Claude Code's own local session transcript for REAL token usage instead of the char/4 estimate; every other AI tool keeps the existing estimate",
    notes: [
      "Claude Code writes a local session transcript " +
      "(~/.claude/projects/{project}/{session-id}.jsonl, plus one file " +
      "per spawned subagent) where every assistant turn carries the " +
      "REAL usage object the Anthropic API actually returned -- not an " +
      "estimate. New `sdd token-log --command {name}` (Python CLI) " +
      "reads it and writes an authoritative row to token-usage.md",
      "This is Claude Code-only by nature -- undocumented, reverse-" +
      "engineered file layout, no equivalent under any other AI tool. " +
      "The shared token-usage-logging.md CLAUDE.md block tries it first " +
      "and falls back to the existing char/4 estimate on any non-zero " +
      "exit code; every other AI tool is unaffected",
      "token-usage-template.md's Per-Command Log table gained a Source " +
      "column (Real (Claude Code) | Estimated) so the two measurement " +
      "kinds are never silently compared to each other",
      "This Node CLI does not implement sdd token-log -- it stays " +
      "scoped to init/upgrade scaffolding, per its own README; this " +
      "migration entry exists so both CLIs report the same sdd_version " +
      "chain for a given manifest.yml",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.66',
    to:   '2.7.67',
    description: "Fix: dashboard Token Usage card showed blanks for token-usage.md files written after the 2.7.66 Source-column rename dropped the 'Est.' prefix from Running Totals labels",
    notes: [
      "The 2.7.66 template rewrite renamed 'Total Est. Input Tokens' " +
      "etc. to 'Total Input Tokens' (a row can now be Real or " +
      "Estimated), but status.py's parser and dashboard.py's rendered " +
      "labels (Python CLI) were never updated to match, so the Token " +
      "Usage card showed '-' for every project upgraded to 2.7.66",
      "status.py now accepts both the new and legacy label text; " +
      "dashboard.py's JS now renders the current label text",
      "This Node CLI does not implement sdd dashboard -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.67',
    to:   '2.7.68',
    description: "Enhance: sdd dashboard (Python CLI) gets a manual Light/Dark/Auto theme toggle plus a discoverable data-sourcing explainer and clearer empty states",
    notes: [
      "The dashboard only ever followed the browser's prefers-color-" +
      "scheme media query, which some browsers/embedded webviews never " +
      "report reliably -- users saw dark/light mode 'not working'. " +
      "Fixed with an explicit Light/Dark/Auto toggle persisted to " +
      "localStorage, verified with Playwright across all theme states",
      "Added a collapsible 'Where this data comes from' explainer near " +
      "the top of the page, and a more actionable empty-features state",
      "This Node CLI does not implement sdd dashboard -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.68',
    to:   '2.7.69',
    description: "Enhance: sdd dashboard (Python CLI) gets a Real/Estimated token badge, a Features Overview table for multi-feature projects, and auto-refreshing Jira/Confluence review links",
    notes: [
      "Token Usage card now shows a Real N / Est. N badge tallied from " +
      "the Per-Command Log's Source column",
      "New Features Overview table (2+ features) lists every feature's " +
      "current step, task progress, and next action with jump links",
      "Once a feature's review links have been checked once (manual " +
      "button click, opt-in preserved), the dashboard now auto-refreshes " +
      "them every 5 minutes instead of only on click",
      "This Node CLI does not implement sdd dashboard -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.69',
    to:   '2.7.70',
    description: "Enhance: sdd dashboard's (Python CLI) Documents card shows who should approve a pending document (role + name from roles.yml) and who approved it, via which mode",
    notes: [
      "status.py parses each document's own '## Approvals' table -- " +
      "filled in identically regardless of review mode (chat/local/" +
      "jira) -- and resolves a pending row's Role cell to the actual " +
      "name in roles.yml. Tolerates both the current 4-column format " +
      "(with Approver) and the legacy 3-column one",
      "Each Documents row now shows a compact 'Awaiting Product Owner: " +
      "Jane Smith' (or the approver's name once approved) summary, plus " +
      "a 👤 toggle for the full Role/Approver/Status/Date table and " +
      "which mode recorded the approval",
      "This Node CLI does not implement sdd dashboard -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.70',
    to:   '2.7.71',
    description: "Enhance: sdd dashboard (Python CLI) consolidates each document's View/Approvals/Comments toggles into one tabbed Details panel",
    notes: [
      "The Documents row had grown to up to 7 elements (View, 👤, 💬, " +
      "Jira pill, Confluence pill, review badge, Approve) across several " +
      "features added this release cycle. Replaced the three expand-" +
      "toggles with one 'Details' button opening a tab strip (Content / " +
      "Approvals / Comments) -- only one panel renders per document now",
      "This Node CLI does not implement sdd dashboard -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.71',
    to:   '2.7.72',
    description: "Fix: sdd dashboard's (Python CLI) Constitution/Token-Usage status badges silently lost their color, and stale 'View' button copy",
    notes: [
      "A CSS descendant-combinator bug ('.kv span:first-child') was " +
      "unintentionally overriding badge colors nested inside a .kv row " +
      "to plain gray -- fixed with a child combinator so only the row's " +
      "own label span is affected",
      "The info box referenced a 'View' button that no longer exists " +
      "after the Details-panel consolidation (2.7.71) -- updated to " +
      "reference the Content tab",
      "This Node CLI does not implement sdd dashboard -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.72',
    to:   '2.7.73',
    description: "Fix: sdd dashboard's (Python CLI) Approve pill could keep showing a stale approver's name after a document was regenerated back to Draft",
    notes: [
      "approvalMode()/approvedRowInfo() previously trusted " +
      "d.local_approval unconditionally, so a doc regenerated back to " +
      "Draft could still show the old approver's checkmark -- " +
      ".local-approvals.yml isn't cleared just because doc content " +
      "changed. Both now check the document's live Status: header " +
      "first, the same authoritative-source rule the status badge " +
      "itself already follows",
      "This Node CLI does not implement sdd dashboard -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.73',
    to:   '2.7.74',
    description: "Enhance: sdd dashboard's (Python CLI) now shows live Jira ticket status (not just links) for review-gate and Jira Export Epic/Story/Task tickets",
    notes: [
      "User asked directly whether the dashboard shows Jira ticket " +
      "status, not just links -- the raw status was already fetched " +
      "but unused for review-gate tickets, and never fetched for " +
      "Export tickets. Both gaps closed",
      "Review-gate ticket pills now show the raw Jira workflow status " +
      "(e.g. 'In Review') alongside SDD's own APPROVED/PENDING/" +
      "NEEDS_REVISION review_status badge",
      "A new batched JQL 'key in (...)' query resolves Epic/Story/Task " +
      "status from docs/jira/{feature}/keys.yml in one call instead of " +
      "one lookup per ticket, with keys validated before being " +
      "interpolated into the query",
      "This Node CLI does not implement sdd dashboard -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.74',
    to:   '2.7.75',
    description: "Fix: sdd_parser.py (Python CLI) never matched the actual shipped stories.md/tasks.md templates -- sdd jira push and sdd pr create --task silently found zero stories/tasks for every real generated feature",
    notes: [
      "sdd_parser.py's regexes expected a heading/field format the " +
      "shipped feature-story-template.md/tasks-template.md have not " +
      "used for some time -- parse_stories()/parse_tasks() returned an " +
      "empty list for every correctly-generated document, silently " +
      "breaking 'sdd jira push' and 'sdd pr create --task' on the " +
      "framework's golden path",
      "Rewritten to match the current templates while still accepting " +
      "the older heading/field style found in already-generated docs",
      "Also fixed: MoSCoW bucket normalization required an exact string " +
      "match against 'must have', but the shipped template's headers " +
      "are 'Must Have Stories' -- every story silently fell through to " +
      "the could-have default, mapping every pushed Jira Story to Low " +
      "priority regardless of its actual bucket",
      "This Node CLI does not implement sdd_parser.py -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.75',
    to:   '2.7.76',
    description: "Fix: /release and /implement's runbook (Python CLI prompts) never went through Jira/Confluence review despite document_reviews.runbook/.release being fully documented and configurable",
    notes: [
      "release.prompt.md had zero Jira/Confluence wiring for release.md " +
      "(only an informal chat sign-off), and implement.prompt.md never " +
      "submitted the runbook (docs/runbook/local-setup.md) for review " +
      "at all -- despite CLAUDE.md's own Jira-mode sequence table " +
      "documenting 'release phase: Runbook -> Release' and the shipped " +
      "integrations.yml.example already configuring both reviewers",
      "Backend bug in the same sweep: resolve_doc_path() had no case " +
      "for 'runbook' -- it would have resolved to a nonexistent path " +
      "instead of the real docs/runbook/local-setup.md; new " +
      "PROJECT_SCOPED_DOCS constant fixes path resolution and " +
      "Confluence page nesting/titling for it",
      "integrations.yml.example's page_map.release entry was also " +
      "commented out by default even though document_reviews.release " +
      "was already active -- uncommented to match runbook's entry",
      "This Node CLI does not implement these prompts -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.76',
    to:   '2.7.77',
    description: "Fix: self-approval risk undocumented, coverage gate was a bare echo, no test caught either -- verified with grep before fixing, per external review",
    notes: [
      "An external agent reviewed the two prior fixes and raised " +
      "several concerns. Re-checked every claim against the actual " +
      "repo with grep/read instead of accepting either the review's or " +
      "this agent's own prior assessment on faith -- some held up, " +
      "some didn't (e.g. a cited '245 tests' figure was stale; actual " +
      "count was 592). Three confirmed, real gaps were fixed",
      "review-gates.md now explicitly states the self-approval risk in " +
      "chat mode: nothing stops the same conversation that drafted a " +
      "document from also being the one that approves it",
      "quality-gate.yml's (Python CLI packs) 'Enforce coverage gate' " +
      "step was a bare echo in every pack -- confirmed by reading the " +
      "actual workflow file. Replaced with a real tripwire that greps " +
      "for jacoco-maven-plugin's <rules> block (Java) or " +
      "coverageThreshold/thresholds config (Node) and fails the CI job " +
      "if missing, across all 5 packs",
      "New test_prompt_review_coverage.py (Python CLI) checks every " +
      "active document_reviews key against its owning .prompt.md file " +
      "for a real 'sdd review submit' call -- verified by reverting " +
      "release.prompt.md to its pre-fix state and confirming the test " +
      "fails exactly where the real bug was",
      "This Node CLI does not implement these prompts/CI templates -- " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.77',
    to:   '2.7.78',
    description: "Fix: sdd-universal missing UI templates, brd-template.md drift, design-template.md numbering gap -- template quality review found real gaps beyond docs/CI",
    notes: [
      "sdd-universal was missing ux-flow-template.md, " +
      "screen-spec-template.md, component-spec-template.md, and " +
      "component-library-template.md even though its own " +
      "specify-doc.prompt.md documents them as valid /specify-doc " +
      "commands and reads .specify/templates/{doc}-template.md " +
      "directly -- broken for exactly the mobile/frontend project " +
      "types sdd-universal auto-detects. Added all four",
      "ux-flow-template.md, screen-spec-template.md, and " +
      "component-spec-template.md had no ID scheme or Version History " +
      "table, unlike every other template in the system. Added " +
      "FLOW/ERR/EDGE-NNN, SCR-NNN, and COMP-NNN respectively, plus " +
      "Version History to all three",
      "brd-template.md had drifted uncoordinated: sdd-universal's copy " +
      "had a Section 9 Investment Summary and domain-aware regulation " +
      "pre-seeding the other four packs never received, despite BRD " +
      "content having no legitimate reason to vary by project type. " +
      "Reconciled using sdd-universal's fuller version as canonical",
      "design-template.md Section 3 skipped from 3.2 to 3.5 with no " +
      "3.3/3.4 content anywhere -- renumbered to 3.3",
      "This Node CLI does not implement /specify-doc or these template " +
      "prompts -- this migration entry exists so both CLIs report the " +
      "same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.78',
    to:   '2.7.79',
    description: "Fix: runbook-template.md missing living-doc framing in 4 packs, security-design/data-model/api-spec inconsistencies across packs, release-template.md pilot-scope broken rollback reference, sdd-universal had no project-type flavor branching for data-model/security/runbook",
    notes: [
      "runbook-template.md was missing its 'Living artifact' framing " +
      "paragraph and used '# Feature: {Feature Name}' instead of " +
      "'# Service:'/'# App:' in frontend-spa, mobile, fullstack, and " +
      "sdd-universal (only sdd-backend-service had it correct). Fixed " +
      "all four",
      "security-design-template.md was inconsistent across packs: only " +
      "sdd-backend-service had a Version History table; only " +
      "sdd-universal had the CVSS scoring column and the 2-row Security " +
      "Officer/Tech Lead Approvals table. Reconciled all five packs",
      "data-model-template.md and api-spec-template.md were missing " +
      "Version History tables in sdd-universal (both docs) and " +
      "sdd-fullstack (api-spec only); also fixed a stale References row " +
      "in sdd-universal's api-spec-template.md",
      "release-template.md Section 7 Rollback Plan pointed to " +
      "docs/runbook/local-setup.md even at pilot scope, where the " +
      "runbook is never generated -- backported sdd-universal's " +
      "pilot-scope fallback rollback table to the other four packs",
      "sdd-universal's specify-doc.prompt.md and implement.prompt.md now " +
      "branch by project_type for data-model/security-design/runbook " +
      "template flavor, instead of always using the server-side/backend " +
      "shape",
      "This Node CLI does not implement /specify-doc, /implement, or " +
      "these template prompts -- this migration entry exists so both " +
      "CLIs report the same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.79',
    to:   '2.7.80',
    description: "Fix: data-model-template.md missing Version History in frontend-spa/mobile/fullstack, security-design-template.md STRIDE column wording inconsistency in sdd-universal",
    notes: [
      "data-model-template.md was missing '## Version History' in " +
      "sdd-frontend-spa, sdd-mobile, and sdd-fullstack -- only " +
      "sdd-backend-service and sdd-universal had it. Added to all three",
      "security-design-template.md's STRIDE column header was 'Threat " +
      "(STRIDE)' in sdd-universal but 'Threat (STRIDE category)' in the " +
      "other four packs -- normalized sdd-universal to match",
      "This Node CLI does not implement these template files -- this " +
      "migration entry exists so both CLIs report the same sdd_version " +
      "chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.80',
    to:   '2.7.81',
    description: "Fix: sdd-micro/setup.sh had zero test coverage -- test-setup.sh only ever tested sdd-universal's setup.sh (hardcoded PACK_DIR); no manifest.yml field changes for any pack",
    notes: [
      "packs/_shared/tests/test-setup.sh was hardcoded to " +
      "packs/sdd-universal -- sdd-micro/setup.sh (a materially " +
      "different script) was never exercised by CI",
      "Added packs/_shared/tests/test-setup-micro.sh mirroring " +
      "test-setup.sh's structure, wired into the same setup-smoke-tests " +
      "CI job",
      "This Node CLI does not implement setup.sh testing -- this " +
      "migration entry exists so both CLIs report the same sdd_version " +
      "chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.81',
    to:   '2.7.82',
    description: "Feature: Business Objectives traceability + dashboard rollup -- brd.md's Business Objectives (§2) and Business Requirements (§5) were previously unlinked siblings; adds a 'Serves BO' column to §5 and rolls BO -> BR -> FR -> TASK up into a per-feature and cross-feature Business Objectives view in `sdd dashboard`",
    notes: [
      "Added 'Serves BO' column to brd-template.md's §5 Business " +
      "Requirements table (all 5 non-micro packs) -- every BR-NNN must " +
      "now cite which BO-NNN from §2 it serves",
      "This Node CLI does not implement the dashboard or status.py " +
      "parsers -- this migration entry exists so both CLIs report the " +
      "same sdd_version chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.82',
    to:   '2.7.83',
    description: "Fix: `sdd config init`'s .specify/integrations.yml scaffold was built from a small hand-maintained template string that had drifted far behind the real integrations.yml.example -- missing project_keys, parent_field_by_level, custom_fields_by_level, diagrams, document_reviews, pr_automation, and code_review entirely, plus most of page_map",
    notes: [
      "`sdd config init` now fills profile/project_key/space_key/" +
      "parent_page_id into the project's own shipped " +
      "integrations.yml.example instead of a separate, drifted template " +
      "string -- every section the current pack version documents is " +
      "present in the scaffolded file",
      "This Node CLI does not implement `sdd config init` -- this " +
      "migration entry exists so both CLIs report the same sdd_version " +
      "chain",
      "This migration only bumps sdd_version — no manifest.yml field " +
      "changes for any pack",
    ],
  },
  {
    from: '2.7.83',
    to:   '2.7.84',
    description: "Docs: HOW-TO-USE.md's 'Phase 0 -- Setup' section never mentioned sdd config init/sdd config test -- added as an explicit optional step right after sdd init/setup.sh, in all 5 non-micro packs",
    notes: [
      "A reader following 'Phase 0 -- Setup (before any command)' top " +
      "to bottom would not discover Jira/Confluence setup exists until " +
      "a much later, unrelated section mentioned it in passing",
      "Docs-only change -- no manifest.yml field changes, no CLI " +
      "behavior change",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
    ],
  },
  {
    from: '2.7.84',
    to:   '2.7.85',
    description: "Fix batch: full template/parser audit found tasks.md checkboxes never flipped by /implement (neutering the BO rollup dashboard), CHG-NNN tasks invisible to the task-heading regex, validate.prompt.md's own step numbering colliding with its template, security-design.md mixing CVSS into a doc that always intended DREAD, CF-NNN consistency findings never reaching clarify.md's gate, and release.md/qa-testcases.md data never feeding back into anything downstream",
    notes: [
      "Tier 1 (7 fixes): implement.prompt.md now flips tasks.md's own " +
      "checkboxes instead of only reporting completion in chat; " +
      "_TASK_HEADING_RE (status.py + sdd_parser.py) widened to " +
      "TASK-NNN|PERF-NNN|CHG-NNN, plus change.prompt.md's CHG-NNN " +
      "template rewritten to an actual heading block so the regex fix " +
      "isn't a no-op; validate.prompt.md's '3a' clarification-scan step " +
      "renumbered to '0a' to stop colliding with the template's real " +
      "§3a section; use-cases-template.md gained an Independent Test " +
      "field per UC; security-design-template.md reconciled to DREAD " +
      "scoring everywhere (was mixing in CVSS) plus a new OWASP Top 10 " +
      "Controls Mapping table; CF-NNN consistency findings now flow " +
      "from analyze.md into clarify.md's own gate; " +
      "constitution-amendment-template.md (previously dead) wired into " +
      "every pack's /specify GATE-1 re-run flow",
      "Tier 2 (4 fixes): release.md's BO Closure 'Met?' checkbox gained " +
      "a No state and now feeds status.py's build_bo_rollup() as new " +
      "outcome/measured_result fields (surfaced in sdd dashboard as a " +
      "Business Outcome column); release.prompt.md's UAT Plan now pairs " +
      "each UC-NNN with its qa-testcases.md/smoke-tests.md TC-NNN(s); " +
      "jira-export-template.md's manual CSV gained a TC Reference " +
      "column; jira.py's parse_changeset() no longer silently drops the " +
      "PR/Status columns from changesets/{CR}.md's §4 table",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "Verified: cli-python pytest 682/682, assert-output.sh clean on " +
      "both worked examples",
    ],
  },
  {
    from: '2.7.85',
    to:   '2.7.86',
    description: "Fix: separate plan_mode (arch.md -> hld.md -> adr.md) had no path to generate the living .specify/service/api-spec.md at all -- unified plan_mode's design.md was the only route -- plus several structural columns had drifted between the two modes",
    notes: [
      "hld-template.md gained a new '## 6. API Design' section " +
      "(renumbered Technology Stack -> 7, NFR Summary -> 8) -- ported " +
      "from design.md's own §3 nearly verbatim, including its skip-list " +
      "and provides/consumes branch",
      "hld-template.md gained a new '## 4. Error / Failure Paths' " +
      "sequence diagram -- design.md §2.5 already generates this " +
      "unconditionally today; separate mode had no equivalent anywhere",
      "plan-hld.prompt.md updated to match: new Diagram 4 and Section 6 " +
      "instructions (API Design ported from plan-design.prompt.md §3, " +
      "including the living-doc api-spec.md walk); Section 8 NFR " +
      "instruction fixed to list all 4 columns its own template defines " +
      "(was only listing 2)",
      "Fixed 3 hardcoded design.md-only references that never branched " +
      "by plan_mode: task.prompt.md's QA-endpoint-source line, " +
      "lld-template.md's References table, and ava.prompt.md's dead " +
      "'api spec' routing row",
      "design-template.md's §1.2/§1.3/§1.4 tables gained columns " +
      "arch-template.md (separate mode's equivalent) already had -- " +
      "'what it must NOT do', 'Alternatives Rejected', " +
      "'Decision (DEC-NNN)'",
      "design.md's §4 ADR block expanded to match adr-template.md's " +
      "Options A/B/C + pros/cons depth",
      "Deleted adr-template.md's dead 'ADR Index' pointer",
      "All 5 packs' CLAUDE.md hld.md description updated to mention API " +
      "design",
      "Template/prompt-only change -- no manifest.yml field changes, no " +
      "CLI behavior change",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "Verified: cli-python pytest 682/682 (unaffected), assert-output.sh " +
      "clean on both worked examples, test-setup.sh 15/15",
    ],
  },
  {
    from: '2.7.86',
    to:   '2.7.87',
    description: "Fix: specify-doc.prompt.md's own living-doc walk (data-model, security-design, component-library) never re-synced Confluence/Jira after an approved change -- only /change's separate living-doc handling did",
    notes: [
      "change.prompt.md already calls `sdd review apply --doc {doc-key}` " +
      "after every living-doc merge, but specify-doc.prompt.md's own " +
      "native SKIP/ADD-unit/UPDATE-unit walk -- the path a later feature " +
      "normally takes to extend data-model.md/security-design.md on its " +
      "own -- only merged, bumped the version, appended history, and " +
      "regenerated the summary, with no re-sync call anywhere",
      "Added step 5 to the 'On approval' list: " +
      "`sdd review apply --doc {doc}` -- re-pushes to Confluence + posts " +
      "a re-review comment on Jira if either is configured, skip " +
      "silently otherwise",
      "Practical effect before this fix: a second feature adding a new " +
      "entity to an already-reviewed data-model.md through the normal " +
      "/specify-doc walk would merge correctly on disk but leave the " +
      "Confluence page silently stale",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "Prompt-only change -- no manifest.yml field changes, no CLI " +
      "behavior change. Verified: cli-python pytest 682/682 (unaffected), " +
      "assert-output.sh clean",
    ],
  },
  {
    from: '2.7.87',
    to:   '2.7.88',
    description: "Fix: /specify-doc's own 'Action 2 doc-set table' cross-reference pointed at a table that didn't exist in specify.prompt.md in any pack -- broke discoverability of which extended docs (data-model, security, component-spec, etc.) a project actually needs",
    notes: [
      "specify-doc.prompt.md, specify-srd.prompt.md, and " +
      "orchestrate.prompt.md (all fully shared across all 5 packs) " +
      "repeatedly said 'refer to the doc-set table in specify.prompt.md " +
      "(Action 2)' -- but no pack's specify.prompt.md had an 'Action 2' " +
      "heading at all, only 'Action 1' (Constitution Part 2). Dead " +
      "pointer in all 5 packs",
      "The gap was papered over in Claude Code specifically because each " +
      "pack's own CLAUDE.md (auto-loaded at session start) already lists " +
      "the real doc names + scope gates, but that fallback doesn't apply " +
      "to non-Claude-Code tools, and sdd-universal's own CLAUDE.md " +
      "punted with 'any other extended doc' instead of enumerating which " +
      "extended docs apply to which of its 10 project_types",
      "Fix: added a real '## Action 2 -- Extended Document Set' table to " +
      "specify.prompt.md in each of the 4 single-type packs, sourced " +
      "from that pack's own CLAUDE.md. sdd-universal got a " +
      "project_type-grouped matrix (consumer-view / mobile / " +
      "server-service / no-runtime-service) rather than a false-precision " +
      "10-type table, since the framework doesn't cleanly define " +
      "per-type applicability for cli/library/iac -- those are marked " +
      "ask-the-user-first instead of a guessed yes/no",
      "specify-doc.prompt.md's no-argument instruction now explicitly " +
      "reads the Action 2 table (filtered by scope/project_type) and " +
      "diffs it against what's already on disk",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "Prompt/doc-only change -- no manifest.yml field changes, no CLI " +
      "behavior change. Verified: cli-python pytest 682/682 (unaffected), " +
      "assert-output.sh clean on both worked examples, every 'Action 2' " +
      "reference across all 5 packs now resolves to a real heading",
    ],
  },
  {
    from: '2.7.88',
    to:   '2.7.89',
    description: "Fix: dashboard's single collapsed 'Extended Specs' pipeline step let generating just one required doc (e.g. security) silently mark ALL of them (data-model, component-spec, ux-flow, ...) as done",
    notes: [
      "status.py's _service_docs_exist() was a bare existence check -- " +
      "'does at least one .md file exist under .specify/service/' -- so " +
      "the dashboard's whole 'Extended Specs' row flipped to done the " +
      "moment ANY ONE of the required docs existed",
      "Also found: the same collapsed step was skipped entirely at pilot " +
      "scope, contradicting CLAUDE.md's own Scope Reference table -- " +
      "security-design.md is required at every scope (pilot gets Threat " +
      "Assessment / §1 only, not zero)",
      "Fix: split into one step per doc, each tracked individually. " +
      "security-design/data-model get their own service_doc step backed " +
      "by checking .specify/service/{key}.md directly; component-spec/" +
      "ux-flow/screen-spec/resilience/investigation are now normal " +
      "per-feature doc steps. Type-specific docs only appear as steps " +
      "when the project's type actually uses them (template-presence " +
      "detection for the 4 single-type packs, project_type field for " +
      "sdd-universal) -- cli/library/iac deliberately show none rather " +
      "than guessing",
      "security-design is now never scope-skipped; data-model/" +
      "component-spec/ux-flow/screen-spec stay mvp+; resilience/" +
      "investigation stay full-only -- each gated individually",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "cli-python only change (sdd/utils/status.py + tests) -- no " +
      "manifest.yml field changes, no prompt/template changes. Verified: " +
      "cli-python pytest 688/688 (6 new regression tests), live run " +
      "against both worked examples confirmed independent tracking and " +
      "correct type-specific doc inclusion, assert-output.sh clean",
    ],
  },
  {
    from: '2.7.89',
    to:   '2.7.90',
    description: "Fix: dashboard's extended-docs steps listed security-design before data-model, so at mvp+ scope the 'next action' hint told users to run security before data-model -- backwards from the recommended /specify-doc sequence",
    notes: [
      "Neither doc depends on the other, so this was never a " +
      "correctness bug, but next_action picks the first non-done, " +
      "non-skipped step in list order -- so at mvp+ scope with nothing " +
      "generated yet, the dashboard said 'Run /specify-doc security' " +
      "before ever mentioning data-model",
      "Swapped the two entries so data-model is listed first, matching " +
      "the recommended /specify-doc sequence (data-model -> security -> " +
      "component-spec/ux-flow if applicable)",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "cli-python only change (list-order only, no gating/skip logic " +
      "touched). Verified: cli-python pytest 688/688 (unaffected), live " +
      "run at mvp scope confirmed next_action now reads " +
      "'Run `/specify-doc data-model`' first",
    ],
  },
  {
    from: '2.7.90',
    to:   '2.7.91',
    description: "Add a cross-reference linter (packs/_shared/tests/check-cross-references.py) that catches dead 'Action N' / '{doc}.md §N' pointers between prompt files before a user finds them",
    notes: [
      "Both real bugs found this session (v2.7.88's dead 'Action 2' " +
      "pointer, v2.7.89's dashboard collapsing several docs' status " +
      "into one boolean) share a root cause: something read as correct " +
      "in isolated review but was never exercised end-to-end, and both " +
      "were only found because a user asked a pointed question -- not " +
      "because any test caught them",
      "The script scans every pack's .github/prompts/*.md and CLAUDE.md " +
      "for 'specify.prompt.md ... (Action N)' and '{doc}.md §N' " +
      "references, then verifies the referenced heading actually exists " +
      "in that pack's own copy of the target file -- each pack checked " +
      "against itself, not a shared assumption",
      "Deliberately skips '*.summary.md §N' refs (no guaranteed section " +
      "numbering) and treats a doc key with no matching template as a " +
      "note, not a failure",
      "Caught two real bugs in itself during development by testing it " +
      "actually fails on a known-bad input: a Path.parents[] off-by-one " +
      "that made it silently scan a nonexistent directory (always " +
      "passed), and a heading-number regex that matched subsection " +
      "numbers too (a renamed top-level section still 'existed' as long " +
      "as any N.x subsection survived)",
      "Wired into CI as a new 'cross-reference-check' job and " +
      "documented in the root CLAUDE.md's 'Testing Setup Scripts' " +
      "section",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "New standalone script, no manifest.yml field changes. Verified: " +
      "cli-python pytest 688/688 (unaffected), assert-output.sh clean on " +
      "both worked examples, test-setup.sh 15/15, test-setup-micro.sh " +
      "12/12",
    ],
  },
  {
    from: '2.7.91',
    to:   '2.7.92',
    description: "setup.sh/setup.ps1 now interactively ask for reading_mode (auto|summary|full) instead of silently baking in the 'auto' default with no prompt",
    notes: [
      "A user asked directly: reading_mode already existed as a " +
      "documented manifest.yml field (AI-2 token-economy switch in " +
      "summary-rules.md), but grepping setup.sh/setup.ps1 confirmed it " +
      "was never part of the interactive flow -- only name, scope, " +
      "feature, and plan_mode were ever asked. Every new project " +
      "silently got 'auto' with no chance to pick summary or full at " +
      "init time",
      "Added a --reading-mode flag (-ReadingMode in PowerShell) and an " +
      "interactive prompt with the same three-option explanation already " +
      "in summary-rules.md, mirroring the existing plan_mode prompt " +
      "pattern exactly -- same env-var-safe substitution in " +
      "sdd-universal/setup.sh, same regex substitution in the shared " +
      "_shared/full/setup.sh used by the other 4 non-micro packs",
      "sdd-micro intentionally excluded -- confirmed via grep it has no " +
      "reading_mode field in its manifest.yml at all (no BRD/UC/SRD " +
      "documents to summarize, so the AI-2 token-economy switch doesn't " +
      "apply there)",
      "Verified with a real pty (not piped stdin, which forces " +
      "non-interactive mode by the script's own design and would've " +
      "given a false pass): the prompt renders, accepts 'summary', and " +
      "writes reading_mode: \"summary\" into manifest.yml. Also verified " +
      "--reading-mode full/summary flags directly on sdd-backend-service, " +
      "sdd-frontend-spa, and sdd-universal's separate setup.sh",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "No manifest.yml schema change for existing projects -- the field " +
      "already existed, only new-project setup behavior changed. " +
      "Verified: cli-python pytest 688/688 (unaffected), test-setup.sh " +
      "15/15, test-setup-micro.sh 12/12, assert-output.sh clean on both " +
      "worked examples",
    ],
  },
  {
    from: '2.7.92',
    to:   '2.7.93',
    description: "Let Jira and Confluence use separate ~/.sdd/config.yml profiles (jira.profile / confluence.profile in integrations.yml) instead of one shared profile for both",
    notes: [
      "A user asked directly: their org runs Jira and Confluence as " +
      "separate Data Center servers with separate credentials -- was that " +
      "ever accounted for? It wasn't. Every command that talks to Jira " +
      "and Confluence resolved exactly ONE Profile (one base_url, one " +
      "credential) from the single top-level integrations.yml profile: " +
      "field, then handed the SAME session to both JiraClient and " +
      "ConfluenceClient -- correct only when both are the same Atlassian " +
      "Cloud site",
      "IntegrationsConfig grew two new optional fields, jira.profile and " +
      "confluence.profile, each falling back to the existing top-level " +
      "profile: when unset -- every existing project with one profile: " +
      "line keeps working identically, no config change required",
      "New atlassian_auth.load_jira_session()/load_confluence_session() " +
      "resolve each service's Profile + Session independently, replacing " +
      "the old shared load_profile()+build_session() pair at every call " +
      "site across config.py, confluence.py, cr.py, dashboard.py, jira.py, " +
      "pr.py, review.py. A command's own --profile flag still wins over " +
      "both",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "integrations.yml.example documents both new fields; no manifest.yml " +
      "schema change for existing projects",
      "Verified: cli-python pytest 695/695 (688 pre-existing + 7 new)",
    ],
  },
  {
    from: '2.7.93',
    to:   '2.7.94',
    description: "'sdd config init' now asks upfront whether Jira and Confluence share one set of credentials or need two, instead of requiring a manual second run + hand-edit to use the jira.profile/confluence.profile split added in 2.7.93",
    notes: [
      "2.7.93 added jira.profile/confluence.profile overrides so the " +
      "two services can use separate ~/.sdd/config.yml profiles, but " +
      "'sdd config init' itself was still a single-profile wizard -- " +
      "getting the split required running init twice and manually " +
      "uncommenting the override lines in integrations.yml afterward. " +
      "A user asked directly: does init actually offer this? It didn't",
      "config_init() now opens with 'Do Jira and Confluence share the " +
      "same site and credentials?' -- Yes keeps the exact original " +
      "single-profile flow; No runs the full credential round (profile " +
      "name, base_url, auth mode, credential storage) twice, once per " +
      "service, via a new _collect_and_save_profile() helper extracted " +
      "from the original inline flow so both paths share identical " +
      "prompts and validation",
      "'Different' mode wires the result automatically -- the " +
      "top-level profile: becomes Jira's, and confluence.profile: is " +
      "uncommented and filled with the Confluence profile name in the " +
      "generated integrations.yml (_integrations_from_example / " +
      "_integrations_template both take an optional confluence_profile " +
      "param). No manual editing step required anymore",
      "A profile is understood as the entire auth set (base_url + " +
      "auth_mode + credential) -- the two profiles created in " +
      "'different' mode are never assumed to share anything, even if " +
      "e.g. the base_url happened to coincide",
      "New tests: test_different_profiles_creates_both_in_config_yml " +
      "(both profiles saved with distinct base_url/auth_mode/storage) " +
      "and test_different_profiles_wires_confluence_override_into_integrations_yml " +
      "(end-to-end: generated integrations.yml actually has the " +
      "override, not just two orphaned config.yml profiles). 5 " +
      "pre-existing config-init tests updated for the new opening " +
      "question",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "No manifest.yml or integrations.yml schema change -- 2.7.93 " +
      "already added the fields this just makes reachable from the " +
      "wizard. Verified: cli-python pytest 697/697 (695 pre-existing " +
      "+ 2 new)",
    ],
  },
  {
    from: '2.7.94',
    to:   '2.7.95',
    description: "Confluence parent-page prompt/config now accepts a pasted page URL, not just the raw numeric ID",
    notes: [
      "A user pointed out that when 'sdd config init' asks for the " +
      "Confluence parent page, most people have the page open in a " +
      "browser tab, not its raw numeric ID memorized -- the wizard only " +
      "accepted the bare ID, forcing a manual trip through Page " +
      "Information to extract it first",
      "New sdd.utils.integrations.parse_confluence_page_id() recognizes " +
      "a bare numeric ID unchanged, a Cloud URL " +
      "('.../pages/123456/Title'), or a Server/Data Center URL " +
      "('...?pageId=123456'), and extracts just the numeric ID from " +
      "either -- a Confluence 'tiny link' (/x/AbCdEf) isn't a page ID " +
      "and can't be resolved without an API call, so it's returned " +
      "unchanged with a wizard warning telling the user to paste the " +
      "full URL instead",
      "Wired into two places: the config-init wizard prompt (so pasting " +
      "a URL there resolves correctly in the generated integrations.yml), " +
      "and load_integrations() itself (so a hand-edited integrations.yml " +
      "with a pasted URL for parent_page_id also resolves correctly at " +
      "push time, not just via the wizard)",
      "integrations.yml.example's parent_page_id comment updated to " +
      "document that either form works",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "No manifest.yml schema change. Verified: cli-python pytest " +
      "707/707 (697 pre-existing + 10 new)",
    ],
  },
  {
    from: '2.7.95',
    to:   '2.7.96',
    description: "'sdd config test' now resolves Jira and Confluence independently, instead of pinging both against one profile's base_url",
    notes: [
      "A user asked whether all docs were updated for the recent " +
      "config-init changes -- while auditing, found that 'sdd config " +
      "test' still resolved exactly ONE Profile and pinged both Jira " +
      "and Confluence against its base_url, even though 2.7.93 let them " +
      "use separate profiles. That means testing the split with " +
      "`sdd config test --profile confluence-dc` (exactly what the " +
      "config-init wizard's own closing message told you to run) would " +
      "try to hit Jira at Confluence's URL and vice versa -- a silent " +
      "false failure for whichever service didn't match the flag",
      "Without --profile, Jira and Confluence are now each resolved " +
      "through integrations.yml's jira.profile/confluence.profile " +
      "independently -- each service is pinged against its own base_url " +
      "and credential. When they resolve to the same profile (the " +
      "common case), only one session is built and no extra output is " +
      "printed, so single-profile projects see identical output to " +
      "before. When they differ, the command prints which profile " +
      "backs which service before testing",
      "An explicit --profile still tests that ONE profile against BOTH " +
      "services, unchanged -- for sanity-checking a profile before it's " +
      "wired into integrations.yml",
      "config_init()'s own closing message was part of the same bug: it " +
      "told users to run 'sdd config test --profile X' twice, which " +
      "doesn't actually isolate a single service. Now scaffolding " +
      "integrations.yml means the message says 'Run sdd config test to " +
      "verify both' (no --profile); declining to scaffold falls back to " +
      "the old two-command guidance with an explicit caveat",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "No manifest.yml schema change. Verified: cli-python pytest " +
      "713/713 (707 pre-existing + 6 new)",
    ],
  },
  {
    from: '2.7.96',
    to:   '2.7.97',
    description: "Jira Feature/Epic description now carries Problem Statement, Business Hypothesis, Description, Out of Scope, and NFR instead of a bare Business Objectives bullet list",
    notes: [
      "A user asked for a specific description template on the " +
      "Feature/Epic issue: Problem Statement, Business Hypothesis, " +
      "Description, Out of Scope, NFR. The previous description was a " +
      "single 'Business Objectives:' bullet list pulled from brd.md's " +
      "BO-NNN rows -- useful, but not the shape being asked for",
      "brd-template.md gains a new '### Business Hypothesis' field " +
      "under §4 Business Context, right after Problem Statement -- a " +
      "testable belief statement, distinct from the Problem Statement " +
      "it sits next to. specify-brd.prompt.md instructs the agent to " +
      "fill it, falling back to [ASSUMPTION-NNN] if no measurable " +
      "signal is available yet",
      "New jira.py parsers pull Problem Statement/Business " +
      "Hypothesis/Description from brd.md §4/§1, Out of Scope from " +
      "brd.md §4's bullet list (not confused with the In Scope bullets " +
      "right above it), and NFR from srd.md §3's NFR-NNN table",
      "New adf_sections() ADF builder renders each as its own heading + " +
      "body, and OMITS a section entirely when its source doesn't " +
      "exist yet or is still unfilled template placeholder text -- e.g. " +
      "NFR is silently absent until /specify-srd runs, without forcing " +
      "the whole description into a placeholder. Falls back to a " +
      "single placeholder paragraph only when every section is empty",
      "sdd review submit's Epic self-bootstrap reuses the same " +
      "feature_extra_fields(), so it gets the new template " +
      "automatically, no separate change needed there",
      "Every existing Epic gets the new description shape on its next " +
      "push (create-or-update is idempotent) -- no manual migration " +
      "step, no manifest.yml schema change",
      "This Node CLI ships from the same pack sources -- this " +
      "migration entry exists so both CLIs report the same sdd_version " +
      "chain",
      "Verified: cli-python pytest 721/721 (713 pre-existing + 8 new), " +
      "cross-reference linter clean, assert-output.sh clean, setup " +
      "smoke tests clean",
    ],
  },
  {
    from: '2.7.97',
    to:   '2.7.98',
    description: "Jira Feature/Epic description gains Business Objectives, Success Criteria, and a Confluence link, following up on the 2.7.97 structured template",
    notes: [
      "Follow-up to a user's structured-description request (2.7.97: " +
      "Problem Statement / Business Hypothesis / Description / Out of " +
      "Scope / NFR) -- asked what else was worth adding to a " +
      "business-level Epic. Shipped three more: Success Criteria " +
      "(closes the loop the Business Hypothesis opens), a Confluence " +
      "link (so the Epic points at the full document, not just an " +
      "excerpt), and Business Objectives (brought back as its own " +
      "compact section, distinct from the free-text Description/" +
      "Hypothesis prose)",
      "New parsers: parse_brd_business_objectives() (brd.md §2's " +
      "BO-NNN table) and parse_brd_success_criteria() (brd.md §8's " +
      "checklist items, section-scoped so a stray checkbox elsewhere " +
      "in the doc can't leak in)",
      "New brd_confluence_link()/_resolve_confluence_base_url() read " +
      "the local .specify/.confluence-drafts.json cache -- no network " +
      "call, link omitted if Confluence isn't configured or brd.md " +
      "hasn't been pushed there yet",
      "feature_extra_fields() gained an optional confluence_base_url " +
      "param (default None, fully backward compatible); " +
      "_push_epic()/_push()/_ensure_epic() thread it through from " +
      "their respective callers",
      "This Node CLI ships from the same pack sources -- this " +
      "migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "No manifest.yml schema change -- every existing Epic picks up " +
      "the two new sections and the link on its next push (idempotent " +
      "upsert). Verified: cli-python pytest 739/739 (721 pre-existing " +
      "+ 18 new), cross-reference linter clean, setup smoke tests clean",
    ],
  },
  {
    from: '2.7.98',
    to:   '2.7.99',
    description: "Packaging metadata only: PyPI/npm Summary and keywords rewritten for discoverability -- no functional change, no manifest.yml effect",
    notes: [
      "A user looked at the sddflow PyPI page and pointed out the " +
      "Summary undersold what the CLI actually does now -- it read " +
      "like a scaffolding tool, with no mention of the Jira/Confluence " +
      "sync, multi-host PR automation, or dashboard that make up most " +
      "of it",
      "cli-python/pyproject.toml's description (PyPI 'Summary') is now " +
      "'Spec-Driven Development CLI for AI coding agents -- SDLC " +
      "workflows with Jira/Confluence sync, multi-host PR automation, " +
      "and live progress dashboards'. keywords gained jira/confluence/" +
      "atlassian/pull-request/code-review/requirements/ai-agent/" +
      "claude-code for search visibility",
      "cli/package.json's description was written separately, not " +
      "copied verbatim -- this Node CLI genuinely doesn't have " +
      "Jira/Confluence integration, PR automation, or a dashboard " +
      "(cli-python-only features), so claiming them here would be " +
      "inaccurate. It now reads 'CLI for the Spec-Driven Development " +
      "(SDD) Framework -- initialize and upgrade AI-agent SDLC packs " +
      "(Claude Code, GitHub Copilot, and any AI coding tool)'",
      "This is the one migration entry in this chain that changes " +
      "nothing a user's project would notice -- no manifest.yml field, " +
      "no generated file, no CLI behavior differs. It exists purely so " +
      "a fresh install after this point reports the new sdd_version",
      "This Node CLI ships from the same pack sources -- this " +
      "migration entry exists so both CLIs report the same sdd_version " +
      "chain",
    ],
  },
  {
    from: '2.7.99',
    to:   '2.7.100',
    description: "'sdd init' now asks plan_mode and reading_mode interactively, like setup.sh already does -- both previously stayed silently at the pack default",
    notes: [
      "A user ran 'sdd init' (the pip-installed CLI, not setup.sh) and " +
      "asked when reading_mode gets asked -- it never was. init.py " +
      "only ever asked project type, project name, feature name, " +
      "scope, and AI tool; plan_mode and reading_mode were silently " +
      "left at whatever the pack's shipped manifest.yml template " +
      "defaults to ('unified'/'auto')",
      "cli-python's README already documents 'sdd init' as 'Replaces " +
      "bash setup.sh / .\\setup.ps1' -- setup.sh has asked both " +
      "interactively since v2.7.92 (reading_mode) and earlier " +
      "(plan_mode), so this was a real parity gap between the two " +
      "scaffolding entry points",
      "init_command() now asks 'Plan document style:' " +
      "(unified/separate) and 'Document reading mode:' " +
      "(auto/summary/full) right after scope, using the same option " +
      "wording as setup.sh's prompts. New --plan-mode/--reading-mode " +
      "flags skip them non-interactively",
      "sdd-micro is exempt -- its manifest.yml template has neither " +
      "field, same is_micro guard already used for scope/project_type",
      "This Node CLI ships from the same pack sources -- this " +
      "migration entry exists so both CLIs report the same sdd_version " +
      "chain",
      "No manifest.yml schema change. Verified: cli-python pytest " +
      "742/742 (739 pre-existing + 3 new)",
    ],
  },
  {
    from: '2.7.100',
    to:   '2.8.0',
    description: "Versioning scheme change: sdd_version is now a capped major.minor.patch counter (patch 0-24, minor 0-9) instead of an ever-growing patch number -- this bump is the one-time reset off the runaway old scheme",
    notes: [
      "The old scheme just incremented the patch number forever -- it " +
      "had reached 2.7.100 (a hundred patch releases within one minor " +
      "version), which a user pointed out was an awkward, hard-to-" +
      "reason-about number",
      "New scheme: patch (Z) ranges 0-24, minor (Y) ranges 0-9. " +
      "Bumping patch past 24 instead increments minor and resets patch " +
      "to 0; bumping minor past 9 instead increments major and resets " +
      "minor to 0. Equivalent to treating the version as one running " +
      "integer N = X*250 + Y*25 + Z, adding 1, and reconstituting X/Y/Z " +
      "via divmod(N, 250) then divmod(rem, 25)",
      "This specific bump (2.7.100 -> 2.8.0) is a manual, one-time " +
      "reset, not the general divmod rule applied retroactively -- the " +
      "user explicitly chose NOT to divmod the old scheme's runaway " +
      "patch count (which would have landed on 3.1.0). Every bump from " +
      "2.8.0 onward uses the plain capped rule with no further special-" +
      "casing",
      "New .claude/skills/version-bump/SKILL.md in this repo encodes " +
      "the full procedure so future bumps apply the rule consistently " +
      "instead of being computed ad hoc each time",
      "Purely a versioning/process change -- no functional CLI behavior " +
      "differs, no manifest.yml schema change. This Node CLI ships from " +
      "the same pack sources -- this migration entry exists so both " +
      "CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 742/742 (unchanged -- no code " +
      "touched), ast.parse on upgrade.py, node --check on upgrade.js",
    ],
  },
  {
    from: '2.8.0',
    to:   '2.8.1',
    description: "Node CLI gets its first automated tests -- ported cli-python's migration-chain-integrity tests to close a coverage gap flagged in code review",
    notes: [
      "An external code review pointed out that this Node CLI had zero " +
      "automated tests -- no test script in package.json, no test " +
      "files anywhere, and the node-cli-sanity CI job only ran " +
      "`node bin/sdd.js --help`. By contrast the Python CLI has " +
      "hundreds of tests covering the same surface, including a test " +
      "that verifies every MIGRATIONS entry's 'from' matches the " +
      "previous entry's 'to' and the chain ends at SDD_VERSION",
      "Both CLIs hand-mirror the same ~100-entry MIGRATIONS table on " +
      "every release (this Node CLI is scaffolding-only and doesn't " +
      "implement most of what it's narrating, per its own README) -- " +
      "until now, only the Python side had a test that would catch a " +
      "broken from/to link. A typo here would go undetected by CI " +
      "until a real user's `sdd upgrade` hit 'No migration path found'",
      "MIGRATIONS is now exported (was module-private) so a test file " +
      "can import it. New cli/tests/upgrade.test.js ports two tests: " +
      "the chain-connectivity check above, and a check that every " +
      "entry's migrate() stamps its own 'to' version",
      "Uses Node's built-in node:test/node:assert -- zero new " +
      "dependencies. New 'test': 'node --test' script in package.json, " +
      "and the node-cli-sanity CI job now runs `npm test` before the " +
      "existing --help smoke test",
      "No functional CLI behavior change, no manifest.yml schema " +
      "change -- purely closing a test-coverage gap. Verified: " +
      "cli-python pytest 742/742 (unchanged), node --test 2/2 passing, " +
      "ast.parse on upgrade.py, node --check on upgrade.js",
    ],
  },
  {
    from: '2.8.1',
    to:   '2.8.2',
    description: "'sdd upgrade' no longer needs one invocation per pending migration -- it now finds the whole chain and offers to jump straight to latest",
    notes: [
      "An external code review (point #3) flagged that " +
      "upgrade_command()/upgradeCommand() in both CLIs only ever found " +
      "and applied a single migration hop per run -- a plain match on " +
      "MIGRATIONS entries whose 'from' equals the current version. " +
      "Since 'from' is unique per entry, this structurally never " +
      "matched more than one, even though it was looped over. A " +
      "project many versions behind needed one `sdd upgrade` " +
      "invocation per pending migration to catch up. The user " +
      "confirmed this was actively painful: they're shipping new " +
      "versions every 30-40 minutes right now",
      "New pendingMigrations() walks the full linear MIGRATIONS chain " +
      "from the current version to SDD_VERSION, returning every " +
      "pending hop in order instead of just the next one",
      "With more than one migration pending, a real interactive " +
      "terminal is now asked whether to jump straight to the latest " +
      "version (apply everything now) or step through one at a time. " +
      "A non-interactive invocation -- CI, piped stdin, scripts -- " +
      "skips the prompt and defaults to jumping straight to latest, so " +
      "automation never needs N reruns to converge",
      "New flags: --to-latest (force jump, skip prompt), --step (force " +
      "one-hop-then-stop -- the original behavior, skip prompt), " +
      "-y/--yes (skip prompt, defaults to jump-to-latest)",
      "TTY detection is broken out into a small _stdinIsInteractive() " +
      "helper rather than a bare process.stdin.isTTY check, for " +
      "reliable testability",
      "cli-python/README.md and cli/README.md's 'sdd upgrade' sections " +
      "document the new prompt and flags",
      "This Node CLI ships from the same pack sources -- this " +
      "migration entry exists so both CLIs report the same sdd_version " +
      "chain",
      "No manifest.yml schema change. Verified: cli-python pytest " +
      "753/753 (742 pre-existing + 11 new), node --test 4/4 in cli/ (2 " +
      "pre-existing + 2 new -- full CliRunner-equivalent interactive-" +
      "prompt coverage wasn't ported to the Node side, a deliberate " +
      "scope limit matching this CLI's existing lighter test " +
      "investment, not an oversight). Manually smoke-tested the real " +
      "CLI: --to-latest jumps v2.0.0 -> v2.8.1 in one call, --step " +
      "applies exactly one hop and prints the rerun hint, and plain " +
      "non-interactive stdin also jumps straight to latest by default",
    ],
  },
  {
    from: '2.8.2',
    to:   '2.8.3',
    description: "Onboarding-friction fixes from an end-user feedback review: sdd-micro redirect, honest 5-minute claim, optional-persona note, cli/ marked private",
    notes: [
      "A user shared an end-user feedback review that pointed out real " +
      "onboarding friction: heavy reading load, an 8-persona team-" +
      "routing system with no signal it's optional, and -- the " +
      "sharpest finding -- no redirect toward sdd-micro for solo/" +
      "prototype users until they'd already committed real time to a " +
      "full pack's docs",
      "Added an sdd-micro redirect callout to all 5 full packs' " +
      "README.md and QUICKSTART.md intro sections. This previously " +
      "only existed in the maintainer repo's own root README.md -- a " +
      "user who copied a single pack into their own project never saw " +
      "it. Caught and fixed a self-introduced bug while implementing " +
      "this: the first draft used a relative link (../sdd-micro/) " +
      "which only resolves inside the maintainer repo; fixed to an " +
      "absolute GitHub URL that works regardless of how a user " +
      "obtained the pack",
      "Fixed QUICKSTART.md's self-contradicting headline in all 5 " +
      "packs: 'Five minutes to your first spec' was directly " +
      "contradicted by a '15-30 min' context-writing step 30 lines " +
      "later in the same file. Reframed honestly",
      "Added a one-line 'this is optional' note to the Virtual Team " +
      "persona section in all 5 packs' README.md, before the " +
      "Maya/Rex/Ava/etc. table",
      "Added \"private\": true to this package.json -- CLAUDE.md " +
      "already documents this package as 'unpublished, from source' " +
      "but nothing enforced that",
      "Not changed: the migration-table duplication between the two " +
      "CLIs -- already test-covered on both sides from a prior round, " +
      "and the review itself downgraded this to 'not urgent'",
      "This Node CLI ships from the same pack sources -- this " +
      "migration entry exists so both CLIs report the same sdd_version " +
      "chain",
      "Documentation/config-only -- no functional code touched, no " +
      "manifest.yml schema change, no CLI behavior differs. Verified: " +
      "cli-python pytest 753/753 (unchanged), cross-reference linter " +
      "clean across all 6 packs, package.json parses",
    ],
  },
  {
    from: '2.8.3',
    to:   '2.8.4',
    description: "Doc-navigation fixes from a third end-user feedback review: Start Here table, self-approval-risk callout, token/cost footprint callout",
    notes: [
      "A user shared a third, more detailed end-user feedback review " +
      "(same theme as the 2.8.3 round, different reviewer): 11 top-" +
      "level docs in each pack with no stated reading order, the self-" +
      "approval-risk disclosure buried inside CLAUDE.md (agent-facing " +
      "only, never surfaced to the human who actually needs to know " +
      "it), and no signal at all about the token/cost footprint of " +
      "running the full document-heavy pipeline",
      "Added a 'Start Here -- Which File Do I Read?' table to the top " +
      "of every full pack's README.md: 3 files to read in order " +
      "(QUICKSTART.md -> README.md -> HOW-TO-USE.md), the remaining " +
      "reference files listed separately as 'skip on first pass, come " +
      "back when you need it'",
      "Added a self-approval-risk callout to every pack's QUICKSTART.md, " +
      "right after the 'review gates work out of the box' paragraph: " +
      "default chat-mode approval only checks that someone typed " +
      "'approved' in the same conversation that wrote the doc -- no " +
      "independent identity check -- pointing to CLAUDE.md's existing " +
      "'Self-approval risk' section for the full explanation instead of " +
      "duplicating it",
      "Added a token/cost footprint callout to every pack's " +
      "QUICKSTART.md intro: describes the pipeline's actual command " +
      "cadence (one agent command per phase, each reading/writing at " +
      "least one document) rather than a fabricated dollar figure -- " +
      "confirmed there is no real token-usage data anywhere in this " +
      "repo to cite (token-pricing.yml.example ships with all rates " +
      "null); points to enabling token-pricing.yml for a real per-" +
      "command log instead",
      "sdd-fullstack's Start Here table omits the IMPROVEMENT-BACKLOG.md " +
      "row -- that pack has only 10 root .md files, unlike the other 4 " +
      "packs' 11 -- verified via a directory listing before writing the " +
      "table, not assumed",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "Documentation-only -- no functional code touched, no manifest.yml " +
      "schema change, no CLI behavior differs. Verified: cli-python " +
      "pytest 753/753 (unchanged), cross-reference linter clean across " +
      "all 6 packs, both setup smoke-test suites (15 + 12) pass",
    ],
  },
  {
    from: '2.8.4',
    to:   '2.8.5',
    description: "Surface the worked examples to real end users; implement TASK-001/002/003 of examples/todo-api for real",
    notes: [
      "Two fixes shipped together, following on from the 2.8.3/2.8.4 " +
      "onboarding-friction rounds",
      "Fix 1 (this repo's packs -- the reason this bump exists): added a " +
      "'Want to see a finished example first?' callout, linking to " +
      "examples/ on GitHub, to all 5 full packs' README.md and " +
      "QUICKSTART.md. Closes a real gap: examples/todo-api and " +
      "examples/habit-tracker-web existed and were well-built, but were " +
      "referenced from nowhere a real user running `sdd init` would ever " +
      "see them -- only from the maintainer repo's own root README.md " +
      "and the CI regression harness (assert-output.sh). A user who " +
      "only ever works inside a copied-out pack folder never knew they " +
      "existed",
      "Fix 2 (examples/ only -- does not touch any pack, included here " +
      "for the full story even though it doesn't change sdd_version-" +
      "relevant files): TASK-001 (Prisma schema + migration), TASK-002 " +
      "(user-scope Prisma extension, FR-007), and TASK-003 (POST /tasks " +
      "endpoint, UC-001) of examples/todo-api's 10-task tasks.md are now " +
      "implemented for real -- actual TypeScript/Express/Prisma/" +
      "PostgreSQL 16 code, actually run against a live local Postgres " +
      "16 instance, 13 tests actually passing (5 unit + 8 integration), " +
      "`tsc --noEmit` clean. Both worked examples had a full spec chain " +
      "(BRD through tasks.md) but zero implementation code before this",
      "tasks.md's checkboxes for TASK-001/002/003's acceptance criteria " +
      "are now [x], each with an 'Implemented:' line pointing at the " +
      "actual files. TASK-004 through TASK-010 remain spec-only, " +
      "unchanged",
      "Two simplifications are called out explicitly in the new " +
      "examples/todo-api/IMPLEMENTATION.md, not hidden: JWT " +
      "verification uses HS256 with a shared secret instead of the " +
      "RS256-from-env scheme context.md's Tech Stack row specifies; and " +
      "the three partial indexes in hld.md's raw SQL aren't expressed " +
      "in prisma/schema.prisma, since Prisma's declarative schema DSL " +
      "doesn't support partial indexes without an unstable preview " +
      "feature",
      "TASK-007 (full auth middleware wiring -- RS256 verification, " +
      "expired-JWT handling) is explicitly NOT marked done. Making " +
      "TASK-003 testable end-to-end required pulling forward a minimal " +
      "HS256 stand-in for auth.middleware.ts and user-scope." +
      "middleware.ts, but that stand-in does not satisfy TASK-007's own " +
      "acceptance criteria and its checkboxes were left unchecked",
      "No simulated /pre-review or /address-review round is included -- " +
      "there's no real reviewer for a maintainer-repo example, and " +
      "simulating one would read as staged rather than as proof",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 753/753 (unchanged), cross-reference " +
      "linter clean across all 6 packs, both setup smoke-test suites " +
      "(15 + 12) pass, assert-output.sh's 33 structural assertions still " +
      "pass, and the new examples/todo-api test suite itself: 13/13 " +
      "passing, tsc --noEmit clean, prisma migrate dev applied clean " +
      "against a freshly created PostgreSQL 16 database",
    ],
  },
  {
    from: '2.8.5',
    to:   '2.8.6',
    description: "Dashboard: per-stage duration, review-round count, and an overall feature Timeline card",
    notes: [
      "User request: 'sdd dashboard' showed each document's status but " +
      "not how long each stage took, how many review rounds it went " +
      "through, or an overall feature start/end",
      "Added per-document Created date, Approved date, duration (in " +
      "days), and revision-round count -- computed from the document's " +
      "own '## Version History' table, data that was already being " +
      "written by the shared review-decision-step block but never read " +
      "back out anywhere. First row = creation date; when Status says " +
      "Approved, the last row is always the approval event; " +
      "revision_rounds counts actual version bumps, not every review " +
      "check -- a pure re-read-and-approve with no edit isn't counted",
      "Added a feature-level Timeline card: start_date is the earliest " +
      "document's created date, end_date is release.md's approved date " +
      "(falls back to its own Approvals-table Date column), duration in " +
      "days once both resolve",
      "Required standardizing the {date} placeholder across every doc " +
      "template to {date: YYYY-MM-DD} so dates are machine-parseable. " +
      "Old documents, or any hand-edited date that isn't ISO 8601, " +
      "simply don't show duration/rounds -- no warning badge, nothing " +
      "else on the page affected (an explicit choice this round, not " +
      "assumed)",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain. The " +
      "dashboard itself is Python-only (cli-python's `sdd dashboard`) " +
      "-- this bump has no corresponding functional change on the Node " +
      "CLI side",
      "Verified: cli-python pytest 765/765 (753 pre-existing + 12 new), " +
      "cross-reference linter clean across all 6 packs, both setup " +
      "smoke-test suites (15 + 12), assert-output.sh's 33 structural " +
      "assertions, the embedded dashboard JS re-verified with `node " +
      "--check`, and a live end-to-end smoke test against a synthetic " +
      "project confirming /api/status and the rendered page both work",
    ],
  },
  {
    from: '2.8.6',
    to:   '2.8.7',
    description: "Removed IMPROVEMENT-BACKLOG.md from every pack -- it was maintainer-only content that sdd init was shipping into every real user's project",
    notes: [
      "A user shared a photo of their own project directory (created via " +
      "`sdd init`) showing IMPROVEMENT-BACKLOG.md sitting right there " +
      "alongside README.md/QUICKSTART.md/etc. -- confirming a real bug",
      "IMPROVEMENT-BACKLOG.md existed in 4 of the 5 full packs as the " +
      "*maintainer's own* internal notes about deferred pack-template " +
      "work. Nothing about it concerned an end user's own project",
      "Root cause: scaffold_pack() (cli-python's sdd/utils/scaffold.py) " +
      "copies a pack's entire folder into a user's project with zero " +
      "exclusion filter -- unlike package.sh's zip builder, which " +
      "already excludes .git/ and CLAUDE.local.md",
      "Fix: deleted the file from all 4 packs (rather than adding an " +
      "exclusion-list mechanism -- the user's explicit choice), removed " +
      "its row from each pack's README.md 'Start Here' table, and " +
      "consolidated the actual content into this maintainer repo's own " +
      "OWNER-GUIDE.md, which is already explicitly the maintainer-only " +
      "document",
      "No functional code changed. A project that already has " +
      "IMPROVEMENT-BACKLOG.md from an earlier `sdd init` keeps its local " +
      "copy -- this migration doesn't delete anything from an existing " +
      "project, it only stops the file from being scaffolded into new " +
      "ones",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 765/765 (unchanged), cross-reference " +
      "linter clean across all 6 packs, both setup smoke-test suites " +
      "(15 + 12), and a live smoke test running `sdd init` end-to-end " +
      "confirming the scaffolded output no longer includes " +
      "IMPROVEMENT-BACKLOG.md",
    ],
  },
  {
    from: '2.8.7',
    to:   '2.8.8',
    description: "Root README '60-Second Overview' and a pack-catalog pointer on every pack's own README -- fixes a first-time-visitor orientation gap",
    notes: [
      "An external (ChatGPT) review flagged that a newcomer to the " +
      "maintainer repo's root README can't quickly answer 7 orientation " +
      "questions: which pack, which CLI, the smallest useful workflow, " +
      "how many documents get generated, whether Jira/Confluence is " +
      "required, the first 3 commands to run, and whether this is for " +
      "solo devs or teams. Most were partially answered already, just " +
      "buried rather than absent",
      "Added a '60-Second Overview' section to the top of the " +
      "maintainer repo's root README.md: one audience line plus a " +
      "4-row table -- CLI + Jira/Confluence optionality, the first 3 " +
      "commands, document count, and a pointer to packs/CATALOG.md's " +
      "decision tree",
      "The document-count figure (12 at pilot scope) was counted " +
      "directly from the real examples/todo-api file listing, not " +
      "guessed -- an initial draft said '~13' and was corrected against " +
      "the actual file count before shipping",
      "Added a one-line 'not sure this is the right pack? see the " +
      "catalog' pointer (absolute GitHub URL) to the top of the 'Start " +
      "Here' section in all 5 full packs' own README.md, so a visitor " +
      "who lands directly on one pack's page still gets routed to the " +
      "decision tree",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain. " +
      "Documentation-only: no functional code touched",
      "Verified: cli-python pytest 765/765 (unchanged), cross-reference " +
      "linter clean across all 6 packs, both setup smoke-test suites " +
      "(15 + 12)",
    ],
  },
  {
    from: '2.8.8',
    to:   '2.8.9',
    description: "Dashboard security hardening: session token + Origin check for network writes, read-only sharing mode, and a fix for a real concurrent-write data-loss bug",
    notes: [
      "Highest-priority item from a comprehensive ChatGPT-review " +
      "verification pass -- closes real, live gaps, not hypothetical " +
      "ones. Dashboard write endpoints had zero authentication when " +
      "bound to a non-loopback address, only a printed console " +
      "warning. There was also an unguarded concurrent-write race on " +
      ".dashboard-comments.json -- verified with a 12-thread " +
      "concurrency test that fails 5/5 without a lock and passes " +
      "reliably with the fix",
      "New --share flag (shortcut for --host 0.0.0.0) and --write flag " +
      "(required to enable writes over a non-local bind). Three modes: " +
      "`sdd dashboard` (unchanged -- 127.0.0.1, writes enabled, no " +
      "token), `sdd dashboard --share` (network-reachable, read-only " +
      "by default), `sdd dashboard --share --write` (network-" +
      "reachable, writes gated by a session token)",
      "Session token via a custom X-SDD-Token header, not a cookie -- " +
      "a cookie would be sent automatically on any cross-origin " +
      "request (that's what makes CSRF possible); a custom header " +
      "only goes out on requests this page's own JS explicitly " +
      "builds, so this one mechanism covers both session-token auth " +
      "and CSRF protection. Delivered via a one-time ?token= query " +
      "param on the auto-opened URL, then stripped from the visible " +
      "URL via history.replaceState",
      "Origin/Host header check as defense in depth on top of the " +
      "token, checked first so a mismatched Origin is rejected even " +
      "if a token somehow leaked",
      "New GET /api/dashboard-info endpoint (never includes the token " +
      "itself) drives an in-page network-sharing banner and hides/" +
      "disables write controls when read-only -- the existing printed " +
      "console warning was invisible to anyone using the dashboard " +
      "from a different machine",
      "The default `sdd dashboard` invocation (no flags) is completely " +
      "unaffected -- all 49 pre-existing dashboard tests still pass " +
      "unchanged",
      "This Node CLI ships from the same pack sources -- this " +
      "migration entry exists so both CLIs report the same " +
      "sdd_version chain. The dashboard itself is Python-only -- no " +
      "corresponding functional change on the Node CLI side",
      "Verified: cli-python pytest 773/773 (765 pre-existing + 8 new), " +
      "plus three live end-to-end smoke tests against a real running " +
      "server in all three modes",
    ],
  },
  {
    from: '2.8.9',
    to:   '2.8.10',
    description: "manifest.py atomic writes + corrupt-file handling, and timeout/retry/backoff for all Jira/Confluence HTTP calls",
    notes: [
      "Next tier from the same ChatGPT-review verification pass, closing " +
      "two more real (not hypothetical) gaps found while verifying the " +
      "review's claims against the actual code",
      "manifest.py: write_manifest() previously wrote directly to " +
      ".specify/manifest.yml with write_text() -- a process killed mid-" +
      "write (e.g. `sdd upgrade` interrupted) could leave a truncated " +
      "file, and every command reads this file, so a truncated manifest " +
      "broke the whole project. Now writes to a temp file in the same " +
      "directory and os.replace()s it into place, which is atomic on " +
      "both POSIX and Windows",
      "manifest.py: read_manifest() previously let a corrupt YAML file " +
      "raise a raw yaml.YAMLError with no guidance. Now wraps the parse " +
      "in try/except and raises a new ManifestError with an actionable " +
      "message (fix by hand, restore from git, or delete and re-run " +
      "`sdd init`). A *missing* manifest still returns None as before -- " +
      "a corrupt manifest means the project clearly exists, so silently " +
      "treating it the same as absent risked a caller re-scaffolding " +
      "over it or quietly dropping real config",
      "atlassian_auth.py: every Jira/Confluence API call goes through a " +
      "requests.Session built by build_session() -- a flaky network " +
      "blip or an Atlassian rate limit previously surfaced as a raw " +
      "unhandled stack trace mid-workflow, since requests has no " +
      "default timeout and no retry logic. Fixed once, centrally, by " +
      "mounting a custom HTTPAdapter on the shared session instead of " +
      "touching the ~25 individual call sites across jira_client.py and " +
      "confluence_client.py: a 20-second default timeout, plus 3 " +
      "retries with exponential backoff on connection errors and on " +
      "429/500/502/503/504 responses, honoring a 429's Retry-After " +
      "header",
      "Retries apply to every HTTP method including POST/PUT -- this " +
      "codebase's writes already lean on label-based find-before-create " +
      "idempotency where duplication would matter, and a connection " +
      "blip silently aborting a document approval or Jira push partway " +
      "through is worse than the small remaining risk of an occasional " +
      "duplicate retry on a genuinely dropped response",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain. " +
      "Both fixes are Python-only (manifest.py and atlassian_auth.py " +
      "have no Node CLI equivalent) -- no functional change on the " +
      "Node CLI side",
      "Verified: cli-python pytest 789/789 (773 pre-existing + 11 " +
      "manifest.py tests + 5 atlassian_auth.py resilience tests), " +
      "including atomicity proven via a monkeypatched os.replace() and " +
      "the retry logic proven against a real flaky local HTTP server " +
      "plus a control-case test showing a plain session without the " +
      "adapter genuinely fails on the same server",
    ],
  },
  {
    from: '2.8.10',
    to:   '2.8.11',
    description: "Fix a real Python 3.9 import crash (PEP 604 `X | None` used without `from __future__ import annotations`) plus a ruff lint/format pass",
    notes: [
      "Real bug, not a lint nitpick: 7 modules used `str | None` / " +
      "`dict | None` union syntax directly in function signatures with " +
      "no `from __future__ import annotations` at the top of the file. " +
      "PEP 604's `X | Y` union syntax is only evaluable at runtime from " +
      "Python 3.10 onward -- on 3.9 (which pyproject.toml's own " +
      "requires-python and classifiers claim to support), importing any " +
      "of these modules raised a TypeError at function-definition time, " +
      "before a single line of the CLI's own logic ever ran. Caught by " +
      "ruff's FA102 rule while setting up CI's new ruff job -- and would " +
      "have been caught immediately by the Python 3.9 CI matrix job " +
      "added one round earlier, since that job would fail on `sdd " +
      "--help` alone",
      "Added ruff to CI (ruff check + ruff format --check), configured " +
      "in cli-python/pyproject.toml. Ran a full pass first: fixed or " +
      "noqa'd (with a reason comment) everything ruff's default ruleset " +
      "flagged except two deliberately-ignored rules -- ISC004 (674 " +
      "hits, this codebase's own style of writing long prose as adjacent " +
      "string literals in lists, not a bug) and BLE001 (67 hits, " +
      "`except Exception:` -- flagged for a dedicated manual triage " +
      "pass, tracked separately, not blanket-suppressed or blanket-" +
      "narrowed blind)",
      "Applied ruff format across the whole package as its own prior " +
      "isolated commit (no functional change, same test results before/" +
      "after) so this commit's diff isn't dominated by pure reformatting " +
      "noise",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain. Both " +
      "fixes are Python-only; no Node CLI equivalent exists for either",
      "Verified: cli-python pytest 789/789 (unchanged pass count " +
      "throughout this round), ruff check and ruff format --check both " +
      "clean, and the specific fix confirmed via `ruff check . --select " +
      "FA102` going from 11 hits to 0",
    ],
  },
  {
    from: '2.8.11',
    to:   '2.8.12',
    description: "Dashboard: confirmation dialog before an approval takes effect; dashboard HTML/CSS/JS moved from one giant Python string to real .css/.js/.html files",
    notes: [
      "Real, user-visible dashboard behavior change: clicking Approve used " +
      "to fire straight to the server after two window.prompt() calls " +
      "(name, optional note). Now shows a window.confirm() summarizing " +
      "the document, feature, approver name, and note before the request " +
      "goes out, and bails out entirely if declined -- guards against an " +
      "accidental click by an already-authorized user (the bigger risk, " +
      "an *unauthorized* person approving, was already closed by the " +
      "session-token work two rounds back)",
      "Also (no user-visible difference, verified byte-identical): the " +
      "dashboard's HTML/CSS/JS -- previously one ~1050-line Python " +
      "triple-quoted string -- now lives in real files under " +
      "sdd/commands/dashboard_static/, assembled into the same single " +
      "self-contained HTML response at import time. No new HTTP routes, " +
      "no extra round-trips",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain. The " +
      "dashboard is Python-only -- no corresponding change on the Node " +
      "CLI side",
      "Verified: cli-python pytest 793/793 (789 pre-existing + 4 new), " +
      "ruff check/format, mypy, and bandit all clean, coverage still 79%, " +
      "and a real wheel build + clean-venv install confirming the " +
      "dashboard's static files ship correctly",
    ],
  },
  {
    from: '2.8.12',
    to:   '2.8.13',
    description: "Add lean/standard/regulated as friendly aliases for pilot/mvp/full scope",
    notes: [
      "Real gap the review flagged: examples/todo-api (a real pilot-scope " +
      "run) generates exactly 12 documents, and 'pilot' reads as a small, " +
      "informal effort right up until a team sees the actual document " +
      "count. A full rename of the scope vocabulary would be a breaking " +
      "change to manifest.yml's schema and every pack's scope-gating " +
      "logic, so this ships a much smaller, safe version instead: lean/" +
      "standard/regulated are accepted as friendlier input names " +
      "wherever scope is set (setup.sh/setup.ps1's --scope, sdd init's " +
      "-s/--scope), resolved to the canonical pilot/mvp/full before " +
      "anything is written. manifest.yml's own scope: field never sees " +
      "the aliases -- no downstream logic needed to change",
      "Also added real input validation that didn't exist before: an " +
      "unrecognized --scope value is now rejected with a clear error " +
      "instead of being silently written into manifest.yml as-is",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain. The " +
      "Node CLI's own init/upgrade scaffolding doesn't take a --scope " +
      "flag today, so there's no corresponding code change on that side",
      "Verified: cli-python pytest 797/797 (793 pre-existing + 4 new), " +
      "ruff check/format, mypy, and bandit all clean, coverage still " +
      "79%; setup.sh smoke suite extended with 3 alias-resolution cases " +
      "+ 1 invalid-scope rejection case, cross-reference checker and " +
      "sync-drift check both clean across all 6 packs",
    ],
  },
  {
    from: '2.8.13',
    to:   '2.8.14',
    description: "Dashboard: require the session token for /api/review-links even in read-only --share mode",
    notes: [
      "Closes a gap found during a second external review pass: read-only " +
      "share mode (--share without --write) already blocked POST /api/" +
      "approve and /api/comment without a token, but GET /api/review-links " +
      "was never gated at all -- it makes a live call to Jira/Confluence " +
      "using the credentials stored on the machine running `sdd " +
      "dashboard`, for whatever --feature the caller names, regardless of " +
      "read-only status. 'Read-only' only ever meant 'no local file " +
      "writes'; it never meant 'no outbound calls under this machine's " +
      "credentials'",
      "Fix: token generation now happens for any non-local bind " +
      "(previously only when --write was also passed), and a new " +
      "_check_review_links_access() helper (reusing the existing Origin+" +
      "token check) gates the /api/review-links handler, skipped only " +
      "when the bind is local. Approve/comment endpoints are unchanged",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain. The " +
      "Node CLI has no dashboard command, so there's no corresponding " +
      "code change on that side",
      "Verified: cli-python pytest 817/817 (812 pre-existing + 5 new " +
      "access-control tests for /api/review-links), ruff check/format, " +
      "mypy, and bandit all clean",
    ],
  },
  {
    from: '2.8.14',
    to:   '2.8.15',
    description: "Add package-verify CI job proving a clean pip install actually works; add sdd init --ai-tool flag",
    notes: [
      "A second external review round flagged that CI never verifies the " +
      "packaging path end to end: sdd/packs/ is gitignored and only " +
      "populated by publish.sh's manual bundling step right before a " +
      "real PyPI upload. Proven to be a live bug: a wheel built the way " +
      "CI already builds it, installed into a venv outside the repo, and " +
      "run via `sdd init`, failed with 'SDD pack files not found.' -- " +
      "scaffold.py's dev-fallback silently masked this in every " +
      "environment that still had the full repo checked out",
      "New 'package-verify' CI job bundles packs like publish.sh does, " +
      "builds sdist+wheel, asserts both contain sdd/packs/sdd-universal/" +
      "setup.sh, installs the wheel into a clean venv, and runs a full " +
      "`sdd init` from outside the repo -- the exact reproduction that " +
      "surfaced the bug, now guarded permanently in CI. The same " +
      "assertion also runs inside publish.sh itself between build and " +
      "upload",
      "Running sdd init fully non-interactively for that CI job surfaced " +
      "a separate real gap: every other prompt (project type, scope, " +
      "plan mode, reading mode) already had a CLI flag override, but " +
      "'Which AI tool will you use?' did not. Added --ai-tool (claude-" +
      "code | copilot | cursor | windsurf | other), validated the same " +
      "way --scope is",
      "This Node CLI ships from the same pack sources -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain. The " +
      "Node CLI's own init scaffolding has no AI-tool prompt to begin " +
      "with, so there's no corresponding code change on that side",
      "Verified: cli-python pytest 819/819 (817 pre-existing + 2 new " +
      "--ai-tool tests), ruff check/format, mypy, and bandit all clean; " +
      "the full package-verify sequence was run manually end to end " +
      "before adding it to CI",
    ],
  },
  {
    from: '2.8.15',
    to:   '2.8.16',
    description: "Fix a silent detect.js bug: Terraform (.tf) projects were never detected as iac",
    notes: [
      "This file's own Terraform-file check called require('fs')." +
      "readdirSync(...) inside a try/catch -- but this file is loaded as " +
      "an ES module ('type': 'module' in package.json), where require " +
      "is not defined at all. The resulting ReferenceError was silently " +
      "swallowed by the catch, so this branch always returned false: a " +
      "pure-Terraform project with no Pulumi.yaml or cdk.json was never " +
      "detected as 'iac'",
      "Fixed by importing readdirSync at the top of detect.js alongside " +
      "the module's other fs calls, instead of a runtime require(). " +
      "Verified the bug and the fix directly: require('fs') throws " +
      "'require is not defined' in a real ESM context, and a scratch " +
      "directory containing only a .tf file now correctly detects as " +
      "'iac' where it previously fell through to null",
      "New tests/detect.test.js covers this case directly -- there was " +
      "no detect.js test coverage at all before this",
      "cli-python's own detect.py does exact dependency-key matching (no " +
      "shell-out, no require()) and was never affected -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "Verified: node --test 6/6 (4 pre-existing + 2 new), npm test and " +
      "the --help smoke test both pass",
    ],
  },
  {
    from: '2.8.16',
    to:   '2.8.17',
    description: "Widen js-yaml's declared range; friendly error on dashboard port conflict; make dashboard's page assembly lazy",
    notes: [
      "This package's js-yaml dependency was pinned to ^4.1.0 " +
      "(effectively <5.0.0), even though an earlier fix (import * as " +
      "yaml, not the default export) already made the code work " +
      "correctly under js-yaml 5.x -- verified again here by actually " +
      "installing js-yaml@5.2.3 and re-running the full test suite + " +
      "--help smoke test. Widened to >=4.1.0 <6.0.0 so users aren't held " +
      "back from picking up js-yaml security/bug fixes for no real " +
      "reason",
      "The other two changes in this release (a friendly error on `sdd " +
      "dashboard` port conflicts instead of a raw traceback, and making " +
      "the dashboard's HTML page assembly lazy instead of running at " +
      "CLI-import time) are cli-python-only -- this Node CLI has no " +
      "dashboard command",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "Verified: npm test and the --help smoke test both pass under " +
      "js-yaml 5.2.3",
    ],
  },
  {
    from: '2.8.17',
    to:   '2.8.18',
    description: "Fix two real project-type misdetection bugs; add ~20-fixture cross-implementation test coverage",
    notes: [
      "Building a shared fixture-test suite across all detection " +
      "implementations surfaced two real, previously-unnoticed bugs, " +
      "fixed alongside the new tests:",
      "(1) setup.sh/setup.ps1 (sdd-universal's auto-detect): a plain " +
      "substring/word-boundary check on 'react-native' also matched " +
      "'react-native-web' -- a real npm package for running React " +
      "Native components on the web, not a mobile project. detect.py/" +
      "detect.js already did exact list/array membership and never had " +
      "this bug",
      "(2) this file's own Angular check used d.startsWith('angular'), " +
      "which no real Angular 2+ project satisfies -- they depend on " +
      "scoped packages like '@angular/core', which start with '@', not " +
      "'angular'. Fixed by switching to a substring check, matching " +
      "setup.sh/setup.ps1's existing (correct) behavior",
      "New tests/detect.test.js (extended) now asserts ~20 synthetic " +
      "project fixtures, the same set mirrored in cli-python/tests/" +
      "test_detect.py and packs/_shared/tests/test-detect-fixtures.sh -- " +
      "there was no dedicated detection test coverage at all before this",
      "This migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "Verified: node --test 27/27, npm test and the --help smoke test " +
      "both pass",
    ],
  },
  {
    from: '2.8.18',
    to:   '2.8.19',
    description: "Add Python 3.13 and 3.14 to the tested/declared version range",
    notes: [
      "cli-python's CI matrix only covered 3.9-3.12, but pypistats.org's " +
      "own download breakdown for sddflow showed real installs already " +
      "happening on Python 3.14 with zero CI coverage for it -- " +
      "prompted by a real user question about when 3.9 support was " +
      "added, which surfaced the matrix was stale on the new-version " +
      "end too, not just the old-version end",
      "Added '3.13' and '3.14' to python-cli-sanity's matrix, and the " +
      "matching classifiers to cli-python/pyproject.toml. Verified with " +
      "a real Python 3.13.12 interpreter: clean pip install, byte-" +
      "compile, --help smoke test, and the full pytest suite (848/848) " +
      "all pass unchanged. Python 3.14 was verified via CI's " +
      "actions/setup-python, not locally",
      "This Node CLI has no equivalent Python version matrix (it's a " +
      "Node.js package) -- this migration entry exists so both CLIs " +
      "report the same sdd_version chain, and no code change was needed " +
      "here",
      "Verified: node --test 27/27, npm test and the --help smoke test " +
      "both pass",
    ],
  },
  {
    from: '2.8.19',
    to:   '2.8.20',
    description: "Drop Python 3.9 support -- requires-python is now >=3.10",
    notes: [
      "Python 3.9 reached end-of-life in October 2025 (no more security " +
      "patches from CPython upstream) -- a deliberate maintainer " +
      "decision to stop supporting it in cli-python, made right after " +
      "the previous release added 3.13/3.14 to the tested range and " +
      "prompted a look at the old end of the matrix too",
      "cli-python's requires-python bumped from '>=3.9' to '>=3.10'; " +
      "the '3.9' classifier and CI matrix entry removed. Real breaking " +
      "change -- `pip install sddflow` now refuses outright on Python " +
      "3.9, verified by inspecting the built wheel's METADATA directly",
      "This Node CLI has no Python version floor of its own (it's a " +
      "Node.js package, unaffected) -- this migration entry exists so " +
      "both CLIs report the same sdd_version chain",
      "Verified: node --test 27/27, npm test and the --help smoke test " +
      "both pass",
    ],
  },
  {
    from: '2.8.20',
    to:   '2.8.21',
    description: "Fix a severe bug: every interactive `sdd init` (and " +
      "the AI-tool prompt in `sdd upgrade`) crashed with " +
      "UnknownPromptTypeError",
    notes: [
      "Dependabot bumped this CLI's inquirer dependency from 9.2.0 to " +
      "14.0.2 (merged into main, inherited by this repo's release " +
      "branch during an earlier PR's merge-conflict resolution). " +
      "inquirer 9+ dropped the legacy 'list' prompt type in favor of " +
      "'select' -- inquirer.prompt() throws for any unregistered type " +
      "string, so this broke every interactive sdd init for anyone " +
      "not passing every single CLI flag (there's no flag to skip the " +
      "AI-tool prompt)",
      "Found by actually running a real interactive `sdd init` against " +
      "a clean install of the live, already-published npm package " +
      "while answering an unrelated question about functional parity " +
      "between the two CLIs -- none of the existing automated tests " +
      "caught this because they only exercised migration-chain logic, " +
      "never a real inquirer prompt call",
      "Fixed src/commands/init.js (5 occurrences) and " +
      "src/commands/upgrade.js (1 occurrence): type: 'list' -> " +
      "type: 'select'. Also fixed a silent secondary bug in init.js's " +
      "scope prompt: the new @inquirer/select prompt's `default` " +
      "option is compared against the choice's *value*, not an index " +
      "into the choices array like the old 'list' type -- " +
      "SCOPES.indexOf(...) was replaced with the actual default scope " +
      "value",
      "Added tests/inquirer-prompt-types.test.js: a regression test " +
      "that scans every inquirer.prompt() call in src/commands/*.js, " +
      "extracts each type: '...' string used, and asserts it's a " +
      "member of the installed inquirer's own currently-registered " +
      "prompt types (read live from inquirer.prompt.prompts, not " +
      "hardcoded) -- a future inquirer upgrade that renames or drops " +
      "a type this codebase depends on now fails this test " +
      "immediately instead of only surfacing as a crash for a real " +
      "user",
      "cli-python never used inquirer and is unaffected by the " +
      "underlying bug -- this migration entry exists so both CLIs " +
      "report the same sdd_version chain",
      "Verified: real clean install of the fixed CLI, real PTY-based " +
      "interactive `sdd init` run (piped stdin doesn't work against " +
      "modern @inquirer/* prompts, which require raw-mode TTY input) " +
      "confirmed the full flow completes and writes a correct " +
      "manifest.yml; node --test 28/28 (27 pre-existing + 1 new); " +
      "cli-python pytest 848/848",
    ],
  },
  {
    from: '2.8.21',
    to:   '2.8.22',
    description: "Fix a real Confluence-review-loop bug: `sdd confluence " +
      "pull` flattened every markdown table into one run-on line",
    notes: [
      "Reported by a user testing the Confluence review round-trip on a " +
      "real project: create a draft via `sdd confluence draft`, edit it " +
      "in Confluence, then `sdd confluence pull` to bring the edits " +
      "back. Every markdown table in the pulled-back document came " +
      "back as a single line of concatenated cell text with no row or " +
      "column structure -- silently corrupting any table-heavy doc " +
      "(Tech Stack in context.md, and BRD/SRD/design docs generally)",
      "Root cause: cli-python's sdd/utils/cf_to_md.py (the Confluence-" +
      "storage-format-to-Markdown converter used by `confluence pull`) " +
      "had no <table> handling at all -- with no table-aware step, its " +
      "final 'strip any remaining HTML tags' pass just deleted the " +
      "table/row/cell tags and left the cell text jammed together, " +
      "since it never inserted a newline or delimiter for table " +
      "structure the way it does for <li> and <p>",
      "This is the same bug class the push direction (md_to_cf.py) " +
      "already had fixed once before -- the pull direction just never " +
      "got the equivalent treatment",
      "This Node CLI has no Confluence integration at all " +
      "(scaffolding-only by design) and is unaffected -- this " +
      "migration entry exists so both CLIs report the same sdd_version " +
      "chain",
      "Verified: cli-python pytest 858/858 (848 pre-existing + 10 new " +
      "regression tests in tests/test_cf_to_md.py); ruff check/format " +
      "and mypy both clean",
    ],
  },
  {
    from: '2.8.22',
    to:   '2.8.23',
    description: "Fix two real integrations.yml bugs: `sdd jira push " +
      "--level epic` crashed with a raw AttributeError on a malformed " +
      "config value, and a bare `sdd confluence push` never included " +
      "the Constitution page",
    notes: [
      "Bug 1 -- reported by a user: `sdd jira push --level epic` " +
      "crashed with `AttributeError: 'dict' object has no attribute " +
      "'replace'` deep inside jira_client.py's find_by_label(). Root " +
      "cause (found by the user): a hand-edited integrations.yml had a " +
      "second `project_key:` block under `jira:` that should have been " +
      "`project_keys:` (plural) -- YAML silently keeps only the LAST " +
      "occurrence of a duplicate mapping key, so a plain string was " +
      "clobbered by a dict",
      "Fixed with two hardening layers in cli-python's " +
      "sdd/utils/integrations.py: a custom PyYAML loader that rejects " +
      "duplicate mapping keys at parse time (naming the exact line and " +
      "suggesting the likely fix for 'project_key'), and type " +
      "validation in JiraConfig.key_for()/parent_field_for() that " +
      "raises a clear error naming the bad YAML key instead of letting " +
      "a malformed value crash a low-level HTTP helper three call " +
      "frames later",
      "Also fixed a related naming gap: the CLI's own `--level epic` " +
      "flag has no relationship to the config-facing level key " +
      "'feature' used throughout project_keys/custom_fields_by_level/ " +
      "parent_field_by_level, so `project_keys: {epic: SUN}` -- the " +
      "natural thing to write -- was silently ignored. 'epic' is now a " +
      "bidirectional alias for 'feature'",
      "Bug 2 -- a bare `sdd confluence push` (no --doc, the normal flow " +
      "right after create-context) never included the Constitution " +
      "page: both the code's default page_map fallback and the " +
      "`sdd config init` wizard's generated page_map omitted the " +
      "'constitution' key, even though the full " +
      "integrations.yml.example reference file already had it. Fixed " +
      "by adding it to both",
      "This Node CLI has no Jira/Confluence integration at all " +
      "(scaffolding-only by design) and is unaffected by either fix -- " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "Verified: cli-python pytest 869/869 (858 pre-existing + 11 new); " +
      "ruff check/format clean; mypy --ignore-missing-imports (matching " +
      "CI's exact invocation) clean with no issues in 31 source files",
    ],
  },
  {
    from: '2.8.23',
    to:   '2.8.24',
    description: "Fix dashboard GATE-1 false positive: token-usage.md " +
      "alone in a feature directory was mistaken for a real downstream " +
      "spec doc, showing 'GATE-1 -- Constitution Finalized' as passed " +
      "immediately after /specify, before the user ever confirmed " +
      "finalization in chat",
    notes: [
      "Reported by a user: the dashboard showed a checkmark next to " +
      "'GATE-1 -- Constitution Finalized' right after /specify created " +
      "the constitution DRAFT, even though they had never told the " +
      "agent 'Constitution Part 2 finalized' in chat",
      "Root cause: constitution.md has no machine-readable Draft/" +
      "Finalized flag by design (GATE-1 confirmation is chat-only), so " +
      "cli-python's status.py infers gate1_inferred purely from whether " +
      "any file besides tasks.md/*.summary.md exists in " +
      ".specify/features/{feature}/. But token-usage.md is written into " +
      "that same directory by /specify itself (and even /create-context, " +
      "which runs before /specify) whenever token-pricing.yml is " +
      "configured -- both commands run before GATE-1 can possibly pass. " +
      "A project with token logging enabled hit a false positive on " +
      "every single run",
      "Fixed in cli-python's sdd/utils/status.py: token-usage.md now " +
      "joins tasks.md in the set of filenames excluded from the " +
      "any_downstream check",
      "This Node CLI has no dashboard at all (scaffolding-only by " +
      "design) and is unaffected -- this migration entry exists so both " +
      "CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 871/871 (869 pre-existing + 2 new); " +
      "ruff check/format and mypy --ignore-missing-imports (matching " +
      "CI's exact invocation) both clean on the changed files",
    ],
  },
  {
    from: '2.8.24',
    to:   '2.8.25',
    description: "Fix dashboard 'not set in roles.yml' false negative: a " +
      "fully filled-in roles.yml still showed no expected approver, " +
      "because every real template's Approvals table Role cell carries " +
      "a RACI annotation the role-key matcher never stripped",
    notes: [
      "Reported by a user: filled in every role in roles.yml (real " +
      "names for product_owner, business_analyst, etc.), but the " +
      "dashboard's BRD Approvals detail panel still showed nothing for " +
      "the pending rows",
      "Root cause: cli-python's status.py normalizes a document's " +
      "Approvals-table Role cell text to roles.yml's snake_case key " +
      "convention ('Product Owner' -> 'product_owner') to match the " +
      "two up. But every shipped template's actual Role cell carries a " +
      "RACI annotation in parentheses -- e.g. brd-template.md's real " +
      "text is 'Product Owner (accountable -- business objectives " +
      "sign-off)', not bare 'Product Owner'. Normalizing the full " +
      "string never matched any roles.yml key -- a 100% miss rate " +
      "across every role, in every document, in every project",
      "Fixed in cli-python's sdd/utils/status.py: the role-key " +
      "normalizer now strips everything from the first '(' onward " +
      "before matching",
      "This Node CLI has no dashboard at all (scaffolding-only by " +
      "design) and is unaffected -- this migration entry exists so " +
      "both CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 874/874 (871 pre-existing + 3 new); " +
      "ruff check/format and mypy --ignore-missing-imports (matching " +
      "CI's exact invocation) both clean on the changed files",
    ],
  },
  {
    from: '2.8.25',
    to:   '2.8.26',
    description: "Fix 'Error loading the extension!' on Confluence: the " +
      "Jira review status banner used a macro name Confluence doesn't " +
      "actually have",
    notes: [
      "Reported by a user: right after approving a BRD, its Confluence " +
      "page showed 'Error loading the extension!' where the 'Jira " +
      "review: VALT-1 -- Approved' banner should be",
      "Root cause: cli-python's review.py maps review status to a " +
      "Confluence panel macro name -- {'APPROVED': 'success', " +
      "'NEEDS_REVISION': 'warning'}, default 'info'. Confluence's " +
      "built-in panel macros are only info/tip/note/warning -- there is " +
      "no 'success' macro, so the page tried to render an unregistered " +
      "extension. Invisible until now because PENDING (the only status " +
      "a fresh review ticket starts in) correctly used 'info' -- the " +
      "bug only fires once a real document reaches APPROVED",
      "Fixed by mapping APPROVED to 'tip' (a real Confluence panel " +
      "macro, renders as a green highlighted box) instead of the " +
      "nonexistent 'success'",
      "This Node CLI has no Jira/Confluence integration at all " +
      "(scaffolding-only by design) and is unaffected -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 874/874; ruff check/format clean; " +
      "mypy --ignore-missing-imports (matching CI's exact invocation) " +
      "clean on the changed files",
    ],
  },
  {
    from: '2.8.26',
    to:   '2.8.27',
    description: "Standardize the {Feature Name} document-header " +
      "placeholder on manifest.yml project.name -- it previously had " +
      "no defined source and silently drifted to context.md's own " +
      "title instead",
    notes: [
      "Reported by a user: a generated BRD's '# Feature: {Feature " +
      "Name}' header showed 'NIPE Validation Service' while " +
      "manifest.yml said name: Validation -- the two had silently " +
      "diverged",
      "Root cause: {Feature Name} is used as a header placeholder in " +
      "~20 templates across every pack, but only ONE place in any " +
      "prompt file ever explicitly defined what it should resolve to " +
      "(the Jira Epic Summary line in specify-brd.prompt.md). Every " +
      "document-header instance was left to each session's judgment, " +
      "so it could drift to context.md's own free-text title instead",
      "Fixed by adding a new shared block, " +
      "_shared/blocks/feature-name-convention.md, inserted into each " +
      "pack's CLAUDE.md right after the 'Confirm: project.name, scope, " +
      "feature, context_file' startup step. States explicitly: " +
      "{Feature Name} = manifest.yml project.name (fallback " +
      "project.feature), never context.md's title",
      "Applied to all 5 lockstep packs -- sdd-micro is intentionally " +
      "excluded from the shared-block sync system and has no " +
      "BRD/SRD/etc. templates using this placeholder",
      "This Node CLI has no CLAUDE.md content of its own " +
      "(scaffolding-only by design) and is unaffected -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "Verified: check-cross-references.py clean across all 6 packs; " +
      "test-setup.sh (19/19) and test-setup-micro.sh (12/12) both pass",
    ],
  },
  {
    from: '2.8.27',
    to:   '2.8.28',
    description: "Per-level Jira issue type overrides (review/chg/cr) " +
      "now actually work; cr.py's Change Request review ticket now " +
      "gets a parent Epic link like every other issue type; " +
      "constitution.md's DRAFT now pushes to Confluence immediately at " +
      "/specify, not only after GATE-1 finalizes",
    notes: [
      "User request: project_keys already supports per-level overrides " +
      "for feature/story/task/review/chg/cr -- asked for the same on " +
      "issue_hierarchy (the Jira issue TYPE per level), and for the " +
      "hierarchy/parent-linking model to be explained and documented",
      "Investigating found issue_hierarchy per-level overrides for " +
      "review/chg/cr were completely non-functional: cli-python's " +
      "load_integrations() built JiraConfig with only feature/story/task " +
      "hardcoded, silently dropping any review/chg/cr entry the user " +
      "wrote in integrations.yml. Fixed with a new " +
      "JiraConfig.issue_type_for(level) method every issue-creation call " +
      "site now routes through, replacing all direct issue_hierarchy[...] " +
      "dict indexing",
      "Also fixed: cr.py's 'sdd cr submit' created the CR-NNN review " +
      "ticket as a fully standalone issue with no parent link at all -- " +
      "the only Jira issue type this CLI ever created that way. It now " +
      "self-bootstraps the Epic and links the CR review ticket under it, " +
      "same as review submit's own review tickets do",
      "Documented the full parent-child hierarchy and the cr-vs-chg " +
      "distinction (cr = the Change Request's own approval ticket, one " +
      "per CR-NNN; chg = individual dev tasks implementing one line of " +
      "an approved CR's plan, one per CHG-NNN row, parented to whichever " +
      "Story satisfies its FR-NNN reference) directly in " +
      "integrations.yml.example's issue_hierarchy comment block and in " +
      "cli-python/README.md",
      "Separately: constitution.md's DRAFT now pushes to Confluence " +
      "immediately when /specify first generates it (same as " +
      "context.md's own draft push in /create-context), not only when " +
      "GATE-1 finalization pushes it later. Applied to all 5 packs' " +
      "specify.prompt.md individually",
      "This Node CLI has no Jira/Confluence integration at all " +
      "(scaffolding-only by design) and is unaffected by any of this -- " +
      "this migration entry exists so both CLIs report the same " +
      "sdd_version chain",
      "Verified: cli-python pytest 880/880 (874 pre-existing + 6 new); " +
      "ruff check/format and mypy --ignore-missing-imports (matching " +
      "CI's exact invocation) both clean on the changed files; " +
      "check-cross-references.py clean across all 6 packs; " +
      "test-setup.sh (19/19) and test-setup-micro.sh (12/12) both pass",
    ],
  },
  {
    from: '2.8.28',
    to:   '2.8.29',
    description: "Fix bare `sdd confluence push` (no --doc) never " +
      "including the context.md page -- the same gap as v2.8.23's " +
      "constitution fix, found while auditing integrations.yml.example " +
      "at a user's request to confirm everything was documented",
    notes: [
      "User asked to double-check integrations.yml.example documented " +
      "everything discussed in the previous round. While re-reading it " +
      "end to end, found 'context' was missing entirely -- not in " +
      "page_map, not in the code's default page map -- the exact same " +
      "bug class as v2.8.23's constitution fix, just never caught for " +
      "context.md at the time",
      "Root cause: cli-python's confluence.py special-cases 'context' " +
      "to always resolve to '{feature} -- Context' regardless of " +
      "page_map -- so `sdd confluence draft --doc context` (what " +
      "/create-context actually calls) worked fine on its own. But a " +
      "bare `sdd confluence push` (no --doc) iterates page_map.keys(), " +
      "and 'context' was never in that set",
      "Fixed by adding 'context' to _DEFAULT_PAGE_MAP, the wizard's " +
      "minimal fallback template, and integrations.yml.example's " +
      "page_map",
      "This Node CLI has no Confluence integration at all " +
      "(scaffolding-only by design) and is unaffected -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 882/882 (880 pre-existing + 2 new); " +
      "ruff check/format and mypy --ignore-missing-imports (matching " +
      "CI's exact invocation) both clean on the changed files; " +
      "check-cross-references.py clean across all 6 packs; " +
      "test-setup.sh (19/19) and test-setup-micro.sh (12/12) both pass",
    ],
  },
  {
    from: '2.8.29',
    to:   '2.8.30',
    description: "Add commented-out document_reviews example entries " +
      "for the living/service-level docs (data-model, security-design, " +
      "api-spec, component-library) to integrations.yml.example",
    notes: [
      "User request, following up on the previous round's " +
      "issue_hierarchy/page_map audit: these four docs had a page_map " +
      "entry (Confluence) but no document_reviews entry (Jira) anywhere " +
      "in the shipped example -- by design (specify-doc.prompt.md's " +
      "documented fallback), but a team that DOES want a formal Jira " +
      "gate on one had no template to copy from",
      "Each gets its OWN single-entry phase (e.g. phase: data-model, " +
      "sequence: 1) rather than sharing one with each other or with " +
      "design -- they're independent (any order, no dependency between " +
      "them), and the predecessor check gates strictly on matching " +
      "phase + sequence-1, so sharing a phase would wrongly block one " +
      "doc on another's approval",
      "All four entries stay fully commented out by default -- active " +
      "document_reviews / page_map keys are completely unaffected",
      "This Node CLI has no Jira/Confluence integration at all " +
      "(scaffolding-only by design) and is unaffected -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 882/882 (no change -- inert " +
      "commented content); check-cross-references.py clean across all " +
      "6 packs; test-setup.sh (19/19) and test-setup-micro.sh (12/12) " +
      "both pass",
    ],
  },
  {
    from: '2.8.30',
    to:   '2.8.31',
    description: "Fix re-pushing a local-svg diagram to Confluence a " +
      "second time -- always failed with 'Cannot add a new attachment " +
      "with same file name as an existing attachment'",
    notes: [
      "Reported by a user during testing: pushed a page with a " +
      "local-svg diagram once successfully, then re-pushed it (no " +
      "content change) -- the SVG attachment upload failed every time " +
      "with a 400 BadRequestException naming the exact collision. The " +
      "page body itself still updated fine, so the failure was easy to " +
      "miss unless watching stderr",
      "Root cause: cli-python's confluence_client.py upload_attachment() " +
      "always POSTed to Confluence's CREATE-a-new-attachment endpoint. " +
      "Its own docstring claimed Confluence auto-versions an existing " +
      "same-named attachment -- that claim was wrong. Confluence " +
      "Cloud's actual behavior: creating a second attachment with an " +
      "already-existing filename is rejected outright. Updating an " +
      "existing attachment's content requires a DIFFERENT endpoint " +
      "(.../child/attachment/{attachmentId}/data), needing the " +
      "attachment's ID first",
      "Fixed with a new get_attachment_by_filename() lookup -- " +
      "upload_attachment() now checks for an existing same-named " +
      "attachment first and routes to the update-data endpoint when " +
      "one exists, the create endpoint otherwise. A page's first push " +
      "(no existing attachment) behaves identically to before; only " +
      "the second-and-later push of the same diagram was affected, " +
      "exactly what was broken",
      "This Node CLI has no Confluence integration at all " +
      "(scaffolding-only by design) and is unaffected -- this migration " +
      "entry exists so both CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 889/889 (882 pre-existing + 7 new); " +
      "ruff check/format and mypy --ignore-missing-imports (matching " +
      "CI's exact invocation) both clean on the changed files",
    ],
  },
  {
    from: '2.8.31',
    to:   '2.8.32',
    description: "Add a project-level 'Living Documents' dashboard " +
      "section for Data Model and Security Design -- previously only " +
      "shown as a bare progress dot duplicated inside every feature's " +
      "own pipeline card, with no Approve button, no Confluence/Jira " +
      "links, and easy to miss entirely",
    notes: [
      "Reported by a user: couldn't find Data Model on the dashboard " +
      "at all, and after generating it its status stuck showing " +
      "'waiting for review' -- the second part turned out to be " +
      "correct/by-design, but the first part was real: these living/ " +
      "service-level docs (one shared file for the whole project, not " +
      "per-feature) were only ever inserted as ordinary steps inside " +
      "each feature's own pipeline -- duplicated once per feature card " +
      "on a multi-feature project, with none of the Approve button/" +
      "links/Details panel every per-feature document already gets",
      "New _service_level_docs() in cli-python's status.py builds full " +
      "doc entries for Data Model and Security Design, exposed as a " +
      "new top-level living_documents/living_local_links pair, " +
      "separate from any one feature. Removed the duplicated per-" +
      "feature pipeline steps. New renderLivingDocuments() in the " +
      "dashboard's app.js renders a card between the Project/" +
      "Constitution cards and the Features Overview table, reusing the " +
      "exact same row-rendering every per-feature document already " +
      "uses -- zero new backend endpoints needed",
      "api-spec and component-library (also living-service docs) are " +
      "deliberately not included -- api-spec has no standalone /specify-" +
      "doc command to link to, and neither has dashboard tracking to " +
      "build on yet; a real gap, but a separate follow-up",
      "This Node CLI has no dashboard at all (scaffolding-only by " +
      "design) and is unaffected -- this migration entry exists so " +
      "both CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 892/892 (889 pre-existing, net +3 " +
      "after rewriting 5 tests that asserted the old per-feature steps " +
      "and adding 3 new end-to-end tests including the exact reported " +
      "multi-feature duplication scenario); ruff check/format and mypy " +
      "--ignore-missing-imports (matching CI's exact invocation) both " +
      "clean; node --check on app.js clean",
    ],
  },
  {
    from: '2.8.32',
    to:   '2.8.33',
    description: "Fix a real document-corrupting bug in `sdd review " +
      "approve --local` (a blind 'Status: Draft' find-replace could " +
      "mangle enum content anywhere in a document's body), a severe " +
      "Confluence-pull data-loss bug (mismatched ac: tag closing could " +
      "delete whole sections), an HTML-comment mangling bug on both " +
      "push and pull, and the security/security-design doc-key naming " +
      "inconsistency -- all found by a user during a real living-" +
      "document review cycle",
    notes: [
      "Bug 1 (data corruption) -- cli-python's review.py flipped a " +
      "document's Status: header via an unanchored regex-replace across " +
      "the ENTIRE document, not scoped to the real header. Reported by " +
      "a user: data-model.md's own template (unlike every other spec " +
      "template) had NO Status: header field at all, so the regex's " +
      "first (and only) match was a §3 enum field written as " +
      "'RuleVersionStatus: DRAFT, SUBMITTED, PUBLISHED, RETIRED' -- " +
      "silently mangled into 'RuleVersionStatus: Approved, SUBMITTED, " +
      "PUBLISHED, RETIRED'. Fixed by scoping the flip to the document's " +
      "front matter (before the first '## ' heading)",
      "Root-caused further: data-model-template.md and security-design-" +
      "template.md never had a Status: header field to begin with -- " +
      "added 'Status: Draft' to both, across all 5 packs, restoring " +
      "correct Draft/Approved status tracking for these living docs",
      "Bug 2 (severe data loss) -- cf_to_md.py's 'strip remaining ac:* " +
      "elements' cleanup paired an opening ac: tag with the NEXT ac: " +
      "closing tag of ANY name, not necessarily its own. Reported by a " +
      "user: a page with a local-svg diagram, followed later by " +
      "another unhandled/nested ac: element, had everything between " +
      "them silently deleted -- 6 tables and an entire numbered section " +
      "in their case. Fixed with a backreference so a match can only " +
      "ever span exactly one element's own content",
      "Bug 3 (data loss + visible garbage) -- HTML comments (e.g. the " +
      "security-sign-off marker specify-doc.prompt.md requires) fell " +
      "through to the paragraph branch on push, getting HTML-escaped " +
      "into VISIBLE garbage text on the actual Confluence page, then " +
      "deleted outright by the generic tag-stripper on pull. Fixed on " +
      "both sides: push passes a comment-only line through literally; " +
      "pull stashes comments into placeholders before any other " +
      "processing and restores them verbatim at the end",
      "Bug 4 (naming inconsistency) -- specify-doc.prompt.md's own " +
      "prose calls it `/specify-doc security`, but every sdd CLI " +
      "command actually requires the doc key `security-design`. Added " +
      "an explicit resolution rule right after the Input section",
      "This Node CLI has no Jira/Confluence integration and no review-" +
      "approval flow of its own (scaffolding-only by design) and is " +
      "unaffected by any of this -- this migration entry exists so " +
      "both CLIs report the same sdd_version chain",
      "Verified: cli-python pytest 904/904 (892 pre-existing + 12 new); " +
      "ruff check/format and mypy --ignore-missing-imports (matching " +
      "CI's exact invocation) both clean on the changed files; " +
      "check-cross-references.py clean across all 6 packs; " +
      "test-setup.sh (19/19) and test-setup-micro.sh (12/12) both pass",
    ],
  },
  {
    from: '2.8.33',
    to:   '2.8.34',
    description: 'Fix two live sequencing bugs a user hit back-to-back ' +
      'during real testing: a /specify-doc chat message that skipped ' +
      'over the mandatory /checklist gate at mvp+/full scope, and a ' +
      'brd.md field that generated an unresolvable [NEEDS ' +
      'CLARIFICATION] marker by design',
    notes: [
      "Bug 1 -- specify-doc.prompt.md's 'all documents complete' " +
      'message named /validate as the next step unconditionally, even ' +
      'though /checklist sits between the extended document set and ' +
      '/validate in the command order and is mandatory at mvp/full ' +
      'scope (optional only at pilot). Reported by a user: the ' +
      "dashboard correctly showed 'Spec Quality Checklist' as the next " +
      "step, but the chat message after the last document approval " +
      "said 'Run /validate ... the gate before /analyze,' skipping " +
      "/checklist entirely. Fixed by making the 'none remain' branch " +
      'check manifest.project.scope: mvp/full now names /checklist ' +
      '(mandatory) as the next command; pilot names it as an optional ' +
      'gate before /validate',
      "Bug 2 -- brd.md §9's 'Build effort (T-shirt)' row was " +
      "generated as 'Derived from analyze.md (filled after /analyze)' " +
      'under a blanket instruction that marks any unfilled Investment ' +
      'Summary item [NEEDS CLARIFICATION]. But analyze.md doesn\'t ' +
      'exist until /analyze runs, which is AFTER /validate in the ' +
      'pipeline order (SPECIFY -> GATE-1 -> VALIDATE -> ANALYZE) -- ' +
      "and checklist.prompt.md's CRITICAL rule #1 blocks /validate on " +
      'any unresolved [NEEDS CLARIFICATION] marker with no per-field ' +
      "carve-out. A user's own /checklist run surfaced this exact " +
      'conflict verbatim. Three-part fix: (1) brd-template.md §9 ' +
      "now writes plain deferred text 'Pending -- estimated after " +
      "/analyze' for this field instead of an implicit-marker-prone " +
      'placeholder -- never a [NEEDS CLARIFICATION] marker; (2) ' +
      "analyze.prompt.md gained a new 'Update BRD Build Effort' step " +
      "that actually implements the template's own long-standing but " +
      'never-implemented promise -- derives a T-shirt size from the ' +
      'COMPLEXITY ratings just produced and writes it back into brd.md ' +
      '§9; (3) checklist.prompt.md\'s CRITICAL rule #1 gained an ' +
      'explicit known-exception carve-out for this one field, as a ' +
      'defensive safety net for any brd.md generated before this fix',
      'specify-doc.prompt.md and brd-template.md and ' +
      'checklist.prompt.md are _shared/full/ sources -- edited once, ' +
      'synced to all 5 packs via sync-blocks.sh. analyze.prompt.md is ' +
      'authored per-pack (not in _shared/) -- the same \'Update BRD ' +
      "Build Effort' step was added individually to all 5 packs' " +
      'analyze.prompt.md, verified identical in content across all 5',
      'This Node CLI has no Jira/Confluence integration and no review-' +
      'approval flow of its own (scaffolding-only by design) and is ' +
      'unaffected by any of this -- this migration entry exists so ' +
      'both CLIs report the same sdd_version chain',
      'Verified: cli-python pytest 904/904 (no Python code touched, ' +
      'only markdown/prompt files); check-cross-references.py clean ' +
      'across all 6 packs; test-setup.sh (19/19) and test-setup-' +
      'micro.sh (12/12) both pass; assert-output.sh clean against ' +
      'examples/todo-api (33/33)',
    ],
  },
  {
    from: '2.8.34',
    to:   '2.8.35',
    description: 'Full review-gate audit across every living and ' +
      'feature document: closed two behavioural gaps (validate/' +
      'analyze/clarify missing the Confluence-only submission ' +
      'fallback; api-spec.md\'s first version never getting a review ' +
      'ticket/page) and fixed a sync-tooling bug that was silently ' +
      'serving 10 pack prompts a stale copy of the approval logic',
    notes: [
      'Requested audit: \'perform an audit to see all living document ' +
      'and feature document create the review ticket and pushed to ' +
      'confluence page and review is pulled from jira and confluence ' +
      'to make sure all are having the same process if jira or ' +
      'confluence is active, else it can be done in chat\'',
      'Finding A -- validate.prompt.md, analyze.prompt.md, ' +
      'clarify.prompt.md (hand-authored, not shared, identical across ' +
      'all 5 packs) only ever called `sdd review submit` and fell ' +
      'straight to pure chat mode on failure. review.py\'s ' +
      'review_submit requires BOTH jira: and confluence: sections and ' +
      'hard-fails otherwise (confirmed by reading the CLI) -- so in a ' +
      'confluence-only project (no jira:) these three documents never ' +
      'reached Confluence, unlike every other reviewed document, which ' +
      'falls through to `sdd confluence draft` first. Fixed by ' +
      'swapping their Step B/C onto the same submit-for-review-step/' +
      'review-decision-step shared blocks the other 12 commands ' +
      'already use, adding the markers to all 5 packs\' copies of the ' +
      '3 files and running sync-blocks.sh -- each file\'s own document-' +
      'specific approval-scope caveat (e.g. validate.md\'s per-item ' +
      'checkboxes not being itemized by a blanket approval) was ' +
      'preserved as trailing prose after the shared block, not lost in ' +
      'the swap',
      'Finding B -- api-spec.md (the third living document, generated ' +
      'inside plan-design.prompt.md when a service-providing feature ' +
      'is planned) had no submission step on first creation, unlike ' +
      'its sibling living docs (data-model, security-design), which ' +
      'get one via specify-doc.prompt.md\'s shared block. api-spec.md ' +
      'only ever reached Confluence/Jira later, when a subsequent ' +
      'feature called `sdd review apply --doc api-spec` on an update ' +
      '-- meaning a service\'s first feature could ship an API ' +
      'contract that was never actually routed through a review ' +
      'ticket. Fixed by adding the same shared submission block ' +
      '(doc_key = api-spec) right after first-time generation, ' +
      'independent of design.md\'s own later approval step',
      'Finding C (found while fixing B, not part of the original two) ' +
      '-- sync-blocks.sh\'s two loops ran in the wrong order: the ' +
      'blocks loop (which refreshes shared:{id} marker regions in ' +
      'pack files) ran BEFORE the full-file loop (which copies ' +
      '_shared/full/{path} whole-file into every pack). Ten ' +
      '.github/prompts/ files in full/ (specify-brd, specify-uc, ' +
      'specify-srd, specify-doc, plan-arch, plan-hld, plan-adr, plan-' +
      'design, plan-lld, task) themselves embed submit-for-review-' +
      'step/review-decision-step markers -- full/ is never itself ' +
      'touched by the blocks loop (it only globs ../sdd-*/), so those ' +
      '10 files\' own inline copies had silently drifted stale ' +
      '(missing review-decision-step\'s \'resolve the approver\'s ' +
      'name from roles.yml, fill the Approver column\' step, added to ' +
      'blocks/review-decision-step.md at some point after these 10 ' +
      'files were last hand-synced). Every sync-blocks.sh run: blocks ' +
      'loop correctly refreshed the 10 files in all 5 packs, then the ' +
      'full-file loop immediately overwrote them back to the stale ' +
      'full/ copy, since cmp always showed a diff. Verified directly: ' +
      'validate.prompt.md (never full-file-synced) had the fresh ' +
      'content, specify-brd.prompt.md (full-file-synced) did not, in ' +
      'the same pack, same run. Fixed two ways: (1) swapped the loop ' +
      'order in sync-blocks.sh so the blocks pass always runs last and ' +
      'has the final word on every marker region regardless of which ' +
      'loop last touched the file; (2) refreshed the 10 full/ files\' ' +
      'own embedded copies to match blocks/*.md exactly, so a ' +
      'maintainer reading full/ directly isn\'t misled either. ' +
      'Confirmed idempotent: three consecutive sync-blocks.sh runs ' +
      'after the fix produce zero further file changes. Added a ' +
      'README.md rule documenting the gotcha so it isn\'t reintroduced',
      'This Node CLI has no Jira/Confluence integration and no review-' +
      'approval flow of its own (scaffolding-only by design) and is ' +
      'unaffected by any of this -- this migration entry exists so ' +
      'both CLIs report the same sdd_version chain',
      'Verified: cli-python pytest 904/904; check-cross-references.py ' +
      'clean across all 6 packs; test-setup.sh (19/19) and test-' +
      'setup-micro.sh (12/12) both pass; assert-output.sh clean ' +
      'against examples/todo-api (33/33); three consecutive sync-' +
      'blocks.sh runs confirmed idempotent (zero diffs after the ' +
      'first)',
    ],
  },
  {
    from: '2.8.35',
    to:   '2.8.36',
    description: 'Fix a real bug reported from live use: brd.md\'s ' +
      'Stakeholders table never actually got its ACT-NNN identifiers ' +
      'filled in by /specify-uc -- the instruction existed but was too ' +
      'easy for an agent to skip',
    notes: [
      'User report: \'after the BRD is created, the ACT-NNN was never ' +
      'assigned after /specify-uc\'',
      'Root cause: specify-uc.prompt.md\'s \'Back-fill BRD ' +
      'Stakeholders\' instruction existed and was structurally correct ' +
      '(right after Save/Write, before drafting Jira stories), but had ' +
      'almost no structural weight -- a single bolded inline paragraph ' +
      'with no heading, sandwiched between two \'Save to:\'/\'Write:\' ' +
      'bullets and the \'Draft Jira Stories\' paragraph, and never ' +
      'mentioned again in the command\'s own completion message (\'Use ' +
      'Cases generated. Review and approve...\') -- nothing in the ' +
      'output even hinted the back-fill had (or hadn\'t) happened. ' +
      'This is the same failure mode as v2.8.34\'s brd.md Build Effort ' +
      'field, fixed the same way there by giving the step its own ' +
      'heading',
      'Fix: promoted the instruction to its own \'### Back-fill BRD ' +
      'Stakeholders (mandatory -- do not skip)\' heading with explicit ' +
      'numbered steps (open brd.md, match each remaining placeholder ' +
      'row to its real actor by role, resolve every cell to either a ' +
      'real ACT-NNN or _(N/A)_, save + regenerate brd.summary.md), and ' +
      'added a line to the completion message confirming the back-fill ' +
      'happened by name, so a skipped back-fill is now visible in the ' +
      'command\'s own output rather than silent',
      'specify-uc.prompt.md is a _shared/full/ source -- edited once, ' +
      'synced to all 5 packs via sync-blocks.sh',
      'This Node CLI has no Jira/Confluence integration and no review-' +
      'approval flow of its own (scaffolding-only by design) and is ' +
      'unaffected by any of this -- this migration entry exists so ' +
      'both CLIs report the same sdd_version chain',
      'Verified: cli-python pytest 904/904; check-cross-references.py ' +
      'clean across all 6 packs; test-setup.sh (19/19) and test-' +
      'setup-micro.sh (12/12) both pass; sync-blocks.sh confirmed ' +
      'idempotent',
    ],
  },
  {
    from: '2.8.36',
    to:   '2.8.37',
    description: 'Answered a user\'s process question about review ' +
      'revisions by fixing the two real gaps it exposed: \'sdd review ' +
      'apply\' never reverted an Approved document\'s own Status ' +
      'header, and never had any way to move a Done/Closed Jira ticket ' +
      'back into an active workflow status',
    notes: [
      'User question: after /validate, /analyze, or /clarify updates ' +
      'documents post-approval, does the status change to review, does ' +
      'that create a new Jira ticket, and does a Closed ticket get ' +
      'reopened? Answer at the time (traced through the actual code, ' +
      'not assumed): no new ticket is ever created (find_by_label ' +
      'always re-uses the same ticket); JiraClient had literally no ' +
      'transition capability at all -- no method to change a ticket\'s ' +
      'workflow status, so a Done/Closed ticket stayed there forever, ' +
      'only ever getting a \'please re-review\' comment; and the ' +
      'document\'s own Status: header was never reverted from Approved ' +
      'either, so both signals of \'this changed, please look again\' ' +
      'were weak. User asked to fix both',
      'Fix 1 (document status) -- added _mark_md_needs_revision() to ' +
      'review.py, the direct counterpart to the existing ' +
      '_mark_md_approved(): flips \'Status: Approved\' back to ' +
      '\'Status: Draft\' (or \'Proposed\' for adr.md, matching its own ' +
      'lifecycle vocabulary) in the document\'s front matter only (same ' +
      'corruption-safety scoping as _mark_md_approved). No-op for a ' +
      'document that was never Approved in the first place. Wired into ' +
      '\'sdd review apply\' unconditionally, before any Jira/Confluence ' +
      'branching, so it fires the same way in every integration mode ' +
      'including pure chat/local',
      'Fix 2 (Jira ticket reopening) -- added get_transitions() and ' +
      'transition_issue() to JiraClient (GET/POST ' +
      '/issue/{key}/transitions, the real Jira REST API for workflow ' +
      'moves -- previously entirely unimplemented). transition_issue() ' +
      'looks for a transition whose target matches the requested status ' +
      'name and executes it, returning False (never raising) if no ' +
      'match exists. Wired into \'sdd review apply\': after posting the ' +
      'existing re-review comment, attempts a transition to the new ' +
      '\'reopen_status\' integrations.yml setting (unset by default -- ' +
      'deliberately opt-in, workflow status names vary too much across ' +
      'orgs to guess safely; documented in integrations.yml.example)',
      'Documented the full actual behavior in the review-gates shared ' +
      'block (CLAUDE.md, all 5 packs): what \'sdd review apply\' does ' +
      'to an Approved document, step by step',
      'This Node CLI has no Jira/Confluence integration and no review-' +
      'approval flow of its own (scaffolding-only by design) and is ' +
      'unaffected by any of this -- this migration entry exists so ' +
      'both CLIs report the same sdd_version chain',
      'Verified: cli-python pytest 922/922 (904 pre-existing + 18 new); ' +
      'ruff check/format clean on all changed files; check-cross-' +
      'references.py clean across all 6 packs; test-setup.sh (19/19) ' +
      'and test-setup-micro.sh (12/12) both pass; sync-blocks.sh ' +
      'confirmed idempotent',
    ],
  },
  {
    from: '2.8.37',
    to:   '2.8.38',
    description: 'Found and fixed a real, live bug while implementing a ' +
      'user-requested design change: the Approvals table\'s ' +
      '\'Pending\' -> \'Approved\' regex has never matched a single ' +
      'real document, on any template, ever -- including via the ' +
      'dashboard\'s Approve button. Also added role-scoped Approvals-' +
      'table flipping so a single Jira reviewer\'s sign-off no longer ' +
      'gets misread as every RACI role\'s',
    notes: [
      'User showed a live design.md approval transcript: an agent ' +
      'blanket-approved all three Approvals-table roles (Architect/' +
      'Tech Lead/Stakeholder) off one Jira ticket assigned only to ' +
      'Architect, then self-corrected. Asked to make that discipline ' +
      'the documented, consistent behavior -- \'check for all docs\'',
      'While designing that fix, found the CLI\'s own Approvals-table ' +
      'flip (_mark_approvals_table) has been silently broken since it ' +
      'was written: its regex expects a 3-column \'Role | Pending | ' +
      'Date\' row shape. Checked every one of the 20 templates with an ' +
      '## Approvals section -- all 20 are actually 4 columns, \'Role | ' +
      'Approver | Status | Date\'. Tested the regex against real rows ' +
      'from real templates: zero matches, on any of them. The existing ' +
      'unit test\'s own fixture invented the same wrong 3-column shape, ' +
      'so nothing ever caught it',
      'Real impact: dashboard.py\'s Approve button calls ' +
      '_mark_md_approved() directly with no prior text edit -- ' +
      'confirmed by reading _do_approve. Every dashboard approval, ' +
      'ever, has flipped the Status header correctly but left the ' +
      'Approvals table stuck on \'Pending\' underneath it. The bug was ' +
      'invisible in the normal chat-driven flow only because the LLM ' +
      'agent edits the table text itself first, before this now-fixed ' +
      'CLI call runs as a no-op safety net with nothing left to do',
      'Also found: _mark_md_approved\'s caller in review_approve never ' +
      'passed --by\'s value through to the flip function at all, so ' +
      'even a working regex would have left the Approver column ' +
      'permanently blank. Same gap existed in dashboard.py\'s ' +
      '_do_approve',
      'Fixed all three together: rewrote _mark_approvals_table\'s ' +
      'regex for the real 4-column shape; added approver_name (fills ' +
      'the Approver column) and role_filter (scopes the flip to Role-' +
      'column text matches, falling back to blanket-flip if nothing ' +
      'matches) parameters, threaded through _mark_md_approved; wired ' +
      'approver_name into both review_approve (--by) and dashboard.py\'s ' +
      '_do_approve (by); added a new --role flag to \'sdd review ' +
      'approve\'',
      'Updated review-decision-step.md (shared block, used by all ~15 ' +
      'review-gated documents): step 1 now distinguishes a Jira-driven ' +
      'approval from a chat-driven one; step 4 flips only the ' +
      'Approvals-table row matching document_reviews.{doc}.reviewer_role ' +
      'when Jira drove it (other RACI rows left Pending, with a ' +
      'fallback to blanket-flip on a role/wording mismatch), unchanged ' +
      'blanket-flip when chat drove it; step 6 passes the new --role ' +
      'flag through so the CLI\'s own safety-net flip matches whichever ' +
      'scope the manual edit already used',
      'review-decision-step.md is a _shared/blocks/ source -- edited ' +
      'once, propagated to all 15 documents across all 5 packs (75 file ' +
      'locations) plus the 10 _shared/full/ sources\' own embedded ' +
      'copies (refreshed for hygiene per the rule added in v2.8.35\'s ' +
      'README.md fix)',
      'This Node CLI has no Jira/Confluence integration and no review-' +
      'approval flow of its own (scaffolding-only by design) and is ' +
      'unaffected by any of this -- this migration entry exists so ' +
      'both CLIs report the same sdd_version chain',
      'Verified: cli-python pytest 930/930 (922 pre-existing + 8 new); ' +
      'ruff check/format clean on all changed files; check-cross-' +
      'references.py clean across all 6 packs; test-setup.sh (19/19) ' +
      'and test-setup-micro.sh (12/12) both pass; sync-blocks.sh ' +
      'confirmed idempotent',
    ],
  },
  {
    from: '2.8.38',
    to:   '2.8.39',
    description: 'Fix a real 409 Conflict a user hit during /plan-lld ' +
      'testing: ConfluenceClient.upsert_page() had no retry-on-version-' +
      'conflict, so a page update racing Confluence\'s own eventual-' +
      'consistency lag failed outright -- and a manual retry reproduced ' +
      'the identical 409, since it resent the same stale version number',
    notes: [
      'User report: \'Could not stamp Jira status onto Confluence: 409 ' +
      'Conflict\' during /plan-lld\'s review submission (a 19-diagram ' +
      'lld.md), then the identical 409 again on a follow-up sdd review ' +
      'apply push, and again on a manual retry -- correctly self-' +
      'diagnosed as \'the page\'s stored version number and what the ' +
      'CLI thinks it is have diverged... not a transient blip\'',
      'Root cause: upsert_page() does one GET (read the page\'s current ' +
      'version) then one PUT (write version+1) with no conflict ' +
      'handling. review_submit calls it twice in one run -- once for ' +
      'the initial push, again right after (once the Jira ticket ' +
      'exists) to stamp its status banner onto the page -- with a burst ' +
      'of diagram-attachment uploads on the same page in between. ' +
      'Confluence Cloud\'s read path can lag slightly behind its own ' +
      'just-completed write in that window, so the second push\'s GET ' +
      'can return a version that\'s already one behind the true current ' +
      'version by the time its PUT reaches the server -- a 409',
      'Confirmed this can\'t be fixed by the existing generic HTTP-' +
      'layer retry (atlassian_auth.py\'s _retrying_adapter, added ' +
      'earlier for 429/5xx): it deliberately excludes 409, because ' +
      'blindly resending the exact same PUT body with the exact same ' +
      'stale version number reproduces the exact same 409 -- exactly ' +
      'what happened when the user retried by hand',
      'Fix: upsert_page() now catches a 409 from update_page(), re-' +
      'fetches the page\'s current version via get_page_by_title, and ' +
      'retries the PUT with the corrected version number, up to 3 ' +
      'attempts total. Any other status code (or a 409 on the final ' +
      'attempt) still raises immediately, unchanged',
      'Fixes all 4 call sites that go through this shared method ' +
      '(review.py\'s two review_submit pushes, cr.py\'s CR page push, ' +
      'confluence.py\'s manual push/draft commands) with one change, ' +
      'not four',
      'This Node CLI has no Jira/Confluence integration and no review-' +
      'approval flow of its own (scaffolding-only by design) and is ' +
      'unaffected by any of this -- this migration entry exists so ' +
      'both CLIs report the same sdd_version chain',
      'Verified: cli-python pytest 934/934 (930 pre-existing + 4 new); ' +
      'ruff check/format clean; mypy --ignore-missing-imports clean on ' +
      'the changed file; check-cross-references.py clean across all 6 ' +
      'packs; test-setup.sh (19/19) passes',
    ],
  },
  {
    from: '2.8.39',
    to:   '2.8.40',
    description: 'Full audit of every prompt across all 5 packs for ' +
      'Jira/Confluence review-flow consistency, requested after the ' +
      'prior round of live-testing fixes -- found and fixed 4 findings: ' +
      'two standalone utility commands (/submit-review, /check-review) ' +
      'had their own hand-written, never-synced review logic that ' +
      'silently regressed behind the canonical shared blocks, plus two ' +
      'documentation-accuracy gaps in those canonical blocks themselves',
    notes: [
      'Audit method: enumerated all 36 prompts x 5 packs, confirmed the ' +
      '27 _shared/full/-sourced ones are byte-identical everywhere, ' +
      'diffed the 9 per-pack-authored ones (cosmetic-only differences, ' +
      'confirmed), then swept every prompt for jira:/confluence: ' +
      'references OUTSIDE the two canonical shared blocks (submit-for-' +
      'review-step, review-decision-step) to find hand-rolled logic ' +
      'that could have drifted -- the same bug class already fixed ' +
      'twice this session',
      'Finding 1 (High) -- submit-review.prompt.md was a third, ' +
      'independently hand-written \'submit for review\' implementation, ' +
      'never synced from the canonical block. It branched only on ' +
      'jira: presence with no confluence-only draft-push branch at all ' +
      '-- in a confluence-only project, running /submit-review directly ' +
      'skipped straight to chat mode, the document never reaching ' +
      'Confluence, even though every document-generation command\'s own ' +
      'inline flow correctly pushes a draft in that exact config. Fixed ' +
      'by rewriting it to delegate directly to submit-for-review-step + ' +
      'review-decision-step (the same blocks every other document ' +
      'uses), keeping only its own Persona/Input/Sequence-rule content',
      'Finding 2 (Medium) -- check-review.prompt.md\'s own \'No-Jira ' +
      'fallback\' explicitly said \'do NOT run the CLI command\' when ' +
      'jira: was absent, then did its own simplified local check (doc ' +
      'header + .local-approvals.yml only). But `sdd review check` ' +
      'already handles the no-jira case gracefully -- confirmed via ' +
      '_print_local_comments_if_any\'s own docstring: \'Pure-local-mode ' +
      'fallback for sdd review check when no jira: section exists to ' +
      'poll,\' which surfaces unacknowledged DASHBOARD comments even ' +
      'with zero Jira/Confluence configured. Fixed with a precisely-' +
      'targeted change: always call `sdd review check`, and only fall ' +
      'back to a hand-written local check when the sdd tool itself ' +
      'isn\'t installed at all',
      'Finding 3 (Low, doc-accuracy) -- review-decision-step.md\'s own ' +
      'Exit 1 (NEEDS REVISION) prose said dashboard comments surface ' +
      '\'when Jira is configured\' -- understating reality, since they ' +
      'surface in pure-local mode too via the same CLI call. Rewrote ' +
      'the exit-code branches to state this correctly',
      'Finding 4 (Low, doc-accuracy) -- submit-for-review-step.md\'s ' +
      'own three branch headings didn\'t literally enumerate a jira-' +
      'only (no confluence:) config -- the correct outcome (fall to ' +
      'chat) was only reachable via inference. Added an explicit fourth ' +
      'branch naming this case directly',
      'submit-for-review-step.md and review-decision-step.md are ' +
      '_shared/blocks/ sources; submit-review.prompt.md and check-' +
      'review.prompt.md are _shared/full/ sources -- all four edited ' +
      'once, propagated to all 5 packs, plus the 10 _shared/full/ files ' +
      'embedding these two blocks had their own copies refreshed for ' +
      'hygiene',
      'This Node CLI has no Jira/Confluence integration and no review-' +
      'approval flow of its own (scaffolding-only by design) and is ' +
      'unaffected by any of this -- this migration entry exists so ' +
      'both CLIs report the same sdd_version chain',
      'Verified: cli-python pytest 934/934 (no Python code touched, ' +
      'only markdown/prompt files); check-cross-references.py clean ' +
      'across all 6 packs; test-setup.sh (19/19) and test-setup-' +
      'micro.sh (12/12) both pass; assert-output.sh clean against ' +
      'examples/todo-api (33/33); sync-blocks.sh confirmed idempotent',
    ],
  },
  {
    from: '2.8.40',
    to:   '2.9.16',
    description: "New Feature Drift Check safety rule, closing a real multi-session collision found during live testing on a project with two features",
    notes: [
      'manifest.project.feature is a single value in one shared file, ' +
      'not per-chat-session state -- every command\'s own \'Before ' +
      'Starting\' step re-reads manifest.yml fresh at the start of that ' +
      'command and substitutes {manifest.project.feature} directly into ' +
      'save/read paths. A user reported running two chat sessions ' +
      'against the same project folder, one per feature, and asked how ' +
      'manifest.yml\'s single project.feature field could possibly work ' +
      'for both at once -- it can\'t: whichever chat last changed it ' +
      '\'wins\', and the other chat\'s next command silently follows the ' +
      'new value instead of the feature it had actually been working ' +
      'on. No error, no warning, just a silently wrong target folder',
      'Added a new standing instruction (packs/_shared/blocks/feature-' +
      'drift-check.md) to all 5 packs\' CLAUDE.md, right after the ' +
      '\'Startup (every session)\' section: once a conversation has ' +
      'established which feature it\'s working on, compare that against ' +
      'project.feature every time a command re-reads manifest.yml; if ' +
      'they now disagree, STOP before reading/writing any document and ' +
      'ask the user to confirm which feature to use, instead of ' +
      'silently following the changed value. No effect on a fresh ' +
      'conversation\'s first command -- nothing yet to contradict',
      'Also added a \'Working on Multiple Features (or Multiple Chat ' +
      'Sessions)\' section to all 5 packs\' HOW-TO-USE.md (before \'File ' +
      'Ownership\'): explains the existing multi-feature-per-project ' +
      'model (each feature already gets its own .specify/features/' +
      '{feature}/ folder; sdd dashboard already shows every feature ' +
      'regardless of which is \'current\' -- this was already true, ' +
      'just undocumented), documents the new drift check, and ' +
      'recommends `git worktree add` (separate manifest.yml per ' +
      'worktree) as the clean way to actually parallelize two chats on ' +
      'two features rather than sharing one manifest.yml',
      'sdd-micro intentionally excluded -- its own CLAUDE.md already ' +
      'documents it as single-purpose by design with no multi-feature ' +
      'split, so this concern doesn\'t apply there',
      'Pure prompt/doc content shipped via the shared-block sync ' +
      'system (packs/_shared/blocks/, packs/_shared/sync-blocks.sh) -- ' +
      'no manifest schema changes, no CLI code changes',
      'Verified: check-cross-references.py clean across all 6 packs; ' +
      'test-setup.sh (19/19) and test-setup-micro.sh (12/12) both ' +
      'pass; sync-blocks.sh run twice consecutively with only the 5 ' +
      'CLAUDE.md + 5 HOW-TO-USE.md + 1 new block file changed ' +
      '(idempotent); cli-python pytest suite green after this ' +
      'migration entry was added',
    ],
  },
  {
    from: '2.9.16',
    to:   '2.9.17',
    description: "New `sdd project-type migrate` command -- guided migration of an sdd-universal project's project_type (e.g. backend-service -> fullstack) after initial setup",
    notes: [
      'Prompted directly by live-testing: a user\'s real project (a ' +
      'validation-service backend, sdd-universal, project_type: backend-' +
      'service) needed a second feature of a genuinely different kind ' +
      'added -- an admin UI to manage its rules. After walking through ' +
      'why that needs project_type: fullstack rather than a per-feature ' +
      'type field (constitution.md is one document for the whole ' +
      'project, not per-feature), the user asked for a real, guided ' +
      'migration path instead of the previous answer of \'hand-edit ' +
      'project_type + remember to separately run /change\' with no ' +
      'guardrails',
      'New sdd/utils/project_type.py: EXTENDED_DOCS_BY_TYPE (which of ' +
      'component-spec/ux-flow/screen-spec each project_type uses -- ' +
      'promoted out of sdd/utils/status.py, which now imports it ' +
      'instead of keeping its own private copy, so the two can never ' +
      'drift), applicable_extended_docs(), and classify_migration() -- ' +
      'compares two project_types\' extended-doc applicability and ' +
      'flags a migration \'lossy\' if it would drop a doc type already ' +
      'in use',
      'New sdd/commands/project_type.py: `sdd project-type show` and ' +
      '`sdd project-type migrate --to <type>` -- dry-run by default ' +
      '(prints the classify_migration() report, writes nothing); ' +
      '`--apply` writes manifest.yml\'s project_type; `--apply` on a ' +
      'lossy migration refuses with exit 1 unless `--force` is also ' +
      'passed. Deliberately never touches constitution.md -- Tech ' +
      'Stack row compatibility can\'t be determined mechanically, so ' +
      'extending the constitution for the new type is always left to ' +
      '/change (change type Technical), which the command\'s own ' +
      'guidance text points to',
      'Added \'Migrating project_type\' to packs/sdd-universal/CLAUDE.md ' +
      '(right after \'Upgrading Scope\') with the full 4-step guided ' +
      'procedure, and a matching short section to HOW-TO-USE.md -- ' +
      'sdd-universal-only, since the other 4 packs each have one fixed ' +
      'tech stack and no project_type field to migrate at all; nothing ' +
      'in their CLAUDE.md/HOW-TO-USE.md changed. Also added a `sdd ' +
      'project-type` entry to cli-python/README.md\'s CLI command ' +
      'reference',
      'This Node CLI has no `sdd project-type` equivalent and no ' +
      'project_type concept of its own (scaffolding-only by design) ' +
      'and is unaffected by any of this -- this migration entry exists ' +
      'so both CLIs report the same sdd_version chain',
      'Verified: cli-python pytest 968/968 (945 pre-existing + 23 new); ' +
      'ruff check/format clean; mypy --ignore-missing-imports sdd/ ' +
      'error count unchanged before/after (same 15 pre-existing errors, ' +
      'confirmed via diff against a stashed baseline); manually smoke-' +
      'tested the CLI end-to-end (dry-run vs --apply, lossy migration ' +
      'refusal without --force, invalid type rejection); check-cross-' +
      'references.py clean across all 6 packs; sync-blocks.sh confirmed ' +
      'only sdd-universal\'s own CLAUDE.md/HOW-TO-USE.md changed; ' +
      'test-setup.sh 19/19 passed',
    ],
  },
  {
    from: '2.9.17',
    to:   '2.9.18',
    description: "New manifest.yml field project.feature_display_name -- fixes a real cross-feature naming collision in {Feature Name} (document headers, Confluence page titles, Jira Epic summaries)",
    notes: [
      'Direct follow-up from the project-type migration work: ' +
      '{Feature Name} previously resolved only from project.name, one ' +
      'project-wide field. On a project with more than one feature -- ' +
      'exactly the scenario the prior two rounds this session were ' +
      'built for -- every feature\'s documents would carry the SAME ' +
      '{Feature Name}, and Confluence page titles/Jira Epic summaries ' +
      'would collide (Confluence page lookup is by title)',
      'packs/_shared/blocks/feature-name-convention.md: new resolution ' +
      'order -- project.feature_display_name (if present/non-empty) -> ' +
      'project.name (single-feature fallback) -> project.feature (slug, ' +
      'last resort). Synced into all 5 packs\' CLAUDE.md',
      'packs/_shared/full/.github/prompts/specify-brd.prompt.md\'s Jira ' +
      'Epic Summary line updated to match. Caught a real staleness bug ' +
      'applying this: hand-editing the 5 pack copies directly first, ' +
      'then running sync-blocks.sh, silently reverted the edit back to ' +
      'the old wording -- sync-blocks.sh regenerates full-file copies ' +
      'from this canonical _shared/full/ source, exactly the ' +
      'documented gotcha in packs/_shared/README.md. Fixed by editing ' +
      'the canonical source instead and re-syncing',
      'Added project.feature_display_name: "" (optional, defaults ' +
      'empty -> falls back to project.name, so every existing single-' +
      'feature project needs zero changes) to all 5 packs\' .specify/' +
      'manifest.yml template, right after the feature field',
      'packs/_shared/blocks/feature-drift-check.md: clarified that an ' +
      'intentional project.feature switch should also update ' +
      'project.context_file and (on a multi-feature project) ' +
      'project.feature_display_name together, not just project.feature ' +
      'alone',
      'All 5 packs\' HOW-TO-USE.md \'Working on Multiple Features\' ' +
      'section: corrected the single-chat-single-feature guidance to ' +
      'mention feature_display_name explicitly, superseding a weaker ' +
      'version from the prior round that only suggested updating ' +
      'project.name \'if you want the docs to header correctly\' -- ' +
      'undersold the actual Confluence/Jira title-collision risk',
      'This Node CLI has no project_type/feature_display_name concept ' +
      'of its own (scaffolding-only by design) and is unaffected by ' +
      'any of this -- this migration entry exists so both CLIs report ' +
      'the same sdd_version chain',
      'Verified: cli-python pytest 968/968 (unaffected -- pure prompt/' +
      'template/manifest-template content, no Python code touched); ' +
      'check-cross-references.py clean across all 6 packs; sync-' +
      'blocks.sh run three times consecutively with zero drift after ' +
      'the specify-brd.prompt.md canonical-source fix; test-setup.sh ' +
      '19/19 and test-setup-micro.sh 12/12 passed; manually confirmed ' +
      'all 5 packs\' manifest.yml template parses as valid YAML with ' +
      'feature_display_name present and empty by default',
    ],
  },
  {
    from: '2.9.18',
    to:   '2.9.19',
    description: "Fix: multi-feature Confluence page overwrites and Jira ticket-identity collisions (real bugs, confirmed by direct testing, not hypothetical)",
    notes: [
      'User explicitly asked \'does this work all over the project ... ' +
      'jira, confluence ... can you test\' -- traced every project_name/' +
      'feature_name usage through the actual CLI code (not just prompts) ' +
      'and empirically ran _resolve_page_title against the real default ' +
      'config: confirmed two features pushing the same doc type (brd/' +
      'use-cases/srd/etc.) silently overwrite each other\'s Confluence ' +
      'page, since Confluence page lookup is by title and the default ' +
      'title had no {feature} in it anywhere',
      'sdd/commands/config.py\'s _integrations_template() (what `sdd ' +
      'config init` actually scaffolds) had NO {feature} placeholder for ' +
      'any per-feature doc key -- fixed to match the already-correct ' +
      'integrations.yml.example (\'feature-first\' convention, {feature} ' +
      'only, no {project} prefix -- that fix landed there in an earlier ' +
      '2.7.35 round but never made it into this scaffold)',
      'sdd/utils/integrations.py\'s _DEFAULT_PAGE_MAP (fallback for ' +
      'document_reviews entries with no explicit confluence_page) had ' +
      'the same gap, fixed. Same for confluence.py\'s and review.py\'s ' +
      'generic inline fallbacks (doc key not in ANY page_map) -- now ' +
      '{project} — {feature} — DOC',
      'review.py\'s Jira review Story summary and Open Questions summary ' +
      'omitted feature_name -- ticket lookup itself was already feature-' +
      'safe (label-scoped), but two features\' tickets showed identical ' +
      'summary text, indistinguishable in Jira\'s own UI. Both now ' +
      'include feature_name',
      'cr.py\'s CR idempotency_label was WORSE -- a real functional bug, ' +
      'not just display: no feature qualifier at all, and CHG-NNN ' +
      'numbering is per-feature (not globally unique), so two features\' ' +
      'own \'CHG-001\' resolved to the SAME Jira ticket via this label ' +
      'lookup -- one feature\'s CR review silently reusing/overwriting ' +
      'an unrelated feature\'s ticket fields. Fixed to include ' +
      'feature_name; cr_check (which had no --feature option or feature ' +
      'resolution at all) fixed to match, since it must use the ' +
      'identical label cr_submit created the ticket under',
      'New: confluence.py\'s feature_collision_warning() -- a safety net ' +
      'for EXISTING projects whose integrations.yml already has an ' +
      'explicit ({feature}-less) title predating this fix (an explicit ' +
      'entry, unlike a fallback template, is never silently rewritten). ' +
      'Wired into `sdd confluence push`/`draft` as a hard block with a ' +
      'new --force flag to override; wired into review.py\'s ' +
      'review_submit and _push_doc_page (7 call sites including the ' +
      'dashboard\'s HTTP approve endpoint) as a non-blocking warning ' +
      'only, since those contexts have no CLI flag surface of their own ' +
      'to gate on',
      'No manifest.yml schema changes -- this is entirely CLI code and a ' +
      'new integrations.yml scaffold template; an EXISTING project\'s ' +
      'integrations.yml is never rewritten by `sdd upgrade` (only ' +
      'manifest.yml is), so an already-scaffolded project should ' +
      'manually add {feature} to its own page_map entries, or rely on ' +
      'the new collision-warning safety net in the meantime',
      'This Node CLI has no Jira/Confluence integration of its own ' +
      '(scaffolding-only by design) and is unaffected by any of this -- ' +
      'this migration entry exists so both CLIs report the same ' +
      'sdd_version chain',
      'Verified: cli-python pytest 983/983 (968 pre-existing + 15 new ' +
      '-- new test_feature_collision_safety.py plus 1 new test in ' +
      'test_review_helpers.py and 1 stale-title assertion corrected); ' +
      'ruff check/format clean; mypy error count unchanged in kind ' +
      '(only the pre-existing TypedDict warning multiplying with the ' +
      'new MIGRATIONS entries, expected); manually confirmed the actual ' +
      'collision before/after the fix (COLLISION -> distinct titles for ' +
      'brd/use-cases/srd)',
    ],
  },
  {
    from: '2.9.19',
    to:   '2.9.20',
    description: "New `sdd feature list`/`sdd feature status` commands -- terminal views of feature status that work without Jira configured",
    notes: [
      'Follow-up on two direct requests: \'let us have feature list\' ' +
      '(after recommending against a manifest.yml project.features list ' +
      '-- the filesystem is already the source of truth, and a manifest ' +
      'list would be a second, driftable copy of it -- a lightweight ' +
      'generated CLI command was proposed instead and accepted), and ' +
      '\'is there a sdd to check the status of a feature ... what is ' +
      'approved and what is pending and who ... what we show in ' +
      'dashboard\' -- there wasn\'t one that works without Jira',
      'sdd review status already existed but requires jira: configured ' +
      'and only shows Jira-tracked document reviews. The dashboard\'s ' +
      'own data (build_project_status/build_feature_status in ' +
      'status.py) already works in every review mode -- chat, local, ' +
      'jira -- by reading each document\'s Status: header and Approvals ' +
      'table directly, but was only ever exposed via the dashboard\'s ' +
      'HTTP handler, no terminal/CLI equivalent',
      'New sdd/commands/feature.py: `sdd feature list` (every feature ' +
      'folder under .specify/features/, each with its current pipeline ' +
      'stage, current-feature marker) and `sdd feature status ' +
      '[--feature NAME]` (full pipeline -- done/current/upcoming/' +
      'skipped steps with who-to-ask-next hints; per-document ' +
      'Approvals-table detail -- who\'s approved, who\'s pending, by ' +
      'role; task progress; Business Objective rollup -- the same ' +
      'picture sdd dashboard renders for one feature, as terminal text, ' +
      'with zero integrations.yml/Jira requirement)',
      'Both call build_project_status()/build_feature_status() directly ' +
      '-- no new data model, no manifest.yml schema change, nothing ' +
      'that could drift from what the dashboard shows, since it\'s the ' +
      'identical function computing both',
      'Promoted status.py\'s private _list_feature_names() to a public ' +
      'list_feature_names() (kept _list_feature_names as an internal ' +
      'alias so every existing internal call site is unchanged) -- ' +
      'feature.py and build_project_status() now share the one ' +
      'canonical directory-scan implementation instead of feature.py ' +
      'needing its own copy',
      'Registered in sdd/__main__.py as `sdd feature`. Added a `sdd ' +
      'feature` entry to cli-python/README.md\'s CLI command reference, ' +
      'explicitly contrasting it with `sdd review status` since the ' +
      'two look similar but serve different scopes',
      'This Node CLI has no feature-status concept of its own ' +
      '(scaffolding-only by design) and is unaffected by any of this -- ' +
      'this migration entry exists so both CLIs report the same ' +
      'sdd_version chain',
      'Verified: cli-python pytest 993/993 (983 pre-existing + 10 new); ' +
      'ruff check/format clean (2 pre-existing E741 warnings in ' +
      'status.py confirmed unrelated); mypy diff against a stashed ' +
      'baseline shows zero new errors, feature.py itself has none at ' +
      'all; manually smoke-tested end-to-end against a hand-built ' +
      '2-feature project',
    ],
  },
  {
    from: '2.9.20',
    to:   '2.9.21',
    description: "Docs: --feature added to every CR (Change Request) example -- none of them showed it before, exactly the drift risk this session's Feature Drift Check work guards against elsewhere",
    notes: [
      'Direct follow-up: \'does the CR resolve based on manifest ' +
      'feature?\' confirmed via code -- sdd cr submit/check resolve ' +
      'feature_name = --feature or manifest.project.feature, same as ' +
      'every other command -- but no CR example anywhere in the docs ' +
      'showed --feature at all',
      'packs/_shared/full/.github/prompts/change.prompt.md (canonical ' +
      'source): Step 7\'s \'Submit for Stakeholder Review\' now runs ' +
      '`sdd cr submit --cr CR-{NNN} --feature {feature}` (was bare), ' +
      'with a note explaining why -- CR numbering restarts per feature ' +
      '(each has its own changesets/ folder), so an implicit ' +
      'resolution risks acting on the wrong feature\'s CR after a ' +
      'Feature Drift Check-class scenario. Same fix applied to both ' +
      '`sdd cr check` mentions (the chat-mode fallback message and the ' +
      'Step 8 summary block). Synced to all 5 packs',
      'Added a \'Change Requests (CR) -- Submit for Review\' subsection ' +
      'to all 5 packs\' HOW-TO-USE.md (before \'Confluence -- Push ' +
      'Documents\', where the only pre-existing CR-adjacent example -- ' +
      '/jira-push chg CR-001, a different command entirely -- already ' +
      'lived). Also added --feature to that pre-existing /jira-push ' +
      'chg CR-001 example line itself, same reasoning',
      'Added a `sdd cr` entry to cli-python/README.md\'s CLI command ' +
      'reference -- this command had no entry there at all before now, ' +
      'a pre-existing documentation gap found while locating where the ' +
      '\'CR examples\' actually lived',
      'This Node CLI has no CR/change-request concept of its own ' +
      '(scaffolding-only by design) and is unaffected by any of this ' +
      '-- this migration entry exists so both CLIs report the same ' +
      'sdd_version chain',
      'Verified: cli-python pytest 993/993 (no .py files touched, pure ' +
      'prompt/doc content); check-cross-references.py clean across all ' +
      '6 packs; sync-blocks.sh run twice consecutively with zero ' +
      'drift; test-setup.sh 19/19 passed',
    ],
  },
  {
    from: '2.9.21',
    to:   '2.9.22',
    description: "validate.prompt.md's CHECKLIST GATE now actually blocks at mvp/full scope, matching what CLAUDE.md already claimed -- found via a live dashboard report ('Next: Run /checklist' shown even though Validate/Analyze/Clarify/Design/LLD/Stories were all already approved)",
    notes: [
      'Root cause: CLAUDE.md\'s Scope Reference table and the ' +
      '/checklist section both document /checklist as \'Mandatory for ' +
      'mvp and full scope ... All CRITICAL items must be resolved ' +
      'before /validate can proceed\' -- but every pack\'s ' +
      'validate.prompt.md Step 0 (\'CHECKLIST GATE (advisory)\') was ' +
      'hard-coded to never block, regardless of scope (\'Do NOT block ' +
      'validate -- /checklist is optional\'). A project could sail from ' +
      'SRD straight through /validate/-analyze/-clarify/-design/' +
      '-plan-lld/-task, all approved, without /checklist ever running ' +
      '-- exactly contradicting the pack\'s own documented policy. The ' +
      'dashboard\'s \'Next: Run /checklist\' was accurate the whole ' +
      'time; the framework just never enforced what it claimed',
      'Fixed in all 5 packs\' validate.prompt.md Step 0: now ' +
      'scope-aware -- pilot stays advisory (warn, don\'t block), ' +
      'mvp/full now genuinely BLOCK when checklists/ is missing (never ' +
      'run) or has open CRITICAL items. sdd-micro excluded (no ' +
      '/checklist in that pack by design)',
      'Fixed all 5 packs\' CLAUDE.md: the self-contradictory section ' +
      'heading \'/checklist -- Optional Spec-Quality Gate\' (directly ' +
      'contradicted the next line, \'Mandatory for mvp and full ' +
      'scope\') is now just \'/checklist -- Spec-Quality Gate\'',
      'Real behavior change for existing mvp/full-scope projects: a ' +
      'project that previously skipped /checklist and already has ' +
      'Validate approved will now be BLOCKED on its next /validate run ' +
      'until /checklist is run and CRITICAL items resolved -- catching ' +
      'up late is expected and intended, not a regression',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain',
      'No .py/.js files touched (pure prompt/CLAUDE.md content); ' +
      'check-cross-references.py clean across all 6 packs; ' +
      'sync-blocks.sh run twice consecutively with zero unexpected ' +
      'drift; test-setup.sh 19/19 passed',
    ],
  },
  {
    from: '2.9.22',
    to:   '2.9.23',
    description: "sdd dashboard: feature tab strip, collapsible section toggles, and stat-tile widgets for multi-feature projects -- requested directly after a user attached a real dashboard PDF snapshot showing the page had grown very long with several features stacked one after another",
    notes: [
      'Client-side only (dashboard_static/app.js + style.css, served ' +
      'verbatim by dashboard.py) -- no Python/server-side changes, no ' +
      'API shape changes, all 74 existing dashboard pytest tests pass ' +
      'unchanged since they only exercise the HTTP handler / JSON API, ' +
      'not the JS/CSS',
      'Feature tab strip (renderFeatureTabs()): only the ACTIVE ' +
      'feature\'s full block (Full Pipeline + Documents + BOs + ' +
      'Timeline + Tasks + Token Usage + Jira Export -- 7 cards) renders ' +
      'now, replacing both the old always-stacked layout and the old ' +
      '\'Features Overview\' table with one compact widget that shows ' +
      'stage + tasks% per feature and switches the active one on click. ' +
      'Single-feature projects are unaffected -- tabs only appear at 2+ ' +
      'features, same threshold the old overview table used',
      'Collapsible section toggles: Living Documents and the ' +
      'project-wide Business Objectives Overview are now <details ' +
      'class="collapsible"> (open by default, same chevron treatment as ' +
      'the existing \'Where this data comes from\' info box) instead of ' +
      'plain cards -- measured a ~22% page-height reduction when ' +
      'collapsed on a 3-feature/9-BO test fixture',
      'Stat-tile widgets: a 3-tile row (Tasks %, Business Objectives ' +
      'outcomes-met, Documents approved) now sits at the top of the ' +
      'active feature\'s block -- previously required scanning three ' +
      'separate cards further down. Business Objectives rows also ' +
      'gained a thin inline progress bar in the Progress cell instead ' +
      'of plain text',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (the Node CLI has no dashboard of its own -- ' +
      'scaffolding-only by design -- so nothing here actually applies ' +
      'to it beyond the version stamp)',
      'Verified: cli-python pytest 993/993; ruff check/format clean; ' +
      'mypy clean; node --check app.js valid syntax. Manually verified ' +
      'end-to-end with a real HTTP server against a synthetic ' +
      '3-feature fixture with the full BO->BR->FR->Task rollup chain ' +
      'wired, screenshotted via Playwright/Chromium in light and dark ' +
      'theme: tab switching, stat tiles, BO progress bars, and the ' +
      'collapse toggle all confirmed working; dark mode colors adapt ' +
      'correctly through the existing CSS variable system',
    ],
  },
  {
    from: '2.9.23',
    to:   '2.9.24',
    description: "sdd dashboard: Tasks pagination, Documents/BO toggles extended to per-feature cards, and a real bug fix -- none of v2.9.23's collapsible sections actually survived the 5s poll -- found via direct user follow-up asking for a full UX review of the dashboard",
    notes: [
      'Client-side only (dashboard_static/app.js + style.css), plus ' +
      'one test updated in test_dashboard.py for renderJiraExport()\'s ' +
      'new third parameter -- no other Python/server-side changes',
      'Tasks pagination: a real project\'s tasks.md can run to ' +
      '50-200+ entries -- renderTasks() now paginates at 20 rows/page ' +
      '(TASKS_PAGE_SIZE) with Prev/Next buttons and a \'Showing X-Y of ' +
      'N - page P/C\' indicator, state.taskPage kept per-feature so ' +
      'switching tabs preserves position. The aggregate progress ' +
      'bar/summary line above the table always reflects the FULL ' +
      'list, not just the current page',
      'Documents (per-feature) and Business Objectives (per-feature) ' +
      'are now collapsible like the project-wide sections already ' +
      'were -- Documents defaults open (bounded list), Business ' +
      'Objectives defaults open only at <=8 BOs ' +
      '(BO_OVERVIEW_AUTO_COLLAPSE_THRESHOLD, also retrofitted onto the ' +
      'existing project-wide BO Overview, which previously always ' +
      'defaulted open regardless of size)',
      'Jira Export\'s Stories/Tasks lists (comma-joined ticket keys, ' +
      'not a table, but still a wall of ~100 links on a big feature) ' +
      'truncate at 12 items with a \'+N more\'/\'show less\' toggle ' +
      '(JIRA_EXPORT_LIST_LIMIT)',
      'Real bug found and fixed while reviewing the whole design: ' +
      'NONE of v2.9.23\'s <details class="collapsible"> sections ' +
      'actually persisted a user\'s open/closed choice -- #root is ' +
      'rebuilt wholesale on every 5s poll, so a manual toggle silently ' +
      'snapped back to its hardcoded default every 5 seconds. Fixed ' +
      'with state.collapsed (keyed by a stable data-section-id per ' +
      '<details>) plus a capture-phase \'toggle\' listener on #root -- ' +
      'native \'toggle\' events don\'t bubble, so capture phase is ' +
      'required for delegation to reach them at all -- and a new ' +
      'sectionOpenAttr(id, defaultOpen) helper that only falls back to ' +
      'the smart default when the user hasn\'t chosen explicitly yet. ' +
      'Applied to all four collapsible sections',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (no dashboard of its own, unaffected beyond the version ' +
      'stamp)',
      'Verified: cli-python pytest 993/993 (992 unchanged + 1 fixed ' +
      'for renderJiraExport\'s new signature); ruff check/format ' +
      'clean; mypy clean; node --check app.js valid syntax. Manually ' +
      'verified end-to-end with a real HTTP server against a ' +
      'synthetic 87-task/14-BO/87-Jira-key fixture, screenshotted via ' +
      'Playwright/Chromium: pagination page 1/5 -> 2/5 transitions ' +
      'correctly, the 14-BO section auto-collapsed as designed, Jira ' +
      'Export\'s \'+75 more\' toggle works, and the persistence fix ' +
      'was directly verified by manually opening a collapsed section ' +
      'then calling the app\'s own refresh() (simulating the 5s poll) ' +
      'and confirming it stayed open -- it would have silently ' +
      'reverted before this fix',
    ],
  },
  {
    from: '2.9.24',
    to:   '3.0.0',
    description: "Fixed the dashboard's Spec Quality Checklist pipeline step, which could NEVER show done no matter how many times /checklist actually ran -- found via direct user report, confirmed against the user's own real filesystem path (.../checklists/{feature}-spec-quality.md). Version rolled to 3.0.0 purely by the capped-counter carry rule (2.9.24 was at both the patch and minor cap simultaneously) -- not a semver breaking-change signal",
    notes: [
      'Root cause, two compounding bugs in sdd/utils/status.py: (1) ' +
      '_feature_docs()\'s doc discovery only globs top-level .md files ' +
      'directly under .specify/features/{feature}/, but ' +
      'checklist.prompt.md actually saves to .specify/features/' +
      '{feature}/checklists/{feature}-spec-quality.md -- a ' +
      'subdirectory, with a filename that doesn\'t even match the ' +
      '\'checklist\' doc_key -- so docs_by_key[\'checklist\'] was ' +
      'always absent regardless of how many times /checklist was ' +
      're-run. (2) Even if found, the checklist template has no ' +
      '`> Status: Draft | ...` header like every other spec doc -- ' +
      'it\'s a self-contained audit report (a CHK-NNN findings table + ' +
      'a manual checkbox section), not a document with a review-gated ' +
      'Draft/Approved lifecycle, so the generic doc-kind \'done\' ' +
      'check (status string contains \'approved\') could never have ' +
      'matched it either',
      'Fixed with a dedicated code path instead of forcing checklist ' +
      'into the generic doc-review-gate model it doesn\'t fit: new ' +
      '_checklist_info(root, feature) looks up the real nested path ' +
      'and counts open CRITICAL-severity rows in the CHK-NNN table ' +
      '(reusing the existing _table_rows_after_heading() helper); the ' +
      'pipeline step\'s kind changed from \'doc\' to its own ' +
      '\'checklist\'; _step_state() and _next_action_sentence() both ' +
      'gained a \'checklist\' branch -- done once the file exists with ' +
      'zero open CRITICAL items, current (with an accurate \'N ' +
      'CRITICAL items still open\' message) while they remain, instead ' +
      'of the generic doc fallback which would have wrongly suggested ' +
      '`sdd review check --doc checklist`, a review-gate command that ' +
      'doesn\'t apply here',
      'build_pipeline() gained a new checklist_info parameter ' +
      '(defaults to \'never run\' so every pre-existing call site, ' +
      'including 125+ existing tests, keeps behaving exactly as ' +
      'before); build_feature_status() computes it via ' +
      '_checklist_info() and threads it through',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (no dashboard of its own, unaffected beyond the version ' +
      'stamp)',
      'Verified: cli-python pytest 1000/1000 (993 unchanged + 7 new ' +
      'regression tests, including one that reproduces the exact ' +
      'user-reported scenario end-to-end through build_feature_status' +
      '() with a real file on disk at the real nested path, confirming ' +
      'the pipeline step shows done and next_action moves past it once ' +
      'downstream is already ahead -- exactly the contradiction the ' +
      'user hit); ruff check/format clean; mypy clean',
    ],
  },
  {
    from: '3.0.0',
    to:   '3.0.1',
    description: "Strengthened the shared Token Usage Logging step (synced to 19 prompt files x 5 packs) after a live user report during /implement: logging was silently skipped for every task once the user asked to proceed through all tasks without stopping for 'go' between them",
    notes: [
      'User\'s scenario: told the agent to proceed through every ' +
      '/implement task without stopping for per-task \'go\'. The ' +
      'agent\'s own transcript showed it interpreting this broadly -- ' +
      'it also silently skipped the Token Usage Logging step for ' +
      'every task, even though token-pricing.yml was already ' +
      'configured and working (confirmed: other commands in the same ' +
      'project -- specify-brd, validate, etc. -- had logged fine)',
      'Root cause: the logging step sits immediately adjacent to the ' +
      '\'WAIT for go\' instruction in every prompt that has it, with ' +
      'nothing telling the agent the two are independent -- an agent ' +
      'optimizing for \'proceed without stopping\' could plausibly ' +
      'read that as license to also skip the adjacent housekeeping ' +
      'step, since nothing said otherwise',
      'Fixed: added a paragraph to ' +
      'packs/_shared/blocks/token-usage-log-step.md clarifying that ' +
      '\'proceed without stopping\' / \'skip confirmation\' ' +
      'instructions waive the PAUSE between steps, not the logging ' +
      'step -- it must still run after every single task/command ' +
      'execution regardless, even mid-way through a batch, since ' +
      'skipping it silently produces an incomplete token-usage.md ' +
      'that under-reports cost',
      'Pack-content-only (prompt instruction text for the AI agent) ' +
      '-- no CLI code touched',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain',
      'Verified: check-cross-references.py clean across all 6 packs; ' +
      'sync-blocks.sh run three times consecutively with zero drift ' +
      'after the first sync (96 files touched: 95 synced pack prompts ' +
      '+ 1 canonical block source); test-setup.sh 19/19 passed; ' +
      'test-setup-micro.sh 12/12 passed (sdd-micro has no such block, ' +
      'unaffected)',
    ],
  },
  {
    from: '3.0.1',
    to:   '3.0.2',
    description: "New `sdd hooks` command: installs a git post-commit hook that makes per-commit Token Usage Logging deterministic during /implement, instead of relying solely on the AI agent following a prompt-file instruction",
    notes: [
      'Direct follow-up to v3.0.1\'s prompt fix -- the user confirmed ' +
      'it wasn\'t enough. Even after pulling the updated framework and ' +
      'manually catching up with `sdd token-log --command implement` ' +
      '(confirming the mechanism itself works fine), the agent still ' +
      'wasn\'t calling it automatically per task during a live batched ' +
      '/implement run. Explicit ask: \'I need for each task.\' A ' +
      'prompt instruction is followed probabilistically, not enforced ' +
      '-- an agent optimizing for \'proceed without stopping\' can ' +
      'plausibly skip adjacent housekeeping regardless of wording, so ' +
      'the only way to make this actually deterministic is ' +
      'code-level, not more prose',
      'New cli-python/sdd/commands/hooks.py: `sdd hooks install` ' +
      'writes .git/hooks/post-commit to call `sdd token-log --command ' +
      'implement` after every commit -- silent/best-effort (no-ops if ' +
      'sdd isn\'t on PATH, token-pricing.yml isn\'t configured, or ' +
      'nothing\'s new since the last logged row) and never blocks the ' +
      'commit it\'s attached to (no `set -e`, unconditional `exit ' +
      '0`). Refuses to overwrite a pre-existing foreign post-commit ' +
      'hook unless --force is passed; idempotent when re-run on its ' +
      'own hook. `sdd hooks status`/`sdd hooks uninstall` for symmetry',
      'Deliberately opt-in, NOT wired into `sdd init`/setup.sh -- ' +
      'installing a git hook is a real side effect on the user\'s ' +
      'repository and shouldn\'t happen without being asked, same ' +
      'principle as token-pricing.yml itself being opt-in',
      'Documented: packs/_shared/blocks/token-usage-logging.md ' +
      '(synced to all 5 packs\' CLAUDE.md) gained a closing paragraph ' +
      'pointing at `sdd hooks install`; cli-python/README.md gained a ' +
      '`### sdd hooks` reference section (previously had none)',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (the Node CLI has no /implement concept of its own -- ' +
      'scaffolding-only by design -- so nothing here actually applies ' +
      'to it beyond the version stamp)',
      'Verified: cli-python pytest 1013/1013 (1000 unchanged + 13 new ' +
      'tests covering fresh install, idempotent re-install, ' +
      'foreign-hook refusal with/without --force, status in all three ' +
      'states, uninstall in all three states, not-a-git-repo handling, ' +
      'and a direct assertion the hook script can never fail a ' +
      'commit); ruff check/format clean; mypy clean (35 source files, ' +
      'up from 34); bandit 0 issues. check-cross-references.py clean ' +
      'across all 6 packs; sync-blocks.sh run twice consecutively ' +
      'with zero drift; test-setup.sh 19/19 passed; test-setup-micro.sh ' +
      '12/12 passed',
    ],
  },
  {
    from: '3.0.2',
    to:   '3.1.0',
    description: "Two purely-additive discoverability links -- `sdd --help` and the dashboard now both point at where to report a bug or request a feature",
    notes: [
      'Follow-up to setting up GitHub Issues (templates, ' +
      'CONTRIBUTING.md, SECURITY.md, making the repo public) earlier ' +
      'the same session -- those solved \'does a place to report ' +
      'issues exist\', this solves \'does anyone using the CLI or ' +
      'dashboard actually see it\', since most sddflow users interact ' +
      'via pip install + CLI/dashboard and may never visit the GitHub ' +
      'repo page directly',
      'cli-python/sdd/__main__.py: the top-level `sdd` Click group ' +
      'gained an epilog shown at the bottom of `sdd --help` -- ' +
      '\'Found a bug or have a feature request? ' +
      'https://github.com/sunil1983us/sddflow/issues\'',
      'cli-python/sdd/commands/dashboard_static/page.html + ' +
      'style.css: a static footer link with the same URL, added ' +
      'outside #root so it survives the dashboard\'s 5s poll ' +
      'innerHTML rebuild untouched -- no app.js changes needed',
      'Also added (not part of this version bump -- prose/governance ' +
      'files sdd upgrade never reads, same bucket as ' +
      'CONTRIBUTING.md/SECURITY.md): CODE_OF_CONDUCT.md (Contributor ' +
      'Covenant v2.1) and .github/PULL_REQUEST_TEMPLATE.md, closing ' +
      'the same gap as GitHub\'s spec-kit repo\'s community-health ' +
      'sidebar',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (the Node CLI has no dashboard or equivalent --help ' +
      'epilog of its own -- scaffolding-only by design -- so nothing ' +
      'here actually applies to it beyond the version stamp)',
      'Verified: cli-python pytest 1013/1013 (unchanged -- no test ' +
      'asserts --help/footer output verbatim); ruff check/format ' +
      'clean; mypy clean (35 source files); `sdd --help` manually ' +
      'confirmed to show the new epilog',
    ],
  },
  {
    from: '3.1.0',
    to:   '3.1.1',
    description: "URL correction following the GitHub repo rename (sunil1983us/universalguide -> sunil1983us/sddflow) -- pure bug fix, no new behavior",
    notes: [
      'The repo was renamed to match the actual product branding ' +
      '(sddflow is already the PyPI package name, npm package name, ' +
      'and CLI binary name -- universalguide never matched any of ' +
      'them). GitHub\'s redirect covers old links indefinitely, but ' +
      'v3.1.0\'s --help epilog and dashboard footer link should say ' +
      'what\'s actually true rather than rely on a redirect forever',
      'cli-python/sdd/__main__.py\'s --help epilog and ' +
      'cli-python/sdd/commands/dashboard_static/page.html\'s footer ' +
      'link both updated to https://github.com/sunil1983us/sddflow/issues',
      'Also corrected in the same sweep (no bump needed on their own ' +
      '-- prose/governance files sdd upgrade never reads): README.md, ' +
      'CONTRIBUTING.md, SECURITY.md, CHANGELOG.md\'s newest entry, ' +
      'pyproject.toml/package.json URLs, the issue templates, and ' +
      'each pack\'s README/QUICKSTART/FLOW-ROLES-GATES.md',
      'Deliberately NOT touched: a test fixture in ' +
      'test_claude_code_transcript.py referencing ' +
      '\'/home/user/Universalguide\' as a local filesystem path ' +
      '(unrelated to the repo name, coincidental match) and an old ' +
      'CHANGELOG.md entry documenting a past release\'s git clone ' +
      'example (historical record, not rewritten)',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (the Node CLI has no dashboard or --help epilog of its ' +
      'own -- scaffolding-only by design -- so nothing here actually ' +
      'applies to it beyond the version stamp)',
      'Verified: cli-python pytest 1013/1013; ruff check/format ' +
      'clean; mypy clean (35 source files); bandit 0 issues; node ' +
      '28/28; grep sweep confirms zero remaining \'universalguide\' ' +
      'references outside the two intentionally-excluded files',
    ],
  },
  {
    from: '3.1.1',
    to:   '3.2.0',
    description: "New `sdd doctor` command -- read-only report of drift between a project's framework-managed files and the currently installed CLI's pack content",
    notes: [
      'First step of a larger effort responding to external review ' +
      'feedback (verified independently before acting on any of it -- ' +
      'radon complexity numbers and coverage percentages matched ' +
      'exactly when re-run): sdd upgrade has only ever stamped ' +
      'manifest.yml\'s sdd_version field, never actually syncing a ' +
      'project\'s templates/prompts/commands/instructions/setup-' +
      'scripts/workflows/.cursor/.vscode files forward to match the ' +
      'installed CLI\'s pack content -- so a project could report ' +
      'itself \'upgraded\' while every one of those files still ' +
      'matched whatever version it was originally scaffolded with',
      'sdd doctor is deliberately read-only -- reports drift, changes ' +
      'nothing -- so it\'s safe to ship and use immediately, ahead of ' +
      'the much bigger sdd upgrade rewrite that will actually apply ' +
      'fixes (a later bump)',
      'New cli-python/sdd/utils/managed_files.py: SHA-256-hashes ' +
      'every managed file in the pack bundled with the currently ' +
      'installed CLI (the \'canonical\' content) and in the project ' +
      'itself, classifying each as up-to-date / missing / needs-' +
      'update / user-modified / differs-for-unknown-reason (the last ' +
      'one being the honest fallback for every project scaffolded ' +
      'before this existed -- no baseline recorded, so it can\'t ' +
      'distinguish a pack update from a hand edit, and doesn\'t guess)',
      'New cli-python/sdd/commands/doctor.py: `sdd doctor` CLI ' +
      'wrapper, reuses upgrade.py\'s existing _resolve_pack() for ' +
      'pack detection, --pack to override, --quiet to only show ' +
      'non-clean files, exit code 0/1 (scriptable)',
      'Real finding surfaced by dogfooding this against a real ' +
      'freshly-scaffolded project, not from the external review: ' +
      '_resolve_pack()\'s existing project_type inference can ' +
      'silently guess the wrong pack for any sdd-universal-scaffolded ' +
      'project, since sdd-universal handles every project_type from ' +
      'one shared set of files rather than becoming a type-specific ' +
      'pack, and manifest.yml has never recorded an explicit ' +
      '\'pack:\' field to disambiguate. Root-caused but not fixed ' +
      'here -- doctor detects when _resolve_pack\'s answer came from ' +
      'inference rather than an explicit stored field and prints a ' +
      'prominent warning instead of silently presenting a guess as ' +
      'fact; a real fix belongs with the pack_version/manifest-schema ' +
      'split planned next in this phased effort',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same ' +
      'sdd_version chain (the Node CLI has no doctor command of its ' +
      'own -- scaffolding-only by design -- so nothing here actually ' +
      'applies to it beyond the version stamp)',
      'Verified: cli-python pytest 1035/1035 (1012 unchanged + 23 new ' +
      'covering inventory building, hashing, baseline loading/' +
      'malformed-JSON handling, all 5 classification branches ' +
      'directly, and the CLI wrapper\'s exit codes/--quiet/inference-' +
      'warning banner); manually verified end-to-end against a real ' +
      'freshly-scaffolded project (113/113 up to date with the ' +
      'correct pack; a hand-edit and a deletion both caught ' +
      'precisely, nothing else flagged); ruff check/format clean; ' +
      'mypy clean (37 source files, up from 35); bandit 0 issues',
    ],
  },
  {
    from: '3.2.0',
    to:   '3.3.0',
    description: "New required-going-forward `pack:` field in manifest.yml, closing the pack-identity gap sdd doctor's warning banner (added in 3.2.0) could only detect, not fix",
    notes: [
      'Direct follow-up to 3.2.0: that release shipped sdd doctor with ' +
      'a warning banner for the case where _resolve_pack() had to ' +
      '*infer* a project\'s pack from project_type rather than read it ' +
      'from an explicit field -- most visibly wrong for sdd-universal, ' +
      'which serves all 10 project_types from one shared set of files ' +
      'and was being silently resolved to a type-specific pack (e.g. ' +
      'sdd-backend-service) instead of itself',
      'This bump fixes it at the source instead of just flagging it: ' +
      'every pack\'s own manifest.yml template (sdd-backend-service, ' +
      'sdd-frontend-spa, sdd-fullstack, sdd-mobile, sdd-universal, and ' +
      'sdd-micro outside the lockstep) now bakes in a static ' +
      '`pack: "sdd-..."` line right after sdd_version, the same ' +
      'pattern already used for sdd_version\'s own static default -- ' +
      'setup.sh/setup.ps1 need no template-substitution logic, the ' +
      'value is simply correct for every project scaffolded from that ' +
      'pack',
      '_resolve_pack() in upgrade.py already prioritized ' +
      'manifest.get(\'pack\') above project_type inference (added in ' +
      'the 3.2.0 work) -- this bump is what actually makes that branch ' +
      'fire for setup.sh/setup.ps1-scaffolded projects; sdd init-' +
      'scaffolded projects were already unaffected, since init has ' +
      'stamped manifest_patch[\'pack\'] since before this phased ' +
      'effort started',
      'PACK-SPEC.md\'s documented manifest.yml schema updated to list ' +
      '`pack:` as a required field alongside sdd_version, so community ' +
      'pack authors building against PACK-SPEC.md include it from day ' +
      'one',
      'Existing projects on older sdd_version have no `pack:` field ' +
      'yet -- this migration entry only stamps sdd_version forward, as ' +
      'always; a project without the field simply keeps falling back ' +
      'to inference (with the 3.2.0 warning banner) until it\'s re-' +
      'scaffolded or the field is added by hand -- there is no ' +
      'destructive or surprising behavior change for anyone upgrading',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (the Node CLI has no pack-resolution logic of its own -- ' +
      'scaffolding-only by design -- so nothing here actually applies ' +
      'to it beyond the version stamp)',
      'Verified: cli-python pytest 1035/1035 (unaffected by the ' +
      'manifest-only change); all 6 packs\' manifest.yml confirmed to ' +
      'parse as valid YAML with the new field; check-cross-' +
      'references.py clean across all 6 packs; test-setup.sh 19/19 and ' +
      'test-setup-micro.sh 12/12 passed; two real functional scaffolds ' +
      're-confirmed the fix end-to-end -- a fresh sdd-backend-service ' +
      'scaffold now resolves via "manifest.yml \'pack\' field" with no ' +
      'warning, and a fresh sdd-universal scaffold (setup.sh --type ' +
      'backend-service) now correctly resolves to sdd-universal ' +
      'instead of the previously-mis-inferred sdd-backend-service',
    ],
  },
  {
    from: '3.3.0',
    to:   '3.4.0',
    description: "New `sdd upgrade --apply-files` -- the real fix, not just the report: safely applies pack-content updates to an existing project instead of only stamping sdd_version",
    notes: [
      'Completes the effort sdd doctor (3.2.0) and the pack: field ' +
      '(3.3.0) were building toward: sdd upgrade used to only ever ' +
      'patch manifest.yml\'s sdd_version -- it never touched the ' +
      'actual template/prompt/command/instruction/setup-script files a ' +
      'project was scaffolded with. --apply-files now actually applies ' +
      'safe updates instead of just reporting them',
      'New sdd/utils/managed_files.py: apply_managed_files() and ' +
      'write_baseline(). Reuses check_managed_files()\'s existing ' +
      'classification -- MISSING and NEEDS_UPDATE (local still matches ' +
      'its last recorded baseline, only canonical content moved on) ' +
      'are applied automatically; USER_MODIFIED and DIFFERS_UNKNOWN ' +
      '(no baseline to tell an update apart from a hand edit) are left ' +
      'alone unless --force is also passed. Every file actually ' +
      'overwritten is backed up first to .specify/.managed-files-' +
      'backups/{timestamp}/, never silently discarded. A fresh ' +
      'baseline is written after every run -- including runs where ' +
      'nothing changed on disk, so a project that\'s already current ' +
      'the first time this flag is used still gets a baseline recorded ' +
      'immediately, rather than only after its first divergence',
      'sdd upgrade gained --apply-files and --force flags alongside ' +
      'the existing --sync-prompts (kept, narrower, unchanged, for ' +
      'backward compatibility). sdd doctor\'s closing note and ' +
      'docstring updated to point at --apply-files now that it exists, ' +
      'instead of saying sdd upgrade doesn\'t apply anything yet',
      'README.md gained a full --apply-files walkthrough plus a new ' +
      '`sdd doctor` section, which had never been documented there at ' +
      'all since it shipped in 3.2.0',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (the Node CLI has no upgrade --apply-files of its own -- ' +
      'scaffolding-only by design -- so nothing here actually applies ' +
      'to it beyond the version stamp)',
      'Verified: cli-python pytest 1055/1055 (1035 unchanged + 20 new ' +
      'covering apply_managed_files()/write_baseline() directly -- ' +
      'missing/needs-update/user-modified/force/dry-run/unknown-pack ' +
      '-- and the CLI wrapper\'s preview, confirm, cancel, --yes, ' +
      '--force, conflicts-only, and pack-inference paths); ruff ' +
      'check/format clean; mypy clean (37 source files); bandit 0 ' +
      'issues; node test 28/28; manually verified end-to-end against a ' +
      'real freshly-scaffolded project -- baseline correctly written ' +
      'on a no-op run, a hand-edited file correctly classified as ' +
      'modified locally by sdd doctor, correctly left alone by ' +
      '--apply-files without --force, and correctly overwritten-with-' +
      'backup by --apply-files --force',
    ],
  },
  {
    from: '3.4.0',
    to:   '3.4.1',
    description: "Bugfix: `sdd config test` no longer crashes with a raw traceback when a Jira/Confluence server responds 200 with a non-JSON body",
    notes: [
      'Real user report: testing PAT auth against two Jira/Confluence ' +
      'Data Center servers, `sdd config test` crashed with an ' +
      'unhandled `json.decoder.JSONDecodeError: Expecting value: line ' +
      '1 column 1 (char 0)` traceback instead of a clean per-service ' +
      'status line',
      'Root cause: response.json() raises this when the server answers ' +
      '200 with a non-JSON body -- most commonly an SSO/login-page ' +
      'redirect, or base_url pointing at the wrong path entirely. ' +
      '`except requests.HTTPError` never caught it, since JSONDecodeError ' +
      'is a RequestException *sibling*, not a subclass of HTTPError -- ' +
      'an easy exception-hierarchy mistake to make and never notice ' +
      'until it happens for real',
      'Fixed by extracting the duplicated Jira/Confluence probe logic ' +
      'in cli-python/sdd/commands/config.py into one _probe_service() ' +
      'helper with three distinct except clauses: HTTPError (the ' +
      'server said no, show its status+body), JSONDecodeError (caught ' +
      'both as the bare stdlib class -- older requests versions raise ' +
      'that directly, matching what the reporting user\'s traceback ' +
      'showed -- and requests.exceptions.InvalidJSONError, the modern ' +
      'requests>=2.27 wrapper -- shows an actionable message pointing ' +
      'at base_url/SSO/token validity instead of a raw parse error), ' +
      'and any other RequestException (connection refused, DNS ' +
      'failure, timeout, TLS error, malformed URL -- requests\' own ' +
      'message is clear enough on its own)',
      'No manifest.yml or generated-file changes -- purely a crash fix ' +
      'in CLI error handling, nothing for an existing project to ' +
      'migrate',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (the Node CLI has no `sdd config test` of its own -- ' +
      'scaffolding-only by design -- so nothing here actually applies ' +
      'to it beyond the version stamp)',
      'Verified: cli-python pytest 1098/1098 (1094 unchanged + 4 new ' +
      'covering all three failure modes, including the exact bare-' +
      'stdlib-JSONDecodeError reproduction of the reported bug and the ' +
      'modern requests-wrapped variant); ruff check/format clean; mypy ' +
      'clean (37 source files); bandit 0 issues; manually confirmed ' +
      'end-to-end through the full Click CLI invocation path (not just ' +
      'the unit tests) -- a probe against a real unreachable server ' +
      'produces a clean per-service error line and exit code 0, never ' +
      'a traceback',
    ],
  },
  {
    from: '3.4.1',
    to:   '3.4.2',
    description: "Bugfix: Jira/Confluence client now targets the correct REST API version/path for Server & Data Center deployments, not just Cloud",
    notes: [
      'Confirmed against two real Jira/Confluence Data Center servers ' +
      '(the same user who reported the 3.4.1 crash): Jira Server/DC ' +
      'does not support REST API v3 at all -- only v2 (JRASERVER-70688, ' +
      'an Atlassian feature request for v3 on Data Center, is still ' +
      'open, confirming this). Confluence Server/DC\'s REST API sits ' +
      'directly at /rest/api, with no /wiki prefix -- that prefix is a ' +
      'Cloud-only convention (Cloud sites share a domain with Jira ' +
      'Cloud, so /wiki disambiguates them there; a standalone Server/DC ' +
      'install has no such collision)',
      'sdd/utils/jira_client.py and confluence_client.py hardcoded the ' +
      'Cloud-only paths (v3, /wiki) unconditionally before this -- ' +
      'every request against a Server/DC instance failed, not always ' +
      'with a clean error: a reverse proxy or SSO gateway in front of ' +
      'the real instance can respond 200 with an HTML login page, or ' +
      '403, for a path it doesn\'t recognize -- which is exactly what ' +
      'the 3.4.1 crash report turned out to be a symptom of',
      'Added Profile.deployment (sdd/utils/atlassian_auth.py): ' +
      '\'server\' for auth_mode == \'pat\', \'cloud\' otherwise. ' +
      'Personal Access Tokens are a Server/DC-only feature -- Cloud ' +
      'doesn\'t support them -- so auth_mode alone is a reliable ' +
      'signal, no separate config field needed. JiraClient/' +
      'ConfluenceClient both gained an optional deployment= keyword ' +
      '(default \'cloud\', so every existing Cloud profile\'s behavior ' +
      'is unchanged) that switches v3->v2 and drops the /wiki prefix ' +
      'for \'server\'',
      'Threaded through all 24 call sites across 8 command files ' +
      '(config.py, jira.py, confluence.py, review.py, cr.py, ' +
      'dashboard.py, pr.py) -- every one already had the Profile ' +
      'object in hand, so each is a one-line deployment=prof.deployment ' +
      'addition, mechanically applied and individually verified',
      'No manifest.yml or generated-file changes -- purely a ' +
      'connectivity fix for PAT/Server-DC profiles; existing Cloud ' +
      '(basic/oauth2) profiles see zero behavior change',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (the Node CLI has no Jira/Confluence client of its own -- ' +
      'scaffolding-only by design -- so nothing here actually applies ' +
      'to it beyond the version stamp)',
      'Verified: cli-python pytest 1108/1108 (1098 unchanged + 10 new ' +
      '-- Profile.deployment for all three auth_modes, JiraClient/' +
      'ConfluenceClient\'s _api() URL construction for both ' +
      'deployments, and one true end-to-end test using the REAL client ' +
      'classes, not fakes, confirming a pat profile actually requests ' +
      '/rest/api/2/myself and /rest/api/user/current with no /wiki ' +
      'segment); ruff check/format clean; mypy clean (37 source files); ' +
      'bandit 0 issues; manually confirmed end-to-end through the full ' +
      'Click CLI invocation path with the real client classes and a ' +
      'mocked Session, matching exactly what the reporting user ' +
      'independently verified by hand with curl/Invoke-RestMethod ' +
      'against their own Data Center servers',
    ],
  },
  {
    from: '3.4.2',
    to:   '3.4.3',
    description: "Security hardening: sdd/utils/git_host.py's host detection no longer trusts a substring match, closing a CodeQL-flagged host-spoofing gap",
    notes: [
      'parse_remote() decided which git host (github/bitbucket/gitlab/' +
      'azure) a repo\'s origin remote belongs to via plain ' +
      '`"github.com" in host`-style substring checks -- CodeQL\'s py/' +
      'incomplete-url-substring-sanitization flagged all 5 occurrences ' +
      '(github.com, bitbucket.org, gitlab, dev.azure.com, ' +
      'visualstudio.com): a host like notgithub.com or github.com.evil.' +
      'example contains the substring "github.com" without being ' +
      'github.com or a subdomain of it',
      'Added _host_is(host, domain) -- exact match or subdomain via ' +
      'str.endswith(f\'.{domain}\') -- for the four hosts that pin to ' +
      'one real domain (github.com, bitbucket.org, dev.azure.com, ' +
      'visualstudio.com). gitlab\'s check stays deliberately broader ' +
      '(self-hosted instances live at arbitrary hostnames, e.g. gitlab.' +
      'mycompany.internal) but moved from an anywhere-substring check ' +
      'to _host_has_label(), requiring "gitlab" to be a full dot/' +
      'hyphen-separated label -- closes notgitlab.io/gitlabish.io ' +
      'false-accepts while still detecting gitlab.corp.io/code-gitlab.' +
      'corp.io',
      'Practical exploitability was narrow -- host comes from the ' +
      'local git remote URL (`git remote get-url origin`), which only ' +
      'decides which provider CLI (gh/glab/az) `sdd pr create` shells ' +
      'out to, not a network-facing trust boundary -- but the fix is ' +
      'free and the old behavior was genuinely wrong regardless of ' +
      'exploitability',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same sdd_version ' +
      'chain (the Node CLI has no PR-creation git-host detection of ' +
      'its own -- scaffolding-only by design -- so nothing here ' +
      'actually applies to it beyond the version stamp)',
      'Verified: cli-python pytest 1120/1120 (1108 unchanged + 12 new ' +
      '-- 8 substring-bypass-rejection cases across all 4 pinned ' +
      'hosts, 2 gitlab label-bypass-rejection cases, and 2 confirming ' +
      'genuine self-hosted GitLab detection still works); ruff check/' +
      'format clean; mypy clean; bandit 0 issues',
    ],
  },
  {
    from: '3.4.3',
    to:   '3.5.0',
    description: "sdd confluence push now detects and warns when a page was edited outside sddflow since its own last push, instead of silently overwriting it; new sdd confluence verify command",
    notes: [
      'upsert_page() always overwrote a Confluence page\'s body with ' +
      'whatever the local .md said, using Confluence\'s optimistic-' +
      'locking version number purely to avoid a 409 -- never to ' +
      'detect a manual edit made in between. A reviewer editing the ' +
      'live page directly (fixing a typo, adding a clarification) had ' +
      'that edit silently discarded the next time anyone ran `sdd ' +
      'confluence push`, with no warning it had ever existed',
      'New cli-python/sdd/utils/confluence_push_log.py: ' +
      'docs/confluence/push-log.yml records {page_id: {doc, title, ' +
      'pushed_version}} after every successful push/draft/pull. ' +
      'check_drift() compares a page\'s live version.number against ' +
      'the recorded value (using version.by/version.when Confluence ' +
      'already returns) to tell \'someone edited this since we last ' +
      'wrote it\' apart from a normal, expected re-push',
      '`sdd confluence push` now checks drift before each doc\'s ' +
      'upsert and, if the page moved, prints who edited it and when, ' +
      'then skips that doc -- pass the new --force-overwrite flag ' +
      '(separate from the existing --force, which governs a ' +
      'different warning about title/feature collisions) to push ' +
      'anyway. `sdd confluence draft`/`pull` record the push-log ' +
      'entry but never warn -- draft/pull\'s entire purpose is ' +
      'inviting a human to edit the page directly in Confluence, so ' +
      'flagging that as drift would be a constant false alarm',
      'New `sdd confluence verify` command: read-only, reports ' +
      'up-to-date/drifted/missing for every page in push-log.yml ' +
      'without pushing or pulling anything -- for checking drift on ' +
      'demand rather than only finding out at the next push',
      'docs/confluence/push-log.yml is new, generated state (like ' +
      'docs/jira/{feature}/keys.yml) -- no manifest.yml schema ' +
      'change, and safe to delete: it only ever gets rebuilt from the ' +
      'next push, never re-derived from Confluence itself',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same ' +
      'sdd_version chain (the Node CLI has no Confluence integration ' +
      'of its own -- scaffolding-only by design -- so nothing here ' +
      'actually applies to it beyond the version stamp)',
      'Verified: cli-python pytest 1143/1143 (1120 unchanged + 23 new ' +
      '-- push-log load/record/drift-check unit tests, plus CLI-level ' +
      'tests for the warn-and-skip path, --force-overwrite, and `sdd ' +
      'confluence verify` in all three states); ruff check/format ' +
      'clean; mypy clean (38 source files); bandit 0 issues',
    ],
  },
  {
    from: '3.5.0',
    to:   '3.6.0',
    description: "/clarify now interviews live chat answers one item at a time and pushes back on vague ones, instead of posting the whole list and passively waiting",
    notes: [
      'Previously /clarify wrote every open item to clarify.md, ' +
      'presented the full report, and then just waited -- whatever ' +
      'came back in chat was mapped to an item\'s ID and accepted ' +
      'as-is, even a vague non-answer like \'make it reasonable\' or ' +
      '\'whatever\'s best\'. The item still got marked RESOLVED, and ' +
      'the same ambiguity could resurface unnoticed at /plan-design',
      'Now: after presenting the full report once (so the human can ' +
      'still see everything at a glance), the live-chat path asks ' +
      'about items one at a time -- CRITICAL/HIGH first -- and, if an ' +
      'answer is still vague, asks one specific follow-up instead of ' +
      'accepting it. Pushes back at most twice per item; a third vague ' +
      'answer resolves by best guess instead of looping forever. A ' +
      'human who pastes answers for several items at once is still ' +
      'accepted immediately -- the one-at-a-time cadence is the ' +
      'default, not a hard rule',
      'The three other intake paths are unchanged: editing clarify.md ' +
      'directly and saying \'done\', \'best guess\'/\'continue\', and ' +
      'an async Jira/Confluence comment reply (pulled in by `sdd ' +
      'review pull-answers --doc clarify`) all still bypass the ' +
      'interview entirely -- only the live-chat answer path changed',
      'Prompt-content only (packs/{sdd-backend-service,sdd-frontend-' +
      'spa,sdd-fullstack,sdd-mobile,sdd-universal}/.github/prompts/' +
      'clarify.prompt.md) -- no CLI code touched, no manifest.yml ' +
      'schema change. sdd-micro is unaffected (no /clarify in its ' +
      '3-command scope)',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same ' +
      'sdd_version chain (the Node CLI has no prompt-execution role ' +
      'of its own -- scaffolding-only by design -- so nothing here ' +
      'actually applies to it beyond the version stamp)',
      'Verified: sync-blocks.sh run twice consecutively with zero ' +
      'unexpected drift (only the 5 intentionally-edited clarify.' +
      'prompt.md files changed); check-cross-references.py clean ' +
      'across all 6 packs; test-setup.sh 19/19 passed',
    ],
  },
  {
    from: '3.6.0',
    to:   '3.6.1',
    description: "status.py's _local_jira_links() now traversal-checks the feature name before building docs/jira/{feature}/keys.yml, closing a CodeQL-flagged path-injection gap",
    notes: [
      '_local_jira_links(root, feature, base_url) built docs/jira/' +
      '{feature}/keys.yml by string concatenation -- root / \'docs\' / ' +
      '\'jira\' / feature / \'keys.yml\' -- with no traversal check of ' +
      'its own. Every current caller already validated `feature` ' +
      'before calling in (dashboard.py\'s /api/review-links endpoint ' +
      'via the _SAFE_TOKEN allowlist regex; the CLI sdd status path, ' +
      'same trust level as a user\'s own manifest.yml), so this was ' +
      'never actually reachable with an attacker-controlled value -- ' +
      'but CodeQL\'s py/path-injection query correctly flags that the ' +
      'function itself provides no guarantee, only its callers happen to',
      'Now routes through safe_feature_path() (validate.py -- the ' +
      'same resolve()+relative_to() traversal check every other ' +
      'doc-path resolution in this codebase already uses) before ' +
      'appending \'keys.yml\'. A feature name that tries to escape ' +
      'docs/jira/ returns the same empty {epic: None, stories: [], ' +
      'tasks: []} result as \'no keys file found\' instead of reading ' +
      'whatever\'s at the escaped path',
      'Same shape and precedent as the 3.4.2 -> 3.4.3 git_host.py ' +
      'CodeQL fix: narrow practical exploitability given the existing ' +
      'caller-side guards, but the fix is free and the old behavior ' +
      'was genuinely under-guarded regardless',
      'This Node CLI ships from the same pack sources -- this ' +
      'migration entry exists so both CLIs report the same ' +
      'sdd_version chain (the Node CLI has no status/Jira-links logic ' +
      'of its own -- scaffolding-only by design -- so nothing here ' +
      'actually applies to it beyond the version stamp)',
      'Verified: cli-python pytest 1144/1144 (1143 unchanged + 1 new ' +
      '-- test_jira_keys_rejects_a_traversal_feature_name, confirming ' +
      'a file placed outside docs/jira/ is never read for a ' +
      '\'../../outside\'-style feature value); ruff check/format ' +
      'clean; mypy clean (38 source files); bandit 0 issues',
    ],
  },
];

// Rare migrations that must transform manifest.yml beyond stamping
// sdd_version go here, keyed by "to" version. Every other hop uses the
// trivial default in migrateFn() (all 117 to date have).
const CUSTOM_MIGRATE = {};

export function migrateFn(to) {
  const custom = CUSTOM_MIGRATE[to];
  if (custom) return custom;
  return (manifest) => {
    manifest.sdd_version = to;
    return manifest;
  };
}

// Every migration from currentVersion to SDD_VERSION, in order -- walks
// the linear MIGRATIONS chain (each "from" is unique, so it's a simple
// linked list) rather than matching only the single next hop. A project
// many versions behind used to need one `sdd upgrade` invocation per
// version; this lets the caller see -- and choose to apply -- the whole
// pending chain in one run. Exported so tests/upgrade.test.js can assert
// it directly.
export function pendingMigrations(currentVersion) {
  const byFrom = new Map(MIGRATIONS.map(m => [m.from, m]));
  const chain = [];
  let version = currentVersion;
  const seenTo = new Set();
  while (version !== SDD_VERSION) {
    const m = byFrom.get(version);
    if (!m) break;
    if (seenTo.has(m.to)) break; // guards against an accidental cycle in hand-edited data
    seenTo.add(m.to);
    chain.push(m);
    version = m.to;
  }
  return chain;
}

// Broken out from a bare `process.stdin.isTTY` check so tests can mock
// it directly without needing a real TTY.
function _stdinIsInteractive() {
  return Boolean(process.stdin.isTTY);
}

export async function upgradeCommand(opts = {}) {
  console.log('');
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log(`  ${chalk.bold.cyan('SDD Framework')} — upgrade`);
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log('');

  if (opts.toLatest && opts.step) {
    console.error(chalk.red('✗  --to-latest and --step are mutually exclusive.'));
    process.exit(1);
  }

  if (!existsSync(MANIFEST_PATH)) {
    console.error(chalk.red(`✗  ${MANIFEST_PATH} not found — run from the pack root directory.`));
    process.exit(1);
  }

  const manifest = readManifest();
  const currentVersion = manifest?.sdd_version ?? null;

  if (currentVersion === SDD_VERSION) {
    console.log(chalk.green(`  ✓  Already at v${SDD_VERSION} — nothing to do.`));
    console.log('');
    return;
  }

  console.log(`  Current version : ${chalk.yellow(currentVersion ?? 'pre-versioning (v1.x)')}`);
  console.log(`  Target version  : ${chalk.green(SDD_VERSION)}`);
  console.log('');

  const pending = pendingMigrations(currentVersion);

  if (pending.length === 0) {
    console.log(chalk.yellow('  No migration path found for your current version.'));
    console.log('  You may need to manually update — see CHANGELOG.md.');
    console.log('');
    return;
  }

  // A project several versions behind used to need one `sdd upgrade`
  // invocation per pending migration. With more than one pending, decide
  // once whether to apply the whole chain now or step through it --
  // explicit flags win; otherwise ask interactively; a script/CI
  // invocation (no real TTY on stdin) defaults to applying everything
  // now rather than silently doing only one hop and needing N reruns.
  let applyAll = true;
  if (pending.length > 1 && !opts.toLatest && !opts.step) {
    if (opts.yes) {
      applyAll = true;
    } else if (_stdinIsInteractive()) {
      const { choice } = await inquirer.prompt([{
        type: 'select',
        name: 'choice',
        message: `You're ${pending.length} versions behind (latest is v${SDD_VERSION}). How would you like to upgrade?`,
        choices: [
          { name: `Jump straight to v${SDD_VERSION} (apply all ${pending.length} migrations now)`, value: true },
          { name: 'Step through one at a time (review each migration\'s notes before continuing)', value: false },
        ],
      }]);
      applyAll = choice;
    }
    // else: non-interactive with neither flag nor --yes -- applyAll
    // stays true (see comment above).
  } else if (opts.step) {
    applyAll = false;
  }

  const toApply = applyAll ? pending : pending.slice(0, 1);
  if (pending.length > 1) {
    console.log(chalk.dim(`  ${pending.length} migrations pending -- ${applyAll ? 'applying all now' : 'applying next hop only'}.`));
    console.log('');
  }

  for (const migration of toApply) {
    console.log(chalk.bold(`  Migrating → v${migration.to}: ${migration.description}`));
    for (const note of migration.notes) {
      console.log(`    ${chalk.dim('•')} ${note}`);
    }
    console.log('');

    // Apply migration
    let m = readManifest();
    m = migrateFn(migration.to)(m);
    patchManifest({ sdd_version: m.sdd_version }, MANIFEST_PATH);
    console.log(`  ${chalk.green('✓')}  ${MANIFEST_PATH} updated to v${migration.to}`);
    console.log('');
  }

  const finalVersion = readManifest()?.sdd_version;
  if (finalVersion !== SDD_VERSION) {
    console.log(chalk.yellow(`  Now at v${finalVersion} — run sdd upgrade again to continue to v${SDD_VERSION}.`));
    console.log('');
  }

  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log(`  ${chalk.bold.green('Upgrade complete!')}  Review the changes above and`);
  console.log('  update any prompt files that reference old command names.');
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log('');
}
