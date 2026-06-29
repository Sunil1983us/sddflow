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
| BO-{NNN} | {objective} | {how measured} |

## 3. Stakeholders (BA-3 — see .specify/memory/roles.yml for named owners)

| ACT-ID | Role | Team | Responsibility |
|---|---|---|---|
| _(set by /specify-uc)_ | Product Owner | {team} | Approves requirements, /validate + /release sign-off |
| _(set by /specify-uc)_ | Business Analyst | {team} | Requirements accuracy, /validate |
| _(set by /specify-uc)_ | Tech Lead | {team} | Reviews architecture, /analyze risk review |
| _(set by /specify-uc)_ | Architect | {team} | /plan-design (ADR entries) review (mvp+) |
| _(set by /specify-uc)_ | Senior Developer | {team} | /plan-lld review (mvp+), implements |
| _(set by /specify-uc)_ | QA Lead | {team} | Test cases, UAT sign-off, /release |
| _(set by /specify-uc)_ | Security Officer | {team} | security-design review (mvp+/full) |
| _(set by /specify-uc)_ | DevOps/SRE | {team} | Runbook, deployment, /release go-live |
| _(set by /specify-uc)_ | UX Lead | {team} | UX/screen review (UI-facing features) |

> ACT-NNN identifiers are assigned by `/specify-uc`. Human actors become Primary or Secondary actors; system integrations become System actors.

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
| BR-{NNN} | {description} | Must Have |
| BR-{NNN} | {description} | Should Have |

## 6. Regulatory and Compliance
| Regulation | Requirement | Impact |
|---|---|---|
| {regulation} | {requirement} | {design impact} |

## 7. Assumptions

> **Two markers — use the right one:**
> - `[ASSUMPTION-NNN: ...]` — agent made a reasonable default and proceeded; business owner confirms/rejects at /validate
> - `[NEEDS CLARIFICATION: {specific question}]` — no safe default; human must answer before /validate sign-off

- [ASSUMPTION-{NNN}] {assumption made due to gap in context}
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
