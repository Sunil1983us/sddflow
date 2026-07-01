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

## 3. Stakeholders (BA-3 — names from .specify/memory/roles.yml; ACT-NNN assigned by /specify-uc)

| ACT-ID | Role | Name / Team | Responsibility |
|---|---|---|---|
| _(set by /specify-uc)_ | Product Owner | {name from roles.yml — product_owner} | Approves requirements, /validate + /release sign-off |
| _(set by /specify-uc)_ | Business Analyst | {name from roles.yml — business_analyst} | Requirements accuracy, /validate |
| _(set by /specify-uc)_ | Tech Lead | {name from roles.yml — tech_lead} | Reviews architecture, /analyze risk review |
| _(set by /specify-uc)_ | Architect | {name from roles.yml — architect} | /plan-design (ADR entries) review (mvp+) |
| _(set by /specify-uc)_ | Senior Developer | {name from roles.yml — senior_developer} | /plan-lld review (mvp+), implements |
| _(set by /specify-uc)_ | QA Lead | {name from roles.yml — qa_lead} | Test cases, UAT sign-off, /release |
| _(set by /specify-uc)_ | Security Officer | {name from roles.yml — security_officer} | security-design review (mvp+/full) |
| _(set by /specify-uc)_ | DevOps/SRE | {name from roles.yml — devops_sre} | Runbook, deployment, /release go-live |
| _(set by /specify-uc)_ | UX Lead | {name from roles.yml — ux_lead} | UX/screen review (UI-facing features) |

> **ACT-NNN identifiers** are assigned by `/specify-uc`. The Name/Team column is filled by `/specify-brd` from `roles.yml`.
> Omit rows for roles not listed in `roles.yml` (e.g. no UX Lead on a backend-only project).

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
