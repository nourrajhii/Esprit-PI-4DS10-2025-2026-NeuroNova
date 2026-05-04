const jwt  = require('jsonwebtoken')
const { User } = require('../models')

function authenticate(req, res, next) {
  const header = req.headers.authorization
  if (!header || !header.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Token manquant' })
  }
  const token = header.slice(7)
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET)
    req.user = payload
    next()
  } catch {
    return res.status(401).json({ error: 'Token invalide ou expiré' })
  }
}

function authorize(...roles) {
  return (req, res, next) => {
    if (!req.user) return res.status(401).json({ error: 'Non authentifié' })
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Accès interdit — rôle insuffisant' })
    }
    next()
  }
}

async function isInvestor(req, res, next) {
  if (!req.user) return res.status(401).json({ error: 'Non authentifié' })
  if (req.user.role === 'admin') return next()
  if (req.user.role !== 'investor') {
    return res.status(403).json({ message: 'Abonnement premium requis' })
  }
  const user = await User.findById(req.user.id).select('subscription')
  if (!user) return res.status(401).json({ error: 'Utilisateur introuvable' })

  const sub = user.subscription
  if (sub.status !== 'active' || (sub.expiresAt && sub.expiresAt < new Date())) {
    return res.status(403).json({ message: 'Abonnement expiré' })
  }
  next()
}

// Keep requireInvestor as alias
const requireInvestor = isInvestor

module.exports = { authenticate, authorize, isInvestor, requireInvestor }
