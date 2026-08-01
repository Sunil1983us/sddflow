// TASK-003 — POST /tasks Endpoint (domain logic half)
// Satisfies: FR-001, FR-002

import type { Prisma } from '@prisma/client';
import { prisma } from '../lib/prisma';
import { CreateTaskInput } from '../schemas/task.schema';

// Prisma's generated types require `userId` on TaskCreateInput because they
// don't know about the runtime extension in src/lib/prisma.ts that injects
// it from AsyncLocalStorage on every create() call. The cast below is the
// documented seam between that static type and the actual runtime contract
// — there is still no code path here where a caller could set another
// user's id, since userId is never accepted as an argument to this function.
type ScopedTaskCreateData = Omit<Prisma.TaskUncheckedCreateInput, 'userId'>;

export async function createTask(input: CreateTaskInput) {
  const data: ScopedTaskCreateData = {
    title: input.title,
    description: input.description,
    dueDate: input.due_date ? new Date(input.due_date) : undefined,
    priority: input.priority,
  };
  return prisma.task.create({ data: data as unknown as Prisma.TaskUncheckedCreateInput });
}
