# CLAUDE.md — SDD Micro Pack
# For tiny/personal projects: a script, a one-off tool, a "hello world"
# app, a small utility. Not for production services — use sdd-universal
# (or a type-specific pack) once the project grows beyond one person or
# one sitting.
#
# Command flow (only 3 commands):
# SPECIFY → [GATE-1: constitution confirmed] → TASK → IMPLEMENT

> **Note:** This pack intentionally does NOT follow `PACK-SPEC.md` (the
> full 11-command SDLC spec). There is no BRD, Use Cases, SRD, Validate,
> Analyze, Clarify, Design, or Release — those exist to make large,
> multi-stakeholder projects traceable and auditable, which is overhead a
> small personal project doesn't need. If this project grows into
> something with real stakeholders, compliance needs, or a team, migrate
> to `sdd-universal` (see README.md → "Outgrowing sdd-micro").

## CREATE-CONTEXT — Optional Pre-Phase (before SPECIFY)
If `.specify/contexts/{feature}.md` does not exist yet, or is empty/a
placeholder, offer `/create-context`: the user pastes informal notes (any
format — even one sentence, e.g. "a script that prints hello world"), the
agent drafts context.md against context-template.md. Unlike the full
packs, there is no multi-feature split check — sdd-micro projects are
single-purpose by design. Skip this entirely if the user already has a
context.md, or just describes the task directly in chat.

## Startup (every session)
1. Read `.specify/manifest.yml`
2. Read `.specify/memory/constitution.md`
3. Confirm: `project.name`, `project.feature`, `project.context_file`
4. If constitution Part 2 not generated → remind user to run `/specify` first
5. If constitution Part 2 generated but NOT confirmed (GATE-1 open) →
   remind user to review it before `/task` can run

## SPECIFY — One Command, One Document

`/specify` reads `context.md` (or the user's chat description if no
context.md exists) and writes constitution Part 2 — a short DRAFT
covering tech stack and any ground rules for this project. There is no
BRD, Use Cases, or SRD — for a "print hello world" script or a small
personal tool, those documents would be pure overhead with nothing real
to say.

**`/specify`:**
  Read context.md if it exists, else ask the user to describe the task in
  1-3 sentences
  Fill constitution Part 2: Tech Stack (language/framework/run
  command/test command — only the rows that actually apply), Ground
  Rules (freeform — anything the user explicitly wants followed)
  Save constitution.md Part 2 as DRAFT
  State: "Constitution Part 2 generated — DRAFT. Review it, then say
  'confirmed' (GATE-1), and I'll run /task."

## GATE-1 — Constitution Part 2 Confirmed (manual, blocking)
After `/specify`, constitution.md Part 2 is a DRAFT. The user reviews the
Tech Stack and Ground Rules rows (edit directly if needed — manual edits
are authoritative) and replies "confirmed". No `/task` may run before
this. This is a lightweight version of GATE-1 in the full packs — one
quick read, not a formal sign-off.

## TASK — Flat Task List (no stories, no Jira)

`/task` reads the confirmed constitution + context.md and writes
`tasks.md` — a flat, numbered list of small, concrete steps. No
Story/Epic hierarchy, no MoSCoW prioritization, no `Satisfies: FR-NNN`
traceability tags, no Jira export. Each task is small enough to
implement and verify in one go.

**`/task`:**
  Break the work into TASK-NNN entries (see tasks-template.md) — each
  with a one-line description, the concrete steps, and how to verify it
  (a command to run, an output to check, or manual steps for something
  that can't be scripted)
  Order tasks so each one leaves the project in a working state
  Save to `.specify/features/{feature}/tasks.md`
  State: "{N} tasks ready. Run /implement to start with TASK-001."

## IMPLEMENT — One Task at a Time

For each task in `tasks.md`, in order:
1. Write the code/change for that task
2. Run the verification step named in the task (test command, manual
   check, etc.) and report the actual result — pass/fail, not assumed
3. Mark the task `Status: Done` in `tasks.md`
4. State: files changed + what was verified → wait for the user to say
   "next" (or "go"/"continue") before starting the next task

If `workflow_mode: local` (the default for this pack): no PR/branch
ceremony — just report the change and verification result directly.
If `workflow_mode: github`: follow the PR Contract below.

## PR Contract (only applies when `workflow_mode: github`)
- Estimate lines changed before every task.
- If > `max_lines_per_pr` → split into smaller tasks → confirm → one at a time.
- After a task: state files + lines + "PR ready" → wait for go.

## Never Do
- Never run `/task` before constitution Part 2 is confirmed (GATE-1)
- Never run `/implement` without a `tasks.md` the user has seen
- Never hardcode secrets or credentials
- Never skip the verification step named in a task — report the actual
  result, never assume it passed
- Never silently expand scope — if the user's request during
  `/implement` clearly adds new work beyond the current task list, stop
  and ask whether to add a new task or handle it as a fresh `/specify`

## Command Order
/create-context (optional) → /specify → [GATE-1: confirmed] → /task → /implement
