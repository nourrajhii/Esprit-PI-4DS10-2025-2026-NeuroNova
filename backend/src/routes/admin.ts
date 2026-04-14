import { Router } from 'express'
import { z } from 'zod'
import { requireAuth } from '../middleware/auth.js'
import { requireAdmin } from '../middleware/requireAdmin.js'
import { prisma } from '../prisma.js'

export function createAdminRouter() {
  const router = Router()

  router.use(requireAuth, requireAdmin)

  router.get('/users', async (_req, res) => {
    const users = await prisma.user.findMany({
      select: { id: true, email: true, name: true, role: true, createdAt: true },
      orderBy: { createdAt: 'desc' },
    })
    res.json({ users })
  })

  const roleSchema = z.enum([
    'individual_investor',
    'professional_investor',
    'real_estate_agency',
    'developer_fund',
  ])

  router.patch('/users/:userId/role', async (req, res) => {
    const userId = String(req.params.userId)
    const body = roleSchema.safeParse(req.body?.role)
    if (!body.success) {
      res.status(400).json({ error: body.error.flatten() })
      return
    }

    const updated = await prisma.user.update({
      where: { id: userId },
      data: { role: body.data },
      select: { id: true, email: true, name: true, role: true },
    })

    res.json({ user: updated })
  })

  router.get('/listings/:listingId/revisions', async (req, res) => {
    const listingId = String(req.params.listingId)
    const revisions = await prisma.listingRevision.findMany({
      where: { listingId },
      include: {
        actor: { select: { id: true, name: true, email: true, role: true } },
      },
      orderBy: { createdAt: 'desc' },
    })

    res.json({ revisions })
  })

  return router
}

