# Copilot Instructions — SDD Framework

## Before Every Response
Read .specify/manifest.yml + constitution.md + summary-rules.md +
change-rules.md + roles.yml

## SPECIFY — Two Actions
- Action 1: Generate constitution.md Part 2 from context — DRAFT
  (Tech Stack 20 concerns + Principles + Domain Rules + Never Do)
- Action 2: Generate spec documents per scope:
  - pilot: brd, srd, security-design (§1)
  - mvp: + api-spec, data-model, security-design (§1-2)
  - full: + resilience, investigation, security-design (§1-4)

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)
Part 2 from Action 1 is a DRAFT. User must review every row and confirm
"Constitution Part 2 finalized" before /validate. Manual edits after this
are authoritative — never silently overwritten by a later /specify.

## Commands

| Command | Verb | Does |
|---|---|---|
| /specify | SPECIFY | Constitution Part 2 (draft) + spec docs |
| — GATE-1 — | (manual) | User finalizes constitution Part 2 |
| /validate | VALIDATE | Business sign-off on brd/srd |
| /analyze | ANALYZE | Risks + complexity |
| /clarify | CLARIFY | Questions → you answer |
| /plan-arch | PLAN-ARCH | Architecture + plan.md + api-spec/data-model/security/resilience refinement |
| /plan-hld | PLAN-HLD | HLD + Mermaid diagrams |
| /plan-lld | PLAN-LLD | LLD (mvp+ only) |
| /plan-adr | PLAN-ADR | ADRs (mvp+ only) |
| /task | TASK | Stories + Tasks + Jira |
| /implement | IMPLEMENT | One task at a time |
| /pre-review | PRE-REVIEW | Code review before PR; checklist → dev picks fixes → agent applies |
| /address-review | ADDR-REVIEW | Address human PR comments; fix, reply, resolve threads, re-request review |
| /release | RELEASE | UAT + deployment + go-live gate |

## Document Review Gates (sdd review)

After each SDD document is generated, submit it for stakeholder approval before
the next document in the phase can proceed:

```bash
sdd review submit --doc brd   # push to Confluence + create Jira review task
sdd review check  --doc brd   # poll outcome (exit 0=approved 1=revision 2=pending)
sdd review apply  --doc brd   # re-push after addressing comments
sdd review status             # dashboard: all documents across all phases
```

Sequence: BRD → SRD → Arch → HLD (specify) · LLD → ADR (planning) · Tasks · Runbook → Release

## Gates
- GATE-1 (constitution Part 2 finalized) before /validate
- /validate (sign-off) before /analyze
- /analyze before /clarify
- /clarify (all answered) before /plan-arch
- AI-8: no unresolved [ASSUMPTION-NNN] in any spec doc before /plan-arch
- /plan-arch reviewed before /plan-hld
- /plan-hld reviewed before /plan-lld or /task
- /task (approved) before /implement
- /pre-review (if enabled) before sdd pr create — runs ONCE per task
- /implement (all tasks merged) before /release

## Pilot Scope — Skip These
- /plan-lld → skip (state: pilot scope)
- /plan-adr → skip (state: pilot scope)

## AI-7 — Apply Glob-Scoped Instructions
Apply every `.github/instructions/*.instructions.md` file's `applyTo`
glob to any matching file you create or edit (api/domain/tests/java).
These model the Java/Spring reference stack (constitution Part 2 →
Language/Framework) — if your stack differs, apply each rule's intent
using that language's idioms and conventions, don't skip it.

## Summary
After every doc: write .summary.md — max SUMMARY_MAX_LINES (AI-2:
summary-first — read only .summary.md after /specify, except /implement
which reads tasks.md + constitution.md in full)

## Never Do
- Never code before context.md updated
- Never hardcode any value
- Never skip paired test
- Never run /release in local mode before all tasks show "Task accepted"

## PR Rule
Estimate → split if >max_lines_per_pr → confirm → one at a time
