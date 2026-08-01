# Clarification Report — {Feature Name}
> Version: {spec version} | Status: Draft | Date: {date: YYYY-MM-DD} | Author: {author}
> Fill all answers before PLAN begins

---

## References
| Source | Sections / IDs Used |
|---|---|
| All prior spec summaries (brd.summary.md, srd.summary.md, etc.) | {ambiguities/assumptions referenced} |
| analyze.summary.md | {risks/complexity items referenced} |

## AMBIGUITIES — AMB-NNN

### AMB-{NNN}: {Topic}
**Found in:** {document + section}
**The ambiguity:** {two valid interpretations}
**Option A:** {interpretation 1}
**Option B:** {interpretation 2}
**Your answer:** {FILL THIS}

---

## GAPS — GAP-NNN

### GAP-{NNN}: {Topic}
**Needed for:** {which design decision}
**The gap:** {what is missing}
**Your answer:** {FILL THIS}

---

## CONFLICTS — CON-NNN

### CON-{NNN}: {Topic}
**Conflict between:** FR-{NNN} and {rule/FR}
**The conflict:** {describe contradiction}
**Your resolution:** {FILL THIS}

---

## ASSUMPTIONS — ASM-NNN

### ASM-{NNN}: {Topic}
**Assumption:** {what was assumed}
**Found in:** {document + section}
**Basis:** {why assumed}
**Correct?** {FILL: Yes / No — if No: correct version}

---

## OPEN QUESTIONS — OQ-NNN

### OQ-{NNN}: {Topic}
**Question:** {decision needed}
**Impact:** {what cannot be designed without this}
**Options:** {list if applicable}
**Your decision:** {FILL THIS}

---

## High/Critical Risks — R-NNN (from analyze.summary.md §2 Risk Register)

### R-{NNN}: {Risk Title from analyze.summary.md §2 "High/Critical Risks — Detail"}
**Risk:** {description from analyze.summary.md}
**Clarification needed:** {what must be clarified to mitigate this risk}
**Your answer:** {FILL THIS}

---

## CONSISTENCY FINDINGS — CF-NNN (from analyze.summary.md §8, CRITICAL only)

> Every CF-NNN that analyze.md §8 marked CRITICAL must appear here —
> analyze.prompt.md's own severity guide blocks /clarify on an unresolved
> CRITICAL finding.

### CF-{NNN}: {Finding Title from analyze.summary.md §8}
**Inconsistency:** {description from analyze.summary.md §8}
**Clarification needed:** {what must be resolved/confirmed to close this finding}
**Your answer:** {FILL THIS}

---

## STATUS TABLE

| ID | Type | Item | Status |
|---|---|---|---|
| AMB-{NNN} | Ambiguity | {topic} | OPEN |
| GAP-{NNN} | Gap | {topic} | OPEN |
| ASM-{NNN} | Assumption | {topic} | OPEN |
| OQ-{NNN} | Open Question | {topic} | OPEN |
| R-{NNN} | High/Critical Risk | {topic} | OPEN |
| CF-{NNN} | Consistency Finding (CRITICAL) | {topic} | OPEN |

Status: OPEN → RESOLVED / CONFIRMED / DECIDED / CORRECTED

All items must be resolved before PLAN begins.

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| Architect (accountable) | | Pending | |

## Version History

| Version | Date | Changed By | Summary of Changes | CHG-NNN |
|---|---|---|---|---|
| 1.0 | {date: YYYY-MM-DD} | {author} | Initial draft | — |
