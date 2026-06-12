# Implementation Plan
# Feature: {Feature Name}

> Version: 1.0 | Status: Draft | Date: {date}
> Input: api-spec.summary.md + arch.summary.md

---

## 1. Approach
{One paragraph — what will be built, in what order, key patterns used.}

## 2. Layer Plan

### 2.1 Domain Layer
```java
// domain/PaymentEntity.java
// Fields: paymentId, correlationId, status, pacs008Xml,
//         clearingRef, amount, currency, debtorBic, creditorBic,
//         transactionId, acceptanceDt, msgId, createdAt, updatedAt

// domain/PaymentStatus.java (enum)
// Values: RECEIVED, VALIDATION, FRAML_CHECK, FUNDS_RESERVED,
//         AWAITING_RECEIPT, RECONCILING, SETTLED

// domain/PaymentStatusHistory.java
// Fields: id, paymentId, fromStatus, toStatus, changedAt
```

### 2.2 Inbound Port
```java
// port/in/ProcessCreditTransferUseCase.java
//   CreditTransferResponse initiate(String pacs008Xml, IcsHeaders headers);

// port/in/ProcessStatusReportUseCase.java
//   StatusReportResponse receive(String pacs002Xml, IcsHeaders headers);
```

### 2.3 Outbound Ports
```java
// port/out/BvsPort.java         → validate(String pacs008Xml, IcsHeaders h)
// port/out/FramlPort.java       → screen(String pacs008Xml, IcsHeaders h)
// port/out/PbsPort.java         → book(PbsRequest request, IcsHeaders h)
// port/out/CsmPort.java         → submit(String pacs008Xml, IcsHeaders h)
// port/out/GatewayCallbackPort  → notify(String pacs002Xml, IcsHeaders h)
// port/out/PaymentRepositoryPort → save, findById, updateStatus
```

### 2.4 Service Layer
```java
// service/InstantCreditTransferService.java
// Implements: ProcessCreditTransferUseCase
// Orchestrates 9 steps:
//   1. Parse pacs.008, generate payment_id
//   2. Persist RECEIVED
//   3. Call BvsPort → persist VALIDATION
//   4. Call FramlPort → persist FRAML_CHECK
//   5. Call PbsPort (EVT_001) → persist FUNDS_RESERVED
//   6. Call CsmPort → store clearing_ref → persist AWAITING_RECEIPT
//   [Leg 2 handled by PaymentStatusReportService]

// service/PaymentStatusReportService.java
// Implements: ProcessStatusReportUseCase
//   7. Reconcile 3 fields → persist RECONCILING
//   8. Call PbsPort (EVT_002) → persist SETTLED
//   9. Call GatewayCallbackPort
```

### 2.5 Mock Adapters
```java
// mock/MockBvsAdapter.java         @Profile("mock") — returns VALID
// mock/MockFramlAdapter.java       @Profile("mock") — returns NO_HIT
// mock/MockPbsAdapter.java         @Profile("mock") — returns RESERVED / BOOKED
// mock/MockCsmAdapter.java         @Profile("mock") — returns SUBMITTED + clearingRef
// mock/MockGatewayCallbackAdapter  @Profile("mock") — logs and returns RECEIVED
// mock/MockDataFactory.java        — reusable test data
```

### 2.6 Controller Layer
```java
// controller/InstantCreditTransferController.java
//   POST /instant-core-service/v1/instant-credit-transfer
//   → reads headers → calls ProcessCreditTransferUseCase → returns 202

// controller/PaymentStatusReportController.java
//   POST /instant-core-service/v1/payment-status-report
//   → reads headers → calls ProcessStatusReportUseCase → returns 200
```

### 2.7 Infrastructure
```java
// adapter/out/JpaPaymentRepositoryAdapter.java  — implements PaymentRepositoryPort
// config/RedisCacheConfig.java                  — idempotency key config
// config/WebClientConfig.java                   — HTTP client for downstream calls
// exception/IcsException.java                   — base exception
// exception/GlobalExceptionHandler.java         — @RestControllerAdvice
```

## 3. DB Migration Plan
| Script | Content |
|---|---|
| V001__create_payments_table.sql | payments table + 3 indexes |
| V002__create_payment_status_history_table.sql | history table + 1 index |

## 4. Test Plan
| Test Class | Type | Covers |
|---|---|---|
| InstantCreditTransferServiceTest | Unit | 9-step orchestration |
| PaymentStatusReportServiceTest | Unit | Leg 2 reconcile + settle |
| MockBvsAdapterTest | Unit | Mock returns correct response |
| InstantCreditTransferControllerIT | Integration | Full POST pacs.008 → 202 |
| PaymentStatusReportControllerIT | Integration | Full POST pacs.002 → 200 |
| PaymentRepositoryIT | Integration | DB read/write with Testcontainers |

---
*Generated from: api-spec.summary.md + arch.summary.md*
