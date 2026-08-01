import { existsSync } from 'fs';
import chalk from 'chalk';
import { readManifest, patchManifest, MANIFEST_PATH, SDD_VERSION } from '../utils/manifest.js';

// Version migration table — describes what changed between pack versions.
// Extend this when releasing a new pack version.
// Each migrate() stamps its own "to" version so chained upgrades stay truthful.
const MIGRATIONS = [
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
    migrate: (manifest) => {
      // Add sdd_version if missing — no other structural changes needed
      manifest.sdd_version = '2.0.0';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.0';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.1';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.3';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.4';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.5';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.6';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.7';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.8';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.9';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.10';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.11';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.12';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.13';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.14';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.15';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.16';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.17';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.18';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.19';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.20';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.21';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.22';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.23';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.24';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.25';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.26';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.27';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.28';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.29';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.30';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.31';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.32';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.33';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.34';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.35';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.36';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.37';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.38';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.39';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.40';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.41';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.42';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.43';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.44';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.45';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.46';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.47';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.48';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.49';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.50';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.51';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.52';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.53';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.54';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.55';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.56';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.57';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.58';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.59';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.60';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.61';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.62';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.63';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.64';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.65';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.66';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.67';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.68';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.69';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.70';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.71';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.72';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.73';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.74';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.75';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.76';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.77';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.78';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.79';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.80';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.81';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.82';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.83';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.84';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.85';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.86';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.87';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.88';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.89';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.90';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.91';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.92';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.93';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.94';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.95';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.96';
      return manifest;
    },
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
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.97';
      return manifest;
    },
  },
];

export async function upgradeCommand() {
  console.log('');
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log(`  ${chalk.bold.cyan('SDD Framework')} — upgrade`);
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log('');

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

  // Find applicable migrations
  const pending = MIGRATIONS.filter(m => {
    if (currentVersion === null && m.from === null) return true;
    return m.from === currentVersion;
  });

  if (pending.length === 0) {
    console.log(chalk.yellow('  No migration path found for your current version.'));
    console.log('  You may need to manually update — see CHANGELOG.md.');
    console.log('');
    return;
  }

  for (const migration of pending) {
    console.log(chalk.bold(`  Migrating → v${migration.to}: ${migration.description}`));
    for (const note of migration.notes) {
      console.log(`    ${chalk.dim('•')} ${note}`);
    }
    console.log('');

    // Apply migration
    let m = readManifest();
    m = migration.migrate(m);
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
