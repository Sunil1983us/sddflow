# Validation Report — Business Sign-Off
# Feature: {Feature Name}
> Version: 1.0 | Status: Draft | Date: {date: YYYY-MM-DD} | Author: {author}
> Run after: Constitution Part 2 finalized | Gate before: /analyze

---

## References
| Source | Sections / IDs Used |
|---|---|
| brd.summary.md | {sections/IDs referenced} |
| use-cases.summary.md | {UC-NNN actor + flow confirmed} |
| srd.summary.md | {sections/IDs referenced} |

## 0a. Needs Clarification Scan (blocking)

> Every `[NEEDS CLARIFICATION-NNN: ...]` marker in brd.md, use-cases.md, or
> srd.md must be answered before business sign-off. Empty table = none found.

| ID | Locations | Question |
|---|---|---|
| {doc}:NC-{NNN} | {doc}:NC-{NNN}{, other-doc:NC-{NNN} if duplicated} | {marker text, verbatim} |

## 1. Business Objective Trace

| BO-NNN (from BRD) | Objective | Success Metric | Addressed By (FR-NNN) | Reviewer Confirms |
|---|---|---|---|---|
| BO-{NNN} | {objective} | {metric} | FR-{NNN}, FR-{NNN} | [ ] |

---

## 2. Business Requirements Review

> Two-column sign-off: the Business Analyst confirms technical reflection; the Product Owner confirms business intent. Each signs only their column.

| BR-NNN | Requirement | Priority | BA Confirms: FR-NNN satisfies BR-NNN? | PO Confirms: Intent matched? |
|---|---|---|---|---|
| BR-{NNN} | {requirement} | Must Have | [ ] Yes  [ ] No — FR-{NNN} | [ ] Yes  [ ] No — comment: |

---

## 3. Assumptions Sign-Off

All `[ASSUMPTION-NNN]` items from BRD/SRD — business owner confirms each:

| ID | Assumption | Correct? | Comment |
|---|---|---|---|
| ASSUMPTION-{NNN} | {assumption} | [ ] Yes [ ] No | |

---

## 3a. Use Case Business Review

> Confirm that each UC-NNN in use-cases.md represents a real business scenario.

| UC-ID | Title | Actor | Business Scenario Correct? | Missing Paths? |
|---|---|---|---|---|
| UC-{NNN} | {title} | ACT-{NNN} | [ ] Yes [ ] No | {any missing AP/EP from business view} |

**Notes:** {anything the business wants to add or change in any use case}

---

## 4. Scope Confirmation

**In Scope (confirmed):**
- [ ] {item}

**Out of Scope (confirmed acceptable):**
- [ ] {item}

---

## 4a. Security Design Sign-Off (mvp+ and full scope only)

> Skip this section for `pilot` scope.

| Status | Reviewer | Date |
|---|---|---|
| {see security-design.md sign-off marker} | {Security Officer — from roles.yml} | |

**If status is `pending`:** Security Officer sign-off on `security-design.md` is required before `/analyze` can proceed.

---

## 4b. Indicative Effort (T-shirt)

> Indicative only — sized so the sign-off decision is made with an effort
> signal in view. Real estimates happen at /task (story points per task);
> a mismatch there triggers a change request, not a silent re-scope.

| FR-NNN | Size | Main effort driver |
|---|---|---|
| FR-{NNN} | S / M / L / XL | {e.g. new integration, migration, complex validation} |

**Total indicative size:** {S/M/L/XL} — {1-line rationale}

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
| CR-{NNN} | {change description} | {role} | {brd / srd / use-cases} | {owner} | {how resolved} | |

**Re-sign-off:** All CR-NNN items resolved → update context.md → re-run `/specify` for affected docs → re-run `/validate`. PO and BA re-sign §5.

---

## 7. Outcome

State one of:
- "VALIDATE complete — all objectives traced, all assumptions confirmed, no open CR-NNN. Ready for /analyze."
- "VALIDATE BLOCKED — Security Officer must approve security-design.md (§4a) before /analyze can proceed."
- "VALIDATE incomplete — {N} CR-NNN items open. Resolve and re-validate before /analyze."

---

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| Product Owner (accountable) | | Pending | |
| Business Analyst (responsible) | | Pending | |

## Version History

| Version | Date | Changed By | Summary of Changes | CHG-NNN |
|---|---|---|---|---|
| 1.0 | {date: YYYY-MM-DD} | {author} | Initial draft | — |
