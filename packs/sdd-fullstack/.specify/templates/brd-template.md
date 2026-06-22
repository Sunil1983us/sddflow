# Business Requirements Document (BRD)
# Feature: {Feature Name}
> Version: 1.0 | Status: Draft | Date: {date} | Author: {author}

---

## References
| Source | Sections / IDs Used |
|---|---|
| .specify/contexts/{feature}.md | {sections/IDs referenced} |

## 1. Executive Summary
{2-3 sentences: what is being built, why, and for whom.}

## 2. Business Objectives
| ID | Objective | Success Metric |
|---|---|---|
| BO-001 | {objective} | {how measured} |

## 3. Stakeholders
| Role | Team | Responsibility |
|---|---|---|
| Product Owner | {team} | Approves requirements |
| Tech Lead | {team} | Reviews architecture |
| Developer | {team} | Implements |

## 4. Business Context
### Problem Statement
{What problem does this solve? What happens today without this?}

### Scope
In Scope:
- {item}

Out of Scope:
- {item}

## 5. Business Requirements
| ID | Requirement | Priority |
|---|---|---|
| BR-001 | {description} | Must Have |
| BR-002 | {description} | Should Have |

## 6. Regulatory and Compliance
| Regulation | Requirement | Impact |
|---|---|---|
| {regulation} | {requirement} | {design impact} |

## 7. Assumptions

> **Two markers — use the right one:**
> - `[ASSUMPTION-NNN: ...]` — agent made a reasonable default and proceeded; business owner confirms/rejects at /validate
> - `[NEEDS CLARIFICATION: {specific question}]` — no safe default; human must answer before /validate sign-off

- [ASSUMPTION-001] {assumption made due to gap in context}
- Use [NEEDS CLARIFICATION: {specific question}] inline on any BR-NNN where a required detail is missing

## 8. Success Criteria
- [ ] {verifiable end-to-end criterion}
- [ ] {verifiable criterion}

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |

## Version History

| Version | Date | Changed By | Summary of Changes | CHG-NNN |
|---|---|---|---|---|
| 1.0 | {date} | {author} | Initial draft | — |
