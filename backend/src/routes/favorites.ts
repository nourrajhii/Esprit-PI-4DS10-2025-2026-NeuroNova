import { Router } from 'express'
import { requireAuth } from '../middleware/auth.js'
import { prisma } from '../prisma.js'

export function createFavoritesRouter() {
  const router = Router()

  router.get('/', requireAuth, async (req, res) => {
    const userId = req.user!.id
    const favorites = await prisma.favorite.findMany({
      where: { userId },
      include: {
        listing: {
          include: { images: { orderBy: { sortOrder: 'asc' }, take: 1 } },
        },
      },
    })

    res.json({
      favorites: favorites.map((f) => ({
        listingId: f.listingId,
        listing: {
          ...f.listing,
          image: f.listing.images[0]?.url ?? null,
        },
      })),
    })
  })

  router.post('/:listingId/toggle', requireAuth, async (req, res) => {
    const userId = req.user!.id
    const listingId = String(req.params.listingId)

    const existing = await prisma.favorite.findUnique({
      where: { userId_listingId: { userId, listingId } },
    })

    if (existing) {
      await prisma.favorite.delete({ where: { id: existing.id } })
      res.json({ saved: false })
      return
    }

    await prisma.favorite.create({ data: { userId, listingId } })
    res.json({ saved: true })
  })

  return router
}

