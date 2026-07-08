---
mode: agent
description: SPECIFY — Constitution Part 2 (DRAFT) — the only spec document sdd-micro generates
---

## Purpose
Generate constitution Part 2: a short, DRAFT tech stack + ground rules
table, so every later command (and every later chat message in this
session) works from the same facts instead of re-guessing the language,
framework, or a rule you already stated. There is no BRD, Use Cases, or
SRD in this pack — see CLAUDE.md for why.

## Before Starting
- Read `.specify/manifest.yml`
- Read `.specify/memory/constitution.md`
- Read `.specify/contexts/{manifest.project.feature}.md` if it exists

## Step 1 — Gather Input
- If `context.md` exists and has content beyond the template
  placeholders, use it.
- Otherwise, use whatever the user described in this chat message. If
  neither exists, ask: "What are you building? A sentence or two is
  fine."

## Step 2 — Fill Constitution Part 2
Fill the Tech Stack and Ground Rules tables in
`.specify/memory/constitution.md`:
- **Tech Stack** — Language, Framework/Library, Run Command, Test/Verify
  Command, Storage. Only fill rows that apply — e.g. "Framework/Library:
  none" and "Storage: none — stateless" are valid, correct answers for a
  small script. Leave `[MISSING — ask user]` for anything you can't
  determine or reasonably infer.
- **Ground Rules** — only add a row if the user explicitly stated
  something (e.g. "use type hints", "no external dependencies"). Leave
  the table with just its header if nothing was stated — don't invent
  rules to fill space.
- **Never Do** — keep the two universal rows; add a project-specific row
  only if the user stated something explicit (e.g. "never write to the
  real API in tests").

Fill the version header: `Version: v1.0 | Last Amended: {today's date} |
Amended By: initial /specify`.

## Step 3 — Save and Report
Save `constitution.md` (Part 1 unchanged, Part 2 updated). State:
"Constitution Part 2 generated — DRAFT. Review the Tech Stack and Ground
Rules rows, edit anything wrong, then say 'confirmed' and I'll run
/task."

## Never Do
- Never invent a tech stack row not stated or clearly implied by the
  input — use `[MISSING — ask user]`
- Never silently overwrite a previously CONFIRMED Part 2 — if
  `/specify` is re-run after GATE-1 passed, show the proposed changes as
  a diff and ask for confirmation again before saving
