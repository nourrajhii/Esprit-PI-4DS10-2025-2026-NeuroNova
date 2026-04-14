import { type Request, type Response, type NextFunction } from 'express'
import { PERMISSIONS, type UserRole } from '../config/rbac.js'

function normalizeRole(role: string | undefined): UserRole | null {
  const r = String(role ?? '')
  if (
    r === 'individual_investor' ||
    r === 'professional_investor' ||
    r === 'real_estate_agency' ||
    r === 'developer_fund'
  ) {
    return r as UserRole
  }
  return null
}

export function requireRole(allowed: UserRole[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    const role = normalizeRole(req.user?.role)
    if (!role || !allowed.includes(role)) {
      res.status(403).json({ error: 'Forbidden' })
      return
    }
    next()
  }
}

export function requireOnePermission<K extends keyof typeof PERMISSIONS>(key: K) {
  return requireRole(PERMISSIONS[key])
}

