import { NextResponse } from 'next/server'
import { getScrapedDb } from '@/lib/mongo'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const db  = await getScrapedDb()
    const col = db.collection('listings')

    const [countResult, priceAgg] = await Promise.all([
      col.estimatedDocumentCount(),
      col.aggregate([
        { $match: { price: { $gte: 5000, $lte: 50_000_000 } } },
        {
          $group: {
            _id: null,
            avg_price:    { $avg: '$price' },
            median_sum:   { $push: '$price' },
            count_priced: { $sum: 1 },
          },
        },
      ]).toArray(),
      // ── price/m² aggregate (separate pipeline for clarity)
    ])

    const pm2Agg = await col.aggregate([
      { $match: { price: { $gte: 5000 }, surface_m2: { $gt: 10 } } },
      { $addFields: { pm2: { $divide: ['$price', '$surface_m2'] } } },
      { $match: { pm2: { $gt: 100, $lt: 20000 } } },
      { $group: { _id: null, avg_pm2: { $avg: '$pm2' } } },
    ]).toArray()

    const stats       = priceAgg[0] ?? {}
    const prices: number[] = (stats.median_sum ?? []).sort((a: number, b: number) => a - b)
    const mid         = Math.floor(prices.length / 2)
    const median      = prices.length > 0 ? prices[mid] : 0

    return NextResponse.json({
      count:           countResult,
      avg_price:       Math.round(stats.avg_price ?? 0),
      median_price:    Math.round(median),
      avg_price_per_m2: Math.round(pm2Agg[0]?.avg_pm2 ?? 0),
    })
  } catch (err) {
    console.error('[API /market/summary]', err)
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
