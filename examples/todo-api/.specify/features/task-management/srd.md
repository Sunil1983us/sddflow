# Software Requirements Document
## Feature: Task Management
## Project: Todo API | Scope: Pilot | Version: 1.0

---

## Functional Requirements

| ID | Requirement | Priority | Satisfies |
|---|---|---|---|
| FR-001 | System shall allow an authenticated user to create a task with: title (required, ≤ 200 chars), description (optional, ≤ 2000 chars), due_date (optional, must not be in the past), priority (low/medium/high, defaults medium) | HIGH | BR-001, BR-002, BR-003 |
| FR-002 | System shall return the created task including server-assigned id, created_at, and status=open | HIGH | BR-001 |
| FR-003 | System shall allow an authenticated user to list their tasks with optional filters: status, priority, sort (due_date asc/desc, created_at desc) | HIGH | BR-001 |
| FR-004 | System shall paginate task lists using cursor-based pagination; default page size 20, max 100 | MEDIUM | BR-006 |
| FR-005 | System shall allow an authenticated user to update title, description, due_date, priority, or status on any of their own tasks | HIGH | BR-001, BR-002, BR-003 |
| FR-006 | System shall allow an authenticated user to delete (soft-delete) any of their own tasks | HIGH | BR-001 |
| FR-007 | System shall enforce strict user-scoping: any request targeting a task not owned by the authenticated user returns HTTP 404 (not 403, to avoid enumeration) | CRITICAL | BR-004 |
| FR-008 | System shall retain tasks with status=done for 90 days; a background job purges them after that | LOW | BR-005 |

---

## Non-Functional Requirements

| ID | Requirement | Measurement |
|---|---|---|
| NFR-001 | p95 response time ≤ 200 ms at 100 concurrent users for all task endpoints | Measured in load test (k6) in staging |
| NFR-002 | API availability ≥ 99.9% monthly (≤ 43 min downtime/month) | Uptime monitoring (Pingdom or equivalent) |
| NFR-003 | All inputs sanitised; OWASP API Security Top 10 (2023) compliance | SAST scan (Semgrep) in CI; pen-test before launch |
| NFR-004 | No PII logged; all log lines include request_id and user_id (hashed) | Log audit in code review |

---

## Use Cases

### UC-001 — Create Task

**Actor:** Registered User  
**Pre-condition:** User has a valid JWT in the Authorization header.

| Step | Given | When | Then |
|---|---|---|---|
| Happy path | Authenticated user, valid payload | POST /tasks with `{title, priority: "high", due_date: "2026-12-31"}` | 201 Created; response body contains task with id, status=open, created_at |
| Missing title | Authenticated user | POST /tasks with `{}` | 400 Bad Request; body `{error: "title is required"}` |
| Past due date | Authenticated user | POST /tasks with `{title: "x", due_date: "2020-01-01"}` | 400 Bad Request; body `{error: "due_date cannot be in the past"}` |
| Unauthenticated | No/invalid JWT | POST /tasks | 401 Unauthorized |

---

### UC-002 — List Tasks

**Actor:** Registered User  
**Pre-condition:** User is authenticated.

| Step | Given | When | Then |
|---|---|---|---|
| Default list | User has 5 tasks | GET /tasks | 200 OK; array of ≤ 20 tasks, next_cursor if more |
| Status filter | User has open and done tasks | GET /tasks?status=done | 200 OK; only done tasks returned |
| Priority filter | User has mixed-priority tasks | GET /tasks?priority=high | 200 OK; only high-priority tasks |
| Empty list | User has no tasks | GET /tasks | 200 OK; `{data: [], next_cursor: null}` |
| Another user's tasks | User A authenticated | GET /tasks | 200 OK; User B's tasks never appear |

---

### UC-003 — Update Task

**Actor:** Registered User  
**Pre-condition:** User is authenticated; task exists.

| Step | Given | When | Then |
|---|---|---|---|
| Mark complete | User owns TASK-X, status=open | PATCH /tasks/TASK-X `{status: "done"}` | 200 OK; task returned with status=done, completed_at set |
| Update title | User owns TASK-X | PATCH /tasks/TASK-X `{title: "new title"}` | 200 OK; task returned with updated title |
| Other user's task | User A authenticated | PATCH /tasks/{User B's task id} | 404 Not Found |
| Invalid status | User owns TASK-X | PATCH /tasks/TASK-X `{status: "invalid"}` | 400 Bad Request |

---

### UC-004 — Delete Task

**Actor:** Registered User  
**Pre-condition:** User is authenticated; task exists.

| Step | Given | When | Then |
|---|---|---|---|
| Soft delete own | User owns TASK-X | DELETE /tasks/TASK-X | 204 No Content; task archived (not removed from DB) |
| Deleted task invisible | Task was soft-deleted | GET /tasks | Archived task does not appear |
| Other user's task | User A authenticated | DELETE /tasks/{User B's task id} | 404 Not Found |

---

## Assumptions

| ID | Assumption | Raised by | Status |
|---|---|---|---|
| [ASSUMPTION-001] | Cursor-based pagination is acceptable (not offset). Cursor is an opaque base64-encoded timestamp+id. | Tech Lead | RESOLVED — confirmed in /clarify |
| [ASSUMPTION-002] | Rate limit of 300 req/min per authenticated user. Enforced at API gateway level. | Tech Lead | RESOLVED — confirmed in /clarify |
