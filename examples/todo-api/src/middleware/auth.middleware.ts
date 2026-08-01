// Auth Middleware — verifies the JWT from the (out-of-scope) Auth Service.
// See .specify/features/task-management/hld.md — "Auth Middleware (JWT verify)"
//
// Simplification vs. context.md's Tech Stack row ("JWT RS256, public key
// from env"): this worked example signs/verifies with HS256 and a shared
// secret so the example is runnable standalone, without standing up a
// second Auth Service to mint RS256 tokens. A real deployment of this pack
// would follow constitution.md's finalized Tech Stack row instead.

import { NextFunction, Request, Response } from 'express';
import jwt from 'jsonwebtoken';

export interface AuthenticatedRequest extends Request {
  userId?: string;
}

export function authMiddleware(req: AuthenticatedRequest, res: Response, next: NextFunction): void {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) {
    res.status(401).json({ error: 'unauthorized' });
    return;
  }

  const token = header.slice('Bearer '.length);
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET as string) as jwt.JwtPayload;
    if (typeof payload.sub !== 'string' || payload.sub.length === 0) {
      res.status(401).json({ error: 'unauthorized' });
      return;
    }
    req.userId = payload.sub;
    next();
  } catch {
    res.status(401).json({ error: 'unauthorized' });
  }
}
