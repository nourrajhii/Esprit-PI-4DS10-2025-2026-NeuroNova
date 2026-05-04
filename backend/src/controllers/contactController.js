const { Contact, Listing, User } = require('../models')
const { sendContactNotificationEmail } = require('../services/email')

async function send(req, res) {
  try {
    const { listingId, message, phone } = req.body
    if (!listingId || !message) {
      return res.status(400).json({ error: 'listingId et message sont requis' })
    }

    const listing = await Listing.findById(listingId)
    if (!listing) return res.status(404).json({ error: 'Annonce introuvable' })

    const contact = await Contact.create({
      listing: listingId,
      sender:  req.user.id,
      seller:  listing.seller,
      message,
      phone: phone || req.user.phone,
    })

    const seller = await User.findById(listing.seller)
    if (seller) {
      sendContactNotificationEmail(seller, contact, listing)
        .catch(e => console.warn('[Email]', e.message))
    }

    return res.status(201).json({ message: 'Demande envoyée avec succès', contact })
  } catch (err) {
    console.error('[contact.send]', err)
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function mySent(req, res) {
  try {
    const contacts = await Contact.find({ sender: req.user.id })
      .populate('listing', 'id title city type')
      .sort({ createdAt: -1 })
    return res.json(contacts)
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function myReceived(req, res) {
  try {
    const contacts = await Contact.find({ seller: req.user.id })
      .populate('listing', 'id title city type')
      .populate('sender',  'id name email phone')
      .sort({ createdAt: -1 })
    return res.json(contacts)
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function all(req, res) {
  try {
    const { page = 0, limit = 20 } = req.query
    const lim  = parseInt(limit)
    const skip = parseInt(page) * lim

    const [total, contacts] = await Promise.all([
      Contact.countDocuments(),
      Contact.find()
        .populate('listing', 'id title city type')
        .populate('sender',  'id name email')
        .populate('seller',  'id name email')
        .sort({ createdAt: -1 })
        .limit(lim)
        .skip(skip),
    ])
    return res.json({ total, page: parseInt(page), contacts })
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function updateStatus(req, res) {
  try {
    const { status } = req.body
    if (!['pending', 'read', 'replied'].includes(status)) {
      return res.status(400).json({ error: 'Status invalide' })
    }

    const contact = await Contact.findById(req.params.id)
    if (!contact) return res.status(404).json({ error: 'Demande introuvable' })

    if (req.user.role !== 'admin' && contact.seller.toString() !== req.user.id) {
      return res.status(403).json({ error: 'Accès interdit' })
    }

    contact.status = status
    await contact.save()
    return res.json(contact)
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

module.exports = { send, mySent, myReceived, all, updateStatus }
