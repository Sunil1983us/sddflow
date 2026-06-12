# QA Test Cases
# Feature: Instant Core Service (ICS) — Full Scope

> Version: 1.0 | Date: {date}
> Input: srd.summary.md + api-spec.summary.md
> Audience: QA Engineers

---

## Test Environment Setup

```
ICS running on: http://localhost:8080
Mock profile: ACTIVE (all downstream mocked)
Mock mode control: http://localhost:8080/actuator/mock-config
DB: PostgreSQL via Docker Compose
Logs: docker-compose logs ics-app --follow
```

---

## Leg 1 — Happy Path

### TC-001: Full Happy Path — Payment SETTLED
**Priority:** P1 — Critical
**Pre-condition:** ICS running, mock profile active, all mocks in HAPPY_PATH mode
**ISO Messages:** pacs.008.001.08 (inbound), pacs.002.001.10 (inbound + outbound)

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST pacs.008 to `/instant-core-service/v1/instant-credit-transfer` with all mandatory headers | HTTP 202 — paymentId returned, status=RECEIVED |
| 2 | Check DB: `SELECT status FROM payments WHERE payment_id = '{id}'` | status = AWAITING_RECEIPT |
| 3 | POST pacs.002 ACCP to `/instant-core-service/v1/payment-status-report` | HTTP 200 — acknowledgementId returned |
| 4 | Check DB final status | status = SETTLED |
| 5 | Check payment_status_history | 7 rows — one per status transition |
| 6 | Check logs | PAYMENT_RECEIVED, 6x STATUS_TRANSITION, PAYMENT_SETTLED all present |

---

## Leg 1 — Unhappy Paths

### TC-002: BVS Validation Failure — Payment REJECTED
**Priority:** P1
**Setup:** Set BVS mock to REJECT mode with reasonCode=FF01
**ISO Messages:** pacs.002.001.10 (outbound — constructed by ICS)

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST pacs.008 with all headers | HTTP 202 — paymentId returned |
| 2 | Check DB status | status = REJECTED |
| 3 | Verify no EVT_001 called | PBS mock call count = 0 |
| 4 | Verify pacs.002 RJCT sent to Gateway callback | Gateway mock received pacs.002 with reason FF01 |
| 5 | Check logs | PAYMENT_REJECTED with FF01 |

---

### TC-003: FRAML Hit — Payment REJECTED
**Priority:** P1
**Setup:** BVS mock = HAPPY_PATH, FRAML mock = REJECT (result=HIT)

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST pacs.008 | HTTP 202 |
| 2 | Check DB status | status = REJECTED |
| 3 | Verify BVS was called, FRAML was called | Both in downstream request logs |
| 4 | Verify EVT_001 NOT called | PBS mock call count = 0 |
| 5 | Verify pacs.002 RJCT sent to Gateway | Gateway mock received pacs.002 |

---

### TC-004: FRAML Timeout — Payment REJECTED
**Priority:** P1
**Setup:** FRAML mock = TIMEOUT mode (delay > 1,000ms)

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST pacs.008 | HTTP 202 |
| 2 | Wait 1,100ms | — |
| 3 | Check DB status | status = REJECTED |
| 4 | Check logs | DOWNSTREAM_TIMEOUT for FRAML |
| 5 | Verify no EVT_001 | PBS mock = 0 calls |

---

### TC-005: Insufficient Funds (AM04) — Payment REJECTED
**Priority:** P1
**Setup:** BVS+FRAML = HAPPY_PATH, PBS mock = REJECT (reasonCode=AM04)

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST pacs.008 | HTTP 202 |
| 2 | Check DB status | status = REJECTED |
| 3 | Verify EVT_001 was attempted | PBS mock called once with EVT_001 |
| 4 | Verify EVT_003 NOT called | PBS mock EVT_003 count = 0 (EVT_001 failed) |
| 5 | Verify pacs.002 RJCT sent | Gateway mock received pacs.002 with AM04 |

---

### TC-006: CSM Submission Failure — EVT_003 Compensation
**Priority:** P1 — Critical (compensation test)
**Setup:** BVS+FRAML+PBS EVT_001 = HAPPY_PATH, CSM = REJECT

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST pacs.008 | HTTP 202 |
| 2 | Check DB status | status = REJECTED |
| 3 | Verify EVT_001 was called | PBS mock EVT_001 count = 1 |
| 4 | **Verify EVT_003 WAS called** | PBS mock EVT_003 count = 1 ← critical |
| 5 | Verify pacs.002 RJCT sent | Gateway mock received pacs.002 |

---

## Leg 2 — Unhappy Paths

### TC-007: pacs.002 RJCT — EVT_003 + REJECTED
**Priority:** P1
**Setup:** Full Leg 1 happy path completes (AWAITING_RECEIPT), then send RJCT

| Step | Action | Expected Result |
|---|---|---|
| 1 | Complete Leg 1 — confirm AWAITING_RECEIPT | — |
| 2 | POST pacs.002 RJCT to payment-status-report | HTTP 200 |
| 3 | Check DB status | status = REJECTED |
| 4 | Verify EVT_003 called | PBS mock EVT_003 = 1 |
| 5 | Verify RT1 pacs.002 forwarded to Gateway | Gateway mock received original pacs.002 (not reconstructed) |

---

### TC-008: RECEIPT_TIMEOUT — EVT_003 + Investigation Case
**Priority:** P1 — Critical
**Setup:** Full Leg 1 completes, no pacs.002 sent within 8,001ms

| Step | Action | Expected Result |
|---|---|---|
| 1 | Complete Leg 1 — confirm AWAITING_RECEIPT | — |
| 2 | Wait 8,100ms — do NOT send pacs.002 | — |
| 3 | Check DB status | status = RECEIPT_TIMEOUT |
| 4 | Verify EVT_003 called | PBS mock EVT_003 = 1 |
| 5 | Check investigation_cases table | 1 row with trigger=RECEIPT_TIMEOUT |
| 6 | Check logs | PAYMENT_TIMEOUT + INVESTIGATION_CREATED |

---

### TC-009: Reconciliation Mismatch — Ring-Fence RETAINED
**Priority:** P1 — Critical (compensation constraint test)
**Setup:** Full Leg 1 completes, send pacs.002 with wrong OrgnlTxId

| Step | Action | Expected Result |
|---|---|---|
| 1 | Complete Leg 1 — confirm AWAITING_RECEIPT | — |
| 2 | POST pacs.002 with mismatched OrgnlTxId | HTTP 200 |
| 3 | Check DB status | status = RECONCILIATION_MISMATCH |
| 4 | **Verify EVT_002 NOT called** | PBS mock EVT_002 = 0 ← critical |
| 5 | **Verify EVT_003 NOT called** | PBS mock EVT_003 = 0 ← critical |
| 6 | Check investigation_cases table | 1 row with mismatch detail JSON |
| 7 | Check logs | RECONCILIATION_MISMATCH (ERROR level) |

---

## Duplicate Check

### TC-010: Duplicate Payment Rejected — AM05
**Priority:** P1
**Setup:** Send same pacs.008 twice

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST pacs.008 (first) | HTTP 202 — paymentId returned |
| 2 | POST exact same pacs.008 again | HTTP 202 — different paymentId OR cached |
| 3 | Check second payment DB status | status = REJECTED (AM05) |
| 4 | Check logs | DUPLICATE_REJECTED with AM05 |

---

## API Validation

### TC-011: Missing Mandatory Header — HTTP 400
**Priority:** P2

| Header Omitted | Expected errorCode |
|---|---|
| X-Correlation-Id | ICS-400 |
| X-Source-System | ICS-400 |
| X-Payment-Direction | ICS-400 |
| X-Message-Type | ICS-400 |
| X-Scheme | ICS-400 |

---

### TC-012: Invalid XML Body — HTTP 400
**Priority:** P2

| Input | Expected |
|---|---|
| Plain text body | HTTP 400, ICS-401 |
| Empty body | HTTP 400 |
| Valid XML but wrong schema | HTTP 400, ICS-401 |
| JSON body (wrong content type) | HTTP 400 |

---

## Resilience

### TC-013: Circuit Breaker Opens After Threshold
**Priority:** P2
**Setup:** Set BVS mock to REJECT — trigger failure threshold

| Step | Action | Expected Result |
|---|---|---|
| 1 | Send N payments (N = CB failure threshold) | All REJECTED |
| 2 | Send N+1 payment | REJECTED immediately — no BVS call |
| 3 | Check logs | CIRCUIT_BREAKER_OPEN for BVS |

---

### TC-014: Retry Exhausted — Failure Path Applied
**Priority:** P2
**Setup:** Set FRAML mock to TIMEOUT for all calls

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST pacs.008 | HTTP 202 |
| 2 | Wait for retries to exhaust | — |
| 3 | Check logs | DOWNSTREAM_RETRY × max-attempts for FRAML |
| 4 | Check DB status | status = REJECTED |

---

## Security

### TC-015: Expired Timestamp — Request Rejected
**Priority:** P2
**Setup:** Send request with X-Timestamp > 30 seconds old

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST with X-Timestamp = 31 seconds ago | HTTP 400 or 401 |
| 2 | Check logs | Timestamp validation failure |

---

## Test Summary

| ID | Scenario | Priority | Type |
|---|---|---|---|
| TC-001 | Full happy path SETTLED | P1 | E2E |
| TC-002 | BVS INVALID → REJECTED | P1 | Unhappy |
| TC-003 | FRAML HIT → REJECTED | P1 | Unhappy |
| TC-004 | FRAML TIMEOUT → REJECTED | P1 | Unhappy |
| TC-005 | AM04 insufficient funds | P1 | Unhappy |
| TC-006 | CSM failure + EVT_003 compensation | P1 | Compensation |
| TC-007 | pacs.002 RJCT + EVT_003 | P1 | Unhappy |
| TC-008 | RECEIPT_TIMEOUT + investigation | P1 | Timeout |
| TC-009 | Reconciliation mismatch — ring-fence retained | P1 | Critical |
| TC-010 | Duplicate AM05 | P1 | Duplicate |
| TC-011 | Missing headers → 400 | P2 | API |
| TC-012 | Invalid XML → 400 | P2 | API |
| TC-013 | Circuit breaker opens | P2 | Resilience |
| TC-014 | Retry exhausted | P2 | Resilience |
| TC-015 | Expired timestamp | P2 | Security |

---
*Generated from: srd.summary.md + api-spec.summary.md*
*Postman collection: docs/qa/postman-collection.json*
