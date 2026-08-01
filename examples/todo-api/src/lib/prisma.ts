// TASK-002 — User-Scope Prisma Middleware
// Satisfies: FR-007 (strict user-scoping)
//
// Every Task-model operation is routed through scopeTaskOperation(), which
// reads user_id from AsyncLocalStorage (set by user-scope.middleware.ts
// after JWT verification) and either injects it into create() payloads or
// appends it to the where clause of every read/update/delete. There is no
// code path in this app that can read or write another user's tasks.

import { PrismaClient } from '@prisma/client';
import { getUserId } from './request-context';

// Operations where the scope filter belongs in `where`, not `data`.
const WHERE_SCOPED_OPERATIONS = new Set([
  'findMany',
  'findFirst',
  'findFirstOrThrow',
  'findUnique',
  'findUniqueOrThrow',
  'update',
  'updateMany',
  'delete',
  'deleteMany',
  'count',
  'aggregate',
]);

type PrismaArgs = Record<string, unknown>;
type PrismaQuery = (args: PrismaArgs) => Promise<unknown>;

// Exported standalone (not just wired into $extends) so it's unit-testable
// against a fake `query` function without a live database or generated
// Prisma client — see tests/unit/user-scope.test.ts.
export async function scopeTaskOperation(
  operation: string,
  args: PrismaArgs,
  query: PrismaQuery,
): Promise<unknown> {
  const userId = getUserId(); // throws if no request-scoped user_id is set

  if (operation === 'create') {
    args.data = { ...(args.data as object), userId };
  } else if (WHERE_SCOPED_OPERATIONS.has(operation)) {
    args.where = { ...(args.where as object), userId };
  }

  return query(args);
}

const basePrisma = new PrismaClient();

export const prisma = basePrisma.$extends({
  name: 'user-scope',
  query: {
    task: {
      async $allOperations({ operation, args, query }) {
        return scopeTaskOperation(operation, args as PrismaArgs, query as PrismaQuery);
      },
    },
  },
});
