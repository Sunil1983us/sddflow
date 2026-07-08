---
mode: agent
description: CREATE-CONTEXT — Turn a rough idea into a short context.md (optional pre-phase, before /specify)
---

## Purpose
Optional. Most sdd-micro projects can skip straight to `/specify` and
describe the task in chat. Use `/create-context` only if you'd rather
have a written context.md first, or you're starting from messier notes
than a sentence or two.

## Before Starting
- Read `.specify/manifest.yml` (if filled — confirm `project.feature`)
- Read `.specify/templates/context-template.md`
- Read `.specify/contexts/CONTEXT-GUIDE.md`

## Step 1 — Gather Input
If the user hasn't already provided notes in this conversation, ask:
"What are you building? A sentence or two is fine — or paste any notes
you already have."

## Step 2 — Draft context.md
Map the input onto context-template.md's sections: What This Does, Tech
Stack, Ground Rules, Out of Scope. For anything not stated or clearly
implied, write `[MISSING — ask user]` — never invent a tech stack choice
or a rule the user didn't state.

## Step 3 — Review
Show the draft. List anything marked `[MISSING — ask user]` as short
questions. The user can answer, say "not sure" (fine for tech stack —
`/specify` can propose a reasonable default), or say "good enough,
proceed".

## Step 4 — Save
Save to `.specify/contexts/{feature}.md` (confirm `{feature}` matches
`manifest.project.feature`, or ask the user to fill it if blank).
State: "Context ready at .specify/contexts/{feature}.md. Run /specify to
generate the constitution."

## Never Do
- Never invent a tech stack choice or ground rule not stated or clearly
  implied — use `[MISSING — ask user]`
- Never overwrite an existing context.md without confirming with the user first
