# _shared — Canonical "Law" Blocks for SDD Packs

This directory is **maintainer-only tooling**. It is never copied into a
user's project — each `sdd-*` pack remains a fully self-contained zip
(see `QUICKSTART.md` → "Copy the Pack"). The marker comments described
below are inert HTML comments if `_shared/` is absent, so packs work
identically whether or not this directory exists alongside them.

## Why

Several sections of `CLAUDE.md` / `.github/copilot-instructions.md` /
`PROMPT-GUIDE.md` are meant to be byte-identical across all `sdd-*` packs
(the command gate order, the PR contract, the core "Never Do" rules,
etc.) — they describe the SDD process, not a tech stack. Today they're
hand-copied into each pack and drift apart (e.g. one pack documents the
`local` workflow_mode branch in its PR Contract, another doesn't).

## How it works

Two sync mechanisms, for two kinds of shared content:

### 1. Marked blocks — shared section within a pack-specific file

- `blocks/{id}.md` holds the canonical text for one shared section.
- In any pack file, wrap the corresponding section with:
  ```
  <!-- shared:{id}:start -->
  ...content (kept in sync with blocks/{id}.md)...
  <!-- shared:{id}:end -->
  ```
- Run `./sync-blocks.sh` to copy each block's content into every pack file
  that has that marker pair, replacing whatever was between the markers.

### 2. Full files — whole file with zero pack-specific content

- `full/{relpath}` holds the canonical content for a whole file that is
  (or should be) byte-identical across every pack that has it — e.g.
  `.claude/commands/*.md`, shared `.specify/templates/*.md`.
- `./sync-blocks.sh` copies `full/{relpath}` to `{pack}/{relpath}` for every
  `sdd-*` pack that already has a file at that path, whenever the contents
  differ.
- A pack that doesn't have `{relpath}` at all is left untouched — `full/`
  only syncs existing files, it never creates new ones in a pack.

## Rules

- **Never hand-edit content between a marker pair in a pack file** — it
  will be overwritten on the next sync. Edit `blocks/{id}.md` instead, then
  run `./sync-blocks.sh` and review the diff across all packs.
- **Never hand-edit a file that has a `full/{relpath}` counterpart** — it
  will be overwritten on the next sync. Edit `full/{relpath}` instead, then
  run `./sync-blocks.sh` and review the diff across all packs.
- A pack-specific section (e.g. frontend's extra "Never call an API
  directly from a component" rules) goes **outside** the marker pair, in
  the same `## Never Do` heading, after the synced block.
- Headings (`## Never Do`, `## PR Contract`, etc.) stay in each pack file —
  only the body between markers is synced.
- If a file legitimately needs to diverge between packs (even slightly),
  remove it from `full/` rather than letting `sync-blocks.sh` fight the
  divergence.

## Current blocks

| Block | Used for |
|---|---|
| `command-gates.md` | "11-Command Gates" — command order + gate rule |
| `pr-contract.md` | "PR Contract" — estimate/split/report-and-wait rule |
| `never-do-core.md` | "Never Do" — the 9 process-level rules common to every pack |
| `startup-instructions.md` | "Startup" item 6 — read `.github/instructions/*.instructions.md` (AI-7) |
| `gate1-reminders.md` | "Startup" items 8-9 — GATE-1 reminders |
| `start-command-body.md` | `.claude/commands/start.md` — Step 0 body (file reads + confirm fields) |

## Current full files

| Path | Used for |
|---|---|
| `.claude/commands/analyze.md` | ANALYZE slash command (Claude Code) |
| `.claude/commands/clarify.md` | CLARIFY slash command |
| `.claude/commands/create-context.md` | CREATE-CONTEXT slash command |
| `.claude/commands/implement.md` | IMPLEMENT slash command |
| `.claude/commands/plan-adr.md` | PLAN-ADR slash command |
| `.claude/commands/plan-arch.md` | PLAN-ARCH slash command |
| `.claude/commands/plan-hld.md` | PLAN-HLD slash command |
| `.claude/commands/plan-lld.md` | PLAN-LLD slash command |
| `.claude/commands/release.md` | RELEASE slash command |
| `.claude/commands/specify.md` | SPECIFY slash command |
| `.claude/commands/task.md` | TASK slash command |
| `.claude/commands/validate.md` | VALIDATE slash command |
| `CLAUDE.local.md` | Gitignored personal-preferences template |
| `.specify/templates/adr-template.md` | ADR template (mvp+) |
| `.specify/templates/hld-template.md` | HLD template |
| `.specify/templates/jira-export-template.md` | Jira CSV export template (Epic terminology) |
| `.specify/templates/lld-template.md` | LLD template (mvp+) |
| `.specify/templates/plan-template.md` | plan.md template (PLAN-ARCH output) |
| `.specify/templates/srd-template.md` | SRD template |
| `.specify/templates/validate-template.md` | VALIDATE report template |
