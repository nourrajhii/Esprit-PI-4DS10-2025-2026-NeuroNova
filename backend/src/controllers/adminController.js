const mongoose = require('mongoose')
const { User, Listing, Contact } = require('../models')

async function stats(req, res) {
  try {
    const twelveMonthsAgo = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000)

    const [
      byType, byStatus, byRole, byMonth, topCities,
      totalListings, totalUsers, totalContacts, totalSubscriptions,
      recentListings, recentUsers,
    ] = await Promise.all([
      Listing.aggregate([{ $group: { _id: '$type', count: { $sum: 1 } } }]),
      Listing.aggregate([{ $group: { _id: '$status', count: { $sum: 1 } } }]),
      User.aggregate([{ $group: { _id: '$role', count: { $sum: 1 } } }]),
      Listing.aggregate([
        { $match: { createdAt: { $gte: twelveMonthsAgo } } },
        { $group: { _id: { $dateToString: { format: '%Y-%m', date: '$createdAt' } }, count: { $sum: 1 } } },
        { $sort: { _id: 1 } },
        { $project: { month: '$_id', count: 1, _id: 0 } },
      ]),
      Listing.aggregate([
        { $group: { _id: '$city', count: { $sum: 1 } } },
        { $sort: { count: -1 } },
        { $limit: 10 },
        { $project: { city: '$_id', count: 1, _id: 0 } },
      ]),
      Listing.countDocuments(),
      User.countDocuments(),
      Contact.countDocuments(),
      User.countDocuments({ 'subscription.status': 'active' }),
      Listing.find()
        .populate('seller', 'id name email')
        .sort({ createdAt: -1 })
        .limit(5),
      User.find()
        .select('-password -refreshToken')
        .sort({ createdAt: -1 })
        .limit(5),
    ])

    return res.json({
      totals: { listings: totalListings, users: totalUsers, contacts: totalContacts, activeSubscriptions: totalSubscriptions },
      byType:   byType.map(r => ({ type: r._id, count: r.count })),
      byStatus: byStatus.map(r => ({ status: r._id, count: r.count })),
      byRole:   byRole.map(r => ({ role: r._id, count: r.count })),
      byMonth,
      topCities,
      recentListings,
      recentUsers,
    })
  } catch (err) {
    console.error('[admin.stats]', err)
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function listUsers(req, res) {
  try {
    const { page = 0, limit = 20, role, search } = req.query
    const query = {}
    if (role)   query.role = role
    if (search) query.$or  = [
      { name:  { $regex: search, $options: 'i' } },
      { email: { $regex: search, $options: 'i' } },
    ]

    const lim  = parseInt(limit)
    const skip = parseInt(page) * lim

    const [total, users] = await Promise.all([
      User.countDocuments(query),
      User.find(query)
        .select('-password -refreshToken')
        .sort({ createdAt: -1 })
        .limit(lim)
        .skip(skip),
    ])
    return res.json({ total, page: parseInt(page), users })
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function updateUserRole(req, res) {
  try {
    const { role } = req.body
    if (!['admin', 'seller', 'investor', 'user'].includes(role)) {
      return res.status(400).json({ error: 'Rôle invalide' })
    }
    const user = await User.findByIdAndUpdate(req.params.id, { role }, { new: true })
    if (!user) return res.status(404).json({ error: 'Utilisateur introuvable' })
    return res.json({ message: 'Rôle mis à jour', user: { id: user.id, role: user.role } })
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function deactivateUser(req, res) {
  try {
    const user = await User.findByIdAndUpdate(
      req.params.id,
      { isActive: false, refreshToken: null },
      { new: true }
    )
    if (!user) return res.status(404).json({ error: 'Utilisateur introuvable' })
    return res.json({ message: 'Utilisateur désactivé' })
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

module.exports = { stats, listUsers, updateUserRole, deactivateUser }
