const { Listing, User } = require('../models')
const { notifyInvestors } = require('../services/notifyInvestors')
const ScrapedListing = require('../models/ScrapedListing')

// Price per m² by city (TND)
const CITY_PRICE_M2 = {
  tunis: 3800, ariana: 3200, 'la marsa': 4200, carthage: 4500, 'la soukra': 3000,
  sousse: 2800, hammamet: 3200, nabeul: 2200, sfax: 2000, monastir: 2600,
  mahdia: 2000, bizerte: 1900, kairouan: 1500, gabes: 1600, 'gabès': 1600,
  'médenine': 1400, medenine: 1400, mednine: 1400, tozeur: 1800, gafsa: 1400,
  jendouba: 1200, zaghouan: 1500, djerba: 3500, 'ben arous': 2800, manouba: 2000,
  kef: 1300, 'le kef': 1300, siliana: 1200, kasserine: 1200, 'sidi bouzid': 1200,
  tataouine: 1100, kebili: 1200, 'kébili': 1200,
}

// Typical surface (m²) by property type — used when surface is missing
const TYPE_DEFAULT_SURFACE = {
  villa: 280, appartement: 100, maison: 160, bureau: 80,
  studio: 45, duplex: 130, terrain: 500, local: 90,
}

// Curated fallback photos by property type (Unsplash, free to use)
const PROPERTY_PHOTOS = {
  villa: [
    'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1583608205776-bfd35f0d9f83?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1613977257363-707ba9348227?w=900&auto=format&fit=crop',
  ],
  appartement: [
    'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1572120360610-d971b9d7767c?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=900&auto=format&fit=crop',
  ],
  maison: [
    'https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=900&auto=format&fit=crop',
  ],
  terrain: [
    'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1604014237800-1c9102c219da?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1500673922987-e212871fec22?w=900&auto=format&fit=crop',
  ],
  bureau: [
    'https://images.unsplash.com/photo-1497366216548-37526070297c?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=900&auto=format&fit=crop',
  ],
  default: [
    'https://images.unsplash.com/photo-1582268611958-ebfd161ef9cf?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1560184897-ae75f418493e?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=900&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=900&auto=format&fit=crop',
  ],
}

function fallbackPhotos(id, type) {
  const key = (type || '').toLowerCase().replace(/[^a-z]/g, '')
  const pool = PROPERTY_PHOTOS[key] || PROPERTY_PHOTOS.default
  // Deterministic pick based on last char of id so same listing always gets same photo
  const idx = id ? (parseInt(id.slice(-4), 16) || 0) % pool.length : 0
  return [pool[idx], pool[(idx + 1) % pool.length]]
}

function estimatePrice(city, surface, type) {
  const key = (city || '').toLowerCase().trim()
  const rate = CITY_PRICE_M2[key] || 2000
  // If no surface, fall back to type-based default surface
  const s = (surface && surface > 0) ? surface : (TYPE_DEFAULT_SURFACE[(type || '').toLowerCase()] || 100)
  return Math.round(s * rate / 1000) * 1000
}

function imageUrls(req, files) {
  if (!files || !files.length) return []
  const base = process.env.BACKEND_PUBLIC_URL || `${req.protocol}://${req.get('host')}`
  return files.map(f => `${base}/uploads/${f.filename}`)
}

function normaliseScraped(doc) {
  const obj = doc.toObject ? doc.toObject() : doc
  const id  = obj._id?.toString()
  let imgs = (obj.image_urls || []).filter(Boolean)
  if (!imgs.length) imgs = fallbackPhotos(id, obj.property_type)

  const rawPrice = obj.price && obj.price > 500 ? obj.price : null
  const price = rawPrice || estimatePrice(obj.city, obj.surface_m2, obj.property_type)
  const isEstimated = !rawPrice

  return {
    _id: id, id,
    title: obj.title || 'Sans titre',
    price, isEstimated,
    city:  obj.city,
    surface: obj.surface_m2,
    images: imgs,
    type: obj.transaction_type || null,
    surface_m2: obj.surface_m2,
    image_urls: imgs,
    transaction_type: obj.transaction_type || null,
    rooms: obj.rooms || 0,
    bathrooms: obj.bathrooms || 0,
    property_type: obj.property_type || null,
    description: obj.description || '',
    phone: obj.phone || null,
    agency_owner: obj.agency_owner || null,
    listing_url: obj.listing_url || null,
    status: 'active',
    source: 'scraped',
    scraped_at: obj.scraped_at,
  }
}

function normaliseLocal(doc) {
  const obj = doc.toObject ? doc.toObject() : doc
  const id  = obj._id?.toString()
  let imgs = (obj.images || []).filter(Boolean)
  if (!imgs.length) imgs = fallbackPhotos(id, obj.type)

  const rawPrice = obj.price && obj.price > 0 ? obj.price : null
  const price = rawPrice || estimatePrice(obj.city, obj.surface, obj.type)
  const isEstimated = !rawPrice

  return {
    _id: id, id,
    title: obj.title,
    price, isEstimated,
    city:  obj.city,
    surface: obj.surface,
    images: imgs,
    type: obj.type,
    surface_m2: obj.surface,
    image_urls: imgs,
    transaction_type: obj.type,
    rooms: obj.rooms || 0,
    bathrooms: obj.bathrooms || 0,
    property_type: null,
    description: obj.description || '',
    phone: null,
    agency_owner: null,
    listing_url: null,
    status: obj.status,
    source: 'seller',
    isEstimated,
  }
}

async function create(req, res) {
  try {
    const { title, description, type, price, surface, rooms, city, address, lat, lng, status } = req.body
    if (!title || !type || !price || !city) {
      return res.status(400).json({ error: 'title, type, price, city sont requis' })
    }
    if (!['vente', 'location'].includes(type)) {
      return res.status(400).json({ error: 'type doit être vente ou location' })
    }

    const coords = (lat && lng) ? [parseFloat(lng), parseFloat(lat)] : [0, 0]

    const listing = await Listing.create({
      title, description, type,
      price:   parseFloat(price),
      surface: surface ? parseFloat(surface) : undefined,
      rooms:   rooms   ? parseInt(rooms)      : undefined,
      city, address,
      location: { type: 'Point', coordinates: coords },
      images: imageUrls(req, req.files),
      status: status || 'active',
      seller: req.user.id,
    })

    if (type === 'vente') {
      notifyInvestors(listing).catch(e => console.warn('[notify]', e.message))
    }

    return res.status(201).json(listing)
  } catch (err) {
    console.error('[listing.create]', err)
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function list(req, res) {
  try {
    const {
      city, type, min_price, max_price, min_surface,
      rooms, page = 0, limit = 20,
    } = req.query

    const lim  = Math.min(parseInt(limit), 100)
    const skip = parseInt(page) * lim

    // ── Local DB query ───────────────────────────────────────────────────────
    const localQuery = { status: 'active' }
    if (city) localQuery.city = { $regex: city, $options: 'i' }
    if (type) localQuery.type = type
    if (min_price || max_price) {
      localQuery.price = {}
      if (min_price) localQuery.price.$gte = parseFloat(min_price)
      if (max_price) localQuery.price.$lte = parseFloat(max_price)
    }

    // ── Scraped DB ───────────────────────────────────────────────────────────
    const ScrapedModel = ScrapedListing.getModel()

    if (ScrapedModel) {
      const scrapedQuery = {
        city:  { $ne: null },
        title: {
          $regex: /^[^\n\r]{10,}$/,
          $not: /^À PROPOS|^A PROPOS|^Liste des|\.com|\.tn|BALLOUCHI|MUBAWAB|TAYARA|Vacances Villa Aline/i,
        },
      }

      if (city) scrapedQuery.city = { $regex: city, $options: 'i' }

      if (type) {
        const rx = type === 'vente' ? /vendre|vente/i : /louer|location/i
        scrapedQuery.transaction_type = rx
      }

      if (min_price) scrapedQuery.price = { ...(scrapedQuery.price || {}), $gte: parseFloat(min_price) }
      if (max_price) scrapedQuery.price = { ...(scrapedQuery.price || {}), $lte: parseFloat(max_price) }
      if (rooms)     scrapedQuery.rooms = { $gte: parseInt(rooms) }
      if (min_surface) scrapedQuery.surface_m2 = { $gte: parseFloat(min_surface) }

      const [scrapedTotal, localTotal] = await Promise.all([
        ScrapedModel.countDocuments(scrapedQuery),
        Listing.countDocuments(localQuery),
      ])
      const total = scrapedTotal + localTotal

      // Pagination strategy: local listings appear on page 0 only (they're few, seller-posted)
      // scraped listings are paginated normally
      let merged = []
      if (parseInt(page) === 0) {
        const [scrapedDocs, localDocs] = await Promise.all([
          ScrapedModel.find(scrapedQuery).sort({ city: 1, scraped_at: -1 }).limit(lim),
          Listing.find(localQuery).sort({ createdAt: -1 }).limit(lim),
        ])
        const localNorm   = localDocs.map(normaliseLocal)
        const scrapedNorm = scrapedDocs.map(normaliseScraped)
        const seen = new Set(localNorm.map(l => l.id))
        merged = [...localNorm]
        scrapedNorm.forEach(s => { if (!seen.has(s.id)) merged.push(s) })
        merged = merged.slice(0, lim)
      } else {
        // Page 1+: scraped only, skip adjusted
        const scrapedSkip = skip - localTotal  // account for local listings on page 0
        const docs = await ScrapedModel.find(scrapedQuery)
          .sort({ city: 1, scraped_at: -1 })
          .limit(lim)
          .skip(Math.max(0, scrapedSkip))
        merged = docs.map(normaliseScraped)
      }

      console.log(`[listing.list] ${merged.length} results, total=${total}, page=${page}`)
      return res.json({ total, page: parseInt(page), listings: merged })
    }

    // ── Fallback: local only ─────────────────────────────────────────────────
    const [total, listings] = await Promise.all([
      Listing.countDocuments(localQuery),
      Listing.find(localQuery).sort({ createdAt: -1 }).limit(lim).skip(skip),
    ])
    return res.json({ total, page: parseInt(page), listings: listings.map(normaliseLocal) })
  } catch (err) {
    console.error('[listing.list]', err)
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function getOne(req, res) {
  try {
    const ScrapedModel = ScrapedListing.getModel()
    if (ScrapedModel) {
      try {
        const doc = await ScrapedModel.findById(req.params.id)
        if (doc) return res.json(normaliseScraped(doc))
      } catch (_) {}
    }
    const listing = await Listing.findById(req.params.id).populate('seller', 'id name email phone')
    if (!listing) return res.status(404).json({ error: 'Annonce introuvable' })
    return res.json(normaliseLocal(listing))
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function update(req, res) {
  try {
    const listing = await Listing.findById(req.params.id)
    if (!listing) return res.status(404).json({ error: 'Annonce introuvable' })

    if (req.user.role === 'seller' && listing.seller.toString() !== req.user.id) {
      return res.status(403).json({ error: 'Vous ne pouvez modifier que vos propres annonces' })
    }

    const { title, description, type, price, surface, rooms, city, address, lat, lng, status } = req.body
    const updates = {}
    if (title)       updates.title       = title
    if (description) updates.description = description
    if (type)        updates.type        = type
    if (price)       updates.price       = parseFloat(price)
    if (surface)     updates.surface     = parseFloat(surface)
    if (rooms)       updates.rooms       = parseInt(rooms)
    if (city)        updates.city        = city
    if (address)     updates.address     = address
    if (lat && lng)  updates.location    = { type: 'Point', coordinates: [parseFloat(lng), parseFloat(lat)] }
    if (status && req.user.role === 'admin') updates.status = status
    if (req.files && req.files.length) updates.images = imageUrls(req, req.files)

    const updated = await Listing.findByIdAndUpdate(req.params.id, updates, { new: true })
    return res.json(updated)
  } catch (err) {
    console.error('[listing.update]', err)
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function remove(req, res) {
  try {
    const listing = await Listing.findById(req.params.id)
    if (!listing) return res.status(404).json({ error: 'Annonce introuvable' })

    if (req.user.role === 'seller' && listing.seller.toString() !== req.user.id) {
      return res.status(403).json({ error: 'Vous ne pouvez supprimer que vos propres annonces' })
    }

    await listing.deleteOne()
    return res.json({ message: 'Annonce supprimée' })
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function myListings(req, res) {
  try {
    const listings = await Listing.find({ seller: req.user.id }).sort({ createdAt: -1 })
    return res.json(listings.map(normaliseLocal))
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

module.exports = { create, list, getOne, update, remove, myListings }
