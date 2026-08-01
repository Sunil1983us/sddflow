// TASK-003 — POST /tasks Endpoint (validation half)
// Error messages match UC-001's exact acceptance table in srd.md verbatim.

import { z } from 'zod';

function isPastDate(dateStr: string): boolean {
  const due = new Date(dateStr);
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  return due.getTime() < startOfToday.getTime();
}

export const createTaskSchema = z
  .object({
    title: z
      .string({ required_error: 'title is required' })
      .min(1, 'title is required')
      .max(200, 'title must be at most 200 characters'),
    description: z.string().max(2000, 'description must be at most 2000 characters').optional(),
    due_date: z
      .string()
      .refine((s) => !Number.isNaN(Date.parse(s)), { message: 'due_date must be a valid date' })
      .optional(),
    priority: z.enum(['low', 'medium', 'high']).default('medium'),
  })
  .superRefine((data, ctx) => {
    if (data.due_date && isPastDate(data.due_date)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['due_date'],
        message: 'due_date cannot be in the past',
      });
    }
  });

export type CreateTaskInput = z.infer<typeof createTaskSchema>;
