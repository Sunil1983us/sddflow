# Jira Export
# Feature: Instant Core Service — {Scope}

> Version: 1.0 | Date: {date}
> Input: srd.summary.md + tasks.md
> Format: Jira CSV import + human-readable stories

---

## 1. Epic

| Field | Value |
|---|---|
| Issue Type | Epic |
| Epic Name | Instant Core Service — {Scope} |
| Summary | ICS — Real-time SEPA Instant Credit Transfer Engine |
| Priority | High |
| Labels | payments, iso20022, sct-inst, ics |

---

## 2. Stories

### STORY-001: Receive and Acknowledge Outbound Credit Transfer
**Epic:** ICS
**Priority:** Must Have
**Description:**
As the Instant Gateway Service, I need to submit a pacs.008 to ICS
and receive a payment_id immediately, so that I can track the payment end-to-end.

**Acceptance Criteria:**
- [ ] POST /instant-core-service/v1/instant-credit-transfer accepts pacs.008 XML
- [ ] ICS generates UUID v4 payment_id and returns HTTP 202 within 200ms
- [ ] Payment record saved to DB with status RECEIVED
- [ ] All mandatory headers validated — HTTP 400 if missing

**Tasks:** TASK-001, TASK-002, TASK-003, TASK-004, TASK-013

---

### STORY-002: Orchestrate Downstream Validation and Screening
**Epic:** ICS
**Priority:** Must Have
**Description:**
As ICS, I need to call BVS and FRAML in sequence to validate and screen
the payment before committing funds.

**Acceptance Criteria:**
- [ ] BVS called after RECEIVED — status → VALIDATION
- [ ] FRAML called after VALIDATION — status → FRAML_CHECK
- [ ] Status persisted to DB before each call
- [ ] Unhappy: BVS INVALID → REJECTED + pacs.002 to Gateway
- [ ] Unhappy: FRAML HIT/ERROR/TIMEOUT → REJECTED + pacs.002 to Gateway

**Tasks:** TASK-005, TASK-006, TASK-008, TASK-011

---

### STORY-003: Reserve Funds and Submit to Clearing
**Epic:** ICS
**Priority:** Must Have
**Description:**
As ICS, I need to ring-fence debtor funds via PBS EVT_001 and submit
the pacs.008 to CSM for RT1 clearing.

**Acceptance Criteria:**
- [ ] PBS EVT_001 called — status → FUNDS_RESERVED
- [ ] Insufficient funds (AM04) → REJECTED + EVT_003 NOT called
- [ ] CSM called — clearing_ref stored — status → AWAITING_RECEIPT
- [ ] CSM failure → REJECTED + EVT_003 called (EVT_001 already succeeded)

**Tasks:** TASK-011, TASK-008

---

### STORY-004: Process CSM Settlement Response
**Epic:** ICS
**Priority:** Must Have
**Description:**
As ICS, I need to receive pacs.002 from CSM, reconcile fields, settle
or reject, and notify the Gateway.

**Acceptance Criteria:**
- [ ] POST /instant-core-service/v1/payment-status-report accepts pacs.002
- [ ] 3-field reconciliation — RECONCILIATION_MISMATCH on any mismatch
- [ ] ACCP → PBS EVT_002 → SETTLED → pacs.002 to Gateway
- [ ] RJCT → PBS EVT_003 → REJECTED → RT1 pacs.002 forwarded to Gateway

**Tasks:** TASK-012, TASK-013

---

### STORY-005: Handle Receipt Timeout
**Epic:** ICS
**Priority:** Must Have
**Description:**
As ICS, I need to detect when no pacs.002 is received within 8,001ms
and apply the correct compensation and terminal status.

**Acceptance Criteria:**
- [ ] Timer starts when CSM submission succeeds
- [ ] No pacs.002 within 8,001ms → RECEIPT_TIMEOUT
- [ ] PBS EVT_003 triggered
- [ ] Investigation case created

**Tasks:** {TASK-NNN}

---

### STORY-006: Duplicate Payment Detection
**Epic:** ICS
**Priority:** Must Have
**Description:**
As ICS, I need to detect duplicate pacs.008 submissions using 6 fields
and reject with ISO code AM05.

**Acceptance Criteria:**
- [ ] 6-field check: TransactionId, AcceptanceDateTime, MsgId, DebtorBIC, CreditorBIC, CreDtTm
- [ ] Duplicate found → REJECTED (AM05) → pacs.002 to Gateway
- [ ] Lookback window configurable — no hardcoding

**Tasks:** {TASK-NNN}

---

### STORY-007: Resilience — Retry and Circuit Breaker
**Epic:** ICS
**Priority:** Must Have
**Description:**
As ICS, I need configurable retry and circuit breaker per downstream
service so the system handles transient failures gracefully.

**Acceptance Criteria:**
- [ ] Retry per service — new X-Request-Id per attempt
- [ ] Circuit breaker per service — CLOSED/OPEN/HALF-OPEN
- [ ] All thresholds configurable — no hardcoding
- [ ] CIRCUIT_BREAKER_OPEN logged on state change

**Tasks:** {TASK-NNN}

---

### STORY-008: Investigation Case Management
**Epic:** ICS
**Priority:** Must Have
**Description:**
As ICS, I need to create investigation case records on
RECONCILIATION_MISMATCH and RECEIPT_TIMEOUT for Operations resolution.

**Acceptance Criteria:**
- [ ] Investigation record written on both triggers
- [ ] trigger_detail JSON contains all relevant fields
- [ ] Ring-fence RETAINED on RECONCILIATION_MISMATCH
- [ ] INVESTIGATION_CREATED logged (WARN)

**Tasks:** {TASK-NNN}

---

### STORY-009: Security — mTLS and HMAC Signing
**Epic:** ICS
**Priority:** Must Have
**Description:**
As ICS, I need mutual TLS and HMAC-SHA256 request signing on all
service-to-service calls for production security.

**Acceptance Criteria:**
- [ ] mTLS configured on all outbound calls (@Profile("prod"))
- [ ] X-Signature header validated on all inbound calls
- [ ] X-Timestamp validated — reject if > 30 seconds old
- [ ] Certificate rotation without service restart

**Tasks:** {TASK-NNN}

---

### STORY-010: SLA Monitoring and Alerts
**Epic:** ICS
**Priority:** Should Have
**Description:**
As Operations, I need ICS to track and alert on SLA breaches so I can
monitor payment processing health.

**Acceptance Criteria:**
- [ ] Leg 1 elapsed time tracked
- [ ] SLA_BREACH logged (WARN) at configured threshold
- [ ] Payment NOT aborted on 7,000ms breach — alert only
- [ ] RECEIPT_TIMEOUT at 8,001ms — payment aborted

**Tasks:** {TASK-NNN}

---

### STORY-011: Runtime Configuration
**Epic:** ICS
**Priority:** Must Have
**Description:**
As Operations, I need all timeouts, retry counts, and feature flags
to be configurable without application redeployment.

**Acceptance Criteria:**
- [ ] Spring Cloud Config integrated
- [ ] Config changes effective within 30 seconds
- [ ] All timeout + retry + CB thresholds configurable
- [ ] FRAML feature flag per scheme

**Tasks:** {TASK-NNN}

---

### STORY-012: Observability — Structured Logging
**Epic:** ICS
**Priority:** Must Have
**Description:**
As Operations, I need all 15 mandatory log events emitted as
structured JSON with payment_id and correlation_id on every line.

**Acceptance Criteria:**
- [ ] All 15 log events present
- [ ] payment_id + correlation_id on every log line
- [ ] Structured JSON format
- [ ] No PII in any log

**Tasks:** {TASK-NNN}

---

## 3. Jira CSV Import

```csv
Issue Type,Summary,Description,Priority,Epic Link,Labels,Acceptance Criteria
Epic,ICS — Instant Core Service,Real-time SEPA SCT Inst engine,High,,payments iso20022,
Story,Receive and Acknowledge Credit Transfer,pacs.008 receipt + payment_id generation,High,ICS,ics leg1,HTTP 202 returned with paymentId
Story,Orchestrate Validation and Screening,BVS + FRAML orchestration,High,ICS,ics validation,BVS VALID + FRAML NO_HIT on happy path
Story,Reserve Funds and Submit to Clearing,PBS EVT_001 + CSM submission,High,ICS,ics clearing,FUNDS_RESERVED + AWAITING_RECEIPT on happy path
Story,Process CSM Settlement Response,pacs.002 reconcile + settle,High,ICS,ics settlement,SETTLED on ACCP + REJECTED on RJCT
Story,Handle Receipt Timeout,8001ms RECEIPT_TIMEOUT,High,ICS,ics resilience,EVT_003 + investigation case created
Story,Duplicate Payment Detection,6-field AM05 check,High,ICS,ics duplicate,REJECTED with AM05 on duplicate
Story,Resilience — Retry and Circuit Breaker,Per-service retry + CB,High,ICS,ics resilience,All thresholds configurable
Story,Investigation Case Management,MISMATCH + TIMEOUT cases,High,ICS,ics investigation,Record written with trigger_detail JSON
Story,Security — mTLS and HMAC,Request signing + validation,High,ICS,ics security,X-Timestamp rejected if >30s old
Story,SLA Monitoring and Alerts,Leg 1 + Leg 2 SLA tracking,Medium,ICS,ics observability,SLA_BREACH logged at threshold
Story,Runtime Configuration,Spring Cloud Config,High,ICS,ics config,Config live within 30 seconds
Story,Observability — Structured Logging,15 mandatory log events,High,ICS,ics observability,payment_id + correlation_id on every line
```

---
*Generated from: srd.summary.md + tasks.md*
*Import via: Jira → Projects → Import → CSV*
