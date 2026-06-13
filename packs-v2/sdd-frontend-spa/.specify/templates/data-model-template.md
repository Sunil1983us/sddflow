# Frontend State & Storage Model
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Scope: Full
> Drafted at: /specify (Input: srd.summary.md)
> Refined at: /plan-arch (Input: + arch.summary.md — store/module design)

---

## 1. Global State Shape

```mermaid
erDiagram
    {STORE_SLICE_A} {
        string id
        string status
        object data
        string updatedAt
    }
    {STORE_SLICE_B} {
        string parentId FK
        array items
        string lastFetchedAt
    }
    {STORE_SLICE_A} ||--o{ {STORE_SLICE_B} : "drives"
```

Store technology: {Redux Toolkit / Zustand / Pinia / Context API — from
constitution.md Tech Stack}.

## 2. State Slices / Modules

### {sliceA} (e.g. `auth`)
| Field | Type | Notes |
|---|---|---|
| user | object \| null | Current authenticated user, hydrated from `/me` |
| status | 'idle' \| 'loading' \| 'authenticated' \| 'error' | |
| token | string \| null | In-memory only — never persisted to localStorage |

**Actions/mutations:** {login, logout, refreshToken}
**Selectors:** {selectCurrentUser, selectIsAuthenticated}

### {sliceB} (e.g. `{feature}`)
| Field | Type | Notes |
|---|---|---|
| items | {Entity}[] | List from GET /api/v1/{resource} |
| selectedId | string \| null | Currently selected item |
| filters | object | Persisted to URL query params, not storage |
| lastFetchedAt | string (ISO 8601) | Used for cache invalidation |

**Actions/mutations:** {fetchList, selectItem, applyFilter}
**Selectors:** {selectFilteredItems, selectSelectedItem}

## 3. Browser Storage Usage

| Storage | Key | What's Stored | Why | Lifetime |
|---|---|---|---|---|
| localStorage | `{app}.theme` | UI theme preference | Persist across sessions, no backend round-trip | Until cleared by user |
| localStorage | `{app}.recentSearches` | Last N search terms | UX convenience | Rolling — max N entries |
| sessionStorage | `{app}.draftForm.{formId}` | In-progress form data | Recover from accidental reload within a session | Tab session |
| IndexedDB | `{app}-cache` DB, `{resource}` store | Offline-readable copies of fetched resources | Offline support (resilience.md §1) | TTL {n} hours or explicit invalidation |
| Cookies | `{app}.refreshToken` (httpOnly, Secure, SameSite=Strict) | Refresh token | Set by backend — not accessible to JS | Backend-defined expiry |

**Never stored in browser storage:** access tokens (kept in memory only),
passwords, full PII payloads beyond what's needed for the active session
(see §6 below).

## 4. Cache Invalidation Strategy

| Data | Cache Location | Invalidate When |
|---|---|---|
| {resource} list | Query cache (`["resource", "list", filters]`) | On create/update/delete mutation; on filter change |
| {resource} detail | Query cache (`["resource", id]`) | On update mutation for that id; TTL {n} min (staleTime) |
| User profile | Global store + query cache | On logout; on profile-update mutation |
| Offline IndexedDB copy | IndexedDB `{resource}` store | On successful re-fetch while online; manual "Refresh" action |

**Stale-while-revalidate:** {yes/no — describe pattern, e.g. show cached
data immediately, refetch in background, replace on success}.

## 5. Enums / Status Values

```
{EntityStatus}:
  {STATE_1}, {STATE_2}, {STATE_3}, {TERMINAL}
```

## 6. Data Classification & Privacy (SEC-7)

| Storage Location.Key | Classification | PII? | Encryption | Retention | Masking in Logs |
|---|---|---|---|---|---|
| localStorage.`{app}.theme` | Public | No | n/a | Until cleared by user | n/a |
| sessionStorage.`{app}.draftForm.{formId}` | Internal/Confidential | Yes/No | n/a (cleared on tab close) | Tab session | Never log form contents |
| IndexedDB.`{resource}` | Confidential | Yes/No | At-rest: relies on OS/browser profile encryption | TTL {n} hours | Never log cached payloads |
| Cookie.`{app}.refreshToken` | Restricted | No (token, not identity data) | httpOnly + Secure + SameSite; In-transit: TLS | Backend-defined | Never log token value |
| In-memory.`auth.token` | Restricted | No | Memory only — cleared on tab close | Session lifetime | Never log token value |

**Classification key:**
- Public — no restriction
- Internal — employees/contractors only
- Confidential — need-to-know (e.g. user-specific business data)
- Restricted — regulated PII/auth secrets — encryption + access audit mandatory

Any storage location marked PII = Yes must:
- Never appear in logs or error-tracking payloads (constitution Part 1 —
  Logging; investigation.md §1 scrubbing rules)
- Be cleared on logout (see §2 `logout` action)
- Be listed in security-design.md §4 Regulatory/Compliance Trace

---
*Drafted from: srd.summary.md (at /specify) | Refined from: arch.summary.md (at /plan-arch)*
