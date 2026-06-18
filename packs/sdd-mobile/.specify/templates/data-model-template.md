# Local Data & Cache Model
# Feature: {Feature Name}
> Version: 1.0 | Date: {date} | Scope: Full

---

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced — drafted at /specify} |
| arch.summary.md | {sections/IDs referenced — refined at /plan-arch: storage/sync layer design} |

## 1. Local Storage Overview

| Concern | Choice |
|---|---|
| Structured storage | {SQLite (via WatermelonDB/Room/Core Data) / Realm — from constitution.md Tech Stack} |
| Key-value storage | {AsyncStorage / MMKV / Keychain-Keystore for secrets} |
| Sync model | {offline-first — local-first writes, background sync queue; see resilience.md §1} |

## 2. Entity Relationship (Local Tables)
```mermaid
erDiagram
    {ENTITY_A} {
        string id PK
        string status
        string data
        string updated_at
        string last_synced_at
        boolean is_dirty
    }
    {ENTITY_B} {
        string id PK
        string entity_a_id FK
        string field_1
        string updated_at
    }
    {ENTITY_A} ||--o{ {ENTITY_B} : "has"
```

## 3. Tables / Stores

### {entity_a} (SQLite/Realm table)
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | TEXT/UUID | NOT NULL | PK — server-assigned or client-generated UUID for offline-created records |
| status | TEXT | NOT NULL | Current lifecycle state |
| {field} | {type} | NULL | {description} |
| updated_at | TEXT (ISO 8601) | NOT NULL | Last local write timestamp |
| last_synced_at | TEXT (ISO 8601) | NULL | Last successful sync with backend — null if never synced |
| is_dirty | INTEGER (0/1) | NOT NULL | 1 = local change pending sync (offline write) |
| sync_error | TEXT | NULL | Last sync error message, if any |

**Indexes:**
- `idx_{table}_status` ON {table}(status)
- `idx_{table}_is_dirty` ON {table}(is_dirty) — used by background sync worker

### {entity_b} (SQLite/Realm table)
| Column | Type | Nullable | Notes |
|---|---|---|---|
| id | TEXT/UUID | NOT NULL | PK |
| entity_a_id | TEXT/UUID | NOT NULL | FK → {entity_a}.id |
| {field} | {type} | NOT NULL | |
| updated_at | TEXT (ISO 8601) | NOT NULL | |

## 4. Key-Value Store Entries (AsyncStorage/MMKV)

| Key | Type | Contents | Lifetime |
|---|---|---|---|
| `{app}.session.refreshToken` | string | Refresh token — **store in Keychain/Keystore, NOT AsyncStorage** | Until logout or expiry |
| `{app}.user.preferences` | JSON | UI preferences (theme, locale, notification settings) | Until cleared by user |
| `{app}.sync.lastFullSyncAt` | string (ISO 8601) | Timestamp of last full sync with backend | Updated each successful sync |
| `{app}.{feature}.lastSyncedAt` | string (ISO 8601) | Per-feature incremental sync cursor | Updated each successful sync |

## 5. Sync Metadata & Outbox

| Field | Type | Notes |
|---|---|---|
| `is_dirty` | boolean | Set on local write while offline or before server ack |
| `last_synced_at` | timestamp \| null | Updated on successful sync |
| `sync_error` | string \| null | Populated on sync failure — surfaced in resilience.md §3 conflict UX |
| Outbox queue | table `sync_outbox` (id, entity, operation, payload, created_at, retry_count) | Background worker drains this queue per resilience.md §1-2 |

## 6. Cache Eviction Policy

| Data | Eviction Trigger | Notes |
|---|---|---|
| {resource} list cache | TTL {n} hours, or explicit "Refresh" pull-to-refresh | Stale-while-revalidate — show cached data immediately, refetch in background |
| {resource} detail cache | TTL {n} hours | Evicted on logout |
| Images/media cache | LRU, max {n} MB | Use platform image-cache library (FastImage/Glide/Coil) |
| Outbox entries | Removed on successful sync ack | Retained with `sync_error` if max retries exceeded — surfaced to user |

## 7. Enums

```
{EntityStatus}:
  {STATE_1}, {STATE_2}, {STATE_3}, {TERMINAL}
```

## 8. Local Migration Scripts

| Script | Purpose |
|---|---|
| V001__{desc} | Create {entity_a} table + indexes |
| V002__{desc} | Create {entity_b} table + indexes |
| V003__{desc} | Create sync_outbox table |

Use the framework's migration mechanism (WatermelonDB schema migrations /
Room `Migration` / Realm schema versioning) — never destructive migrations
that drop user data without an export/warning step.

## 9. Data Dictionary

| Field | Business Meaning |
|---|---|
| id | Unique local/system identifier — may be client-generated UUID until first sync |
| status | Current lifecycle state of the entity |
| is_dirty | Indicates an unsynced local change exists |
| {field} | {business meaning} |

## 10. Data Classification & Privacy (SEC-7)

| Table/Key.Column | Classification | PII? | Encryption | Retention | Masking in Logs |
|---|---|---|---|---|---|
| {entity_a}.{field} | Public/Internal/Confidential/Restricted | Yes/No | At-rest: SQLCipher/Realm encryption / In-transit: TLS | {N days or "until logout"} | {mask pattern or "N/A"} |
| `{app}.session.refreshToken` (Keychain/Keystore) | Restricted | No (token, not identity data) | Keychain (iOS) / Keystore (Android) — hardware-backed where available | Until logout or expiry | Never log token value |
| {entity_b}.{field} | {classification} | Yes/No | {approach} | {policy} | {pattern} |

**Classification key:**
- Public — no restriction
- Internal — employees/contractors only
- Confidential — need-to-know (e.g. user-specific business data)
- Restricted — regulated PII/PCI/PHI/auth secrets — Keychain/Keystore-backed
  encryption + access audit mandatory

Any table/key marked PII = Yes must:
- Never appear in logs or crash reports (constitution Part 1 — Logging;
  investigation.md §1 scrubbing rules)
- Be cleared on logout (see §4 key-value store entries)
- Be listed in security-design.md §4 Regulatory/Compliance Trace

---

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |
