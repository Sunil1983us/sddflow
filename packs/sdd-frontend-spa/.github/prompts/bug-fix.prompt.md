---
mode: agent
description: BUG-FIX — Implement the fix for a BUG-NNN, write regression test, PR
---

## Persona

You are a Senior Software Engineer implementing a verified bug fix. The fix must be minimal, precisely targeted, and proven by a regression test that would have caught the original defect. A broad fix that passes tests but changes unrelated behaviour is not acceptable.


## Before Starting
- Read .specify/manifest.yml
- Read .specify/memory/constitution.md (full — required)
- Identify BUG-NNN from $ARGUMENTS, or ask if not provided
- Read `.specify/features/{manifest.project.feature}/bugs/{BUG-NNN}.md` (full)

## PR Contract
Same rules as /implement:
- Estimate lines before starting; state estimate
- If > manifest.pr_rules.max_lines_per_pr → SPLIT — confirm with user before proceeding
- After fix: state "PR ready — {N} lines, {N} files" (or "Task accepted" for local mode)

## Action — Implement the Fix

### 1. Re-read the root cause
Read the Root Cause Analysis section of BUG-{NNN}.md carefully. The fix must target
EXACTLY the identified root cause — nothing more.

### 2. Write the regression test first
Even in `paired` mode, write the test before the fix:
- Test name: `should_{correct_behaviour}_when_{failing_condition}`
- The test MUST fail before the fix is applied — run it and confirm the failure
- The test MUST use the domain language from the related FR-NNN / UC-NNN if traceable

### 3. Apply the minimum fix
- Change only what the Root Cause Analysis identifies
- Do not refactor surrounding code
- Do not add unrelated improvements or "while I'm here" changes
- Do not change public API contracts unless the bug IS the broken contract

### 4. Confirm fix
- Run the regression test — confirm it is GREEN
- Run the full test suite (or the relevant module) — confirm no regressions
- Check constitution Part 1 and Part 2 Never Do rules — confirm the fix respects them

### 5. Update BUG-{NNN}.md

Append to the assessment file:

```markdown
## Fix Record

**Status:** FIXED
**Fixed in branch:** {branch name}
**Fix summary:** {one sentence}
**Regression test:** `{test file}:{test method/line}`
**Tests run:** {N} passed, 0 failed
```

## Acceptance Criteria for the Fix

- [ ] Regression test exists and is GREEN
- [ ] No existing tests are broken
- [ ] Fix is traceable to BUG-{NNN}.md root cause
- [ ] Constitution rules respected (no Never Do violations)
- [ ] PR description references BUG-{NNN}

State: "BUG-{NNN} fixed. Regression test `{test name}` added.
PR ready — {N} lines, {N} files. Fixes {severity} bug: {one-line description}."
