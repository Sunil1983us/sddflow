# Architecture & Plan
## Feature: Task Management
## Project: Todo API | Run by: /plan-arch

---

## Architecture Decisions

### ADR-1 — Hexagonal Architecture with Service + Repository Layers

**Decision:** Implement TaskService (domain logic) and TaskRepository (data access) as separate classes. Express route handlers are thin adapters — they validate input, call TaskService, and format the response. No business logic in controllers.

**Rationale:** Keeps domain testable without a database; consistent with constitution.md Part 1 (hexagonal pattern).

**Consequence:** Adds one extra layer vs. a direct-to-DB controller, but enables unit-testing TaskService with mock repositories and integration-testing repositories independently.

---

### ADR-2 — Prisma Global User-Scope Middleware

**Decision:** Apply a Prisma client extension (middleware) that automatically appends `WHERE user_id = $current_user_id` to all Task queries. Individual service methods do not pass user_id explicitly — it's injected by the middleware.

**Rationale:** Eliminates the entire class of IDOR bugs caused by forgetting to filter by user. Satisfies FR-007 at the data layer, not application layer.

**Consequence:** Requires the authenticated user's ID to be available in Prisma context. Implemented via AsyncLocalStorage (Node.js built-in) — no global state.

---

### ADR-3 — Cursor-Based Pagination

**Decision:** Cursor encodes `(created_at ISO string, id UUID)` as base64 JSON. Client sends `?cursor=<token>` on subsequent pages.

**Rationale:** Stable under concurrent inserts (no offset drift). Confirmed in Q-001 during /clarify.

**Consequence:** Cannot jump to arbitrary pages. Acceptable for this use case.

---

## Component Map

```
src/
  routes/
    tasks.routes.ts          # Express router — input validation only
  services/
    task.service.ts          # Domain logic (TaskService)
  repositories/
    task.repository.ts       # Prisma data access (TaskRepository)
  middleware/
    auth.middleware.ts       # JWT verification
    user-scope.middleware.ts # Sets user_id in AsyncLocalStorage
  models/
    task.model.ts            # Prisma schema types + domain types
  utils/
    cursor.ts                # Encode/decode pagination cursor
    validation.ts            # Zod schemas for request bodies
```

---

## Plan

| Phase | Tasks | Estimate |
|---|---|---|
| 1 — Foundation | Prisma schema, migrations, user-scope middleware | TASK-001, TASK-002 |
| 2 — Core API | POST /tasks, GET /tasks, PATCH /tasks/:id, DELETE /tasks/:id | TASK-003 – TASK-007 |
| 3 — Hardening | Cursor pagination, input validation, error handling | TASK-008, TASK-009 |
| 4 — Purge logic | SQL + cron script for 90-day purge | TASK-010 |

**Total estimate:** ~8–10 days (1 sprint, solo developer).
