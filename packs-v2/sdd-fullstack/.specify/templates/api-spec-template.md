# API Specification
# Feature: {Feature Name}

> Version: 1.0 | Status: Draft | Date: {date}
> Input: arch.summary.md + srd.summary.md

---

## 1. Overview
Base URL: `/instant-core-service/v1`
Content-Type: `application/xml` (request bodies) / `application/json` (responses)

---

## 2. ICS Inbound Endpoints

### POST /instant-core-service/v1/instant-credit-transfer
**Purpose:** Leg 1 — receive outbound pacs.008 from Gateway
**Caller:** Instant Gateway Service

**Request Headers:**
| Header | Mandatory | Value |
|---|---|---|
| X-Correlation-Id | Yes | YYYYMMDD-OB-NNNNNN |
| X-Tracking-Id | No | Absent on first call |
| X-Source-System | Yes | Originating system ID |
| X-Payment-Direction | Yes | OUTBOUND |
| X-Message-Type | Yes | pacs.008 |
| X-Scheme | Yes | SCT_INST |
| Content-Type | Yes | application/xml |

**Request Body:** pacs.008.001.08 XML

**Response: HTTP 202 Accepted**
```json
{
  "paymentId": "a1b2c3d4-0001-0001-0001-000000000001",
  "correlationId": "20260609-OB-000001",
  "status": "RECEIVED",
  "timestamp": "2026-06-09T10:15:30.265Z"
}
```

**Error Responses:**
| HTTP | Code | Condition |
|---|---|---|
| 400 | ICS-400 | Missing mandatory header |
| 400 | ICS-401 | Invalid XML — cannot parse |
| 500 | ICS-500 | Internal server error |

---

### POST /instant-core-service/v1/payment-status-report
**Purpose:** Leg 2 — receive pacs.002 ACCP from CSM Service
**Caller:** CSM Service

**Request Headers:**
| Header | Mandatory | Value |
|---|---|---|
| X-Correlation-Id | Yes | YYYYMMDD-OB-NNNNNN |
| X-Tracking-Id | Yes | payment_id from ICS |
| X-Source-System | Yes | CSM |
| X-Payment-Direction | Yes | OUTBOUND |
| X-Message-Type | Yes | pacs.002 |
| X-Scheme | Yes | SCT_INST |
| Content-Type | Yes | application/xml |

**Request Body:** pacs.002.001.10 XML

**Response: HTTP 200 OK**
```json
{
  "acknowledgementId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "trackingId": "a1b2c3d4-0001-0001-0001-000000000001",
  "correlationId": "20260609-OB-000001",
  "status": "RECEIVED",
  "timestamp": "2026-06-09T10:15:30.265Z"
}
```

---

## 3. ICS Outbound Calls (Mocked in Pilot)

### POST /validation/v1 — BVS
**Request:** pacs.008 XML + headers
**Happy Path Response:**
```json
{ "result": "OK", "status": "VALID",
  "trackingId": "...", "correlationId": "..." }
```

### POST /framl/v1 — FRAML
**Request:** pacs.008 XML + headers
**Happy Path Response:**
```json
{ "result": "NO_HIT", "status": "NO_HIT",
  "trackingId": "...", "correlationId": "..." }
```

### POST /booking/v1 — PBS EVT_001
**Request Body:**
```json
{ "payload": "<pacs.008 xml>", "eventId": "EVT_001",
  "typeOfBooking": "R", "amount": 250.00, "currency": "EUR",
  "debtorBIC": "TESTBICXXX", "creditorBIC": "DESTBICXXX" }
```
**Happy Path Response:**
```json
{ "result": "OK", "status": "RESERVED", "eventId": "EVT_001",
  "trackingId": "...", "correlationId": "..." }
```

### POST /booking/v1 — PBS EVT_002
**Request Body:** same as EVT_001 with `"eventId": "EVT_002"`, `"typeOfBooking": "B"`
**Happy Path Response:**
```json
{ "result": "OK", "status": "BOOKED", "eventId": "EVT_002",
  "trackingId": "...", "correlationId": "..." }
```

### POST /clearing-settlement-service/v1 — CSM
**Request:** pacs.008 XML + headers
**Happy Path Response:**
```json
{ "status": "SUBMITTED", "clearingRef": "RT1-2026-000001",
  "trackingId": "...", "correlationId": "..." }
```

### POST /instant-gateway/v1/payment-status-notification — Gateway Callback
**Request:** pacs.002 XML + headers
**Mock URL:** `http://mock-gateway-service:8080/instant-gateway/v1/payment-status-notification`
**Expected Acknowledgement:**
```json
{ "status": "RECEIVED", "trackingId": "...", "correlationId": "..." }
```

---

## 4. Error Catalog
| Code | HTTP | Meaning |
|---|---|---|
| ICS-400 | 400 | Missing mandatory header |
| ICS-401 | 400 | Invalid XML body |
| ICS-500 | 500 | Internal processing error |

---
*Generated from: arch.summary.md + srd.summary.md*
