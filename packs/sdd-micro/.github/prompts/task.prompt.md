---
mode: agent
description: TASK — Flat, numbered task list (no stories, no Jira)
---

## Purpose
Break the confirmed scope into small, concrete, independently-verifiable
steps before any code is written — the one piece of ceremony this pack
keeps, because it's what actually prevents scope drift on a small
project.

## Before Starting
- Read `.specify/manifest.yml`
- Read `.specify/memory/constitution.md` — Tech Stack row drives every
  run/test command written into tasks.md
- Read `.specify/contexts/{manifest.project.feature}.md` if it exists

## Verify Gate
Confirm constitution Part 2 has been confirmed (GATE-1 — the user said
"confirmed" after the last `/specify`). If not, STOP and ask for that
confirmation first.

## Your Task
1. Read `.specify/templates/tasks-template.md`
2. Break the work into `TASK-NNN` entries, ordered so each one leaves the
   project in a working, runnable state when done. Keep each task small —
   implementable and verifiable in one pass.
3. For each task write:
   - **Steps** — the concrete change to make
   - **Verify** — the exact command to run (using the Test/Verify
     Command from constitution Part 2 where it applies) or, if nothing
     can be scripted, the manual check and expected result
   - **Status: Not Started**
4. Save to `.specify/features/{manifest.project.feature}/tasks.md`
5. State: "{N} tasks ready. Run /implement to start with TASK-001."

## Never Do
- Never write a task with no concrete verification step
- Never invent a test/run command not derivable from constitution Part 2
  or something the user stated — write "manual run — describe expected
  output" instead of guessing
