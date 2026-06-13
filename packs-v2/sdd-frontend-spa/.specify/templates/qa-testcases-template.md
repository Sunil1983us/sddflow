# QA Test Cases
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Input: api-spec.summary.md + srd.summary.md

---

## 1. Test Coverage Summary

| Category | Cases | Automated | Manual |
|---|---|---|---|
| Happy Path | {N} | ✅ | — |
| Validation | {N} | ✅ | — |
| Auth | {N} | ✅ | — |
| Unhappy Path | {N} | ✅ | — |
| Performance | {N} | — | ✅ |

---

## 2. Happy Path

### TC-001: {Feature} — Success
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
**Given:** Request missing {mandatory_field}
**When:** Request submitted
**Then:**
- Response status: 400
- errorCode: VALIDATION_ERROR
- message mentions {field}

### TC-003: Invalid Field Format
**Given:** {field} in wrong format
**When:** Request submitted
**Then:** Response status 400, errorCode VALIDATION_ERROR

### TC-004: Duplicate Request (Idempotency)
**Given:** Same Idempotency-Key used twice
**When:** Second request submitted
**Then:** Response status 409, errorCode DUPLICATE_REQUEST

---

## 4. Auth Tests

### TC-005: Missing Auth Header
**Given:** Request with no auth
**Then:** Response status 401

### TC-006: Invalid Auth
**Given:** Request with invalid token/key
**Then:** Response status 401

---

## 5. Unhappy Path Tests

### TC-007: {Integration} Failure
**Given:** {Integration} returns error/timeout
**Then:**
- Correct failure status in DB
- Correct error response
- Compensation triggered (if applicable)

### TC-008: {Integration} Timeout
**Given:** {Integration} times out
**Then:**
- Timeout status in DB
- Log: timeout event recorded

---

## 6. Performance Tests

### TC-009: Response Time
**Given:** {N} concurrent requests
**When:** Sustained for 60 seconds
**Then:**
- P99 ≤ {target from NFR}
- Error rate < 1%

### TC-010: Throughput
**Given:** {N} TPS load
**Then:** All requests processed within SLA

---

## 7. Postman Collection Structure

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
*Generated from: api-spec.summary.md + srd.summary.md*
