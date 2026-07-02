# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Repo Is

This is the **maintainer repository** for the SDD (Spec-Driven Development) Framework — a collection of self-contained packs that end-users copy into their own projects. Work here is about authoring, fixing, and syncing those packs, not running the SDD workflow itself.

End-user usage (running `/specify`, `/validate`, etc.) happens inside a copy of a pack in the user's own project — each pack's own `CLAUDE.md` governs that.

---

## Repository Layout

```
packs/
  _shared/          # Canonical source for content shared across all packs
  sdd-universal/    # Meta-pack: auto-detects project type (10 types)
  sdd-backend-service/
  sdd-frontend-spa/
  sdd-mobile/
  sdd-fullstack/
cli/                # Node.js CLI (npm: sdd-init) — init/upgrade scaffolding only
cli-python/         # Python CLI (pip: sdd-init) — full-featured (Jira, Confluence, reviews, PRs)
examples/
  todo-api/         # Complete worked example of SDD outputs
SPEC-KIT-COMPARISON.md   # Competitive positioning against GitHub spec-kit
PACK-SPEC.md             # Specification for building community packs
```

Each `sdd-*` pack is fully self-contained — a user copies one pack folder into their project and never touches this repo again. Packs must never import from each other or from `_shared/` at runtime.

---

## The Shared Sync System

`_shared/` is the canonical source of truth for content that is byte-identical across all packs. **Never hand-edit synced content directly in a pack.**

### Two sync mechanisms

**1. Marked blocks** (`_shared/blocks/*.md`)
Content wrapped with HTML comment markers in pack files:
```
<!-- shared:{id}:start -->
...content owned by _shared/blocks/{id}.md...
<!-- shared:{id}:end -->
```
Edit the block file, then run sync:
```bash
bash packs/_shared/sync-blocks.sh
```

Current blocks: `command-gates`, `gate1-reminders`, `never-do-core`, `pr-contract`, `review-gates`, `scope-reference`, `startup-instructions`, `start-command-body`, `team-routing`. (`ls packs/_shared/blocks/` is authoritative if this list drifts.)

**2. Full files** (`_shared/full/**`)
Whole files that are identical across packs (e.g. `CLAUDE.local.md`, `.windsurfrules`, `setup.sh`, `setup.ps1`, `.claude/commands/*.md`, `.specify/templates/*`). Synced with:
```bash
bash packs/_shared/sync-blocks.sh   # handles both blocks and full files
```
Full-file sync only updates a file if it already exists in the target pack — it never creates new files.

### Package a single pack for distribution
```bash
bash packs/_shared/package.sh sdd-universal
# outputs a zip/tarball ready for users to copy
```

---

## Command Triplicity

Each SDD command lives in **three places simultaneously**:

| Location | Used by |
|---|---|
| `.claude/commands/{cmd}.md` | Claude Code native slash commands |
| `.github/prompts/{cmd}.prompt.md` | GitHub Copilot + Cursor + any-AI copy-paste |
| `.github/copilot-instructions.md` | Copilot Chat entrypoint (references the prompt files) |

When adding or changing a command, update all three. The `.claude/commands/` files in `_shared/full/.claude/commands/` are the canonical source — sync propagates them to every pack.

---

## Detection Order Rule (Critical)

Two places define how project type is auto-detected, and they **must stay in sync**:

1. `setup.sh` `detect_project_type()` — bash execution order
2. `specify.prompt.md` Step 0 table — AI lookup order

**Rule**: mobile checks (pubspec.yaml, react-native) must appear **before** fullstack checks in both files. A React Native + pom.xml monorepo must resolve to `mobile`, not `fullstack`. If you change detection logic in one, change it in the other.

`sdd-universal/setup.ps1` `Detect-ProjectType` is a third location — keep its order matching `setup.sh`.

---

## Pack Anatomy (what each file does)

Every pack contains:

| File | Purpose |
|---|---|
| `CLAUDE.md` | Agent startup checklist + 11-command flow (pack governs itself when deployed) |
| `.specify/memory/constitution.md` | Part 1: universal rules (never edit). Part 2: DRAFT per project, finalized at GATE-1 |
| `.specify/memory/roles.yml` | RACI — which role is accountable at each gate |
| `.specify/manifest.yml` | Project config: name, scope, feature, project_type, pr_rules, workflow_mode |
| `.specify/templates/` | 30+ document templates for all SDD outputs |
| `.github/prompts/` | One prompt file per command (portable to any AI tool) |
| `.claude/commands/` | Claude Code native slash command wrappers |
| `.github/instructions/` | Pack-specific coding standards (applied by AI-7 rule to matching files) |
| `setup.sh` / `setup.ps1` | One-command initializer — fills manifest.yml, creates context file |

`sdd-universal` additionally has auto-detect logic in `setup.sh`/`setup.ps1` and per-type branching in `specify.prompt.md` Step 0.

---

## Making Changes Across All Packs

**Change shared behavior (gates, PR contract, Never Do rules, startup):**
1. Edit the relevant file in `_shared/blocks/`
2. Run `bash packs/_shared/sync-blocks.sh`
3. Verify the markers in each pack updated correctly

**Change a command that is identical across all packs:**
1. Edit `_shared/full/.claude/commands/{cmd}.md`
2. Edit `_shared/full/.github/prompts/{cmd}.prompt.md` (if it exists there)
3. Run `bash packs/_shared/sync-blocks.sh`

**Change a command that differs per pack** (e.g. `specify.prompt.md` — different tech stack rows per pack):
Edit each pack's `.github/prompts/specify.prompt.md` individually.

**Add a new pack:**
1. Copy `sdd-backend-service/` as a base
2. Adapt: tech stack rows in `specify.prompt.md`, `.github/instructions/`, constitution Part 1 domain rules
3. Do NOT touch shared block markers — they stay identical
4. Run `bash packs/_shared/sync-blocks.sh` to populate all shared content

---

## sdd-universal Specifics

`sdd-universal` is the only pack where the tech stack rows in `specify.prompt.md` are conditional on `project_type`. It contains 10 separate tech stack tables (one per type) in Action 1, and a 10-type × 3-scope doc-set table in Action 2.

When adding a new project type:
- Add detection signal to `setup.sh` `detect_project_type()` (bash)
- Add detection row to `specify.prompt.md` Step 0 table (AI lookup)
- Add detection to `setup.ps1` `Detect-ProjectType` (PowerShell)
- Add tech stack rows table to `specify.prompt.md` Action 1
- Add doc-set row to `specify.prompt.md` Action 2 table
- Keep mobile before fullstack in all three detection functions

---

## Scope Levels

Three scopes control which documents and commands run:

| Scope | Commands skipped | Extra docs |
|---|---|---|
| `pilot` | `/plan-lld`, `/plan-adr` | BRD, SRD, Security-Design §1, Arch, HLD, Tasks, Stories, Release |
| `mvp` | none | + API Spec, Data Model, Security-Design §1-2, LLD, ADR, QA Cases, Runbook |
| `full` | none | + Resilience, Investigation, Security-Design §1-4, OpenAPI |

Document inventory is defined in `specify.prompt.md` Action 2 — this is the single source of truth for what each scope produces.

---

## Testing Setup Scripts

After changing any `setup.sh` (edit `_shared/full/setup.sh` or `sdd-universal/setup.sh`, then sync), run the smoke-test suite — it covers injection-class names, all project types, and non-interactive execution. CI runs it on every PR (`setup-smoke-tests` job in `.github/workflows/ci.yml`).

```bash
bash packs/_shared/tests/test-setup.sh
```

The suite runs setup with stdin from `/dev/null` — setup scripts must never hang or crash when run non-interactively (CI, piped input): optional prompts fall back to defaults, required ones fail fast with a message naming the missing flag.
