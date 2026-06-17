# Context: task-management
# Project: Todo API

## What This Does
A REST API that lets authenticated users create, list, update, and delete personal
todo tasks. Tasks have a title, optional description, due date, and priority level
(low/medium/high). Each user sees only their own tasks. The API will be consumed by
a React web client (built separately).

## Actors
- **Registered User** — creates and manages their own tasks via the web client
- **System** — sends due-date reminder emails (out of scope for this feature)

## Key Flows
1. **Create task** — POST /tasks with title, optional description, due date, priority →
   returns created task with generated ID
2. **List tasks** — GET /tasks with optional ?status=&priority=&sort= filters →
   returns paginated task list (20 per page default)
3. **Update task** — PATCH /tasks/:id to change title, description, due date,
   priority, or status (open/in-progress/done)
4. **Delete task** — DELETE /tasks/:id; soft-delete (archived flag), not hard delete

## Integrations
- PostgreSQL 16 for persistence
- JWT from the existing Auth Service (shared secret, RS256)
- No external services for this feature

## Business Rules
- A user cannot read or modify another user's tasks (strict data isolation)
- Title is required; max 200 characters
- Description: optional; max 2000 characters
- Due date: optional; cannot be in the past on create
- Priority: low | medium | high (defaults to medium)
- Status: open | in-progress | done (defaults to open)
- Completed tasks (status=done) are retained for 90 days, then auto-purged

## Tech Stack
- Language: TypeScript 5.x
- Runtime: Node.js 20 LTS
- Framework: Express 4.x
- ORM: Prisma 5.x
- Database: PostgreSQL 16
- Auth: JWT (RS256, verified by middleware; public key from env)
- Testing: Jest + Supertest
- Build: tsc + esbuild
- CI: GitHub Actions

## Non-Functional Requirements
- p95 response time: < 200 ms under 100 concurrent users
- Availability: 99.9% monthly uptime
- Security: OWASP API Top 10 compliance; all inputs sanitised
- Data retention: done tasks purged after 90 days (cron job, separate service)

## Out of Scope
- Task sharing / collaboration between users
- File attachments
- Subtasks / nested tasks
- Reminder email sending (the trigger data is stored, dispatch is a separate service)
- Frontend implementation

## Open Questions
- Should pagination use cursor-based or offset-based approach?
  (Preference: cursor for consistency with future mobile client)
- What is the rate limit per user per minute?
  (Proposal: 300 req/min per user — needs Product Owner sign-off)
