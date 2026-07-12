from pathlib import Path
import click
from rich.console import Console

from sdd.utils.manifest import read_manifest, patch_manifest, MANIFEST_PATH, SDD_VERSION

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
]


@click.command()
def upgrade_command():
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
        return

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
        return

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
