# Backend API Contract (Consumer)
# Feature: {Feature Name}
> Version: 1.0 | Date: {date: YYYY-MM-DD} | Scope: MVP+

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: service layer / API client design} |

## 1. Base URL
```
{protocol}://{host}/api/v1
```
Configured via runtime config (`/config.json`) or build-time env var
(`VITE_API_BASE_URL` / `NEXT_PUBLIC_API_BASE_URL` / etc.) — never hardcoded
(constitution Part 1 — OPS-7).

## 2. Authentication
| Method | Header | Notes |
|---|---|---|
| {Bearer/OAuth2/Session Cookie} | {header name} | Token storage: {memory/httpOnly cookie} — never localStorage for access tokens unless context.md explicitly approves |

## 3. Common Headers (sent by this SPA)
| Header | Mandatory | Description |
|---|---|---|
| Authorization | Yes (authenticated routes) | `Bearer {token}` |
| X-Correlation-Id | Yes | UUID v4 — generated client-side, propagated to backend, included in error reports |
| X-Client-Version | Yes | App build/version — for backend-side debugging of client issues |
| Content-Type | Yes (mutations) | application/json |
| Idempotency-Key | Recommended (mutations) | UUID v4 — dedup key for retried requests |

## 4. Endpoints Consumed

### GET /api/v1/{resource}
**Purpose:** {what this SPA fetches and where it's used — page/component}
**Used by:** {ComponentName / page route}

**Response 200 OK:**
```json
{
  "{resourceId}": "string — UUID",
  "{field1}": "{type — description}",
  "status": "string",
  "createdAt": "string — ISO 8601 UTC",
  "updatedAt": "string — ISO 8601 UTC"
}
```

**Client-side handling:**
| Concern | Behaviour |
|---|---|
| Loading state | {skeleton/spinner — component name} |
| Empty state | {what's shown when list is empty} |
| Caching | {query cache key + staleTime, e.g. react-query `["resource", id]`} |
| Retry/Timeout | See resilience.md §2 (Full scope) — pilot/mvp: {n} attempts, {ms}ms timeout |

**Response 404 Not Found:**
```json
{
  "errorCode": "NOT_FOUND",
  "message": "{resource} not found"
}
```
**UI behaviour on 404:** {redirect to /not-found, inline empty state, etc.}

---

### POST /api/v1/{resource}
**Purpose:** {what user action triggers this — form/button}
**Used by:** {ComponentName / page route}

**Request:**
```json
{
  "{field1}": "{type — description}",
  "{field2}": "{type — description}"
}
```
**Client-side validation (before send):** {validation library/schema — e.g. zod/yup — must mirror backend rules from srd.md}

**Response 201/202:**
```json
{
  "{resourceId}": "string — UUID",
  "status": "string — initial status",
  "receivedAt": "string — ISO 8601 UTC"
}
```
**UI behaviour on success:** {toast, redirect, optimistic update + cache invalidation}

**Response 400 Bad Request:**
```json
{
  "errorCode": "VALIDATION_ERROR",
  "message": "{description}",
  "field": "{field that failed}"
}
```
**UI behaviour on 400:** {inline field error — map `field` to form field name}

**Response 409 Conflict:**
```json
{
  "errorCode": "DUPLICATE_REQUEST",
  "message": "Duplicate Idempotency-Key"
}
```
**UI behaviour on 409:** {treat as success if idempotent, or show conflict message}

---

## 5. Status Codes & Client Behaviour
| HTTP | Meaning | Client behaviour |
|---|---|---|
| 200 | OK | Render data |
| 201 | Created | Update cache, navigate/confirm |
| 202 | Accepted | Show pending/processing state, poll if applicable |
| 400 | Bad Request | Inline form/field error |
| 401 | Unauthorized | Redirect to login, clear session state |
| 403 | Forbidden | Show "access denied" UI — no retry |
| 404 | Not Found | Empty/not-found state |
| 409 | Conflict | Conflict-specific message — see endpoint |
| 429 | Too Many Requests | Backoff per resilience.md, show rate-limit notice |
| 500/502/503 | Server Error | Generic error UI + retry option (resilience.md) |

## 6. Error Response Format (from backend)
```json
{
  "errorCode": "string — unique code",
  "message": "string — human readable",
  "timestamp": "string — ISO 8601",
  "traceId": "string — correlation ID"
}
```
The SPA surfaces `message` only when it is safe for end users (per backend
contract); otherwise maps `errorCode` to a localized user-facing string.
`traceId` is included in error-tracking reports (investigation.md, Full scope).

## 7. Error Codes → UI Mapping
| Code | HTTP | UI Treatment |
|---|---|---|
| VALIDATION_ERROR | 400 | Inline field error |
| DUPLICATE_REQUEST | 409 | Conflict message / idempotent success |
| NOT_FOUND | 404 | Empty/not-found state |
| UNAUTHORIZED | 401 | Redirect to login |
| FORBIDDEN | 403 | Access-denied page |
| INTERNAL_ERROR | 500 | Generic error banner + retry |
| {DOMAIN_ERROR} | 422 | {domain-specific UI treatment} |

## 8. Client-Side Retry/Timeout Assumptions
| Endpoint | Timeout | Retry Attempts | Backoff |
|---|---|---|---|
| GET /api/v1/{resource} | {ms} | {n} | {exponential/linear} |
| POST /api/v1/{resource} | {ms} | 0 (mutations not retried automatically) | n/a |

Full detail (Full scope) in resilience.md §2-3.

---

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |
