require('dotenv').config()
const express = require('express')
const cors    = require('cors')
const path    = require('path')

const { connectDB } = require('./config/database')
const { connectScrapedDB } = require('./config/scrapedDatabase')
const { webhook }   = require('./controllers/subscriptionController')
const { seedAdmin } = require('../scripts/seedAdmin')

const app = express()

// Stripe webhook (MUST be before json middleware - needs raw body)
app.post(
  '/subscription/webhook',
  express.raw({ type: 'application/json' }),
  webhook
)

// CORS: allow localhost (any port), the configured FRONTEND_URL, and any origin
// matching SERVER_HOST regardless of port (so the same VM works on :3001, :80,
// or via the nginx reverse-proxy without per-port whitelisting).
const SERVER_HOST = process.env.SERVER_HOST || ''
const STATIC_ORIGINS = [
  process.env.FRONTEND_URL || 'http://localhost:3001',
  'http://localhost:3000',
  'http://localhost:3001',
  'http://localhost:3002',
  'http://localhost:3003',
]
app.use(cors({
  origin: (origin, callback) => {
    if (!origin) return callback(null, true)
    if (STATIC_ORIGINS.includes(origin)) return callback(null, true)
    if (SERVER_HOST) {
      try {
        const u = new URL(origin)
        if (u.hostname === SERVER_HOST) return callback(null, true)
      } catch (_) { /* fall through */ }
    }
    if (/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)) {
      return callback(null, true)
    }
    return callback(new Error('CORS: origin ' + origin + ' not allowed'))
  },
  credentials: true,
}))
app.use(express.json({ limit: '10mb' }))
app.use(express.urlencoded({ extended: true, limit: '10mb' }))

// Static uploads
app.use('/uploads', express.static(path.join(__dirname, '../uploads')))

// Routes
app.use('/auth',         require('./routes/auth'))
app.use('/listings',     require('./routes/listings'))
app.use('/subscription', require('./routes/subscription'))
app.use('/contacts',     require('./routes/contacts'))
app.use('/admin',        require('./routes/admin'))

// Health check
app.get('/health', (req, res) => res.json({ status: 'ok', service: 'estatemind-backend', ts: Date.now() }))

// 404
app.use((req, res) => res.status(404).json({ error: `Route ${req.method} ${req.path} introuvable` }))

// Error handler
app.use((err, req, res, next) => {
  console.error('[Unhandled]', err)
  res.status(500).json({ error: err.message || 'Erreur interne' })
})

// Start
const PORT = parseInt(process.env.PORT || '4000')

async function start() {
  try {
    await connectDB()
    await connectScrapedDB()
    await seedAdmin()
    app.listen(PORT, () => {
      console.log('[backend] listening on :' + PORT)
    })
  } catch (e) {
    console.error('[startup]', e)
    process.exit(1)
  }
}

start()
