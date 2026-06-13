# Business Requirements Document (BRD)
# Feature: {Feature Name}
> Version: 1.0 | Status: Draft | Date: {date} | Author: {author}

---

## 1. Executive Summary
{2-3 sentences: what is being built, why, and for whom.}

## 2. Business Objectives
| ID | Objective | Success Metric |
|---|---|---|
| BO-001 | {objective} | {how measured} |

## 3. Stakeholders (BA-3 — see .specify/memory/roles.yml for named owners)
| Role | Team | Responsibility |
|---|---|---|
| Product Owner | {team} | Approves requirements, /validate + /release sign-off |
| Business Analyst | {team} | Requirements accuracy, /validate |
| Tech Lead | {team} | Reviews architecture, /analyze risk review |
| Architect | {team} | /plan-adr review (mvp+) |
| Senior Developer (Mobile) | {team} | /plan-lld review (mvp+), implements |
| QA Lead | {team} | Test cases, UAT sign-off, /release |
| Security Officer | {team} | security-design review (mvp+/full) |
| DevOps/SRE | {team} | Runbook, app-store release pipeline, /release go-live |
| UX Lead | {team} | screen-spec / ux-flow review |

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
- [ASSUMPTION-001] {assumption made due to gap in context}

## 8. Success Criteria
- [ ] {verifiable end-to-end criterion}
- [ ] {verifiable criterion}

---
*Generated from: .specify/contexts/{feature}.md*
