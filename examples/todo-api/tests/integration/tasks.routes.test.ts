// TASK-003 — POST /tasks Endpoint — integration tests
// Definition of Done: `jest --testPathPattern tasks.routes` green.
// Exercises the real Express app against a real PostgreSQL database.

import request from 'supertest';
import jwt from 'jsonwebtoken';
import { createApp } from '../../src/app';
import { prisma } from '../../src/lib/prisma';

const app = createApp();

function tokenFor(userId: string): string {
  return jwt.sign({ sub: userId }, process.env.JWT_SECRET as string, { expiresIn: '1h' });
}

beforeEach(async () => {
  // Raw SQL bypasses the user-scope Prisma extension entirely — the only
  // place in this codebase that does, and only for test housekeeping.
  await prisma.$executeRaw`DELETE FROM tasks`;
});

afterAll(async () => {
  await prisma.$disconnect();
});

describe('POST /tasks (UC-001)', () => {
  it('happy path: creates a task and returns 201 with status=open', async () => {
    const res = await request(app)
      .post('/tasks')
      .set('Authorization', `Bearer ${tokenFor('user-1')}`)
      .send({ title: 'Ship the demo', priority: 'high', due_date: '2026-12-31' });

    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({
      title: 'Ship the demo',
      priority: 'high',
      status: 'open',
    });
    expect(res.body.id).toEqual(expect.any(String));
    expect(res.body.created_at).toBeDefined();
  });

  it('missing title -> 400 {error: "title is required"}', async () => {
    const res = await request(app)
      .post('/tasks')
      .set('Authorization', `Bearer ${tokenFor('user-1')}`)
      .send({});

    expect(res.status).toBe(400);
    expect(res.body).toEqual({ error: 'title is required' });
  });

  it('past due_date -> 400 {error: "due_date cannot be in the past"}', async () => {
    const res = await request(app)
      .post('/tasks')
      .set('Authorization', `Bearer ${tokenFor('user-1')}`)
      .send({ title: 'x', due_date: '2020-01-01' });

    expect(res.status).toBe(400);
    expect(res.body).toEqual({ error: 'due_date cannot be in the past' });
  });

  it('title over 200 chars -> 400', async () => {
    const res = await request(app)
      .post('/tasks')
      .set('Authorization', `Bearer ${tokenFor('user-1')}`)
      .send({ title: 'x'.repeat(201) });

    expect(res.status).toBe(400);
  });

  it('no JWT -> 401', async () => {
    const res = await request(app).post('/tasks').send({ title: 'x' });
    expect(res.status).toBe(401);
  });

  it('invalid JWT -> 401', async () => {
    const res = await request(app)
      .post('/tasks')
      .set('Authorization', 'Bearer not-a-real-token')
      .send({ title: 'x' });
    expect(res.status).toBe(401);
  });

  it('defaults priority to medium and status to open when omitted', async () => {
    const res = await request(app)
      .post('/tasks')
      .set('Authorization', `Bearer ${tokenFor('user-1')}`)
      .send({ title: 'no priority given' });

    expect(res.status).toBe(201);
    expect(res.body.priority).toBe('medium');
    expect(res.body.status).toBe('open');
  });

  it('scopes created tasks to the authenticated user (FR-007)', async () => {
    await request(app)
      .post('/tasks')
      .set('Authorization', `Bearer ${tokenFor('user-A')}`)
      .send({ title: 'user A task' });

    const rows = await prisma.$queryRaw<{ user_id: string }[]>`SELECT user_id FROM tasks`;
    expect(rows).toHaveLength(1);
    expect(rows[0].user_id).toBe('user-A');
  });
});
