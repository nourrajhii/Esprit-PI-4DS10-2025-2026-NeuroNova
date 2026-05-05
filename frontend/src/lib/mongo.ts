import { MongoClient } from 'mongodb'

// ── Connection cache (Next.js hot-reload safe) ────────────────────────────────
declare global {
  // eslint-disable-next-line no-var
  var _mongoScrapedClient: MongoClient | undefined
  // eslint-disable-next-line no-var
  var _mongoMainClient: MongoClient | undefined
}

async function getScrapedClient(): Promise<MongoClient> {
  // Read env at runtime (not build time) so Docker builds succeed without secrets
  const SCRAPED_URI = process.env.SCRAPED_DB_URI
  if (!SCRAPED_URI) throw new Error('SCRAPED_DB_URI is not set')
  if (!global._mongoScrapedClient) {
    global._mongoScrapedClient = new MongoClient(SCRAPED_URI, { tls: true, tlsAllowInvalidCertificates: true })
    await global._mongoScrapedClient.connect()
  }
  return global._mongoScrapedClient
}

async function getMainClient(): Promise<MongoClient> {
  const MAIN_URI    = process.env.MONGODB_URI
  const SCRAPED_URI = process.env.SCRAPED_DB_URI
  const uri = MAIN_URI || SCRAPED_URI
  if (!uri) throw new Error('MONGODB_URI is not set')
  if (!global._mongoMainClient) {
    global._mongoMainClient = new MongoClient(uri, { tls: true, tlsAllowInvalidCertificates: true })
    await global._mongoMainClient.connect()
  }
  return global._mongoMainClient
}

/** dcrawl database — scraped listings from Mubawab/Menzili */
export async function getScrapedDb() {
  const client = await getScrapedClient()
  return client.db('dcrawl')
}

/** estatemind database — user listings, auth, etc. */
export async function getMainDb() {
  const client = await getMainClient()
  return client.db('estatemind')
}

// ── Price estimation heuristic (base TND/m² by city) ─────────────────────────
// Used when a listing has price = 0 or null
const PRICE_PM2: Record<string, number> = {
  'Tunis': 3400, 'Ariana': 2900, 'Ben Arous': 2500, 'Manouba': 2200,
  'Nabeul': 2500, 'Zaghouan': 1400, 'Bizerte': 1900, 'Béja': 1200,
  'Jendouba': 1000, 'Kef': 1000, 'Siliana': 950, 'Sousse': 2700,
  'Monastir': 2400, 'Mahdia': 1700, 'Sfax': 1900, 'Kairouan': 1300,
  'Kasserine': 900, 'Sidi Bouzid': 900, 'Gabès': 1400, 'Médenine': 1600,
  'Tataouine': 950, 'Gafsa': 1100, 'Tozeur': 1200, 'Kébili': 1000,
  // Common aliases from scraped data
  'Hammamet': 2800, 'La Marsa': 3800, 'Carthage': 4200, 'Sidi Bou Said': 5500,
  'Lac': 3600, 'Centre Ville': 3200, 'Ennasr': 2800, 'Menzah': 3000,
  'Manar': 2700, 'Borj Louzir': 2400,
}

export function estimatePrice(city: string, surface: number | null | undefined): number {
  const normalised = city?.trim() || ''
  // Try exact match first, then partial match
  const pm2 = PRICE_PM2[normalised]
    ?? Object.entries(PRICE_PM2).find(([k]) => normalised.toLowerCase().includes(k.toLowerCase()))?.[1]
    ?? 1800  // national average fallback
  const s = surface && surface > 0 ? surface : 85  // fallback surface
  return Math.round(pm2 * s)
}

/** Normalise a raw MongoDB document to the shared MongoListing shape */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normaliseListing(doc: any): Record<string, unknown> {
  const id = doc._id?.toString() ?? doc.id ?? ''
  const city = doc.city || doc.gouvernorat || doc.location || 'Tunisie'
  const rawSurface = doc.surface_m2 || doc.surface || doc.area || null
  // Surface sanity: reject > 5000 m² (likely corrupt) or < 5 m²
  const surface = rawSurface && rawSurface >= 5 && rawSurface <= 5000 ? rawSurface : null

  const rawPrice = doc.price ?? doc.prix ?? 0
  // Price sanity: Tunisian real estate range ~5,000 – 50,000,000 TND.
  // Values outside this range are corrupt data — estimate instead.
  const price = rawPrice >= 5000 && rawPrice <= 50_000_000
    ? rawPrice
    : estimatePrice(city, surface)

  // Rooms sanity: real apartments have 1-20 rooms, not 219 or 611
  const rawRooms = doc.rooms ?? doc.pieces ?? null
  const rooms = rawRooms && rawRooms > 0 && rawRooms <= 20 ? rawRooms : null

  const rawBath = doc.bathrooms ?? doc.salles_bain ?? null
  const bathrooms = rawBath && rawBath > 0 && rawBath <= 10 ? rawBath : null

  // Normalise images: prefer image_urls, fall back to images array
  const rawImgUrls: string[] = doc.image_urls || doc.images || []
  const image_urls = rawImgUrls
    .filter((u): u is string => typeof u === 'string' && u.startsWith('http'))

  // Clean up listing-code prefixes in title (e.g. "L219 Dar BARBAROUSSE" → "Dar BARBAROUSSE")
  const rawTitle = doc.title || doc.titre || `${doc.property_type || 'Bien'} à ${city}`
  const title = rawTitle.replace(/^L\d+\s+/i, '').trim() || rawTitle

  return {
    id,
    _id: id,
    title,
    price,
    city,
    surface_m2: surface,
    rooms,
    bathrooms,
    property_type:    doc.property_type    || doc.type_bien || null,
    transaction_type: doc.transaction_type || doc.type      || null,
    listing_url:      doc.listing_url      || doc.url       || null,
    image_urls,
    description:      doc.description || null,
    agency_owner:     doc.agency_owner || doc.agence || null,
    phone:            doc.phone        || doc.telephone || null,
    source:           doc.source || 'scraped',
    gouvernorat:      doc.gouvernorat || city,
  }
}
