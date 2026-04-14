import Papa from 'papaparse'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Listing } from '../data/mockListings'
import { clearImportedListings, writeImportedListings } from '../lib/importedListingsStore'

type Row = {
  id?: string
  title?: string
  price?: string | number
  city?: string
  property_type?: string
  surface_m2?: string | number
  rooms?: string | number
  bathrooms?: string | number
  transaction_type?: string
  url?: string
}

const PLACEHOLDER_IMAGE =
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1200&q=80'

function toInt(v: unknown, fallback = 0) {
  const n = typeof v === 'number' ? v : Number(String(v ?? '').replace(',', '.'))
  if (!Number.isFinite(n)) return fallback
  return Math.round(n)
}

function mapType(s: string | undefined): Listing['type'] {
  const v = (s ?? '').toLowerCase()
  if (v.includes('house') || v.includes('villa') || v.includes('maison')) return 'house'
  if (v.includes('studio')) return 'studio'
  if (v.includes('loft')) return 'loft'
  return 'apartment'
}

function mapTransaction(s: string | undefined): Listing['transactionType'] {
  const v = (s ?? '').toLowerCase()
  if (v.includes('loc')) return 'location'
  return 'vente'
}

export function ImportDataset() {
  const [fileName, setFileName] = useState<string | null>(null)
  const [count, setCount] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const hint = useMemo(
    () =>
      'Expected columns: id,title,price,city,property_type,surface_m2,rooms,bathrooms,transaction_type,url',
    [],
  )

  function handleFile(file: File) {
    setError(null)
    setFileName(file.name)
    Papa.parse<Row>(file, {
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        try {
          const rows = (result.data ?? []).filter(Boolean)
          const now = new Date().toISOString().slice(0, 10)

          const listings: Listing[] = rows
            .map((r, i) => {
              const id = String(r.id ?? `csv-${i}`)
              const title = String(r.title ?? 'Annonce')
              const city = String(r.city ?? 'Tunis')
              const price = toInt(r.price, 0)
              const areaM2 = Math.max(1, toInt(r.surface_m2, 1))
              const rooms = Math.max(1, toInt(r.rooms, 1))
              const bathrooms = Math.max(0, toInt(r.bathrooms, 0))
              const externalUrl = r.url ? String(r.url) : undefined

              return {
                id,
                title,
                city,
                price: price || 0,
                currency: 'TND',
                rooms,
                areaM2,
                bathrooms,
                type: mapType(r.property_type),
                transactionType: mapTransaction(r.transaction_type),
                image: PLACEHOLDER_IMAGE,
                description: title,
                publishedAt: now,
                externalUrl,
              }
            })
            .filter((l) => l.title && l.city)

          writeImportedListings(listings)
          setCount(listings.length)
        } catch (e) {
          setError('Could not import CSV. Please check columns/format.')
          setCount(null)
        }
      },
      error: () => {
        setError('Could not read CSV file.')
        setCount(null)
      },
    })
  }

  return (
    <div className="page-post">
      <header className="page-head">
        <h1>Import dataset (CSV)</h1>
        <p>
          Upload your CSV and we will show every announcement on the Tunisia map. Data is stored in
          your browser (demo).
        </p>
      </header>

      <section className="dash-card" style={{ maxWidth: 720 }}>
        <p className="dash-note" style={{ marginBottom: 12 }}>
          {hint}
        </p>

        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) handleFile(f)
          }}
        />

        {fileName && (
          <p className="dash-note" style={{ marginTop: 10 }}>
            File: <strong>{fileName}</strong>
          </p>
        )}
        {count !== null && (
          <div className="success-banner" style={{ marginTop: 14 }}>
            <p style={{ marginBottom: 8 }}>
              <strong>Imported:</strong> {count} listing(s)
            </p>
            <Link to="/map" className="btn btn--primary">
              Open Tunisia map
            </Link>
          </div>
        )}
        {error && <p className="form-error">{error}</p>}

        <div style={{ marginTop: 12 }}>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => {
              clearImportedListings()
              setCount(null)
              setFileName(null)
              setError(null)
            }}
          >
            Clear imported dataset
          </button>
        </div>
      </section>
    </div>
  )
}

