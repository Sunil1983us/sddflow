# Validation Report — Business Sign-Off
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}
> Run after: Constitution Part 2 finalized | Gate before: /analyze

---

## References
| Source | Sections / IDs Used |
|---|---|
| brd.summary.md | {sections/IDs referenced} |
| use-cases.summary.md | {UC-NNN actor + flow confirmed} |
| srd.summary.md | {sections/IDs referenced} |

## 1. Business Objective Trace

| BO-NNN (from BRD) | Objective | Success Metric | Addressed By (FR-NNN) | Reviewer Confirms |
|---|---|---|---|---|
| BO-001 | {objective} | {metric} | FR-{NNN}, FR-{NNN} | [ ] |

---

## 2. Business Requirements Review

> Two-column sign-off: the Business Analyst confirms technical reflection; the Product Owner confirms business intent. Each signs only their column.

| BR-NNN | Requirement | Priority | BA Confirms: FR-NNN satisfies BR-NNN? | PO Confirms: Intent matched? |
|---|---|---|---|---|
| BR-001 | {requirement} | Must Have | [ ] Yes  [ ] No — FR-{NNN} | [ ] Yes  [ ] No — comment: |

---

## 3. Assumptions Sign-Off

All `[ASSUMPTION-NNN]` items from BRD/SRD — business owner confirms each:

| ID | Assumption | Correct? | Comment |
|---|---|---|---|
| ASSUMPTION-001 | {assumption} | [ ] Yes [ ] No | |

---

## 3a. Use Case Business Review

> Confirm that each UC-NNN in use-cases.md represents a real business scenario.

| UC-ID | Title | Actor | Business Scenario Correct? | Missing Paths? |
|---|---|---|---|---|
| UC-001 | {title} | ACT-001 | [ ] Yes [ ] No | {any missing AP/EP from business view} |

**Notes:** {anything the business wants to add or change in any use case}

---

## 4. Scope Confirmation

**In Scope (confirmed):**
- [ ] {item}

**Out of Scope (confirmed acceptable):**
- [ ] {item}

---

## 5. Sign-Off

| Role | Name | Decision | Date |
|---|---|---|---|
| Product Owner | {name} | [ ] Approved  [ ] Changes Requested | |
| Business Analyst | {name} | [ ] Approved  [ ] Changes Requested | |

---

## 6. Change Requests (when §5 decision is "Changes Requested")

> Each change gets a CR-NNN ID. Re-sign-off confirms every CR-NNN is resolved before /analyze proceeds.

| CR-NNN | Description | Raised By | Affects Doc(s) | Owner | Resolution | Resolved Date |
|---|---|---|---|---|---|---|
| CR-001 | {change description} | {role} | {brd / srd / use-cases} | {owner} | {how resolved} | |

**Re-sign-off:** All CR-NNN items resolved → update context.md → re-run `/specify` for affected docs → re-run `/validate`. PO and BA re-sign §5.

---

## 7. Outcome

State one of:
- "VALIDATE complete — all objectives traced, all assumptions confirmed, no open CR-NNN. Ready for /analyze."
- "VALIDATE incomplete — {N} CR-NNN items open. Resolve and re-validate before /analyze."

---

## Approvals
| Role | Status | Date |
|---|---|---|
| Product Owner (accountable) | Pending | |
| Business Analyst (responsible) | Pending | |
