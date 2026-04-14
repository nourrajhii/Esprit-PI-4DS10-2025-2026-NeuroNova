import { Router } from 'express'
import multer from 'multer'
import path from 'node:path'
import fs from 'node:fs'
import { z } from 'zod'
import { requireAuth } from '../middleware/auth.js'
import { requireOnePermission } from '../middleware/requireRoles.js'
import { prisma } from '../prisma.js'

const uploadBodySchema = z.object({
  altText: z.string().min(1).max(300).optional(),
  sortOrder: z.coerce.number().int().min(0).optional(),
})

export function createUploadsRouter() {
  const router = Router()

  const uploadDir = process.env.UPLOAD_DIR ?? './uploads'
  if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true })

  const storage = multer.diskStorage({
    destination: (_req, _file, cb) => cb(null, uploadDir),
    filename: (_req, file, cb) => {
      const ext = path.extname(file.originalname) || '.jpg'
      const name = `upload_${Date.now()}_${Math.random().toString(16).slice(2)}${ext}`
      cb(null, name)
    },
  })

  const upload = multer({
    storage,
    limits: { fileSize: 10 * 1024 * 1024 }, // 10MB
  })

  router.post('/', upload.single('file'), async (req, res) => {
    if (!req.file) {
      res.status(400).json({ error: 'Missing file' })
      return
    }
    const storageKey = req.file.filename
    const url = `/static/${storageKey}`
    res.status(201).json({ url, storageKey })
  })

  router.post(
    '/listings/:listingId/images',
    requireAuth,
    requireOnePermission('canUploadListingImages'),
    upload.single('file'),
    async (req, res) => {
    const listingId = String(req.params.listingId)
    if (!req.file) {
      res.status(400).json({ error: 'Missing file' })
      return
    }

    const bodyParsed = uploadBodySchema.safeParse(req.body)
    if (!bodyParsed.success) {
      res.status(400).json({ error: bodyParsed.error.flatten() })
      return
    }

    const listing = await prisma.listing.findUnique({ where: { id: listingId } })
    if (!listing) {
      res.status(404).json({ error: 'Listing not found' })
      return
    }
    if (listing.ownerId !== req.user!.id) {
      res.status(403).json({ error: 'Forbidden' })
      return
    }

    const storageKey = req.file.filename
    const url = `/static/${storageKey}`

    const image = await prisma.listingImage.create({
      data: {
        listingId,
        url,
        storageKey,
        altText: bodyParsed.data.altText,
        sortOrder: bodyParsed.data.sortOrder ?? undefined,
      },
    })

    // Create a revision record (audit trail)
    await prisma.listingRevision.create({
      data: {
        listingId,
        actorId: req.user!.id,
        operation: 'add_image',
        beforeJson: JSON.stringify({}),
        afterJson: JSON.stringify({ imageId: image.id, url }),
      },
    })

    res.status(201).json(image)
    },
  )

  return router
}

