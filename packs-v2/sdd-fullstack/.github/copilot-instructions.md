# Copilot Instructions — SDD Framework

## Before Every Response
Read .specify/manifest.yml + constitution.md + summary-rules.md

## SPECIFY — Two Actions
Action 1: Generate constitution.md Part 2 from context
  (Tech Stack — Backend / Frontend / Shared + Principles + Domain Rules +
  Never Do)
Action 2: Generate spec documents per scope

## 9 Commands

| Command | Verb | Does |
|---|---|---|
| /specify | SPECIFY | Constitution + spec docs |
| /analyze | ANALYZE | Risks + complexity |
| /clarify | CLARIFY | Questions → you answer |
| /plan-arch | PLAN-ARCH | Architecture + plan.md |
| /plan-hld | PLAN-HLD | HLD + Mermaid diagrams |
| /plan-lld | PLAN-LLD | LLD (mvp+ only) |
| /plan-adr | PLAN-ADR | ADRs (mvp+ only) |
| /task | TASK | Stories + Tasks + Jira |
| /implement | IMPLEMENT | One task at a time |

## Gates
/analyze before /clarify
/clarify (all answered) before /plan-arch
/plan-arch reviewed before /plan-hld
/plan-hld reviewed before /plan-lld or /task
/task (approved) before /implement

## Pilot Scope — Skip These
/plan-lld → skip (state: pilot scope)
/plan-adr → skip (state: pilot scope)

## Summary
After every doc: write .summary.md — max SUMMARY_MAX_LINES

## PR Rule
Estimate → split if >max_lines_per_pr → confirm → one at a time
