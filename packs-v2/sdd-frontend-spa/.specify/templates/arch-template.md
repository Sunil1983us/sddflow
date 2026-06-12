# Architecture Design Document
# Feature: {Feature Name}

> Version: 1.0 | Status: Draft | Date: {date}
> Input: srd.summary.md

---

## 1. Architecture Overview
{One paragraph — hexagonal, ports and adapters, mock-first.}

## 2. Component Diagram
```
[Gateway] ──POST pacs.008──► [InstantCreditTransferController]
                                        │
                                        ▼
                             [ProcessCreditTransferUseCase] ← port/in
                                        │
                                        ▼
                         [InstantCreditTransferService]
                                        │
              ┌─────────────────────────┼──────────────────────┐
              ▼                         ▼                       ▼
          [BvsPort]               [FramlPort]             [PbsPort]
          MockBvsAdapter          MockFramlAdapter        MockPbsAdapter
              │                         │                       │
              ▼                         ▼                       ▼
          [CsmPort]          [GatewayCallbackPort]     [PaymentRepositoryPort]
          MockCsmAdapter     MockGatewayCallbackAdapter JpaPaymentAdapter
```

## 3. Layer Responsibilities
| Layer | Package | Responsibility |
|---|---|---|
| Controller | controller/ | Receive HTTP, delegate to inbound port, return response |
| Inbound Port | port/in/ | Use case interface |
| Service | service/ | Orchestrate 9-step payment flow |
| Outbound Port | port/out/ | Interface per downstream system |
| Mock Adapter | mock/ | @Profile("mock") happy path responses |
| Domain | domain/ | PaymentEntity, PaymentStatus enum |
| Repository | repository/ | Spring Data JPA |
| DTO | dto/ | Java records for request/response |

## 4. Key Design Decisions
| ID | Decision | Rationale |
|---|---|---|
| ADR-001 | Hexagonal architecture | Isolate domain from infrastructure |
| ADR-002 | Mock-first all downstream | Pilot — no real integrations |
| ADR-003 | Synchronous REST for all calls | Simplest for pilot demo |
| ADR-004 | Status persisted before each step | RPO = zero |
| ADR-005 | Java records for DTOs | Java 21 idiomatic |

## 5. Payment Orchestration Flow
```
receive pacs.008
    → persist RECEIVED
    → call BVS → persist VALIDATION
    → call FRAML → persist FRAML_CHECK
    → call PBS EVT_001 → persist FUNDS_RESERVED
    → call CSM → store clearing_ref → persist AWAITING_RECEIPT
    [async: receive pacs.002 via POST]
    → reconcile 3 fields → persist RECONCILING
    → call PBS EVT_002 → persist SETTLED
    → callback Gateway
```

## 6. Data Architecture
| Table | Purpose |
|---|---|
| payments | One row per payment — full lifecycle state |
| payment_status_history | Audit trail — one row per status change |

## 7. Security (Pilot)
- No mTLS in pilot — plain HTTP between Docker containers
- No HMAC signature validation in pilot
- All services on Docker Compose internal network

## 8. Observability
- Structured JSON logs
- Every log line: payment_id + correlation_id
- Log events: PAYMENT_RECEIVED, STATUS_TRANSITION, DOWNSTREAM_REQUEST,
  DOWNSTREAM_RESPONSE, PAYMENT_SETTLED

---
*Generated from: srd.summary.md*
