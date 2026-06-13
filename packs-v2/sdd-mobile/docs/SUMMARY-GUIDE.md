# Summary Guide

## What Is a Summary?
Every generated document gets two files:
- `{doc}.md` — full document (you review)
- `{doc}.summary.md` — compressed handoff (agent reads for next verb)

## Why
Without summaries: 15,000+ tokens by verb 4
With summaries: ~600 tokens constant every verb

## Format
```
# {Document} Summary — {Feature}
> Lines: {N} / {SUMMARY_MAX_LINES}
## What — 1-2 sentences
## Key Decisions — bullets
## Key Artifacts — identifiers only
## Constraints — hard rules
## Out of Scope — excluded items
```

## Change the Limit
Edit `.specify/memory/summary-rules.md`:
```
SUMMARY_MAX_LINES: 20   ← change this
```
Tell agent: "Summary rules updated — re-read summary-rules.md"

## Recommended by Scope
| Scope | Lines | Tokens |
|---|---|---|
| Pilot | 15-20 | ~250 |
| MVP | 20-25 | ~350 |
| Full | 25-35 | ~450 |

## What Each Command Reads (AI-2 — summary-first, mandatory)
SPECIFY reads: context.md (full — first run only)
GATE-1 (manual): you read constitution.md Part 2 in full to finalize it
VALIDATE reads: brd.summary + srd.summary
ANALYZE reads: validate.summary + srd.summary + brd.summary
CLARIFY reads: all spec summaries + analyze.summary
PLAN-ARCH reads: clarify.summary + analyze.summary + all spec summaries
PLAN-HLD reads: arch.summary + analyze.summary
PLAN-LLD reads: plan.summary + arch.summary
PLAN-ADR reads: arch.summary + analyze.summary
TASK reads: plan.summary + analyze.summary + clarify.summary
IMPLEMENT reads: tasks.md (one task, full) + constitution.md (full)
RELEASE reads: tasks.md + qa-testcases.summary + brd.summary + srd.summary

After /specify, no command should read a full `.md` document except the
two exceptions above (GATE-1 manual review, and IMPLEMENT's tasks.md +
constitution.md).
