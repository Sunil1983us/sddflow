# _shared — Canonical "Law" Blocks for SDD Packs

This directory is **maintainer-only tooling**. It is never copied into a
user's project — each `sdd-*` pack remains a fully self-contained zip
(see `GETTING-STARTED.md` → "Copy Pack"). The marker comments described
below are inert HTML comments if `_shared/` is absent, so packs work
identically whether or not this directory exists alongside them.

## Why

Several sections of `CLAUDE.md` / `.github/copilot-instructions.md` /
`PROMPT-GUIDE.md` are meant to be byte-identical across all `sdd-*` packs
(the 11-command gate order, the PR contract, the core "Never Do" rules,
etc.) — they describe the SDD process, not a tech stack. Today they're
hand-copied into each pack and drift apart (e.g. one pack documents the
`local` workflow_mode branch in its PR Contract, another doesn't).

## How it works

- `blocks/{id}.md` holds the canonical text for one shared section.
- In any pack file, wrap the corresponding section with:
  ```
  <!-- shared:{id}:start -->
  ...content (kept in sync with blocks/{id}.md)...
  <!-- shared:{id}:end -->
  ```
- Run `./sync-blocks.sh` to copy each block's content into every pack file
  that has that marker pair, replacing whatever was between the markers.

## Rules

- **Never hand-edit content between a marker pair in a pack file** — it
  will be overwritten on the next sync. Edit `blocks/{id}.md` instead, then
  run `./sync-blocks.sh` and review the diff across all packs.
- A pack-specific section (e.g. frontend's extra "Never call an API
  directly from a component" rules) goes **outside** the marker pair, in
  the same `## Never Do` heading, after the synced block.
- Headings (`## Never Do`, `## PR Contract`, etc.) stay in each pack file —
  only the body between markers is synced.

## Current blocks

| Block | Used for |
|---|---|
| `command-gates.md` | "11-Command Gates" — command order + gate rule |
| `pr-contract.md` | "PR Contract" — estimate/split/report-and-wait rule |
| `never-do-core.md` | "Never Do" — the 9 process-level rules common to every pack |
| `startup-instructions.md` | "Startup" item 6 — read `.github/instructions/*.instructions.md` (AI-7) |
| `gate1-reminders.md` | "Startup" items 8-9 — GATE-1 reminders |
| `start-command-body.md` | `.claude/commands/start.md` — Step 0 body (file reads + confirm fields) |
