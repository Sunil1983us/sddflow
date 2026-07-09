# Copilot Instructions — SDD Micro

Tiny/personal projects only — 3 commands, no BRD/UC/SRD/Validate/
Analyze/Clarify/Design/Release ceremony. See `CLAUDE.md` for why.

## Before Every Response
Read `.specify/manifest.yml` + `.specify/memory/constitution.md`

## Commands

| Command | Does | Gate |
|---|---|---|
| `/create-context` *(optional)* | Rough notes → short context.md | — |
| `/specify` | Constitution Part 2 (DRAFT) — tech stack + ground rules | — |
| — GATE-1 — | User reviews Part 2 and says "confirmed" | manual |
| `/task` | Flat, numbered task list | GATE-1 |
| `/implement` | One task at a time, verified as you go | tasks.md reviewed |

## GATE-1 — Constitution Part 2 Confirmed (manual, blocking)
Part 2 is a DRAFT until the user reviews it and says "confirmed". Manual
edits after this are authoritative. `/task` cannot run before this.

## Never Do
- Never run /task before GATE-1
- Never run /implement without a tasks.md the user has seen
- Never hardcode secrets or credentials
- Never skip a task's verification step — report the actual result

## Command Order
/create-context (optional) → /specify → [GATE-1] → /task → /implement
