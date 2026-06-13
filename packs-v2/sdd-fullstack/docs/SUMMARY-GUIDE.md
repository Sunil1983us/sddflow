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

## What Each Verb Reads (AI-2 — summary-first, mandatory)
CREATE-CONTEXT (optional, before SPECIFY) reads: any raw notes provided +
  context.raw.md (if re-run) — writes context.md. No other command ever
  reads context.raw.md.
SPECIFY reads: context.summary.md
ANALYZE reads: srd.summary + brd.summary
CLARIFY reads: all spec summaries + analyze.summary
PLAN reads: clarify.summary + analyze.summary
TASK reads: plan.summary + analyze.summary
IMPLEMENT reads: tasks.md (one task) + constitution.md
