import { NextRequest, NextResponse } from 'next/server'
import { getScrapedDb, getMainDb, normaliseListing } from '@/lib/mongo'
import { ObjectId } from 'mongodb'

export const dynamic = 'force-dynamic'

const ALL_GOVS = [
  'Tunis','Ariana','Ben Arous','Manouba','Nabeul','Zaghouan','Bizerte',
  'Béja','Jendouba','Kef','Siliana','Sousse','Monastir','Mahdia',
  'Sfax','Kairouan','Kasserine','Sidi Bouzid','Gabès','Médenine',
  'Tataouine','Gafsa','Tozeur','Kébili',
]

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = req.nextUrl
    const city     = searchParams.get('city')     || ''
    const minPrice = Number(searchParams.get('min_price')) || 0
    const maxPrice = Number(searchParams.get('max_price')) || 0
    const rooms    = Number(searchParams.get('rooms'))     || 0
    const txType   = searchParams.get('transaction_type') || ''
    const limit    = Math.min(Number(searchParams.get('limit')) || 24, 100)
    const skip     = Number(searchParams.get('skip')) || 0
    const govMode  = searchParams.get('by_gov') === '1'   // return 1 per governorate
    const q        = searchParams.get('q') || ''

    const scrapedDb = await getScrapedDb()
    const col       = scrapedDb.collection('listings')

    // Also fetch seller-posted listings from main estatemind DB
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let sellerCol: any = null
    try {
      const mainDb = await getMainDb()
      sellerCol = mainDb.collection('listings')
    } catch { /* non-fatal — fall back to scraped only */ }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const filter: Record<string, any> = {}
    if (city)   filter.city = { $regex: city, $options: 'i' }
    if (txType) filter.transaction_type = { $regex: txType, $options: 'i' }
    if (rooms)  filter.$or = [{ rooms: rooms }, { pieces: rooms }]
    if (q)      filter.$or = [
      { title: { $regex: q, $options: 'i' } },
      { description: { $regex: q, $options: 'i' } },
      { city: { $regex: q, $options: 'i' } },
    ]
    if (minPrice > 0) filter.price = { ...filter.price, $gte: minPrice }
    if (maxPrice > 0) filter.price = { ...filter.price, $lte: maxPrice }

    // Seller listings use 'type' not 'transaction_type', and status must be active
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sellerFilter: Record<string, any> = { status: 'active' }
    if (city)   sellerFilter.city = { $regex: city, $options: 'i' }
    if (txType) sellerFilter.type = { $regex: txType, $options: 'i' }
    if (rooms)  sellerFilter.rooms = rooms
    if (q)      sellerFilter.$or = [
      { title: { $regex: q, $options: 'i' } },
      { description: { $regex: q, $options: 'i' } },
      { city: { $regex: q, $options: 'i' } },
    ]
    if (minPrice > 0) sellerFilter.price = { ...sellerFilter.price, $gte: minPrice }
    if (maxPrice > 0) sellerFilter.price = { ...sellerFilter.price, $lte: maxPrice }

    if (govMode) {
      // Return up to 2 representative listings per governorate (for map coverage)
      const govListings: Record<string, unknown>[] = []
      for (const gov of ALL_GOVS) {
        const docs = await col
          .find({ city: { $regex: gov, $options: 'i' }, ...filter })
          .sort({ _id: -1 })
          .limit(2)
          .toArray()
        for (const d of docs) govListings.push(normaliseListing(d))
        // Add seller listings per gov too
        if (sellerCol) {
          const sDocs = await sellerCol
            .find({ city: { $regex: gov, $options: 'i' }, status: 'active' })
            .sort({ createdAt: -1 })
            .limit(1)
            .toArray()
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          for (const d of sDocs as any[]) govListings.push(normaliseListing({ ...d, source: 'seller', transaction_type: d.type }))
        }
      }
      return NextResponse.json({ listings: govListings, total: govListings.length, skip: 0, limit: govListings.length })
    }

    // Fetch seller listings first (show them prominently), then scraped
    const sellerDocs = sellerCol
      ? await sellerCol.find(sellerFilter).sort({ createdAt: -1 }).toArray()
      : []
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sellerListings = sellerDocs.map((d: any) =>
      normaliseListing({ ...d, source: 'seller', transaction_type: d.type, surface_m2: d.surface })
    )

    const [docs, scrapedTotal] = await Promise.all([
      col.find(filter).sort({ _id: -1 }).skip(Math.max(0, skip - sellerDocs.length)).limit(limit - Math.min(sellerDocs.length, limit)).toArray(),
      col.countDocuments(filter),
    ])

    const listings = [...sellerListings, ...docs.map(normaliseListing)]
    const total    = scrapedTotal + sellerDocs.length
    return NextResponse.json({ listings, total, skip, limit })
  } catch (err) {
    console.error('[API /listings]', err)
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  // Allow searching by array of IDs (used by compare page)
  try {
    const body = await req.json()
    const ids: string[] = body.ids || []
    if (!ids.length) return NextResponse.json({ listings: [] })

    const db  = await getScrapedDb()
    const col = db.collection('listings')

    const objectIds = ids.flatMap(id => {
      try { return [new ObjectId(id)] } catch { return [] }
    })
    const docs = await col.find({ _id: { $in: objectIds } }).toArray()
    return NextResponse.json({ listings: docs.map(normaliseListing) })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
