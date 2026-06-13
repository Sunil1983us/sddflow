# Backend API Contract (Consumer)
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Scope: MVP+
> Drafted at: /specify (Input: srd.summary.md)
> Refined at: /plan-arch (Input: + arch.summary.md — service layer / API client design)

---

## 1. Base URL
```
{protocol}://{host}/api/v1
```
Configured via build-time env config (`.env` / `react-native-config` /
Flutter `--dart-define`) per environment (dev/staging/prod) — never
hardcoded (constitution Part 1 — OPS-7).

## 2. Authentication & Token Refresh
| Method | Header | Notes |
|---|---|---|
| {Bearer/OAuth2/OIDC} | Authorization: Bearer {token} | Access token stored in Keychain (iOS) / Keystore (Android) — never AsyncStorage/plain prefs |

**Token refresh flow:**
| Step | Behaviour |
|---|---|
| Access token expiry | {lifetime, e.g. 15 min} |
| Refresh token expiry | {lifetime, e.g. 30 days} — stored in Keychain/Keystore only |
| On 401 | API client pauses queued requests, calls `POST /api/v1/auth/refresh` with refresh token, retries original request with new access token |
| Refresh failure | Clear tokens, navigate to login screen, surface "session expired" message |
| Concurrent 401s | Single in-flight refresh — other requests queue and replay after refresh resolves |

## 3. Common Headers (sent by this app)
| Header | Mandatory | Description |
|---|---|---|
| Authorization | Yes (authenticated routes) | `Bearer {token}` |
| X-Correlation-Id | Yes | UUID v4 — generated client-side per request, propagated to backend, included in crash reports |
| X-Client-Version | Yes | App build/version (e.g. `1.4.2 (build 87)`) — for backend-side debugging of client issues |
| X-Platform | Yes | `ios` \| `android` |
| Content-Type | Yes (mutations) | application/json |
| Idempotency-Key | Recommended (mutations) | UUID v4 — dedup key, important for retried requests after connectivity drop |

## 4. Endpoints Consumed

### GET /api/v1/{resource}
**Purpose:** {what this app fetches and where it's used — screen/view-model}
**Used by:** {ScreenName / ViewModel}

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
| Loading state | {skeleton/shimmer placeholder — component name} |
| Empty state | {what's shown when list is empty} |
| Local cache | Written to local store on success — see data-model.md §2 (table/key + sync metadata) |
| Offline | If offline, serve from local cache and show "offline — last updated {timestamp}" (resilience.md §1, Full scope) |
| Retry/Timeout | See §8 below — pilot/mvp: {n} attempts, {ms}ms timeout |

**Response 404 Not Found:**
```json
{
  "errorCode": "NOT_FOUND",
  "message": "{resource} not found"
}
```
**App behaviour on 404:** {navigate back, show empty/not-found state}

---

### POST /api/v1/{resource}
**Purpose:** {what user action triggers this — screen/button}
**Used by:** {ScreenName / ViewModel}

**Request:**
```json
{
  "{field1}": "{type — description}",
  "{field2}": "{type — description}"
}
```
**Client-side validation (before send):** {validation lib/schema — must mirror backend rules from srd.md}

**Offline behaviour:** If offline, write to local outbox/sync queue
(data-model.md §2) with `dirty=true`, show optimistic UI update, sync when
connectivity restored (resilience.md §1).

**Response 201/202:**
```json
{
  "{resourceId}": "string — UUID",
  "status": "string — initial status",
  "receivedAt": "string — ISO 8601 UTC"
}
```
**App behaviour on success:** {toast/snackbar, navigate, optimistic update reconciled with server response}

**Response 400 Bad Request:**
```json
{
  "errorCode": "VALIDATION_ERROR",
  "message": "{description}",
  "field": "{field that failed}"
}
```
**App behaviour on 400:** {inline field error — map `field` to form field name}

**Response 409 Conflict:**
```json
{
  "errorCode": "DUPLICATE_REQUEST",
  "message": "Duplicate Idempotency-Key"
}
```
**App behaviour on 409:** {treat as success if idempotent — reconcile local outbox entry, or show conflict message per resilience.md §3 conflict resolution}

---

## 5. Status Codes & App Behaviour
| HTTP | Meaning | App behaviour |
|---|---|---|
| 200 | OK | Render data, update local cache |
| 201 | Created | Update local cache, reconcile outbox entry |
| 202 | Accepted | Show pending/processing state, poll or wait for push notification |
| 400 | Bad Request | Inline form/field error |
| 401 | Unauthorized | Trigger token refresh flow (§2); on failure → login screen |
| 403 | Forbidden | Show "access denied" screen — no retry |
| 404 | Not Found | Empty/not-found state |
| 409 | Conflict | Conflict-specific handling — see endpoint + resilience.md §3 |
| 429 | Too Many Requests | Backoff per §8, show rate-limit notice |
| 500/502/503 | Server Error | Generic error state + retry option (resilience.md) |

## 6. Error Response Format (from backend)
```json
{
  "errorCode": "string — unique code",
  "message": "string — human readable",
  "timestamp": "string — ISO 8601",
  "traceId": "string — correlation ID"
}
```
The app surfaces `message` only when it is safe for end users (per backend
contract); otherwise maps `errorCode` to a localized user-facing string.
`traceId` is attached to crash/error reports (investigation.md §1, Full scope).

## 7. Error Codes → App Behaviour
| Code | HTTP | App Treatment |
|---|---|---|
| VALIDATION_ERROR | 400 | Inline field error |
| DUPLICATE_REQUEST | 409 | Conflict message / idempotent success |
| NOT_FOUND | 404 | Empty/not-found state |
| UNAUTHORIZED | 401 | Trigger token refresh, then login if it fails |
| FORBIDDEN | 403 | Access-denied screen |
| INTERNAL_ERROR | 500 | Generic error banner + retry |
| {DOMAIN_ERROR} | 422 | {domain-specific app treatment} |

## 8. Client-Side Retry/Timeout Assumptions
| Endpoint | Timeout | Retry Attempts | Backoff |
|---|---|---|---|
| GET /api/v1/{resource} | {ms, e.g. 10000ms} | {n, e.g. 3} | Exponential — 1s, 2s, 4s |
| POST /api/v1/{resource} | {ms, e.g. 15000ms} | 0 (mutations not retried automatically — queued via outbox instead, see resilience.md §1) | n/a |

Full detail (Full scope) in resilience.md §2-3.

---
*Drafted from: srd.summary.md (at /specify) | Refined from: arch.summary.md (at /plan-arch)*
