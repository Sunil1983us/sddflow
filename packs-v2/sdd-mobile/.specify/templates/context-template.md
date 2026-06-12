# System Context — {Service Name}
# Version: {version} | Scope: {pilot | mvp | full}
# Date: {date} | Author: {author}

> This is the single source of truth for this service.
> All documents, code, tasks, and tests are derived from this file.
> Never change code without updating this context first.

---

## 1. What This Service Does
{2-3 sentences. What problem does it solve? What does it process?}

## 2. Actors
| Actor | Type | Role |
|---|---|---|
| {name} | Human / System | {role} |

## 3. Key Flows

### Flow 1: {Name} — Happy Path
Step 1: {who does what}
Step 2: {system calls downstream → result}
Step 3: {outcome}

### Flow 2: {Name} — Unhappy Path (if in scope)
Trigger: {what causes this}
Steps: {what happens + resolution}

## 4. Endpoints
| Method | Path | Purpose | Caller | Request | Response |
|---|---|---|---|---|---|
| POST | /api/v1/{resource} | {purpose} | {caller} | {type} | {type} |

## 5. Integrations
| System | Direction | Purpose | Phase 1 |
|---|---|---|---|
| {name} | Inbound/Outbound | {purpose} | Mock/Real |

## 6. Business Rules
- {Rule 1 — specific and verifiable}
- {Rule 2}

## 7. Non-Functional Requirements
| Category | Requirement |
|---|---|
| Performance | {P99 response target} |
| Availability | {uptime target} |
| Throughput | {TPS peak} |
| Data Retention | {years} |

## 8. Constraints
- {Technical constraint}
- {Regulatory constraint}

## 9. Out of Scope
- {Excluded item 1}
- {Excluded item 2}

## 10. Open Questions
| ID | Question | Owner | Due |
|---|---|---|---|
| OQ-001 | {question} | {owner} | {date} |

---

## CHANGELOG

### v1.0 — {date} — {author}
- Added: Initial version

### How to add future entries:
v{N.N} — {date} — {author}
Added:   {new capability or rule}
Changed: {what was modified and why}
Fixed:   {what was corrected}
Removed: {what was explicitly removed}
Impact:  {which documents need updating}

