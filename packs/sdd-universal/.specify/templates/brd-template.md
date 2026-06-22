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
| BR-001 | {description} | Must Have |
| BR-002 | {description} | Should Have |

## 6. Regulatory and Compliance

> **Domain-aware seeding:** Agent pre-populates known regulations from domain signals in `context.md`.
> Common signals: "payment / card / PCI" → PCI-DSS | "health / patient / PHI" → HIPAA | "EU / GDPR / personal data" → GDPR | "financial / SOX" → SOX | "government / FedRAMP" → FedRAMP.
> Rows without a confirmed regulation are marked `[NEEDS CLARIFICATION: which regulation applies to {area}?]` — these block /validate.

| Regulation | Requirement | Design Impact | Confirmed? |
|---|---|---|---|
| {regulation — pre-seeded from domain or [NEEDS CLARIFICATION]} | {requirement} | {design impact} | [ ] |

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

## 9. Investment Summary

> **Purpose:** Gives the executive sponsor the cost and return context needed to sign off on BRD scope and priority.
> Agent extracts from `context.md` if present; otherwise marks items `[NEEDS CLARIFICATION]`.

| Item | Value | Source / Notes |
|---|---|---|
| Delivery scope | {pilot / mvp / full} | manifest.yml |
| Build effort (T-shirt) | {S < 1 sprint / M 1–3 / L 3–6 / XL 6+} | Derived from analyze.md (filled after /analyze) |
| Estimated team cost | {currency amount or [NEEDS CLARIFICATION]} | {from context.md or business case at {link}} |
| Expected ROI / payback period | {e.g. 12-month payback / {N}× ROI or [NEEDS CLARIFICATION]} | {from context.md or business case} |
| Cost of inaction | {what happens if this is NOT built} | {from context.md problem statement} |
| Business case reference | {link / document title or N/A} | |

> If cost and ROI are commercially sensitive and not appropriate for this document, state: "Investment details are in the business case at {link} — not reproduced here."

---

## Approvals

| Role | Status | Date |
|---|---|---|
| Product Owner (accountable — business objectives sign-off) | Pending | |
| Business Analyst (responsible — requirements accuracy) | Pending | |

## Version History

| Version | Date | Changed By | Summary of Changes | CHG-NNN |
|---|---|---|---|---|
| 1.0 | {date} | {author} | Initial draft | — |
