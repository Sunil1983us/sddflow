# API Specification
# Service: {Service Name}
> Version: 1.0 | Date: {date}
>
> **Living document** — describes the whole service's API surface, not one
> feature. Lives at `.specify/service/api-spec.md`. Every feature after the
> first one extends this file with new/changed endpoints (see
> `plan-design.prompt.md` §3) — it is never regenerated from a blank
> template. `design.md` §3 (per-feature) points here and lists only this
> feature's contribution.

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced} |
| arch.summary.md | {sections/IDs referenced} |

## 1. Base URL
```
{protocol}://{host}/api/v1
```

## 2. Authentication
| Method | Header | Notes |
|---|---|---|
| {Bearer/API Key/mTLS} | {header name} | {requirements} |

## 3. Common Headers
| Header | Mandatory | Description |
|---|---|---|
| X-Correlation-Id | Yes | UUID v4 — trace across services |
| X-Source-System | Yes | Caller system name |
| Content-Type | Yes | application/json |
| Idempotency-Key | Yes (mutations) | UUID v4 — dedup key |

## 4. Endpoints

### POST /api/v1/{resource}
**Purpose:** {what this creates or triggers}
**Caller:** {upstream service or actor}

**Request:**
```json
{
  "{field1}": "{type — description}",
  "{field2}": "{type — description}",
  "{amount}": "number — decimal, 4dp",
  "{currency}": "string — ISO 4217"
}
```

**Response 202 Accepted:**
```json
{
  "{resourceId}": "string — UUID",
  "status": "string — initial status",
  "receivedAt": "string — ISO 8601 UTC"
}
```

**Response 400 Bad Request:**
```json
{
  "errorCode": "VALIDATION_ERROR",
  "message": "{description}",
  "field": "{field that failed}"
}
```

**Response 409 Conflict:**
```json
{
  "errorCode": "DUPLICATE_REQUEST",
  "message": "Duplicate Idempotency-Key"
}
```

---

### GET /api/v1/{resource}/{id}
**Purpose:** {what this retrieves}

**Response 200 OK:**
```json
{
  "{resourceId}": "string — UUID",
  "status": "string",
  "createdAt": "string — ISO 8601 UTC",
  "updatedAt": "string — ISO 8601 UTC"
}
```

**Response 404 Not Found:**
```json
{
  "errorCode": "NOT_FOUND",
  "message": "{resource} not found"
}
```

---

## 5. Status Codes
| HTTP | Meaning | When |
|---|---|---|
| 200 | OK | GET success |
| 201 | Created | Resource created |
| 202 | Accepted | Async accepted |
| 400 | Bad Request | Validation failed |
| 401 | Unauthorized | Auth missing or invalid |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Duplicate request |
| 500 | Internal Error | Unexpected failure |

## 6. Error Response Format
```json
{
  "errorCode": "string — unique code",
  "message": "string — human readable",
  "timestamp": "string — ISO 8601",
  "traceId": "string — correlation ID"
}
```

## 7. Error Codes
| Code | HTTP | Meaning |
|---|---|---|
| VALIDATION_ERROR | 400 | Request failed validation |
| DUPLICATE_REQUEST | 409 | Duplicate Idempotency-Key |
| NOT_FOUND | 404 | Resource does not exist |
| UNAUTHORIZED | 401 | Auth missing or invalid |
| INTERNAL_ERROR | 500 | Unexpected system failure |
| {DOMAIN_ERROR} | 422 | {domain-specific error} |

---

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |

## Version History

| Version | Date | Feature | Change | CR |
|---|---|---|---|---|
| 1.0 | {date} | {feature that first created this document} | Initial API surface | — |
