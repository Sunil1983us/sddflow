# Change Management Guide
# How Changes Work in the SDD Framework

---

## The Fundamental Rule

> Never change code directly.
> Change the context first.
> Let the pipeline propagate.

This keeps every document, every class, and every test
in sync with each other — permanently.

---

## Why This Matters

```
Without this rule:
  Code v1.2  ←──── out of sync
  Spec v1.0  ←──── stale
  Tests v1.1 ←──── partial

  Result: nobody knows what the system actually does.
  AI in next session: generates wrong code because it reads stale docs.

With this rule:
  Code v1.2  ←──┐
  Spec v1.2  ←──┤ always in sync
  Tests v1.2 ←──┘

  Result: AI always has accurate context.
  Onboarding: read context.md — understand the whole system.
```

---

## The Three Types of Change

### Type 1 — Additive (new field, new rule, new endpoint)
Something new is added. Existing behaviour unchanged.
```
Example: Add X-Priority header support
Example: Add clearing_ref to response
Example: Add new GET /payments/{id}/status endpoint
```

### Type 2 — Modification (change existing behaviour)
Existing behaviour changes. May break consumers.
```
Example: Change payment status REJECTED → DECLINED
Example: Change timeout from 1,000ms to 2,000ms
Example: Change reconciliation from 3 fields to 4 fields
```

### Type 3 — Scope Upgrade (new capability cluster)
A new area of functionality is added. Multiple documents affected.
```
Example: Add retry + circuit breaker (pilot → mvp)
Example: Add inbound payment flow
Example: Add investigation case workflow
```

---

## The Change Workflow — Step by Step

### STEP C1 — Write the Change in Context

Open `.specify/contexts/{feature}.md`

Add to the CHANGELOG section at the bottom:

```markdown
### v1.1 — 2026-06-15 — {your name}
- Added: X-Priority header support on all inbound requests
- Changed: nothing
- Removed: nothing
- Impact: api-spec.md, srd.md (FR-016 added)
```

Also update the relevant section of the context:

```markdown
## HTTP Headers

### Before (v1.0)
| Header | Mandatory |
|---|---|
| X-Correlation-Id | Yes |

### After (v1.1) — added X-Priority
| Header | Mandatory |
|---|---|
| X-Correlation-Id | Yes |
| X-Priority | No — HIGH, NORMAL, LOW |
```

---

### STEP C2 — Run Impact Analysis

**Claude Code:**
```
Read .specify/memory/change-rules.md
Read .specify/contexts/{feature}.md — focus on latest CHANGELOG entry

Perform impact analysis for the change in v{N.N}:
  1. List every document that needs updating
  2. List every document that is NOT affected
  3. Estimate new tasks needed
  4. Estimate total lines and PRs

Use the impact matrix from change-rules.md.
Do NOT update anything yet — analysis only.
Show results in the impact analysis format.
```

**GitHub Copilot:**
```
@workspace Read .specify/memory/change-rules.md
Read .specify/contexts/{feature}.md changelog v{N.N}

Perform impact analysis only — do not change anything.
Show: documents to update, documents to skip, new tasks needed.
```

**Example Output:**
```
CHANGE: Add X-Priority header support
VERSION: v1.1

CONTEXT UPDATED: ✅

DOCUMENTS TO UPDATE:
  ✅ srd.md          — add FR-016: X-Priority header support
  ✅ api-spec.md     — add X-Priority to header tables
  ✅ srd.summary.md  — regenerate
  ✅ api-spec.summary.md — regenerate
  ⏭ arch.md         — not affected
  ⏭ data-model.md   — not affected
  ⏭ hld.md          — not affected
  ⏭ lld.md          — not affected
  ⏭ plan.md         — not affected

NEW TASKS:
  CHG-001: Add X-Priority to IcsHeaders record — est. 20 lines — 1 PR
  CHG-002: Update controllers to read X-Priority — est. 40 lines — 1 PR
  CHG-003: Update mock adapters to propagate X-Priority — est. 30 lines — 1 PR
  CHG-004: Update integration tests — est. 60 lines — 1 PR

TOTAL: 2 documents, 4 tasks, ~150 lines, 4 PRs
```

---

### STEP C3 — Review Gate (You)

Before the agent touches anything:
```
Review the impact analysis.

Questions to ask:
  □ Are the right documents listed for update?
  □ Are any documents incorrectly included?
  □ Do the new tasks make sense?
  □ Is the estimate reasonable?

Type "go" to proceed.
Type "adjust: {what to change}" to correct the analysis.
```

---

### STEP C4 — Update Documents

**Claude Code:**
```
Read .specify/memory/change-rules.md
Read .specify/contexts/{feature}.md — v{N.N} changes only
Read the current version of each affected document

Update ONLY these documents:
  - srd.md  (add FR-016)
  - api-spec.md (add X-Priority to header tables)

Rules:
  - Preserve all existing content
  - Add new content in the correct section
  - Mark new content with a version comment: <!-- v1.1 -->
  - Do NOT rewrite existing sections
  - Regenerate .summary.md for each updated document

Show a diff summary after each update:
  "srd.md: added FR-016 in Section 3.1 — 8 lines added"
```

**GitHub Copilot:**
```
@workspace Read .specify/memory/change-rules.md
Read current srd.md and api-spec.md

Update srd.md: add FR-016 for X-Priority header support.
Update api-spec.md: add X-Priority to all header tables.
Preserve all existing content.
Regenerate both .summary.md files.
```

---

### STEP C5 — Add Change Tasks to tasks.md

**Claude Code:**
```
Read .specify/features/{feature}/tasks.md

Append a new change set section at the bottom:

## Change Set: v1.1 — {date} — X-Priority header support

### CHG-001 — Add X-Priority to IcsHeaders record
Dependencies: none
Estimated lines: 20 | PR: single
Files: IcsHeaders.java
Acceptance criteria:
  - [ ] X-Priority field added to IcsHeaders record
  - [ ] Optional — defaults to NORMAL if absent
  - [ ] Unit test: IcsHeaders created with and without X-Priority

### CHG-002 — Update controllers to read X-Priority
...

Save updated tasks.md. List all CHG tasks added.
```

---

### STEP C6 — Implement Change Tasks

Same as normal implementation — one task at a time.
PR rules still apply — max 400 lines per PR.

**Claude Code:**
```
Read .specify/memory/constitution.md
Read .specify/features/{feature}/tasks.md

Execute CHG-001: Add X-Priority to IcsHeaders record.
Estimate lines — state PR strategy.
Write implementation + paired test.
Confirm acceptance criteria met.
Wait for go before CHG-002.
```

---

## Change Impact By Document

Use this as a quick reference to know what needs updating:

### Changed: Business Rule
```
Update: context.md → srd.md → arch.md (if structural)
Skip:   brd.md, hld.md, data-model.md, api-spec.md
Tasks:  1-3 CHG tasks
```

### Added: New Field to Request/Response
```
Update: context.md → api-spec.md
Skip:   brd.md, srd.md, arch.md, data-model.md, hld.md
Tasks:  1-2 CHG tasks
```

### Added: New Endpoint
```
Update: context.md → srd.md (new FR) → api-spec.md → lld.md
Skip:   brd.md, arch.md, data-model.md, hld.md
Tasks:  3-5 CHG tasks
```

### Added: New Status
```
Update: context.md → srd.md → api-spec.md → data-model.md → hld.md (diagram)
Skip:   brd.md, arch.md
Tasks:  3-5 CHG tasks
```

### Added: New DB Table
```
Update: context.md → data-model.md → arch.md → lld.md
Skip:   brd.md, srd.md, api-spec.md, hld.md
Tasks:  2-3 CHG tasks (Flyway + adapter + tests)
```

### Changed: NFR (timeout, SLA, TPS)
```
Update: context.md → srd.md (NFR section) → resilience.md
Skip:   brd.md, arch.md, data-model.md, api-spec.md, hld.md
Tasks:  1-3 CHG tasks (config changes)
```

### Scope Upgrade (pilot → mvp)
```
Update: context.md → manifest.yml → new documents (lld, resilience, adr...)
New documents generated: only the newly enabled ones
Tasks:  many CHG tasks
```

---

## Version Control Conventions

### Context File Versioning
```
# In context.md header:
# Version: 1.2

# In CHANGELOG:
### v1.2 — 2026-06-20 — Sunil
- Added: retry config per downstream service
- Impact: srd.md (NFR-008), resilience.md
```

### Document Versioning
Each updated document gets a version comment on changed sections:
```markdown
<!-- Updated: v1.1 — added X-Priority header -->
| X-Priority | No | HIGH, NORMAL, LOW |
```

### Task Versioning
```markdown
## Change Set: v1.1 — 2026-06-15 — X-Priority
CHG-001 ...

## Change Set: v1.2 — 2026-06-20 — Retry config
CHG-005 ...
```

### Git Commit Conventions for Changes
```bash
# Document updates
git commit -m "docs(v1.1): update srd + api-spec for X-Priority header"

# Implementation changes
git commit -m "feat(CHG-001): add X-Priority to IcsHeaders record"
git commit -m "feat(CHG-002): update controllers to read X-Priority"
git commit -m "test(CHG-004): update integration tests for X-Priority"
```

---

## What Happens If Code Changes Without Context Update

If someone changes code without updating context.md:

```
Next AI session:
  Agent reads stale context.md
  Agent generates code based on stale context
  New code contradicts existing change
  Regression introduced

Fix protocol:
  1. Revert the direct code change
  2. Update context.md with what changed and why
  3. Run impact analysis
  4. Let the pipeline generate the correct change
```

This is why `constitution.md` has the rule:
**"Never change code without updating context first."**

---

## Change Prompts — Quick Reference

### Impact Analysis
```
Read change-rules.md + contexts/{f}.md (latest changelog)
Perform impact analysis only — do not change anything.
Show: update/skip list + new tasks + total estimate.
```

### Update Documents
```
Read change-rules.md + contexts/{f}.md (v{N.N} only)
Update ONLY: {list from impact analysis}
Preserve all existing content.
Regenerate summaries for updated docs.
Show diff summary after each.
```

### Add Change Tasks
```
Read tasks.md
Append Change Set v{N.N} section with CHG-NNN tasks.
Each task: description, dependencies, estimated lines, acceptance criteria.
```

### Implement Change Task
```
Read constitution.md + tasks.md
Execute CHG-{NNN}: {title}
Estimate lines, split if needed, implement + test, confirm criteria.
```

