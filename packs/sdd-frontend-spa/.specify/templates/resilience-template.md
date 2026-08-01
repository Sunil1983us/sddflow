# Frontend Resilience
# Feature: {Feature Name}
> Version: 1.0 | Date: {date: YYYY-MM-DD} | Scope: Full only — skip for pilot + mvp

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: integration list} |

## 1. Offline Detection & UX

| Concern | Behaviour |
|---|---|
| Detection | `navigator.onLine` + `online`/`offline` window events; optional periodic health-check ping |
| Offline banner | Persistent, non-blocking banner: "{message}" — shown app-wide when offline |
| Offline-capable routes | {list routes/components that remain usable offline via cached/IndexedDB data — see data-model.md §3} |
| Reconnect behaviour | On `online` event: dismiss banner, revalidate stale queries, flush any queued mutations |
| Service worker | {Yes/No — if Yes: caching strategy (stale-while-revalidate / cache-first for static assets, network-first for API)} |

---

## 2. API Call Retry & Backoff Policy

| Call Type | Retry? | Max Attempts | Backoff | Notes |
|---|---|---|---|---|
| GET (queries) | Yes | 3 | Exponential — 500ms, 1s, 2s | Skip retry on 4xx (except 429) |
| POST/PUT/PATCH/DELETE (mutations) | No (default) | 0 | n/a | Re-running a mutation can duplicate side effects — use Idempotency-Key (api-spec.md §3) if retry is required |
| 429 Too Many Requests | Yes | per `Retry-After` header | As specified by header | Show rate-limit notice to user |

```ts
// Example: react-query / TanStack Query retry config
{
  retry: (failureCount, error) => {
    if (error.status >= 400 && error.status < 500 && error.status !== 429) {
      return false; // don't retry client errors
    }
    return failureCount < 3;
  },
  retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
}
```

### Rule: Correlation ID per Retry
- `X-Correlation-Id` is generated once per logical user action and reused
  across all retry attempts (mirrors backend correlation tracing)
- Each retry attempt is logged client-side with attempt number (for
  error-tracking — see investigation.md §1)

---

## 3. Timeout Handling for Slow Networks

| Call Type | Timeout | On Timeout |
|---|---|---|
| GET (queries) | {ms, e.g. 8000ms} | Show "taking longer than usual" message; allow manual retry |
| POST/PUT/PATCH/DELETE (mutations) | {ms, e.g. 15000ms} | Show timeout error; do NOT auto-retry — confirm with user before resubmitting |
| File upload/download | {ms or none — use progress events} | Show progress indicator; allow cancel |

```ts
// Example: AbortController-based timeout
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 8000);
fetch(url, { signal: controller.signal }).finally(() => clearTimeout(timeoutId));
```

---

## 4. Error Boundaries (Component-Level Fallback UI)

| Boundary Scope | Component | Fallback UI | Recovery |
|---|---|---|---|
| App root | `<AppErrorBoundary>` | Full-page "Something went wrong" + reload button | Reload app |
| Route/page | `<PageErrorBoundary>` | In-layout error card, nav remains usable | "Try again" re-mounts the page |
| Widget/section | `<WidgetErrorBoundary>` | Inline "Unable to load {widget}" placeholder | Retry button re-fetches just that widget |

**Rule:** Every error boundary reports the caught error + component stack
to the error-tracking SDK (investigation.md §1) with the active
correlation ID and route.

---

## 5. Degraded-Mode UX

| Scenario | Degraded UX |
|---|---|
| Initial load, data not yet fetched | Skeleton screens matching final layout (component-spec.md) — never blank white screen or layout shift |
| Refetch in progress, stale data available | Show stale data with a subtle "updating..." indicator (stale-while-revalidate — data-model.md §4) |
| Fetch failed, cached data available (IndexedDB) | Show cached data + "showing offline data from {timestamp}" banner |
| Fetch failed, no cached data | Empty state with retry action — never a raw error stack |
| Non-critical widget fails | Page remains usable; only that widget shows its error boundary fallback (§4) |

---

## 6. Failure Paths

| Trigger | Action | User-Visible Result |
|---|---|---|
| API retry exhausted (query) | Show cached/stale data if available, else error state | "Unable to refresh — showing last known data" or error card |
| API timeout (mutation) | Surface error, do not auto-retry | "Request timed out — please try again" |
| Offline during mutation | Block submit, queue if supported, else disable form | "You're offline — changes will be saved when you reconnect" or disabled form with banner |
| Error boundary triggered | Render fallback UI at the appropriate scope (§4) | Scoped fallback — rest of app unaffected |

---

## 7. Observability

| Event | Reported To | Data Included |
|---|---|---|
| Retry attempt | Console (dev) / error-tracking breadcrumb (prod) | endpoint, attempt number, correlation ID |
| Retry exhausted | Error-tracking SDK | endpoint, attempts, last error, correlation ID |
| Error boundary triggered | Error-tracking SDK | component stack, route, correlation ID |
| Offline/online transition | Analytics/RUM | timestamp, duration offline |
| Timeout | Error-tracking SDK | endpoint, timeout value, correlation ID |

See investigation.md (Full scope) for SDK integration details and triage.

---

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |
