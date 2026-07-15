# QA Test Cases
# Feature: {Feature Name}
> Version: 1.0 | Status: Draft | Date: {date} | Author: {author}

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

> **Non-HTTP projects** (project_type: cli, data-ml, library, batch/pipeline):
> replace the `Endpoint:` field with the trigger that fits the project —
> `Command:` (CLI invocation + args), `Input:` (dataset/file/fixture), or
> `Call:` (public API function) — and phrase **Then** in terms of exit codes,
> stdout/stderr, output artifacts, or return values instead of HTTP status.
> The example in each section shows the HTTP form; a CLI-form example is
> included in §2 below.

---

## 2. Happy Path

### TC-{NNN}: {Feature} — Success
**Type:** E2E | **UAT Relevant:** Yes
**Endpoint:** POST /api/v1/{resource}
**Given:** Valid request with all mandatory fields
**When:** Request submitted with valid auth
**Then:**
- Response status: 202
- Response body contains {resourceId}
- DB: record saved with correct initial status
- Log: request received event logged

### TC-{NNN}: {Feature} — Success (non-HTTP form, e.g. CLI)
**Type:** E2E | **UAT Relevant:** Yes
**Command:** {tool} {subcommand} --input {fixture}
**Given:** Valid input file with all mandatory fields
**When:** Command runs with default options
**Then:**
- Exit code: 0
- stdout contains {expected summary line}
- Output artifact written to {path} with expected structure
- No stderr output

---

## 3. Validation Tests

### TC-{NNN}: Missing Mandatory Field
**Type:** Integration | **UAT Relevant:** No
**Given:** Request missing {mandatory_field}
**When:** Request submitted
**Then:**
- Response status: 400
- errorCode: VALIDATION_ERROR
- message mentions {field}

### TC-{NNN}: Invalid Field Format
**Type:** Integration | **UAT Relevant:** No
**Given:** {field} in wrong format
**When:** Request submitted
**Then:** Response status 400, errorCode VALIDATION_ERROR

### TC-{NNN}: Duplicate Request (Idempotency)
**Type:** Integration | **UAT Relevant:** No
**Given:** Same Idempotency-Key used twice
**When:** Second request submitted
**Then:** Response status 409, errorCode DUPLICATE_REQUEST

---

## 4. Auth Tests

### TC-{NNN}: Missing Auth Header
**Type:** Integration | **UAT Relevant:** No
**Given:** Request with no auth
**Then:** Response status 401

### TC-{NNN}: Invalid Auth
**Type:** Integration | **UAT Relevant:** No
**Given:** Request with invalid token/key
**Then:** Response status 401

---

## 5. Unhappy Path Tests

### TC-{NNN}: {Integration} Failure
**Type:** E2E | **UAT Relevant:** Yes
**Given:** {Integration} returns error/timeout
**Then:**
- Correct failure status in DB
- Correct error response
- Compensation triggered (if applicable)

### TC-{NNN}: {Integration} Timeout
**Type:** E2E | **UAT Relevant:** Yes
**Given:** {Integration} times out
**Then:**
- Timeout status in DB
- Log: timeout event recorded

---

## 6. Performance Tests

### TC-{NNN}: Response Time
**Type:** Performance | **UAT Relevant:** No
**Given:** {N} concurrent requests
**When:** Sustained for 60 seconds
**Then:**
- P99 ≤ {target from NFR}
- Error rate < 1%

### TC-{NNN}: Throughput
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

### Exploratory Charter EC-{NNN}: {High-Risk Area}
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
  ├── Happy Path — TC-{NNN}
  ├── Validation — TC-{NNN} to TC-{NNN}
  ├── Auth — TC-{NNN} to TC-{NNN}
  ├── Unhappy Path — TC-{NNN} to TC-{NNN}
  └── Cleanup — Remove test data
```

---

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| QA Lead (accountable — test case completeness) | | Pending | |
| Tech Lead (consulted — coverage against FR-NNN) | | Pending | |

## Version History

| Version | Date | Changed By | Summary of Changes | CHG-NNN |
|---|---|---|---|---|
| 1.0 | {date} | {author} | Initial draft | — |
