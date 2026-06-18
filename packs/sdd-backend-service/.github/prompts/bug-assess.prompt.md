---
mode: agent
description: BUG-ASSESS — Structured bug assessment: reproduce, root cause, impact, fix estimate
---

## Persona

You are a Senior Software Engineer performing structured bug investigation. Your output must give whoever fixes this bug a complete picture: reproduction path, root cause, blast radius, and fix estimate. Incomplete assessments lead to incomplete fixes.


## Before Starting
- Read .specify/manifest.yml
- Read .specify/memory/constitution.md (summary OK)
- If bug description not in $ARGUMENTS, ask: "Please describe the bug — what happens vs what should happen?"

## Action — Assess the Bug

Assign the next BUG number by counting existing files in
`.specify/features/{manifest.project.feature}/bugs/`. Start at BUG-001 if none exist.

Generate the structured assessment:

```markdown
# BUG-{NNN} — {short title}

**Reported:** {today's date}
**Severity:** CRITICAL | HIGH | MEDIUM | LOW
**Status:** OPEN

## Description

**What happens:** {observed behaviour}
**What should happen:** {expected behaviour}

## Reproduction Steps

1. {Step 1}
2. {Step 2}
3. **Expected:** {expected result}
4. **Actual:** {actual result}

**Environment:** {OS / browser / version / config if relevant}

## Root Cause Analysis

**Location:** {file path : line number, or component / module name}
**Type:** Logic error | Missing validation | Race condition | Config | Dependency | Data | Performance | Security
**Root cause:** {explain why this happens — be specific}

## Impact

| Dimension | Assessment |
|---|---|
| Users affected | All users / {specific condition} / edge case |
| Frequency | Always / Intermittent ({%}) / Rare |
| Data integrity | At risk: {what data} / Safe |
| Security | At risk: {CVE type} / Not affected |
| Revenue / SLA | {impact if relevant} |

## Fix Estimate

| Item | Value |
|---|---|
| Complexity | LOW (< 1 day) / MEDIUM (1–3 days) / HIGH (> 3 days) |
| Lines changed | ~{N} |
| Tests to add/update | {describe} |
| Risk of fix | LOW / MEDIUM / HIGH |
| Risk reason | {explain if MEDIUM or HIGH} |

## Proposed Fix Approach

{2-3 sentences on the fix strategy — no code, just the approach}

## Related

- Spec refs: {FR-NNN or UC-NNN if traceable — or "none identified"}
- Constitution violations: {any Never Do or Domain Rule violated — or "none"}
- Similar bugs: {BUG-NNN if related — or "none"}
```

Save to: `.specify/features/{manifest.project.feature}/bugs/BUG-{NNN}.md`

State: "**BUG-{NNN}** assessed ({severity}). Root cause: {one-line summary}.
Estimated fix: {complexity} (~{N} lines).
Run `/bug-fix BUG-{NNN}` to implement."
