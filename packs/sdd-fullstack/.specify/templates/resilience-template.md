# Resilience Design
# Feature: {Feature Name}
> Version: 1.0 | Date: {date}
> Scope: MVP+ only — skip for pilot

---

## References
| Source | Sections / IDs Used |
|---|---|
| arch.summary.md | {sections/IDs referenced} |
| srd.summary.md | {sections/IDs referenced} |

## 1. Resilience Strategy

| Integration | Retry | Circuit Breaker | Timeout | Fallback |
|---|---|---|---|---|
| {Integration A} | 3 attempts | Yes | 1,000ms | {fallback action} |
| {Integration B} | 2 attempts | Yes | 2,000ms | {fallback action} |
| {Database} | 3 attempts | No | 5,000ms | Fail fast |

---

## 2. Retry Configuration

### {Integration A}
```yaml
resilience4j:
  retry:
    instances:
      {integrationA}:
        max-attempts: 3
        wait-duration: 500ms
        exponential-backoff-multiplier: 2
        retry-exceptions:
          - java.io.IOException
          - java.util.concurrent.TimeoutException
        ignore-exceptions:
          - {BusinessException}
```

### Rule: New Request ID per Retry
- Correlation ID unchanged across retries
- New {requestId} on every retry attempt
- Log each retry attempt with attempt number

---

## 3. Circuit Breaker Configuration

```yaml
resilience4j:
  circuitbreaker:
    instances:
      {integrationA}:
        failure-rate-threshold: 50
        slow-call-rate-threshold: 80
        slow-call-duration-threshold: 2s
        permitted-number-of-calls-in-half-open-state: 3
        sliding-window-size: 10
        wait-duration-in-open-state: 30s
```

**States:** CLOSED → OPEN → HALF-OPEN
**When OPEN:** Apply failure path immediately — do not wait

---

## 4. Timeout Configuration

```yaml
resilience4j:
  timelimiter:
    instances:
      {integrationA}:
        timeout-duration: 1s
        cancel-running-future: true
```

---

## 5. Failure Paths

| Trigger | Action | Status |
|---|---|---|
| {IntegrationA} retry exhausted | {action} | {FAILURE_STATUS} |
| {IntegrationB} circuit open | {action} | {FAILURE_STATUS} |
| Timeout exceeded | {action} | {TIMEOUT_STATUS} |

---

## 6. Compensation

| Trigger | Compensation Action | Notes |
|---|---|---|
| Failure after {step N} | {undo action} | Only if {condition} |
| {condition} | Never compensate | {why} |

---

## 7. Observability
| Event | Log Level | Metric |
|---|---|---|
| Retry attempt | WARN | retry.attempt.count |
| Retry exhausted | ERROR | retry.exhausted.count |
| Circuit opened | ERROR | circuit.open.count |
| Timeout | ERROR | timeout.count |

---

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |
