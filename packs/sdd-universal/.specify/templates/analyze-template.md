# Analysis Report
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced} |
| brd.summary.md | {sections/IDs referenced} |

## 1. Executive Summary
{2-3 sentences: overall complexity, biggest risks, key recommendation.}
Overall Complexity: LOW | MEDIUM | HIGH

---

## 2. Risk Register

| ID | Risk | Likelihood | Impact | Linked FR/NFR (AR-3) | Mitigation |
|---|---|---|---|---|---|
| R-001 | {risk} | Low/Med/High | Low/Med/High/Critical | FR-{NNN} / NFR-{NNN} | {action} |

Every risk must link to at least one FR-NNN or NFR-NNN it threatens — if
none applies, link to the relevant Domain Rule from constitution Part 2.
Carried into feature-story-template.md Traceability Matrix (R-NNN column).

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
| U-001 | {what we don't know} | {consequence} | Yes/No |

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
| CF-001 | {Duplication\|Ambiguity\|CoverageGap\|TerminologyDrift\|ConstitutionConflict} | CRITICAL\|HIGH\|MEDIUM\|LOW | {doc + section} | {what was found} | {what to do} |

### Severity Guide
- **CRITICAL** — block /clarify: constitution conflict (FR/NFR violates a MUST rule); FR/NFR with zero UC coverage
- **HIGH** — resolve in /clarify: duplicate or conflicting requirements; ambiguous security/performance attribute without threshold
- **MEDIUM** — address before /plan-arch: terminology drift; missing non-functional task coverage; underspecified edge case
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
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
