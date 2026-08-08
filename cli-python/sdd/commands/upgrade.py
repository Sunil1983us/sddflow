from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

import click
from rich.console import Console

from sdd.utils.manifest import MANIFEST_PATH, SDD_VERSION, patch_manifest, read_manifest
from sdd.utils.scaffold import (
    ALL_PACKS,
    TYPE_TO_PACK,
    UNIVERSAL_PACK,
    sync_pack_prompts,
)

console = Console()

# "from" is a reserved word, so this uses TypedDict's functional (string-key)
# form rather than class syntax -- the dict literals below use "from" as an
# ordinary string key, which is fine, just not as a Python identifier.
#
# No "migrate" field: every one of the 117 hops below has only ever stamped
# sdd_version (verified -- none has transformed manifest.yml content). Rather
# than hand-writing that identical lambda 117 times, _migrate_fn() below
# supplies it by default; _CUSTOM_MIGRATE exists for the rare future entry
# that genuinely needs to transform the manifest.
Migration = TypedDict(
    "Migration",
    {
        "from": "str | None",  # None only for the very first entry (pre-versioning)
        "to": str,
        "description": str,
        "notes": "list[str]",
    },
)

_CUSTOM_MIGRATE: dict[str, Callable[[dict], dict]] = {}


def _migrate_fn(to: str) -> Callable[[dict], dict]:
    custom = _CUSTOM_MIGRATE.get(to)
    if custom is not None:
        return custom
    return lambda m: {**m, "sdd_version": to}


# Version migration table — extend when releasing a new pack version.
MIGRATIONS: list[Migration] = [
    {
        "from": None,  # None = pre-versioning (no sdd_version field)
        "to": "2.0.0",
        "description": "Initial versioned release",
        "notes": [
            "Added sdd_version field to manifest.yml for upgrade tracking",
            "setup.sh/setup.ps1 rewritten — eliminates injection bugs",
            'Input validation: project/feature names with " are rejected early',
            "Detection order fix: mobile (react-native) now checked before fullstack",
            "Python CLI added alongside Node.js CLI (pip install sddflow)",
        ],
    },
    {
        "from": "2.0.0",
        "to": "2.7.0",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "/change command: type-aware change requests at any SDLC stage",
            "/jira-push: progressive Jira export (Epic/Story/Task/CHG)",
            "Review gates: three modes (chat / local / jira) — Jira now optional",
            "sdd review approve --local also updates the doc's Confluence page",
            "setup.sh/setup.ps1 safe in non-interactive runs (CI, piped input)",
            "Re-copy the pack (or run sdd init over it) to pick up new prompt files",
        ],
    },
    {
        "from": "2.7.0",
        "to": "2.7.1",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "/create-context: Endpoints and NFRs now get a proposed "
            "scope-appropriate starting default, marked "
            "(SUGGESTED DEFAULT — edit or confirm), instead of always "
            "falling back to [MISSING — ask user]",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .github/prompts/create-context.prompt.md",
        ],
    },
    {
        "from": "2.7.1",
        "to": "2.7.3",
        "description": "Version scheme unified — one number instead of two",
        "notes": [
            "sdd_version no longer tracks a separate content/schema "
            "counter — it now always matches the installed sddflow "
            "package version (sdd --version), so this file and the CLI "
            "never show two different numbers again",
            "No framework content changed in this step beyond the "
            "version scheme itself",
        ],
    },
    {
        "from": "2.7.3",
        "to": "2.7.4",
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
    },
    {
        "from": "2.7.4",
        "to": "2.7.5",
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
    },
    {
        "from": "2.7.5",
        "to": "2.7.6",
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
    },
    {
        "from": "2.7.6",
        "to": "2.7.7",
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
    },
    {
        "from": "2.7.7",
        "to": "2.7.8",
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
            'said plain "runbook.md" — corrected to '
            "docs/runbook/local-setup.md, matching what /implement "
            "actually generates in every pack",
            "Fixed: frontend-spa/mobile CLAUDE.md and HOW-TO-USE.md "
            'marked data-model as "full only" — corrected to mvp+, '
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
            'component-spec.md\'s "Shared Components Used" section '
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
    },
    {
        "from": "2.7.8",
        "to": "2.7.9",
        "description": "Content release — no manifest schema changes",
        "notes": [
            "/create-context gains a Feature Size Check (Step 1.5): "
            "before drafting context.md, it clusters the raw notes by "
            "actor+goal and flags it if 2+ independently-shippable "
            'capabilities were pasted in as one feature (e.g. "submit '
            'a payment" + "view a payments dashboard")',
            "If a split is found, the agent asks whether to treat it as "
            "one feature or build one slice at a time — on a split, the "
            "chosen slice's raw text continues through drafting as "
            "normal, and every other slice's raw notes are saved to its "
            "own .specify/contexts/{slug}.raw.md so nothing is lost and "
            "it can be picked up later with /create-context",
            "Re-copy the pack (or run sdd init over it) to pick up the "
            "updated .github/prompts/create-context.prompt.md",
        ],
    },
    {
        "from": "2.7.9",
        "to": "2.7.10",
        "description": "Bug fix — /change living-document handling, no manifest schema changes",
        "notes": [
            "Fixed: /change's Stage Detection scanned only "
            ".specify/features/{feature}/ for every document, but "
            "context.md (.specify/contexts/) and data-model.md/"
            "security-design.md/api-spec.md/component-library.md "
            "(.specify/service/, living since 2.7.6) never lived there — "
            'a CR could report all four as "not yet created" even when '
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
    },
    {
        "from": "2.7.10",
        "to": "2.7.11",
        "description": "Multi-feature safety fixes for sdd jira push and sdd confluence push, plus /change --feature override, no manifest schema changes",
        "notes": [
            'Fixed: LIVING_SERVICE_DOCS was missing "component-library" '
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
            'Added: /change --feature {slug} "description" — targets a '
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
    },
    {
        "from": "2.7.11",
        "to": "2.7.12",
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
    },
    {
        "from": "2.7.12",
        "to": "2.7.13",
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
    },
    {
        "from": "2.7.13",
        "to": "2.7.14",
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
    },
    {
        "from": "2.7.14",
        "to": "2.7.15",
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
    },
    {
        "from": "2.7.15",
        "to": "2.7.16",
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
    },
    {
        "from": "2.7.16",
        "to": "2.7.17",
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
    },
    {
        "from": "2.7.17",
        "to": "2.7.18",
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
    },
    {
        "from": "2.7.18",
        "to": "2.7.19",
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
    },
    {
        "from": "2.7.19",
        "to": "2.7.20",
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
    },
    {
        "from": "2.7.20",
        "to": "2.7.21",
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
    },
    {
        "from": "2.7.21",
        "to": "2.7.22",
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
    },
    {
        "from": "2.7.22",
        "to": "2.7.23",
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
    },
    {
        "from": "2.7.23",
        "to": "2.7.24",
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
    },
    {
        "from": "2.7.24",
        "to": "2.7.25",
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
            '"parent" field team-managed projects use',
            "All five call sites now print a warning naming the child/"
            "parent keys, the underlying error, and a pointer to `sdd "
            "config fields --project {key}` to find the right Epic Link "
            "field ID for parent_field in integrations.yml -- still never "
            "blocks the push/submit itself, just makes the failure visible",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
    },
    {
        "from": "2.7.25",
        "to": "2.7.26",
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
    },
    {
        "from": "2.7.26",
        "to": "2.7.27",
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
    },
    {
        "from": "2.7.27",
        "to": "2.7.28",
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
    },
    {
        "from": "2.7.28",
        "to": "2.7.29",
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
    },
    {
        "from": "2.7.29",
        "to": "2.7.30",
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
    },
    {
        "from": "2.7.30",
        "to": "2.7.31",
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
    },
    {
        "from": "2.7.31",
        "to": "2.7.32",
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
    },
    {
        "from": "2.7.32",
        "to": "2.7.33",
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
    },
    {
        "from": "2.7.33",
        "to": "2.7.34",
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
    },
    {
        "from": "2.7.34",
        "to": "2.7.35",
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
    },
    {
        "from": "2.7.35",
        "to": "2.7.36",
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
            'reference shape (ac:adf-node type="extension" with a '
            "dynamically-obtained local-id, confirmed via research, not "
            'the same simple ac:structured-macro ac:name="..." shape '
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
    },
    {
        "from": "2.7.36",
        "to": "2.7.37",
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
            'on flowchart stadium-shape nodes (Actor(["User"]), used '
            "in every design/hld/arch template's Actor node) and on "
            "classDiagram entirely. mmdr (Rust-based, ~18MB, zero "
            "further Python dependencies) rendered all four correctly, "
            "confirmed both textually and via visual PNG inspection",
            "mmdr is an optional dependency, not a hard one -- new "
            "[project.optional-dependencies].diagrams extra in "
            "pyproject.toml, installed with pip install "
            '"sddflow[diagrams]", imported lazily only when '
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
    },
    {
        "from": "2.7.37",
        "to": "2.7.38",
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
            '\'Or just say: "Maya, write the use cases for checkout" '
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
    },
    {
        "from": "2.7.38",
        "to": "2.7.39",
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
    },
    {
        "from": "2.7.39",
        "to": "2.7.40",
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
    },
    {
        "from": "2.7.40",
        "to": "2.7.41",
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
    },
    {
        "from": "2.7.41",
        "to": "2.7.42",
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
    },
    {
        "from": "2.7.42",
        "to": "2.7.43",
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
    },
    {
        "from": "2.7.43",
        "to": "2.7.44",
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
    },
    {
        "from": "2.7.44",
        "to": "2.7.45",
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
            'a JSON {"error": ...} with status 500 instead of a bare '
            "connection reset (which was crashing the whole request, not "
            "just this endpoint); the frontend's 5s poll loop catches "
            "fetch/parse failures and shows a visible error banner "
            "instead of silently freezing on stale data",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
    },
    {
        "from": "2.7.45",
        "to": "2.7.46",
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
    },
    {
        "from": "2.7.46",
        "to": "2.7.47",
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
    },
    {
        "from": "2.7.47",
        "to": "2.7.48",
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
    },
    {
        "from": "2.7.48",
        "to": "2.7.49",
        "description": "Fix: a Confluence diagram fence whose *configured* rendering mode failed (missing mmdr package, invalid diagram source, or an app macro mode with no macro name set) silently fell back to a plain code block with zero indication anything was wrong -- now prints a warning naming the reason -- no manifest schema changes",
        "notes": [
            "User-reported: set diagrams.mode: local-svg in "
            "integrations.yml, re-pushed a Use Cases page with a Mermaid "
            "relationship diagram, and the diagram still showed as plain "
            "text instead of an image -- with no error or warning "
            "anywhere to explain why",
            "Root cause: md_to_cf.py's _render_local_svg() caught every "
            "renderer exception (including the common case -- `pip "
            'install "sddflow[diagrams]"` never having been run, so '
            "the optional mmdr package isn't installed) and discarded "
            "the reason, falling back to a plain code block silently. A "
            "real, fixable failure was indistinguishable from "
            "diagrams.mode simply not being configured at all",
            "md_to_storage()'s return type changed (again) from "
            "tuple[str, list[Attachment]] to tuple[str, list[Attachment], "
            "list[str]] -- the third element is one human-readable "
            "warning per diagram fence whose *configured* mode failed to "
            'render (never populated when diagrams.mode is "none", '
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
    },
    {
        "from": "2.7.49",
        "to": "2.7.50",
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
    },
    {
        "from": "2.7.50",
        "to": "2.7.51",
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
    },
    {
        "from": "2.7.51",
        "to": "2.7.52",
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
    },
    {
        "from": "2.7.52",
        "to": "2.7.53",
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
    },
    {
        "from": "2.7.53",
        "to": "2.7.54",
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
    },
    {
        "from": "2.7.54",
        "to": "2.7.55",
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
            'via a live grep -o "NEEDS CLARIFICATION-[0-9]*" against '
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
    },
    {
        "from": "2.7.55",
        "to": "2.7.56",
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
    },
    {
        "from": "2.7.56",
        "to": "2.7.57",
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
    },
    {
        "from": "2.7.57",
        "to": "2.7.58",
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
    },
    {
        "from": "2.7.58",
        "to": "2.7.59",
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
    },
    {
        "from": "2.7.59",
        "to": "2.7.60",
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
    },
    {
        "from": "2.7.60",
        "to": "2.7.61",
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
    },
    {
        "from": "2.7.61",
        "to": "2.7.62",
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
    },
    {
        "from": "2.7.62",
        "to": "2.7.63",
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
    },
    {
        "from": "2.7.63",
        "to": "2.7.64",
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
            '_render_local_svg() now emits <ac:image ac:width="{width}">'
            " -- Confluence scales height to match, preserving aspect "
            "ratio",
            "integrations.yml.example (all 5 packs) documents the new "
            "local_svg.width option in place of the old placeholder "
            "'no options today' comment",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
    },
    {
        "from": "2.7.64",
        "to": "2.7.65",
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
    },
    {
        "from": "2.7.65",
        "to": "2.7.66",
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
    },
    {
        "from": "2.7.66",
        "to": "2.7.67",
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
    },
    {
        "from": "2.7.67",
        "to": "2.7.68",
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
    },
    {
        "from": "2.7.68",
        "to": "2.7.69",
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
    },
    {
        "from": "2.7.69",
        "to": "2.7.70",
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
    },
    {
        "from": "2.7.70",
        "to": "2.7.71",
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
    },
    {
        "from": "2.7.71",
        "to": "2.7.72",
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
            'text still said \'"View" reads the raw .md file from '
            "disk' -- a leftover from before the View/Approvals/"
            "Comments toggles were consolidated into one Details panel "
            "with tabs (2.7.71). Updated to reference the Details "
            "button's Content tab instead",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
    },
    {
        "from": "2.7.72",
        "to": "2.7.73",
        "description": "Fix: sdd dashboard's Approve pill could keep showing a stale approver's name after a document was regenerated back to Draft",
        "notes": [
            "Flagged during the previous UX review as a known, pre-"
            "existing (not introduced that round) edge case, then the "
            "user asked how to fix it -- so it's fixed now",
            "approvalMode() and approvedRowInfo() (dashboard.py) "
            "previously trusted d.local_approval unconditionally: once "
            "`sdd review approve --local` (or the dashboard's own "
            "Approve button) wrote a record for a doc key, the Approve "
            "pill kept showing that approver's name even after the "
            "document was regenerated back to Draft -- "
            ".local-approvals.yml isn't cleared just because a doc's "
            "content changed, so the record can outlive the approval it "
            "recorded",
            "Both functions now check the document's live Status: "
            "header first -- the same authoritative-source rule "
            "badge(d.status, 'doc') already follows, and the same one "
            "CLAUDE.md documents as the gate in every review mode. Only "
            "once the header actually says Approved do they consult "
            "local_approval / the Jira review status / the doc's own "
            "Approvals table to find out who",
            "Verified live: a doc with a stale local_approval record but "
            "Status: Draft now shows the Approve button (not the old "
            "checkmark), and its Approvals tab correctly says 'Not yet "
            "approved' instead of 'Recorded via: Local'",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
    },
    {
        "from": "2.7.73",
        "to": "2.7.74",
        "description": "Enhance: sdd dashboard now shows live Jira ticket status (not just links) for both review-gate tickets and Jira Export Epic/Story/Task tickets",
        "notes": [
            "User asked directly: 'do we show the Jira status also?' -- "
            "investigation found the raw Jira status was already fetched "
            "but unused for review-gate tickets, and never fetched at "
            "all for Export tickets. User chose to close both gaps",
            "linkPill() now shows the review-gate ticket's raw Jira "
            "workflow status (e.g. 'In Review') as a suffix next to the "
            "pill, alongside (not merged with) SDD's own APPROVED/"
            "PENDING/NEEDS_REVISION review_status badge -- the two are "
            "legitimately different concepts shown side by side",
            "New _fetch_export_ticket_statuses() reads Epic/Story/Task "
            "keys from docs/jira/{feature}/keys.yml and resolves their "
            "live status with a single batched JQL 'key in (...)' query "
            "instead of one lookup per ticket",
            "Jira keys from keys.yml are validated against "
            "_JIRA_KEY_RE before being interpolated into the JQL string "
            "-- keys normally come from Jira's own API but the file is "
            "user-editable on disk, and JQL has no parameterized-query "
            "binding",
            "_fetch_review_links()'s guard relaxed from requiring "
            "document_reviews to be configured to requiring only jira: "
            "or confluence: -- a project using Jira solely for "
            "progressive export (no document review gates) can now "
            "still use the status check",
            "The '\U0001f504 Check Jira/Confluence review links' button "
            "renamed to '\U0001f504 Check Jira/Confluence status' since "
            "it now refreshes ticket status too, reusing the existing "
            "on-demand + 5-minute auto-refresh mechanism rather than "
            "adding a second control",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
    },
    {
        "from": "2.7.74",
        "to": "2.7.75",
        "description": "Fix: sdd_parser.py never matched the actual shipped stories.md/tasks.md templates -- sdd jira push and sdd pr create --task silently found zero stories/tasks for every real generated feature",
        "notes": [
            "Found while helping a user debug why 'sdd jira push' created "
            "nothing even after fixing Jira/Confluence credentials -- "
            "traced it to sdd_parser.py's regexes expecting a heading/"
            "field format ('### STORY-NNN — Title' em-dash, "
            "'**As a**'/'**Satisfies:**' bold fields, '## TASK-NNN' H2) "
            "that the shipped feature-story-template.md/tasks-template.md "
            "have not used for some time (they use '### STORY-NNN: "
            "Title' colon, '**As**'/'**Linked FRs:**' for stories, and "
            "'### TASK-NNN' H3 with entirely plain/unbolded fields for "
            "tasks) -- parse_stories()/parse_tasks() returned an empty "
            "list for every correctly-generated document",
            "This silently broke 'sdd jira push --level story/task' "
            "(reported 'No stories or tasks found') and 'sdd pr create "
            "--task TASK-NNN' (reported 'TASK-NNN not found in "
            "tasks.md') for every project using the current templates "
            "-- both are on the framework's golden path",
            "sdd_parser.py rewritten to match the current templates "
            "while still accepting the older em-dash/bold-field style "
            "found in this repo's own worked examples, so already-"
            "generated docs in either style parse correctly",
            "Also fixed: _normalize_moscow() required an exact 'must "
            "have' string match, but the shipped template's bucket "
            "headers are 'Must Have Stories' (trailing word) -- every "
            "story silently fell through to the could-have default, "
            "mapping every Jira Story to Low priority regardless of "
            "its actual MoSCoW bucket",
            "New golden-template tests parse the actual shipped "
            "feature-story-template.md/tasks-template.md files directly "
            "(not just hand-written fixtures) so a future template edit "
            "that breaks the parser fails CI instead of shipping silently "
            "broken again",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
    },
    {
        "from": "2.7.75",
        "to": "2.7.76",
        "description": "Fix: /release and /implement's runbook never went through Jira/Confluence review despite document_reviews.runbook/.release being fully documented and configurable",
        "notes": [
            "Prompted by a user asking for a full audit of every pipeline "
            "step's Jira/Confluence coverage, after the sdd_parser.py fix "
            "above -- release.prompt.md had ZERO Jira/Confluence wiring "
            "for release.md (only an informal chat sign-off), and "
            "implement.prompt.md never submitted the runbook "
            "(docs/runbook/local-setup.md) for review at all -- not even "
            "chat-mode approval -- despite CLAUDE.md's own Jira-mode "
            "sequence table documenting 'release phase: Runbook -> "
            "Release, reviewer: DevOps -> Release Manager' and the "
            "shipped integrations.yml.example already configuring both "
            "document_reviews.runbook and .release with sequence numbers",
            "Backend bug found in the same sweep: resolve_doc_path() had "
            "no case for 'runbook' -- 'sdd review submit --doc runbook' "
            "would have resolved to the nonexistent "
            ".specify/features/{feature}/runbook.md instead of the real "
            "docs/runbook/local-setup.md, and confluence.py's page-"
            "nesting/title logic didn't treat 'runbook' as project-"
            "scoped (living) the way data-model/security-design/api-spec/"
            "constitution already are -- new PROJECT_SCOPED_DOCS constant "
            "in validate.py fixes both",
            "release.prompt.md and implement.prompt.md now submit "
            "release.md/runbook.md through the same Submit-for-Review + "
            "review-decision-step flow every other document uses, across "
            "all 5 packs",
            "integrations.yml.example's page_map.release entry was also "
            "commented out by default even though document_reviews.release "
            "was already active -- a user copying the example as-is would "
            "have hit a missing-page_map-entry error the first time this "
            "new wiring ran; uncommented to match runbook's existing "
            "active entry",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
    },
    {
        "from": "2.7.76",
        "to": "2.7.77",
        "description": "Fix: self-approval risk undocumented, coverage gate was a bare echo, no test caught either -- verified all three with grep before fixing, per external review of the sdd_parser.py/release.md audit",
        "notes": [
            "An external agent reviewed the two prior fixes (sdd_parser.py, "
            "release.md/runbook wiring) and raised several concerns. "
            "Re-checked every claim with grep/read against the actual "
            "repo instead of accepting either the review's or this "
            "agent's own prior assessment on faith -- some held up, some "
            "didn't (e.g. the review's '245 tests' figure was stale; "
            "actual count was 592 at the time). Three confirmed, real "
            "gaps were fixed",
            "review-gates.md now explicitly states the self-approval "
            "risk in chat mode: nothing stops the same conversation that "
            "drafted a document from also being the one that approves "
            "it -- no independent reviewer identity check exists. This "
            "was previously only implicit in the scope-based mode "
            "guidance",
            "quality-gate.yml's 'Enforce coverage gate' step was a bare "
            "`echo` in every pack (confirmed by reading the actual "
            "workflow file) -- it always printed a success-sounding "
            "message regardless of whether coverage was configured at "
            "all. Replaced with a real tripwire: the step now greps "
            "pom.xml for jacoco-maven-plugin's <rules> block (Java packs) "
            "or vitest/jest config for coverageThreshold/thresholds (Node "
            "packs), and fails the CI job with actionable guidance if "
            "the configuration is missing -- across all 5 packs, "
            "including fullstack's separate backend+frontend jobs",
            "New test_prompt_review_coverage.py: for every doc key with "
            "an active document_reviews entry in the shipped "
            "integrations.yml.example, asserts the owning .prompt.md "
            "file actually contains a 'sdd review submit --doc {key}' "
            "call, across all 5 packs (56 cases). This is the cheap, "
            "buildable version of 'run the pipeline against a mocked "
            "Jira/Confluence' -- prompts are AI instructions, not "
            "executable code, so a structural presence check is what's "
            "actually feasible in CI. Verified by temporarily reverting "
            "release.prompt.md to its pre-fix state and confirming the "
            "new test fails exactly where the real bug was, then passes "
            "again once restored",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
    },
    {
        "from": "2.7.77",
        "to": "2.7.78",
        "description": "Fix: sdd-universal missing UI templates, brd-template.md drift, design-template.md numbering gap -- template quality review found real gaps beyond docs/CI",
        "notes": [
            "sdd-universal was missing ux-flow-template.md, "
            "screen-spec-template.md, component-spec-template.md, and "
            "component-library-template.md even though its own "
            "specify-doc.prompt.md documents /specify-doc "
            "component-spec|ux-flow|screen-spec as valid commands and "
            "reads .specify/templates/{doc}-template.md directly -- a "
            "broken reference for exactly the mobile/frontend project "
            "types sdd-universal auto-detects. Added all four",
            "ux-flow-template.md, screen-spec-template.md, and "
            "component-spec-template.md had no ID scheme or Version "
            "History table, unlike every other template in the system. "
            "Added FLOW/ERR/EDGE-NNN, SCR-NNN, and COMP-NNN respectively, "
            "plus Version History to all three. Enrolled into "
            "_shared/full/ since they were already byte-identical across "
            "every pack that ships them",
            "brd-template.md had drifted uncoordinated: sdd-universal's "
            "copy had a Section 9 Investment Summary and domain-aware "
            "regulation pre-seeding (PCI/HIPAA/GDPR) the other four packs "
            "(byte-identical to each other) never received. Unlike "
            "api-spec/data-model/security-design/runbook -- which "
            "legitimately vary by project type -- BRD content has no "
            "such reason to differ. Enrolled into _shared/full/ using "
            "sdd-universal's fuller version as canonical",
            "design-template.md Section 3 skipped from 3.2 to 3.5 with "
            "no 3.3/3.4 content anywhere in the file -- renumbered to "
            "3.3",
            "Known gaps NOT fixed in this pass: sdd-universal's "
            "specify-doc.prompt.md has no project-type branching for "
            "which flavor of data-model/security-design template to use "
            "(a detected frontend/mobile project would get the "
            "DB-schema/server-side flavor); sdd-universal's api-spec, "
            "data-model, runbook, and openapi templates are each missing "
            "content sdd-backend-service's same-flavor copies already "
            "have; security-design-template.md has a structural (not "
            "content) mismatch between backend and universal",
            "This migration only bumps sdd_version -- no manifest.yml "
            "field changes for any pack",
        ],
    },
    {
        "from": "2.7.78",
        "to": "2.7.79",
        "description": "Fix: runbook-template.md missing living-doc framing in 4 packs, security-design/data-model/api-spec inconsistencies across packs, release-template.md pilot-scope broken rollback reference, sdd-universal had no project-type flavor branching for data-model/security/runbook",
        "notes": [
            "runbook-template.md was missing its 'Living artifact' framing "
            "paragraph and used '# Feature: {Feature Name}' instead of "
            "'# Service:'/'# App:' in frontend-spa, mobile, fullstack, and "
            "sdd-universal (only sdd-backend-service had it correct) -- an "
            "agent following the template literally would treat the "
            "runbook as a fresh per-feature doc instead of extending the "
            "living one, silently dropping a prior feature's additions. "
            "Fixed all four",
            "security-design-template.md was inconsistent across packs: "
            "only sdd-backend-service had a Version History table; only "
            "sdd-universal had the CVSS scoring column and the 2-row "
            "Security Officer/Tech Lead Approvals table. Reconciled all "
            "five packs to have all three",
            "data-model-template.md and api-spec-template.md were missing "
            "Version History tables in sdd-universal (both docs) and "
            "sdd-fullstack (api-spec only). Added. Also fixed "
            "sdd-universal's api-spec-template.md References row, which "
            "cited 'arch.summary.md ... ports/adapters' -- leftover text "
            "that didn't match how api-spec.md is actually fed (per "
            "plan-design.prompt.md Section 3: design.summary.md, which "
            "feature added/changed which endpoints)",
            "release-template.md Section 7 Rollback Plan pointed to "
            "docs/runbook/local-setup.md in sdd-backend-service, "
            "frontend-spa, mobile, and fullstack even at pilot scope, "
            "where the runbook is never generated -- a broken reference. "
            "Backported sdd-universal's pilot-scope fallback rollback "
            "table (already correct there) to all four packs, plus two "
            "extra Post-Deploy Smoke Test monitoring rows sdd-universal "
            "already had",
            "sdd-universal's specify-doc.prompt.md read one single "
            "template flavor for data-model and security-design "
            "regardless of detected project_type -- a frontend-spa or "
            "mobile project would get the DB-schema/server-side flavor "
            "instead of state/storage-model or local-cache-model content. "
            "Added project_type branching (frontend-spa/desktop -> "
            "*-template-frontend.md, mobile -> *-template-mobile.md, "
            "else -> default) to the shared specify-doc.prompt.md source "
            "(safe no-op for the other four packs, which have no "
            "project_type field) and shipped the new frontend/mobile "
            "flavor template files for sdd-universal. Same fix applied to "
            "runbook generation in implement.prompt.md",
            "Verified: sync-blocks.sh clean, cli-python pytest 648/648, "
            "assert-output.sh 33/33 on both worked examples, setup smoke "
            "tests 15/15",
        ],
    },
    {
        "from": "2.7.79",
        "to": "2.7.80",
        "description": "Fix: data-model-template.md missing Version History in frontend-spa/mobile/fullstack, security-design-template.md STRIDE column wording inconsistency in sdd-universal -- found while verifying the v2.7.79 fix batch's own consistency",
        "notes": [
            "data-model-template.md was missing '## Version History' in "
            "sdd-frontend-spa, sdd-mobile, and sdd-fullstack -- only "
            "sdd-backend-service and (as of 2.7.79) sdd-universal had it. "
            "Found because sdd-universal's new data-model-template-frontend.md/"
            "-mobile.md flavor files (copied verbatim from those packs' own "
            "templates) diffed non-empty against their source -- the "
            "source packs were the ones missing content, not the copies. "
            "Added Version History to all three",
            "security-design-template.md's STRIDE threat table column was "
            "'Threat (STRIDE)' in sdd-universal but 'Threat (STRIDE "
            "category)' in the other four packs -- pre-existing wording "
            "drift, not something the 2.7.79 CVSS-column fix introduced. "
            "Normalized sdd-universal to match",
            "Verified: sync-blocks.sh clean, cli-python pytest 648/648, "
            "assert-output.sh 33/33",
        ],
    },
    {
        "from": "2.7.80",
        "to": "2.7.81",
        "description": "Fix: sdd-micro/setup.sh had zero test coverage -- test-setup.sh only ever tested sdd-universal's setup.sh (hardcoded PACK_DIR); no manifest.yml field changes for any pack, including sdd-micro (this is a CI/test-harness fix, not a pack-content change)",
        "notes": [
            "Found while reviewing sdd-micro end-to-end: "
            "packs/_shared/tests/test-setup.sh's own header says 'Smoke "
            "tests for sdd-universal/setup.sh' and hardcodes "
            "PACK_DIR=packs/sdd-universal -- sdd-micro/setup.sh (a "
            "materially different script: --project/--feature only, no "
            "--type/--scope, its own non-interactive default fallback to "
            "'untitled-project'/'main') was never exercised by CI despite "
            "root CLAUDE.md describing the smoke-test suite as covering "
            "'injection-class names, all project types, and "
            "non-interactive execution' in a way that read as a blanket "
            "guarantee",
            "Added packs/_shared/tests/test-setup-micro.sh, mirroring "
            "test-setup.sh's ok()/nok() structure and covering the same "
            "injection classes (quotes, backslash, ampersand, slash, "
            "unicode) plus two cases specific to this script: the "
            "no-args non-interactive default path, and the 'unknown "
            "option' rejection (sdd-micro's setup.sh has no --type flag, "
            "unlike sdd-universal's)",
            "Wired into .github/workflows/ci.yml's existing "
            "setup-smoke-tests job as a second step, and documented in "
            "root CLAUDE.md's Testing Setup Scripts section",
            "Verified the new test actually has teeth: temporarily "
            "disabled sdd-micro/setup.sh's double-quote validation guard, "
            "confirmed the 2 double-quote-rejection cases failed as "
            "expected (exit 1), then restored the original file (git "
            "diff clean) and re-ran clean (12/12)",
            "Deliberately kept sdd-micro's own manifest.yml sdd_version "
            "untouched (still 2.7.41) -- this fix only adds test/CI "
            "infrastructure in this repo, it does not change any file "
            "sdd-micro itself ships to a user's project via `sdd init "
            "--pack sdd-micro`",
        ],
    },
    {
        "from": "2.7.81",
        "to": "2.7.82",
        "description": "Feature: Business Objectives traceability + dashboard rollup -- brd.md's Business Objectives (§2) and Business Requirements (§5) were previously unlinked siblings; adds a 'Serves BO' column to §5 and rolls BO -> BR -> FR -> TASK up into a per-feature and cross-feature Business Objectives view in `sdd dashboard`",
        "notes": [
            "Added 'Serves BO' column to brd-template.md's §5 Business "
            "Requirements table (all 5 non-micro packs) -- every BR-NNN "
            "must now cite which BO-NNN from §2 it serves. Updated "
            "specify-brd.prompt.md with fill instructions",
            "Added status.py parsers: _parse_brd_bo (brd.md §2/§5, "
            "tolerant of 3- or 4-column Business Objectives tables and "
            "legacy 'Satisfies' column headers), _parse_uc_traces "
            "(use-cases.md Use Case Index table, falls back to scanning "
            "narrative '### UC-NNN' sections' '**Trace:**'/'**BR "
            "Traces:**' lines when no Index table exists), _parse_srd_fr "
            "(srd.md Functional Requirements table, tolerant of the "
            "5-column canonical shape and a 4-column 'Satisfies' "
            "variant, plus §4 Use Case Coverage as a UC-link fallback)",
            "Added build_bo_rollup(): chains BO -> BR (brd.md 'Serves "
            "BO') -> FR (srd.md 'Source'/'Satisfies', the reliable "
            "bridge since use-cases.md's FR Traces column is only "
            "backfilled by a manual /specify-srd re-run and is often "
            "skipped in practice) -> TASK (tasks.md 'Satisfies:' field + "
            "completion status). UC-NNN is gathered from both "
            "use-cases.md and srd.md for display, but status/percent-done "
            "is computed from the BR->FR->TASK bridge only",
            "Wired into build_feature_status() (per-feature "
            "'business_objectives' key) and build_project_status() (flat "
            "cross-feature 'business_objectives' list, each row tagged "
            "with its feature name -- BO-NNN numbering is local to each "
            "feature's brd.md, same as the existing Actor Registry "
            "pattern)",
            "Added a 'Business Objectives' card to `sdd dashboard`: a "
            "cross-feature rollup card (BO, Objective, Feature, Use "
            "Cases, Status, Progress) shown above the per-feature blocks, "
            "plus a per-feature card in each feature's block",
            "Status computed by task completion percentage (0 done -> "
            "Not Started, some done or in-progress -> In Progress, all "
            "done -> Done), not release.md's BO closure field -- picked "
            "so the dashboard reflects live task state rather than a "
            "field only updated at /release time",
            "Verified end-to-end against examples/todo-api's real "
            "brd.md/use-cases.md/srd.md/tasks.md (which deviate from the "
            "raw templates in exactly the ways the tolerant parsing "
            "above accounts for) via the dashboard's live HTTP server, "
            "screenshotted in both light and dark mode",
            "Added 20 pytest cases covering 3-vs-4-column BO tables, "
            "legacy 'Satisfies' headers, unfilled template placeholders, "
            "the Use Case Index fallback, orphaned BRs, and the flattened "
            "cross-feature rollup",
            "Verified: sync-blocks.sh clean, cli-python pytest 664/664",
        ],
    },
    {
        "from": "2.7.82",
        "to": "2.7.83",
        "description": "Fix: `sdd config init`'s .specify/integrations.yml scaffold was built from a small hand-maintained template string in config.py that had drifted far behind the real integrations.yml.example -- missing project_keys, parent_field_by_level, custom_fields_by_level, diagrams, document_reviews, pr_automation, and code_review entirely, plus most of page_map",
        "notes": [
            "Reported directly: 'while creating integration file, it "
            "does not fill the full information ... we have made many "
            "changes to integrations.yml file'. Confirmed: "
            "_integrations_template() in cli-python/sdd/commands/"
            "config.py only ever produced profile + a 9-key page_map + "
            "jira.custom_fields.story_points -- every section added to "
            "integrations.yml.example over the life of this project "
            "(project_keys, parent_field_by_level, "
            "custom_fields_by_level, diagrams, document_reviews, "
            "pr_automation, code_review) was never ported into the "
            "wizard's own template, so a user running `sdd config init` "
            "got a materially smaller file than what the pack actually "
            "supports, with no indication anything was missing",
            "Root cause: two independent sources of truth for the same "
            "file shape (a Python string vs. the shipped .example) that "
            "nothing enforced staying in sync -- every feature added "
            "sections to integrations.yml.example and none to "
            "config.py's template, since there is no automated diff "
            "between the two",
            "Fix: `sdd config init` now fills profile/project_key/"
            "space_key/parent_page_id into the project's own shipped "
            "`.specify/integrations.yml.example` (present in every "
            "project since `sdd init`) instead of a separate template "
            "string -- every section the current pack version documents "
            "is present in the scaffolded file, most left commented out "
            "exactly as the .example ships them. Falls back to the old "
            "minimal built-in template only if no .example file exists "
            "in the project (very old init, or a pack without one, e.g. "
            "sdd-micro)",
            "document_reviews: carries the example's placeholder Jira "
            "accountIds verbatim (same as the .example itself ships) -- "
            "the wizard now prints an explicit warning telling the user "
            "to replace them with real reviewers, or delete entries they "
            "don't want routed through Jira, before `sdd review submit`",
            "{feature}/{project} template variables in page_map are "
            "runtime substitutions (filled by _push_doc_page at push "
            "time) and are deliberately left untouched by the new "
            "substitution logic -- only the four wizard-collected values "
            "are replaced",
            "This Node CLI does not implement `sdd config init` -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "This migration only bumps sdd_version — no manifest.yml "
            "field changes for any pack",
            "Added 6 pytest cases: placeholder substitution, every "
            "optional section present, blank parent_page_id stays "
            "commented, {feature}/{project} vars untouched, and two "
            "CliRunner end-to-end tests (example present / absent)",
            "Verified: cli-python pytest 670/670",
        ],
    },
    {
        "from": "2.7.83",
        "to": "2.7.84",
        "description": "Docs: HOW-TO-USE.md's 'Phase 0 -- Setup (before any command)' section listed /create-context and sdd init/setup.sh but never mentioned sdd config init/sdd config test at all -- a reader following that section top to bottom for the full pre-flight checklist would not discover Jira/Confluence setup exists until a much later, unrelated section mentioned it in passing",
        "notes": [
            "Asked directly, after the v2.7.83 config-init fix: 'is that "
            "all document in how to use?' -- confirmed no. Phase 0 only "
            "covered /create-context and sdd init/setup.sh; sdd config "
            "init and sdd config test were documented elsewhere in the "
            "same file (their own reference entries, cross-referenced "
            "only from unrelated later sections like Document Review "
            "Gates), never listed as part of the sequential pre-flight "
            "checklist itself",
            "Added a new '#### Jira/Confluence integration -- sdd config "
            "init (optional)' subsection immediately after the existing "
            "sdd init/setup.sh subsection in Phase 0, in all 5 non-micro "
            "packs' HOW-TO-USE.md -- states it's optional and skippable "
            "for chat-mode approvals, shows sdd config init + sdd config "
            "test, and notes it can be run at any point later, not just "
            "at this step",
            "sdd-micro intentionally excluded (no Jira/Confluence "
            "integration in that pack, not part of the shared-block sync "
            "system)",
            "Docs-only change -- no manifest.yml field changes, no CLI behavior change",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Verified: cli-python pytest 670/670 (unaffected, docs-only)",
        ],
    },
    {
        "from": "2.7.84",
        "to": "2.7.85",
        "description": "Fix batch: full template/parser audit found tasks.md checkboxes never flipped by /implement (silently neutering the BO rollup dashboard), CHG-NNN tasks invisible to the task-heading regex, validate.prompt.md's own step numbering colliding with its template, security-design.md mixing CVSS scoring into a doc that always intended DREAD, CF-NNN consistency findings never reaching clarify.md's gate, and release.md's BO Closure/qa-testcases.md's UAT-relevant rows never feeding back into anything downstream",
        "notes": [
            "Tier 1 (7 fixes): (1) implement.prompt.md now instructs "
            "flipping tasks.md's own acceptance-criteria checkboxes from "
            "[ ] to [x], not just reporting completion in chat -- "
            "'sdd dashboard' counts checked boxes, an unflipped box read "
            "as not-done no matter what shipped; (2) status.py's and "
            "sdd_parser.py's _TASK_HEADING_RE widened to accept "
            "TASK-NNN|PERF-NNN|CHG-NNN (status.py was missing PERF-NNN "
            "entirely -- a latent inconsistency between the two regex "
            "locations found mid-fix), plus change.prompt.md's CHG-NNN "
            "generation template rewritten to an actual ### heading block "
            "matching tasks-template.md's shape (it previously had no "
            "markdown heading at all, so the regex widening alone would "
            "have been a no-op); (3) validate.prompt.md's blocking '3a. "
            "NEEDS CLARIFICATION SCAN' step renumbered to '0a' (it "
            "collided with the template's real '§3a Use Case Business "
            "Review' section) and validate-template.md gained the "
            "missing '## 0a. Needs Clarification Scan' table; (4) "
            "use-cases-template.md gained an Independent Test field per "
            "UC (specify-uc.prompt.md updated to fill it); (5) "
            "security-design-template.md's Threat Model reconciled to "
            "DREAD scoring everywhere (was mixing in CVSS with a "
            "mismatched /release gate) with the STRIDE section correctly "
            "scoped to mvp+, plus a new OWASP Top 10 Controls Mapping "
            "table (mobile's existing OWASP MASVS table moved into scope "
            "instead of duplicated); (6) CF-NNN (Consistency Findings) "
            "from analyze.md's own CRITICAL severity gate now actually "
            "reach clarify.md -- new template section, clarify.prompt.md "
            "instruction, and review.py's _CLARIFY_ITEM_CODE regex "
            "widened to recognize the CF prefix; (7) "
            "constitution-amendment-template.md (previously entirely "
            "dead -- referenced only as 'the save location', nothing "
            "ever generated it) wired into every pack's /specify GATE-1 "
            "re-run flow, saving CA-{NNN}.md amendment records",
            "Tier 2 (4 fixes): (1) release.md's §6 Business Objective "
            "Closure 'Met?' checkbox widened from Yes/Pending to "
            "Yes/No/Pending (there was previously no way to record a "
            "missed objective at all), and status.py gained "
            "_parse_release_bo_closure() wired into build_bo_rollup() as "
            "new 'outcome'/'measured_result' fields alongside (not "
            "replacing) the existing task-completion-derived 'status' -- "
            "surfaced in sdd dashboard's Business Objectives table as a "
            "new Business Outcome column; (2) release.prompt.md's UAT "
            "Plan step now pairs each UC-NNN row with the TC-NNN(s) that "
            "actually exercise it (qa-testcases.md's UAT Relevant: Yes "
            "rows at mvp+, smoke-tests.md's TC-S-NNN at pilot) instead of "
            "restating the UC with no test-case traceability at all -- "
            "release-template.md's UAT Plan table gained a TC-NNN column "
            "in all 5 packs; (3) jira-export-template.md's manual-import "
            "CSV gained a TC Reference column (Task rows only) so the "
            "CSV fallback path doesn't silently drop qa-testcases.md "
            "traceability the way it already carries FR/UC references; "
            "(4) jira.py's parse_changeset() was silently dropping the "
            "PR and Status columns from changesets/{CR}.md's §4 table -- "
            "rewritten to a tolerant per-line cell parser that captures "
            "both (defaulting to None for older 4-column rows) and "
            "surfaces them in the CHG Jira issue's description",
            "New pytest coverage for every fix: task-heading PERF/CHG "
            "counting, CF-NNN parse/patch round-trip, "
            "_parse_release_bo_closure (met/not_met/pending/unfilled-"
            "placeholder), build_bo_rollup outcome wiring, and "
            "parse_changeset's PR/Status/legacy-4-column/placeholder-row "
            "handling",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Verified: cli-python pytest 682/682, assert-output.sh clean "
            "on both worked examples",
        ],
    },
    {
        "from": "2.7.85",
        "to": "2.7.86",
        "description": "Fix: separate plan_mode (arch.md -> hld.md -> adr.md) had no path to generate the living .specify/service/api-spec.md at all -- unified plan_mode's design.md was the only route -- plus the two mode's document sets had drifted apart on several structural columns",
        "notes": [
            "Found via direct question: user asked whether unified design.md "
            "and separate arch.md/hld.md/adr.md actually cover the same "
            "ground. Verified against the real template/prompt files rather "
            "than from memory (the first pass had wrongly claimed "
            "design-template.md needed 'promoting' into the shared-sync "
            "system -- it was already there, confirmed by re-checking with "
            "md5sum across shared + all 5 packs)",
            "hld-template.md gained a new '## 6. API Design' section "
            "(renumbered Technology Stack -> 7, NFR Summary -> 8) -- ported "
            "from design.md's own §3 nearly verbatim, including its "
            "skip-list and provides/consumes branch, so it inherits the "
            "same per-project-type safety already proven there",
            "hld-template.md gained a new '## 4. Error / Failure Paths' "
            "sequence diagram (renumbering State Machine 4->5) -- design.md "
            "§2.5 already generates this unconditionally across all 5 "
            "packs today; separate mode had no equivalent anywhere",
            "plan-hld.prompt.md updated to match: new Diagram 4 (Error/"
            "Failure Paths) and Section 6 (API Design, with the full "
            "living-doc api-spec.md walk logic ported from "
            "plan-design.prompt.md §3); preview list and Section 8 NFR "
            "instruction fixed to list all 4 columns its own template "
            "defines (was only listing 2)",
            "Fixed 3 hardcoded design.md-only references that never "
            "branched by plan_mode even though the rest of their files "
            "did: task.prompt.md's QA-endpoint-source line, "
            "lld-template.md's References table, and ava.prompt.md's "
            "dead 'api spec' routing row (pointed at specify-doc.prompt.md, "
            "which explicitly refuses to generate api-spec)",
            "design-template.md's §1.2/§1.3/§1.4 tables gained the "
            "'what it must NOT do' / 'Alternatives Rejected' / "
            "'Decision (DEC-NNN)' columns that arch-template.md (separate "
            "mode's equivalent) already had -- plan-design.prompt.md's §1 "
            "instruction updated to match",
            "design.md's §4 ADR block expanded from a compact bullet list "
            "to the same Options A/B/C + pros/cons depth adr-template.md "
            "already uses -- plan-design.prompt.md §4 updated to match",
            "Deleted adr-template.md's dead 'ADR Index: docs/architecture/"
            "decisions.md' pointer -- no command ever generated that file",
            "All 5 packs' CLAUDE.md 'PLAN Sub-Commands' hld.md description "
            "updated to mention API design (was diagrams-only)",
            "Every edited file confirmed byte-identical across "
            "_shared/full + all 5 packs via md5sum after sync-blocks.sh",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Template/prompt-only change -- no manifest.yml field changes, "
            "no CLI behavior change. Verified: cli-python pytest 682/682 "
            "(unaffected), assert-output.sh clean on both worked examples, "
            "test-setup.sh 15/15",
        ],
    },
    {
        "from": "2.7.86",
        "to": "2.7.87",
        "description": "Fix: specify-doc.prompt.md's own SKIP/ADD-unit/UPDATE-unit living-doc walk (data-model, security-design, component-library) never re-synced Confluence/Jira after an approved change -- only /change's separate living-doc handling did",
        "notes": [
            "Asked directly whether ALL living-document updates get pushed "
            "to Confluence. Verified against the real files: change.prompt.md "
            "already calls `sdd review apply --doc {doc-key}` after every "
            "living-doc merge (confirmed at 3 separate spots), but "
            "specify-doc.prompt.md's own native walk -- the path a later "
            "feature normally takes to extend data-model.md/security-design.md "
            "on its own, not via a formal Change Request -- only merged, "
            "bumped the version, appended history, and regenerated the "
            "summary. No re-sync call anywhere in that block",
            "Same gap plan-design.prompt.md's api-spec.md walk had already "
            "solved (and this session's v2.7.86 fix ported into "
            "plan-hld.prompt.md) -- specify-doc.prompt.md's generic "
            "living-doc block (shared by data-model, security-design, and "
            "component-library via its own 'follow the same discipline' "
            "cross-reference) never got the same fix",
            "Added step 5 to the 'On approval' list: "
            "`sdd review apply --doc {doc}` -- re-pushes to Confluence + "
            "posts a re-review comment on Jira if either is configured, "
            "skip silently otherwise. Matches change.prompt.md's own "
            "wording for the same operation",
            "Practical effect before this fix: if data-model.md's "
            "Confluence page was already reviewed and live, a second "
            "feature adding a new entity through the normal "
            "/specify-doc data-model walk (not /change) would merge "
            "correctly on disk but leave the Confluence page silently "
            "stale",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Prompt-only change -- no manifest.yml field changes, no CLI "
            "behavior change. Verified: cli-python pytest 682/682 "
            "(unaffected), assert-output.sh clean",
        ],
    },
    {
        "from": "2.7.87",
        "to": "2.7.88",
        "description": "Fix: /specify-doc's own 'Action 2 doc-set table' cross-reference pointed at a table that didn't exist in specify.prompt.md in any pack -- broke discoverability of which extended docs (data-model, security, component-spec, etc.) a project actually needs",
        "notes": [
            "User asked how an end user is supposed to know which "
            "`/specify-doc {name}` to run, given something like a "
            "database schema is needed by almost every project -- "
            "isn't that overly complicated?",
            "Verified against the real files, not memory: "
            "specify-doc.prompt.md, specify-srd.prompt.md, and "
            "orchestrate.prompt.md (all three fully shared, byte-identical "
            "across all 5 packs) repeatedly say 'refer to the doc-set "
            "table in specify.prompt.md (Action 2)' for both the "
            "no-argument doc listing and the scope-check gate. Grepped "
            "'^## Action' in every pack's specify.prompt.md -- only "
            "'Action 1' (Constitution Part 2) exists anywhere. 'Action 2' "
            "was a dead pointer in all 5 packs",
            "The gap was papered over in Claude Code specifically because "
            "each pack's own CLAUDE.md (auto-loaded at session start) "
            "already lists the real doc names + scope gates -- but that "
            "fallback doesn't exist for non-Claude-Code tools entering "
            "through copilot-instructions.md, and sdd-universal's own "
            "CLAUDE.md punted with 'any other extended doc' instead of "
            "enumerating which of component-spec/ux-flow/screen-spec/"
            "resilience/investigation apply to which of its 10 "
            "project_types",
            "Fix: added a real '## Action 2 -- Extended Document Set' "
            "table to specify.prompt.md in each of the 4 single-type "
            "packs (backend-service, frontend-spa, mobile, fullstack), "
            "sourced from that pack's own CLAUDE.md so the two stay "
            "consistent. sdd-universal got a project_type-grouped matrix "
            "(consumer-view / mobile / server-service / no-runtime-service) "
            "instead of a false-precision 10-type table, since the "
            "framework doesn't itself define per-type applicability for "
            "cli/library/iac cleanly -- those three are marked "
            "ask-the-user-first rather than a guessed yes/no",
            "specify-doc.prompt.md's own no-argument instruction "
            "sharpened to explicitly read the Action 2 table (filtered "
            "by scope/project_type) and diff it against what's already "
            "on disk, instead of vaguely 'listing remaining documents'",
            "sdd-universal CLAUDE.md's vague '/specify-doc {name} -> any "
            "other extended doc' line pointed at the new Action 2 table "
            "instead of leaving it to guesswork",
            "orchestrate.prompt.md's existing Action 2 references, and "
            "each pack's CLAUDE.md 'Run after: /specify (Action 2)' "
            "bookend note, needed no changes -- they now resolve to a "
            "real heading instead of a dead one",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Prompt/doc-only change -- no manifest.yml field changes, no "
            "CLI behavior change. Verified: cli-python pytest 682/682 "
            "(unaffected), assert-output.sh clean on both worked examples, "
            "every 'Action 2' reference across all 5 packs now resolves "
            "to a real heading (grepped and confirmed), specify-doc.prompt.md "
            "confirmed byte-identical across _shared/full + all 5 packs "
            "via md5sum after sync-blocks.sh",
        ],
    },
    {
        "from": "2.7.88",
        "to": "2.7.89",
        "description": "Fix: dashboard's single collapsed 'Extended Specs' pipeline step let generating just one required doc (e.g. security) silently mark ALL of them (data-model, component-spec, ux-flow, ...) as done",
        "notes": [
            "User asked directly whether the dashboard tells someone when "
            "they forgot to run /specify-doc for a required extended doc. "
            "Checked cli-python/sdd/utils/status.py rather than assuming: "
            "_service_docs_exist() was a bare existence check -- 'does at "
            "least one .md file exist under .specify/service/' -- and the "
            "dashboard's whole 'Extended Specs (Data Model, Security, ...)' "
            "row flipped to done the moment ANY ONE of them existed",
            "Practical effect before this fix: running only "
            "`/specify-doc security` (forgetting data-model entirely) "
            "already showed the dashboard's single extended-specs row as "
            "satisfied -- exactly the silent gap the user was worried about",
            "Also found: the same collapsed step was skipped entirely at "
            "pilot scope, which contradicts CLAUDE.md's own Scope "
            "Reference table -- security-design.md is required at every "
            "scope (pilot gets Threat Assessment / §1 only, not zero)",
            "Fix: split the single row into one step per doc. "
            "security-design and data-model each get their own "
            "'service_doc' step backed by a new _service_doc_info(root, "
            "key) helper that checks .specify/service/{key}.md "
            "individually (existence + Status: header) instead of a "
            "folder-wide boolean. component-spec/ux-flow/screen-spec/"
            "resilience/investigation are now normal per-feature 'doc' "
            "steps (they already had per-file tracking via "
            "_feature_docs(), they just weren't in PIPELINE_DOCS or "
            "referenced by any pipeline step)",
            "Type-specific docs (component-spec/ux-flow/screen-spec) are "
            "only added as steps at all when the project's type actually "
            "uses them -- detected via _applicable_extended_docs(): "
            "template-file presence under .specify/templates/ for the 4 "
            "single-type packs (each ships only the templates its type "
            "needs), or manifest.yml's project_type field for "
            "sdd-universal (which ships every template up front, so "
            "presence-detection alone would wrongly say yes to "
            "everything). cli/library/iac deliberately map to no docs "
            "shown, rather than guessing -- same 'ask the user, don't "
            "assert a false yes/no' stance taken for the Action 2 table "
            "in 2.7.88",
            "security-design is now never scope-skipped (was wrongly "
            "skipped entirely at pilot); data-model/component-spec/"
            "ux-flow/screen-spec stay mvp+; resilience/investigation stay "
            "full-only -- each gated individually instead of one shared "
            "skip reason for the whole block",
            "Dashboard frontend (dashboard.py's renderPipelineStep) needed "
            "no changes -- it already renders any step generically from "
            "label/state/skip/command, with no hardcoded reference to the "
            "old 'extended-specs' id or 'service_docs' kind",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "cli-python only change (sdd/utils/status.py + its tests) -- "
            "no manifest.yml field changes, no prompt/template changes. "
            "Verified: cli-python pytest 688/688 (6 new regression tests "
            "added for the exact bug + corrected scope gating), live "
            "build_project_status() run against examples/todo-api and "
            "examples/habit-tracker-web confirmed security-design/"
            "data-model now track independently and component-spec/"
            "ux-flow correctly appear only for the frontend-spa example, "
            "assert-output.sh clean on both worked examples",
        ],
    },
    {
        "from": "2.7.89",
        "to": "2.7.90",
        "description": "Fix: dashboard's extended-docs steps listed security-design before data-model, so at mvp+ scope the 'next action' hint told users to run security before data-model -- backwards from the recommended /specify-doc sequence",
        "notes": [
            "User checked the dashboard step order against the practical "
            "sequence recommended earlier (data-model -> security -> "
            "component-spec/ux-flow) and asked whether it matched",
            "It didn't: _standard_pipeline_steps() listed security-design "
            "first. Neither doc depends on the other, so this was never "
            "a correctness bug, but build_pipeline()'s next_action picks "
            "the first non-done, non-skipped step in list order -- so at "
            "mvp+ scope with nothing generated yet, the dashboard said "
            "'Run /specify-doc security' before ever mentioning data-model",
            "Swapped the two entries in extended_steps so data-model is "
            "listed first, matching the recommended order. At pilot scope "
            "this has no visible effect (data-model is skipped there "
            "anyway, so security-design still surfaces first); at mvp+ "
            "the dashboard's next_action now correctly says "
            "'Run /specify-doc data-model' first",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "cli-python only change (sdd/utils/status.py, list-order "
            "only, no gating/skip logic touched) -- no manifest.yml field "
            "changes. Verified: cli-python pytest 688/688 (unaffected -- "
            "no test asserted next_step_id ordering between these two), "
            "live build_pipeline() run at mvp scope confirmed "
            "next_action now reads 'Run `/specify-doc data-model`' first",
        ],
    },
    {
        "from": "2.7.90",
        "to": "2.7.91",
        "description": "Add a cross-reference linter (packs/_shared/tests/check-cross-references.py) that catches dead 'Action N' / '{doc}.md §N' pointers between prompt files before a user finds them",
        "notes": [
            "Both real bugs found this session (v2.7.88's dead 'Action 2 "
            "doc-set table' pointer, v2.7.89's dashboard collapsing "
            "several docs' status into one boolean) share a root cause: "
            "something read as correct in isolated review but was never "
            "exercised end-to-end, and both were only found because a "
            "user asked a pointed question -- not because any test caught "
            "them. This closes that gap for the first bug class",
            "The script scans every pack's .github/prompts/*.md and "
            "CLAUDE.md for two patterns: 'specify.prompt.md ... (Action "
            "N)' and '{doc}.md §N', then verifies the referenced "
            "heading actually exists -- '## Action N' in that pack's own "
            "specify.prompt.md, or a top-level '## N. ...' heading in "
            "that doc's own *-template.md. Each pack is checked against "
            "its own copies, not a shared assumption, since packs can "
            "diverge",
            "Deliberately skips '*.summary.md §N' references (AI-2 "
            "summaries are a compressed digest with no guaranteed section "
            "numbering -- checking them would produce false positives, "
            "not real findings) and treats a doc key with no matching "
            "template as a note, not a failure (usually means the "
            "reference wasn't to a real document at all)",
            "Caught two real bugs in itself during development, both "
            "found by deliberately testing that it actually fails on a "
            "known-bad input rather than trusting a clean first run: (1) "
            "a Path.parents[] off-by-one meant it silently scanned a "
            "nonexistent directory and always passed; (2) the heading "
            "number regex matched digits from subsection numbers too "
            "(e.g. picked up '3' from '### 3.1 ...' even after the real "
            "'## 3. ...' heading was renamed), so a renamed top-level "
            "section wasn't detected as long as any N.x subsection "
            "survived -- fixed by only matching exactly '## N.' (two "
            "hashes)",
            "Verified end-to-end after both fixes: passes clean on the "
            "current repo (50 real references checked across 6 packs, "
            "confirmed via --verbose), and correctly fails with a clear "
            "file:line message when a heading is deliberately renamed in "
            "a scratch test, then passes again once reverted",
            "Wired into CI as a new 'cross-reference-check' job "
            "(.github/workflows/ci.yml) and documented in the root "
            "CLAUDE.md's 'Testing Setup Scripts' section alongside the "
            "other two harnesses",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "New standalone script, no manifest.yml field changes, no "
            "existing-code changes. Verified: cli-python pytest 688/688 "
            "(unaffected), assert-output.sh clean on both worked "
            "examples, test-setup.sh 15/15, test-setup-micro.sh 12/12",
        ],
    },
    {
        "from": "2.7.91",
        "to": "2.7.92",
        "description": "setup.sh/setup.ps1 now interactively ask for reading_mode (auto|summary|full) instead of silently baking in the 'auto' default with no prompt",
        "notes": [
            "A user asked directly: reading_mode already existed as a "
            "documented manifest.yml field (AI-2 token-economy switch in "
            "summary-rules.md), but grepping setup.sh/setup.ps1 confirmed "
            "it was never part of the interactive flow -- only name, "
            "scope, feature, and plan_mode were ever asked. Every new "
            "project silently got 'auto' with no chance to pick summary "
            "or full at init time",
            "Added a --reading-mode flag (-ReadingMode in PowerShell) and "
            "an interactive prompt with the same three-option explanation "
            "already in summary-rules.md, mirroring the existing plan_mode "
            "prompt pattern exactly -- same env-var-safe substitution in "
            "sdd-universal/setup.sh (project/feature names can contain "
            "special characters), same regex substitution in the shared "
            "_shared/full/setup.sh used by the other 4 non-micro packs",
            "sdd-micro intentionally excluded -- confirmed via grep it has "
            "no reading_mode field in its manifest.yml at all (no "
            "BRD/UC/SRD documents to summarize, so the AI-2 token-economy "
            "switch doesn't apply there)",
            "Verified with a real pty (not piped stdin, which forces "
            "non-interactive mode by the script's own design and would've "
            "given a false pass): the prompt renders, accepts 'summary', "
            'and writes reading_mode: "summary" into manifest.yml. Also '
            "verified --reading-mode full/summary flags directly on "
            "sdd-backend-service, sdd-frontend-spa, and sdd-universal's "
            "separate setup.sh",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "No manifest.yml schema change for existing projects -- the "
            "field already existed, only new-project setup behavior "
            "changed. Verified: cli-python pytest 688/688 (unaffected), "
            "test-setup.sh 15/15, test-setup-micro.sh 12/12, "
            "assert-output.sh clean on both worked examples",
        ],
    },
    {
        "from": "2.7.92",
        "to": "2.7.93",
        "description": "Let Jira and Confluence use separate ~/.sdd/config.yml profiles (jira.profile / confluence.profile in integrations.yml) instead of one shared profile for both",
        "notes": [
            "A user asked directly: their org runs Jira and Confluence as "
            "separate Data Center servers with separate credentials -- was "
            "that ever accounted for? It wasn't. Every command that talks "
            "to Jira and Confluence -- reviewed all ~19 call sites across "
            "config.py, confluence.py, cr.py, dashboard.py, jira.py, pr.py, "
            "review.py -- resolved exactly ONE Profile (one base_url, one "
            "credential) from the single top-level integrations.yml "
            "profile: field, then handed the SAME session to both "
            "JiraClient and ConfluenceClient. Correct only when both are "
            "the same Atlassian Cloud site (one hostname, one API token "
            "covers both) -- silently wrong the moment they're different "
            "servers",
            "IntegrationsConfig grew two new optional fields, jira.profile "
            "and confluence.profile, each falling back to the existing "
            "top-level profile: when unset (JiraConfig.profile / "
            "ConfluenceConfig.profile in utils/integrations.py, resolved "
            "via new jira_profile_name()/confluence_profile_name() "
            "methods) -- so every existing project with one profile: line "
            "keeps working identically, no manifest.yml or integrations.yml "
            "change required",
            "New atlassian_auth.load_jira_session(cfg, profile_override) "
            "and load_confluence_session(cfg, profile_override) resolve "
            "the Profile + authenticated Session for each service "
            "independently, replacing the old load_profile()+build_session() "
            "pair at every call site. A command's own --profile flag still "
            "wins over both, matching the old precedence",
            "cr_submit (cr.py) and the dashboard's review-links fetch "
            "resolve each session conditionally -- only if that service's "
            "section (jira:/confluence:) is actually configured -- since "
            "unconditionally resolving both (as an early draft of this fix "
            "did) would require credentials for a service the user never "
            "configured for that command",
            "integrations.yml.example documents both new fields with a "
            "note on when to use them (Data Center, not Cloud); synced to "
            "all 5 non-micro packs via sync-blocks.sh",
            "New tests: 4 in test_config_and_integrations.py (profile "
            "fallback, independent override, one-service override, "
            "missing-section tolerance) + 3 in test_atlassian_auth.py "
            "(different base_urls resolve independently, same profile "
            "when unset, explicit override still wins)",
            "Verified: cli-python pytest 695/695 (688 pre-existing + 7 "
            "new), including updating ~13 existing tests in "
            "test_review_helpers.py/test_confluence_push_cli.py/test_cr.py "
            "that mocked the old load_profile/build_session pair directly",
        ],
    },
    {
        "from": "2.7.93",
        "to": "2.7.94",
        "description": "'sdd config init' now asks upfront whether Jira and Confluence share one set of credentials or need two, instead of requiring a manual second run + hand-edit to use the jira.profile/confluence.profile split added in 2.7.93",
        "notes": [
            "2.7.93 added jira.profile/confluence.profile overrides so the "
            "two services can use separate ~/.sdd/config.yml profiles, but "
            "'sdd config init' itself was still a single-profile wizard -- "
            "getting the split required running init twice and manually "
            "uncommenting the override lines in integrations.yml afterward. "
            "A user asked directly: does init actually offer this? It "
            "didn't",
            "config_init() now opens with 'Do Jira and Confluence share "
            "the same site and credentials?' -- Yes keeps the exact "
            "original single-profile flow; No runs the full credential "
            "round (profile name, base_url, auth mode, credential storage) "
            "twice, once per service, via a new _collect_and_save_profile() "
            "helper extracted from the original inline flow so both paths "
            "share identical prompts and validation",
            "'Different' mode wires the result automatically -- the "
            "top-level profile: becomes Jira's, and confluence.profile: is "
            "uncommented and filled with the Confluence profile name in "
            "the generated integrations.yml (_integrations_from_example / "
            "_integrations_template both take an optional confluence_profile "
            "param). No manual editing step required anymore",
            "A profile is understood as the entire auth set (base_url + "
            "auth_mode + credential) -- the two profiles created in "
            "'different' mode are never assumed to share anything, even if "
            "e.g. the base_url happened to coincide",
            "New tests: test_different_profiles_creates_both_in_config_yml "
            "(both profiles saved with distinct base_url/auth_mode/storage) "
            "and test_different_profiles_wires_confluence_override_into_integrations_yml "
            "(end-to-end: generated integrations.yml actually has the "
            "override, not just two orphaned config.yml profiles). 5 "
            "pre-existing config-init tests updated for the new opening "
            "question",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "No manifest.yml or integrations.yml schema change -- 2.7.93 "
            "already added the fields this just makes reachable from the "
            "wizard. Verified: cli-python pytest 697/697 (695 pre-existing "
            "+ 2 new)",
        ],
    },
    {
        "from": "2.7.94",
        "to": "2.7.95",
        "description": "Confluence parent-page prompt/config now accepts a pasted page URL, not just the raw numeric ID",
        "notes": [
            "A user pointed out that when 'sdd config init' asks for the "
            "Confluence parent page, most people have the page open in a "
            "browser tab, not its raw numeric ID memorized -- the wizard "
            "only accepted the bare ID, forcing a manual trip through "
            "Page Information to extract it first",
            "New sdd.utils.integrations.parse_confluence_page_id() "
            "recognizes a bare numeric ID unchanged, a Cloud URL "
            "('.../pages/123456/Title'), or a Server/Data Center URL "
            "('...?pageId=123456'), and extracts just the numeric ID from "
            "either -- a Confluence 'tiny link' (/x/AbCdEf) isn't a page "
            "ID and can't be resolved without an API call, so it's "
            "returned unchanged with a wizard warning telling the user "
            "to paste the full URL instead",
            "Wired into two places: the config-init wizard prompt (so "
            "pasting a URL there resolves correctly in the generated "
            "integrations.yml), and load_integrations() itself (so a "
            "hand-edited integrations.yml with a pasted URL for "
            "parent_page_id also resolves correctly at push time, not "
            "just via the wizard)",
            "integrations.yml.example's parent_page_id comment updated "
            "to document that either form works",
            "New tests: parse_confluence_page_id() parametrized over bare "
            "ID / Cloud URL / Server-DC URL / blank / tiny-link fallback, "
            "load_integrations() resolving a pasted URL from YAML, and an "
            "end-to-end config-init wizard test asserting the generated "
            "integrations.yml has just the numeric ID after pasting a URL "
            "at the prompt",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "No manifest.yml schema change. Verified: cli-python pytest "
            "707/707 (697 pre-existing + 10 new)",
        ],
    },
    {
        "from": "2.7.95",
        "to": "2.7.96",
        "description": "'sdd config test' now resolves Jira and Confluence independently, instead of pinging both against one profile's base_url",
        "notes": [
            "A user asked whether all docs were updated for the recent "
            "config-init changes -- while auditing, found that 'sdd "
            "config test' still resolved exactly ONE Profile and pinged "
            "both Jira and Confluence against its base_url, even though "
            "2.7.93 let them use separate profiles. That means testing "
            "the split with `sdd config test --profile confluence-dc` "
            "(exactly what the config-init wizard's own closing message "
            "told you to run) would try to hit Jira at Confluence's URL "
            "and vice versa -- a silent false failure for whichever "
            "service didn't match the flag",
            "Without --profile, Jira and Confluence are now each resolved "
            "through integrations.yml's jira.profile/confluence.profile "
            "(cfg.jira_profile_name()/confluence_profile_name(), same "
            "helpers load_jira_session/load_confluence_session already "
            "use) independently -- each service is pinged against its "
            "own base_url and credential. When they resolve to the same "
            "profile (the common case), only one session is built and no "
            "extra output is printed, so single-profile projects see "
            "identical output to before. When they differ, the command "
            "prints which profile backs which service before testing",
            "An explicit --profile still tests that ONE profile against "
            "BOTH services, unchanged -- for sanity-checking a profile "
            "before it's wired into integrations.yml. This is a "
            "deliberate override, matching the 'a command's own --profile "
            "flag still wins over both' precedent load_jira_session/ "
            "load_confluence_session already established",
            "config_init()'s own closing message was part of the same "
            "bug: it told users to run 'sdd config test --profile X' "
            "twice, which (see above) doesn't actually isolate a single "
            "service. Now scaffolding integrations.yml means the message "
            "says 'Run sdd config test to verify both' (no --profile, "
            "since the split is now resolvable automatically); declining "
            "to scaffold falls back to the old two-command guidance with "
            "an explicit caveat that each call tests one profile against "
            "both services",
            "New tests: single-profile pings-once (no profile-name lines "
            "printed), split-profile pings each against its own base_url, "
            "explicit --profile overrides the split, an unknown "
            "confluence.profile reports which service's config failed, "
            "plus the two config-init closing-message variants (scaffolded "
            "vs declined)",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "No manifest.yml schema change. Verified: cli-python pytest "
            "713/713 (707 pre-existing + 6 new)",
        ],
    },
    {
        "from": "2.7.96",
        "to": "2.7.97",
        "description": "Jira Feature/Epic description now carries Problem Statement, Business Hypothesis, Description, Out of Scope, and NFR instead of a bare Business Objectives bullet list",
        "notes": [
            "A user asked for a specific description template on the "
            "Feature/Epic issue: Problem Statement, Business Hypothesis, "
            "Description, Out of Scope, NFR. The previous description was "
            "a single 'Business Objectives:' bullet list pulled from "
            "brd.md's BO-NNN rows -- useful, but not the shape being "
            "asked for",
            "brd-template.md gains a new '### Business Hypothesis' field "
            "under §4 Business Context, right after Problem Statement -- "
            "a testable belief statement ('We believe that X for Y will "
            "result in Z; we'll know this is true when...'), distinct "
            "from the Problem Statement it sits next to. "
            "specify-brd.prompt.md instructs the agent to fill it, "
            "falling back to [ASSUMPTION-NNN] if no measurable signal is "
            "available yet",
            "New jira.py parsers: parse_brd_problem_statement/"
            "_business_hypothesis/_executive_summary (brd.md §4/§4/§1), "
            "parse_brd_out_of_scope (brd.md §4's 'Out of Scope:' bullets, "
            "not confused with the 'In Scope:' bullets right above them), "
            "and parse_srd_nfr_rows (srd.md §3's NFR-NNN table, "
            "'Category: Requirement' per row)",
            "New adf_sections() ADF builder renders each as its own "
            "heading + body, and OMITS a section entirely (no empty "
            "heading) when its source doesn't exist yet or is still "
            "unfilled template placeholder text -- e.g. NFR is silently "
            "absent until /specify-srd runs, without forcing the whole "
            "description into a placeholder. Falls back to a single "
            "'Details pending -- run /specify-brd...' paragraph only "
            "when every section is empty (the Epic bootstrapped right "
            "after /specify, before brd.md exists at all)",
            "parse_brd_objectives() and the old Business Objectives-only "
            "adf_doc() call in feature_extra_fields() are removed -- "
            "nothing else referenced the BO-NNN parser directly",
            "sdd review submit's Epic self-bootstrap (_ensure_epic in "
            "review.py) reuses the same feature_extra_fields(), so it "
            "gets the new template automatically, no separate change "
            "needed there",
            "Every existing Epic gets the new description shape on its "
            "next push (create-or-update is idempotent, keyed by the "
            "existing sdd-feature:{feature} label) -- no manual migration "
            "step, no manifest.yml schema change",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Verified: cli-python pytest 721/721 (713 pre-existing + 8 "
            "new), cross-reference linter clean, assert-output.sh clean "
            "against examples/todo-api, setup smoke tests clean",
        ],
    },
    {
        "from": "2.7.97",
        "to": "2.7.98",
        "description": "Jira Feature/Epic description gains Business Objectives, Success Criteria, and a Confluence link, following up on the 2.7.97 structured template",
        "notes": [
            "Follow-up to a user's structured-description request "
            "(2.7.97: Problem Statement / Business Hypothesis / "
            "Description / Out of Scope / NFR) -- asked what else was "
            "worth adding to a business-level Epic. Recommended and "
            "shipped three more: Success Criteria (closes the loop the "
            "Business Hypothesis opens -- 'we'll know this is true "
            "when X'), a Confluence link (so the Epic points at the "
            "full document, not just an excerpt), and Business "
            "Objectives (brought back as its own compact section, "
            "distinct from the free-text Description/Hypothesis prose)",
            "New parsers: parse_brd_business_objectives() (brd.md §2's "
            "BO-NNN table -- 'BO-NNN: {objective} — {success metric}' "
            "per row, metric appended only when the row has one) and "
            "parse_brd_success_criteria() (brd.md §8's checklist items, "
            "section-scoped so a stray checkbox elsewhere in the doc, "
            "e.g. a compliance table cell, can't leak in)",
            "New brd_confluence_link()/_resolve_confluence_base_url() "
            "read the local .specify/.confluence-drafts.json cache "
            "(same file status.py's dashboard link resolution already "
            "reads) -- no network call, None (link omitted) if "
            "Confluence isn't configured or brd.md hasn't been pushed "
            "there yet. sdd jira push resolves the base_url itself via "
            "a local ~/.sdd/config.yml lookup; sdd review submit reuses "
            "the Confluence Profile it already resolved for this doc's "
            "own push, costing nothing extra",
            "New _append_link_section() appends a 'Full Document' "
            "heading + ADF link mark after adf_sections()'s output -- a "
            "hyperlink needs a `link` mark, which adf_sections' plain-"
            "string/bullet-list body support can't express",
            "feature_extra_fields() gained an optional "
            "confluence_base_url param (default None, fully backward "
            "compatible); _push_epic()/_push()/_ensure_epic() thread it "
            "through from their respective callers",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "No manifest.yml schema change -- every existing Epic picks "
            "up the two new sections and the link on its next push "
            "(idempotent upsert, no manual step). Verified: cli-python "
            "pytest 739/739 (721 pre-existing + 18 new), cross-reference "
            "linter clean, setup smoke tests clean",
        ],
    },
    {
        "from": "2.7.98",
        "to": "2.7.99",
        "description": "Packaging metadata only: PyPI/npm Summary and keywords rewritten for discoverability -- no functional change, no manifest.yml effect",
        "notes": [
            "A user looked at the sddflow PyPI page and pointed out the "
            "Summary ('SDD Framework CLI -- initialize and upgrade "
            "Spec-Driven Development packs') undersold what the CLI "
            "actually does now -- it reads like a scaffolding tool, with "
            "no mention of the Jira/Confluence sync, multi-host PR "
            "automation, or dashboard that make up most of it",
            "cli-python/pyproject.toml's description (PyPI 'Summary') is "
            "now: 'Spec-Driven Development CLI for AI coding agents -- "
            "SDLC workflows with Jira/Confluence sync, multi-host PR "
            "automation, and live progress dashboards'. keywords gained "
            "jira/confluence/atlassian/pull-request/code-review/"
            "requirements/ai-agent/claude-code for search visibility",
            "cli/package.json's description was written separately, not "
            "copied verbatim -- the Node CLI genuinely doesn't have "
            "Jira/Confluence integration, PR automation, or a dashboard "
            "(cli-python-only features per this repo's own CLAUDE.md), "
            "so claiming them there would be inaccurate. It now reads "
            "'CLI for the Spec-Driven Development (SDD) Framework -- "
            "initialize and upgrade AI-agent SDLC packs (Claude Code, "
            "GitHub Copilot, and any AI coding tool)'",
            "'Author: None' on the PyPI page (also raised) is expected, "
            "not a bug: PEP 621's authors=[{name,email}] maps to the "
            "combined 'Author-email' Core Metadata field per spec, "
            "leaving the legacy 'Author' field blank -- there's no "
            "separate name-only field to populate instead",
            "This is the one migration entry in this chain that changes "
            "nothing a user's project would notice -- no manifest.yml "
            "field, no generated file, no CLI behavior differs. It exists "
            "purely so a fresh `pip install`/`npm install` after this "
            "point reports the new sdd_version, and so `sdd upgrade` on "
            "an older project doesn't get stuck on an unreachable target",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Publishing this to PyPI (so the new Summary is actually "
            "visible on pypi.org) still requires the maintainer's own "
            "`python -m build && twine upload` (or equivalent CI step) "
            "-- this repo has no PyPI credentials or publish automation",
        ],
    },
    {
        "from": "2.7.99",
        "to": "2.7.100",
        "description": "'sdd init' now asks plan_mode and reading_mode interactively, like setup.sh already does -- both previously stayed silently at the pack default",
        "notes": [
            "A user ran 'sdd init' (the pip-installed CLI, not "
            "setup.sh) and asked when reading_mode gets asked -- it "
            "never was. init.py only ever asked project type, project "
            "name, feature name, scope, and AI tool; plan_mode and "
            "reading_mode were silently left at whatever the pack's "
            "shipped manifest.yml template defaults to ('unified'/"
            "'auto'), with no way to choose otherwise short of hand-"
            "editing manifest.yml afterward",
            "This README already documents 'sdd init' as 'Replaces "
            "bash setup.sh / .\\setup.ps1' -- setup.sh has asked both "
            "interactively since v2.7.92 (reading_mode) and earlier "
            "(plan_mode), so this was a real parity gap between the "
            "two scaffolding entry points, not a new feature",
            "init_command() now asks 'Plan document style:' "
            "(unified/separate) and 'Document reading mode:' "
            "(auto/summary/full) right after scope, using the exact "
            "same option wording as setup.sh's prompts. New "
            "--plan-mode/--reading-mode flags skip them non-"
            "interactively, matching --scope/--type's existing pattern",
            "sdd-micro is exempt -- its manifest.yml template has "
            "neither field (3-command pack, no plan/design gates), same "
            "is_micro guard already used for scope/project_type",
            "New tests: interactive selection written to manifest, CLI "
            "flags skip both prompts, sdd-micro never prompts for "
            "either. 4 pre-existing scaffold/fill-mode tests updated to "
            "pass --plan-mode/--reading-mode so their questionary.select "
            "side_effect lists (and stated intent, e.g. 'only ai_tool "
            "prompted') stay accurate now that two more prompts exist "
            "in the call sequence",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "No manifest.yml schema change -- both fields already "
            "existed, this just makes them reachable from 'sdd init' "
            "the same way they're reachable from setup.sh. Verified: "
            "cli-python pytest 742/742 (739 pre-existing + 3 new)",
        ],
    },
    {
        "from": "2.7.100",
        "to": "2.8.0",
        "description": "Versioning scheme change: sdd_version is now a capped major.minor.patch counter (patch 0-24, minor 0-9) instead of an ever-growing patch number -- this bump is the one-time reset off the runaway old scheme",
        "notes": [
            "The old scheme just incremented the patch number forever -- "
            "it had reached 2.7.100 (a hundred patch releases within one "
            "minor version), which a user pointed out was an awkward, "
            "hard-to-reason-about number",
            "New scheme: patch (Z) ranges 0-24, minor (Y) ranges 0-9. "
            "Bumping patch past 24 instead increments minor and resets "
            "patch to 0; bumping minor past 9 instead increments major "
            "and resets minor to 0. Equivalent to treating the version "
            "as one running integer N = X*250 + Y*25 + Z, adding 1, and "
            "reconstituting X/Y/Z via divmod(N, 250) then divmod(rem, 25)",
            "This specific bump (2.7.100 -> 2.8.0) is a manual, one-time "
            "reset, not the general divmod rule applied retroactively -- "
            "the user explicitly chose NOT to divmod the old scheme's "
            "runaway patch count (which would have landed on 3.1.0, per "
            "100 = 4*25 rollovers of the old y=7 baseline, itself "
            "overflowing the new y-cap of 10). Every bump from 2.8.0 "
            "onward uses the plain capped rule with no further special-"
            "casing",
            "New .claude/skills/version-bump/SKILL.md in this repo "
            "encodes the full procedure (compute next version, update "
            "all 9 lockstep files, append matching migration entries to "
            "both upgrade.py and upgrade.js, add the CHANGELOG.md entry, "
            "run verification) so future bumps apply the rule "
            "consistently instead of being computed ad hoc each time",
            "Purely a versioning/process change -- no functional CLI "
            "behavior differs, no manifest.yml schema change. This Node "
            "CLI ships from the same pack sources -- this migration "
            "entry exists so both CLIs report the same sdd_version chain",
            "Verified: cli-python pytest 742/742 (unchanged from 2.7.100 "
            "-- no code touched), ast.parse on upgrade.py, node --check "
            "on upgrade.js",
        ],
    },
    {
        "from": "2.8.0",
        "to": "2.8.1",
        "description": "Node CLI gets its first automated tests -- ported cli-python's migration-chain-integrity tests to close a coverage gap flagged in code review",
        "notes": [
            "An external code review pointed out that cli/ (the Node CLI) "
            "had zero automated tests -- no test script in package.json, "
            "no test files anywhere, and the node-cli-sanity CI job only "
            "ran `node bin/sdd.js --help`. By contrast this Python CLI "
            "has hundreds of tests covering the same surface, including "
            "test_migration_table_is_a_connected_chain_ending_at_current, "
            "which verifies every MIGRATIONS entry's 'from' matches the "
            "previous entry's 'to' and the chain ends at SDD_VERSION",
            "Both CLIs hand-mirror the same ~100-entry MIGRATIONS table "
            "on every release (the Node CLI is scaffolding-only and "
            "doesn't implement most of what it's narrating, per its own "
            "README) -- until now, only this Python side had a test that "
            "would catch a broken from/to link. A typo on the Node side "
            "would go undetected by CI until a real user's `sdd upgrade` "
            "hit 'No migration path found'",
            "cli/src/commands/upgrade.js's MIGRATIONS const is now "
            "exported (was module-private) so a test file can import it. "
            "New cli/tests/upgrade.test.js ports two tests: the chain-"
            "connectivity check above, and a check that every entry's "
            "migrate() stamps its own 'to' version",
            "Uses Node's built-in node:test/node:assert -- zero new "
            "dependencies. New 'test': 'node --test' script in "
            "cli/package.json, and the node-cli-sanity CI job now runs "
            "`npm test` before the existing --help smoke test",
            "No functional CLI behavior change, no manifest.yml schema "
            "change -- purely closing a test-coverage gap. Verified: "
            "cli-python pytest 742/742 (unchanged), node --test 2/2 "
            "passing in cli/, ast.parse on upgrade.py, node --check on "
            "upgrade.js",
        ],
    },
    {
        "from": "2.8.1",
        "to": "2.8.2",
        "description": "'sdd upgrade' no longer needs one invocation per pending migration -- it now finds the whole chain and offers to jump straight to latest",
        "notes": [
            "An external code review (point #3) flagged that "
            "upgrade_command()/upgradeCommand() in both CLIs only ever "
            "found and applied a single migration hop per run -- a plain "
            "match on MIGRATIONS entries whose 'from' equals the current "
            "version. Since 'from' is unique per entry, this structurally "
            "never matched more than one, even though it was looped over. "
            "A project many versions behind needed one `sdd upgrade` "
            "invocation per pending migration to catch up. The user "
            "confirmed this was actively painful: they're shipping new "
            "versions every 30-40 minutes right now",
            "New _pending_migrations()/pendingMigrations() walks the full "
            "linear MIGRATIONS chain from the current version to "
            "SDD_VERSION, returning every pending hop in order instead of "
            "just the next one",
            "With more than one migration pending, a real interactive "
            "terminal is now asked whether to jump straight to the latest "
            "version (apply everything now) or step through one at a "
            "time (to read each version's notes before continuing). A "
            "non-interactive invocation -- CI, piped stdin, scripts -- "
            "skips the prompt and defaults to jumping straight to latest, "
            "so automation never needs N reruns to converge",
            "New flags in both CLIs: --to-latest (force jump, skip "
            "prompt), --step (force one-hop-then-stop -- the original "
            "behavior, skip prompt), -y/--yes (skip prompt, defaults to "
            "jump-to-latest -- extends the Python side's existing --yes "
            "flag, which previously only covered the --sync-prompts "
            "confirmation)",
            "TTY detection is broken out into a small "
            "_stdin_is_interactive()/_stdinIsInteractive() helper rather "
            "than a bare sys.stdin.isatty()/process.stdin.isTTY check -- "
            "Click's CliRunner reassigns sys.stdin to its own captured "
            "stream during invoke(), which silently defeats a naive "
            "patch() set up before the call; the helper makes this "
            "reliably mockable in tests",
            "cli-python/README.md and cli/README.md's 'sdd upgrade' "
            "sections document the new prompt and flags",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "No manifest.yml schema change. Verified: cli-python pytest "
            "753/753 (742 pre-existing + 11 new), node --test 4/4 in "
            "cli/ (2 pre-existing + 2 new -- full CliRunner-equivalent "
            "interactive-prompt coverage wasn't ported to the Node side, "
            "a deliberate scope limit matching this CLI's existing "
            "lighter test investment, not an oversight). Manually "
            "smoke-tested the real CLI: --to-latest jumps v2.0.0 -> "
            "v2.8.1 in one call, --step applies exactly one hop and "
            "prints the rerun hint, and plain non-interactive stdin also "
            "jumps straight to latest by default",
        ],
    },
    {
        "from": "2.8.2",
        "to": "2.8.3",
        "description": "Onboarding-friction fixes from an end-user feedback review: sdd-micro redirect, honest 5-minute claim, optional-persona note, cli/ marked private",
        "notes": [
            "A user shared an end-user feedback review (from another chat "
            "session) that pointed out real onboarding friction: heavy "
            "reading load, an 8-persona team-routing system with no "
            "signal it's optional, and -- the sharpest finding -- no "
            "redirect toward sdd-micro for solo/prototype users until "
            "they'd already committed real time to a full pack's docs",
            "Added an sdd-micro redirect callout to all 5 full packs' "
            "README.md and QUICKSTART.md 'What Is This?'/intro sections: "
            "'Building something small, solo, or just prototyping? ... "
            "use sdd-micro instead.' This previously only existed in the "
            "maintainer repo's own root README.md -- a user who copied a "
            "single pack into their own project (the documented "
            "deployment model) never saw it. Caught and fixed a self-"
            "introduced bug while implementing this: the first draft "
            "used a relative link (../sdd-micro/) which only resolves "
            "inside this maintainer repo where packs are siblings; fixed "
            "to an absolute GitHub URL that works regardless of how a "
            "user obtained the pack",
            "Fixed QUICKSTART.md's self-contradicting headline in all 5 "
            "packs: 'Five minutes to your first spec' was directly "
            "contradicted by a '15-30 min' context-writing step 30 lines "
            "later in the same file. Reframed honestly: '5 minutes to "
            "get set up. Your first full feature spec takes longer -- "
            "budget half a day for a first pass'",
            "Added a one-line 'this is optional' note to the Virtual "
            "Team persona section in all 5 packs' README.md, before the "
            "Maya/Rex/Ava/etc. table -- the persona system itself isn't "
            "the problem (it's a real convenience layer, not a second "
            "required thing to learn), the problem was nothing telling "
            "a first-time reader that before they hit an 8-row table",
            'Added "private": true to cli/package.json -- CLAUDE.md '
            "already documents this package as 'unpublished, from "
            "source' but nothing enforced that; an accidental npm "
            "publish would have succeeded",
            "Not changed: the migration-table duplication between this "
            "CLI and cli/upgrade.js -- already test-covered on both "
            "sides from a prior round, and the review itself downgraded "
            "this to 'not urgent'",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Documentation/config-only -- no functional code touched, no "
            "manifest.yml schema change, no CLI behavior differs. "
            "Verified: cli-python pytest 753/753 (unchanged), cross-"
            "reference linter clean across all 6 packs, package.json "
            "parses",
        ],
    },
    {
        "from": "2.8.3",
        "to": "2.8.4",
        "description": "Doc-navigation fixes from a third end-user feedback review: Start Here table, self-approval-risk callout, token/cost footprint callout",
        "notes": [
            "A user shared a third, more detailed end-user feedback review "
            "(same theme as the 2.8.3 round, different reviewer): 11 "
            "top-level docs in each pack with no stated reading order, "
            "the self-approval-risk disclosure buried inside CLAUDE.md "
            "(agent-facing only, never surfaced to the human who actually "
            "needs to know it), and no signal at all about the token/cost "
            "footprint of running the full document-heavy pipeline",
            "Added a 'Start Here -- Which File Do I Read?' table to the "
            "top of every full pack's README.md: 3 files to read in order "
            "(QUICKSTART.md -> README.md -> HOW-TO-USE.md), the remaining "
            "8ish reference files listed separately as 'skip on first "
            "pass, come back when you need it'",
            "Added a self-approval-risk callout to every pack's "
            "QUICKSTART.md, right after the 'review gates work out of the "
            "box' paragraph: default chat-mode approval only checks that "
            "someone typed 'approved' in the same conversation that wrote "
            "the doc -- no independent identity check -- pointing to "
            "CLAUDE.md's existing 'Self-approval risk' section for the "
            "full explanation instead of duplicating it",
            "Added a token/cost footprint callout to every pack's "
            "QUICKSTART.md intro: describes the pipeline's actual command "
            "cadence (one agent command per phase, each reading/writing "
            "at least one document) rather than a fabricated dollar "
            "figure -- confirmed there is no real token-usage data "
            "anywhere in this repo to cite (token-pricing.yml.example "
            "ships with all rates null); points to enabling "
            "token-pricing.yml for a real per-command log instead",
            "sdd-fullstack's Start Here table omits the "
            "IMPROVEMENT-BACKLOG.md row -- that pack has only 10 root "
            ".md files, unlike the other 4 packs' 11 -- verified via a "
            "directory listing before writing the table, not assumed",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Documentation-only -- no functional code touched, no "
            "manifest.yml schema change, no CLI behavior differs. "
            "Verified: cli-python pytest 753/753 (unchanged), cross-"
            "reference linter clean across all 6 packs, both setup "
            "smoke-test suites (15 + 12) pass",
        ],
    },
    {
        "from": "2.8.4",
        "to": "2.8.5",
        "description": "Surface the worked examples to real end users; implement TASK-001/002/003 of examples/todo-api for real",
        "notes": [
            "Two fixes shipped together, following on from the 2.8.3/2.8.4 "
            "onboarding-friction rounds",
            "Fix 1 (this repo's packs -- the reason this bump exists): "
            "added a 'Want to see a finished example first?' callout, "
            "linking to examples/ on GitHub, to all 5 full packs' "
            "README.md and QUICKSTART.md. Closes a real gap found while "
            "reviewing the framework end-to-end: examples/todo-api and "
            "examples/habit-tracker-web existed and were well-built, but "
            "were referenced from nowhere a real user running `sdd init` "
            "would ever see them -- only from this maintainer repo's own "
            "root README.md and the CI regression harness "
            "(assert-output.sh). A user who only ever works inside a "
            "copied-out pack folder never knew they existed",
            "Fix 2 (examples/ only -- does not touch any pack, included "
            "here for the full story even though it doesn't change "
            "sdd_version-relevant files): TASK-001 (Prisma schema + "
            "migration), TASK-002 (user-scope Prisma extension, FR-007), "
            "and TASK-003 (POST /tasks endpoint, UC-001) of "
            "examples/todo-api's 10-task tasks.md are now implemented for "
            "real -- actual TypeScript/Express/Prisma/PostgreSQL 16 code, "
            "actually run against a live local Postgres 16 instance, 13 "
            "tests actually passing (5 unit + 8 integration), `tsc "
            "--noEmit` clean. Both worked examples had a full spec chain "
            "(BRD through tasks.md) but zero implementation code before "
            "this -- three independent end-user reviews flagged that gap "
            "as the biggest open question ('does this produce real "
            "software or just paperwork')",
            "tasks.md's checkboxes for TASK-001/002/003's acceptance "
            "criteria are now [x], each with an 'Implemented:' line "
            "pointing at the actual files. TASK-004 through TASK-010 "
            "remain spec-only, unchanged",
            "Two simplifications are called out explicitly in the new "
            "examples/todo-api/IMPLEMENTATION.md, not hidden: JWT "
            "verification uses HS256 with a shared secret instead of the "
            "RS256-from-env scheme context.md's Tech Stack row specifies "
            "(verifying real RS256 tokens needs a real Auth Service to "
            "mint them); and the three partial indexes in hld.md's raw "
            "SQL (`WHERE archived = false` etc.) aren't expressed in "
            "prisma/schema.prisma, since Prisma's declarative schema DSL "
            "doesn't support partial indexes without an unstable preview "
            "feature",
            "TASK-007 (full auth middleware wiring -- RS256 verification, "
            "expired-JWT handling) is explicitly NOT marked done. Making "
            "TASK-003 testable end-to-end required pulling forward a "
            "minimal HS256 stand-in for auth.middleware.ts and "
            "user-scope.middleware.ts, but that stand-in does not satisfy "
            "TASK-007's own acceptance criteria and its checkboxes were "
            "left unchecked",
            "No simulated /pre-review or /address-review round is "
            "included -- there's no real reviewer for a maintainer-repo "
            "example, and simulating one would read as staged rather "
            "than as proof",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Verified: cli-python pytest 753/753 (unchanged -- no "
            "cli-python code touched), cross-reference linter clean "
            "across all 6 packs, both setup smoke-test suites (15 + 12) "
            "pass, assert-output.sh's 33 structural assertions still "
            "pass against the edited tasks.md, and -- specific to this "
            "round -- the new examples/todo-api test suite itself: 13/13 "
            "passing (jest --testPathPattern user-scope 5/5, jest "
            "--testPathPattern tasks.routes 8/8), tsc --noEmit clean, "
            "prisma migrate dev applied clean against a freshly created "
            "PostgreSQL 16 database",
        ],
    },
    {
        "from": "2.8.5",
        "to": "2.8.6",
        "description": "Dashboard: per-stage duration, review-round count, and an overall feature Timeline card",
        "notes": [
            "User request: 'sdd dashboard' showed each document's status "
            "but not how long each stage took, how many review rounds it "
            "went through, or an overall feature start/end",
            "Added per-document Created date, Approved date, duration (in "
            "days), and revision-round count -- computed from the "
            "document's own '## Version History' table, data that was "
            "already being written by the shared review-decision-step "
            "block (used by every /specify-*, /plan-*, and /task command) "
            "but never read back out anywhere. First row = creation date; "
            "when Status says Approved, the last row is always the "
            "approval event (that block always appends a same-version "
            "'Approved' row on the final approval, regardless of chat/"
            "local/jira mode); revision_rounds counts actual version "
            "bumps in the table, i.e. rounds that changed content, not "
            "every review check -- a pure re-read-and-approve with no "
            "edit doesn't bump the version so isn't counted",
            "Added a feature-level Timeline card: start_date is the "
            "earliest document's created date (normally brd.md), "
            "end_date is release.md's approved date (falls back to its "
            "own Approvals-table Date column, since release.md has no "
            "Version History table), duration in days once both resolve",
            "Required standardizing the {date} placeholder across every "
            "doc template to {date: YYYY-MM-DD} so dates are machine-"
            "parseable -- both the shared _shared/full/.specify/templates "
            "(synced to all 5 packs) and each pack's own non-shared "
            "templates (release, arch, api-spec, security-design, "
            "data-model, resilience, investigation, runbook, and the "
            "frontend/mobile-specific variants). sdd-micro's own "
            "context-template.md was deliberately left untouched -- it's "
            "outside the shared-block/version-lockstep system",
            "Old documents, or any hand-edited date that isn't ISO 8601, "
            "simply don't show duration/rounds -- no warning badge, "
            "nothing else on the page affected. This was an explicit "
            "choice (silent degradation over a visible warning state) "
            "made this round rather than assumed",
            "New status.py functions: _parse_iso_date, "
            "_parse_version_history_table, _doc_timing, "
            "_feature_timeline. New dashboard.py JS: timingSummaryLine() "
            "(per-doc line under the status badge), renderTimeline() (the "
            "feature-level card)",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain. The dashboard itself is Python-only "
            "(cli-python's `sdd dashboard`) -- this bump has no "
            "corresponding functional change on the Node CLI side",
            "Verified: cli-python pytest 765/765 (753 pre-existing + 12 "
            "new, covering the Version History parser, ISO date parser, "
            "per-doc timing including the release.md Approvals-table "
            "fallback, and feature timeline rollup), cross-reference "
            "linter clean across all 6 packs, both setup smoke-test "
            "suites (15 + 12), assert-output.sh's 33 structural "
            "assertions, the embedded dashboard JS re-verified with "
            "`node --check`, and a live end-to-end smoke test running "
            "the actual `sdd dashboard` HTTP server against a synthetic "
            "project confirming /api/status returns correct timing/"
            "timeline JSON and the page includes the new Timeline card",
        ],
    },
    {
        "from": "2.8.6",
        "to": "2.8.7",
        "description": "Removed IMPROVEMENT-BACKLOG.md from every pack -- it was maintainer-only content that sdd init was shipping into every real user's project",
        "notes": [
            "A user shared a photo of their own project directory (created "
            "via `sdd init`) showing IMPROVEMENT-BACKLOG.md sitting right "
            "there alongside README.md/QUICKSTART.md/etc. -- confirming a "
            "real bug rather than a hypothetical one",
            "IMPROVEMENT-BACKLOG.md existed in packs/sdd-backend-service, "
            "sdd-frontend-spa, sdd-mobile, and sdd-universal (sdd-fullstack "
            "never had it) as the *maintainer's own* internal notes about "
            "deferred pack-template work -- e.g. 'Add an "
            "observability-template.md if this pack is used for services "
            "with formal SLOs'. Nothing about it concerned an end user's "
            "own project",
            "Root cause: scaffold_pack() (sdd/utils/scaffold.py) copies a "
            "pack's entire folder into a user's project via "
            "pack_src.rglob('*') with zero exclusion filter -- unlike "
            "package.sh's zip builder, which already excludes .git/ and "
            "CLAUDE.local.md. This maintainer-only file had no such "
            "exclusion and landed in every real user's project, "
            "indistinguishable from anything actually meant for them",
            "Fix: deleted the file from all 4 packs (rather than adding "
            "an exclusion-list mechanism to scaffold_pack()/package.sh -- "
            "the user's explicit choice), removed its row from each of "
            "those packs' README.md 'Start Here' reference table, and "
            "consolidated all the actual content -- deduped, backend-"
            "service and universal were byte-identical -- into this "
            "maintainer repo's own OWNER-GUIDE.md as a new section '8. "
            "Deferred Improvement Items', since OWNER-GUIDE.md is already "
            "explicitly the maintainer-only document",
            "No functional code changed -- scaffold_pack.py itself is "
            "untouched. This is a content-only fix: 4 files deleted, 4 "
            "README rows removed, 1 new OWNER-GUIDE.md section added. A "
            "project that already has IMPROVEMENT-BACKLOG.md from an "
            "earlier `sdd init` keeps its local copy -- this migration "
            "doesn't delete anything from an existing project, it only "
            "stops the file from being scaffolded into new ones",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Verified: cli-python pytest 765/765 (unchanged -- no code "
            "touched, no test referenced IMPROVEMENT-BACKLOG.md), cross-"
            "reference linter clean across all 6 packs, both setup "
            "smoke-test suites (15 + 12), and a live smoke test actually "
            "running `sdd init` end-to-end confirming the scaffolded "
            "output (138 files) no longer includes IMPROVEMENT-BACKLOG.md",
        ],
    },
    {
        "from": "2.8.7",
        "to": "2.8.8",
        "description": "Root README '60-Second Overview' and a pack-catalog pointer on every pack's own README -- fixes a first-time-visitor orientation gap",
        "notes": [
            "An external (ChatGPT) review flagged that a newcomer to the "
            "maintainer repo's root README can't quickly answer 7 "
            "orientation questions: which pack, which CLI, the smallest "
            "useful workflow, how many documents get generated, whether "
            "Jira/Confluence is required, the first 3 commands to run, "
            "and whether this is for solo devs or teams. Checked the "
            "claim against the actual repo -- most were partially "
            "answered already, just buried rather than absent",
            "Added a '60-Second Overview' section to the top of the "
            "maintainer repo's root README.md, right after the intro "
            "paragraph: one audience line ('Built for teams that need "
            "audit trails...') plus a 4-row table -- CLI + Jira/"
            "Confluence optionality, the first 3 commands, document "
            "count, and a pointer to packs/CATALOG.md's decision tree",
            "The document-count figure (12 at pilot scope) was counted "
            "directly from the real examples/todo-api file listing, not "
            "guessed -- an initial draft said '~13' and was corrected "
            "against the actual file count before shipping, the same "
            "verify-before-claiming discipline used for every prior "
            "onboarding-friction round this chain",
            "Added a one-line 'not sure this is the right pack? see the "
            "catalog' pointer (absolute GitHub URL, matching the sdd-"
            "micro/examples redirect pattern from earlier rounds -- "
            "packs are distributed standalone once copied out of this "
            "repo) to the top of the 'Start Here' section in all 5 full "
            "packs' own README.md, so a visitor who lands directly on "
            "one pack's page (not the root) still gets routed to the "
            "decision tree",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain. Documentation-only: no functional code "
            "touched, no manifest.yml schema change",
            "Verified: cli-python pytest 765/765 (unchanged), cross-"
            "reference linter clean across all 6 packs, both setup "
            "smoke-test suites (15 + 12)",
        ],
    },
    {
        "from": "2.8.8",
        "to": "2.8.9",
        "description": "Dashboard security hardening: session token + Origin check for network writes, read-only sharing mode, and a fix for a real concurrent-write data-loss bug",
        "notes": [
            "Highest-priority item from a comprehensive ChatGPT-review "
            "verification pass -- this closes real, live gaps, not "
            "hypothetical ones. Dashboard write endpoints (POST /api/"
            "approve, POST /api/comment) had zero authentication when "
            "bound to a non-loopback address, only a printed console "
            "warning. There was also an unguarded concurrent-write race "
            "on .dashboard-comments.json -- ThreadingHTTPServer runs "
            "each request on its own thread with no lock around the "
            "read-modify-write cycle. Verified both: wrote a 12-thread "
            "concurrency test, confirmed it fails 5/5 without a lock, "
            "then confirmed it passes reliably once the fix is in place",
            "New --share flag (shortcut for --host 0.0.0.0) and --write "
            "flag (required to enable writes over a non-local bind). "
            "Three modes: `sdd dashboard` (unchanged -- 127.0.0.1, "
            "writes enabled, no token, zero friction for the default "
            "local case), `sdd dashboard --share` (network-reachable, "
            "read-only by default), `sdd dashboard --share --write` "
            "(network-reachable, writes enabled, gated by a session "
            "token)",
            "Session token: secrets.token_urlsafe(24), generated only "
            "when writes are enabled on a non-local bind, required via "
            "a custom X-SDD-Token header rather than a cookie -- a "
            "cookie would be sent automatically by the browser on any "
            "cross-origin request, which is what makes CSRF possible; a "
            "custom header only goes out on requests this page's own JS "
            "explicitly builds, so this one mechanism covers both the "
            "session-token and CSRF-protection asks from the review. "
            "The token is delivered via a one-time ?token= query param "
            "on the auto-opened URL, then stripped from the visible URL "
            "via history.replaceState so it doesn't linger in browser "
            "history",
            "Origin/Host header check as defense in depth on top of the "
            "token: rejects a write request with 403 if it carries an "
            "Origin header that doesn't match this server's own known "
            "addresses, checked before the token so a mismatched Origin "
            "is rejected even if a token somehow leaked",
            "New GET /api/dashboard-info endpoint (never includes the "
            "token itself) so the page's own JS can render an in-page "
            "network-sharing banner and hide/disable the Approve button "
            "and comment form when read-only -- the existing printed "
            "console warning was invisible to anyone using the "
            "dashboard from a different machine",
            "The default `sdd dashboard` invocation (no flags) is "
            "completely unaffected -- all 49 pre-existing dashboard "
            "tests still pass unchanged, plus a new explicit sanity "
            "test asserting the default state is local+open",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain. The dashboard itself is Python-only -- "
            "this bump has no corresponding functional change on the "
            "Node CLI side",
            "Verified: cli-python pytest 773/773 (765 pre-existing + 8 "
            "new), plus three live end-to-end smoke tests against a "
            "real running server in all three modes (default, --share, "
            "--share --write) confirming the token extracted from the "
            "printed console output actually works and wrong/missing "
            "tokens are rejected",
        ],
    },
    {
        "from": "2.8.9",
        "to": "2.8.10",
        "description": "manifest.py atomic writes + corrupt-file handling, and timeout/retry/backoff for all Jira/Confluence HTTP calls",
        "notes": [
            "Next tier from the same ChatGPT-review verification pass, "
            "closing two more real (not hypothetical) gaps found while "
            "verifying the review's claims against the actual code",
            "manifest.py: write_manifest() previously wrote directly to "
            ".specify/manifest.yml with write_text() -- a process killed "
            "mid-write (e.g. `sdd upgrade` interrupted) could leave a "
            "truncated file, and every command reads this file, so a "
            "truncated manifest broke the whole project. Now writes to a "
            "temp file in the same directory and os.replace()s it into "
            "place, which is atomic on both POSIX and Windows",
            "manifest.py: read_manifest() previously let a corrupt YAML "
            "file raise a raw yaml.YAMLError with no guidance. Now wraps "
            "the parse in try/except and raises a new ManifestError with "
            "an actionable message (fix by hand, restore from git, or "
            "delete and re-run `sdd init`). Deliberately distinct from a "
            "*missing* manifest, which still returns None as before -- a "
            "corrupt manifest means the project clearly exists, so "
            "silently treating it the same as absent risked a caller "
            "re-scaffolding over it or quietly dropping real config",
            "atlassian_auth.py: every Jira/Confluence API call goes "
            "through a requests.Session built by build_session() -- a "
            "flaky network blip or an Atlassian rate limit previously "
            "surfaced as a raw unhandled stack trace mid-workflow, since "
            "requests has no default timeout and no retry logic. Fixed "
            "once, centrally, by mounting a custom HTTPAdapter on the "
            "shared session instead of touching the ~25 individual call "
            "sites across jira_client.py and confluence_client.py: a "
            "20-second default timeout (requests.Session has no built-in "
            "way to set one, so overriding the adapter's send() is the "
            "standard workaround), plus 3 retries with exponential "
            "backoff on connection errors and on 429/500/502/503/504 "
            "responses, honoring a 429's Retry-After header",
            "Retries apply to every HTTP method including POST/PUT -- "
            "this codebase's writes already lean on label-based "
            "find-before-create idempotency where duplication would "
            "matter, and a connection blip silently aborting a document "
            "approval or Jira push partway through is worse than the "
            "small remaining risk of an occasional duplicate retry on a "
            "genuinely dropped response",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain. Both fixes are Python-only (manifest.py "
            "and atlassian_auth.py have no Node CLI equivalent) -- no "
            "functional change on the Node CLI side",
            "Verified: cli-python pytest 789/789 (773 pre-existing + 11 "
            "manifest.py tests + 5 atlassian_auth.py resilience tests), "
            "including atomicity proven via a monkeypatched os.replace() "
            "that asserts the destination still holds old content and "
            "the temp source holds new content at replace-time, and the "
            "retry logic proven against a real flaky local HTTP server "
            "(fails twice with 503 then succeeds) plus a control-case "
            "test showing a plain session without the adapter genuinely "
            "fails on the same server",
        ],
    },
    {
        "from": "2.8.10",
        "to": "2.8.11",
        "description": "Fix a real Python 3.9 import crash (PEP 604 `X | None` used without `from __future__ import annotations`) plus a ruff lint/format pass",
        "notes": [
            "Real bug, not a lint nitpick: 7 modules (init.py, upgrade.py, "
            "detect.py, manifest.py, scaffold.py, validate.py, plus one "
            "test file) used `str | None` / `dict | None` union syntax "
            "directly in function signatures with no `from __future__ "
            "import annotations` at the top of the file. PEP 604's `X | Y` "
            "union syntax is only evaluable at runtime from Python 3.10 "
            "onward -- on 3.9 (which pyproject.toml's own `requires-python "
            '= ">=3.9"` and classifiers claim to support), importing '
            "any of these modules raised `TypeError: unsupported operand "
            "type(s) for |` at function-definition time, before a single "
            "line of the CLI's own logic ever ran. Caught by ruff's FA102 "
            "rule while setting up CI's new ruff job (task #32 in this "
            "session's review-tracker) -- and would have been caught "
            "immediately by the Python 3.9 CI matrix job added one round "
            "earlier (v2.8.10 -> this bump's sibling change), since a "
            "3.9 job would fail on `sdd --help` alone",
            "Added ruff to CI (`ruff check .` + `ruff format --check .`), "
            "configured in cli-python/pyproject.toml's new [tool.ruff] "
            "section. Ran a full pass first: fixed or noqa'd (with a "
            "reason comment) everything ruff's default ruleset flagged "
            "except two deliberately-ignored rules -- ISC004 (674 hits, "
            "this codebase's own style of writing long prose as adjacent "
            "string literals in lists, not a bug) and BLE001 (67 hits, "
            "`except Exception:` -- flagged for a dedicated manual triage "
            "pass, tracked separately, not blanket-suppressed or blanket-"
            "narrowed blind)",
            "Applied `ruff format` across the whole package as its own "
            "prior isolated commit (no functional change, same test "
            "results before/after) so this commit's diff isn't dominated "
            "by pure reformatting noise",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain. Both fixes are Python-only; no Node CLI "
            "equivalent exists for either",
            "Verified: cli-python pytest 789/789 (unchanged pass count "
            "throughout this round), `ruff check .` and `ruff format "
            "--check .` both clean, and the specific fix confirmed via "
            "`ruff check . --select FA102` going from 11 hits to 0",
        ],
    },
    {
        "from": "2.8.11",
        "to": "2.8.12",
        "description": "Dashboard: confirmation dialog before an approval takes effect; dashboard HTML/CSS/JS moved from one giant Python string to real .css/.js/.html files",
        "notes": [
            "Real, user-visible dashboard behavior change: clicking Approve "
            "used to fire straight to the server after two window.prompt() "
            "calls (name, optional note). Now shows a window.confirm() "
            "summarizing the document, feature, approver name, and note "
            "before the request goes out, and bails out entirely if "
            "declined -- guards against an accidental click by an "
            "already-authorized user (the bigger risk, an *unauthorized* "
            "person approving, was already closed by the session-token "
            "work two rounds back)",
            "Also (no user-visible difference, verified byte-identical): "
            "the dashboard's HTML/CSS/JS -- previously one ~1050-line "
            "Python triple-quoted string with no editor syntax "
            "highlighting or linting -- now lives in real files under "
            "sdd/commands/dashboard_static/ (style.css, theme.js, app.js, "
            "page.html), assembled into the same single self-contained "
            "HTML response at import time. No new HTTP routes, no extra "
            "round-trips. Required adding those files to pyproject.toml's "
            "wheel/sdist `artifacts` lists -- confirmed by actually "
            "building the wheel and installing it into a clean venv, not "
            "just by reasoning about the hatchling config",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain. The dashboard is Python-only -- no "
            "corresponding change on the Node CLI side",
            "Verified: cli-python pytest 793/793 (789 pre-existing + 4 "
            "new), ruff check/format, mypy, and bandit all clean, coverage "
            "still 79% (above the 77% floor), and a real wheel build + "
            "clean-venv install confirming the dashboard's static files "
            "ship correctly and the page renders with no leaked "
            "placeholder tokens",
        ],
    },
    {
        "from": "2.8.12",
        "to": "2.8.13",
        "description": "Add lean/standard/regulated as friendly aliases for pilot/mvp/full scope",
        "notes": [
            "Real gap the review flagged: examples/todo-api (a real pilot-"
            "scope run) generates exactly 12 documents, and 'pilot' reads "
            "as a small, informal effort right up until a team sees the "
            "actual document count. A full rename of the scope vocabulary "
            "would be a breaking change to manifest.yml's schema and every "
            "pack's scope-gating logic, so this ships a much smaller, "
            "safe version instead: lean/standard/regulated are accepted "
            "as friendlier input names wherever scope is set "
            "(setup.sh/setup.ps1's --scope, sdd init's -s/--scope), "
            "resolved to the canonical pilot/mvp/full before anything is "
            "written. manifest.yml's own scope: field, and every gate/"
            "command that reads it, never sees the aliases -- no "
            "downstream logic needed to change",
            "Also added real input validation that didn't exist before: "
            "an unrecognized --scope value (a typo, or anything outside "
            "the 6 accepted spellings) is now rejected with a clear error "
            "instead of being silently written into manifest.yml as-is",
            "Updated in all three implementations that set scope: "
            "packs/_shared/full/setup.sh and setup.ps1 (synced to 4 of "
            "the 5 full packs), sdd-universal's own separate setup.sh/"
            "setup.ps1 copies, and cli-python's sdd init -s/--scope flag. "
            "Documented in the root CLAUDE.md's Scope Levels section and "
            "the shared scope-reference block (propagated to every pack's "
            "own CLAUDE.md via sync-blocks.sh)",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain. The Node CLI's own init/upgrade "
            "scaffolding doesn't take a --scope flag today, so there's no "
            "corresponding code change on that side",
            "Verified: cli-python pytest 797/797 (793 pre-existing + 4 "
            "new), ruff check/format, mypy, and bandit all clean, "
            "coverage still 79%; setup.sh smoke suite extended with 3 "
            "alias-resolution cases + 1 invalid-scope rejection case (19/"
            "19 passing), cross-reference checker and sync-drift check "
            "both clean across all 6 packs, and a direct manual run "
            "against a synced pack (sdd-backend-service) confirming both "
            'the happy path (--scope lean -> scope: "pilot") and the '
            "rejection path (--scope not-real -> exit 1) end to end",
        ],
    },
    {
        "from": "2.8.13",
        "to": "2.8.14",
        "description": "Dashboard: require the session token for /api/review-links even in read-only --share mode",
        "notes": [
            "Closes a gap found during a second external review pass: "
            "read-only share mode (--share without --write) already "
            "blocked POST /api/approve and /api/comment without a token, "
            "but GET /api/review-links was never gated at all -- it makes "
            "a live call to Jira/Confluence using the credentials stored "
            "on the machine running `sdd dashboard`, for whatever "
            "--feature the caller names, regardless of read-only status. "
            "'Read-only' only ever meant 'no local file writes'; it never "
            "meant 'no outbound calls under this machine's credentials'",
            "Fix: token generation in dashboard_command() now happens for "
            "any non-local bind (previously only when --write was also "
            "passed), and a new _check_review_links_access() helper "
            "(reusing the existing Origin+token check) gates the "
            "/api/review-links handler, skipped only when the bind is "
            "local. Approve/comment endpoints are unchanged -- they still "
            "go through _check_write_access(), which now delegates its "
            "Origin/token check to the same shared helper",
            "Also reworded the console output and the in-page info banner "
            "to state plainly that 'Check Jira/Confluence status' is not "
            "affected by read-only mode and always requires the token",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain. The Node CLI has no dashboard command, so "
            "there's no corresponding code change on that side",
            "Verified: cli-python pytest 817/817 (812 pre-existing + 5 "
            "new access-control tests for /api/review-links), ruff check/"
            "format, mypy, and bandit all clean",
        ],
    },
    {
        "from": "2.8.14",
        "to": "2.8.15",
        "description": "Add package-verify CI job proving a clean pip install actually works; add sdd init --ai-tool flag",
        "notes": [
            "A second external review round flagged that CI never verifies "
            "the packaging path end to end: sdd/packs/ is gitignored and "
            "only populated by publish.sh's manual bundling step right "
            "before a real PyPI upload, so nothing catches a wheel built "
            "without that step. This was proven to be a live bug, not a "
            "hypothetical one: a wheel built the way CI already builds it "
            "(pip install ./cli-python, no publish.sh), installed into a "
            "venv outside the repo, and run via `sdd init` from a real-"
            "world project directory, failed with 'SDD pack files not "
            "found.' scaffold.py's dev-fallback (walk up to a git "
            "checkout's packs/ directory) silently masks this in any CI "
            "job or dev environment that still has the full repo checked "
            "out, which is every environment this project's CI used until "
            "now",
            "New 'package-verify' CI job: bundles packs the same way "
            "publish.sh does, builds sdist+wheel via `python -m build` "
            "(sdist->wheel path, not --wheel alone, since that alone "
            "would miss a build backend that only bundles gitignored "
            "files into the wheel target's own artifacts config, not the "
            "sdist's), asserts both archives contain "
            "sdd/packs/sdd-universal/setup.sh, installs the wheel into a "
            "clean venv, and runs a full `sdd init` from a scratch "
            "directory outside the repo -- this is the exact reproduction "
            "that first surfaced the bug, now guarded permanently in CI",
            "The same assertion (wheel/sdist actually contain the bundled "
            "packs) is now also run inside publish.sh itself, between the "
            "build and upload steps, so a manual publish run outside CI "
            "can't ship a broken package either",
            "Along the way, running `sdd init` fully non-interactively for "
            "the CI job surfaced a real, separate gap: every other "
            "interactive prompt (project type, scope, plan mode, reading "
            "mode) already had a CLI flag override, but 'Which AI tool "
            "will you use?' did not -- it was the one prompt with no way "
            "to skip, so any fully unattended `sdd init` (CI, scripts, "
            "this new package-verify job) would hang or abort on a "
            "non-interactive stdin. Added --ai-tool (claude-code | "
            "copilot | cursor | windsurf | other), validated the same way "
            "--scope is",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain. The Node CLI's own init scaffolding has no "
            "AI-tool prompt to begin with, so there's no corresponding "
            "code change on that side",
            "Verified: cli-python pytest 819/819 (817 pre-existing + 2 "
            "new --ai-tool tests), ruff check/format, mypy, and bandit all "
            "clean; the full package-verify sequence (bundle -> build -> "
            "assert contents -> clean venv install -> sdd init from "
            "outside the repo) was run manually end to end before adding "
            "it to CI, confirming both the failure it catches and the fix",
        ],
    },
    {
        "from": "2.8.15",
        "to": "2.8.16",
        "description": "Fix a silent detect.js bug: Terraform (.tf) projects were never detected as iac",
        "notes": [
            "cli/src/utils/detect.js's Terraform-file check called "
            "require('fs').readdirSync(...) inside a try/catch -- but "
            "this file is loaded as an ES module ('type': 'module' in "
            "cli/package.json), where require is not defined at all. The "
            "resulting ReferenceError was silently swallowed by the "
            "catch, so this branch always returned false: a pure-"
            "Terraform project with no Pulumi.yaml or cdk.json was never "
            "detected as 'iac' by the Node CLI's project-type auto-"
            "detection",
            "Fixed by importing readdirSync at the top of the file "
            "alongside the module's other fs calls (existsSync, "
            "readFileSync), instead of a runtime require(). Verified the "
            "bug and the fix directly: require('fs') throws 'require is "
            "not defined' in a real ESM context, and a scratch directory "
            "containing only a .tf file now correctly detects as 'iac' "
            "where it previously fell through to null",
            "New cli/tests/detect.test.js covers this case directly (plus "
            "a no-markers-detected sanity check) -- the Node CLI had no "
            "detect.js test coverage at all before this",
            "This Python CLI's own detect.py does exact dependency-key "
            "matching (no shell-out, no require()) and was never affected "
            "-- this migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Verified: cli-python pytest 824/824 unaffected; cli node "
            "--test 6/6 (4 pre-existing + 2 new), npm test and the --help "
            "smoke test both pass",
        ],
    },
    {
        "from": "2.8.16",
        "to": "2.8.17",
        "description": "Widen js-yaml's declared range; friendly error on dashboard port conflict; make dashboard's page assembly lazy",
        "notes": [
            "cli/package.json's js-yaml dependency was pinned to ^4.1.0 "
            "(effectively <5.0.0), even though an earlier fix "
            "(import * as yaml, not the default export) already made the "
            "code work correctly under js-yaml 5.x -- verified again here "
            "by actually installing js-yaml@5.2.3 and re-running the full "
            "test suite + --help smoke test. Widened to >=4.1.0 <6.0.0 so "
            "users aren't held back from picking up js-yaml security/bug "
            "fixes for no real reason",
            "sdd dashboard binding to a port already in use used to "
            "surface as a raw, unhandled OSError traceback. Wrapped the "
            "ThreadingHTTPServer(...) call in a try/except OSError that "
            "prints a clear message and, specifically for EADDRINUSE, "
            "suggests --port as the way out, then exits 1 cleanly. New "
            "test simulates the collision with a real bound socket and "
            "asserts no traceback reaches the user",
            "dashboard.py's _load_page() (assembles the dashboard's HTML "
            "page from dashboard_static/*.css/*.js/*.html) used to run at "
            "import time -- and dashboard.py is imported by sdd/__main__.py "
            "unconditionally, so every single `sdd` invocation (sdd "
            "--help, sdd init, anything) paid the cost of reading and "
            "concatenating those 4 files even when nowhere near the "
            "dashboard command. Now @lru_cache(maxsize=1)'d and only "
            "assembled on the first request that actually needs it",
            "This Node CLI ships from the same pack sources -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain. The port-conflict and lazy-page changes "
            "are cli-python-only (the Node CLI has no dashboard command)",
            "Verified: cli-python pytest 825/825 (824 pre-existing + 1 "
            "new port-conflict test), ruff check/format, mypy, and bandit "
            "all clean; cli node --test 6/6 unaffected, npm test and the "
            "--help smoke test both pass under js-yaml 5.2.3",
        ],
    },
    {
        "from": "2.8.17",
        "to": "2.8.18",
        "description": "Fix two real project-type misdetection bugs; add ~20-fixture cross-implementation test coverage",
        "notes": [
            "Building a shared fixture-test suite across all detection "
            "implementations (the last item from the second external "
            "review round) surfaced two real, previously-unnoticed bugs, "
            "fixed alongside the new tests:",
            "(1) setup.sh/setup.ps1 (sdd-universal's auto-detect, used "
            "when project_type is left as 'auto'): a plain substring/"
            "word-boundary check on the 'react-native' dependency name "
            "also matched 'react-native-web' -- a real, common npm "
            "package for running React Native components on the web, not "
            "a mobile project. The '-' immediately after 'native' is "
            "already a regex word boundary, so \\b didn't exclude it "
            "either; fixed with a space-padded whole-token match instead. "
            "detect.py/detect.js already did exact list/array membership "
            "and never had this bug",
            "(2) detect.py/detect.js: the Angular check used "
            "d.startswith('angular'), which no real Angular 2+ project "
            "satisfies -- they depend on scoped packages like "
            "'@angular/core', which start with '@', not 'angular'. Only "
            "ancient AngularJS 1.x used the bare 'angular' package name. "
            "Fixed by switching to a substring check, matching setup.sh/"
            "setup.ps1's existing (correct) behavior. This means real "
            "Angular projects using sdd-universal's Python/Node auto-"
            "detect path were silently falling through to no detection "
            "at all until now",
            "New: cli-python/tests/test_detect.py, cli/tests/detect.test.js "
            "(extended), and packs/_shared/tests/test-detect-fixtures.sh "
            "(new, wired into the setup-smoke-tests CI job) all assert "
            "the same ~20 synthetic project fixtures against their "
            "respective implementation -- there was no dedicated "
            "detection test coverage at all before this in any of the "
            "three",
            "Scoped down from the review's original 'make detect.py "
            "canonical, have setup.sh/setup.ps1 shell out to it' "
            "suggestion: shelling out would require a Python "
            "installation as a hard runtime dependency of pack setup "
            "scripts, which currently only soft-depend on python3 for "
            "package.json parsing (with no fallback if it's absent). "
            "Keeping four independent implementations in sync via "
            "identical fixture tests achieves the same actual goal -- "
            "catching divergence -- without that new dependency",
            "setup.ps1 has the equivalent fix but isn't covered by an "
            "automated fixture loop (no pwsh available in every "
            "environment this session's tests ran in) -- verified by "
            "direct code inspection: PowerShell's -match operator has "
            "the identical non-anchored substring semantics as bash's "
            "grep -E, so the same space-padded token-match fix applies "
            "identically. Windows CI (windows-setup-smoke-test) at least "
            "validates setup.ps1 parses and runs",
            "Verified: cli-python pytest 848/848 (825 pre-existing + 23 "
            "new), ruff check/format, mypy, and bandit all clean; cli "
            "node --test 27/27; bash test-detect-fixtures.sh 23/23; "
            "sync-drift check and cross-reference checker both clean",
        ],
    },
    {
        "from": "2.8.18",
        "to": "2.8.19",
        "description": "Add Python 3.13 and 3.14 to the tested/declared version range",
        "notes": [
            "CI's python-cli-sanity matrix only covered 3.9-3.12, but "
            "pypistats.org's own download breakdown for sddflow showed "
            "real installs already happening on Python 3.14 with zero CI "
            "coverage for it -- prompted by a real user question about "
            "when 3.9 support was added, which surfaced the matrix was "
            "stale on the new-version end too, not just the old-version "
            "end",
            "Added '3.13' and '3.14' to python-cli-sanity's matrix, and "
            "the matching classifiers to pyproject.toml. Verified with "
            "the real Python 3.13.12 interpreter (installed locally, not "
            "simulated): clean pip install, byte-compile, --help smoke "
            "test, and the full pytest suite (848/848) all pass "
            "unchanged. Python 3.14 has no local interpreter available "
            "to verify directly in this environment -- CI's "
            "actions/setup-python will be the first real verification "
            "for it",
            "No code changes needed -- the codebase already builds "
            "cleanly on 3.13, consistent with there being no 3.9-only "
            "syntax debt left after the from __future__ import "
            "annotations fix in v2.8.11",
            "This Node CLI has no equivalent Python version matrix (it's "
            "a Node.js package) -- this migration entry exists so both "
            "CLIs report the same sdd_version chain",
            "Verified: cli-python pytest 848/848 under both the default "
            "interpreter and a real Python 3.13.12 venv; ruff check/"
            "format, mypy, and bandit all clean",
        ],
    },
    {
        "from": "2.8.19",
        "to": "2.8.20",
        "description": "Drop Python 3.9 support -- requires-python is now >=3.10",
        "notes": [
            "Python 3.9 reached end-of-life in October 2025 (no more "
            "security patches from CPython upstream) -- a deliberate "
            "maintainer decision to stop supporting it, made right after "
            "the previous release added 3.13/3.14 to the tested range "
            "and prompted a look at the old end of the matrix too",
            "requires-python bumped from '>=3.9' to '>=3.10' in "
            "pyproject.toml; the '3.9' classifier and CI matrix entry "
            "removed. This is a real breaking change -- `pip install "
            "sddflow` (or any upgrade) now refuses outright on Python "
            "3.9, verified by inspecting the built wheel's METADATA: "
            "'Requires-Python: >=3.10' is correctly embedded, which is "
            "what pip actually checks before installing, on any Python "
            "version, without needing a 3.9 interpreter present to "
            "verify the rejection",
            "Bumping ruff's target-version from py39 to py310 (matching "
            "the new floor) surfaced two real modernization findings "
            "ruff couldn't previously suggest (they require 3.10+): "
            "typing.Callable -> collections.abc.Callable in upgrade.py, "
            "and manual zip(chain, chain[1:]) -> itertools.pairwise() in "
            "test_upgrade.py. Both fixed",
            "The from __future__ import annotations guards added in "
            "v2.8.11 (for the Python 3.9 crash fix) were left in place "
            "rather than removed -- they're harmless no-ops on 3.10+ and "
            "removing them would be pure unnecessary churn",
            "This Node CLI has no Python version floor of its own (it's "
            "a Node.js package) -- this migration entry exists so both "
            "CLIs report the same sdd_version chain",
            "Verified: cli-python pytest 848/848 on both a real Python "
            "3.10.20 interpreter (the new floor) and a real Python "
            "3.13.12 interpreter; ruff check/format, mypy, and bandit "
            "all clean; wheel METADATA inspected directly to confirm "
            "the Requires-Python constraint took effect",
        ],
    },
    {
        "from": "2.8.20",
        "to": "2.8.21",
        "description": (
            "Fix a severe bug in the published Node CLI: every "
            "interactive `sdd init` (and the AI-tool prompt in `sdd "
            "upgrade`) crashed with UnknownPromptTypeError"
        ),
        "notes": [
            "Dependabot bumped the Node CLI's inquirer dependency from "
            "9.2.0 to 14.0.2 (merged into main, inherited by this repo's "
            "release branch during an earlier PR's merge-conflict "
            "resolution). inquirer 9+ dropped the legacy 'list' prompt "
            "type in favor of 'select' -- inquirer.prompt() throws for "
            "any unregistered type string, so this broke every "
            "interactive sdd init for anyone not passing every single "
            "CLI flag (there's no flag to skip the AI-tool prompt)",
            "Found by actually running a real interactive `sdd init` "
            "against a clean install of the live, already-published npm "
            "package while answering an unrelated question about "
            "functional parity between the two CLIs -- none of the "
            "existing automated tests caught this because they only "
            "exercised migration-chain logic, never a real inquirer "
            "prompt call",
            "Fixed cli/src/commands/init.js (5 occurrences) and "
            "cli/src/commands/upgrade.js (1 occurrence): "
            "type: 'list' -> type: 'select'. Also fixed a silent "
            "secondary bug in init.js's scope prompt: the new "
            "@inquirer/select prompt's `default` option is compared "
            "against the choice's *value*, not an index into the "
            "choices array like the old 'list' type -- "
            "SCOPES.indexOf(...) was replaced with the actual default "
            "scope value",
            "Added cli/tests/inquirer-prompt-types.test.js: a "
            "regression test that scans every inquirer.prompt() call "
            "in src/commands/*.js, extracts each type: '...' string "
            "used, and asserts it's a member of the installed "
            "inquirer's own currently-registered prompt types (read "
            "live from inquirer.prompt.prompts, not hardcoded) -- a "
            "future inquirer upgrade that renames or drops a type this "
            "codebase depends on now fails this test immediately "
            "instead of only surfacing as a crash for a real user",
            "This Python CLI never used inquirer (it's a Node package) "
            "and is unaffected by the underlying bug -- this migration "
            "entry exists only so both CLIs report the same "
            "sdd_version chain",
            "Verified: real clean install of the fixed Node CLI, real "
            "PTY-based interactive `sdd init` run (piped stdin doesn't "
            "work against modern @inquirer/* prompts, which require "
            "raw-mode TTY input) confirmed the full flow completes and "
            "writes a correct manifest.yml; cli node --test 28/28 "
            "(27 pre-existing + 1 new); cli-python pytest 848/848",
        ],
    },
    {
        "from": "2.8.21",
        "to": "2.8.22",
        "description": (
            "Fix a real Confluence-review-loop bug: `sdd confluence pull` "
            "flattened every markdown table into one run-on line"
        ),
        "notes": [
            "Reported by a user testing the Confluence review round-trip "
            "on a real project: create a draft via `sdd confluence "
            "draft`, edit it in Confluence, then `sdd confluence pull` "
            "to bring the edits back. Every markdown table in the "
            "pulled-back document came back as a single line of "
            "concatenated cell text with no row or column structure -- "
            "silently corrupting any table-heavy doc (Tech Stack in "
            "context.md, and BRD/SRD/design docs generally)",
            "Root cause: sdd/utils/cf_to_md.py (the Confluence-storage-"
            "format-to-Markdown converter used by `confluence pull`) had "
            "no <table> handling at all. Confluence storage format "
            "renders a table as an unbroken "
            "<table><tbody><tr><th>...</th></tr>...</tbody></table> "
            "string with no whitespace between tags (see "
            "md_to_cf.py's _render_table(), the push-direction "
            "counterpart) -- with no table-aware step, cf_to_md.py's "
            "final 'strip any remaining HTML tags' pass just deleted "
            "the table/row/cell tags and left the cell text jammed "
            "together, since (unlike its handling for <li> and <p>) it "
            "never inserted a newline or delimiter for table structure",
            "This is the same bug class md_to_cf.py (the push direction) "
            "already had fixed once before, per test_md_to_cf.py's "
            "TestTables -- the pull direction just never got the "
            "equivalent treatment, and there was no cf_to_md.py test "
            "file at all before this fix to have caught it",
            "Fixed by adding a _table_to_md() converter to cf_to_md.py: "
            "extracts <table>...</table>, reconstructs a GFM pipe table "
            "(header row, alignment-marker separator row from any "
            "style=\"text-align:...\" on the header cells, body rows), "
            "re-escapes any literal '|' in cell text back to '\\|' "
            "(the inverse of the push side's unescape), and pads a "
            "body row that has fewer cells than the header. Inserted "
            "into the pipeline after the existing bold/italic/inline-"
            "code/link conversions (so cell content is already "
            "markdown-formatted) and before the generic tag-stripping "
            "step",
            "This Node CLI has no Confluence integration at all "
            "(scaffolding-only by design) and is unaffected -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Added tests/test_cf_to_md.py (new file, 10 tests): full "
            "md_to_storage() -> cf_to_md() round-trip coverage for "
            "simple tables, wide multi-row tables (the exact shape "
            "reported broken), alignment markers, inline formatting "
            "inside cells, an escaped literal pipe in a cell, a ragged "
            "body row shorter than the header, a table followed by a "
            "paragraph, a heading before a table, two tables in one "
            "document, and a table-free document (regression guard "
            "against the new table regex misfiring on unrelated "
            "content)",
            "Verified: cli-python pytest 858/858 (848 pre-existing + 10 "
            "new); ruff check/format and mypy both clean; manual "
            "round-trip test through the real md_to_storage()/cf_to_md() "
            "pair confirmed byte-for-byte table fidelity including "
            "alignment, inline code, bold, links, and an escaped "
            "literal pipe",
        ],
    },
    {
        "from": "2.8.22",
        "to": "2.8.23",
        "description": (
            "Fix two real integrations.yml bugs: `sdd jira push --level "
            "epic` crashed with a raw AttributeError on a malformed "
            "config value, and a bare `sdd confluence push` never "
            "included the Constitution page"
        ),
        "notes": [
            "Bug 1 -- reported by a user: `sdd jira push --level epic` "
            "crashed with `AttributeError: 'dict' object has no "
            "attribute 'replace'` deep inside jira_client.py's "
            "find_by_label(). The user root-caused their own instance: "
            "a hand-edited integrations.yml had a second `project_key:` "
            "block under `jira:` that should have been `project_keys:` "
            "(plural, for the per-level override section) -- YAML "
            "silently keeps only the LAST occurrence of a duplicate "
            "mapping key, so the plain string from the first block was "
            "clobbered by a dict from the second, and jira.project_key "
            "resolved to a dict instead of a string",
            "Fixed with two independent hardening layers in "
            "sdd/utils/integrations.py: (1) load_integrations() now "
            "parses integrations.yml with a custom PyYAML loader "
            "(_DuplicateKeyLoader) that rejects a duplicate mapping key "
            "anywhere in the file at parse time, naming the exact line "
            "number and -- when the key is 'project_key' specifically -- "
            "suggesting the likely fix ('did you mean \"project_keys\"'); "
            "(2) JiraConfig.key_for()/parent_field_for() now validate "
            "the resolved value is actually a string, raising a new "
            "JiraConfigError naming the exact bad YAML key instead of "
            "letting a malformed value silently propagate three call "
            "frames deep into a low-level HTTP helper. New "
            "IntegrationsConfigError/JiraConfigError exception types; "
            "every load_integrations() call site across jira.py, "
            "confluence.py, cr.py, review.py, pr.py, dashboard.py, "
            "config.py, and status.py updated to catch the new error "
            "type alongside the existing FileNotFoundError handling",
            "Also fixed a related, independently-discovered naming gap "
            "while investigating: the CLI's own `--level epic` flag "
            "(jira.py's _LEVELS) has no relationship to the config-facing "
            "level key 'feature' used throughout project_keys / "
            "custom_fields_by_level / parent_field_by_level -- and "
            "jira.py's own code always resolves via key_for('feature'), "
            "never key_for('epic'). A user writing `project_keys: {epic: "
            "SUN}` (the natural thing to write, matching the CLI's own "
            "terminology) was silently ignored with no error at all. "
            "key_for()/fields_for()/parent_field_for() now accept "
            "'epic' as a bidirectional alias for 'feature'",
            "Bug 2 -- found while investigating a second user report: "
            "`sdd confluence draft --doc constitution` works fine (the "
            "title/path resolution for 'constitution' is fully special-"
            "cased and doesn't touch page_map at all), but a bare `sdd "
            "confluence push` (no --doc, the normal flow right after "
            "create-context) iterates page_map.keys() -- and both "
            "_DEFAULT_PAGE_MAP (the code fallback used when "
            "integrations.yml has no explicit page_map: override, which "
            "is what `sdd config init`'s wizard produces) and the "
            "wizard's own _integrations_template() omitted the "
            "'constitution' key entirely, even though the full "
            "integrations.yml.example reference file already had it -- "
            "confirmed by that file's own comment on the key ('this key "
            "only controls whether a bare sdd confluence push includes "
            "it'). A clean drift bug: the .example file was updated for "
            "this reason at some point, the other two definitions of "
            "the default doc set never were",
            "Fixed by adding 'constitution' to both _DEFAULT_PAGE_MAP "
            "(sdd/utils/integrations.py) and the wizard template's "
            "page_map block (sdd/commands/config.py's "
            "_integrations_template())",
            "This Node CLI has no Jira/Confluence integration at all "
            "(scaffolding-only by design) and is unaffected by either "
            "fix -- this migration entry exists so both CLIs report the "
            "same sdd_version chain",
            "Added 11 new tests: 9 in tests/test_config_and_integrations.py "
            "(TestJiraConfigRobustness -- duplicate-key detection at "
            "load time incl. the exact reported shape, the line-number "
            "and suggested-fix message, a duplicate key elsewhere in the "
            "file, wrong-shape project_key/parent_field values, the "
            "epic/feature alias in both directions including that an "
            "explicit 'feature' entry isn't overridden by an 'epic' one, "
            "and a well-formed file loading completely unaffected by the "
            "stricter loader) plus updated EXPECTED_DOC_KEYS coverage; "
            "2 in tests/test_confluence_push_cli.py (a bare push now "
            "creates the Constitution page from a wizard-shaped "
            "integrations.yml with no page_map override, and explicit "
            "--doc constitution continues to work)",
            "Verified: cli-python pytest 869/869 (858 pre-existing + 11 "
            "new); ruff check/format clean; mypy --ignore-missing-imports "
            "(matching CI's exact invocation) clean with no issues in 31 "
            "source files; manually reproduced the exact reported "
            "duplicate-key YAML shape and confirmed it now raises a "
            "clear IntegrationsConfigError instead of crashing",
        ],
    },
    {
        "from": "2.8.23",
        "to": "2.8.24",
        "description": (
            "Fix dashboard GATE-1 false positive: token-usage.md alone "
            "in a feature directory was mistaken for a real downstream "
            "spec doc, showing 'GATE-1 -- Constitution Finalized' as "
            "passed immediately after /specify, before the user ever "
            "confirmed finalization in chat"
        ),
        "notes": [
            "Reported by a user: the dashboard showed a checkmark next "
            "to 'GATE-1 -- Constitution Finalized' right after /specify "
            "created the constitution DRAFT, even though they had never "
            "told the agent 'Constitution Part 2 finalized' in chat. "
            "Confirmed via direct question -- they answered 'Never "
            "confirmed -- straight after /specify'",
            "Root cause: constitution.md has no machine-readable Draft/"
            "Finalized flag by design (GATE-1 confirmation is chat-only, "
            "per specify.prompt.md), so status.py's "
            "_constitution_status() infers gate1_inferred purely from "
            "whether any file besides tasks.md/*.summary.md exists in "
            ".specify/features/{feature}/. But token-usage.md is written "
            "into that same directory by /specify itself (and even "
            "/create-context, which runs before /specify) whenever "
            "token-pricing.yml is configured -- both commands run before "
            "GATE-1 can possibly pass. The heuristic's exclusion list "
            "only ever accounted for tasks.md and *.summary.md, so a "
            "project with token logging enabled hit a false positive on "
            "every single run",
            "Fixed in sdd/utils/status.py's _constitution_status(): "
            "token-usage.md now joins tasks.md in the set of filenames "
            "excluded from the any_downstream check",
            "This Node CLI has no dashboard at all (scaffolding-only by "
            "design) and is unaffected -- this migration entry exists "
            "so both CLIs report the same sdd_version chain",
            "Added 2 new tests to tests/test_status.py: "
            "test_constitution_gate1_pending_when_only_token_usage_file_exists "
            "(the exact reported false positive) and "
            "test_constitution_gate1_passed_when_downstream_doc_exists_alongside_token_usage "
            "(confirms a real downstream doc still correctly reports "
            "'passed' even with token-usage.md present alongside it)",
            "Verified: cli-python pytest 871/871 (869 pre-existing + 2 "
            "new); ruff check/format and mypy --ignore-missing-imports "
            "(matching CI's exact invocation) both clean on the changed "
            "files -- the pre-existing E741/E402 ruff hits and the "
            "'Library stubs not installed' mypy notes elsewhere in the "
            "codebase were confirmed present on a clean checkout before "
            "this change too, unrelated to it",
        ],
    },
    {
        "from": "2.8.24",
        "to": "2.8.25",
        "description": (
            "Fix dashboard 'not set in roles.yml' false negative: a "
            "fully filled-in roles.yml still showed no expected approver, "
            "because every real template's Approvals table Role cell "
            "carries a RACI annotation the role-key matcher never "
            "stripped"
        ),
        "notes": [
            "Reported by a user: filled in every role in roles.yml "
            "(product_owner, business_analyst, etc., each with a real "
            "name), but the dashboard's BRD Approvals detail panel still "
            "showed nothing for the pending rows",
            "Root cause: status.py's _normalize_role_key() converts a "
            "document's Approvals-table Role cell text to roles.yml's "
            "snake_case key convention ('Product Owner' -> "
            "'product_owner') so the two can be matched up. But every "
            "shipped template's actual Role cell carries a RACI "
            "annotation in parentheses -- e.g. brd-template.md's real "
            "text is 'Product Owner (accountable -- business objectives "
            "sign-off)', not bare 'Product Owner'. Normalizing the full "
            "string produced "
            "'product_owner_accountable_business_objectives_sign_off', "
            "which never matches any roles.yml key -- a 100% miss rate "
            "across every role, in every document, in every project, "
            "regardless of how completely roles.yml was filled in. The "
            "pre-existing tests never caught this because they only ever "
            "exercised bare role labels ('Product Owner'), not the real "
            "template shape",
            "Fixed in sdd/utils/status.py's _normalize_role_key(): now "
            "strips everything from the first '(' onward before "
            "normalizing, so 'Product Owner (accountable -- ...)' and "
            "'DevOps/SRE (consulted -- ...)' resolve the same as their "
            "bare forms did",
            "This Node CLI has no dashboard at all (scaffolding-only by "
            "design) and is unaffected -- this migration entry exists "
            "so both CLIs report the same sdd_version chain",
            "Added 3 new tests to tests/test_status.py: "
            "test_normalize_role_key_strips_raci_annotation_from_real_template_shape "
            "(unit-level, every real Role-cell shape from the shipped "
            "templates), "
            "test_resolve_expected_approver_with_real_template_role_label "
            "(through the public resolver), and "
            "test_feature_docs_approvals_resolve_expected_approver_with_real_brd_role_label "
            "(end-to-end through build_feature_status with a real "
            "roles.yml and a real BRD-shaped Approvals table -- the "
            "exact reported scenario)",
            "Verified: cli-python pytest 874/874 (871 pre-existing + 3 "
            "new); ruff check/format and mypy --ignore-missing-imports "
            "(matching CI's exact invocation) both clean on the changed "
            "files",
        ],
    },
    {
        "from": "2.8.25",
        "to": "2.8.26",
        "description": (
            "Fix 'Error loading the extension!' on Confluence: the Jira "
            "review status banner used a macro name Confluence doesn't "
            "actually have"
        ),
        "notes": [
            "Reported by a user: right after approving a BRD, its "
            "Confluence page showed 'Error loading the extension!' where "
            "the 'Jira review: VALT-1 -- Approved' banner should be",
            "Root cause: review.py's _jira_status_banner() maps review "
            "status to a Confluence panel macro name -- "
            "{'APPROVED': 'success', 'NEEDS_REVISION': 'warning'}, "
            "default 'info'. Confluence's built-in panel macros are only "
            "info/tip/note/warning -- there is no 'success' macro, so "
            "the page tried to render an unregistered extension and "
            "showed the generic error instead. This was invisible until "
            "now because PENDING (the only status a fresh review ticket "
            "starts in) correctly used 'info' -- the bug only fires once "
            "a real document reaches APPROVED",
            "Fixed by mapping APPROVED to 'tip' (a real Confluence panel "
            "macro, renders as a green highlighted box) instead of the "
            "nonexistent 'success'",
            "This Node CLI has no Jira/Confluence integration at all "
            "(scaffolding-only by design) and is unaffected -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Updated tests/test_review_helpers.py's "
            "test_banner_for_approved_status to assert the real macro "
            "name and explicitly assert the invalid one is gone",
            "Verified: cli-python pytest 874/874; ruff check/format "
            "clean; mypy --ignore-missing-imports (matching CI's exact "
            "invocation) clean on the changed files",
        ],
    },
    {
        "from": "2.8.26",
        "to": "2.8.27",
        "description": (
            "Standardize the {Feature Name} document-header placeholder "
            "on manifest.yml project.name -- it previously had no "
            "defined source and silently drifted to context.md's own "
            "title instead"
        ),
        "notes": [
            "Reported by a user: a generated BRD's '# Feature: {Feature "
            "Name}' header showed 'NIPE Validation Service' while "
            "manifest.yml said name: Validation -- the two had silently "
            "diverged",
            "Root cause: {Feature Name} is used as a header placeholder "
            "in ~20 templates across every pack (BRD, SRD, use-cases, "
            "design, tasks, release, etc.), but only ONE place in any "
            "prompt file ever explicitly defined what it should resolve "
            "to -- the Jira Epic Summary line in specify-brd.prompt.md "
            "('Feature Name from manifest.yml project.name, or "
            "project.feature if absent'). Every document-header instance "
            "was left to each session's judgment, so it could drift to "
            "context.md's own free-text title ('# System Context -- "
            "{Service Name}') instead, and could even differ "
            "document-to-document within the same project",
            "Fixed by adding a new shared block, "
            "_shared/blocks/feature-name-convention.md, inserted into "
            "each pack's CLAUDE.md right after the 'Confirm: "
            "project.name, scope, feature, context_file' startup step "
            "(read at the start of every session, so it's in context "
            "before any document is generated). States explicitly: "
            "{Feature Name} = manifest.yml project.name (fallback "
            "project.feature), never context.md's title",
            "Applied to all 5 lockstep packs (backend-service, "
            "frontend-spa, fullstack, mobile, universal) -- sdd-micro is "
            "intentionally excluded from the shared-block sync system "
            "per its own CLAUDE.md and has no BRD/SRD/etc. templates "
            "using this placeholder",
            "This Node CLI has no CLAUDE.md content of its own "
            "(scaffolding-only by design) and is unaffected -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Verified: python3 packs/_shared/tests/check-cross-"
            "references.py --verbose clean across all 6 packs; "
            "packs/_shared/tests/test-setup.sh (19/19) and "
            "test-setup-micro.sh (12/12) both pass; manually confirmed "
            "the same shared-block content appears identically in all 5 "
            "packs' CLAUDE.md",
        ],
    },
    {
        "from": "2.8.27",
        "to": "2.8.28",
        "description": (
            "Per-level Jira issue type overrides (review/chg/cr) now "
            "actually work; cr.py's Change Request review ticket now "
            "gets a parent Epic link like every other issue type; "
            "constitution.md's DRAFT now pushes to Confluence "
            "immediately at /specify, not only after GATE-1 finalizes"
        ),
        "notes": [
            "User request: project_keys already supports per-level "
            "overrides for feature/story/task/review/chg/cr -- asked for "
            "the same on issue_hierarchy (the Jira issue TYPE per "
            "level), and for the hierarchy/parent-linking model to be "
            "explained and documented",
            "Investigating found issue_hierarchy per-level overrides for "
            "review/chg/cr were completely non-functional even though "
            "jira.py's own `.get('chg', ...)` fallback code implied they "
            "worked: load_integrations() built JiraConfig with only "
            "feature/story/task hardcoded, silently dropping any "
            "review/chg/cr entry the user wrote in integrations.yml. "
            "Fixed with a new JiraConfig.issue_type_for(level) method "
            "(mirrors key_for()'s alias/fallback semantics, including "
            "the 'epic' <-> 'feature' bidirectional alias) that every "
            "issue-creation call site in jira.py/review.py/cr.py now "
            "routes through, replacing all direct issue_hierarchy[...] "
            "dict indexing",
            "Design note: issue_hierarchy's dataclass default and "
            "load_integrations() construction deliberately stay EMPTY "
            "by default (all resolution happens in issue_type_for(), "
            "same pattern as project_keys/key_for()) -- an earlier "
            "version of this fix pre-filled every level's default into "
            "the stored dict, which broke the 'epic' alias (since "
            "'feature' was then always present, the alias fallback "
            "never got a chance to fire for an `issue_hierarchy: {epic: "
            "...}` override). Caught by the fix's own test suite before "
            "shipping",
            "Also fixed while investigating: cr.py's 'sdd cr submit' "
            "created the CR-NNN review ticket as a fully standalone "
            "issue with no parent link at all -- the only Jira issue "
            "type this CLI ever created that way (Epic/Story/Task/"
            "review tickets all link up under the Epic). It now "
            "self-bootstraps the Epic (reusing review.py's "
            "_ensure_epic()) and links the CR review ticket under it, "
            "same as review.submit's own review tickets do",
            "Documented the full parent-child hierarchy and the cr-vs-"
            "chg distinction (cr = the Change Request's own approval "
            "ticket, one per CR-NNN; chg = individual dev tasks "
            "implementing one line of an approved CR's plan, one per "
            "CHG-NNN row, parented to whichever Story satisfies its "
            "FR-NNN reference) directly in integrations.yml.example's "
            "issue_hierarchy comment block -- the single canonical "
            "source synced to every pack -- and in cli-python/README.md",
            "Separately: constitution.md's DRAFT now pushes to "
            "Confluence immediately when /specify first generates it "
            "(same as context.md's own draft push in /create-context), "
            "not only when GATE-1 finalization pushes it later -- a "
            "reviewer can now comment on the constitution in Confluence "
            "before finalizing, matching how context.md already worked. "
            "Applied to all 5 packs' specify.prompt.md (Action 1, right "
            "after saving the DRAFT) individually, since specify.prompt.md "
            "differs per pack (different tech stack rows) and isn't part "
            "of the shared-block sync system",
            "This Node CLI has no Jira/Confluence integration at all "
            "(scaffolding-only by design) and is unaffected by any of "
            "this -- this migration entry exists so both CLIs report "
            "the same sdd_version chain",
            "Added tests: TestIssueTypeFor (5 tests) in "
            "test_config_and_integrations.py covering default behavior, "
            "independent review/chg/cr overrides, the epic alias, and "
            "end-to-end usage from review.py/cr.py; TestCrSubmitParentLink "
            "(1 test) in test_cr.py verifying the new Epic self-"
            "bootstrap + parent link; updated FakeJiraClient in test_cr.py "
            "to track set_parent() calls and return unique issue keys",
            "Verified: cli-python pytest 880/880 (874 pre-existing + 6 "
            "new); ruff check/format and mypy --ignore-missing-imports "
            "(matching CI's exact invocation) both clean on the changed "
            "files; check-cross-references.py clean across all 6 packs; "
            "test-setup.sh (19/19) and test-setup-micro.sh (12/12) both "
            "pass",
        ],
    },
    {
        "from": "2.8.28",
        "to": "2.8.29",
        "description": (
            "Fix bare `sdd confluence push` (no --doc) never including "
            "the context.md page -- the same gap as v2.8.23's "
            "constitution fix, found while auditing integrations.yml.example "
            "at a user's request to confirm everything was documented"
        ),
        "notes": [
            "User asked to double-check integrations.yml.example "
            "documented everything discussed in the previous round "
            "(issue_hierarchy, hierarchy diagram, cr/chg). While "
            "re-reading it end to end, found 'context' was missing "
            "entirely -- not in page_map, not in _DEFAULT_PAGE_MAP -- "
            "the exact same bug class as v2.8.23's constitution fix, "
            "just never caught for context.md at the time",
            "Root cause: _resolve_page_title() in confluence.py "
            "special-cases 'context' to always resolve to '{feature} -- "
            "Context' regardless of what's in page_map -- so `sdd "
            "confluence draft --doc context` (what /create-context "
            "actually calls) worked fine on its own. But a bare `sdd "
            "confluence push` (no --doc) iterates page_map.keys(), and "
            "'context' was never in that set, so a bulk push silently "
            "never attempted the context page",
            "Fixed by adding 'context' to _DEFAULT_PAGE_MAP "
            "(sdd/utils/integrations.py), the wizard's minimal fallback "
            "template (_integrations_template() in "
            "sdd/commands/config.py), and integrations.yml.example's "
            "page_map (with the same 'value is ignored, only presence "
            "matters' comment already on the constitution entry)",
            "This Node CLI has no Confluence integration at all "
            "(scaffolding-only by design) and is unaffected -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Added TestConfluencePushIncludesContextByDefault (2 tests) "
            "in test_confluence_push_cli.py mirroring the existing "
            "constitution regression class; added 'context' to "
            "EXPECTED_DOC_KEYS in test_config_and_integrations.py",
            "Verified: cli-python pytest 882/882 (880 pre-existing + 2 "
            "new); ruff check/format and mypy --ignore-missing-imports "
            "(matching CI's exact invocation) both clean on the changed "
            "files; check-cross-references.py clean across all 6 packs; "
            "test-setup.sh (19/19) and test-setup-micro.sh (12/12) both "
            "pass",
        ],
    },
    {
        "from": "2.8.29",
        "to": "2.8.30",
        "description": (
            "Add commented-out document_reviews example entries for the "
            "living/service-level docs (data-model, security-design, "
            "api-spec, component-library) to integrations.yml.example"
        ),
        "notes": [
            "User request, following up on the previous round's "
            "issue_hierarchy/page_map audit: these four docs had a "
            "page_map entry (Confluence) but no document_reviews entry "
            "(Jira) anywhere in the shipped example -- confirmed as "
            "by-design (specify-doc.prompt.md's documented fallback: "
            "sdd review submit fails with no document_reviews entry, "
            "falls through to sdd confluence draft instead of silently "
            "dropping to chat mode), but a team that DOES want a formal "
            "Jira gate on one of these had no template to copy from",
            "Each of the four gets its OWN single-entry phase (e.g. "
            "phase: data-model, sequence: 1) rather than sharing one "
            "phase/sequence sequence with each other or with design -- "
            "they're independent (any order, no dependency between "
            "them), and review.py's predecessor check "
            "(_check_predecessor) gates strictly on matching phase + "
            "sequence-1, so sharing a phase would wrongly block one doc "
            "on another's approval",
            "All four entries stay fully commented out by default -- "
            "active document_reviews / page_map keys are completely "
            "unaffected; a bare `sdd config init` project behaves "
            "identically to before this change",
            "This Node CLI has no Jira/Confluence integration at all "
            "(scaffolding-only by design) and is unaffected -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "No new tests needed -- purely commented-out documentation; "
            "verified the file still parses as valid YAML and the "
            "active document_reviews/page_map key sets are byte-for-"
            "byte unchanged",
            "Verified: cli-python pytest 882/882 (no change -- inert "
            "commented content); check-cross-references.py clean across "
            "all 6 packs; test-setup.sh (19/19) and test-setup-micro.sh "
            "(12/12) both pass",
        ],
    },
    {
        "from": "2.8.30",
        "to": "2.8.31",
        "description": (
            "Fix re-pushing a local-svg diagram to Confluence a second "
            "time -- always failed with 'Cannot add a new attachment "
            "with same file name as an existing attachment'"
        ),
        "notes": [
            "Reported by a user during testing: pushed a page with a "
            "local-svg diagram once successfully, then re-pushed it "
            "(no content change, purely a re-push) -- the SVG attachment "
            "upload failed every single time with a 400 "
            "BadRequestException naming the exact collision. The page "
            "body itself still updated fine, so the failure was easy to "
            "miss unless you were watching stderr",
            "Root cause: confluence_client.py's upload_attachment() "
            "always POSTed to Confluence's CREATE-a-new-attachment "
            "endpoint (.../child/attachment). Its own docstring claimed "
            "Confluence auto-versions an existing same-named attachment "
            "the way page updates do -- that claim was simply wrong. "
            "Confluence Cloud's actual behavior: creating a second "
            "attachment with a filename that already exists on the page "
            "is rejected outright. Updating an existing attachment's "
            "content requires a DIFFERENT endpoint entirely (POST "
            ".../child/attachment/{attachmentId}/data), which needs the "
            "attachment's ID first",
            "Fixed with a new get_attachment_by_filename() lookup "
            "(Confluence's attachment-list endpoint supports filtering "
            "by filename server-side, so this is one extra call, not a "
            "fetch-all-and-scan) -- upload_attachment() now checks for "
            "an existing same-named attachment first and routes to the "
            "update-data endpoint when one exists, the create endpoint "
            "otherwise. Every page's first push (no existing attachment) "
            "behaves identically to before; only the second-and-later "
            "push of the same diagram is affected, which is exactly "
            "what was broken",
            "This Node CLI has no Confluence integration at all "
            "(scaffolding-only by design) and is unaffected -- this "
            "migration entry exists so both CLIs report the same "
            "sdd_version chain",
            "Added 7 new tests in test_confluence_client.py: "
            "TestGetAttachmentByFilename (3 tests: none-found, "
            "found-returns-first-match, queries by the right filename) "
            "and TestUploadAttachmentUpdatesExisting (4 tests: no-"
            "existing-attachment still hits the create endpoint, an "
            "existing attachment hits the update-data endpoint -- the "
            "exact reported bug -- not the create endpoint, the update "
            "path still sends the same XSRF/Content-Type headers and "
            "multipart file the create path already needed, and the "
            "lookup uses the actual filename being uploaded). Updated "
            "the pre-existing TestUploadAttachment fixture to explicitly "
            "mock the new lookup call (previously relied on implicit "
            "MagicMock auto-attributes, which would have silently taken "
            "the wrong branch after this fix)",
            "Verified: cli-python pytest 889/889 (882 pre-existing + 7 "
            "new); ruff check/format and mypy --ignore-missing-imports "
            "(matching CI's exact invocation) both clean on the changed "
            "files",
        ],
    },
    {
        "from": "2.8.31",
        "to": "2.8.32",
        "description": (
            "Add a project-level 'Living Documents' dashboard section "
            "for Data Model and Security Design -- previously only "
            "shown as a bare progress dot duplicated inside every "
            "feature's own pipeline card, with no Approve button, no "
            "Confluence/Jira links, and easy to miss entirely"
        ),
        "notes": [
            "Reported by a user: couldn't find Data Model on the "
            "dashboard at all, and after generating it its status stuck "
            "showing 'waiting for review' -- the second part turned out "
            "to be correct/by-design (a Draft doc is genuinely awaiting "
            "approval), but the first part was a real gap: these two "
            "living/service-level docs (one shared file for the whole "
            "project, .specify/service/{key}.md, not per-feature) were "
            "only ever inserted as ordinary steps inside each feature's "
            "own pipeline -- meaning on a multi-feature project the SAME "
            "doc showed up duplicated once per feature card, each "
            "computed from the identical underlying file, and neither "
            "instance had the Approve button / Confluence+Jira links / "
            "Details panel every per-feature document already gets, "
            "since the per-feature Documents table (_feature_docs()) "
            "only ever scanned .specify/features/{feature}/, never "
            ".specify/service/",
            "New _service_level_docs() in status.py builds full doc "
            "entries (status, approvals, comments, timing -- same shape "
            "_feature_docs() returns) for Data Model and Security "
            "Design, exposed as a new top-level living_documents / "
            "living_local_links pair in build_project_status()'s JSON, "
            "separate from any one feature",
            "Removed the two 'service_doc' step entries from "
            "extended_steps in build_pipeline() so they no longer "
            "duplicate inside every feature's own Full Pipeline card. "
            "build_pipeline()'s service_docs parameter and "
            "_step_state()'s 'service_doc' kind branch are now dead "
            "code (no step ever produces that kind anymore) -- left in "
            "place rather than removed, since trimming a public "
            "function's signature would touch every call site/test that "
            "constructs it for no behavioral gain",
            "New renderLivingDocuments() in the dashboard's app.js "
            "renders a 'Living Documents' card between the Project/"
            "Constitution cards and the Features Overview table, reusing "
            "renderDocRow() directly -- the exact same Approve button, "
            "Details panel (Content/Approvals/Comments tabs), and "
            "Confluence/Jira link pills every per-feature document "
            "already has, with zero new dashboard.py backend endpoints "
            "needed (approve/comment/doc-content already route through "
            "resolve_doc_path(), which was already living-doc-aware). "
            "Only docs that actually exist are shown, matching how "
            "per-feature Documents tables never show a row for an "
            "ungenerated doc either",
            "api-spec and component-library (also in LIVING_SERVICE_DOCS, "
            "sdd/utils/validate.py) are deliberately NOT included in "
            "this section -- api-spec is produced by /plan-design §3, "
            "not a standalone /specify-doc command, and neither has any "
            "dashboard tracking to build on yet; a real gap, but a "
            "separate follow-up, not scope-crept into this fix",
            "This Node CLI has no dashboard at all (scaffolding-only by "
            "design) and is unaffected -- this migration entry exists "
            "so both CLIs report the same sdd_version chain",
            "Updated 5 pre-existing tests in test_status.py that "
            "asserted the old per-feature 'data-model'/'security-design' "
            "pipeline steps existed, rewriting them against "
            "_service_level_docs() directly (independent tracking, "
            "Draft-is-not-Approved, pilot-scope gating). Added 3 new "
            "end-to-end tests: living_documents/living_local_links "
            "appear in build_project_status()'s output, the exact "
            "reported multi-feature duplication bug (a shared doc must "
            "not appear as a step in any feature's own pipeline), and "
            "sdd-micro (scope=None) safely reports an empty list rather "
            "than crashing or showing the backend-service default pair",
            "Verified: cli-python pytest 892/892 (889 pre-existing + 3 "
            "net new -- 2 removed, 4 rewritten, 5 added across the "
            "rewrite); ruff check/format and mypy --ignore-missing-"
            "imports (matching CI's exact invocation) both clean on the "
            "changed files; node --check on app.js clean; manually "
            "verified build_project_status()'s JSON shape end-to-end "
            "against a real fixture project (Draft data-model.md with "
            "an Approvals table) before wiring the frontend",
        ],
    },
    {
        "from": "2.8.32",
        "to": "2.8.33",
        "description": (
            "Fix a real document-corrupting bug in `sdd review approve "
            "--local` (a blind 'Status: Draft' find-replace could mangle "
            "enum content anywhere in a document's body), a severe "
            "Confluence-pull data-loss bug (mismatched ac: tag closing "
            "could delete whole sections), an HTML-comment mangling bug "
            "on both push and pull, and the security/security-design "
            "doc-key naming inconsistency -- all found by a user during "
            "a real living-document review cycle"
        ),
        "notes": [
            "Bug 1 (data corruption) -- _mark_md_approved() in review.py "
            "flipped a document's Status: header via "
            "`re.sub(r'Status:\\\\s*(Draft|Proposed)\\\\b', 'Status: "
            "Approved', text, count=1)` -- unanchored across the ENTIRE "
            "document, not scoped to the real header. Reported by a "
            "user: data-model.md's own template (unlike every other "
            "spec template) had NO Status: header field at all, so the "
            "regex's first (and only) match was a §3 enum field written "
            "as 'RuleVersionStatus: DRAFT, SUBMITTED, PUBLISHED, "
            "RETIRED' -- silently mangled into 'RuleVersionStatus: "
            "Approved, SUBMITTED, PUBLISHED, RETIRED'. Fixed by scoping "
            "the flip to the document's front matter (before the first "
            "'## ' heading), where every template's real header line "
            "lives, in both its 'Version: ... | Status: ...' shape (most "
            "templates) and its 'Status: ... | ...' shape (adr.md)",
            "Root-caused further: data-model-template.md and security-"
            "design-template.md never had a Status: header field to "
            "begin with -- added 'Status: Draft' to both, across all 5 "
            "packs, matching every other template's convention and "
            "giving the (now-safe) header-flip regex a real target to "
            "find, restoring correct Draft/Approved status tracking for "
            "these two living docs (which the dashboard's new Living "
            "Documents section, shipped last round, depends on)",
            "Bug 2 (severe data loss) -- cf_to_md.py's 'strip remaining "
            "ac:* elements' cleanup used `<ac:[^>]+>.*?</ac:[^>]+>`, "
            "pairing an opening ac: tag with the NEXT ac: closing tag of "
            "ANY name, not necessarily its own. Reported by a user: a "
            "page with a local-svg <ac:image> diagram, followed later by "
            "another unhandled/nested ac: element, had everything "
            "between the <ac:image> and that unrelated LATER closing tag "
            "silently deleted -- 6 tables and an entire numbered section "
            "in their case. Fixed with a backreference "
            "(`<ac:([a-zA-Z-]+)[^>]*>.*?</ac:\\\\1>`) so a match can only "
            "ever span exactly one element's own content",
            "Bug 3 (data loss + visible garbage) -- HTML comments (e.g. "
            "specify-doc.prompt.md's '<!-- security-sign-off: ... -->' "
            "marker) fell through md_to_cf.py's paragraph branch on "
            "push, which HTML-escaped them into VISIBLE garbage text on "
            "the actual Confluence page ('&lt;!-- ... --&gt;'), and then "
            "cf_to_md.py's final 'strip any remaining HTML tags' step "
            "deleted them outright on pull (a bare <!-- ... --> matches "
            "that step's generic <[^>]+> pattern, which has no notion of "
            "comments vs. tags). Fixed on both sides: push now passes a "
            "comment-only line through literally instead of escaping it; "
            "pull now stashes comments into placeholders before any "
            "other processing and restores them verbatim at the very "
            "end, immune to every intermediate regex pass including the "
            "ac: stripping fix above",
            "Bug 4 (naming inconsistency) -- specify-doc.prompt.md's own "
            "prose and command syntax call it `/specify-doc security`, "
            "but `sdd review submit --doc security` and `sdd confluence "
            "draft --doc security` both fail outright -- the only doc "
            "key any sdd command accepts is `security-design` (the real "
            "filename). The prompt referenced `{doc_key}` in six-plus "
            "places without ever DEFINING it in terms of the raw `{doc}` "
            "argument -- added an explicit resolution rule right after "
            "the Input section: `security` normalizes to `security-"
            "design` immediately, before any template read, file save, "
            "or CLI invocation",
            "This Node CLI has no Jira/Confluence integration and no "
            "review-approval flow of its own (scaffolding-only by "
            "design) and is unaffected by any of this -- this migration "
            "entry exists so both CLIs report the same sdd_version chain",
            "Added regression tests: TestMarkMdApproved (+3, exact "
            "reported enum-corruption shape, a lookalike body field "
            "alongside a real header, and adr.md's Status-first header "
            "shape) in test_review_helpers.py; TestAcTagStripping (+3) "
            "in test_cf_to_md.py; TestHtmlComments (+3) in each of "
            "test_md_to_cf.py and test_cf_to_md.py",
            "Verified: cli-python pytest 904/904 (892 pre-existing + 12 "
            "new); ruff check/format and mypy --ignore-missing-imports "
            "(matching CI's exact invocation) both clean on the changed "
            "files; check-cross-references.py clean across all 6 packs; "
            "test-setup.sh (19/19) and test-setup-micro.sh (12/12) both "
            "pass",
        ],
    },
    {
        "from": "2.8.33",
        "to": "2.8.34",
        "description": (
            "Fix two live sequencing bugs a user hit back-to-back during "
            "real testing: a /specify-doc chat message that skipped over "
            "the mandatory /checklist gate at mvp+/full scope, and a "
            "brd.md field that generated an unresolvable [NEEDS "
            "CLARIFICATION] marker by design"
        ),
        "notes": [
            "Bug 1 -- specify-doc.prompt.md's 'all documents complete' "
            "message named /validate as the next step unconditionally, "
            "even though /checklist sits between the extended document "
            "set and /validate in the command order and is mandatory at "
            "mvp/full scope (optional only at pilot). Reported by a user: "
            "the dashboard correctly showed 'Spec Quality Checklist' as "
            "the next step, but the chat message after the last document "
            "approval said 'Run /validate ... the gate before /analyze,' "
            "skipping /checklist entirely. Fixed by making the 'none "
            "remain' branch check manifest.project.scope: mvp/full now "
            "names /checklist (mandatory) as the next command; pilot "
            "names it as an optional gate before /validate",
            "Bug 2 -- brd.md §9's 'Build effort (T-shirt)' row was "
            "generated as 'Derived from analyze.md (filled after "
            "/analyze)' under a blanket instruction that marks any "
            "unfilled Investment Summary item [NEEDS CLARIFICATION]. But "
            "analyze.md doesn't exist until /analyze runs, which is AFTER "
            "/validate in the pipeline order (SPECIFY -> GATE-1 -> "
            "VALIDATE -> ANALYZE) -- and checklist.prompt.md's CRITICAL "
            "rule #1 blocks /validate on any unresolved [NEEDS "
            "CLARIFICATION] marker with no per-field carve-out. A user's "
            "own /checklist run surfaced this exact conflict verbatim. "
            "Three-part fix: (1) brd-template.md §9 now writes plain "
            "deferred text 'Pending -- estimated after /analyze' for this "
            "field instead of an implicit-marker-prone placeholder -- "
            "never a [NEEDS CLARIFICATION] marker; (2) analyze.prompt.md "
            "gained a new 'Update BRD Build Effort' step that actually "
            "implements the template's own long-standing but never-"
            "implemented promise -- derives a T-shirt size from the "
            "COMPLEXITY ratings just produced and writes it back into "
            "brd.md §9; (3) checklist.prompt.md's CRITICAL rule #1 "
            "gained an explicit known-exception carve-out for this one "
            "field, as a defensive safety net for any brd.md generated "
            "before this fix",
            "specify-doc.prompt.md and brd-template.md and "
            "checklist.prompt.md are _shared/full/ sources -- edited "
            "once, synced to all 5 packs via sync-blocks.sh. "
            "analyze.prompt.md is authored per-pack (not in _shared/) -- "
            "the same 'Update BRD Build Effort' step was added "
            "individually to all 5 packs' analyze.prompt.md, verified "
            "identical in content across all 5",
            "This Node CLI has no Jira/Confluence integration and no "
            "review-approval flow of its own (scaffolding-only by "
            "design) and is unaffected by any of this -- this migration "
            "entry exists so both CLIs report the same sdd_version chain",
            "Verified: cli-python pytest 904/904 (no Python code touched, "
            "only markdown/prompt files); check-cross-references.py clean "
            "across all 6 packs; test-setup.sh (19/19) and "
            "test-setup-micro.sh (12/12) both pass; assert-output.sh "
            "clean against examples/todo-api (33/33)",
        ],
    },
]


def _stdin_is_interactive() -> bool:
    """Broken out from a bare `sys.stdin.isatty()` call so tests can
    mock it directly -- Click's CliRunner reassigns `sys.stdin` to its
    own captured stream for the duration of `invoke()`, which silently
    defeats a `patch("sys.stdin.isatty", ...)` set up before the call
    (it patches the pre-swap object, not the one CliRunner installs)."""
    return sys.stdin.isatty()


def _pending_migrations(current_version: str | None) -> list[Migration]:
    """Every migration from current_version to SDD_VERSION, in order --
    walks the linear MIGRATIONS chain (each "from" is unique, so it's a
    simple linked list) rather than matching only the single next hop.
    A project many versions behind used to need one `sdd upgrade`
    invocation per version; this lets a caller see -- and choose to
    apply -- the whole pending chain in one run."""
    by_from = {m["from"]: m for m in MIGRATIONS}
    chain = []
    version = current_version
    seen_to = set()
    while version != SDD_VERSION:
        m = by_from.get(version)
        if m is None:
            break
        if m["to"] in seen_to:
            break  # guards against an accidental cycle in hand-edited data
        seen_to.add(m["to"])
        chain.append(m)
        version = m["to"]
    return chain


def _resolve_pack(manifest: dict, pack_override: str | None) -> tuple[str, str]:
    """Returns (pack_name, how-we-know) -- "how" is shown to the user so an
    inferred (rather than certain) answer is never presented as fact.
    Raises ValueError if --pack names something that doesn't exist."""
    if pack_override:
        if pack_override not in ALL_PACKS:
            raise ValueError(
                f"Unknown pack '{pack_override}'. Available: {', '.join(ALL_PACKS)}"
            )
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
        return TYPE_TO_PACK[
            project_type
        ], f"inferred from project_type '{project_type}'"

    return (
        UNIVERSAL_PACK,
        "no pack recorded and project_type unrecognized — defaulting to sdd-universal",
    )


def _do_sync_prompts(pack_override: str | None, yes: bool) -> None:
    manifest = read_manifest() or {}
    try:
        pack_name, source = _resolve_pack(manifest, pack_override)
    except ValueError as e:
        console.print(f"  [red]✗  {e}[/red]")
        console.print()
        return

    console.print(
        f"  [bold]Syncing prompts from pack:[/bold] [cyan]{pack_name}[/cyan]  [dim]({source})[/dim]"
    )
    if "inferred" in source or "defaulting" in source:
        console.print(
            "  [dim]Not certain which pack this project uses — pass --pack "
            "explicitly if this guess is wrong.[/dim]"
        )
    console.print()

    preview = sync_pack_prompts(pack_name, dry_run=True)
    changed = preview["updated"] + preview["added"]
    if not changed:
        console.print(
            "  [green]✓  .github/prompts/ and .claude/commands/ are already up to date.[/green]"
        )
        console.print()
        return

    if preview["updated"]:
        console.print(
            f"  [yellow]{len(preview['updated'])} file(s) will be updated[/yellow] (backed up first):"
        )
        for f in preview["updated"]:
            console.print(f"    [dim]•[/dim] {f}")
    if preview["added"]:
        console.print(
            f"  [green]{len(preview['added'])} file(s) will be added[/green] (new in this pack version):"
        )
        for f in preview["added"]:
            console.print(f"    [dim]•[/dim] {f}")
    console.print(
        f"  [dim]{len(preview['unchanged'])} file(s) already up to date, left alone.[/dim]"
    )
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
        console.print(
            f"  [dim]Backups of overwritten files: {result['backup_dir']}[/dim]"
        )
    console.print()


@click.command()
@click.option(
    "--sync-prompts",
    is_flag=True,
    help="Re-copy this project's .github/prompts/ and .claude/commands/ "
    "from the current pack, overwriting stale copies. sdd upgrade "
    "alone only ever patches manifest.yml's sdd_version -- it never "
    "touches these files, so fixes made to prompt content after this "
    "project was scaffolded need this flag to actually reach it.",
)
@click.option(
    "--pack",
    "pack_override",
    default=None,
    help=f"Pack to sync prompts from, overriding manifest.yml/inference. One of: {', '.join(ALL_PACKS)}",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip the confirmation prompt for --sync-prompts, and (when "
    "multiple migrations are pending) skip the jump-to-latest-vs-"
    "step prompt by jumping straight to latest.",
)
@click.option(
    "--to-latest",
    is_flag=True,
    help="When multiple migrations are pending, apply all of them in "
    "this run instead of asking or stopping after one hop.",
)
@click.option(
    "--step",
    is_flag=True,
    help="When multiple migrations are pending, apply only the next "
    "one and stop -- the original behavior, for reviewing each "
    "migration's notes before continuing to the next.",
)
def upgrade_command(sync_prompts, pack_override, yes, to_latest, step):
    """Migrate manifest.yml to the current pack version."""
    console.print()
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("  [bold cyan]SDD Framework[/bold cyan] — upgrade")
    console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print()

    if to_latest and step:
        console.print("[red]✗  --to-latest and --step are mutually exclusive.[/red]")
        raise SystemExit(1)

    if not Path(MANIFEST_PATH).exists():
        console.print(
            f"[red]✗  {MANIFEST_PATH} not found — run from the pack root directory.[/red]"
        )
        raise SystemExit(1)

    manifest = read_manifest()
    current_version = manifest.get("sdd_version") if manifest else None

    if current_version == SDD_VERSION:
        console.print(f"  [green]✓  Already at v{SDD_VERSION} — nothing to do.[/green]")
        console.print()
        if not sync_prompts:
            return
    else:
        console.print(
            f"  Current version : [yellow]{current_version or 'pre-versioning (v1.x)'}[/yellow]"
        )
        console.print(f"  Target version  : [green]{SDD_VERSION}[/green]")
        console.print()

        pending = _pending_migrations(current_version)

        if not pending:
            console.print(
                "[yellow]  No migration path found. See CHANGELOG.md for manual steps.[/yellow]"
            )
            console.print()
            if not sync_prompts:
                return
        else:
            # A project several versions behind used to need one `sdd
            # upgrade` invocation per pending migration. With more than
            # one pending, decide once whether to apply the whole chain
            # now or step through it -- explicit flags win; otherwise
            # ask interactively; a script/CI invocation (no real TTY on
            # stdin) defaults to applying everything now rather than
            # silently doing only one hop and needing N reruns.
            apply_all = True
            if len(pending) > 1 and not to_latest and not step:
                if yes:
                    apply_all = True
                elif _stdin_is_interactive():
                    import questionary

                    choice = questionary.select(
                        f"You're {len(pending)} versions behind (latest is "
                        f"v{SDD_VERSION}). How would you like to upgrade?",
                        choices=[
                            questionary.Choice(
                                f"Jump straight to v{SDD_VERSION} (apply all "
                                f"{len(pending)} migrations now)",
                                value=True,
                            ),
                            questionary.Choice(
                                "Step through one at a time (review each "
                                "migration's notes before continuing)",
                                value=False,
                            ),
                        ],
                    ).ask()
                    apply_all = True if choice is None else choice
                # else: non-interactive with neither flag nor --yes --
                # apply_all stays True (see docstring note above).
            elif step:
                apply_all = False

            to_apply = pending if apply_all else pending[:1]
            if len(pending) > 1:
                console.print(
                    f"  [dim]{len(pending)} migrations pending -- "
                    f"{'applying all now' if apply_all else 'applying next hop only'}.[/dim]"
                )
                console.print()

            for migration in to_apply:
                console.print(
                    f"  [bold]Migrating → v{migration['to']}: {migration['description']}[/bold]"
                )
                for note in migration["notes"]:
                    console.print(f"    [dim]•[/dim] {note}")
                console.print()

                updated = _migrate_fn(migration["to"])(read_manifest())
                patch_manifest({"sdd_version": updated["sdd_version"]})
                console.print(
                    f"  [green]✓[/green]  {MANIFEST_PATH} updated to v{migration['to']}"
                )
                console.print()

            final_version = (read_manifest() or {}).get("sdd_version")
            if final_version != SDD_VERSION:
                console.print(
                    f"  [yellow]Now at v{final_version} — run [cyan]sdd upgrade[/cyan] again "
                    f"to continue to v{SDD_VERSION}.[/yellow]"
                )
                console.print()

            console.print(
                "[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]"
            )
            console.print("  [bold green]Upgrade complete![/bold green]")
            console.print(
                "[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]"
            )
            console.print()

    if sync_prompts:
        _do_sync_prompts(pack_override, yes)
