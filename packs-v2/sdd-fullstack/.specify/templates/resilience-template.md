# Resilience Design
# Feature: {Feature Name}

> Version: 1.0 | Date: {date}
> Input: arch.summary.md

---

## 1. Overview
{Retry + circuit breaker strategy per downstream service.}

## 2. Retry Configuration Per Service

| Service | Max Attempts | Delay (ms) | Backoff Multiplier |
|---|---|---|---|
| BVS | {n} | {ms} | {x} |
| FRAML | {n} | {ms} | {x} |
| PBS EVT_001 | {n} | {ms} | {x} |
| PBS EVT_002 | {n} | {ms} | {x} |
| PBS EVT_003 | {n} | {ms} | {x} |
| CSM | {n} | {ms} | {x} |
| Gateway Callback | {n} | {ms} | {x} |

**Rules:**
- New X-Request-Id on every retry attempt
- payment_id + correlation_id unchanged across retries
- On exhaustion: apply failure path for that service

## 3. Circuit Breaker Per Service

| Service | Failure Threshold | Open Duration (ms) | Half-Open Probes |
|---|---|---|---|
| BVS | {n} | {ms} | {n} |
| FRAML | {n} | {ms} | {n} |
| PBS | {n} | {ms} | {n} |
| CSM | {n} | {ms} | {n} |
| Gateway | {n} | {ms} | {n} |

**State Transitions:**
```
CLOSED → OPEN (on failure threshold breach)
OPEN → HALF-OPEN (after open duration)
HALF-OPEN → CLOSED (on probe success)
HALF-OPEN → OPEN (on probe failure)
```

**When OPEN:** Apply failure path immediately — no downstream call.
Log: CIRCUIT_BREAKER_OPEN event (WARN)

## 4. Timeout Per Service

| Service | Timeout (ms) | On Timeout |
|---|---|---|
| BVS | 500 | Reject — VALIDATION_FAILED |
| FRAML | 1,000 | Reject — treat as ERROR |
| PBS EVT_001 | 200 | Reject — no compensation needed |
| PBS EVT_002 | 200 | Reject — investigation case |
| PBS EVT_003 | 200 | Log + alert — ring-fence may be retained |
| CSM | 6,000 | Reject — RECEIPT_SUBMITTED stays |
| Gateway Callback | 3,000 | Retry per policy — then investigation |

## 5. Failure Path Per Service

| Service | Failure | Compensation | Terminal Status |
|---|---|---|---|
| BVS | INVALID / timeout | None | REJECTED |
| FRAML | HIT / ERROR / timeout | None | REJECTED |
| PBS EVT_001 | FAILED / timeout | None | REJECTED |
| CSM | FAILED / timeout | EVT_003 (if EVT_001 OK) | REJECTED |
| Leg 2 — PBS EVT_002 | FAILED | Investigation | INVESTIGATION |
| Gateway Callback | All retries fail | Investigation | SETTLED (payment still settled) |

## 6. Runtime Config Keys

```yaml
app:
  resilience:
    bvs:
      timeout-ms: 500
      retry-max: 3
      retry-delay-ms: 100
      cb-failure-threshold: 5
      cb-open-duration-ms: 30000
    framl:
      timeout-ms: 1000
      retry-max: 2
      cb-failure-threshold: 3
    # ... per service
```

---
*Generated from: arch.summary.md*
