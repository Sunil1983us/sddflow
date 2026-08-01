// TASK-003 — POST /tasks Endpoint
// Satisfies: FR-001, FR-002 | Gate: UC-001 (srd.md)

import { Router } from 'express';
import type { Task } from '@prisma/client';
import { createTaskSchema } from '../schemas/task.schema';
import { createTask } from '../services/task.service';

export const tasksRouter = Router();

function serializeTask(task: Task) {
  return {
    id: task.id,
    title: task.title,
    description: task.description,
    due_date: task.dueDate,
    priority: task.priority,
    status: task.status,
    created_at: task.createdAt,
    updated_at: task.updatedAt,
  };
}

tasksRouter.post('/', async (req, res, next) => {
  const parsed = createTaskSchema.safeParse(req.body);
  if (!parsed.success) {
    const message = parsed.error.issues[0]?.message ?? 'invalid request body';
    res.status(400).json({ error: message });
    return;
  }

  try {
    const task = await createTask(parsed.data);
    res.status(201).json(serializeTask(task));
  } catch (err) {
    next(err);
  }
});
