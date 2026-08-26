// Wires together Auth Middleware -> Scope Middleware -> Tasks Router,
// matching the Component Diagram in .specify/features/task-management/hld.md.

import express, { Express } from 'express';
import rateLimit from 'express-rate-limit';
import { authMiddleware } from './middleware/auth.middleware';
import { userScopeMiddleware } from './middleware/user-scope.middleware';
import { tasksRouter } from './routes/tasks.routes';

// CodeQL js/missing-rate-limiting: an unbounded route accepts as many
// requests as a client can send, making it a cheap DoS vector and (for
// authMiddleware's JWT check specifically) a cheap way to brute-force
// tokens. windowMs/max are deliberately generous defaults for a worked
// example -- tune per deployment, not a value this example can know.
const tasksRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  limit: 300, // per IP, per window
  standardHeaders: true, // RateLimit-* response headers
  legacyHeaders: false, // no deprecated X-RateLimit-* headers
});

export function createApp(): Express {
  const app = express();
  app.use(express.json());
  app.use('/tasks', tasksRateLimiter, authMiddleware, userScopeMiddleware, tasksRouter);
  return app;
}
