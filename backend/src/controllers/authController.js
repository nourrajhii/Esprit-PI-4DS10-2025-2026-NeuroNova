const bcrypt = require('bcryptjs')
const jwt    = require('jsonwebtoken')
const { User } = require('../models')
const { sendWelcomeEmail } = require('../services/email')
const { sendWelcomeWhatsApp } = require('../services/sms')

function signAccess(user) {
  return jwt.sign(
    { id: user.id, email: user.email, role: user.role, name: user.name },
    process.env.JWT_SECRET,
    { expiresIn: process.env.JWT_EXPIRES_IN || '15m' }
  )
}

function signRefresh(user) {
  return jwt.sign(
    { id: user.id },
    process.env.JWT_REFRESH_SECRET,
    { expiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d' }
  )
}

async function register(req, res) {
  try {
    const { name, email, password, phone, role } = req.body
    if (!name || !email || !password) {
      return res.status(400).json({ error: 'Nom, email et mot de passe sont requis' })
    }

    // Block admin creation via public registration
    if (role === 'admin') {
      return res.status(403).json({ error: 'Création de compte administrateur non autorisée' })
    }

    const exists = await User.findOne({ email: email.toLowerCase() })
    if (exists) return res.status(409).json({ error: 'Email déjà utilisé' })

    const allowedRoles = ['user', 'seller', 'investor']
    const assignedRole = allowedRoles.includes(role) ? role : 'user'

    const hash = await bcrypt.hash(password, 12)
    const user = await User.create({ name, email, phone, password: hash, role: assignedRole })

    sendWelcomeEmail(user).catch(e => console.warn('[Email]', e.message))
    if (phone) sendWelcomeWhatsApp(user).catch(e => console.warn('[WhatsApp]', e.message))

    const access  = signAccess(user)
    const refresh = signRefresh(user)
    await User.findByIdAndUpdate(user._id, { refreshToken: refresh })

    return res.status(201).json({
      message: 'Compte créé avec succès',
      accessToken: access,
      refreshToken: refresh,
      user: { id: user.id, name: user.name, email: user.email, role: user.role },
    })
  } catch (err) {
    console.error('[register]', err)
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function login(req, res) {
  try {
    const { email, password } = req.body
    if (!email || !password) {
      return res.status(400).json({ error: 'Email et mot de passe requis' })
    }

    const user = await User.findOne({ email: email.toLowerCase() })
    if (!user) return res.status(401).json({ error: 'Identifiants incorrects' })

    const valid = await bcrypt.compare(password, user.password)
    if (!valid) return res.status(401).json({ error: 'Identifiants incorrects' })

    if (!user.isActive) return res.status(403).json({ error: 'Compte désactivé' })

    const access  = signAccess(user)
    const refresh = signRefresh(user)
    await User.findByIdAndUpdate(user._id, { refreshToken: refresh })

    return res.json({
      accessToken: access,
      refreshToken: refresh,
      user: { id: user.id, name: user.name, email: user.email, role: user.role },
    })
  } catch (err) {
    console.error('[login]', err)
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function refresh(req, res) {
  try {
    const { refreshToken } = req.body
    if (!refreshToken) return res.status(400).json({ error: 'Refresh token requis' })

    let payload
    try {
      payload = jwt.verify(refreshToken, process.env.JWT_REFRESH_SECRET)
    } catch {
      return res.status(401).json({ error: 'Refresh token invalide' })
    }

    const user = await User.findOne({ _id: payload.id, refreshToken })
    if (!user) return res.status(401).json({ error: 'Refresh token révoqué' })

    const newAccess  = signAccess(user)
    const newRefresh = signRefresh(user)
    await User.findByIdAndUpdate(user._id, { refreshToken: newRefresh })

    return res.json({ accessToken: newAccess, refreshToken: newRefresh })
  } catch (err) {
    console.error('[refresh]', err)
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function logout(req, res) {
  try {
    await User.findByIdAndUpdate(req.user.id, { refreshToken: null })
    return res.json({ message: 'Déconnexion réussie' })
  } catch (err) {
    console.error('[logout]', err)
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function me(req, res) {
  try {
    const user = await User.findById(req.user.id).select('-password -refreshToken')
    if (!user) return res.status(404).json({ error: 'Utilisateur introuvable' })
    return res.json(user)
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

module.exports = { register, login, refresh, logout, me }
