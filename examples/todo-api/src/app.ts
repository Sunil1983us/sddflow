// Wires together Auth Middleware -> Scope Middleware -> Tasks Router,
// matching the Component Diagram in .specify/features/task-management/hld.md.

import express, { Express } from 'express';
import { authMiddleware } from './middleware/auth.middleware';
import { userScopeMiddleware } from './middleware/user-scope.middleware';
import { tasksRouter } from './routes/tasks.routes';

export function createApp(): Express {
  const app = express();
  app.use(express.json());
  app.use('/tasks', authMiddleware, userScopeMiddleware, tasksRouter);
  return app;
}
