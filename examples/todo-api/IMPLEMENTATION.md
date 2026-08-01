# Implementation Status

This worked example was originally spec-only: every SDD document existed
(BRD → Use Cases → SRD → HLD → `stories.md` → `tasks.md`) but no code did.
**TASK-001, TASK-002, and TASK-003** (of the 10 in `tasks.md`) are now
implemented for real — real TypeScript, a real PostgreSQL 16 database, a
real test suite, actually run and passing. TASK-004 through TASK-010
remain at the spec/task-breakdown stage, exactly as before.

This file, and the code it describes, exist purely to prove out what
`/implement` produces — see each pack's own `CLAUDE.md` for what that
command actually does in a real project.

## What's implemented

| Task | What | Files |
|---|---|---|
| TASK-001 | Prisma schema + migration | `prisma/schema.prisma`, `prisma/migrations/20260801180720_init/` |
| TASK-002 | User-scope Prisma extension (FR-007) | `src/lib/request-context.ts`, `src/lib/prisma.ts` |
| TASK-003 | `POST /tasks` endpoint (UC-001) | `src/routes/tasks.routes.ts`, `src/schemas/task.schema.ts`, `src/services/task.service.ts` |

Plus the minimum app scaffolding needed to make TASK-003 exercisable
end-to-end: `src/app.ts`, `src/server.ts`, `src/middleware/auth.middleware.ts`,
`src/middleware/user-scope.middleware.ts`.

## Two deliberate simplifications (both documented at the point of code, not hidden)

1. **JWT verification uses HS256 with a shared secret**, not the RS256 +
   public-key-from-env scheme `context.md`'s Tech Stack row and TASK-007
   specify. Verifying real RS256 tokens needs a real Auth Service (or a
   key pair + issuer) to mint them — out of scope for making TASK-003
   demonstrably work. See the comment at the top of
   `src/middleware/auth.middleware.ts`.
2. **The three partial indexes in `hld.md`'s "Key Indexes" section**
   (`WHERE archived = false`, `WHERE status = 'done' ...`) are not
   expressed in `prisma/schema.prisma` — Prisma's declarative schema DSL
   doesn't support partial indexes without an unstable preview feature.
   The migration has plain composite indexes instead (same columns, no
   `WHERE` predicate).

Neither simplification affects TASK-001/002/003's own acceptance
criteria — both are noted here so nobody mistakes this example for a
literal, unmodified implementation of `hld.md`.

## What this does *not* claim

- **TASK-007 is not done.** Its acceptance criteria (RS256 verification,
  expired-JWT handling) are broader than what TASK-003 needed to be
  testable — see `tasks.md`'s TASK-007 note.
- **No `/pre-review` or `/address-review` round is represented here.**
  There's no real reviewer for a maintainer-repo example; simulating one
  would read as staged. What's here is exactly what `/implement` +
  passing tests produce, nothing past that.
- **TASK-004 through TASK-010 are unimplemented.** GET/PATCH/DELETE
  endpoints, pagination, input-validation hardening beyond TASK-003's
  scope, and the purge cron script are still spec-only.

## Running it

```bash
cd examples/todo-api
npm install

# PostgreSQL 16 must be running locally (or point DATABASE_URL elsewhere)
cp .env.example .env        # edit if your local Postgres differs
npx prisma migrate dev      # applies prisma/migrations/, generates the client

npm test                    # runs both suites — 13 tests
npx tsc --noEmit            # confirms the build compiles clean
```

## Verified (this round)

- `npx tsc -p tsconfig.json --noEmit` — clean, no type errors
- `npx jest --testPathPattern user-scope` — 5/5 passing (TASK-002's stated DoD command)
- `npx jest --testPathPattern tasks.routes` — 8/8 passing (TASK-003's stated DoD command)
- `npx prisma migrate dev` — applied clean against a freshly created PostgreSQL 16 database
- All of the above run against a real, local PostgreSQL 16 instance — no mocked database layer anywhere except the AsyncLocalStorage-level unit tests in TASK-002, which are unit tests by design (see their own file header).
