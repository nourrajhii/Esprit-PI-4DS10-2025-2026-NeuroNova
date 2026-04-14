import { Router } from 'express'
import bcrypt from 'bcryptjs'
import { z } from 'zod'
import { prisma } from '../prisma.js'
import { signAccessToken } from '../utils/jwt.js'
import { requireAuth } from '../middleware/auth.js'

const registerSchema = z.object({
  email: z.string().email(),
  name: z.string().min(2).max(120),
  password: z.string().min(6),
  role: z.enum([
    'individual_investor',
    'professional_investor',
    'real_estate_agency',
    'developer_fund',
  ]),
})

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
})

export function createAuthRouter() {
  const router = Router()

  router.post('/register', async (req, res) => {
    const body = registerSchema.safeParse(req.body)
    if (!body.success) {
      res.status(400).json({ error: body.error.flatten() })
      return
    }

    const { email, name, password, role } = body.data

    const existing = await prisma.user.findUnique({ where: { email } })
    if (existing) {
      res.status(409).json({ error: 'Email already in use' })
      return
    }

    const passwordHash = await bcrypt.hash(password, 12)
    const user = await prisma.user.create({
      data: { email, name, passwordHash, role },
      select: { id: true, email: true, name: true, role: true },
    })

    const token = signAccessToken({ sub: user.id, role: user.role })
    res.json({ token, user })
  })

  router.post('/login', async (req, res) => {
    const body = loginSchema.safeParse(req.body)
    if (!body.success) {
      res.status(400).json({ error: body.error.flatten() })
      return
    }

    const { email, password } = body.data
    const user = await prisma.user.findUnique({ where: { email } })
    if (!user) {
      res.status(401).json({ error: 'Invalid credentials' })
      return
    }

    const ok = await bcrypt.compare(password, user.passwordHash)
    if (!ok) {
      res.status(401).json({ error: 'Invalid credentials' })
      return
    }

    const token = signAccessToken({ sub: user.id, role: user.role })
    res.json({
      token,
      user: { id: user.id, email: user.email, name: user.name, role: user.role },
    })
  })

  router.get('/me', requireAuth, async (req, res) => {
    const userId = req.user!.id
    const user = await prisma.user.findUnique({
      where: { id: userId },
      select: { id: true, email: true, name: true, role: true },
    })
    if (!user) {
      res.status(404).json({ error: 'Not found' })
      return
    }
    res.json({ user })
  })

  return router
}

