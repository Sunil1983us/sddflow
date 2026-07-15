from pathlib import Path
import click
from rich.console import Console

from sdd.utils.manifest import read_manifest, patch_manifest, MANIFEST_PATH, SDD_VERSION
from sdd.utils.scaffold import ALL_PACKS, TYPE_TO_PACK, UNIVERSAL_PACK, sync_pack_prompts

console = Console()

# Version migration table — extend when releasing a new pack version.
# Each migrate() stamps its own "to" version so chained upgrades stay truthful.
MIGRATIONS = [
    {
        "from":        None,       # None = pre-versioning (no sdd_version field)
        "to":          "2.0.0",
        "description": "Initial versioned release",
        "notes": [
            "Added sdd_version field to manifest.yml for upgrade tracking",
            "setup.sh/setup.ps1 rewritten — eliminates injection bugs",
            "Input validation: project/feature names with \" are rejected early",
            "Detection order fix: mobile (react-native) now checked before fullstack",
            "Python CLI added alongside Node.js CLI (pip install sddflow)",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.0.0"},
    },
    {
        "from":        "2.0.0",
        "to":          "2.7.0",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "/change command: type-aware change requests at any SDLC stage",
            "/jira-push: progressive Jira export (Epic/Story/Task/CHG)",
            "Review gates: three modes (chat / local / jira) — Jira now optional",
            "sdd review approve --local also updates the doc's Confluence page",
            "setup.sh/setup.ps1 safe in non-interactive runs (CI, piped input)",
            "Re-copy the pack (or run sdd init over it) to pick up new prompt files",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.0"},
    },
    {
        "from":        "2.7.0",
        "to":          "2.7.1",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "/create-context: Endpoints and NFRs now get a proposed "
            "scope-appropriate starting default, marked "
            "(SUGGESTED DEFAULT — edit or confirm), instead of always "
            "falling back to [MISSING — ask user]",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .github/prompts/create-context.prompt.md",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.1"},
    },
    {
        "from":        "2.7.1",
        "to":          "2.7.3",
        "description": "Version scheme unified — one number instead of two",
        "notes": [
            "sdd_version no longer tracks a separate content/schema "
            "counter — it now always matches the installed sddflow "
            "package version (sdd --version), so this file and the CLI "
            "never show two different numbers again",
            "No framework content changed in this step beyond the "
            "version scheme itself",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.3"},
    },
    {
        "from":        "2.7.3",
        "to":          "2.7.4",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "/change: when a CR fundamentally broadens or narrows what a "
            "feature IS (not just a detail change) — e.g. a fixed "
            "pain.001→pacs.008 converter generalized into a generic ISO "
            "20022 parser — the agent now recommends renaming the "
            "feature slug to match, and will perform the rename "
            "(directory, manifest.yml, context file) if you approve",
            "changeset-template.md: added a 'Feature renamed' row to §1 "
            "Change Description",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .github/prompts/change.prompt.md and "
            "changeset-template.md",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.4"},
    },
    {
        "from":        "2.7.4",
        "to":          "2.7.5",
        "description": "Security fix — no manifest schema changes",
        "notes": [
            "sdd confluence / sdd cr / sdd jira now validate the feature "
            "name against path traversal before touching disk, matching "
            "sdd pr / sdd review, which already did this — previously "
            "a feature name containing '../' sequences (e.g. from a "
            "manifest.yml value not everyone on the project reviewed "
            "carefully) could read or write files outside "
            "'.specify/features/', including pushing arbitrary local "
            "file contents to Confluence/Jira",
            "Also fixed a bypass in the underlying containment check "
            "itself: a feature name resolving to a sibling directory "
            "sharing a string prefix with the base directory (e.g. "
            "'features-legacy' next to 'features') incorrectly passed "
            "validation — it now correctly requires the resolved path "
            "to be inside the base directory, not just prefix-matching",
            "No action needed unless you use --feature or "
            "project.feature values with '../' in them, which was never "
            "valid usage",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.5"},
    },
    {
        "from":        "2.7.5",
        "to":          "2.7.6",
        "description": "Content release — new .specify/service/ directory",
        "notes": [
            "data-model.md, security-design.md, and the API design section "
            "of design.md are now living, service-level documents instead "
            "of being regenerated per feature — they live at "
            "'.specify/service/{doc}.md' and get extended/amended by every "
            "feature after the first one that needs them, instead of each "
            "feature getting its own independent (and eventually "
            "contradictory) copy",
            "docs/runbook/local-setup.md, docs/openapi.yaml, and "
            "docker-compose.yml/k8s manifests now have explicit "
            "check-before-regenerate guidance for the same reason",
            "If you already have per-feature data-model.md/security-design.md "
            "files from before this release, they are NOT automatically "
            "moved or merged — the first time you run /specify-doc "
            "data-model (or security) again, it creates a fresh "
            "'.specify/service/' copy. You'll want to manually reconcile "
            "any existing per-feature versions into that one file yourself",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .github/prompts/specify-doc.prompt.md and "
            "plan-design.prompt.md",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.6"},
    },
    {
        "from":        "2.7.6",
        "to":          "2.7.7",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "Constitution Part 2 gains a 'Service NFR Baseline' table — "
            "the first feature to reach /specify-srd fills it from its "
            "own NFR-NNN rows; every later feature's srd.md references it "
            "instead of restating the same performance/availability "
            "numbers, and only gives its own NFR-NNN row to something "
            "genuinely different from the baseline",
            "/specify-uc: an actor already defined in another feature's "
            "use-cases.md (same real-world role) is now reused, not "
            "re-derived — numbering stays local per file, only the "
            "description content carries over",
            "/plan-design, /plan-arch, /plan-hld: architecture pattern, "
            "system layers, cross-cutting concerns, and the System "
            "Context/Container diagrams are established once by the "
            "first feature and referenced ('unchanged from {feature}, "
            "see there') by every later feature instead of being "
            "re-derived every time",
            "tasks.md Phase A (scaffold/dependencies) gained the same "
            "check-before-regenerate guidance Phase F already had",
            "release.md's Deployment Plan and Post-Deploy Smoke Test now "
            "point at docs/runbook/local-setup.md for the standard "
            "steps instead of re-deriving the strategy each release",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated prompt files",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.7"},
    },
    {
        "from":        "2.7.7",
        "to":          "2.7.8",
        "description": "Content release — per-pack consistency fixes, no manifest schema changes",
        "notes": [
            "Fixed: frontend-spa/mobile design.md §3 now names "
            "api-spec-template.md explicitly for the consumer-view "
            "branch — it existed but was never referenced by any prompt",
            "Fixed: CLAUDE.md Scope Reference table's API Spec row split "
            "into provider (living, .specify/service/api-spec.md) vs "
            "consumer (per-feature, design.md §3) — the single "
            "unconditional row contradicted frontend-spa/mobile's own "
            "consumer-view carve-out",
            "Fixed: release-template.md in frontend-spa/mobile/fullstack "
            "said plain \"runbook.md\" — corrected to "
            "docs/runbook/local-setup.md, matching what /implement "
            "actually generates in every pack",
            "Fixed: frontend-spa/mobile CLAUDE.md and HOW-TO-USE.md "
            "marked data-model as \"full only\" — corrected to mvp+, "
            "matching the Scope Reference table and every other pack",
            "Fixed: universal CLAUDE.md/HOW-TO-USE.md referenced a stale "
            "/specify-doc api-spec command — api-spec moved to "
            "/plan-design §3 back in 2.7.6 but universal's docs were "
            "never updated",
            "data-model.md, security-design.md, and api-spec.md now "
            "carry the same living-document banners/framing in "
            "fullstack and universal as they already had in "
            "backend-service — the underlying living-doc mechanism "
            "(specify-doc.prompt.md, plan-design.prompt.md) was already "
            "shared/active in these packs, only the pack-specific "
            "template headers were missing it",
            "Added a 'Service NFR Baseline' table to fullstack (split "
            "Backend/Frontend) and universal constitution.md, wired "
            "into each pack's own specify.prompt.md — same mechanism "
            "backend-service got in 2.7.7",
            "Added an 'App NFR Baseline' table (pack-appropriate "
            "categories — load time/bundle size for frontend-spa; cold "
            "start/offline sync latency for mobile) to frontend-spa/"
            "mobile constitution.md, wired into specify.prompt.md and "
            "the shared specify-srd.prompt.md NFR-baseline-reference "
            "logic (now pack-agnostic wording)",
            "Frontend-spa/mobile's data-model.md (Frontend State & "
            "Storage Model / Local Data & Cache Model) and "
            "security-design.md are now explicitly living/app-level "
            "documents — same mechanism as backend-service's "
            "data-model.md, just describing state/storage and "
            "client-side security instead of a DB schema",
            "New living document for frontend-spa/fullstack: "
            ".specify/service/component-library.md catalogs "
            "shared/reusable components across features — "
            "component-spec.md's \"Shared Components Used\" section "
            "now points here instead of restating each shared "
            "component's full prop/event spec per feature",
            "release.md's Deployment Plan / Post-Deploy Smoke Test in "
            "frontend-spa, mobile, fullstack, and universal now "
            "reference docs/runbook/local-setup.md as the standard, "
            "established-once strategy instead of re-describing it "
            "every release — the same pattern backend-service got in "
            "2.7.7",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated prompt/template files",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.8"},
    },
    {
        "from":        "2.7.8",
        "to":          "2.7.9",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "/create-context gains a Feature Size Check (Step 1.5): "
            "before drafting context.md, it clusters the raw notes by "
            "actor+goal and flags it if 2+ independently-shippable "
            "capabilities were pasted in as one feature (e.g. \"submit "
            "a payment\" + \"view a payments dashboard\")",
            "If a split is found, the agent asks whether to treat it as "
            "one feature or build one slice at a time — on a split, the "
            "chosen slice's raw text continues through drafting as "
            "normal, and every other slice's raw notes are saved to its "
            "own .specify/contexts/{slug}.raw.md so nothing is lost and "
            "it can be picked up later with /create-context",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .github/prompts/create-context.prompt.md",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.9"},
    },
    {
        "from":        "2.7.9",
        "to":          "2.7.10",
        "description": "Bug fix — /change living-document handling, no manifest schema changes",
        "notes": [
            "Fixed: /change's Stage Detection scanned only "
            ".specify/features/{feature}/ for every document, but "
            "context.md (.specify/contexts/) and data-model.md/"
            "security-design.md/api-spec.md/component-library.md "
            "(.specify/service/, living since 2.7.6) never lived there — "
            "a CR could report all four as \"not yet created\" even when "
            "they existed and were approved, hiding the CR's real impact "
            "entirely",
            "Added: cross-feature impact check for living documents — "
            "before /change approves an UPDATE/RERUN to data-model.md/"
            "security-design.md/api-spec.md/component-library.md, it now "
            "checks the Version History to see which feature last "
            "touched the specific unit being changed. If a different "
            "feature than the one raising the CR touched it, the "
            "proposal includes an explicit warning naming that feature "
            "and what to check — advisory, not a hard block",
            "changeset-template.md rows for the three/four living "
            "documents now note their real (.specify/service/) location, "
            "with a new line explaining how to record cross-feature "
            "impact in the walk table",
            "change-rules.md (all 5 packs) documents the same real file "
            "locations and the cross-feature impact rule",
            "Fixed the same stale-path bug in the test harness itself — "
            "packs/_shared/tests/assert-output.sh checked data-model.md/"
            "security-design.md under the feature directory; it now "
            "checks .specify/service/ — this had been silently wrong "
            "since 2.7.6 because the only CI-exercised example runs at "
            "pilot scope, which skips those checks entirely",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .github/prompts/change.prompt.md and "
            "changeset-template.md",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.10"},
    },
    {
        "from":        "2.7.10",
        "to":          "2.7.11",
        "description": "Multi-feature safety fixes for sdd jira push and sdd confluence push, plus /change --feature override, no manifest schema changes",
        "notes": [
            "Fixed: LIVING_SERVICE_DOCS was missing \"component-library\" "
            "(frontend-spa/fullstack's shared component catalog) — "
            "resolve_doc_path() routed it to .specify/features/{feature}/ "
            "instead of the correct .specify/service/, breaking sdd review "
            "and sdd confluence for that one doc type",
            "Fixed: sdd confluence push/draft/pull built a page title from "
            "only {project}, never {feature} — on a multi-feature project, "
            "two features pushing the same per-feature doc type (brd, "
            "use-cases, srd, design, lld, ...) upserted the SAME Confluence "
            "page and silently overwrote each other's content. "
            "_resolve_page_title() now substitutes {feature} into the "
            "title when the page_map template includes that placeholder "
            "(opt-in — existing configs without it see no title change, "
            "so no page gets orphaned), and always strips {feature} for "
            "living/service-level docs, which must stay ONE shared page "
            "regardless of which feature pushed them",
            "Fixed: sdd jira push/sync keyed Story/Task idempotency labels "
            "on sdd:{id} only, not qualified by feature — since STORY-NNN/"
            "TASK-NNN numbering restarts independently per feature (same "
            "as CR-NNN), two features' STORY-001 collided and the second "
            "feature's push silently overwrote the first feature's Jira "
            "issue. Labels are now sdd:{feature}:{id}, matching the "
            "Feature-level label (sdd-feature:{feature}) which was already "
            "feature-safe. One-time migration cost: the first push after "
            "upgrading creates fresh issues under the new label rather "
            "than finding old ones under the old label — nothing is "
            "deleted or overwritten, but pre-upgrade issues should be "
            "manually closed if they're now duplicates",
            "Added: /change --feature {slug} \"description\" — targets a "
            "feature other than manifest.yml's active one for this CR "
            "only, without editing manifest.yml. Errors clearly (lists "
            "the features it actually found) if the named feature doesn't "
            "exist, rather than silently falling back to the manifest "
            "default. Also fixed a related gap this surfaced: the "
            "context.md-rename special handling used to update "
            "manifest.yml's active feature unconditionally on a rename — "
            "now only does so when the renamed feature is the one "
            "manifest.yml already points to, so a --feature-scoped CR "
            "can't silently switch which feature every other command "
            "operates on",
            "Added: optional per-feature token/cost usage logging "
            "(.specify/features/{feature}/token-usage.md) — off by "
            "default, turns on by copying token-pricing.yml.example to "
            "token-pricing.yml. Self-estimated (characters ÷ 4), not "
            "measured — no AI tool this framework supports exposes exact "
            "token introspection",
            "jira-config.yml (legacy Jira integration path, contains "
            "credential placeholders) is now gitignored by default in all "
            "5 packs — it wasn't before, despite its own header comment "
            "saying it should be",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .specify/integrations.yml.example (per-feature "
            "page_map entries now include {feature}) and .gitignore",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.11"},
    },
    {
        "from":        "2.7.11",
        "to":          "2.7.12",
        "description": "Multi-feature safety fix for the progressive Jira export path (/jira-push, jira-push.py), no manifest schema changes",
        "notes": [
            "Fixed: the progressive Jira export mechanism (/specify-brd, "
            "/specify-uc, /specify-srd writing docs/jira/epic.md, "
            "stories-draft.md, stories-refined.md; /jira-push and "
            ".specify/scripts/jira-push.py reading them and writing "
            "docs/jira/keys.yml) lived at one fixed global path, not "
            "scoped per feature like .specify/features/{feature}/ already "
            "is. On a multi-feature project, a second feature's BRD/UC/SRD "
            "approval overwrote the first feature's staged Epic/Story "
            "export files on disk, and pushing the second feature's Epic "
            "overwrote the first feature's locally-tracked Jira key in "
            "keys.yml -- corrupting parent-link lookups for the first "
            "feature's Stories/Tasks the next time it was touched. This is "
            "a more severe version of the same class of bug fixed in "
            "2.7.11 for sdd jira push/sdd confluence push: there, the "
            "Jira issues themselves were protected by title-based "
            "matching in most cases; here, the LOCAL staging files had no "
            "per-feature isolation at all",
            "All docs/jira/ artifacts are now under docs/jira/{feature}/ -- "
            "epic.md, stories-draft.md, stories-refined.md, keys.yml, "
            "stories.md, jira-import.csv -- mirroring "
            ".specify/features/{feature}/. Verified with a direct "
            "load_keys/save_keys round-trip for two features confirming "
            "no cross-feature collision",
            "Re-copy the pack (or run sdd init/sdd upgrade over it) to "
            "pick up the updated .specify/scripts/jira-push.py and the "
            "five .github/prompts/*.prompt.md files that write/read these "
            "paths (specify-brd, specify-uc, specify-srd, task, "
            "jira-push). Any docs/jira/*.md or keys.yml files from before "
            "this upgrade are not migrated automatically -- move them "
            "into docs/jira/{feature}/ manually if you want to keep them.",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.12"},
    },
    {
        "from":        "2.7.12",
        "to":          "2.7.13",
        "description": "New sdd-micro pack for tiny/personal projects; no changes for existing packs' manifest schema",
        "notes": [
            "Added a 6th pack, sdd-micro, for scripts and small personal "
            "projects that don't need the full 11-command SDLC: just "
            "/specify -> [GATE-1] -> /task -> /implement. It intentionally "
            "does not follow PACK-SPEC.md (no BRD/Use Cases/SRD, no "
            "Validate/Analyze/Clarify/Design/Release) and is hand-"
            "maintained rather than wired into packs/_shared/sync-blocks.sh "
            "-- see packs/sdd-micro/CLAUDE.md and WHY-SDD.md",
            "sdd init --pack sdd-micro (or the interactive picker's "
            "'Choose from all packs...' option) now scaffolds it. Its "
            "manifest.yml has no scope/project_type fields, so sdd init "
            "skips those two questions when it detects a micro-shaped "
            "manifest (no scope/project_type keys) -- existing packs' "
            "manifests are unaffected, they always carry both keys",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for the 5 existing packs",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.13"},
    },
    {
        "from":        "2.7.13",
        "to":          "2.7.14",
        "description": "New sdd dashboard command (local status UI); no manifest schema changes",
        "notes": [
            "Added `sdd dashboard`: a local, read-only web UI over "
            ".specify/ -- pipeline progress, task completion, and token "
            "usage per feature. Stdlib-only HTTP server, no new pip "
            "dependency. Unlike `sdd review status`, it needs no Jira/"
            "Confluence configuration -- it reads the `Status:` header "
            "already written into each doc's .md file, which is the "
            "authoritative gate in every review mode (chat/local/jira)",
            "New module sdd/utils/status.py (build_project_status, "
            "build_feature_status) parses per-feature docs, tasks.md "
            "(both the full packs' checkbox format and sdd-micro's "
            "**Status:** field), and token-usage.md running totals -- "
            "pure filesystem reads, no writes, safe to poll",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.14"},
    },
    {
        "from":        "2.7.14",
        "to":          "2.7.15",
        "description": "sdd dashboard gains Jira/Confluence links, LAN sharing, and an in-page doc viewer; no manifest schema changes",
        "notes": [
            "Local, instant links (no network) now show on each pipeline "
            "doc: Jira Epic/Story/Task links from docs/jira/{feature}/"
            "keys.yml, and Confluence page links from "
            ".specify/.confluence-drafts.json, when either exists",
            "New 'Check Jira/Confluence review links' button per feature "
            "queries Jira/Confluence live (via your existing ~/.sdd/"
            "config.yml profile and .specify/integrations.yml) to resolve "
            "the sdd review submit review-gate tickets, which are never "
            "cached locally -- this is on-demand only, never on the "
            "automatic 5s poll",
            "New 'View' button per document reads the raw .md straight "
            "from disk into the page, so you don't have to leave the "
            "browser to check content",
            "New `--host` flag (default 127.0.0.1) -- run with "
            "`--host 0.0.0.0` on a shared devbox so teammates on the same "
            "network can open the dashboard from their own browser; the "
            "CLI now prints a caution and the reachable LAN URL when "
            "bound non-locally. Still one process on one machine, not a "
            "hosted service, and unauthenticated -- only use on a trusted "
            "network",
            "The new /api/doc and /api/review-links endpoints take "
            "feature/doc query params from HTTP requests, not just local "
            "CLI flags -- both are validated against a strict "
            "[A-Za-z0-9_-]+ pattern before touching the filesystem, "
            "closing off path traversal now that --host can make this "
            "network-reachable",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.15"},
    },
    {
        "from":        "2.7.15",
        "to":          "2.7.16",
        "description": "sdd dashboard gains Approve + review comments (syncs to Confluence/Jira); no manifest schema changes",
        "notes": [
            "New 'Approve' button per document flips that doc's Status: "
            "header to Approved and records who/when/why in "
            ".specify/.local-approvals.yml -- the exact same file and "
            "format `sdd review approve --local` already uses, so the "
            "CLI and the dashboard share one audit trail. Mirrors to "
            "Confluence automatically if configured (same as the CLI "
            "command), and posts a best-effort comment to the doc's "
            "review-gate Jira ticket if configured -- neither failing "
            "blocks the local approval",
            "New comment box (new POST /api/comment) saves review "
            "comments locally to .specify/.dashboard-comments.json, "
            "scoped per feature+document (a new store, so this one is "
            "feature-scoped from the start -- unlike .local-approvals.yml, "
            "which stays keyed by bare doc name to match the CLI format "
            "exactly), and best-effort mirrors to Jira the same way",
            "Known limitation carried over from `sdd review approve`/"
            "`review check`: .local-approvals.yml isn't feature-scoped, "
            "so on a multi-feature project approving one feature's "
            "'brd' doesn't distinguish it from another feature's 'brd' "
            "at the review-check layer. Not something this migration "
            "introduces or fixes -- see cli-python/README.md's dashboard "
            "section",
            "Confluence comment posting isn't implemented (only page "
            "content sync on approve) -- ConfluenceClient has no "
            "comment-write method yet",
            "--host 0.0.0.0's printed warning now also covers write "
            "access: anyone reachable on the network can approve "
            "documents and post comments, not just view status",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.16"},
    },
    {
        "from":        "2.7.16",
        "to":          "2.7.17",
        "description": "sdd dashboard/CLI Approve now also fills the doc's own '## Approvals' table, not just the Status: header; no manifest schema changes",
        "notes": [
            "Bug fix: `sdd review approve --local` and the dashboard's "
            "Approve button previously only flipped a doc's `Status:` "
            "header to Approved -- the '## Approvals' table further down "
            "the same file (Role/Status/Date rows) was left showing "
            "'Pending' even after approval, so the header and the "
            "visible table body disagreed",
            "Every 'Pending' row inside the '## Approvals' section is now "
            "flipped to 'Approved' with today's date filled in, scoped to "
            "that section only -- a coincidental 'Pending' cell elsewhere "
            "in the doc is never touched",
            "Self-healing: running approve again on a doc whose header "
            "was already 'Approved' by the old code, but whose table "
            "still says 'Pending', now fixes the table too",
            "Local-mode approval records one approver for the whole "
            "document (not one per RACI row), so a multi-row table (e.g. "
            "design.md's Architect/Tech Lead/Stakeholder rows) has every "
            "row flipped together, matching the document-level Status: "
            "header rather than attributing individual rows to reviewers "
            "the CLI/dashboard were never told about",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.17"},
    },
    {
        "from":        "2.7.17",
        "to":          "2.7.18",
        "description": "Every document-generating command prompt now reminds the agent to log token usage, closing a gap where the instruction only lived in CLAUDE.md; no manifest schema changes",
        "notes": [
            "Bug fix: token usage logging (opt-in via .specify/memory/"
            "token-pricing.yml) was only documented in CLAUDE.md, read "
            "once at session start -- no individual command prompt ever "
            "referenced it, so the agent had to spontaneously recall a "
            "rule from a different, earlier-read file every command. In "
            "practice this made logging unreliable even when "
            "token-pricing.yml existed and was correctly filled in",
            "New shared block token-usage-log-step now appears near the "
            "end of every document-generating command prompt "
            "(/create-context, every /specify-*, /plan-*, /task, "
            "/implement, /release, /change, /checklist, /validate, "
            "/analyze, /clarify) -- a short reminder to check for "
            "token-pricing.yml and log this command's usage right there, "
            "at the point the agent is about to finish and report",
            "This is a prompt-content change, not a code change -- it "
            "makes the existing token-usage-logging behavior (still "
            "documented in full in CLAUDE.md) more likely to actually "
            "run, it doesn't change what gets logged or how",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.18"},
    },
    {
        "from":        "2.7.18",
        "to":          "2.7.19",
        "description": "sdd config init/set-secret can store Jira/Confluence credentials in the OS keychain instead of an env var; no manifest schema changes",
        "notes": [
            "New credential_store option in ~/.sdd/config.yml, alongside "
            "the existing auth_mode: 'keyring' (recommended) stores the "
            "credential via the OS-native secure store (macOS Keychain / "
            "Windows Credential Manager / Linux Secret Service, through "
            "the new keyring dependency); 'env' is the pre-existing "
            "behavior and remains the default for profiles written before "
            "this version",
            "This closes a real usability gap: an env var exported in one "
            "terminal is invisible to an AI coding tool's own subprocess "
            "shell (or any other new shell), which showed up as "
            "'can't connect to Jira/Confluence' even when the token "
            "itself was fine. A keychain-stored credential is readable by "
            "any process on the machine, not scoped to one shell session",
            "sdd config init now asks which storage to use (keychain "
            "recommended by default) and, for keychain, asks for the "
            "secret directly and stores it -- no env var name is written "
            "to config.yml for that profile",
            "New 'sdd config set-secret --profile {name}' command rotates "
            "a keychain-stored credential without re-running the whole "
            "init wizard",
            "Existing env-var profiles are completely unaffected -- "
            "credential_store defaults to 'env' when absent from an "
            "already-written config.yml, and that code path's behavior "
            "is byte-for-byte unchanged",
            "If no keychain backend is available (headless Linux, "
            "minimal containers), config init/set-secret fail with a "
            "clear message suggesting the env var option instead, rather "
            "than a raw traceback",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.19"},
    },
    {
        "from":        "2.7.19",
        "to":          "2.7.20",
        "description": "sdd jira push now matches /jira-push's content (Feature/Epic description, Story/Task Acceptance Criteria) and sdd review submit self-bootstraps that Epic and parents review tickets under it; no manifest schema changes",
        "notes": [
            "sdd jira push previously created the Feature/Epic with a "
            "blank description and dropped Task Acceptance Criteria "
            "entirely, even though the parser already extracted it -- "
            "both the Feature/Epic (from brd.md's Business Objectives) "
            "and every Story/Task description now carry real content, "
            "matching what the progressive /jira-push script already did",
            "sdd review submit now ensures the Feature/Epic exists before "
            "creating a document's review ticket (self-bootstrapping it "
            "from brd.md if `sdd jira push` hasn't run yet) and parents "
            "the review ticket under it, so review tickets and later "
            "dev Story/Task tickets converge on one Epic per feature",
            "Fixed a label collision: review-ticket idempotency labels "
            "were not feature-qualified (sdd-doc:{doc}), so a second "
            "feature's review submission for the same doc key could "
            "silently overwrite the first feature's ticket on a "
            "multi-feature project -- now sdd-doc:{feature}:{doc}, "
            "matching the fix already applied to Story/Task labels. "
            "sdd review check/status/apply and the dashboard's "
            "approve/comment endpoints were updated to look up the same "
            "qualified label, so any review ticket created after "
            "upgrading is found correctly by all of them",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.20"},
    },
    {
        "from":        "2.7.20",
        "to":          "2.7.21",
        "description": "sdd jira push now supports --level (progressive pushes) and --cr (CHG tasks); /jira-push and .specify/scripts/jira-push.py retired in favor of it; no manifest schema changes",
        "notes": [
            "sdd jira push gained --level {epic|story|task|chg|all} (default "
            "all) and --cr CR-NNN, so it can push progressively at each "
            "SDLC gate exactly like the old standalone script did -- Epic "
            "right after BRD approval, Stories after Use Cases/SRD, Tasks "
            "after /task, CHG tasks after /change. A level pushed on its "
            "own finds its parent live via Jira labels (no local cache "
            "needed for correctness), so levels can be pushed in any "
            "order",
            "The /jira-push slash command is now a thin wrapper around "
            "this same CLI command (same config, same behavior) instead "
            "of invoking a separate standalone script -- "
            ".specify/scripts/jira-push.py and "
            ".specify/templates/jira-config-template.yml are removed from "
            "every pack. All Jira/Confluence configuration now lives in "
            "one place: .specify/integrations.yml",
            "docs/jira/{feature}/keys.yml is still written after every "
            "push, as a local human-readable summary -- but it has never "
            "been required reading for correctness on either the old or "
            "new path; it can be deleted or go stale without affecting a "
            "future push",
            "Two new optional custom_fields keys (fr_reference, "
            "moscow_priority) let Story/Task/CHG issues carry those as "
            "separate Jira fields, in addition to the plain-text line "
            "already in every issue's description -- see "
            "integrations.yml.example",
            "If your project still has .specify/jira-config.yml from "
            "before this version: it's no longer read by anything. Your "
            "existing .specify/integrations.yml jira: section (or "
            "'sdd config init') is now the only config sdd jira push and "
            "/jira-push use",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.21"},
    },
    {
        "from":        "2.7.21",
        "to":          "2.7.22",
        "description": "Fix: Markdown tables were flattened into unreadable one-line paragraphs on every Confluence push -- md_to_cf.py now renders GFM pipe tables as real Confluence tables; no manifest schema changes",
        "notes": [
            "md_to_cf.py (the Markdown -> Confluence Storage Format "
            "converter used by every sdd confluence push / sdd review "
            "submit / sdd review approve --local / sdd cr submit call) "
            "had no table support at all -- every '| cell | cell |' row "
            "fell through to the generic paragraph handler and was "
            "joined with spaces onto one line, destroying row/column "
            "structure. This affected every document template in every "
            "pack, since nearly all of them use Markdown tables (BRD "
            "objectives, API endpoint tables, FR/NFR tables, etc.)",
            "GFM pipe tables ('| ... |' header row + '|---|---|' "
            "separator row) are now parsed and rendered as real "
            "<table><tbody><tr><th>/<td></tr></tbody></table> markup, "
            "which Confluence renders natively -- including alignment "
            "markers (:---, :---:, ---:) as text-align styles, and "
            "**bold**/`code`/[links] inside cells",
            "Re-push any already-published Confluence page to pick up "
            "correctly-rendered tables: sdd confluence push --doc {name} "
            "(or --all)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.22"},
    },
    {
        "from":        "2.7.22",
        "to":          "2.7.23",
        "description": "Fix: JiraClient.search() called the Jira Cloud search endpoint Atlassian removed (410 Gone), breaking every sdd review submit / sdd jira push idempotency lookup; no manifest schema changes",
        "notes": [
            "Atlassian deprecated and removed GET /rest/api/3/search "
            "(announced Aug 2024) in favor of POST /rest/api/3/search/jql. "
            "Every call the CLI makes that looks up an existing Jira "
            "issue by label -- find_by_label(), used by sdd review "
            "submit's Epic self-bootstrap, sdd jira push's upsert logic, "
            "and sdd review check/status/apply -- went through the old "
            "endpoint and started failing with 410 Gone once Atlassian's "
            "rollout reached a given Jira Cloud instance",
            "Found via a real sdd review submit failure during "
            "pre-publish testing: the Confluence half succeeded but the "
            "Jira half failed, so the review fell back to chat approval "
            "with no Jira ticket created",
            "JiraClient.search() now POSTs to /rest/api/3/search/jql with "
            "jql/fields/maxResults in the JSON body, matching Atlassian's "
            "documented migration path -- fields are sent as a real JSON "
            "array now, not a comma-joined query-string value",
            "Only the first page of results is fetched (no nextPageToken "
            "follow-up) -- every caller in this codebase is an "
            "idempotency lookup expecting 0-1 matches, well under the "
            "50-result default, so pagination was never needed and still "
            "isn't",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.23"},
    },
    {
        "from":        "2.7.23",
        "to":          "2.7.24",
        "description": "Fix: document review commands never automatically read reviewer comments back and incorporated them -- 9 command prompts across all 5 packs now delegate to the check/apply loop that already existed but was never wired in; no manifest schema changes",
        "notes": [
            "Every document-generating command (specify-brd, specify-uc, "
            "specify-srd, specify-doc, plan-design, plan-arch, plan-hld, "
            "plan-adr, plan-lld) had its own hand-duplicated 'on approval' "
            "step that only triggered on the user literally saying "
            "'approved', and treated any other outcome (NEEDS REVISION, "
            "PENDING) as a plain yes/no confirmation prompt -- it never "
            "read the reviewer's Jira comments back or updated the "
            "document, even though check-review.prompt.md/submit-review."
            "prompt.md already implemented that exact loop correctly as "
            "a separate, manually-invoked command",
            "Found via real end-to-end testing: after leaving comments "
            "on a submitted BRD review ticket, nothing in the /specify-brd "
            "flow ever fetched or acted on them automatically",
            "All 9 prompts now share one 'review-decision-step' block: "
            "trigger on any check-in (not just the word 'approved'), run "
            "sdd review check, and on NEEDS REVISION actually read the "
            "printed comments, edit the document, and run sdd review "
            "apply -- matching what CLAUDE.md's review-gates block "
            "already documented as the intended behavior but no command "
            "actually implemented",
            "Also fixes a real bug in packs/_shared/sync-blocks.sh: a "
            "brand-new shared block with zero existing matches made grep "
            "exit 1, which under `set -e -o pipefail` silently aborted "
            "the whole sync script before the full-file-copy loop ever "
            "ran. Now uses process substitution so a first-time block "
            "with no matches yet doesn't abort the script",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.24"},
    },
    {
        "from":        "2.7.24",
        "to":          "2.7.25",
        "description": "Fix: failed Jira parent-link calls (Story/Task/CHG under Epic, review ticket under Epic) were silently swallowed with no trace -- now print a diagnosable warning; no manifest schema changes",
        "notes": [
            "Every set_parent() call site (Story/Task/CHG under Epic in "
            "`sdd jira push`, and the review ticket under the Epic in "
            "`sdd review submit`) was wrapped in a bare `except Exception: "
            "pass` -- a failed parent link vanished with zero indication, "
            "even though the issue itself was created successfully",
            "Found via real testing: a review ticket and its Epic both "
            "appeared in Jira but were not linked, with no error message "
            "anywhere to explain why -- root cause turned out to be a "
            "company-managed (classic) Jira project, where Story/Task-to-"
            "Epic linking uses the Epic Link custom field, not the "
            "\"parent\" field team-managed projects use",
            "All five call sites now print a warning naming the child/"
            "parent keys, the underlying error, and a pointer to `sdd "
            "config fields --project {key}` to find the right Epic Link "
            "field ID for parent_field in integrations.yml -- still never "
            "blocks the push/submit itself, just makes the failure visible",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.25"},
    },
    {
        "from":        "2.7.25",
        "to":          "2.7.26",
        "description": "Fix: token usage logging was placed after multi-turn approval-wait STOP points in 9 command prompts, so it almost never actually fired -- moved to right after the document is saved; no manifest schema changes",
        "notes": [
            "2.7.18 wired the token-usage-log-step reminder into every "
            "document-generating command, but in 9 of them (specify-brd, "
            "specify-uc, specify-srd, specify-doc, plan-design, plan-arch, "
            "plan-hld, plan-adr, plan-lld) it was placed at the very end "
            "of the file, AFTER the Stakeholder Review and Approval "
            "section -- which contains STOP points that end the current "
            "turn and defer continuation to a much later turn (after the "
            "user says 'done' or 'approved', sometimes several exchanges "
            "later). The document itself was already fully saved and "
            "complete well before that point, but the logging instruction "
            "sat unreachable behind those unrelated approval-wait turns",
            "Found via real testing: token-pricing.yml existed and the "
            "feature was correctly enabled, but token-usage.md was still "
            "never being updated",
            "The token-usage-log-step block now sits immediately after "
            "the document is saved (right before the Stakeholder Review "
            "section begins) in all 9 affected prompts, guaranteeing it "
            "executes in the same turn as the actual generation work -- "
            "regardless of how many turns the subsequent approval flow "
            "takes",
            "task.prompt.md, checklist.prompt.md, implement/release/"
            "validate/analyze/clarify.prompt.md were already correctly "
            "placed (no approval-wait STOP between generation and the "
            "log step) and needed no change. create-context.prompt.md "
            "and change.prompt.md log at their genuine completion point "
            "(after the user's iteration loop finishes) by design -- "
            "those commands aren't finished, and their output isn't "
            "final, until that point, so no change was needed there either",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.26"},
    },
    {
        "from":        "2.7.26",
        "to":          "2.7.27",
        "description": "Fix: token usage logging still didn't fire even after the 2.7.26 placement fix, because agents were relying on a stale in-conversation memory of token-pricing.yml being absent instead of re-checking; token-usage-log-step now says to re-read the file fresh every time; no manifest schema changes",
        "notes": [
            "2.7.26 moved the token-usage-log-step block to right after "
            "the document is saved, fixing the structural/placement bug "
            "-- but real testing showed the symptom persisted: the user "
            "confirmed via `ls -la` that token-pricing.yml demonstrably "
            "existed at the correct path, yet the agent still reported "
            "'No token-pricing.yml, so skipping usage logging' on a "
            "later command in the same conversation",
            "Root cause was neither the opt-in gate nor placement -- it "
            "was the model treating an earlier, in-conversation check "
            "(made before the user created the file) as still valid, "
            "rather than performing a fresh file read on each command",
            "token-usage-log-step.md now explicitly instructs: check "
            "now, with a fresh file read -- not a memory of whether the "
            "file existed earlier in this conversation -- since the user "
            "may have created it mid-session after an earlier command "
            "already found it missing",
            "Hit the same content-precedence sync gotcha documented in "
            "the 2.7.24 notes a second time: editing only "
            "packs/_shared/blocks/token-usage-log-step.md was not "
            "enough, because 13 files under packs/_shared/full/.github/"
            "prompts/ have this block's content embedded directly (full-"
            "file sync always wins over the blocks loop within a single "
            "sync-blocks.sh run) -- had to re-embed the new wording into "
            "all 13 canonical files, not just the block source, for the "
            "fix to actually propagate to any pack",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.27"},
    },
    {
        "from":        "2.7.27",
        "to":          "2.7.28",
        "description": "Fix: sdd dashboard's comment box lost typed text on the 5s auto-poll, and the per-feature grid cramped the Pipeline card's links column; no manifest schema changes",
        "notes": [
            "User-reported via live testing: typing a reviewer name/comment "
            "into the dashboard's inline comment form and pausing for even "
            "a few seconds would wipe the field -- the text 'disappeared'",
            "Root cause: dashboard.py's render() unconditionally replaces "
            "#root's entire innerHTML on every refresh() call, and "
            "setInterval(refresh, 5000) fires that every 5s regardless of "
            "whether the user is mid-keystroke in the comment-by/comment-"
            "text fields -- the freshly-built DOM nodes came back empty "
            "and unfocused",
            "Fixed with two complementary mechanisms: (1) a delegated "
            "'input' listener now mirrors every keystroke into "
            "state.commentDrafts, keyed by feature+doc, and renderComments"
            "Panel() re-hydrates the input/textarea value from that draft "
            "on every render -- this is what actually stops the text from "
            "being lost; (2) render() also captures the focused element "
            "and its selection range before the innerHTML swap and "
            "restores both afterward, so typing feels uninterrupted rather "
            "than just 'recovers after the fact'",
            "Draft is cleared from state once a comment successfully posts",
            "Verified live with a Playwright-driven headless Chromium "
            "session against a real `sdd dashboard` instance: typed text "
            "survived two full 5s poll cycles, focus/caret were restored, "
            "and Post Comment still worked end-to-end and cleared the "
            "draft afterward",
            "Also addressed a layout complaint from the same report -- the "
            "per-feature grid used a flat auto-fit minmax(220px) for all "
            "four cards (Pipeline, Tasks, Token Usage, Jira Export), so "
            "the Pipeline card's Links column (View/Approve/comment-count/"
            "Jira+Confluence pills) got squeezed and visually cut off at "
            "narrow widths. The new .feature-grid class widens the "
            "breakpoint to minmax(320px) and makes the Pipeline card span "
            "the full row via grid-column: 1 / -1; .links-cell now wraps "
            "with flex-wrap instead of forcing nowrap. Verified with "
            "screenshots at 1200px and 900px viewport widths",
            "3 new regression tests in test_dashboard.py guard the fix at "
            "the source level (commentDrafts wiring, focus-restore, draft-"
            "clear-on-submit) so a future edit can't silently drop it "
            "without a test noticing, without adding a browser-automation "
            "dependency to CI",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.28"},
    },
    {
        "from":        "2.7.28",
        "to":          "2.7.29",
        "description": "Feature: sdd dashboard gains a Full Pipeline section per feature -- the complete command sequence for this scope/plan mode, current step, and a plain-language next-action sentence; no manifest schema changes",
        "notes": [
            "User-requested: the dashboard's old Pipeline card only listed "
            "docs that already exist on disk, giving no sense of how much "
            "of the whole workflow remains or what command to run next -- "
            "review gates weren't represented either (an existing-but-"
            "unapproved doc looked the same as a fully approved one)",
            "New status.py functions -- _standard_pipeline_steps() (the "
            "~20-step flow shared by backend/frontend-spa/mobile/fullstack/"
            "universal, per each pack's own CLAUDE.md header), "
            "_micro_pipeline_steps() (sdd-micro's 3-command flow, selected "
            "when manifest.yml has no project.scope field), and "
            "build_pipeline() -- resolve the full step list against what's "
            "actually on disk (doc Status: headers, tasks.md progress, "
            "constitution/GATE-1 state) into done/current/upcoming/skipped "
            "per step, plus a single next_action sentence",
            "Every step this scope/plan_mode would ever skip is still "
            "shown, struck through, with a hover tooltip explaining why "
            "(e.g. 'skipped -- pilot scope', 'skipped -- unified plan "
            "mode') -- mirrors CLAUDE.md's Scope Reference table exactly, "
            "so the dashboard doesn't just omit steps and leave the user "
            "guessing why LLD or ADR never showed up",
            "'current' doubles as the review-gate signal: a doc that "
            "exists but whose Status: header isn't yet Approved shows as "
            "current (awaiting review), not done -- so approving a doc is "
            "what visibly advances the stepper, not just generating it",
            "dashboard.py: new .pipeline-flow stepper UI (renderPipelineFlow, "
            "renderPipelineStep) plus a highlighted next-action box; the "
            "old doc-list card is renamed Pipeline -> Documents to avoid "
            "clashing with the new Full Pipeline card, which takes the "
            "full-width card-wide slot instead",
            "12 new status.py tests (build_pipeline across scope x "
            "plan_mode combinations, gate1/review-gate/task-progress "
            "transitions, sdd-micro's 3-step flow) plus 2 new dashboard.py "
            "source guards; verified live with a Playwright-driven "
            "headless Chromium session and screenshots across two "
            "features at different pipeline positions",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.29"},
    },
    {
        "from":        "2.7.29",
        "to":          "2.7.30",
        "description": "Feature: sdd upgrade --sync-prompts -- re-copies .github/prompts/ and .claude/commands/ from the current pack into an already-scaffolded project, since plain `sdd upgrade` only ever patches manifest.yml's sdd_version and never touches prompt file content; sdd init now also records a new `pack` manifest field",
        "notes": [
            "Root cause of a real user-reported confusion: after several "
            "prompt-content fixes shipped in 2.7.24/2.7.26/2.7.27 (review-"
            "decision-step wiring, token-usage-log-step placement and "
            "stale-context wording), the user upgraded the sddflow package "
            "and still saw the old, unfixed behavior in their existing "
            "test project -- because sdd init copies .github/prompts/ and "
            ".claude/commands/ into a project exactly once, at scaffold "
            "time, and sdd upgrade has never re-synced them",
            "New sdd/utils/scaffold.py:sync_pack_prompts() diffs each file "
            "in those two directories against the installed pack's "
            "current version; unchanged files are left alone, changed "
            "files are backed up to .specify/.prompt-sync-backups/"
            "{timestamp}/ before being overwritten (so a project with "
            "hand-edited prompts never silently loses those edits), and "
            "missing files are added",
            "sdd upgrade --sync-prompts shows a preview (updated/added/"
            "unchanged counts and filenames) and asks for confirmation "
            "before writing anything, unless --yes is passed; runs even "
            "when the project is already at the current sdd_version, "
            "since that check and this one are orthogonal",
            "Which pack to sync from is resolved via --pack flag > "
            "manifest.yml's new 'pack' field (written by sdd init on "
            "every new project going forward) > inferred from "
            "project_type > sdd-universal as a last resort -- an inferred "
            "guess is always labeled as such in the output, since "
            "projects scaffolded before this release have no 'pack' field "
            "recorded and the guess could be wrong (e.g. someone who used "
            "sdd-universal for a backend-service-typed project)",
            "26 new tests (7 in test_scaffold.py for sync_pack_prompts "
            "itself -- add/update/unchanged/backup/dry-run/out-of-scope-"
            "dirs-untouched/unknown-pack; 19 in test_upgrade.py for pack "
            "resolution and the CLI flag's preview/confirm/cancel/--yes/"
            "already-current-version paths); also verified live end-to-"
            "end against the real bundled packs (sdd init, hand-stale a "
            "prompt file, sdd upgrade --sync-prompts, confirm/cancel both "
            "paths, re-run to confirm idempotency)",
            "New manifest.yml field: 'pack' (string, e.g. "
            "'sdd-backend-service') -- written by sdd init only on a "
            "fresh scaffold; this migration does not backfill it onto "
            "existing projects, since sdd upgrade has no reliable way to "
            "know which pack an existing project was scaffolded from "
            "(that's exactly the gap --pack/inference exists to cover)",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.30"},
    },
    {
        "from":        "2.7.30",
        "to":          "2.7.31",
        "description": "Feature: Jira Epic/Story/Task hierarchy overhaul -- Epic now created at /specify (before any spec doc exists), review tickets are Story issues (not Task) parented to the Epic, Confluence + Jira submission happen together immediately (no more 'push a draft, wait for done, then submit' staging step), and specify-uc pushes a draft Story per use case that /task finalizes in place; no manifest schema changes",
        "notes": [
            "User-requested redesign, in four parts, confirmed via explicit "
            "design choices before implementation: (1) Epic/Feature "
            "created right after /specify generates the constitution, "
            "not lazily on first `sdd review submit`; (2) review tickets "
            "(BRD, Use Cases, SRD, Design/Arch/HLD/ADR, LLD, Tasks, "
            "Runbook, Release) are now issue type Story, not Task, so "
            "they sit at the same hierarchy level as dev Stories under "
            "the Epic -- Epic -> Story -> Task throughout, review tickets "
            "included; (3) `sdd review submit` (Confluence push + Jira "
            "Story creation) now runs immediately when a document is "
            "generated, replacing the old two-stage 'push a Confluence-"
            "only draft, wait for the user to say done, then formally "
            "submit to Jira' flow; (4) `sdd jira push --level uc-draft` "
            "(new) creates one lightweight placeholder Story per UC-NNN "
            "right after /specify-uc, which /task later finalizes in "
            "place -- via a new '**Derived from:** UC-NNN' field on "
            "stories that trace 1:1 to a single use case -- instead of "
            "creating a second, separate issue for the same use case",
            "New shared block epic-bootstrap-step.md wired into all 5 "
            "packs' specify.prompt.md (via the blocks sync system, not "
            "full-file sync, since specify.prompt.md differs per pack)",
            "New shared block submit-for-review-step.md replaces the old "
            "duplicated Step A/B Confluence-then-Jira prose in 9 command "
            "prompts (specify-brd/uc/srd/doc, plan-design/arch/hld/adr/"
            "lld) -- 5 of these previously had the two-stage pattern, 4 "
            "(plan-arch/hld/adr/lld) already called `sdd review submit` "
            "directly and were converted to the shared block for "
            "consistency, not because they were broken",
            "review.py: review ticket issuetype changed from "
            "issue_hierarchy.get('task', 'Task') to "
            "issue_hierarchy.get('story', 'Story'); "
            "_link_review_task_to_epic renamed to "
            "_link_review_story_to_epic; review_submit now also records "
            "its Confluence page in the same .confluence-drafts.json "
            "drafts file `sdd confluence draft` uses, so `sdd confluence "
            "pull --doc {doc}` still works after this change even though "
            "the separate draft-push step is gone",
            "jira.py: new _push_uc_draft_stories() function and 'uc-draft' "
            "--level choice (deliberately excluded from --level all, "
            "since it's a one-time bootstrap tied to /specify-uc, not "
            "part of the regular epic -> story -> task progression); "
            "_push_stories() now reuses a UC's idempotency label "
            "(sdd:{feature}:UC-NNN) instead of minting a new "
            "sdd:{feature}:STORY-NNN one when a Story's new derived_uc "
            "field is set, so the SAME Jira issue gets finalized in "
            "place rather than duplicated",
            "sdd_parser.py: new UseCase dataclass + parse_use_cases(); "
            "Story dataclass gained a derived_uc: str | None field, "
            "parsed from a '**Derived from:** UC-NNN' line -- only "
            "present when a story traces 1:1 back to a single use case, "
            "per task.prompt.md's own instruction; omitted otherwise, "
            "falling back to today's STORY-NNN-keyed labeling unchanged",
            "sdd init now writes a new 'pack' field to manifest.yml "
            "(unrelated to this feature directly, carried over from "
            "2.7.30's --sync-prompts work) -- not touched further here",
            "26 new tests across test_jira_push_levels.py (UC draft "
            "creation, re-run idempotency, derived_uc reuse, unchanged "
            "no-derived_uc behavior), test_sdd_parser.py (new file: "
            "derived_uc extraction, parse_use_cases), and "
            "test_review_helpers.py (Confluence drafts-file bookkeeping "
            "on review submit, plus the _link_review_story_to_epic "
            "rename)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.31"},
    },
    {
        "from":        "2.7.31",
        "to":          "2.7.32",
        "description": "Feature: per-issue-type Jira project key overrides -- new integrations.yml jira.project_keys: {level: KEY} block lets an org keep its Epic/Feature in one Jira project and Stories/Tasks (or review tickets, CRs, CHGs) in another; every project-key call site now resolves through JiraConfig.key_for(level) instead of the single project_key field; no manifest schema changes",
        "notes": [
            "User-requested: 'cfg.jira.project_key is only KEY, there are "
            "possible that org can have different project key for type of "
            "ticket ... I have to have configuration as much as possible'",
            "integrations.py: JiraConfig gained project_keys: dict "
            "(default {}) and a key_for(level) method -- returns "
            "project_keys.get(level, project_key); every level not listed "
            "in project_keys silently falls back to the single "
            "project_key, so existing integrations.yml files with no "
            "project_keys: block are unaffected",
            "Valid levels: feature (the Epic/Feature created at "
            "/specify), story (dev Stories + UC-draft placeholder "
            "Stories), task (dev Tasks), review (the review-gate Story "
            "each `sdd review submit` creates), chg (CHG-NNN "
            "change-request tasks), cr (CR-NNN change-request review "
            "tasks from `sdd cr submit`)",
            "jira.py, review.py, cr.py, pr.py, dashboard.py: every "
            "cfg.jira.project_key / jira_cfg.project_key call site that "
            "picks a project for a create/find-by-label call converted "
            "to cfg.jira.key_for(<level>); _find_story_key's signature "
            "changed from (client, project_key, feature_name, story_id) "
            "to (client, project_key, feature_name, story) -- it now "
            "checks the UC-derived label before falling back to the "
            "STORY-NNN label, fixing a latent bug where a UC-derived "
            "story's real key could be missed entirely when --level task "
            "ran in a separate invocation from --level story",
            "sdd jira push's status header now prints any configured "
            "project_keys overrides plus a standing warning when any are "
            "set",
            "IMPORTANT CAVEAT (documented in integrations.yml.example "
            "and README.md, not a bug): Jira's parent/Epic-Link field "
            "generally does not support linking issues across different "
            "Jira projects on the standard REST API this CLI uses -- "
            "true cross-project hierarchy needs Advanced Roadmaps (Jira "
            "Premium). If project_keys puts a child level in a different "
            "project than its parent level, the child issue is still "
            "created but the parent link may silently fail to appear in "
            "Jira. This was already covered by the existing "
            "_warn_parent_link_failed() safety net (prints 'was not "
            "linked under ...' rather than swallowing the error), which "
            "this feature relies on rather than duplicating",
            "7 new tests: 2 in test_config_and_integrations.py (key_for "
            "default-empty-dict and override-specific-levels), 5 across "
            "test_jira_push_levels.py (TestProjectKeysOverride -- epic/"
            "story/task/uc-draft create + parent-lookup calls all use "
            "their level's override) and test_review_helpers.py "
            "(_ensure_epic under a feature override; failed-link warning "
            "names the review-level override, not the base project_key)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.32"},
    },
    {
        "from":        "2.7.32",
        "to":          "2.7.33",
        "description": "Feature: per-level custom field ID overrides + fixed team field -- new integrations.yml jira.custom_fields_by_level: {level: {field: id}} block overrides the common custom_fields mapping per level, and base_fields.team + custom_fields.team stamps a fixed team name/ID on every issue created; no manifest schema changes",
        "notes": [
            "User-requested follow-on to 2.7.32's project_keys: 'They "
            "need to have team name, story point, acceptance criteria, "
            "and they can have some customer field also .. can it send "
            "the field as per the configuration .. they have have "
            "project specific or common'",
            "Motivation: if project_keys (2.7.32) puts a level's issues "
            "in a different Jira project than another level's, that "
            "project almost always has different custom field IDs too "
            "-- not just a different project key -- so a single common "
            "custom_fields mapping would silently write to the wrong "
            "(or a nonexistent) field ID on that project",
            "integrations.py: JiraConfig gained custom_fields_by_level: "
            "dict (default {}) and a fields_for(level) method -- merges "
            "custom_fields_by_level.get(level, {}) over the common "
            "custom_fields dict, override wins per-key, mirroring "
            "key_for()'s fallback semantics; every project with no "
            "custom_fields_by_level entries behaves exactly as before",
            "JiraConfig also gained team: str | None (parsed from "
            "base_fields.team) -- a single fixed value (e.g. 'Team "
            "Phoenix'), the same on every issue, not something that "
            "varies per story/task; confirmed explicitly by the user as "
            "the intended semantics before implementation",
            "jira.py: every custom-field call site (feature_extra_fields, "
            "_push_stories, _push_tasks, _push_chg, "
            "_push_uc_draft_stories) now reads cfg.fields_for(level) "
            "instead of cfg.custom_fields directly; new "
            "_apply_team_field() helper stamps cfg.team via "
            "fields_for(level)['team'] on every issue type when both are "
            "configured, no-ops otherwise",
            "8 new tests: 4 in test_config_and_integrations.py "
            "(fields_for default/override, team default/parsed), 4 in "
            "test_jira_push_levels.py (TestCustomFieldsAndTeam -- "
            "per-level custom field override doesn't leak to other "
            "levels, team stamped on Epic/Story/Task/UC-draft/CHG, team "
            "never sent when cfg.team is unset even if the field ID is "
            "configured)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.33"},
    },
    {
        "from":        "2.7.33",
        "to":          "2.7.34",
        "description": "Fix: sdd review submit / sdd cr submit were silently skipping base_fields.labels and the team stamp that every other issue type gets; add jira.parent_field_by_level per-level override, same pattern as project_keys/custom_fields_by_level; no manifest schema changes",
        "notes": [
            "User-requested field audit ('Can you check all fields while "
            "sending to api for jira?') surfaced two real gaps, not just "
            "documentation drift: review.py's review_submit() and cr.py's "
            "cr_submit() hand-build their Jira `fields` dict directly "
            "rather than routing through jira.py's _upsert_issue() (the "
            "function every Epic/Story/Task/CHG issue goes through) -- "
            "both had silently dropped cfg.jira.labels (base_fields.labels, "
            "e.g. the default 'sdd-generated' label) and never applied "
            "base_fields.team, even when configured",
            "Fix: review_submit's fields['labels'] is now "
            "cfg.jira.labels + ['sdd-review', idempotency_label] (was: "
            "hardcoded to just the latter two); cr_submit's is now "
            "cfg.jira.labels + ['sdd-cr', idempotency_label]; both now "
            "call jira.py's _apply_team_field() helper so a configured "
            "team is stamped on review/CR tickets exactly like it already "
            "was on Epic/Story/Task/CHG issues. No other custom_fields "
            "entries (story_points/acceptance_criteria/etc.) are applied "
            "to review/CR tickets -- those have no meaning on a review "
            "ticket, this was a deliberate scope decision, not an "
            "oversight",
            "New JiraConfig.parent_field_by_level: dict + "
            "parent_field_for(level) method, exact same fallback pattern "
            "as key_for()/fields_for() from 2.7.32/2.7.33 -- lets an org "
            "whose Story/Task Jira project (via project_keys) needs a "
            "different parenting mechanism than the Epic's project (e.g. "
            "one is next-gen and uses the 'parent' system field, the "
            "other is classic company-managed and needs the Epic Link "
            "custom field) express that per level. All 5 set_parent() "
            "call sites (Story/UC-draft-Story/Task/CHG under their "
            "parent in jira.py, review Story under Epic in review.py) "
            "now resolve through parent_field_for(level) instead of the "
            "single parent_field",
            "10 new tests: 2 in test_config_and_integrations.py "
            "(parent_field_for default/override), 5 in "
            "test_jira_push_levels.py (TestParentFieldOverride -- each "
            "set_parent() call site honors its own level's override), "
            "2 in test_review_helpers.py (parent_field_for override on "
            "the review-Epic link, plus a full review_submit() "
            "end-to-end test confirming labels/team now reach the "
            "created Story -- not just the extracted helper functions), "
            "and a new test_cr.py (cr_submit() end-to-end, same "
            "assertion for CR review tasks)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.34"},
    },
    {
        "from":        "2.7.34",
        "to":          "2.7.35",
        "description": "Feature: Confluence page hierarchy (Project -> Feature -> doc pages), created automatically and idempotently -- fix: document_reviews.confluence_page titles never had {feature} substituted, only {project}, so two features submitting the same doc type silently overwrote each other's Confluence page; no manifest schema changes",
        "notes": [
            "User-requested: 'can we have created under sub pages .. create "
            "a project page, under feature page and different steps pages "
            "under feature?' -- every page now nests under parent_page_id "
            "-> a Project container page -> a Feature container page, both "
            "created idempotently the first time any doc is pushed for "
            "that project/feature. Living/service-level docs (data-model, "
            "security-design, api-spec, component-library, runbook) nest "
            "directly under the Project page instead, since they're "
            "shared across every feature",
            "IMPORTANT CAVEAT verified before implementing (Confluence "
            "enforces page-title uniqueness per SPACE, not per parent "
            "page -- confirmed via Atlassian community docs): nesting is "
            "purely a navigation convenience, it does NOT relax the need "
            "for {feature} in the page title text. Two features' "
            "same-titled pages would still collide even nested under "
            "different Feature pages. This is why page_map/"
            "document_reviews.confluence_page templates keep {feature} in "
            "the title -- confirmed with the user before implementing, "
            "since an earlier 'simplify titles now that nesting exists' "
            "framing would have silently reintroduced the exact collision "
            "bug fixed in 2.7.x's earlier 'Fix Confluence page-title "
            "collision across features' work",
            "REAL BUG FOUND AND FIXED: document_reviews.confluence_page "
            "(used by sdd review submit/_push_doc_page, separate from "
            "page_map used by sdd confluence push/draft) only ever had "
            "{project} substituted in its title -- {feature} was never "
            "substituted at all, in any of the 3 call sites (review_submit, "
            "_push_doc_page, review_apply). Two features submitting the "
            "same doc type (e.g. both push a BRD for review) would upsert "
            "the SAME Confluence page, silently overwriting each other's "
            "content -- the exact collision class already fixed for "
            "page_map, just never applied to document_reviews.confluence_page. "
            "All 3 call sites now do .replace('{feature}', feature_name) "
            "in addition to .replace('{project}', project_name)",
            "confluence.py: new _ensure_container_page() (idempotent "
            "find-by-title-in-space, else create), resolve_feature_parent_id() "
            "(Project -> Feature chain), resolve_doc_parent_id() (routes "
            "living/service-level docs to the Project page instead of a "
            "Feature page); wired into confluence_push, confluence_draft, "
            "review.py's review_submit/_push_doc_page/review_apply, and "
            "cr.py's cr_submit (which also dropped {project} from its CR "
            "page title in favor of {feature}, matching the new "
            "'feature-first' title convention)",
            "_push_doc_page() signature changed: now takes feature_name "
            "as a required third argument (previously computed nothing "
            "about feature at all) -- callers in review.py's review_approve "
            "and dashboard.py's approve endpoint updated to resolve and "
            "pass it",
            "_CONTEXT_PAGE_TITLE changed from '{project} — Context: "
            "{feature}' to '{feature} — Context', matching the new "
            "feature-first convention applied to page_map/"
            "document_reviews.confluence_page in the shipped example",
            "9 new tests: 8 in new test_confluence_hierarchy.py "
            "(_ensure_container_page idempotency, resolve_feature_parent_id "
            "Project->Feature chain and sharing across features, "
            "resolve_doc_parent_id living-doc vs per-feature routing), 1 "
            "regression test in test_review_helpers.py proving two "
            "features no longer collide on the same review Confluence "
            "page, plus fixes to 2 pre-existing tests whose expectations "
            "matched the old title format",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.35"},
    },
    {
        "from":        "2.7.35",
        "to":          "2.7.36",
        "description": "Feature: Confluence diagram-macro rendering modes (mermaid-app, plantuml-macro) -- new confluence.diagrams: config block routes ```mermaid/```plantuml fences through an installed Confluence app's macro instead of the plain code-block rendering; no manifest schema changes",
        "notes": [
            "User-reported: Mermaid diagrams pushed to Confluence only "
            "ever showed as plain code text, never as a rendered "
            "diagram -- root cause is that md_to_cf.py routed every "
            "fenced code block, regardless of language, through "
            "Confluence's built-in 'code' macro (a syntax-highlighted "
            "text block), and Confluence has no native diagram renderer "
            "at all",
            "Researched (with web search) and ruled out several "
            "approaches before implementing: Confluence's native "
            "paste-markdown editor feature does not render Mermaid; "
            "whole-document 'Markdown macro' apps and Mermaid-specific "
            "apps both exist on the Atlassian Marketplace but are "
            "org-installation-dependent; PlantUML apps require a "
            "different diagram language (not mechanically convertible "
            "from Mermaid) and by default call out to the public "
            "plantuml.com server unless self-hosted",
            "Shipped this round: new integrations.py DiagramsConfig "
            "dataclass (ConfluenceConfig.diagrams field) supporting "
            "mode: none (default, unchanged behavior) | mermaid-app | "
            "plantuml-macro, each with a configurable macro_name (the "
            "ac:name of whatever Confluence app the org has installed)",
            "md_to_cf.py: new _render_fence()/_diagram_macro() helpers -- "
            "a ```mermaid fence routes through mermaid_app.macro_name "
            "when mode == mermaid-app; a ```plantuml fence routes "
            "through plantuml_macro.macro_name when mode == "
            "plantuml-macro; every other fence (and a diagram fence "
            "with no matching mode/macro configured) falls back to the "
            "existing code-macro rendering, never crashes or emits a "
            "broken macro reference for a misconfiguration",
            "md_to_storage()'s signature gained an optional second "
            "parameter (diagrams: DiagramsConfig | None = None, "
            "defaulting to mode 'none') -- all 6 call sites across "
            "confluence.py, review.py, and cr.py updated to pass "
            "cfg.confluence.diagrams through",
            "Two more modes -- local-svg (render Mermaid to SVG "
            "locally, no external network call, then attach as an "
            "image) and markdown-macro (delegate the whole page to a "
            "whole-document Markdown-rendering Forge app) -- were "
            "explicitly deferred, not implemented: local-svg needs a "
            "rendering-tool evaluation spike first (which Python-native "
            "renderer actually covers the diagram types SDD templates "
            "generate), and markdown-macro's Forge-based macro "
            "reference shape (ac:adf-node type=\"extension\" with a "
            "dynamically-obtained local-id, confirmed via research, not "
            "the same simple ac:structured-macro ac:name=\"...\" shape "
            "the other two modes use) needs verified testing against a "
            "real installed app before shipping, to avoid producing a "
            "broken macro island in Confluence",
            "7 new tests in test_md_to_cf.py (TestDiagramMacros) -- "
            "default behavior unchanged, correct macro emitted per "
            "mode, safe fallback when misconfigured, diagram fences of "
            "the wrong mode/language left alone, CDATA escaping",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.36"},
    },
    {
        "from":        "2.7.36",
        "to":          "2.7.37",
        "description": "Feature: Confluence local-svg diagram mode -- ```mermaid fences can now be rendered to SVG entirely offline (no browser, no Node.js, no network call, no Confluence app) and attached to the page as an image; no manifest schema changes",
        "notes": [
            "Completes the local-svg mode explicitly deferred in "
            "2.7.36's migration notes -- that release shipped "
            "mermaid-app/plantuml-macro (both require an installed "
            "Confluence app); this release adds the offline option for "
            "orgs that don't have or can't install one",
            "Renderer choice was verified, not assumed: built an "
            "isolated venv, confirmed two PyPI candidates actually "
            "exist, extracted the real Mermaid diagram types SDD "
            "templates generate (flowchart, sequenceDiagram, "
            "classDiagram, erDiagram), and rendered each type through "
            "each candidate. mermaidx/mmdc (JS-engine backend) failed "
            "on flowchart stadium-shape nodes (Actor([\"User\"]), used "
            "in every design/hld/arch template's Actor node) and on "
            "classDiagram entirely. mmdr (Rust-based, ~18MB, zero "
            "further Python dependencies) rendered all four correctly, "
            "confirmed both textually and via visual PNG inspection",
            "mmdr is an optional dependency, not a hard one -- new "
            "[project.optional-dependencies].diagrams extra in "
            "pyproject.toml, installed with pip install "
            "\"sddflow[diagrams]\", imported lazily only when "
            "diagrams.mode == local-svg is actually configured",
            "New sdd/utils/mermaid_render.py wraps mmdr.render(...).svg() "
            "and raises a clear MermaidRendererNotInstalled error naming "
            "the exact install command if configured but missing, "
            "instead of a bare ImportError traceback",
            "New ConfluenceClient.upload_attachment() posts to "
            "/content/{id}/child/attachment with the X-Atlassian-Token: "
            "nocheck header multipart uploads require to bypass XSRF "
            "protection -- Confluence auto-versions an existing "
            "attachment with the same filename, so no separate update "
            "path is needed",
            "md_to_storage()'s return type changed from str to "
            "tuple[str, list[Attachment]] -- attachments is always [] "
            "except in local-svg mode, where each successfully-rendered "
            "```mermaid fence contributes one (filename, svg_bytes, "
            "media_type) entry the caller uploads after upsert_page(); "
            "all 6 call sites across confluence.py, review.py, and "
            "cr.py updated to unpack the tuple and call the new shared "
            "upload_diagram_attachments() helper",
            "Every failure mode falls back to something safe rather "
            "than crashing the whole document push: missing dependency "
            "or invalid diagram source -> plain code block for that one "
            "diagram (page push continues); failed attachment upload -> "
            "warning printed, page content (already saved) is "
            "unaffected, remaining attachments still upload",
            "17 new tests across 4 files: test_mermaid_render.py (3), "
            "TestLocalSvgMode in test_md_to_cf.py (5), "
            "test_confluence_client.py (5), TestUploadDiagramAttachments "
            "in test_confluence_hierarchy.py (4)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.37"},
    },
    {
        "from":        "2.7.37",
        "to":          "2.7.38",
        "description": "Feature: Virtual Team persona hints on the sdd dashboard's Full Pipeline stepper -- each step owned by a named team member (Maya, Rex, Ava, Leo, Kai, Quinn, Riley) shows a name badge and a ready-to-type natural-language ask; no manifest schema changes",
        "notes": [
            "User-requested: the dashboard's Full Pipeline stepper showed "
            "only raw slash commands (e.g. 'Run /plan-design to generate "
            "the Design') -- no link back to the CLAUDE.md 'Virtual Team "
            "— Address by Name' convention already documented and used "
            "throughout every pack, where addressing a team member by "
            "name (e.g. 'Ava, design checkout') works identically to "
            "running the underlying slash command",
            "New _STEP_PERSONA map in status.py maps each pipeline step "
            "id to (persona name, natural-language ask template with a "
            "{feature} placeholder) -- e.g. brd -> (Maya, 'create the BRD "
            "for {feature}'). Steps with no clear single owner are "
            "intentionally absent: /specify and GATE-1 run before any "
            "persona takes over; the runbook is a byproduct of "
            "/implement, not something you ask for directly",
            "build_pipeline() gained a feature: str parameter (interpolated "
            "into each persona's ask) and now attaches a persona dict "
            "(name, role, ask) to every resolved step plus a next_persona "
            "field alongside the existing next_action sentence",
            "sdd-micro has no Virtual Team at all (see its own CLAUDE.md) "
            "-- _persona_hint() returns None unconditionally when scope "
            "is None (the signal build_pipeline already uses to select "
            "sdd-micro's 3-command pipeline over the standard one), so "
            "the hint never appears there",
            "dashboard.py: each pstep badge shows the persona's name "
            "before its label and the full name/role/ask in its hover "
            "tooltip; the Next box gained a second line -- e.g. "
            "'Or just say: \"Maya, write the use cases for checkout\" "
            "(Maya — Business Analyst)' -- rendered only when the next "
            "step has a persona owner",
            "Verified end-to-end against a real temp project through a "
            "running sdd dashboard instance (not just unit tests) -- "
            "confirmed via headless-browser screenshot in both light and "
            "dark mode that the persona badge and Next-box ask line "
            "render correctly",
            "4 new tests in test_status.py covering: next_persona names "
            "the right owner, every step with an owner carries a persona "
            "dict, specify/gate1 have none, sdd-micro never gets a hint",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.38"},
    },
    {
        "from":        "2.7.38",
        "to":          "2.7.39",
        "description": "Feature: extend Virtual Team persona hints to the dashboard's Documents card and sdd review status; fix: awaiting-review docs no longer show a misleading creation-phrased persona ask; no manifest schema changes",
        "notes": [
            "Extends 2.7.38's dashboard Full Pipeline persona hints to the "
            "two other places that guess 'what's next': the dashboard's "
            "Documents card ('Next: Use Cases — or say: \"Maya, write the "
            "use cases for checkout\"') and the terminal-only `sdd review "
            "status` (each non-Approved, non-Blocked row gains a '· ask "
            "{name}' hint using the same Virtual Team roster)",
            "Bug found while extending: build_pipeline's next_persona was "
            "attached even when a step was 'current' because the doc "
            "already exists and is awaiting review, not because it's "
            "about to be created -- every ask template is creation-phrased "
            "('create the BRD for X'), which misleadingly implied the doc "
            "didn't exist yet. Fixed by suppressing next_persona (and the "
            "equivalent field on _current_stage) specifically for that "
            "state; the per-step badge/tooltip is unaffected since it's a "
            "general 'who owns this kind of work' reference, not a "
            "claim about this specific document's current state",
            "New public status.persona_for(step_id, feature, scope) "
            "wrapper lets sdd review status (which reads "
            "document_reviews keys directly, not the pipeline) reuse the "
            "same _STEP_PERSONA lookup without importing a private helper",
            "_current_stage() gained feature/scope parameters (previously "
            "positional-only docs) so it can build the same "
            "{feature}-interpolated ask the pipeline uses",
            "9 new tests: 1 for the awaiting-review suppression fix, 5 for "
            "_current_stage's persona field (fresh project, upcoming doc, "
            "awaiting approval, sdd-micro), 1 for persona_for(), 3 in "
            "test_review_helpers.py for sdd review status's ask hint "
            "(not-submitted, approved-shows-nothing, needs-revision)",
            "Verified end-to-end against a live dashboard instance via "
            "headless-browser screenshot, confirming both the Documents "
            "card's ask line and the awaiting-approval no-ask case render "
            "correctly, not just unit tests",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.39"},
    },
    {
        "from":        "2.7.39",
        "to":          "2.7.40",
        "description": "Fix: review-driven document edits (Jira comment, dashboard comment, or chat feedback) now bump the doc's Version header and log a Version History row -- previously only /change did this, and the approval step's Version History row hardcoded '1.0' instead of the document's actual current version; prompt/template content only, no manifest schema changes",
        "notes": [
            "User-reported: after addressing reviewer comments (via Jira, "
            "local mode, or the dashboard) and updating a document, its "
            "Version header stayed at 1.0 forever with no record of what "
            "changed or when -- unlike /change (post-approval Change "
            "Requests), which already bumps the version and appends a "
            "Version History row for every applied change",
            "Root cause: the shared review-decision-step.md block (embedded "
            "in every review-gated command -- specify-brd, specify-uc, "
            "specify-srd, specify-doc, plan-design/arch/hld/adr/lld) told "
            "the agent to 'edit the document to address the feedback' on "
            "NEEDS REVISION, but never mentioned bumping Version or logging "
            "Version History -- so the discipline /change already has was "
            "simply never applied to the earlier pre-approval review cycle",
            "Second, smaller bug found while fixing the first: the "
            "approval-logging step's Version History row template hardcoded "
            "'| 1.0 | {today} | ... |' literally, instead of referencing "
            "the document's actual current version -- wrong for any doc "
            "past its first revision. Fixed to use '{current version}' in "
            "both review-decision-step.md and validate.prompt.md's own "
            "inline copy of the same approval step",
            "New 'Revision Logging' rule in review-decision-step.md: any "
            "review-driven content edit, regardless of which mode surfaced "
            "the feedback (Jira comment via sdd review check, a dashboard "
            "comment -- which mirrors to the Jira ticket when Jira is "
            "configured -- or feedback relayed in chat), increments the "
            "Version header and appends a Version History row. A pure "
            "approval with no content change does not bump the version",
            "review-gates.md (CLAUDE.md's Document Review Gates summary) "
            "gained a one-line pointer to this rule for discoverability "
            "at session-startup read time, without duplicating the full "
            "step-by-step instructions",
            "Maintenance note for future _shared/ edits: files that are "
            "BOTH full-file-synced AND contain a shared:{id} marker span "
            "(the 9 review-decision-step.md host files) need their marker "
            "content refreshed in _shared/full/ itself too -- the blocks "
            "loop only touches ../sdd-*/ directories, so editing only "
            "blocks/{id}.md leaves _shared/full/'s copy stale, and the "
            "full-file loop that runs after it will silently overwrite the "
            "packs' freshly-substituted content back to that stale copy",
            "Prompt/template content only -- no CLI code changed, no new "
            "tests (nothing here is unit-testable; verified by reading the "
            "synced output in all 5 packs and re-running sync-blocks.sh "
            "twice to confirm convergence, plus the existing pytest suite "
            "and assert-output.sh/test-setup.sh regression suites, none of "
            "which touch prompt file content)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.40"},
    },
    {
        "from":        "2.7.40",
        "to":          "2.7.41",
        "description": "Feature: sdd review check/apply now discover and acknowledge dashboard-left review comments in pure local mode (no jira: configured) -- new sdd review comments command too; no manifest schema changes",
        "notes": [
            "User-reported gap, found while shipping 2.7.40's version-bump "
            "fix: in pure local mode (no jira: section at all), a dashboard "
            "comment landed only in .dashboard-comments.json with no way "
            "for the agent to discover it except the user manually relaying "
            "it in chat -- sdd review check always returned NOT SUBMITTED "
            "in that case, and sdd review apply hard-required both jira: "
            "and confluence: to even run",
            "New sdd/utils/dashboard_comments.py: unacknowledged(feature, "
            "doc) reads .dashboard-comments.json and filters out anything "
            "already handled; acknowledge(feature, doc) records the current "
            "moment in a new .specify/.dashboard-comments-ack.json (an "
            "append-only comments log has no per-entry 'handled' flag, so "
            "acknowledgement is tracked separately as a per-feature/doc "
            "timestamp cutoff)",
            "sdd review check: when no jira: is configured, falls back to "
            "unacknowledged() before giving up with NOT SUBMITTED -- prints "
            "any found in the same shape as the Jira NEEDS_REVISION branch "
            "and exits 1, so the existing review-decision-step.md prompt "
            "instructions ('run sdd review check ... follow exit code') "
            "work unchanged in pure local mode, no prompt edits needed",
            "sdd review apply: when neither jira: nor confluence: is "
            "configured (including no integrations.yml at all), "
            "acknowledges local comments instead of hard-erroring -- the "
            "existing 'then run sdd review apply' prompt instruction now "
            "also works unchanged in pure local mode",
            "New sdd review comments --doc {doc} [--ack] command for "
            "explicit/manual use and discoverability outside the "
            "check/apply cycle -- lists unacknowledged comments (exit "
            "1 if any, 0 if none) or, with --ack, marks them all addressed",
            "When Jira IS configured, dashboard comments already mirror to "
            "the doc's Jira review ticket (existing behavior, unchanged) "
            "-- the new fallback only ever triggers in the jira: absent "
            "branches, so nothing here affects Jira-configured projects",
            "14 new tests: 8 in test_dashboard_comments.py (all_comments, "
            "unacknowledged, acknowledge -- including that acknowledging "
            "doesn't hide comments left afterward), 6 in "
            "test_review_helpers.py (check/apply/comments CLI behavior end "
            "to end via CliRunner, no mocking)",
            "Verified end-to-end against the real sdd CLI (not just pytest "
            "mocks): ran a live sdd dashboard instance, posted a comment "
            "through its actual /api/comment endpoint exactly as the "
            "browser UI would, confirmed sdd review check picked it up "
            "(exit 1, comment text printed), edited the doc, ran sdd "
            "review apply (acknowledged), then confirmed sdd review check "
            "and sdd review comments both correctly stopped reporting it",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.41"},
    },
    {
        "from":        "2.7.41",
        "to":          "2.7.42",
        "description": "Docs consistency (Virtual Team + /taskstoissues in HOW-TO-USE.md, dangling CHANGELOG.md reference removed, workflow_mode wording propagated to frontend-spa/mobile/fullstack) + new test coverage for sdd init, sdd pr, and the dashboard HTTP handler; no manifest schema changes",
        "notes": [
            "Quick-win doc fixes from a full-project audit: removed the "
            "dangling 'CHANGELOG.md' row from the README.md Read Next "
            "table in all 5 packs (no such file is ever scaffolded into a "
            "user's project); added a Virtual Team -- Address by Name "
            "section and a /taskstoissues entry to HOW-TO-USE.md in all 5 "
            "packs (both features already existed and worked, they just "
            "weren't documented in the primary end-user guide)",
            "workflow_mode (github/local) consistency fix: "
            "sdd-frontend-spa, sdd-mobile, and sdd-fullstack already "
            "documented workflow_mode: local as supported in "
            "HOW-TO-USE.md, but CLAUDE.md's PR Contract/VALIDATE-RELEASE "
            "gate text, implement.prompt.md's After Writing branch, "
            "release.prompt.md's Verify Gate, PROMPT-GUIDE.md, the "
            "quality-gate.yml starter-workflow comment, and "
            "constitution.md's PR Rules table never branched on it -- "
            "local mode silently behaved like github mode in those 3 "
            "packs. Propagated the exact pattern already proven in "
            "sdd-universal/sdd-backend-service so all 5 packs now behave "
            "identically",
            "New tests/test_dashboard_http.py (12 tests): real-socket "
            "tests against dashboard.py's _Handler on an ephemeral "
            "localhost port -- GET /, /api/status, /api/doc, "
            "/api/review-links, POST /api/approve, /api/comment, "
            "path-traversal rejection, invalid-JSON-body rejection, and "
            "404s. Complements the existing helper-level tests in "
            "test_dashboard.py, which never exercised do_GET/do_POST "
            "themselves",
            "New tests/test_init.py (6 tests): fill mode (manifest.yml "
            "already exists) with CLI flags supplied, context-file "
            "no-clobber, sdd-micro detection (manifest lacking "
            "project_type/scope), invalid project-name rejection, and "
            "scaffold mode (no manifest.yml yet -- pack gets copied in "
            "first)",
            "New tests/test_pr.py (14 tests): sdd pr create (task lookup, "
            "branch/PR-title/PR-body construction, missing-task and "
            "missing-integrations.yml failures, PrCreateError manual "
            "fallback, --feature override), plus comments/reply/resolve/"
            "request-review (unresolved-comment listing, comment-id "
            "matching, and graceful degradation when a provider raises "
            "ReviewActionError e.g. Bitbucket has no thread-resolution "
            "API). All git-host interaction is mocked at the "
            "detect_host/get_provider boundary -- provider-internal "
            "behavior is already covered by test_git_host.py",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.42"},
    },
    {
        "from":        "2.7.42",
        "to":          "2.7.43",
        "description": "Fix: sdd init no longer re-asks project type after a type-dedicated pack (backend-service/frontend-spa/mobile/fullstack) is chosen -- no manifest schema changes",
        "notes": [
            "User-reported: choosing sdd-backend-service from 'Choose from "
            "all packs...' (when auto-detection failed) still triggered a "
            "second detect_project_type() call right after scaffold_pack "
            "copied that pack's own files in, and then a 'Project type:' "
            "select listing all 10 types including irrelevant ones (mobile, "
            "desktop, ...) for a project the user just said was "
            "sdd-backend-service",
            "New PACK_TO_TYPE reverse map (of scaffold.py's TYPE_TO_PACK) in "
            "init.py -- when the chosen (or, in fill mode, already-recorded "
            "manifest.pack) pack is one of the 4 type-dedicated packs, "
            "project_type is pinned directly from the pack name and neither "
            "detection nor the select prompt runs",
            "sdd-universal is unaffected -- it is not in TYPE_TO_PACK "
            "(genuinely branches its tech-stack tables on project_type "
            "across 10 types), so its existing detect/confirm/select flow "
            "is unchanged",
            "Same fix applied to the Node CLI (cli/src/commands/init.js) "
            "for parity, though it has no test suite to extend",
            "New regression test in test_init.py "
            "(test_dedicated_pack_choice_skips_redundant_type_prompt): "
            "detection returns None (as in the user's repro) and "
            "questionary.select has only 2 canned answers (pack choice, "
            "ai_tool) -- a third .ask() call for project type would raise "
            "StopIteration and fail the test",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.43"},
    },
    {
        "from":        "2.7.43",
        "to":          "2.7.44",
        "description": "Fix: sdd dashboard's Full Pipeline flow no longer shows 'Constitution (Part 2)' as done before /specify has actually run -- no manifest schema changes",
        "notes": [
            "User-reported: on a brand-new project (sdd init only, /specify "
            "never run), the dashboard's Full Pipeline showed a checkmark "
            "next to 'Constitution (Part 2)' -- constitution.md is "
            "scaffolded for every project by sdd init (Part 1 boilerplate + "
            "a Part 2 template full of {extracted from context} / "
            "{derived} / {date} placeholders), so the old 'does the file "
            "exist' check was always true, immediately after scaffolding",
            "_constitution_status() in status.py now also parses the Part "
            "2 section (from the 'PART 2' marker onward) for unresolved "
            "{...}-style template placeholders via a new "
            "_TEMPLATE_PLACEHOLDER_RE regex -- only when none remain (i.e. "
            "/specify has actually filled Part 2 in, even pre-GATE-1 as a "
            "DRAFT) is the new 'part2_generated' field True",
            "_step_state() for both the 'constitution' and 'manual_gate' "
            "(GATE-1) pipeline-step kinds now branches on "
            "constitution.part2_generated instead of the old bare "
            "constitution.exists",
            "dashboard.py's 'Constitution — GATE-1' detail card gained a "
            "new 'Part 2 generated' row alongside the existing 'Exists' "
            "row, for the same clarity in the raw-status view",
            "Verified against all 5 packs' real shipped constitution.md "
            "templates (sdd-universal, sdd-backend-service, "
            "sdd-frontend-spa, sdd-mobile, sdd-fullstack) plus sdd-micro's, "
            "and via a live build_project_status() run against a "
            "freshly-scaffolded project directory -- all correctly report "
            "part2_generated: False pre-/specify",
            "5 new/updated tests in test_status.py: 2 new end-to-end tests "
            "against build_project_status() (freshly-scaffolded template "
            "vs. filled-in Part 2), 1 new build_pipeline() regression test, "
            "plus 2 existing fixtures (_GATE1_PASSED and the GATE-1 "
            "awaiting-confirmation test) updated to include the new field",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.44"},
    },
    {
        "from":        "2.7.44",
        "to":          "2.7.45",
        "description": "Fix: sdd dashboard crashed on every poll once a feature had a Jira progressive export (docs/jira/{feature}/keys.yml) -- no manifest schema changes",
        "notes": [
            "User-reported: AttributeError ('str' object has no attribute "
            "'get') on every /api/status poll. status.py's "
            "_local_jira_links() assumed keys.yml's epic field was a dict "
            "and stories/tasks were lists of dicts, each with a jira_key "
            "field -- but jira.py's actual writer (_save_keys_summary()) "
            "writes epic as a plain string and stories/tasks as flat "
            "{sdd_id: jira_key} dicts. This schema drifted apart when "
            "jira.py was rewritten (Phase 1, replacing jira-push.py) "
            "without updating the reader to match",
            "The existing unit tests for _local_jira_links() were written "
            "against the reader's (wrong) assumed shape, not the writer's "
            "real output, so the drift went uncaught until a real user "
            "hit it",
            "New _jira_key_from() helper in status.py parses both the "
            "real (string epic / flat-dict stories+tasks) shape and the "
            "old assumed (dict-with-jira_key / list-of-dicts) shape -- "
            "never crashes regardless of which is on disk",
            "New round-trip test (test_jira_keys_round_trip_through_real_"
            "writer) calls jira.py's actual _save_keys_summary() and "
            "verifies status.py's reader parses exactly what it wrote, so "
            "this writer/reader contract can't silently drift apart "
            "again without failing a test",
            "Hardening: /api/status now catches any exception and returns "
            "a JSON {\"error\": ...} with status 500 instead of a bare "
            "connection reset (which was crashing the whole request, not "
            "just this endpoint); the frontend's 5s poll loop catches "
            "fetch/parse failures and shows a visible error banner "
            "instead of silently freezing on stale data",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.45"},
    },
    {
        "from":        "2.7.45",
        "to":          "2.7.46",
        "description": "Fix: a failed sdd review submit (document_reviews not configured for a doc) silently skipped the Confluence draft push and the Jira Epic Business Objectives refresh -- no manifest schema changes",
        "notes": [
            "User-reported: sdd review submit --doc brd failed with "
            "\"'brd' not in document_reviews in integrations.yml\" "
            "(document_reviews is a separate config section from jira:/"
            "confluence: -- needs a reviewer assigned per doc) -- the "
            "agent correctly fell back to chat-mode review per spec, but "
            "that fallback skipped the Confluence draft push entirely "
            "even though confluence: WAS configured, and never refreshed "
            "the Jira Epic with the BRD's real Business Objectives (that "
            "refresh only happens as a side effect of review submit "
            "succeeding)",
            "submit-for-review-step.md (shared block used by all 9 "
            "doc-generating commands -- BRD, Use Cases, SRD, extended "
            "docs, all /plan-* commands): a failed sdd review submit now "
            "falls through to the confluence-only branch (push a draft) "
            "instead of skipping Confluence, only dropping to bare chat "
            "mode if confluence: itself is absent too",
            "specify-brd.prompt.md (all 5 packs) Step D: when jira: is "
            "configured but the Epic wasn't refreshed by a successful "
            "review submit, now explicitly runs 'sdd jira push --level "
            "epic' to push the real Business Objectives -- this only "
            "needs jira: configured, not document_reviews",
            "Hit the same _shared/full/ full-file-sync-overwrites-"
            "blocks-sync gotcha as the 2.7.40 fix: submit-for-review-"
            "step.md is embedded in 9 prompt files that are ALSO "
            "full-file synced from _shared/full/ -- patched all 9 "
            "_shared/full/.github/prompts/*.prompt.md copies (plus the "
            "specify-brd.prompt.md-specific Step D edit) before "
            "re-running sync-blocks.sh; verified 0 diffs on two "
            "subsequent runs",
            "Also clarified for the user (not a bug): constitution.md is "
            "never Confluence-synced at all (no page_map entry, by "
            "design), and hand-editing any .md file locally never "
            "auto-pushes to Confluence on its own -- sync only happens "
            "on an explicit command or as a side effect of sdd review "
            "approve --local. No filesystem watcher exists by design",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.46"},
    },
    {
        "from":        "2.7.46",
        "to":          "2.7.47",
        "description": "Feature: cross-project Jira parent-link fallback via a 'Relates' issue link when project_keys routes a level to a different project than its parent -- no manifest schema changes",
        "notes": [
            "User-reported (via follow-up diagnosis of the project_keys "
            "config): when a level (story/task) is routed to a different "
            "Jira project than its parent (Epic), Jira's parent/Epic-Link "
            "field rejects the cross-project link outright -- a Jira "
            "platform limitation. The child issue was still created, but "
            "the parent link silently never appeared, with only a "
            "warning printed and no actual fallback attempted",
            "New JiraClient.link_issues() creates a plain 'Relates' issue "
            "link (POST /rest/api/3/issueLink, default link type present "
            "on every Jira instance) -- unlike parent/Epic-Link, issue "
            "links are not scoped to a single project",
            "_warn_parent_link_failed() (used by all 4 sdd jira push "
            "call sites -- story, uc-draft, task, chg -- and by sdd "
            "review submit's review-ticket linking) now automatically "
            "attempts this fallback the moment set_parent() fails, and "
            "reports which kind of link actually landed",
            "Documented in README.md and integrations.yml.example's "
            "project_keys cross-project caveat",
            "8 new tests: TestLinkIssues in test_jira_client.py (endpoint, "
            "payload, link-type default/override, HTTP-error "
            "propagation) and a new test_jira_parent_link_fallback.py "
            "covering the fallback-attempted / fallback-succeeded / "
            "fallback-also-failed paths",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.47"},
    },
    {
        "from":        "2.7.47",
        "to":          "2.7.48",
        "description": "Feature: dashboard's existing 'Check Jira/Confluence review links' button now also surfaces the sdd review check --doc classification (APPROVED/NEEDS_REVISION/PENDING) and reviewer comments per document -- no manifest schema changes",
        "notes": [
            "User-requested: a dashboard equivalent of `sdd review check "
            "--doc` to check review status/comments without leaving the "
            "browser",
            "dashboard.py's _fetch_review_links() (the existing on-demand, "
            "button-triggered Jira/Confluence lookup, architecturally "
            "separate from the network-free 5s /api/status poll) now also "
            "calls review.py's own _get_review_status() -- reusing the "
            "exact APPROVED/NEEDS_REVISION/PENDING classification `sdd "
            "review check` uses instead of re-deriving it -- and fetches "
            "Jira reviewer comments via client.get_comments()",
            "Frontend: a color-coded review-status badge (reusing the "
            "existing badge() renderer, new 'review' kind) now appears "
            "next to each document's Jira pill, and Jira review comments "
            "are shown in the existing per-doc comments panel (💬), "
            "labeled separately from local dashboard comments",
            "Same requirement as `sdd review check` itself: only works "
            "where document_reviews is configured in integrations.yml -- "
            "no new gap introduced",
            "2 new tests in test_dashboard.py exercising the real "
            "classification wiring (NEEDS_REVISION with a comment, "
            "APPROVED via approved_statuses) plus 2 source-level page "
            "guards for the new badge/comments markup",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.48"},
    },
    {
        "from":        "2.7.48",
        "to":          "2.7.49",
        "description": "Fix: a Confluence diagram fence whose *configured* rendering mode failed (missing mmdr package, invalid diagram source, or an app macro mode with no macro name set) silently fell back to a plain code block with zero indication anything was wrong -- now prints a warning naming the reason -- no manifest schema changes",
        "notes": [
            "User-reported: set diagrams.mode: local-svg in "
            "integrations.yml, re-pushed a Use Cases page with a Mermaid "
            "relationship diagram, and the diagram still showed as plain "
            "text instead of an image -- with no error or warning "
            "anywhere to explain why",
            "Root cause: md_to_cf.py's _render_local_svg() caught every "
            "renderer exception (including the common case -- `pip "
            "install \"sddflow[diagrams]\"` never having been run, so "
            "the optional mmdr package isn't installed) and discarded "
            "the reason, falling back to a plain code block silently. A "
            "real, fixable failure was indistinguishable from "
            "diagrams.mode simply not being configured at all",
            "md_to_storage()'s return type changed (again) from "
            "tuple[str, list[Attachment]] to tuple[str, list[Attachment], "
            "list[str]] -- the third element is one human-readable "
            "warning per diagram fence whose *configured* mode failed to "
            "render (never populated when diagrams.mode is \"none\", "
            "since that's expected default behavior, not a failure)",
            "Also fixed the same silent-fallback gap for mermaid-app/"
            "plantuml-macro modes selected with no macro_name configured "
            "-- previously indistinguishable from an unconfigured mode "
            "too",
            "All 6 call sites (confluence push, confluence draft, sdd "
            "review submit, sdd review apply, review.py's internal "
            "_push_doc_page, sdd cr submit) now print each warning in "
            "yellow after a successful page push",
            "9 new/updated tests in test_md_to_cf.py: missing macro_name "
            "warnings for both mermaid-app and plantuml-macro, a "
            "renderer-exception warning naming the actual error, a "
            "dedicated MermaidRendererNotInstalled test asserting the "
            "warning names the exact `pip install` fix, and confirming "
            "mode: none / successful renders never produce warnings",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.49"},
    },
    {
        "from":        "2.7.49",
        "to":          "2.7.50",
        "description": "Fix: Confluence diagram attachment uploads (diagrams.mode: local-svg) were rejected with HTTP 415 by every Confluence instance -- the multipart request never actually carried a multipart Content-Type header -- no manifest schema changes",
        "notes": [
            "User-reported (via their own diagnosis of the editable "
            "install): after fixing an unrelated integrations.yml "
            "indentation bug that was silently disabling diagrams.mode "
            "entirely, the diagram STILL didn't render -- this time "
            "with a real Confluence API error: 'diagram-1.svg -- 415 "
            "Unsupported Media Type'",
            "Root cause: build_session() sets a blanket Content-Type: "
            "application/json on the shared requests.Session for every "
            "other call this client makes. upload_attachment()'s "
            "multipart POST (files=...) never overrode it, and requests "
            "only computes its own multipart/form-data; boundary=... "
            "Content-Type when no Content-Type header is already "
            "present on the request -- so Confluence received multipart "
            "bytes mislabeled as application/json and rejected them "
            "with 415, while the page content itself still saved fine "
            "(only the image attachment failed, silently, per the "
            "code's own defensive design -- no exception surfaced "
            "anywhere in this call path)",
            "confluence_client.py's upload_attachment() now explicitly "
            "passes Content-Type: None in the per-request headers dict "
            "-- requests' documented way to remove a session-level "
            "header for one request -- letting it compute the correct "
            "multipart boundary header itself. Verified against a real "
            "requests.Session (not just a mock) that this produces the "
            "expected 'multipart/form-data; boundary=...' header",
            "1 new test in test_confluence_client.py asserting Content-"
            "Type is explicitly unset in the request headers",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.50"},
    },
    {
        "from":        "2.7.50",
        "to":          "2.7.51",
        "description": "Feature: the dashboard's per-document Jira review-gate pill now has a local, instant fallback (mirroring Confluence's), instead of staying blank until the live 'Check Jira/Confluence review links' button is clicked -- no manifest schema changes",
        "notes": [
            "User-reported: the dashboard's Confluence pill next to a "
            "document always showed up, but the Jira pill only appeared "
            "after clicking the live check button -- the asymmetry "
            "turned out to be real, not a config issue: sdd review "
            "submit created the review-gate Jira ticket but never wrote "
            "its key anywhere locally, unlike Confluence (which has "
            "written to .confluence-drafts.json on every push since the "
            "dashboard shipped)",
            "New .specify/.jira-review-links.json, written by "
            "review.py's _record_review_link() -- called from both "
            "review_submit (after the review Story is created/updated) "
            "and review_apply (when it finds the existing ticket to "
            "notify). Same not-feature-scoped limitation as "
            ".confluence-drafts.json by design, to keep the two files "
            "symmetric",
            "status.py's new _local_review_links() reads it the same "
            "way _local_confluence_links() reads the Confluence file -- "
            "no network call, wired into build_feature_status()'s "
            "local_links.jira_review",
            "dashboard.py threads local.jira_review through renderFeature "
            "-> renderDocs -> renderDocRow, used as a fallback (reviewJira "
            "|| localJira) the same way Confluence's pill already falls "
            "back to its local cache -- the live check remains what "
            "refreshes status/comments and re-verifies a possibly-stale "
            "local pill",
            "13 new/updated tests: _record_review_link round-trip "
            "(test_review_helpers.py), review_submit/review_apply "
            "writing the link end-to-end, 6 status.py reader tests plus "
            "a real-writer round-trip lock, and a dashboard.py source-"
            "level guard for the new frontend wiring",
            "Also corrected two now-stale docstrings that predated this "
            "fix and had already drifted from reality: "
            "_local_confluence_links() claimed sdd review submit pages "
            "were 'never cached locally the same way' -- they were, via "
            "_record_confluence_draft_link(), since before this session",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.51"},
    },
    {
        "from":        "2.7.51",
        "to":          "2.7.52",
        "description": "Fix: dashboard's Full Pipeline 'Next:' text could contradict the pipeline diagram itself when an optional step (e.g. checklist at pilot scope) was consciously skipped -- no manifest schema changes",
        "notes": [
            "User-reported: the dashboard showed the pipeline diagram's "
            "current-step marker on 'validate' (already exists, awaiting "
            "review) while the 'Next:' text still said 'Run /checklist to "
            "generate the Spec Quality Checklist' -- checklist is optional "
            "at pilot scope and this project never ran it, but validate.md "
            "already existed",
            "Root cause: _step_state() never consults a step's 'optional' "
            "flag, so an optional step whose doc file doesn't exist always "
            "reports state 'upcoming' -- indistinguishable from 'not "
            "reached yet'. build_pipeline()'s main loop picked the first "
            "non-done step in list order as next_action, and checklist "
            "sits before validate in PIPELINE_DOCS, so it always won even "
            "though the step's own rendered state (o upcoming) was correct",
            "Fix: new _later_doc_step_exists() helper in status.py -- if a "
            "later non-skipped doc-kind step already exists on disk, an "
            "earlier optional+upcoming step is treated as consciously "
            "bypassed and is skipped when picking next_action/next_step_id. "
            "The per-step 'resolved' states (what renders the flow diagram "
            "itself) are untouched -- only the next_action selection "
            "heuristic changed",
            "2 new tests in test_status.py: the bypassed-optional-step "
            "regression case, and a sanity check that a genuinely "
            "not-yet-reached optional step is still picked as next_action "
            "normally",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.52"},
    },
    {
        "from":        "2.7.52",
        "to":          "2.7.53",
        "description": "Feature: blocked documents (e.g. validate.md, on unresolved [NEEDS CLARIFICATION-NNN] markers) can now collect reviewer answers via Jira/Confluence instead of only direct chat/doc edits -- no manifest schema changes",
        "notes": [
            "User-requested: a document like validate.md can be blocked "
            "before it's ever submitted for formal review (brd.md/"
            "use-cases.md/srd.md still have unresolved [NEEDS "
            "CLARIFICATION] markers) -- previously there was no way to "
            "route those specific open questions through Jira/Confluence "
            "the way an already-submitted document's reviewer comments "
            "already could",
            "[NEEDS CLARIFICATION] markers are now numbered locally per "
            "document -- [NEEDS CLARIFICATION-NNN: {question}] -- "
            "matching the [ASSUMPTION-NNN] convention already in use. "
            "This gives every marker a stable, doc-qualified ID "
            "({doc}:NC-{NNN}, e.g. brd:NC-002) that a reviewer's answer "
            "can cite exactly, instead of matching by paraphrased "
            "question text",
            "New sdd review push-questions --doc {doc}: parses a blocked "
            "document's | ID | Locations | Question | table (see "
            "validate.prompt.md's §3a-BLOCKING) and creates/updates one "
            "Jira ticket + Confluence page. Uses the SAME idempotency "
            "label sdd review submit looks for, so once every question "
            "is answered and the document unblocks, sdd review submit "
            "finds and evolves this same ticket in place (posting a "
            "transition comment) instead of creating a second one",
            "New sdd review pull-answers --doc {doc}: fetches comments "
            "from that ticket, matches lines like 'brd:NC-002: <answer>' "
            "against the open items, and patches each answered "
            "[NEEDS CLARIFICATION-NNN] marker directly into its source "
            "document -- bumping that document's Version header and "
            "appending a Version History row. A question asked in more "
            "than one document (a Locations column listing more than one "
            "ID) gets the same answer applied to every one of them from "
            "a single reviewer reply",
            "validate.prompt.md (all 5 packs, not a shared file) updated: "
            "§3a-BLOCKING now calls pull-answers before re-scanning and "
            "push-questions after detecting a block, and its table cites "
            "doc-qualified marker IDs instead of an ad-hoc Q1..Q7 scheme",
            "specify-brd/specify-uc/specify-srd/specify-doc.prompt.md "
            "(shared) and the submit-for-review-step block updated for "
            "the new marker numbering and ID-based comment matching",
            "23 new tests in test_review_helpers.py: table/answer "
            "parsing, marker patching (version bump + Version History, "
            "multi-location propagation, legacy/missing-marker "
            "tolerance), and the push-questions -> submit same-ticket "
            "transition end-to-end",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.53"},
    },
    {
        "from":        "2.7.53",
        "to":          "2.7.54",
        "description": "Fix: multi-line sdd review pull-answers replies (one 'brd:NC-NNN: answer' per line, e.g. a real 7-item Jira comment) were silently collapsed into a single garbled line, so only the first item ever got parsed -- no manifest schema changes",
        "notes": [
            "User-reported: a reviewer answered all 7 open questions on a "
            "push-questions ticket, one per line as instructed, but "
            "pull-answers reported 'no new replies' every time",
            "Root cause: _extract_text() joined every text run in the "
            "whole ADF comment body with a single space, with no regard "
            "for paragraph boundaries. Jira's rich-text comment editor "
            "stores each line a user types as a SEPARATE paragraph node "
            "in the ADF tree, not one paragraph with embedded newlines -- "
            "so a real multi-line reply collapsed into one run-on line, "
            "and _ANSWER_LINE_RE's per-line ^...$ matching (anchored on "
            "actual \\n characters) then only ever found the first item, "
            "with the rest of the comment swallowed into its answer",
            "_extract_text() rewritten to walk ADF block-level nodes "
            "(paragraph, heading, codeBlock, blockquote, listItem) and "
            "join THOSE with newlines, while text runs within a single "
            "block are concatenated directly (also fixes a smaller "
            "pre-existing issue: formatting-split text runs within one "
            "sentence previously got a spurious extra space inserted "
            "between them). hardBreak nodes (shift+enter within one "
            "paragraph) also now produce a newline",
            "Also used by review_check's printed reviewer-comment display "
            "and the dashboard's Jira-comment surfacing -- both benefit "
            "from the same fix, previously showing run-on multi-line "
            "Jira comments as one wrapped line",
            "5 new tests: separate-paragraphs-become-separate-lines, "
            "plain-string-body unchanged, hardBreak handling, and an "
            "end-to-end reproduction of the exact reported bug (7 "
            "distinct paragraph answers, all 7 must parse)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.54"},
    },
    {
        "from":        "2.7.54",
        "to":          "2.7.55",
        "description": "Fix: sdd review pull-answers never patched a marker in any project whose brd.md/use-cases.md/srd.md predate the NEEDS CLARIFICATION-NNN numbering feature -- no manifest schema changes",
        "notes": [
            "User-reported: pull-answers reported 0 items patched every "
            "time despite valid, correctly-formatted answers on the "
            "Jira ticket, confirmed via live diagnostics against the "
            "user's real project -- extract_text (fixed in 2.7.54), "
            "cwd, and comment parsing were each individually confirmed "
            "correct in isolation, narrowing the failure to "
            "_patch_marker itself",
            "Root cause: validate.md's own §3a-BLOCKING scan only "
            "DISPLAYS synthesized {doc}:NC-{NNN} IDs for legacy "
            "unnumbered [NEEDS CLARIFICATION: ...] markers (order of "
            "appearance) -- it never writes those numbers back into the "
            "source document, since scanning isn't editing. Confirmed "
            "via a live grep -o \"NEEDS CLARIFICATION-[0-9]*\" against "
            "the user's brd.md returning zero matches despite the "
            "displayed table citing brd:NC-001 etc. _patch_marker's "
            "exact-string search for the numbered form therefore never "
            "found anything to replace, in any project generated before "
            "this feature shipped",
            "New _number_legacy_markers(): retroactively numbers any "
            "unnumbered [NEEDS CLARIFICATION: ...] marker in a source "
            "doc as [NEEDS CLARIFICATION-NNN: ...], in order of "
            "appearance, continuing after the highest existing number so "
            "a doc with a mix of both forms doesn't collide -- wired "
            "into review_pull_answers to run once per referenced doc "
            "before any patch is attempted",
            "Secondary fix: the AI generating validate.md's Locations "
            "column has, in practice, abbreviated use-cases.md as 'uc' "
            "(resolve_doc_path's real key is 'use-cases', matching the "
            "filename stem) -- new _normalize_doc_key() maps known "
            "abbreviations before every resolve_doc_path call sourced "
            "from a parsed location ID. validate.prompt.md (all 5 packs) "
            "tightened to require an exact filename stem going forward",
            "11 new tests: legacy-marker numbering (order, zero-padding, "
            "mixed-state continuation, already-numbered untouched, "
            "missing file), doc-key alias normalization, and an "
            "end-to-end reproduction of the exact reported bug (a "
            "validate.md table citing brd:NC-001/uc:NC-001 against docs "
            "still in the old unnumbered form, confirming pull-answers "
            "now retrofits and patches both)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.55"},
    },
    {
        "from":        "2.7.55",
        "to":          "2.7.56",
        "description": "Fix: sdd review pull-answers patched BRD/SRD/UC locally but never refreshed their existing Confluence pages, leaving them showing stale pre-answer [NEEDS CLARIFICATION] markers -- no manifest schema changes",
        "notes": [
            "User-reported: after /validate's push-questions/pull-answers "
            "round-trip resolved every open question, brd.md/srd.md/"
            "use-cases.md were updated on disk and their versions bumped, "
            "but their Confluence pages (created back at their own "
            "/specify-brd -> sdd review submit time) still showed the old "
            "unresolved markers -- only validate.md's own page was ever "
            "touched by push-questions/pull-answers",
            "review_pull_answers now tracks the on-disk path of every doc "
            "it successfully patches, and after the patch loop, re-pushes "
            "each one's Confluence page via the same _push_doc_page() "
            "helper sdd review approve already uses -- best-effort per "
            "doc, so one page's failure never blocks the others or the "
            "patching that already succeeded",
            "Only runs when confluence: is configured in integrations.yml; "
            "silently skipped otherwise, matching the rest of "
            "pull-answers' safe-to-call-unconditionally contract",
            "1 new test: push-questions -> answer -> pull-answers, "
            "confirming both patched docs' Confluence pages are created/"
            "updated with the expected page-map titles",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.56"},
    },
    {
        "from":        "2.7.56",
        "to":          "2.7.57",
        "description": "Guardrail: validate.prompt.md Step C no longer lets a document-level approval auto-check per-item §1-§4 confirmation checkboxes -- no manifest schema changes",
        "notes": [
            "User-reported (from a live project's /analyze run): a prior "
            "agent session, chasing the analyze.prompt.md verify gate's "
            "literal 'VALIDATE complete' string, bulk-checked every "
            "unchecked box in validate.md's §1 (Reviewer Confirms), §2 "
            "(BA/PO Confirms), §3 (assumption Correct?), §3a (UC Business "
            "Scenario Correct?), and §4 (Scope Confirmation) -- inferring "
            "itemized per-line business sign-off purely from the "
            "document's overall Jira ticket having been closed after a "
            "Q&A comment thread, which is not the same as a named "
            "reviewer actually addressing that specific item",
            "validate.prompt.md's own Step C only ever specified updating "
            "the header (Status: Draft -> Approved) and the §5 Approvals "
            "table -- the agent's bulk-check of §1-§4 was not something "
            "the prompt told it to do; this migration tightens the "
            "wording to explicitly forbid it and to say what to do "
            "instead (leave unchecked with a note, or point to the "
            "specific reviewer statement that confirmed that exact item)",
            "This matters most for regulated/financial-transfer features "
            "where §1-§4's checkboxes are meant to be a traceable, "
            "defensible audit trail of actual line-item business review "
            "-- not a formality that gets rubber-stamped to satisfy a "
            "downstream gate's string match",
            "Applied identically to validate.prompt.md in all 5 packs "
            "(not a shared/blocks file -- each pack's copy edited "
            "individually, same wording)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.57"},
    },
    {
        "from":        "2.7.57",
        "to":          "2.7.58",
        "description": "Feature: analyze.md and clarify.md can now go through the same Jira/Confluence review-gate flow as brd/srd/etc (a new 'validate' phase) -- no manifest schema changes",
        "notes": [
            "User asked why /analyze and /clarify never got pushed to "
            "Confluence/Jira the way /validate does -- by design they "
            "were chat-only working documents, but nothing in "
            "resolve_doc_path/review_submit/review_approve actually "
            "required that; they're fully generic by doc key",
            "Added document_reviews.validate/.analyze/.clarify entries "
            "to integrations.yml.example (phase: validate, sequence "
            "1/2/3 -- validate before analyze before clarify, enforced "
            "by the same predecessor-sequence gate every other phase "
            "already uses), plus matching page_map entries",
            "analyze.prompt.md and clarify.prompt.md (all 5 packs) gained "
            "the same Stakeholder Review and Approval Step B/C section "
            "validate.prompt.md already has -- sdd review submit/check/"
            "approve, same approval-signal handling, same guardrail "
            "against inferring per-section findings as individually "
            "confirmed by a document-level approval",
            "Fixed clarify-template.md's header, which said "
            "'Status: OPEN' instead of 'Status: Draft' -- "
            "_mark_md_approved's regex only recognizes Draft/Proposed, "
            "so the approval flip would have silently never updated the "
            "header for clarify.md without this fix",
            "Each of validate/analyze/clarify is optional individually -- "
            "add only the ones you want routed through Jira/Confluence; "
            "the rest stay chat-only, per review-gates.md",
            "4 new tests: generic submit works for analyze/clarify doc "
            "keys, the validate-phase sequence gate blocks analyze until "
            "validate is approved, and the clarify.md header fix is "
            "confirmed to make the approval flow work end-to-end",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.58"},
    },
    {
        "from":        "2.7.58",
        "to":          "2.7.59",
        "description": "Feature: Confluence pages for documents under Jira review now show a live Jira link + status banner, and page_map covers every generated doc type (qa-testcases, tasks, checklist, and the living/service docs) -- no manifest schema changes",
        "notes": [
            "User asked why a doc pushed to Jira for review didn't also "
            "get its Confluence page stamped with the ticket link/status "
            "so a reviewer could see it without leaving Confluence -- the "
            "page only ever mirrored the .md content, never the Jira "
            "state, since the two pushes happened in unrelated code paths",
            "sdd review submit/check/apply now prepend a small info/"
            "success/warning panel (via the new _push_doc_page banner) "
            "showing the ticket key, link, and live status (Pending/"
            "Needs Revision/Approved) -- refreshed every time the CLI "
            "touches that document's review state, so it never goes "
            "stale between submit and the reviewer's eventual decision",
            "Only applies to doc keys with a document_reviews entry (i.e. "
            "actually under Jira review) -- docs pushed via the page_map "
            "fallback alone (no Jira gate configured) get a plain page, "
            "same as before",
            "User also asked for a Confluence page for 'QA test case etc "
            "-- whatever there in local md file' -- page_map in "
            "integrations.yml.example now also covers qa-testcases, "
            "tasks, checklist, and the 4 living/service-level docs "
            "(data-model, security-design, api-spec, component-library), "
            "so `sdd confluence push --doc <key>` works for all of them, "
            "not just the phase-gated documents",
            "6 new tests: banner HTML per status, submit stamps a Pending "
            "banner once the ticket exists, check refreshes an existing "
            "page to Approved, and the page_map fallback path (no Jira "
            "gate) omits the banner entirely",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.59"},
    },
    {
        "from":        "2.7.59",
        "to":          "2.7.60",
        "description": "Feature: clarify.md's own open items (AMB/GAP/CON/ASM/OQ/R) can now be pushed to Jira/Confluence for answers via sdd review push-questions/pull-answers, the same way validate.md's [NEEDS CLARIFICATION-NNN] markers already could -- no manifest schema changes",
        "notes": [
            "User pointed out that /validate's open questions could already "
            "be answered via Jira (push-questions/pull-answers), but /clarify's "
            "8-item report had no such path -- push-questions silently found "
            "nothing to push because it only ever recognized the "
            "'{doc}:NC-{NNN}' bracketed-marker scheme, not clarify.md's own "
            "STATUS TABLE (AMB/GAP/CON/ASM/OQ/R rows)",
            "Added a parallel parse/patch path scoped to --doc clarify: "
            "_parse_clarify_open_items reads OPEN STATUS TABLE rows (posting "
            "each item's full section as the Jira question text), "
            "_parse_clarify_answers reads 'clarify:AMB-001: <answer>'-style "
            "replies, and _patch_clarify_item fills the item's {FILL...} "
            "placeholder and flips its STATUS TABLE row to the terminal "
            "status for its type (RESOLVED for AMB/GAP/R, CORRECTED for CON, "
            "DECIDED for OQ, CONFIRMED/CORRECTED for ASM depending on "
            "whether the answer starts with 'yes')",
            "review_push_questions/review_pull_answers now branch on "
            "doc == 'clarify' for parsing/patching only -- the surrounding "
            "Jira ticket creation, idempotency-label reuse, and Confluence "
            "re-push logic is unchanged and fully shared with the existing "
            "NC-NNN path",
            "clarify.prompt.md (all 5 packs) documents this under 'Accepted "
            "reply forms'; review-gates.md's shared block gained a matching "
            "paragraph, synced into every pack's CLAUDE.md",
            "16 new tests: STATUS TABLE parsing (including skipping already-"
            "resolved rows), answer-line parsing, placeholder fill + "
            "per-type status flip (all 5 terminal statuses, including both "
            "ASM branches), and end-to-end push-questions/pull-answers CLI "
            "coverage including the Confluence re-push",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.60"},
    },
    {
        "from":        "2.7.60",
        "to":          "2.7.61",
        "description": "Fix: /clarify now auto-pushes its open items to Jira/Confluence on generation and auto-pulls answers on re-run, matching /validate's existing behavior -- prompt-only, no CLI or manifest changes",
        "notes": [
            "The 2.7.60 clarify Jira-answers feature only wired the CLI "
            "(push-questions/pull-answers) to understand clarify.md's STATUS "
            "TABLE -- it left clarify.prompt.md requiring the user to "
            "explicitly ask for the Jira push each time, unlike "
            "validate.prompt.md's §3a, which pushes automatically the "
            "moment it detects open items and pulls automatically at the "
            "start of every re-run",
            "clarify.prompt.md (all 5 packs) now: (1) at the top of 'Your "
            "Task', if clarify.md already exists, runs pull-answers first "
            "and skips regeneration if everything is now resolved; (2) "
            "right after saving a freshly generated clarify.md, "
            "auto-runs `sdd review push-questions --doc clarify` when "
            "document_reviews.clarify is configured, before presenting "
            "the report to the user",
            "'Accepted reply forms' simplified accordingly -- Jira/"
            "Confluence answers are now just another accepted reply form "
            "(pulled in automatically), not a separate manual opt-in step",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.61"},
    },
    {
        "from":        "2.7.61",
        "to":          "2.7.62",
        "description": "Fix: clarify.md's Step 4 now re-syncs affected documents to Confluence/Jira after applying an answer, sdd review apply no longer requires both jira: and confluence:; new sdd confluence push --summary pushes a doc's .summary.md to its own page -- no manifest schema changes",
        "notes": [
            "User found 3 issues with the clarify Jira-answers flow: (1) "
            "when an answer got applied to brd/srd/use-cases (Step 4), "
            "those documents were updated locally and their .summary.md "
            "regenerated, but the change never reached Confluence or "
            "notified that document's own Jira reviewer; (2) same root "
            "cause, described as 'status not updating, only summary is "
            "created'; (3) enhancement request -- push .summary.md files "
            "to their own Confluence page too",
            "clarify.prompt.md (all 5 packs) Step 4 now runs `sdd review "
            "apply --doc {doc}` for each affected document right after "
            "bumping its version -- this re-pushes the updated content to "
            "that document's OWN Confluence page and posts a 'please "
            "re-review' comment on its OWN Jira ticket, independent of "
            "clarify.md's ticket. Skips silently if not configured",
            "review_apply no longer hard-requires both jira: and "
            "confluence: sections (previously errored out entirely on a "
            "confluence-only or jira-only project) -- it now does "
            "whichever half is actually configured, matching the rest of "
            "the framework's confluence-is-independently-optional design",
            "New `sdd confluence push --doc {doc} --summary` pushes "
            "{doc}.summary.md (if it exists) to a separate page titled "
            "'... — Summary', leaving the full doc's own page untouched. "
            "clarify.prompt.md Step 5 now auto-runs this for "
            "clarify.summary.md when confluence: is configured",
            "10 new tests: confluence-only and jira-only review_apply "
            "paths, and 4 covering the --summary flag (push, full-doc-"
            "unaffected, missing-summary-file skip, dry-run)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.62"},
    },
    {
        "from":        "2.7.62",
        "to":          "2.7.63",
        "description": "Fix: plan-design.prompt.md's api-spec.md merge and change.prompt.md's entire document walk (UPDATE/RERUN/ANNOTATE) now re-sync to Confluence/Jira after each local update -- prompt-only, no CLI or manifest changes",
        "notes": [
            "Same root cause as 2.7.62's clarify fix, found in two more "
            "places: plan-design.prompt.md §3 merges endpoint changes into "
            "the living .specify/service/api-spec.md (bump version, "
            "Version History, regenerate summary) but never re-pushed it; "
            "change.prompt.md's Step 5 document walk can UPDATE, RERUN, or "
            "ANNOTATE any of 14 document types in the full pipeline chain "
            "(brd through tasks) with the identical local-only pattern",
            "plan-design.prompt.md (all 5 packs) now runs `sdd review apply "
            "--doc api-spec` immediately after merging into api-spec.md, "
            "before design.md §3's own summary text",
            "change.prompt.md (all 5 packs) now runs `sdd review apply "
            "--doc {doc-key}` at the end of all three action branches "
            "(ANNOTATE, UPDATE incl. 'modify', RERUN) for every document in "
            "the walk order except constitution.md (not resolvable via "
            "resolve_doc_path -- it lives outside .specify/features/ and "
            ".specify/service/, never pushed). A doc-key convention note "
            "(filename minus .md) was added once near the walk order line",
            "No CLI changes needed -- this reuses sdd review apply exactly "
            "as fixed/relaxed in 2.7.62 (works with confluence-only, "
            "jira-only, or both; skips silently if neither is configured)",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.63"},
    },
    {
        "from":        "2.7.63",
        "to":          "2.7.64",
        "description": "Fix: local-svg diagrams pushed to Confluence now render at a readable width (ac:width=900 by default, configurable via diagrams.local_svg.width) instead of the SVG's own tiny intrinsic size -- no manifest schema changes",
        "notes": [
            "User reported that Mermaid diagrams rendered via "
            "diagrams.mode: local-svg showed up very small on the "
            "Confluence page, forcing the reader to open and zoom -- "
            "root cause: _render_local_svg() emitted <ac:image> with no "
            "ac:width attribute, so Confluence displayed the image at "
            "the SVG's own intrinsic size (Mermaid's renderer typically "
            "emits a few hundred pixels)",
            "New DiagramsConfig.local_svg_width field (default 900), "
            "configured via a nested diagrams.local_svg.width key in "
            "integrations.yml, matching the existing mermaid_app/"
            "plantuml_macro nested-dict convention",
            "_render_local_svg() now emits <ac:image ac:width=\"{width}\">"
            " -- Confluence scales height to match, preserving aspect "
            "ratio",
            "integrations.yml.example (all 5 packs) documents the new "
            "local_svg.width option in place of the old placeholder "
            "'no options today' comment",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.64"},
    },
    {
        "from":        "2.7.64",
        "to":          "2.7.65",
        "description": "Fix: /task never pushed stories/tasks to Jira or Confluence, diagram attachment 400s hid the real reason, constitution.md is now pushable; adds Approver name column to every Approvals table",
        "notes": [
            "User reported 4 real gaps after running /task: (1) the "
            "placeholder Jira Story created at /specify-uc time never got "
            "updated/finalized, (2) Tasks were never created in Jira nor "
            "linked to their Story, (3) no Confluence page (with Jira "
            "link + status) was ever created for tasks.md, (4) no /task "
            "document reached Confluence at all -- root cause: "
            "task.prompt.md's old Section 4 only generated an offline CSV "
            "export and told the user to manually run a retired /jira-push "
            "slash command; it never called the sdd CLI",
            "task.prompt.md (all 5 packs) rewritten: new Section 4 "
            "auto-runs `sdd jira push --level story` then `--level task` "
            "(finalizes UC-draft Stories in place, creates real Tasks "
            "linked to their parent Story); new Section 5 pushes "
            "stories.md/qa-testcases.md directly to Confluence and runs "
            "tasks.md through the same Submit-for-Review + review-decision "
            "discipline every other document uses (tasks.md has a real "
            "document_reviews gate, reviewed by the Scrum Master); the old "
            "CSV export is kept as Section 6, relabelled as an offline "
            "fallback",
            "Added missing `stories`/`smoke-tests` page_map entries "
            "(collision risk across features without them, same bug "
            "class as an earlier fix); fixed document_reviews.tasks."
            "confluence_page ('Task Breakdown') diverging from page_map."
            "tasks ('Tasks') -- they must agree or review submit/apply "
            "and a direct confluence push land on two different pages",
            "Diagram attachment 400 errors (e.g. a sequence diagram during "
            "`sdd review check --doc design`) only ever showed a bare "
            "'400 Client Error: Bad Request for url: ...' with no reason "
            "-- upload_diagram_attachments now parses the actual "
            "Confluence error body (message/errors) into the warning. "
            "_render_local_svg also now guards against mmdr returning "
            "non-SVG output for certain diagrams without raising, which "
            "previously reached Confluence as malformed bytes",
            "constitution.md was the one document with no way to reach "
            "Confluence at all -- resolve_doc_path/_resolve_page_title/"
            "resolve_doc_parent_id/_push_doc_page now special-case "
            "'constitution' as a project-wide page (like living docs, "
            "but at .specify/memory/ not .specify/service/); "
            "specify.prompt.md (all 5 packs) auto-pushes it right after "
            "GATE-1 finalizes or a later amendment is confirmed",
            "Every document template's `## Approvals` table gained an "
            "`Approver` column between Role and Status (132 template "
            "files across _shared + all 5 packs) -- the review-decision-"
            "step shared block now resolves the approver's actual name "
            "from roles.yml's `roles:` map (filled in once per project) "
            "before falling back to asking, and writes it into that "
            "column, so approvals show who, not just which role",
            "token-usage-template.md's own notes section now explains "
            "specifically why the estimate reads far lower than a "
            "provider's real usage dashboard (scoped to doc I/O only, "
            "excludes system prompt/tool defs/conversation history) and "
            "points to the AI tool's own native usage reporting as the "
            "authoritative source -- there is no API this framework can "
            "call to get a real number from inside a prompt",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.65"},
    },
    {
        "from":        "2.7.65",
        "to":          "2.7.66",
        "description": "Add: sdd token-log reads Claude Code's own local session transcript for REAL token usage (not the char/4 estimate) -- new CLI command + token-usage-template.md Source column; every other AI tool keeps the existing estimate",
        "notes": [
            "The user asked whether anything more could be done about "
            "the token-usage estimate reading much lower than a real "
            "usage dashboard. Verified: Claude Code writes a local "
            "session transcript (~/.claude/projects/{project}/"
            "{session-id}.jsonl, plus one file per spawned subagent "
            "under {session-id}/subagents/) where every assistant turn "
            "carries the REAL usage object the Anthropic API actually "
            "returned -- input_tokens, output_tokens, "
            "cache_creation_input_tokens, cache_read_input_tokens. Not "
            "an estimate",
            "New sdd/utils/claude_code_transcript.py locates the current "
            "session's transcript (and its subagent transcripts) and "
            "sums real usage per model since a given timestamp",
            "New `sdd token-log --command {name}` CLI command: resolves "
            "the window to sum (since the last logged row's timestamp, "
            "or the whole session for the first command logged), writes/"
            "creates token-usage.md from the template, appends one row "
            "per model, and updates Running Totals -- all without agent "
            "hand-arithmetic. Exit codes let a calling prompt distinguish "
            "success (0), the opt-in gate being off (2, token-pricing.yml "
            "missing), and no transcript found (3, not Claude Code or no "
            "session has touched this project -- fall back to the "
            "estimate) from an actual error (1)",
            "This is Claude Code-only by nature -- the transcript path/"
            "format is undocumented and reverse-engineered, not a "
            "published API, and has no equivalent under any other AI "
            "tool this framework supports. token-usage-logging.md (the "
            "shared CLAUDE.md block) now tries `sdd token-log` first and "
            "falls back to the existing char/4 estimate whenever it's "
            "unavailable or exits non-zero -- every other AI tool "
            "(Copilot, Cursor, Windsurf, copy-paste 'any AI') is "
            "completely unaffected, still estimate-only",
            "token-usage-template.md's Per-Command Log table gained a "
            "Source column (Real (Claude Code) | Estimated) so the two "
            "measurement kinds are never silently compared to each "
            "other. A pre-existing token-usage.md from before this "
            "column existed (7-column rows) is never rewritten -- new "
            "rows are only ever appended, old ones parsed generically "
            "for the Running Totals sum but left byte-for-byte untouched",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.66"},
    },
    {
        "from":        "2.7.66",
        "to":          "2.7.67",
        "description": "Fix: dashboard Token Usage card showed all blanks for any token-usage.md written after the Source-column rename (2.7.66) dropped the 'Est.' prefix from Running Totals labels",
        "notes": [
            "The 2.7.66 token-usage-template.md rewrite renamed the "
            "Running Totals labels from 'Total Est. Input Tokens' etc. "
            "to 'Total Input Tokens' (since a row can now be Real or "
            "Estimated, not only estimated) -- but status.py's "
            "_RUNNING_TOTAL_ROW_RE regex and dashboard.py's rendered JS "
            "labels were never updated to match, so every token-usage.md "
            "created or updated after that rename showed '-' for all "
            "three totals in `sdd dashboard`'s Token Usage card",
            "status.py: _RUNNING_TOTAL_ROW_RE now makes 'Est. ' optional "
            "in the label, and _parse_token_usage() checks both the new "
            "and legacy label text, so files written before or after "
            "2.7.66 both parse correctly",
            "dashboard.py: renderTokenUsage() JS now renders the current "
            "'Total Input/Output Tokens' / 'Total Cost (USD)' labels",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.67"},
    },
    {
        "from":        "2.7.67",
        "to":          "2.7.68",
        "description": "Enhance: sdd dashboard gets a manual Light/Dark/Auto theme toggle (fixes theme not switching for users whose browser doesn't report prefers-color-scheme reliably) plus a discoverable data-sourcing explainer and clearer empty states",
        "notes": [
            "The user reported dark/light mode 'not working' on the "
            "dashboard. The dashboard only ever followed the browser's "
            "prefers-color-scheme media query -- some browsers/embedded "
            "webviews never report that signal reliably, so the page was "
            "stuck on one theme regardless of OS setting. Fixed by adding "
            "an explicit Light / Dark / Auto toggle (top right) that sets "
            "data-theme on <html>, which CSS gives higher specificity "
            "than the media query, and persists the choice to "
            "localStorage so it survives reloads",
            "Verified with Playwright across all 3 states (OS=dark + "
            "auto, forced light while OS=dark, forced dark, back to "
            "auto, OS=light + auto) plus reload-persistence -- each "
            "produced the expected --bg value",
            "Added a collapsible 'Where this data comes from' info box "
            "near the top of the page (was previously a long paragraph "
            "buried at the bottom, easy to miss) explaining which cards "
            "are local-file-only vs. the one on-demand live Jira/"
            "Confluence check",
            "The 'no features yet' empty state now names the actual "
            "next command (/specify or sdd specify) instead of just "
            "stating the absence",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.68"},
    },
    {
        "from":        "2.7.68",
        "to":          "2.7.69",
        "description": "Enhance: sdd dashboard gets a Real/Estimated token badge, a Features Overview table for multi-feature projects, and auto-refreshing Jira/Confluence review links",
        "notes": [
            "Token Usage card now shows a 'Source mix' row -- Real N / "
            "Est. N badges tallied from the Per-Command Log's Source "
            "column (status.py's _parse_command_log_sources; mirrors "
            "token_log.py's row-parsing so legacy 7-column rows without "
            "a Source column still count correctly, as Estimated)",
            "New 'Features Overview' card (only shown once a project has "
            "2+ features -- redundant for one) lists every feature's "
            "current pipeline step, task progress, and next action in "
            "one table, each row linking to that feature's full block "
            "further down the page",
            "The 'Check Jira/Confluence review links' button remains the "
            "only way to make the first live call for a feature (opt-in "
            "preserved) -- but once you've checked a feature at least "
            "once, the dashboard now quietly re-checks it every 5 "
            "minutes so the pills don't go stale without a re-click. A "
            "transient failure during auto-refresh keeps the last known-"
            "good result rather than flashing an error over data that "
            "was fine a moment ago",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.69"},
    },
    {
        "from":        "2.7.69",
        "to":          "2.7.70",
        "description": "Enhance: sdd dashboard's Documents card now shows who should approve a pending document (role + name from roles.yml) and who approved it, via which mode, once it is",
        "notes": [
            "The user asked: for a document that isn't approved, who "
            "should approve it (role + name)? For one that is, who "
            "approved it, and was that recorded via Jira or a manual/"
            "chat approval? Neither status.py nor the dashboard captured "
            "any of this before -- only the bare Status: header value",
            "New status.py._parse_approvals_table(path) parses a "
            "document's own '## Approvals' table -- present in every "
            "template, filled in identically regardless of review mode "
            "(chat/local/jira) per the review-decision-step shared "
            "block -- so it is the one source of truth for 'who "
            "approved this / who's still pending' that works the same "
            "way everywhere. Tolerates the older 3-column format (Role | "
            "Status | Date) from before the Approver column existed "
            "(added in an earlier release) alongside the current "
            "4-column one",
            "New status.py._resolve_expected_approver() normalizes a "
            "document's human-readable Role cell ('Product Owner', "
            "'DevOps/SRE') to roles.yml's snake_case key convention "
            "(product_owner, devops_sre) and looks up the actual name "
            "filled in there -- so a pending document names the person, "
            "not just the role",
            "dashboard.py: each Documents row now shows a compact one-"
            "line summary under the Status badge ('Awaiting Product "
            "Owner: Jane Smith', or the approver's name once approved), "
            "plus a new 👤 toggle (matching the existing 💬 comments "
            "pattern) that expands the full Role/Approver/Status/Date "
            "table and states which mode recorded the approval (Local / "
            "Jira / Chat only — no audit file)",
            "The existing Approve pill (next to the Approve button) now "
            "shows the resolved approver's name for every review mode, "
            "not just local mode as before -- previously a Jira- or "
            "chat-approved document still showed a bare 'Approve' "
            "button even though its Status header already said Approved",
            "Verified end-to-end with Playwright: pending single-"
            "approver doc, approved doc via each of the three record "
            "sources (local_approval, chat-only via the doc's own "
            "table, legacy 3-column table), and a multi-row pending doc",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.70"},
    },
    {
        "from":        "2.7.70",
        "to":          "2.7.71",
        "description": "Enhance: sdd dashboard consolidates each document's View/Approvals/Comments toggles into one tabbed Details panel, decluttering the Documents row",
        "notes": [
            "Follow-up to a UX review the user asked for after several "
            "features were bolted onto the same Documents row this "
            "release cycle (View, 👤 Approvals, 💬 Comments, Jira pill, "
            "Confluence pill, review-status badge -- up to 7 elements in "
            "one cell). Verified with Playwright at 600px/900px widths: "
            "no findings of actual breakage, but the row had grown past "
            "a comfortable scan-width, and opening View + Approvals + "
            "Comments together stacked three separate panels",
            "dashboard.py: replaced the three independent expand-toggles "
            "with a single 'Details' button that opens one panel with a "
            "tab strip (Content / Approvals / Comments) -- only one tab's "
            "content renders at a time. The Links cell is now typically "
            "just [Approve] [Details] [Jira pill] [Confluence pill]",
            "Posting a comment now opens the panel on the Comments tab "
            "(previously: expanded a separate comments-only panel)",
            "New state shape: openDocs (Set of doc keys with the panel "
            "open) + docTab (doc key -> active tab, default 'content'), "
            "replacing the previous expandedDocs/expandedComments/"
            "expandedApprovals three-Set setup",
            "Verified end-to-end with Playwright: row button count "
            "before/after, tab switching, comment-then-auto-switch-to-"
            "Comments-tab, and confirmed only one detail panel renders "
            "per document at a time",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.71"},
    },
    {
        "from":        "2.7.71",
        "to":          "2.7.72",
        "description": "Fix: sdd dashboard's Constitution/Token-Usage status badges silently lost their green/amber color, and the info box referenced a 'View' button that no longer exists",
        "notes": [
            "A second UX review pass (user asked to review the whole "
            "dashboard again after the Details-panel consolidation) "
            "found two real, verified regressions rather than just "
            "opinion -- confirmed each with a live headless-browser "
            "check of computed CSS/DOM before and after the fix",
            "CSS bug: '.kv span:first-child { color: var(--muted) }' "
            "used a descendant combinator, so it also matched a badge/"
            "pill span nested inside a .kv row's value column whenever "
            "that badge was the value span's only child -- a badge IS "
            "':first-child' of ITS OWN parent too. This silently forced "
            "the Constitution card's gate-1 badge and the Token Usage "
            "card's Real/Est 'Source mix' badges to plain gray instead "
            "of their intended green, losing the color cue exactly "
            "where it mattered. Fixed with a child combinator "
            "('.kv > span:first-child'), which only ever matches the "
            "row's own direct label span",
            "Stale copy: the info box's 'Where this data comes from' "
            "text still said '\"View\" reads the raw .md file from "
            "disk' -- a leftover from before the View/Approvals/"
            "Comments toggles were consolidated into one Details panel "
            "with tabs (2.7.71). Updated to reference the Details "
            "button's Content tab instead",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
        "migrate": lambda m: {**m, "sdd_version": "2.7.72"},
    },
]


def _resolve_pack(manifest: dict, pack_override: str | None) -> tuple[str, str]:
    """Returns (pack_name, how-we-know) -- "how" is shown to the user so an
    inferred (rather than certain) answer is never presented as fact.
    Raises ValueError if --pack names something that doesn't exist."""
    if pack_override:
        if pack_override not in ALL_PACKS:
            raise ValueError(f"Unknown pack '{pack_override}'. Available: {', '.join(ALL_PACKS)}")
        return pack_override, "--pack flag"

    stored = manifest.get("pack")
    if stored:
        return stored, "manifest.yml 'pack' field"

    project = manifest.get("project") or {}
    is_micro = "project_type" not in manifest and "scope" not in project
    if is_micro:
        return "sdd-micro", "no scope/project_type in manifest.yml (sdd-micro shape)"

    project_type = manifest.get("project_type")
    if project_type in TYPE_TO_PACK:
        return TYPE_TO_PACK[project_type], f"inferred from project_type '{project_type}'"

    return UNIVERSAL_PACK, "no pack recorded and project_type unrecognized — defaulting to sdd-universal"


def _do_sync_prompts(pack_override: str | None, yes: bool) -> None:
    manifest = read_manifest() or {}
    try:
        pack_name, source = _resolve_pack(manifest, pack_override)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        console.print()
        return

    console.print(f"  [bold]Syncing prompts from pack:[/bold] [cyan]{pack_name}[/cyan]  [dim]({source})[/dim]")
    if "inferred" in source or "defaulting" in source:
        console.print(
            "  [dim]Not certain which pack this project uses — pass --pack "
            "explicitly if this guess is wrong.[/dim]"
        )
    console.print()

    preview = sync_pack_prompts(pack_name, dry_run=True)
    changed = preview["updated"] + preview["added"]
    if not changed:
        console.print("  [green]✓  .github/prompts/ and .claude/commands/ are already up to date.[/green]")
        console.print()
        return

    if preview["updated"]:
        console.print(f"  [yellow]{len(preview['updated'])} file(s) will be updated[/yellow] (backed up first):")
        for f in preview["updated"]:
            console.print(f"    [dim]•[/dim] {f}")
    if preview["added"]:
        console.print(f"  [green]{len(preview['added'])} file(s) will be added[/green] (new in this pack version):")
        for f in preview["added"]:
            console.print(f"    [dim]•[/dim] {f}")
    console.print(f"  [dim]{len(preview['unchanged'])} file(s) already up to date, left alone.[/dim]")
    console.print()

    if not yes and not click.confirm("  Proceed?", default=True):
        console.print("  [yellow]Cancelled — no files changed.[/yellow]")
        console.print()
        return

    result = sync_pack_prompts(pack_name)
    console.print(
        f"  [green]✓[/green]  {len(result['updated'])} updated, {len(result['added'])} added, "
        f"{len(result['unchanged'])} unchanged."
    )
    if result["backup_dir"]:
        console.print(f"  [dim]Backups of overwritten files: {result['backup_dir']}[/dim]")
    console.print()


@click.command()
@click.option("--sync-prompts", is_flag=True,
              help="Re-copy this project's .github/prompts/ and .claude/commands/ "
                   "from the current pack, overwriting stale copies. sdd upgrade "
                   "alone only ever patches manifest.yml's sdd_version -- it never "
                   "touches these files, so fixes made to prompt content after this "
                   "project was scaffolded need this flag to actually reach it.")
@click.option("--pack", "pack_override", default=None,
              help=f"Pack to sync prompts from, overriding manifest.yml/inference. One of: {', '.join(ALL_PACKS)}")
@click.option("-y", "--yes", is_flag=True, help="Skip the confirmation prompt for --sync-prompts.")
def upgrade_command(sync_prompts, pack_override, yes):
    """Migrate manifest.yml to the current pack version."""
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print(f"  [bold cyan]SDD Framework[/bold cyan] — upgrade")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    if not Path(MANIFEST_PATH).exists():
        console.print(f"[red]✗  {MANIFEST_PATH} not found — run from the pack root directory.[/red]")
        raise SystemExit(1)

    manifest = read_manifest()
    current_version = manifest.get("sdd_version") if manifest else None

    if current_version == SDD_VERSION:
        console.print(f"  [green]✓  Already at v{SDD_VERSION} — nothing to do.[/green]")
        console.print()
        if not sync_prompts:
            return
    else:
        console.print(f"  Current version : [yellow]{current_version or 'pre-versioning (v1.x)'}[/yellow]")
        console.print(f"  Target version  : [green]{SDD_VERSION}[/green]")
        console.print()

        pending = [
            m for m in MIGRATIONS
            if (current_version is None and m["from"] is None)
            or m["from"] == current_version
        ]

        if not pending:
            console.print("[yellow]  No migration path found. See CHANGELOG.md for manual steps.[/yellow]")
            console.print()
            if not sync_prompts:
                return
        else:
            for migration in pending:
                console.print(f"  [bold]Migrating → v{migration['to']}: {migration['description']}[/bold]")
                for note in migration["notes"]:
                    console.print(f"    [dim]•[/dim] {note}")
                console.print()

                updated = migration["migrate"](read_manifest())
                patch_manifest({"sdd_version": updated["sdd_version"]})
                console.print(f"  [green]✓[/green]  {MANIFEST_PATH} updated to v{migration['to']}")
                console.print()

            final_version = (read_manifest() or {}).get("sdd_version")
            if final_version != SDD_VERSION:
                console.print(
                    f"  [yellow]Now at v{final_version} — run [cyan]sdd upgrade[/cyan] again "
                    f"to continue to v{SDD_VERSION}.[/yellow]"
                )
                console.print()

            console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
            console.print("  [bold green]Upgrade complete![/bold green]")
            console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
            console.print()

    if sync_prompts:
        _do_sync_prompts(pack_override, yes)
