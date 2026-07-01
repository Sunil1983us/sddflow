# Analysis Report
# Feature: {Feature Name}
> Version: 1.0 | Status: Draft | Date: {date} | Author: {author}

---

## References
| Source | Sections / IDs Used |
|---|---|
| brd.summary.md | {sections/IDs referenced} |
| use-cases.summary.md | {UC-NNN, EP-NNN-X exception paths referenced} |
| srd.summary.md | {FR-NNN, NFR-NNN referenced} |

## 1. Executive Summary
{2-3 sentences: overall complexity, biggest risks, key recommendation.}
Overall Complexity: LOW | MEDIUM | HIGH
Complexity Context: {1 sentence — e.g. "MEDIUM: 3 external integrations, 1 HIGH data-consistency risk, estimated 3–5 sprints at typical team velocity."}

---

## 2. Risk Register

| ID | Risk | Likelihood | Impact | Linked FR/NFR (AR-3) | Mitigation | Mitigating Tasks |
|---|---|---|---|---|---|---|
| R-{NNN} | {risk} | Low/Med/High | Low/Med/High/Critical | FR-{NNN} / NFR-{NNN} | {action} | _(filled by /task)_ |

Every risk must link to at least one FR-NNN or NFR-NNN it threatens — if
none applies, link to the relevant Domain Rule from constitution Part 2.
Carried into feature-story-template.md Traceability Matrix (R-NNN column).
`Mitigating Tasks` is populated by `/task` — each TASK-NNN that directly addresses this risk is listed here, giving the tech lead a live link from risk to deliverable.

### High/Critical Risks — Detail

#### R-{NNN}: {Risk Title}
**Description:** {what could go wrong}
**Trigger:** {what causes this}
**Linked FR/NFR:** FR-{NNN} / NFR-{NNN}
**Impact on design:** {architectural consequence}
**Mitigation:** {concrete action}

---

## 3. Dependency Map

| Dependency | Type | Owner | Risk | Contingency |
|---|---|---|---|---|
| {system/team} | Blocking/Non-blocking | {owner} | Low/Med/High | {fallback} |

---

## 4. Complexity Assessment

| Area | Complexity | Reason | Likely SPLIT? |
|---|---|---|---|
| {feature area} | Low/Med/High | {reason} | Yes/No |

---

## 5. NFR Impact Analysis

| NFR | Requirement | Design Constraint |
|---|---|---|
| NFR-{NNN} | {requirement} | {what it forces in design} |

---

## 6. Unknowns — Spike Work Needed

| ID | Unknown | Impact | Spike? |
|---|---|---|---|
| U-{NNN} | {what we don't know} | {consequence} | Yes/No |

---

## 7. Recommendation

**Approach:** {suggested implementation approach}

**Items to Raise in /clarify:**
- {ambiguity from R-NNN or U-NNN}

**Tasks Likely Needing SPLIT:**
- {area} — reason: {complexity or size}

---

## 8. Consistency Findings

> This section is populated by cross-artifact consistency checks.
> CRITICAL findings block /clarify until resolved.

| ID | Category | Severity | Location | Summary | Recommendation |
|---|---|---|---|---|---|
| CF-{NNN} | {Duplication\|Ambiguity\|CoverageGap\|TerminologyDrift\|ConstitutionConflict} | CRITICAL\|HIGH\|MEDIUM\|LOW | {doc + section} | {what was found} | {what to do} |

### Severity Guide
- **CRITICAL** — block /clarify: constitution conflict (FR/NFR violates a MUST rule); FR/NFR with zero UC coverage
- **HIGH** — resolve in /clarify: duplicate or conflicting requirements; ambiguous security/performance attribute without threshold
- **MEDIUM** — address before /plan-design: terminology drift; missing non-functional task coverage; underspecified edge case
- **LOW** — optional improvement: wording; minor redundancy

---

## 9. Distributed Systems Consistency

> Skip this section if the feature has no async flows, external integrations,
> or shared mutable state across services. Mark "N/A — synchronous only."

| Area | Risk | Likelihood | Mitigation |
|---|---|---|---|
| Shared mutable state | {race condition or lost update scenario} | Low/Med/High | {optimistic lock / event sourcing / saga} |
| Async delivery | {at-least-once delivery — duplicate handling required?} | Low/Med/High | {idempotency key / deduplication} |
| Saga / distributed tx | {compensation required if step N fails after step N-1 commits?} | Low/Med/High | {compensating transaction list} |
| Eventual consistency window | {how long can data be stale — is that acceptable?} | Low/Med/High | {polling / event notification / read-your-writes} |
| External integration failure | {what is the blast radius if {integration} is down?} | Low/Med/High | {circuit breaker / fallback / graceful degrade} |

**Idempotency requirements:** {list operations that must be idempotent, and their idempotency key strategy}

**At-least-once delivery guarantees:** {list async flows, expected duplicate rate, deduplication approach}

---

## Approvals
| Role | Status | Date |
|---|---|---|
| Tech Lead (accountable) | Pending | |
| Architect (consulted, mvp+) | Pending | |

## Version History

| Version | Date | Changed By | Summary of Changes | CHG-NNN |
|---|---|---|---|---|
| 1.0 | {date} | {author} | Initial draft | — |
