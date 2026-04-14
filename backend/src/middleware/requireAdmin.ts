import { type Request, type Response, type NextFunction } from 'express'
import { prisma } from '../prisma.js'

function parseAdminEmails(): string[] {
  const raw = process.env.ADMIN_EMAILS ?? ''
  return raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
}

export async function requireAdmin(req: Request, res: Response, next: NextFunction) {
  try {
    const user = req.user
    if (!user) {
      res.status(401).json({ error: 'Unauthorized' })
      return
    }

    const adminEmails = parseAdminEmails()
    if (adminEmails.length > 0) {
      const dbUser = await prisma.user.findUnique({ where: { id: user.id }, select: { email: true } })
      if (!dbUser || !adminEmails.includes(dbUser.email)) {
        res.status(403).json({ error: 'Forbidden' })
        return
      }
      next()
      return
    }

    // Fallback: for demo/prototype, use developer_fund as admin if ADMIN_EMAILS is not set.
    if (user.role !== 'developer_fund') {
      res.status(403).json({ error: 'Forbidden' })
      return
    }

    next()
  } catch {
    res.status(500).json({ error: 'Admin check failed' })
  }
}

