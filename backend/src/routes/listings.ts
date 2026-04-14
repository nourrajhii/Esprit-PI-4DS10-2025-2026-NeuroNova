import { Router } from 'express'
import { z } from 'zod'
import { requireAuth } from '../middleware/auth.js'
import { requireOnePermission } from '../middleware/requireRoles.js'
import { prisma } from '../prisma.js'

const listingType = z.enum(['apartment', 'house', 'studio', 'loft'])

const createListingSchema = z.object({
  title: z.string().min(2).max(200),
  city: z.string().min(2).max(100),
  price: z.number().int().positive(),
  currency: z.string().min(2).max(6).default('EUR'),
  rooms: z.number().int().positive(),
  areaM2: z.number().int().positive(),
  type: listingType,
  description: z.string().min(10).max(2000),
})

const updateListingSchema = createListingSchema.partial()

export function createListingsRouter() {
  const router = Router()

  router.get('/', async (req, res) => {
    const q = String(req.query.q ?? '').trim()
    const city = String(req.query.city ?? '').trim()
    const type = String(req.query.type ?? '').trim()
    const maxPrice = req.query.maxPrice ? Number(req.query.maxPrice) : undefined

    // Default: only published listings
    // If authenticated: include the user's listings as well (drafts/rejected)
    let userId: string | null = null
    const auth = String(req.header('authorization') ?? '')
    const m = auth.match(/^Bearer\s+(.+)$/)
    if (m?.[1]) {
      // Best effort: ignore auth errors for public browse.
      try {
        const decoded = await import('../utils/jwt.js')
        const { verifyAccessToken } = decoded as { verifyAccessToken: (t: string) => { sub: string } }
        userId = verifyAccessToken(m[1]).sub
      } catch {
        // ignore
      }
    }

    const and: any[] = []
    const or: any[] = [{ status: 'published' }]
    if (userId) or.push({ ownerId: userId })
    and.push({ OR: or })

    if (q) {
      and.push({
        OR: [
          { title: { contains: q, mode: 'insensitive' } },
          { city: { contains: q, mode: 'insensitive' } },
          { description: { contains: q, mode: 'insensitive' } },
        ],
      })
    }
    if (city) and.push({ city })
    if (type) and.push({ type })
    if (maxPrice && Number.isFinite(maxPrice)) and.push({ price: { lte: maxPrice } })

    const where = { AND: and }

    const listings = await prisma.listing.findMany({
      where,
      include: { images: { orderBy: { sortOrder: 'asc' }, take: 1 } },
      orderBy: { updatedAt: 'desc' },
    })

    res.json({
      listings: listings.map((l) => ({
        ...l,
        // Convenience: front-end can assume there is always a primary image.
        image: l.images[0]?.url ?? null,
      })),
    })
  })

  router.get('/:id', async (req, res) => {
    const id = String(req.params.id)

    // Read authorization token if present
    const auth = String(req.header('authorization') ?? '')
    const m = auth.match(/^Bearer\s+(.+)$/)

    let userId: string | null = null
    if (m?.[1]) {
      try {
        const { verifyAccessToken } = await import('../utils/jwt.js')
        userId = verifyAccessToken(m[1]).sub
      } catch {
        userId = null
      }
    }

    const listing = await prisma.listing.findFirst({
      where: {
        id,
        OR: [
          { status: 'published' },
          userId ? { ownerId: userId } : { status: 'published' },
        ],
      } as any,
      include: { images: { orderBy: { sortOrder: 'asc' } } },
    })

    if (!listing) {
      res.status(404).json({ error: 'Not found' })
      return
    }

    res.json(listing)
  })

  router.post('/', requireAuth, async (req, res) => {
    const body = createListingSchema.safeParse(req.body)
    if (!body.success) {
      res.status(400).json({ error: body.error.flatten() })
      return
    }

    const userId = req.user!.id
    const created = await prisma.listing.create({
      data: { ownerId: userId, ...body.data, status: 'draft' },
      include: { images: true },
    })
    res.status(201).json(created)
  })

  router.put('/:id', requireAuth, requireOnePermission('canEditOwnListing'), async (req, res) => {
    const id = String(req.params.id)
    const body = updateListingSchema.safeParse(req.body)
    if (!body.success) {
      res.status(400).json({ error: body.error.flatten() })
      return
    }

    const existing = await prisma.listing.findUnique({ where: { id } })
    if (!existing) {
      res.status(404).json({ error: 'Not found' })
      return
    }
    if (existing.ownerId !== req.user!.id) {
      res.status(403).json({ error: 'Forbidden' })
      return
    }

    const before = JSON.stringify(existing)
    const after = await prisma.listing.update({
      where: { id },
      data: body.data as any,
    })
    const revision = await prisma.listingRevision.create({
      data: {
        listingId: id,
        actorId: req.user!.id,
        operation: 'update',
        beforeJson: before,
        afterJson: JSON.stringify(after),
      },
    })

    res.json({ ...after, revisionId: revision.id })
  })

  router.post(
    '/:id/submit',
    requireAuth,
    requireOnePermission('canEditOwnListing'),
    async (req, res) => {
    const id = String(req.params.id)
    const existing = await prisma.listing.findUnique({ where: { id } })
    if (!existing) {
      res.status(404).json({ error: 'Not found' })
      return
    }
    if (existing.ownerId !== req.user!.id) {
      res.status(403).json({ error: 'Forbidden' })
      return
    }

    const before = JSON.stringify(existing)
    const after = await prisma.listing.update({
      where: { id },
      data: { status: 'submitted' },
    })
    await prisma.listingRevision.create({
      data: {
        listingId: id,
        actorId: req.user!.id,
        operation: 'submit',
        beforeJson: before,
        afterJson: JSON.stringify(after),
      },
    })

    res.json(after)
    },
  )

  router.post('/:id/publish', requireAuth, requireOnePermission('canPublish'), async (req, res) => {
    const id = String(req.params.id)
    const existing = await prisma.listing.findUnique({ where: { id } })
    if (!existing) {
      res.status(404).json({ error: 'Not found' })
      return
    }
    if (existing.ownerId !== req.user!.id) {
      res.status(403).json({ error: 'Forbidden' })
      return
    }

    const before = JSON.stringify(existing)
    const after = await prisma.listing.update({
      where: { id },
      data: { status: 'published', publishedAt: new Date() },
    })
    await prisma.listingRevision.create({
      data: {
        listingId: id,
        actorId: req.user!.id,
        operation: 'publish',
        beforeJson: before,
        afterJson: JSON.stringify(after),
      },
    })

    res.json(after)
  })

  router.delete('/:id', requireAuth, requireOnePermission('canDeleteOwnListing'), async (req, res) => {
    const id = String(req.params.id)
    const existing = await prisma.listing.findUnique({ where: { id } })
    if (!existing) {
      res.status(404).json({ error: 'Not found' })
      return
    }
    if (existing.ownerId !== req.user!.id) {
      res.status(403).json({ error: 'Forbidden' })
      return
    }

    const before = JSON.stringify(existing)
    await prisma.listingRevision.create({
      data: {
        listingId: id,
        actorId: req.user!.id,
        operation: 'delete',
        beforeJson: before,
        afterJson: JSON.stringify({ deleted: true }),
      },
    })

    await prisma.listing.delete({ where: { id } })
    res.json({ ok: true })
  })

  return router
}

