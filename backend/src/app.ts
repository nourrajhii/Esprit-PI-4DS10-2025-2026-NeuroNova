import express from 'express'
import cors from 'cors'
import helmet from 'helmet'
import morgan from 'morgan'
import { createAuthRouter } from './routes/auth.js'
import { createListingsRouter } from './routes/listings.js'
import { createFavoritesRouter } from './routes/favorites.js'
import { createUploadsRouter } from './routes/uploads.js'
import { createAiRouter } from './routes/ai.js'
import { createAdminRouter } from './routes/admin.js'

export function createApp() {
  const app = express()

  app.use(helmet())
  app.use(
    cors({
      origin: process.env.CORS_ORIGIN ?? 'http://localhost:5173',
      credentials: true,
    }),
  )
  app.use(express.json({ limit: '2mb' }))
  app.use(morgan('dev'))

  app.get('/health', (_req, res) => {
    res.json({ ok: true })
  })

  // Helpful default route so "Cannot GET /" is avoided.
  app.get('/', (_req, res) => {
    res.json({
      service: 'REAL backend',
      health: '/health',
      endpoints: ['/auth', '/listings', '/favorites', '/uploads', '/ai'],
      note: 'Use /auth/login to get a JWT, then call protected endpoints with Authorization: Bearer <token>.',
    })
  })

  app.use('/auth', createAuthRouter())
  app.use('/listings', createListingsRouter())
  app.use('/favorites', createFavoritesRouter())
  app.use('/uploads', createUploadsRouter())
  app.use('/ai', createAiRouter())
  app.use('/admin', createAdminRouter())

  return app
}

