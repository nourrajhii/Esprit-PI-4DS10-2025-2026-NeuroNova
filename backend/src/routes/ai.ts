import { Router } from 'express'
import { z } from 'zod'
import { prisma } from '../prisma.js'
import { requireAuth } from '../middleware/auth.js'
import { requireOnePermission } from '../middleware/requireRoles.js'
import { estimatePrice } from '../services/ai/price.js'
import { legalAssistant } from '../services/ai/legal.js'
import { buildThreeDJobOutput } from '../services/ai/threeD.js'

export function createAiRouter() {
  const router = Router()

  const priceSchema = z.object({
    city: z.string().min(2),
    type: z.enum(['apartment', 'house', 'studio', 'loft']),
    areaM2: z.number().positive(),
    rooms: z.number().int().positive().optional(),
  })

  router.post('/price-estimate', async (req, res) => {
    const body = priceSchema.safeParse(req.body)
    if (!body.success) {
      res.status(400).json({ error: body.error.flatten() })
      return
    }

    const result = estimatePrice(body.data)
    res.json(result)
  })

  const legalSchema = z.object({
    jurisdiction: z.string().min(2),
    scenario: z.enum(['sale', 'lease', 'agency', 'developer']),
    question: z.string().min(5),
    propertySummary: z.string().optional(),
  })

  router.post('/legal-assistant', async (req, res) => {
    const body = legalSchema.safeParse(req.body)
    if (!body.success) {
      res.status(400).json({ error: body.error.flatten() })
      return
    }

    const result = legalAssistant(body.data)
    res.json(result)
  })

  const jobCreateSchema = z.object({
    listingId: z.string().optional(),
    kind: z.enum(['preview_from_plans', 'convert_glb', 'generate_thumbnail', 'generic']),
    payload: z.record(z.string(), z.unknown()).optional(),
  })

  router.post('/3d/jobs', requireAuth, requireOnePermission('canUse3DJobs'), async (req, res) => {
    const body = jobCreateSchema.safeParse(req.body)
    if (!body.success) {
      res.status(400).json({ error: body.error.flatten() })
      return
    }

    const job = await prisma.aIAgentJob.create({
      data: {
        actorId: req.user!.id,
        kind: body.data.kind,
        inputJson: JSON.stringify(body.data.payload ?? {}),
        status: 'queued',
      },
    })

    // Stub processing: simulate async work (replace with BullMQ/worker later)
    void (async () => {
      await prisma.aIAgentJob.update({
        where: { id: job.id },
        data: { status: 'processing' },
      })

      await new Promise((r) => setTimeout(r, 2000))

      const output = buildThreeDJobOutput({ listingId: body.data.listingId, kind: body.data.kind })
      await prisma.aIAgentJob.update({
        where: { id: job.id },
        data: { status: 'succeeded', outputJson: JSON.stringify(output) },
      })
    })().catch(async () => {
      await prisma.aIAgentJob.update({
        where: { id: job.id },
        data: { status: 'failed' },
      })
    })

    res.status(201).json({ jobId: job.id })
  })

  router.get('/jobs/:jobId', requireAuth, requireOnePermission('canUse3DJobs'), async (req, res) => {
    const jobId = String(req.params.jobId)
    const job = await prisma.aIAgentJob.findUnique({ where: { id: jobId } })
    if (!job || job.actorId !== req.user!.id) {
      res.status(404).json({ error: 'Not found' })
      return
    }

    res.json({
      id: job.id,
      kind: job.kind,
      status: job.status,
      createdAt: job.createdAt,
      output: job.outputJson ? JSON.parse(job.outputJson) : null,
    })
  })

  return router
}

