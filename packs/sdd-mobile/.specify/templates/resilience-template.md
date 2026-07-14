# Mobile Resilience
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Scope: Full only — skip for pilot + mvp

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: integration list} |

## 1. Offline-First Strategy

| Concern | Behaviour |
|---|---|
| Default assumption | Assume offline first — every read serves from local store (data-model.md §3), every write goes to local store first (constitution Part 1 — Never Do) |
| Connectivity detection | NetInfo (React Native) / connectivity_plus (Flutter) — `online`/`offline` events drive UI state and sync triggers |
| Local-first writes | Mutations write to local table with `is_dirty=true` and an entry in `sync_outbox` (data-model.md §5) immediately — UI updates optimistically |
| Background sync queue | Background task (e.g. WorkManager/BackgroundTasks, or in-app queue drained on app-foreground/connectivity-restore) drains `sync_outbox` in FIFO order per entity |
| Offline-capable screens | {list screens that remain usable offline via cached local data — see data-model.md §3} |
| Reconnect behaviour | On connectivity restored: dismiss offline banner, drain `sync_outbox`, revalidate stale caches per data-model.md §6 |

---

## 2. API Call Retry & Backoff Policy

| Call Type | Retry? | Max Attempts | Backoff | Notes |
|---|---|---|---|---|
| GET (reads) | Yes | 3 | Exponential — 1s, 2s, 4s | Skip retry on 4xx (except 429); serve cached data while retrying |
| POST/PUT/PATCH/DELETE (outbox sync) | Yes — via outbox | Up to {n, e.g. 5} per outbox entry | Exponential with jitter — 2s, 4s, 8s, 16s, 32s | Use Idempotency-Key (api-spec.md §3) so retries are safe to duplicate |
| 429 Too Many Requests | Yes | per `Retry-After` header | As specified by header | Pause sync worker for the indicated duration |

```ts
// Example: outbox sync worker retry config
const retryConfig = {
  maxAttempts: 5,
  backoff: (attempt) => Math.min(2000 * 2 ** attempt, 60000) + jitter(),
  retryableStatuses: [408, 429, 500, 502, 503, 504],
  giveUpAfter: (entry) => entry.retryCount >= 5, // mark sync_error, surface to user
};
```

### Rule: Correlation ID per Sync Attempt
- `X-Correlation-Id` is generated once per outbox entry and reused across
  all retry attempts (mirrors backend correlation tracing)
- Each retry attempt is logged with attempt number (for crash/error
  reporting — see investigation.md §1)

---

## 3. Conflict Resolution Strategy (Offline Edits)

| Scenario | Strategy | Notes |
|---|---|---|
| {Resource} edited offline, unchanged on server since | Apply local change — last-write-wins | No conflict — `updated_at` on server matches `last_synced_at` |
| {Resource} edited offline AND on server (by another user/device) | {last-write-wins by timestamp / field-level merge / user-prompt} | {describe per-entity policy — e.g. "merge" for non-overlapping fields, "user-prompt" for conflicting fields} |
| {Resource} deleted on server, edited offline | User-prompt: "This item was deleted — keep your changes as new item, or discard?" | Never silently drop user data |
| Outbox entry references a now-deleted parent | Discard outbox entry, notify user | Log to investigation.md |

**Conflict UX:**
| Step | Behaviour |
|---|---|
| Detect | 409 Conflict response, or server `updated_at` newer than `last_synced_at` |
| Surface | Non-blocking conflict banner/modal on affected screen — never block the whole app |
| Resolve | User picks "Keep mine" / "Keep server's" / "Merge" (if applicable) — choice written back via outbox |
| Audit | Conflict + resolution logged with correlation ID (investigation.md §1) |

---

## 4. Timeout Configuration

| Call Type | Timeout | On Timeout |
|---|---|---|
| GET (reads) | {ms, e.g. 10000ms} | Serve cached data + "showing cached data" indicator; retry per §2 |
| POST/PUT/PATCH/DELETE (outbox sync) | {ms, e.g. 20000ms} | Mark outbox entry for retry per §2 — do not duplicate on next app launch |
| File upload/download (media) | {ms or none — use progress events} | Show progress indicator; allow cancel + resume |

```ts
// Example: AbortController-based timeout for fetch
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 10000);
fetch(url, { signal: controller.signal }).finally(() => clearTimeout(timeoutId));
```

---

## 5. Degraded Connectivity UX

| Scenario | UX |
|---|---|
| App launch, offline | Show cached data immediately (never blank screen) + persistent offline banner: "{message}" |
| Action taken offline | Optimistic UI update + small "queued — will sync" indicator (badge/icon on the item) |
| Sync in progress | Subtle "syncing..." indicator — never blocks interaction |
| Sync failed (max retries exceeded) | Item shows "sync failed" indicator with manual "Retry" action; surfaced in a "Pending changes" screen if queue grows |
| Reconnected | Brief "back online — syncing {n} changes" toast, banner dismissed |
| Slow/flaky connection | Skeleton/shimmer placeholders matching final layout — never layout shift; requests respect §4 timeouts |

---

## 6. Failure Paths

| Trigger | Action | User-Visible Result |
|---|---|---|
| API retry exhausted (read) | Serve cached/stale data if available, else error state | "Unable to refresh — showing data from {timestamp}" or error card |
| Outbox sync exhausted (write) | Mark entry `sync_error`, stop auto-retry | "Some changes couldn't be saved — tap to retry" in Pending Changes screen |
| Offline during critical action (e.g. payment) | Block submit — do not queue irreversible/financial actions | "You're offline — this action requires a connection" |
| Conflict unresolved | Hold outbox entry, prompt user (§3) | Conflict banner/modal on affected screen |

---

## 7. Observability

| Event | Reported To | Data Included |
|---|---|---|
| Sync attempt | Breadcrumb (crash SDK) | entity, attempt number, correlation ID |
| Sync exhausted | Crash/error-tracking SDK | entity, attempts, last error, correlation ID |
| Conflict detected | Crash/error-tracking SDK + investigation log | entity, correlation ID, resolution chosen |
| Offline/online transition | Analytics | timestamp, duration offline, pending outbox count |
| Timeout | Crash/error-tracking SDK | endpoint, timeout value, correlation ID |

See investigation.md (Full scope) for SDK integration details and triage.

---

## Approvals
| Role | Approver | Status | Date |
|---|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | | Pending | |
