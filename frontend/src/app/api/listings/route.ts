import { NextRequest, NextResponse } from 'next/server'
import { getScrapedDb, normaliseListing } from '@/lib/mongo'
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

    const db   = await getScrapedDb()
    const col  = db.collection('listings')

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
      }
      return NextResponse.json({ listings: govListings, total: govListings.length, skip: 0, limit: govListings.length })
    }

    const [docs, total] = await Promise.all([
      col.find(filter).sort({ _id: -1 }).skip(skip).limit(limit).toArray(),
      col.countDocuments(filter),
    ])

    const listings = docs.map(normaliseListing)
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
