import { NextRequest, NextResponse } from 'next/server'
import { getScrapedDb, normaliseListing } from '@/lib/mongo'
import { ObjectId } from 'mongodb'

export const dynamic = 'force-dynamic'

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params
    const db  = await getScrapedDb()
    const col = db.collection('listings')

    let doc = null

    // Try ObjectId first, then string id field
    try {
      doc = await col.findOne({ _id: new ObjectId(id) })
    } catch {
      doc = await col.findOne({ id })
    }
    if (!doc) doc = await col.findOne({ id })
    if (!doc) return NextResponse.json({ error: 'Not found' }, { status: 404 })

    return NextResponse.json(normaliseListing(doc))
  } catch (err) {
    console.error('[API /listings/[id]]', err)
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
