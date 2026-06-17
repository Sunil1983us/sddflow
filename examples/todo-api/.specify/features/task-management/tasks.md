# Task Breakdown
## Feature: Task Management
## Project: Todo API | Run by: /task

---

## TASK-001 — Prisma Schema + Migration

**Story:** STORY-001 (Create a Task)  
**Satisfies:** FR-001, FR-002  
**Estimate:** ~50 lines (schema) + ~30 lines (migration)

**Description:**  
Define the `tasks` table in `prisma/schema.prisma`. Add enum types for `Priority` and `Status`. Write and apply initial migration.

**Acceptance Criteria:**
- [ ] `tasks` table created with all columns from HLD data model
- [ ] Enums: `Priority { low medium high }`, `Status { open in_progress done }`
- [ ] Migration runs clean on a fresh PostgreSQL 16 instance
- [ ] `prisma generate` produces TypeScript types

**Definition of Done:** Migration committed; `npx prisma migrate dev` passes locally.

---

## TASK-002 — User-Scope Prisma Middleware

**Story:** STORY-005 (Data Isolation)  
**Satisfies:** FR-007  
**Estimate:** ~60 lines

**Description:**  
Implement Prisma client extension that reads `user_id` from `AsyncLocalStorage` and appends `WHERE user_id = $user_id` to all `Task` model operations. Write unit tests with mock Prisma client.

**Acceptance Criteria:**
- [ ] Extension registered in `src/lib/prisma.ts`
- [ ] AsyncLocalStorage set by `user-scope.middleware.ts` after JWT validation
- [ ] Unit test: `findMany` without ALS user_id throws an error
- [ ] Unit test: `findMany` with ALS user_id appends correct filter

**Definition of Done:** Unit tests pass; `jest --testPathPattern user-scope` green.

---

## TASK-003 — POST /tasks Endpoint

**Story:** STORY-001  
**Satisfies:** FR-001, FR-002  
**Estimate:** ~80 lines (route + service + tests)

**Description:**  
Implement `POST /tasks`. Route validates body with Zod (title required, due_date not past, priority enum). Calls `TaskService.createTask()`. Returns 201 with created task.

**Acceptance Criteria:**
- [ ] UC-001 happy path passes integration test (Supertest)
- [ ] Missing title → 400 with `{error: "title is required"}`
- [ ] Past due_date → 400 with `{error: "due_date cannot be in the past"}`
- [ ] Title > 200 chars → 400
- [ ] No JWT → 401

**Definition of Done:** Integration tests pass; `jest --testPathPattern tasks.routes` green.

---

## TASK-004 — GET /tasks Endpoint (Basic)

**Story:** STORY-002  
**Satisfies:** FR-003  
**Estimate:** ~70 lines

**Description:**  
Implement `GET /tasks` returning user's non-archived tasks sorted by `created_at DESC`. No pagination yet (added in TASK-008). Supports `?status=` and `?priority=` query filters.

**Acceptance Criteria:**
- [ ] UC-002 happy path (default list) passes
- [ ] Status filter returns only matching tasks
- [ ] Priority filter returns only matching tasks
- [ ] Tasks from another user never appear

**Definition of Done:** Integration tests pass.

---

## TASK-005 — PATCH /tasks/:id Endpoint

**Story:** STORY-003  
**Satisfies:** FR-005, FR-007  
**Estimate:** ~70 lines

**Description:**  
Implement `PATCH /tasks/:id`. Accepts partial updates for title, description, due_date, priority, status. Sets `completed_at` when status changes to `done`. Scoped by user-middleware (wrong user → 404).

**Acceptance Criteria:**
- [ ] UC-003 happy path passes
- [ ] Marking done sets `completed_at`
- [ ] Another user's task → 404
- [ ] Invalid status → 400

**Definition of Done:** Integration tests pass.

---

## TASK-006 — DELETE /tasks/:id Endpoint

**Story:** STORY-004  
**Satisfies:** FR-006, FR-007  
**Estimate:** ~40 lines

**Description:**  
Implement `DELETE /tasks/:id`. Sets `archived = true` (soft-delete). Returns 204. Scoped by user-middleware.

**Acceptance Criteria:**
- [ ] Returns 204 on success
- [ ] Task no longer appears in GET /tasks after delete
- [ ] Another user's task → 404

**Definition of Done:** Integration tests pass.

---

## TASK-007 — Auth + User-Scope Middleware Wiring

**Story:** STORY-005  
**Satisfies:** FR-007  
**Estimate:** ~50 lines

**Description:**  
Wire `auth.middleware.ts` (JWT RS256 verify using public key from env) and `user-scope.middleware.ts` (sets AsyncLocalStorage) into the Express app before the tasks router. Add integration test that a request with invalid JWT returns 401.

**Acceptance Criteria:**
- [ ] Valid JWT → user_id available in ALS throughout request lifecycle
- [ ] Invalid JWT → 401
- [ ] Expired JWT → 401
- [ ] Missing Authorization header → 401

**Definition of Done:** Integration tests pass.

---

## TASK-008 — Cursor-Based Pagination

**Story:** STORY-002  
**Satisfies:** FR-004  
**Estimate:** ~80 lines (util + route update + tests)

**Description:**  
Implement `src/utils/cursor.ts` (encode/decode base64 JSON cursor of `{created_at, id}`). Update `GET /tasks` to accept `?cursor=` and return `{data: Task[], next_cursor: string | null}`.

**Acceptance Criteria:**
- [ ] Second page via cursor returns next 20 tasks, not repeating previous
- [ ] Last page returns `next_cursor: null`
- [ ] Invalid cursor → 400
- [ ] Cursor round-trips through encode→decode unchanged

**Definition of Done:** Integration tests pass; `cursor.ts` has unit tests.

---

## TASK-009 — Input Validation + Error Handling

**Story:** STORY-001, STORY-003  
**Satisfies:** FR-001, NFR-003  
**Estimate:** ~60 lines

**Description:**  
Centralise Zod validation schemas in `src/utils/validation.ts`. Add global Express error handler that formats Zod errors as `{error: string, details: []}` and Prisma errors as `{error: "not found"}`. Ensure no stack traces leak in production.

**Acceptance Criteria:**
- [ ] Zod validation errors return 400 with human-readable message
- [ ] Unknown route returns 404
- [ ] Unhandled errors return 500 with no stack trace in NODE_ENV=production
- [ ] NFR-004: no PII in any log output (verified in unit test)

**Definition of Done:** Error handling tests pass; manual test confirms no stack leak.

---

## TASK-010 — 90-Day Purge SQL + Cron Script

**Story:** STORY-004 (retention)  
**Satisfies:** FR-008  
**Estimate:** ~30 lines

**Description:**  
Write `scripts/purge-done-tasks.sql` that deletes tasks where `status = 'done' AND completed_at < NOW() - INTERVAL '90 days'`. Write a Node.js wrapper `scripts/purge-done-tasks.ts` that runs the query, logs count of deleted rows, and emits a Prometheus counter `sdd_tasks_purged_total`. Platform team wires this to their cron service.

**Acceptance Criteria:**
- [ ] Script deletes only tasks > 90 days old with status=done
- [ ] Script logs `{event: "purge_complete", deleted_count: N}` as structured JSON
- [ ] Counter `sdd_tasks_purged_total` emitted (verified in unit test with mock)
- [ ] Script is idempotent (running twice doesn't error)

**Definition of Done:** Unit test passes; script reviewed by DevOps/SRE (Raj Patel).
