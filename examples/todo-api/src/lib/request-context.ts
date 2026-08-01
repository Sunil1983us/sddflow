// TASK-002 — User-Scope Prisma Middleware (context half)
// See .specify/features/task-management/hld.md — "Scope Middleware\n(AsyncLocalStorage user_id)"

import { AsyncLocalStorage } from 'node:async_hooks';

export interface RequestContext {
  userId: string;
}

export const requestContext = new AsyncLocalStorage<RequestContext>();

export function getUserId(): string {
  const store = requestContext.getStore();
  if (!store) {
    throw new Error(
      'No user-scope context set — this Task query ran outside requestContext.run(). ' +
        'user-scope.middleware.ts must wrap every authenticated request.',
    );
  }
  return store.userId;
}
