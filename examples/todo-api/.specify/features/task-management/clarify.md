# Clarification Report
## Feature: Task Management
## Project: Todo API | Run by: /clarify

---

## Open Questions → Resolutions

| # | Question | Raised by | Answer | Answered by |
|---|---|---|---|---|
| Q-001 | Cursor vs offset pagination — which approach? | Tech Lead (context.md) | **Cursor-based.** Encode (created_at, id) as opaque base64. Rationale: consistent under concurrent inserts; aligns with planned mobile client. | Product Owner (Sarah Chen) |
| Q-002 | Rate limit: 300 req/min per user at API gateway? | Tech Lead (context.md) | **Confirmed: 300 req/min per user.** Enforce at gateway (Kong). Clients receive HTTP 429 with Retry-After header. | Product Owner (Sarah Chen) |
| Q-003 | Soft-delete visibility — should done+archived tasks appear in the list API at all? | Tech Lead | **No.** Archived (soft-deleted) tasks are invisible in GET /tasks. A future `/tasks/archive` endpoint is out of scope. | Product Owner (Sarah Chen) |
| Q-004 | Who is responsible for the 90-day purge cron job? | Tech Lead | **Platform team** will deploy a shared cron service. This feature provides the SQL logic (delete WHERE status=done AND completed_at < NOW() - INTERVAL '90 days' AND user_id = ...). | DevOps/SRE (Raj Patel) |

---

## Clarification Summary

All ASSUMPTION-NNN markers in srd.md are now RESOLVED. No open questions remain.

**Gate status: PASSED** — /plan-arch may proceed.

---

## clarify.summary.md

See `clarify.summary.md` for the AI-2 summary (used by downstream commands).
