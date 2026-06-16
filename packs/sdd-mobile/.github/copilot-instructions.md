# Copilot Instructions — SDD Framework

## Before Every Response
Read .specify/manifest.yml + constitution.md + summary-rules.md +
change-rules.md + roles.yml

## SPECIFY — Two Actions
Action 1: Generate constitution.md Part 2 from context — DRAFT
  (Tech Stack 20 concerns + Principles + Domain Rules + Never Do)
Action 2: Generate spec documents per scope:
  pilot: brd, srd, security-design (§1)
  mvp:   + screen-spec, ux-flow, api-spec (§1-2 security-design)
  full:  + data-model, resilience, investigation, security-design (§1-4)

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)
Part 2 from Action 1 is a DRAFT. User must review every row and confirm
"Constitution Part 2 finalized" before /validate. Manual edits after this
are authoritative — never silently overwritten by a later /specify.

## 11 Commands

| Command | Verb | Does |
|---|---|---|
| /specify | SPECIFY | Constitution Part 2 (draft) + spec docs |
| — GATE-1 — | (manual) | User finalizes constitution Part 2 |
| /validate | VALIDATE | Business sign-off on brd/srd |
| /analyze | ANALYZE | Risks + complexity |
| /clarify | CLARIFY | Questions → you answer |
| /plan-arch | PLAN-ARCH | Architecture + plan.md + screen-spec/ux-flow/api-spec/data-model/security/resilience refinement |
| /plan-hld | PLAN-HLD | HLD + Mermaid diagrams |
| /plan-lld | PLAN-LLD | LLD (mvp+ only) |
| /plan-adr | PLAN-ADR | ADRs (mvp+ only) |
| /task | TASK | Stories + Tasks + Jira |
| /implement | IMPLEMENT | One task at a time |
| /release | RELEASE | UAT + store-release plan + go-live gate |

## Gates
GATE-1 (constitution Part 2 finalized) before /validate
/validate (sign-off) before /analyze
/analyze before /clarify
/clarify (all answered) before /plan-arch
AI-8: no unresolved [ASSUMPTION-NNN] in any spec doc before /plan-arch
/plan-arch reviewed before /plan-hld
/plan-hld reviewed before /plan-lld or /task
/task (approved) before /implement
/implement (all tasks merged) before /release

## Pilot Scope — Skip These
/plan-lld → skip (state: pilot scope)
/plan-adr → skip (state: pilot scope)

## AI-7 — Apply Glob-Scoped Instructions
Apply every `.github/instructions/*.instructions.md` file's `applyTo`
glob to any matching file you create or edit (screens/services/tests).

## Summary
After every doc: write .summary.md — max SUMMARY_MAX_LINES (AI-2:
summary-first — read only .summary.md after /specify, except /implement
which reads tasks.md + constitution.md in full)

## PR Rule
Estimate → split if >max_lines_per_pr → confirm → one at a time
