# Task List
# Feature: {Feature Name}

> Version: 1.0 | Status: Not Started | Date: {date}
> Input: plan.summary.md

## How to Use
Give Claude Code one task at a time:
```
Read .specify/memory/constitution.md
Read .specify/features/instant-credit-transfer/tasks.md
Execute TASK-{NNN} — confirm acceptance criteria before marking done.
```

---

## Phase 1 — Project Foundation

### TASK-001 — Maven Project + Dependencies
**Satisfies:** NFR-001 (structure)
**Dependencies:** None
**Description:**
Create `pom.xml` with all required dependencies.
Create Spring Boot main class. Set `spring.profiles.active=mock`.
**Acceptance Criteria:**
- [ ] `mvn clean install` passes
- [ ] Spring Boot starts on port 8080
- [ ] Mock profile active by default
- [ ] No hardcoded values — all config in application.yml

---

### TASK-002 — application.yml Files
**Satisfies:** NFR-001
**Dependencies:** TASK-001
**Description:**
Create `application.yml`, `application-mock.yml`, `application-prod.yml`.
Include all downstream service URLs, timeout values, Redis config.
**Acceptance Criteria:**
- [ ] All downstream URLs configurable — no hardcoded values
- [ ] Mock profile overrides all downstream URLs to localhost mocks
- [ ] Redis connection configured
- [ ] Virtual threads enabled

---

### TASK-003 — Domain Entity + Enum
**Satisfies:** FR-{NNN}
**Dependencies:** TASK-001
**Description:**
Create `PaymentEntity.java` and `PaymentStatus.java` enum.
All fields per data-model.md. No Spring/JPA imports in domain.
**Acceptance Criteria:**
- [ ] All columns from data model present
- [ ] Amount is BigDecimal
- [ ] PaymentStatus enum has all 7 statuses
- [ ] No Spring or JPA annotations on domain class
- [ ] Unit test: entity construction

---

### TASK-004 — Flyway Migration Scripts
**Satisfies:** FR-{NNN} (persistence)
**Dependencies:** TASK-003
**Description:**
Create V001 and V002 migration scripts.
**Acceptance Criteria:**
- [ ] V001__create_payments_table.sql — all columns, 3 indexes
- [ ] V002__create_payment_status_history_table.sql — all columns, 1 index
- [ ] `mvn flyway:migrate` runs clean on fresh DB

---

### TASK-005 — Inbound Port Interfaces
**Satisfies:** FR-{NNN}
**Dependencies:** TASK-003
**Description:**
Create `ProcessCreditTransferUseCase` and `ProcessStatusReportUseCase` interfaces.
**Acceptance Criteria:**
- [ ] Both interfaces in `port/in/`
- [ ] Method signatures use DTO records — not entities
- [ ] Javadoc on every method

---

### TASK-006 — Outbound Port Interfaces
**Satisfies:** FR-{NNN}
**Dependencies:** TASK-003
**Description:**
Create all 6 outbound port interfaces.
**Acceptance Criteria:**
- [ ] BvsPort, FramlPort, PbsPort, CsmPort, GatewayCallbackPort, PaymentRepositoryPort
- [ ] All in `port/out/`
- [ ] Javadoc on every method

---

## Phase 2 — Mock Layer

### TASK-007 — Mock Data Factory
**Satisfies:** Test infrastructure
**Dependencies:** TASK-003
**Description:**
Create `MockDataFactory.java` with static methods for all test data.
**Acceptance Criteria:**
- [ ] Methods for: sample pacs.008 XML, pacs.002 XML, PaymentEntity
- [ ] All data realistic — valid IBANs, UUIDs, amounts
- [ ] No hardcoded UUIDs — generate fresh per call

---

### TASK-008 — Mock Adapters (All 5)
**Satisfies:** FR-{NNN} (mock integrations)
**Dependencies:** TASK-006, TASK-007
**Description:**
Create all 5 mock adapters — one class per downstream service.
All annotated `@Profile("mock")`. All return happy path only.
**Acceptance Criteria:**
- [ ] MockBvsAdapter — returns VALID
- [ ] MockFramlAdapter — returns NO_HIT
- [ ] MockPbsAdapter — returns RESERVED (EVT_001) / BOOKED (EVT_002)
- [ ] MockCsmAdapter — returns SUBMITTED + clearingRef
- [ ] MockGatewayCallbackAdapter — logs + returns RECEIVED
- [ ] All have Thread.sleep(50ms) latency simulation
- [ ] Unit test per mock adapter

---

## Phase 3 — Repository

### TASK-009 — JPA Repository + Adapter
**Satisfies:** FR-{NNN} (persistence)
**Dependencies:** TASK-004, TASK-006
**Description:**
Create Spring Data JPA repository and `JpaPaymentRepositoryAdapter`.
**Acceptance Criteria:**
- [ ] Implements PaymentRepositoryPort
- [ ] save, findById, updateStatus all working
- [ ] Testcontainers integration test: save → find → verify
- [ ] Status history written on every updateStatus call

---

## Phase 4 — Service Layer

### TASK-010 — DTOs (Request / Response Records)
**Satisfies:** FR-{NNN}
**Dependencies:** TASK-001
**Description:**
Create all request/response Java records.
`IcsHeaders` record for header propagation.
**Acceptance Criteria:**
- [ ] CreditTransferResponse record
- [ ] StatusReportResponse record
- [ ] IcsHeaders record with all 6 mandatory headers
- [ ] PbsRequest record with all booking fields

---

### TASK-011 — InstantCreditTransferService (Leg 1)
**Satisfies:** FR-{NNN} (steps 1–6)
**Dependencies:** TASK-005, TASK-006, TASK-008, TASK-010
**Description:**
Implement Leg 1 orchestration — steps 1 through 6.
Inject all ports via interfaces. Persist status before each step.
**Acceptance Criteria:**
- [ ] Implements ProcessCreditTransferUseCase
- [ ] Generates payment_id (UUID v4)
- [ ] Persists status before calling each downstream service
- [ ] Calls BVS → FRAML → PBS EVT_001 → CSM in order
- [ ] Stores clearing_ref from CSM response
- [ ] All log events present: PAYMENT_RECEIVED, STATUS_TRANSITION x5,
      DOWNSTREAM_REQUEST x4, DOWNSTREAM_RESPONSE x4
- [ ] payment_id + correlation_id on every log line
- [ ] Unit test: happy path — all mocks return success, status = AWAITING_RECEIPT

---

### TASK-012 — PaymentStatusReportService (Leg 2)
**Satisfies:** FR-{NNN} (steps 7–9)
**Dependencies:** TASK-011
**Description:**
Implement Leg 2 — receive pacs.002, reconcile, settle, callback.
**Acceptance Criteria:**
- [ ] Implements ProcessStatusReportUseCase
- [ ] Reconciles 3 fields: OrgnlTxId, AccptncDtTm, OrgnlMsgId
- [ ] Calls PBS EVT_002 → persists SETTLED
- [ ] Calls GatewayCallbackPort with pacs.002 ACCP
- [ ] Log events: STATUS_TRANSITION x2, DOWNSTREAM_REQUEST x2,
      DOWNSTREAM_RESPONSE x2, PAYMENT_SETTLED
- [ ] Unit test: happy path — status = SETTLED

---

## Phase 5 — API Layer

### TASK-013 — REST Controllers
**Satisfies:** FR-{NNN}
**Dependencies:** TASK-010, TASK-011, TASK-012
**Description:**
Create both REST controllers. Read headers into IcsHeaders record.
Delegate to inbound port interfaces only.
**Acceptance Criteria:**
- [ ] InstantCreditTransferController — POST endpoint returns 202
- [ ] PaymentStatusReportController — POST endpoint returns 200
- [ ] Both read all 6 mandatory headers
- [ ] Both validate Content-Type = application/xml
- [ ] No business logic in either controller

---

### TASK-014 — GlobalExceptionHandler
**Satisfies:** NFR-{NNN} (error handling)
**Dependencies:** TASK-001
**Description:**
Create `IcsException` base class and `GlobalExceptionHandler`.
**Acceptance Criteria:**
- [ ] IcsException has errorCode + message
- [ ] Handler returns structured error JSON
- [ ] No stack trace in response
- [ ] Missing header → ICS-400
- [ ] Invalid XML → ICS-401
- [ ] Unexpected error → ICS-500

---

### TASK-015 — Controller Integration Tests
**Satisfies:** Testing for TASK-013
**Dependencies:** TASK-013, TASK-014
**Description:**
Full end-to-end integration tests using @SpringBootTest + mock profile.
**Acceptance Criteria:**
- [ ] POST valid pacs.008 → 202 + paymentId in response
- [ ] POST valid pacs.002 → 200 + acknowledgementId in response
- [ ] POST missing header → 400 ICS-400
- [ ] POST invalid XML body → 400 ICS-401

---

## Phase 6 — Infrastructure

### TASK-016 — Docker Compose
**Satisfies:** NFR-{NNN} (deployment)
**Dependencies:** TASK-001
**Description:**
Create `docker-compose.yml` with app, postgres, redis.
Create `Dockerfile`. Create `.env.example`.
**Acceptance Criteria:**
- [ ] `docker-compose up` starts all 3 services
- [ ] App connects to PostgreSQL — Flyway runs on startup
- [ ] App connects to Redis
- [ ] No hardcoded credentials — all from .env
- [ ] Health check endpoint responds: GET /actuator/health

---

## Task Summary

| ID | Title | Phase | Status |
|---|---|---|---|
| TASK-001 | Maven Project + Dependencies | Foundation | [ ] |
| TASK-002 | application.yml Files | Foundation | [ ] |
| TASK-003 | Domain Entity + Enum | Foundation | [ ] |
| TASK-004 | Flyway Migration Scripts | Foundation | [ ] |
| TASK-005 | Inbound Port Interfaces | Foundation | [ ] |
| TASK-006 | Outbound Port Interfaces | Foundation | [ ] |
| TASK-007 | Mock Data Factory | Mock Layer | [ ] |
| TASK-008 | Mock Adapters (All 5) | Mock Layer | [ ] |
| TASK-009 | JPA Repository + Adapter | Repository | [ ] |
| TASK-010 | DTOs | Service Layer | [ ] |
| TASK-011 | InstantCreditTransferService | Service Layer | [ ] |
| TASK-012 | PaymentStatusReportService | Service Layer | [ ] |
| TASK-013 | REST Controllers | API Layer | [ ] |
| TASK-014 | GlobalExceptionHandler | API Layer | [ ] |
| TASK-015 | Controller Integration Tests | API Layer | [ ] |
| TASK-016 | Docker Compose | Infrastructure | [ ] |

---
*Generated from: plan.summary.md*

---

## PR Size Reference — All Tasks

| Task | Estimated Lines | PR Strategy |
|---|---|---|
| TASK-001 | ~80 | Single PR |
| TASK-002 | ~60 | Single PR |
| TASK-003 | ~90 | Single PR |
| TASK-004 | ~50 | Single PR |
| TASK-005 | ~40 | Single PR |
| TASK-006 | ~60 | Single PR |
| TASK-007 | ~80 | Single PR |
| TASK-008 | ~200 | Single PR (5 mocks) |
| TASK-009 | ~120 | Single PR |
| TASK-010 | ~80 | Single PR |
| TASK-011 | ~580 | **SPLIT: A+B+C** |
| TASK-012 | ~320 | Single PR |
| TASK-013 | ~150 | Single PR |
| TASK-014 | ~80 | Single PR |
| TASK-015 | ~200 | Single PR |
| TASK-016 | ~100 | Single PR |

**Rule:** Any task marked SPLIT must be confirmed before coding starts.
