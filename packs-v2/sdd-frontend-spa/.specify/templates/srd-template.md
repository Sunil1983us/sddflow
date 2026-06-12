# System Requirements Document (SRD)
# Feature: {Feature Name}

> Version: 1.0 | Status: Draft | Date: {date}
> Input: brd.summary.md

---

## 1. System Overview
{One paragraph — what ICS does technically.}

## 2. Functional Requirements
| ID | Requirement | Source |
|---|---|---|
| FR-001 | {description} | BR-{NNN} |

## 3. Non-Functional Requirements
| ID | Category | Requirement |
|---|---|---|
| NFR-001 | Performance | Leg 1 P99 ≤ 4,000 ms |
| NFR-002 | Availability | 99.99% uptime |
| NFR-003 | Throughput | 500 TPS peak |
| NFR-004 | Persistence | All state transitions persisted before next step |
| NFR-005 | Data Retention | Payments: 7 years |

## 4. Use Cases

### UC-001: Process Outbound Credit Transfer (Happy Path)
- **Actor:** Instant Gateway Service
- **Trigger:** POST /instant-core-service/v1/instant-credit-transfer
- **Precondition:** Valid pacs.008 XML received
- **Steps:** {list steps}
- **Outcome:** Payment SETTLED, pacs.002 ACCP sent to Gateway

### UC-002: Receive CSM Payment Status Report
- **Actor:** CSM Service
- **Trigger:** POST /instant-core-service/v1/payment-status-report
- **Steps:** {list steps}
- **Outcome:** EVT_002 triggered, status SETTLED

## 5. ISO 20022 Message Scope
| Message | Type | Direction |
|---|---|---|
| Credit Transfer | pacs.008.001.08 | Inbound from Gateway |
| Payment Status Report | pacs.002.001.10 | Inbound from CSM |
| Status Notification | pacs.002.001.10 | Outbound to Gateway |

## 6. Integration Points
| Service | Endpoint | Direction | Phase 1 |
|---|---|---|---|
| BVS | POST /validation/v1 | Outbound | Mock |
| FRAML | POST /framl/v1 | Outbound | Mock |
| PBS | POST /booking/v1 | Outbound | Mock |
| CSM | POST /clearing-settlement-service/v1 | Outbound | Mock |
| Gateway Callback | POST /instant-gateway/v1/payment-status-notification | Outbound | Mock |

## 7. Payment Status Flow
```
RECEIVED → VALIDATION → FRAML_CHECK → FUNDS_RESERVED
→ AWAITING_RECEIPT → RECONCILING → SETTLED
```

## 8. Header Requirements
| Header | Mandatory | Description |
|---|---|---|
| X-Correlation-Id | Yes | End-to-end tracing key |
| X-Tracking-Id | No (absent first call) | payment_id from ICS |
| X-Source-System | Yes | Originating system |
| X-Payment-Direction | Yes | OUTBOUND |
| X-Message-Type | Yes | pacs.008 or pacs.002 |
| X-Scheme | Yes | SCT_INST |

## 9. Constraints
{List known technical or business constraints.}

---
*Generated from: brd.summary.md*
