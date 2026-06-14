---
mode: agent
description: CREATE-CONTEXT — Turn informal notes into a structured context.md (optional pre-phase, before /specify)
---

## Purpose
This is an OPTIONAL pre-phase for users who do not yet have a structured
`.specify/contexts/{feature}.md` file. If you already have one written per
`.specify/contexts/CONTEXT-GUIDE.md`, skip this command and run /specify
directly.

## Before Starting
- Read .specify/manifest.yml (if filled — confirm project.feature)
- Read .specify/templates/context-template.md
- Read .specify/contexts/CONTEXT-GUIDE.md

## Step 1 — Gather Raw Input
If the user has not already provided notes in this conversation, ask:
  "Paste anything you have — notes, an email, a requirements doc, bullet
  points, even rough/incomplete thoughts. Any format is fine. Or give me
  the path to an existing file with this information."

Accept:
- Free text pasted in chat, and/or
- A path to an existing file (any format)

## Step 2 — Draft context.md
Map the raw input onto every section of context-template.md:
  1. What This Service Does
  2. Actors
  3. Key Flows (happy + unhappy path)
  4. Endpoints
  5. Integrations
  6. Business Rules
  7. Non-Functional Requirements
  8. Constraints
  9. Out of Scope
  10. Open Questions
  11. Tech Stack

For each section:
- Fill in anything the raw input states or clearly implies. Mark
  agent-inferred content with "(inferred — confirm)".
- If a section has nothing to go on, write `[MISSING — ask user]`.

## Step 3 — Missing Information Checklist
Produce a numbered, plain-language checklist — one question per
`[MISSING — ask user]` marker, grouped by section, written for a
non-technical reader. Examples:
  1. (Tech Stack) What programming language/framework will this use? If
     you're not sure, say "not sure — recommend one" and the architect can
     decide later at /plan-arch.
  2. (Actors) Who are the different types of people or systems that will
     use this? (e.g. "customer", "admin", "support team", "another
     internal service")
  3. (NFRs) Roughly how many users/requests per day? Any uptime
     requirement (e.g. "must be up during business hours" vs "24/7")?
  4. (Constraints) Any rules you must follow (legal, security, "must use
     our existing X system", budget/timeline)?
  5. (Out of Scope) Anything people might assume is included but isn't,
     for this first version?

STOP here. Show the draft context.md AND the checklist. Tell the user:
  "Answer any of these you can — partial answers are fine, and 'not sure'
  is a valid answer for technical questions (the architect will decide
  later). Reply with your answers, or say 'good enough, proceed' to save
  the draft as-is with the remaining [MISSING — ask user] markers for
  later."

## Step 4 — Iterate
On each reply:
- Update context.md, resolving `[MISSING — ask user]` markers for
  anything answered
- Re-run Step 3 for anything still open
- Repeat until the user says "good enough, proceed" or no
  `[MISSING — ask user]` markers remain

## Step 5 — Save
Save the finished draft to `.specify/contexts/{feature}.md` (the file
/specify reads — confirm `{feature}` matches manifest.project.feature, or
ask the user to fill manifest.project.feature if blank).

If the raw input in Step 1 was non-trivial (more than a couple of lines, or
an uploaded/linked file), ask:
  "Keep your original notes for reference at
  .specify/contexts/{feature}.raw.md? (recommended — lets you re-run
  /create-context later with more detail, e.g. when scope changes from
  pilot to mvp/full). yes/no"

If yes, save the raw input verbatim to `.specify/contexts/{feature}.raw.md`
with this header:
```
# Pre-context notes — reference only
# Not read by /specify or any other SDD command (AI-2)
# Source for .specify/contexts/{feature}.md — regenerate via /create-context
```

- State: "Context file ready at .specify/contexts/{feature}.md
  ({N} of {M} sections complete, {K} still marked [MISSING — ask user]).
  Run /specify to generate constitution Part 2 (DRAFT) + spec docs."
- If any `[MISSING — ask user]` markers remain, add: "Note: /specify
  Action 1 will carry forward any remaining [MISSING — ask user] markers
  into constitution Part 2 — resolve them at GATE-1."

## Never Do
- Never invent business rules, NFR numbers, or constraints not stated or
  reasonably inferable — use `[MISSING — ask user]` instead
- Never skip the Missing Information Checklist, even if the draft looks
  complete
- Never overwrite an existing `.specify/contexts/{feature}.md` without
  confirming with the user first (offer to show a diff / merge instead)
- Never read `.specify/contexts/{feature}.raw.md` in any command other than
  /create-context (AI-2 — it is reference-only)
