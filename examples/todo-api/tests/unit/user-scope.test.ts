// TASK-002 — User-Scope Prisma Middleware — unit tests
// Definition of Done: `jest --testPathPattern user-scope` green.
//
// Tests scopeTaskOperation() directly against a fake `query` function, so
// this suite needs no live database and no generated Prisma client.

import { requestContext } from '../../src/lib/request-context';
import { scopeTaskOperation } from '../../src/lib/prisma';

describe('scopeTaskOperation', () => {
  it('findMany without ALS user_id throws an error', async () => {
    const query = jest.fn();

    await expect(scopeTaskOperation('findMany', {}, query)).rejects.toThrow(
      /No user-scope context set/,
    );
    expect(query).not.toHaveBeenCalled();
  });

  it('findMany with ALS user_id appends the correct filter', async () => {
    const query = jest.fn().mockResolvedValue([]);

    await requestContext.run({ userId: 'user-123' }, async () => {
      await scopeTaskOperation('findMany', { where: { status: 'open' } }, query);
    });

    expect(query).toHaveBeenCalledWith({ where: { status: 'open', userId: 'user-123' } });
  });

  it('create() injects user_id into data instead of filtering where', async () => {
    const query = jest.fn().mockResolvedValue({});

    await requestContext.run({ userId: 'user-456' }, async () => {
      await scopeTaskOperation('create', { data: { title: 'x' } }, query);
    });

    expect(query).toHaveBeenCalledWith({ data: { title: 'x', userId: 'user-456' } });
  });

  it('create() without ALS user_id throws before calling query', async () => {
    const query = jest.fn();

    await expect(scopeTaskOperation('create', { data: { title: 'x' } }, query)).rejects.toThrow();
    expect(query).not.toHaveBeenCalled();
  });

  it('two concurrent requests never leak user_id across each other', async () => {
    const seenFilters: unknown[] = [];
    const query = jest.fn(async (args: Record<string, unknown>) => {
      seenFilters.push(args.where);
      return [];
    });

    await Promise.all([
      requestContext.run({ userId: 'user-A' }, () =>
        scopeTaskOperation('findMany', { where: {} }, query),
      ),
      requestContext.run({ userId: 'user-B' }, () =>
        scopeTaskOperation('findMany', { where: {} }, query),
      ),
    ]);

    expect(seenFilters).toContainEqual({ userId: 'user-A' });
    expect(seenFilters).toContainEqual({ userId: 'user-B' });
  });
});
