# Copilot Instructions — SDD Framework

## Before Every Response
Read .specify/manifest.yml + constitution.md + summary-rules.md +
change-rules.md + roles.yml

## SPECIFY — Five Sub-Commands
`/specify` generates constitution Part 2 only (DRAFT). Spec documents are
generated one at a time using dedicated sub-commands:

| Command | Generates | Gate |
|---|---|---|
| `/specify` | Constitution Part 2 (DRAFT) | — |
| `/specify-brd` | BRD | GATE-1 passed |
| `/specify-uc` | Use Cases (ACT-NNN + UC-NNN with MP/AP/EP) | BRD approved |
| `/specify-srd` | SRD | Use Cases approved |
| `/specify-doc {name}` | security / data-model / resilience / investigation | SRD approved |

## GATE-1 — Constitution Part 2 Finalized (manual, blocking)
Part 2 is a DRAFT until the user reviews every row and confirms
"Constitution Part 2 finalized". Manual edits after this are authoritative.
Nothing after /specify runs until GATE-1 passes.

## Commands

| Command | Verb | Does |
|---|---|---|
| /specify | SPECIFY | Constitution Part 2 (DRAFT) |
| — GATE-1 — | (manual) | User finalizes constitution Part 2 |
| /specify-brd | SPECIFY-BRD | Business Requirements Document |
| /specify-uc | SPECIFY-UC | Use Case Specification |
| /specify-srd | SPECIFY-SRD | Software Requirements Document |
| /specify-doc | SPECIFY-DOC | Extended spec documents |
| /checklist | CHECKLIST | Spec quality gate (mandatory mvp+) |
| /validate | VALIDATE | Business sign-off on BRD + Use Cases + SRD |
| /analyze | ANALYZE | Risks + complexity + distributed systems |
| /clarify | CLARIFY | Questions → you answer |
| /plan-design | PLAN-DESIGN | Architecture + Diagrams + API Design + ADRs |
| /plan-lld | PLAN-LLD | LLD (mvp+ only) |
| /task | TASK | Stories + Tasks + Jira |
| /implement | IMPLEMENT | One task at a time |
| /pre-review | PRE-REVIEW | Code review before PR; checklist → dev picks fixes |
| /address-review | ADDR-REVIEW | Address human PR comments; fix, reply, resolve |
| /release | RELEASE | UAT + deployment + go-live gate |

## Document Review Gates (sdd review)

After each SDD document is generated, submit it for stakeholder approval:

```bash
sdd review submit --doc brd        # push to Confluence + create Jira review task
sdd review check  --doc brd        # poll outcome (exit 0=approved 1=revision 2=pending)
sdd review apply  --doc brd        # re-push after addressing comments
sdd review status                  # dashboard: all documents across all phases
```

Sequence: BRD → Use Cases → SRD → Design (specify) · LLD (planning) · Tasks · Runbook → Release

## Gates
- GATE-1 (constitution Part 2 finalized) before /specify-brd
- /specify-brd reviewed before /specify-uc
- /specify-uc reviewed before /specify-srd
- /specify-srd reviewed before /validate
- /validate (sign-off) before /analyze
- /analyze before /clarify
- /clarify (all answered) before /plan-design
- AI-8: no unresolved [ASSUMPTION-NNN] in any spec doc before /plan-design
- /plan-design reviewed before /plan-lld or /task
- /task (approved) before /implement
- /pre-review (if enabled) before sdd pr create — runs ONCE per task
- /implement (all tasks merged) before /release

## Pilot Scope — Skip These
- /plan-lld → skip (state: pilot scope)
- /specify-doc data-model → skip (state: pilot scope)
- /specify-doc resilience → skip (state: pilot scope)

## AI-7 — Apply Glob-Scoped Instructions
Apply every `.github/instructions/*.instructions.md` file's `applyTo`
glob to any matching file you create or edit. These model the reference
stack (constitution Part 2 → Language/Framework) — if your stack differs,
apply each rule's intent using that language's idioms, don't skip it.

## AI-2 — Reading Mode (token economy)
After /specify, read `.summary.md` files for prior documents. Behaviour
governed by `reading_mode` in manifest.yml (default: auto):
- auto: use .summary.md if present; fallback to full + generate
- summary: always use .summary.md; warn if missing
- full: always read full .md (maximum quality)
Exception: /implement always reads tasks.md + constitution.md in full.

## Summary
After every doc: write .summary.md — max SUMMARY_MAX_LINES.

## Never Do
- Never code before context.md updated
- Never hardcode any value
- Never skip paired test
- Never run /release in local mode before all tasks show "Task accepted"

## PR Rule
Estimate → split if >max_lines_per_pr → confirm → one at a time
