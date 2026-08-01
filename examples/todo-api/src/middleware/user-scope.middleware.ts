// TASK-002 — User-Scope Prisma Middleware (request-wiring half)
// Runs after auth.middleware.ts. Opens the AsyncLocalStorage context that
// src/lib/prisma.ts's scopeTaskOperation() reads for the rest of this request.

import { NextFunction, Response } from 'express';
import { requestContext } from '../lib/request-context';
import { AuthenticatedRequest } from './auth.middleware';

export function userScopeMiddleware(req: AuthenticatedRequest, res: Response, next: NextFunction): void {
  if (!req.userId) {
    // Defensive only — auth.middleware always runs first and either sets
    // req.userId or responds 401 itself before this middleware is reached.
    res.status(401).json({ error: 'unauthorized' });
    return;
  }
  requestContext.run({ userId: req.userId }, next);
}
