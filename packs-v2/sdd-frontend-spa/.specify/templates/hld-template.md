# High Level Design (HLD)
# Instant Core Service (ICS) — Pilot

> Version: 1.0 | Status: Draft | Date: {date}
> Input: arch.summary.md + srd.summary.md

---

## 1. Purpose
{One paragraph — what ICS does, why it exists, pilot scope.}

---

## 2. System Context (C4 Level 1)

```mermaid
graph TD
    Channel([Customer / Channel])
    Gateway[Instant Gateway Service]
    ICS[Instant Core Service **ICS**]
    BVS[Business Validation Service]
    FRAML[Fraud & AML Service]
    PBS[Payment Booking Service]
    CSM[CSM Service]
    CBS([Core Banking System])
    RT1([RT1 — EBA Clearing])

    Channel -->|pain.001| Gateway
    Gateway -->|pacs.008 XML| ICS
    ICS -->|validate| BVS
    ICS -->|screen| FRAML
    ICS -->|EVT_001 / EVT_002| PBS
    PBS -->|fund events| CBS
    ICS -->|pacs.008| CSM
    CSM -->|Swift AGI| RT1
    RT1 -->|pacs.002| CSM
    CSM -->|pacs.002| ICS
    ICS -->|pacs.002 callback| Gateway
```

> **Pilot:** BVS, FRAML, PBS, CSM, Gateway callback are all mocked.

---

## 3. Container Diagram (C4 Level 2)

```mermaid
graph TD
    subgraph Docker Compose Network
        GW[Mock Gateway\nport 8081]
        ICS[ICS App\nSpring Boot 3\nport 8080]
        PG[(PostgreSQL 15\nport 5432)]
        RD[(Redis 7\nport 6379)]
        MOCK[Mock Services\nBVS / FRAML / PBS / CSM]
    end

    GW -->|POST pacs.008| ICS
    ICS -->|JPA / Flyway| PG
    ICS -->|idempotency keys| RD
    ICS -->|HTTP mocked calls| MOCK
    MOCK -->|pacs.002 push| ICS
    ICS -->|pacs.002 callback| GW
```

---

## 4. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Java | 21 |
| Framework | Spring Boot | 3.x |
| Build | Maven | 3.9+ |
| Database | PostgreSQL | 15 |
| Cache | Redis | 7 |
| ORM | Spring Data JPA + Hibernate | 6 |
| DB Migration | Flyway | Latest |
| Testing | JUnit 5 + Mockito + Testcontainers | — |
| Containerisation | Docker + Docker Compose | Latest |
| API Style | REST — OpenAPI 3.0 | — |
| Deployment | On-premise | Docker only |

---

## 5. Payment Flow — Happy Path

```mermaid
sequenceDiagram
    participant GW as Gateway
    participant ICS as ICS
    participant BVS as BVS (Mock)
    participant FRAML as FRAML (Mock)
    participant PBS as PBS (Mock)
    participant CSM as CSM (Mock)

    GW->>ICS: POST /instant-credit-transfer (pacs.008)
    ICS-->>GW: 202 Accepted {paymentId}
    Note over ICS: status = RECEIVED

    ICS->>BVS: POST /validation/v1
    BVS-->>ICS: result=OK, status=VALID
    Note over ICS: status = VALIDATION

    ICS->>FRAML: POST /framl/v1
    FRAML-->>ICS: result=NO_HIT
    Note over ICS: status = FRAML_CHECK

    ICS->>PBS: POST /booking/v1 (EVT_001)
    PBS-->>ICS: result=OK, status=RESERVED
    Note over ICS: status = FUNDS_RESERVED

    ICS->>CSM: POST /clearing-settlement-service/v1
    CSM-->>ICS: status=SUBMITTED, clearingRef=RT1-xxx
    Note over ICS: status = AWAITING_RECEIPT

    CSM->>ICS: POST /payment-status-report (pacs.002 ACCP)
    ICS-->>CSM: 200 Acknowledged
    Note over ICS: status = RECONCILING

    ICS->>PBS: POST /booking/v1 (EVT_002)
    PBS-->>ICS: result=OK, status=BOOKED
    Note over ICS: status = SETTLED

    ICS->>GW: POST /payment-status-notification (pacs.002)
    GW-->>ICS: 200 Acknowledged
```

---

## 6. Payment Status Machine

```mermaid
stateDiagram-v2
    [*] --> RECEIVED
    RECEIVED --> VALIDATION
    VALIDATION --> FRAML_CHECK
    FRAML_CHECK --> FUNDS_RESERVED
    FUNDS_RESERVED --> AWAITING_RECEIPT
    AWAITING_RECEIPT --> RECONCILING
    RECONCILING --> SETTLED
    SETTLED --> [*]
```

> Pilot has one terminal status only: SETTLED

---

## 7. Key Design Principles

| Principle | Applied As |
|---|---|
| Hexagonal Architecture | Ports & Adapters — domain isolated from infrastructure |
| Mock-First | All 5 downstream services mocked via @Profile("mock") |
| Persist Before Proceed | Status written to DB before each downstream call |
| Zero PII in Logs | IBAN masked — payment_id + correlation_id only |
| Pilot Simplicity | No retry, no circuit breaker, no compensation |

---

## 8. Non-Functional Summary

| Category | Target |
|---|---|
| End-to-end SLA | 7,000 ms |
| Leg 1 ICS budget | 4,000 ms |
| Availability | 99.99% (production target) |
| Throughput | 500 TPS peak (production target) |
| Data Retention | 7 years (payments) |
| Deployment | Docker Compose — on-premise |

---

## 9. Out of Scope — Pilot

```
Retry / circuit breaker / compensation
Unhappy path handling
Investigation cases
mTLS / HMAC signatures
Inbound payment flow
pacs.004 payment return
Runtime config server
```

---
*Generated from: arch.summary.md + srd.summary.md*
*Diagrams: Mermaid — renders in GitHub, VS Code, and Claude*
