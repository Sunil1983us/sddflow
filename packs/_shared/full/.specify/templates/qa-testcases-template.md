# QA Test Cases
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}

---

## References
| Source | Sections / IDs Used |
|---|---|
| use-cases.summary.md | {sections/IDs referenced} |
| srd.summary.md | {sections/IDs referenced} |

## 1. Test Coverage Summary

| Category | Cases | Type | Automated | Manual | UAT Relevant |
|---|---|---|---|---|---|
| Happy Path | {N} | E2E | ✅ | — | Yes |
| Validation | {N} | Integration | ✅ | — | No |
| Auth | {N} | Integration | ✅ | — | No |
| Unhappy Path | {N} | E2E | ✅ | — | Yes |
| Performance | {N} | Performance | — | ✅ | No |
| Boundary / Exploratory | {N} | Unit/Integration | — | ✅ | No |

> **UAT filter:** For UAT sign-off, run only TC-NNN rows where `UAT Relevant: Yes`. All other types are developer/CI gates only.

---

## 2. Happy Path

### TC-001: {Feature} — Success
**Type:** E2E | **UAT Relevant:** Yes
**Endpoint:** POST /api/v1/{resource}
**Given:** Valid request with all mandatory fields
**When:** Request submitted with valid auth
**Then:**
- Response status: 202
- Response body contains {resourceId}
- DB: record saved with correct initial status
- Log: request received event logged

---

## 3. Validation Tests

### TC-002: Missing Mandatory Field
**Type:** Integration | **UAT Relevant:** No
**Given:** Request missing {mandatory_field}
**When:** Request submitted
**Then:**
- Response status: 400
- errorCode: VALIDATION_ERROR
- message mentions {field}

### TC-003: Invalid Field Format
**Type:** Integration | **UAT Relevant:** No
**Given:** {field} in wrong format
**When:** Request submitted
**Then:** Response status 400, errorCode VALIDATION_ERROR

### TC-004: Duplicate Request (Idempotency)
**Type:** Integration | **UAT Relevant:** No
**Given:** Same Idempotency-Key used twice
**When:** Second request submitted
**Then:** Response status 409, errorCode DUPLICATE_REQUEST

---

## 4. Auth Tests

### TC-005: Missing Auth Header
**Type:** Integration | **UAT Relevant:** No
**Given:** Request with no auth
**Then:** Response status 401

### TC-006: Invalid Auth
**Type:** Integration | **UAT Relevant:** No
**Given:** Request with invalid token/key
**Then:** Response status 401

---

## 5. Unhappy Path Tests

### TC-007: {Integration} Failure
**Type:** E2E | **UAT Relevant:** Yes
**Given:** {Integration} returns error/timeout
**Then:**
- Correct failure status in DB
- Correct error response
- Compensation triggered (if applicable)

### TC-008: {Integration} Timeout
**Type:** E2E | **UAT Relevant:** Yes
**Given:** {Integration} times out
**Then:**
- Timeout status in DB
- Log: timeout event recorded

---

## 6. Performance Tests

### TC-009: Response Time
**Type:** Performance | **UAT Relevant:** No
**Given:** {N} concurrent requests
**When:** Sustained for 60 seconds
**Then:**
- P99 ≤ {target from NFR}
- Error rate < 1%

### TC-010: Throughput
**Type:** Performance | **UAT Relevant:** No
**Given:** {N} TPS load
**Then:** All requests processed within SLA

---

## 7. Boundary & Exploratory Tests

> Generated from boundary value analysis on FR-NNN inputs and exploratory
> charters for high-complexity/high-risk areas.

### TC-{N}: {Field} — Boundary Value
**FR Trace:** FR-{NNN}
**Given:** {field} at its minimum valid boundary value
**When:** Request submitted
**Then:** Accepted — boundary is inclusive

### TC-{N+1}: {Field} — Off-By-One (below minimum)
**Given:** {field} set to one below minimum valid value
**When:** Request submitted
**Then:** Rejected — 400 VALIDATION_ERROR

### TC-{N+2}: {Field} — Maximum Boundary
**Given:** {field} at its maximum valid boundary value
**When:** Request submitted
**Then:** Accepted — boundary is inclusive

### TC-{N+3}: {Field} — Null / Empty Input
**Given:** Optional {field} set to null or empty string
**When:** Request submitted
**Then:** {Accepted with default / Rejected — as per FR-NNN}

---

### Exploratory Charter EC-001: {High-Risk Area}
**Charter:** Explore {feature area} to discover defects around {scenario}
**Session length:** 60 min
**Target:** FR-{NNN} / R-{NNN} (from analyze.md)
**Areas to probe:** {state transitions}, {concurrent modifications}, {large payloads}
**Debrief:** Document findings as TC-NNN entries if reproducible

---

## 8. Postman Collection Structure

```
{Feature Name} Tests/
  ├── Setup — Create test data
  ├── Happy Path — TC-001
  ├── Validation — TC-002 to TC-004
  ├── Auth — TC-005 to TC-006
  ├── Unhappy Path — TC-007 to TC-008
  └── Cleanup — Remove test data
```

---

## Approvals
| Role | Status | Date |
|---|---|---|
| QA Lead (accountable — test case completeness) | Pending | |
| Tech Lead (consulted — coverage against FR-NNN) | Pending | |
