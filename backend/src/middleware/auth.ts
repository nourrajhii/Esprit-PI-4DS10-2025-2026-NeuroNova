import { type Request, type Response, type NextFunction } from 'express'
import { verifyAccessToken } from '../utils/jwt.js'

export type AuthUser = {
  id: string
  role: string
}

export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const header = req.header('authorization') || ''
  const [type, token] = header.split(' ')
  if (type !== 'Bearer' || !token) {
    res.status(401).json({ error: 'Unauthorized' })
    return
  }

  try {
    const decoded = verifyAccessToken(token)
    req.user = { id: decoded.sub, role: decoded.role } as AuthUser
    next()
  } catch {
    res.status(401).json({ error: 'Unauthorized' })
  }
}

// Express type augmentation
declare global {
  namespace Express {
    interface Request {
      user?: AuthUser
    }
  }
}

