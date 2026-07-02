# Use Case Specification — Task Management
# Feature: task-management
> Version: 1.0 | Status: Approved | Date: 2026-05-12 | Author: Maya (Business Analyst)

---

## References
| Source | Sections / IDs Used |
|---|---|
| brd.md | BR-001 – BR-006, BO-001, BO-002 |
| context.md | Actors, key flows, API surface |

---

## 1. Actors

| ID | Actor | Type | Description |
|---|---|---|---|
| ACT-001 | Registered User | Human (via web client / API) | Authenticated free-tier or paid user managing their personal tasks |
| ACT-002 | Retention Job | System | Scheduled background job that purges done tasks older than 90 days (BR-005) |

---

## 2. Use Cases

### UC-001 — Create Task

**Actor:** ACT-001 Registered User
**Goal:** Capture a new task with title, optional description, due date, and priority
**Pre-condition:** User has a valid JWT in the Authorization header
**Trace:** BR-001, BR-002, BR-003

**Main Path (MP):**
1. User submits POST /tasks with `{title, description?, due_date?, priority?}`
2. System validates: title required ≤ 200 chars, description ≤ 2000 chars, due_date not in the past, priority in low/medium/high (defaults medium)
3. System persists the task scoped to the authenticated user
4. System returns 201 Created with id, status=open, created_at

**Alternate Paths:**
- AP-1-1: No priority supplied → task created with priority=medium
- AP-1-2: No due_date supplied → task created without a due date

**Exception Paths:**
- EP-1-1: Missing title → 400 Bad Request `{error: "title is required"}`
- EP-1-2: due_date in the past → 400 Bad Request `{error: "due_date cannot be in the past"}`
- EP-1-3: Missing/invalid JWT → 401 Unauthorized

**Independent Test:** Create a task with only a title; verify 201, status=open, priority=medium, and that it appears in GET /tasks.

---

### UC-002 — List Tasks

**Actor:** ACT-001 Registered User
**Goal:** View own tasks, filtered and sorted, with pagination
**Pre-condition:** User is authenticated
**Trace:** BR-001, BR-004, BR-006

**Main Path (MP):**
1. User submits GET /tasks (optional filters: status, priority; sort: due_date asc/desc, created_at desc)
2. System returns 200 OK with up to 20 of the user's own tasks and next_cursor when more exist

**Alternate Paths:**
- AP-2-1: status filter → only matching tasks returned
- AP-2-2: priority filter → only matching tasks returned
- AP-2-3: User has no tasks → 200 OK `{data: [], next_cursor: null}`

**Exception Paths:**
- EP-2-1: Missing/invalid JWT → 401 Unauthorized
- EP-2-2: Page size requested above 100 → clamped to 100 (no error)

**Independent Test:** Seed tasks for two users; verify User A's list never contains User B's tasks (BR-004).

---

### UC-003 — Update Task

**Actor:** ACT-001 Registered User
**Goal:** Modify title, description, due_date, priority, or status of an owned task
**Pre-condition:** User is authenticated; task exists and is owned by the user
**Trace:** BR-001, BR-002, BR-003, BR-004

**Main Path (MP):**
1. User submits PATCH /tasks/{id} with any updatable fields
2. System validates fields (same rules as UC-001; status in open/done)
3. System persists changes; setting status=done stamps completed_at
4. System returns 200 OK with the updated task

**Alternate Paths:**
- AP-3-1: status=done → completed_at set; task enters the 90-day retention window (BR-005)

**Exception Paths:**
- EP-3-1: Task owned by another user → 404 Not Found (not 403 — avoids id enumeration)
- EP-3-2: Invalid status value → 400 Bad Request
- EP-3-3: Missing/invalid JWT → 401 Unauthorized

**Independent Test:** PATCH status=done on an owned task; verify 200, completed_at present; PATCH another user's task id; verify 404.

---

### UC-004 — Delete Task

**Actor:** ACT-001 Registered User
**Goal:** Remove an owned task from active use (soft delete)
**Pre-condition:** User is authenticated; task exists and is owned by the user
**Trace:** BR-001, BR-004, BR-005

**Main Path (MP):**
1. User submits DELETE /tasks/{id}
2. System soft-deletes (archives) the task — the row is retained in the database
3. System returns 204 No Content

**Alternate Paths:**
- AP-4-1: Subsequent GET /tasks → archived task does not appear

**Exception Paths:**
- EP-4-1: Task owned by another user → 404 Not Found
- EP-4-2: Missing/invalid JWT → 401 Unauthorized

**Independent Test:** Delete an owned task; verify 204, task absent from list, row still present in DB with archived flag.

---

### UC-005 — Purge Expired Done Tasks

**Actor:** ACT-002 Retention Job
**Goal:** Permanently remove done tasks older than 90 days
**Pre-condition:** Scheduled trigger fires (daily)
**Trace:** BR-005

**Main Path (MP):**
1. Job selects tasks with status=done and completed_at older than 90 days
2. Job hard-deletes the selected rows in batches
3. Job logs the purge count

**Exception Paths:**
- EP-5-1: Database unavailable → job aborts, logs error, retries on next schedule (no partial state)

**Independent Test:** Seed a done task with completed_at = 91 days ago; run the job; verify the row is removed and the purge is logged.

---

## 3. Approvals

| Role | Status | Date |
|---|---|---|
| Business Analyst | Approved | 2026-05-12 |
| Product Owner | Approved | 2026-05-12 |

## Version History

| Version | Date | Command | Change | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-05-12 | /specify-uc | Initial use case specification | Product Owner |
