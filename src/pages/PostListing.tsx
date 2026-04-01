import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Listing } from '../data/mockListings'
import { addUserListing } from '../lib/listingsStore'

const emptyForm = {
  title: '',
  city: '',
  description: '',
  price: '',
  areaM2: '',
  rooms: '2',
  type: 'apartment' as Listing['type'],
}

export function PostListing() {
  const [form, setForm] = useState(emptyForm)
  const [created, setCreated] = useState<{ id: string } | null>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const price = Number(form.price)
    const areaM2 = Number(form.areaM2)
    const rooms = Number(form.rooms)
    if (!Number.isFinite(price) || price <= 0) return
    if (!Number.isFinite(areaM2) || areaM2 <= 0) return
    if (!Number.isFinite(rooms) || rooms < 1) return

    const listing = addUserListing({
      title: form.title,
      city: form.city,
      description: form.description,
      price,
      areaM2,
      rooms,
      type: form.type,
    })
    setCreated({ id: listing.id })
    setForm(emptyForm)
  }

  return (
    <div className="page-post">
      <header className="page-head">
        <h1>Publish a listing</h1>
        <p>
          Saves to your browser (demo) and appears in Explore, Map, and your dashboard — swap for
          your API when ready.
        </p>
      </header>

      {created ? (
        <div className="success-banner">
          <p>
            <strong>Listing saved locally.</strong> It is visible across the app until you clear site
            data.
          </p>
          <div className="success-actions">
            <Link to={`/property/${created.id}`} className="btn btn--primary">
              View listing
            </Link>
            <Link to="/dashboard" className="text-link">
              Dashboard →
            </Link>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setCreated(null)}
            >
              Add another
            </button>
          </div>
        </div>
      ) : (
        <form className="post-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Title</span>
            <input
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="e.g. Bright 2BR near central station"
              required
            />
          </label>
          <label className="field">
            <span>City</span>
            <input
              value={form.city}
              onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
              placeholder="e.g. Bordeaux"
              required
            />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea
              rows={5}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Key facts, condition, energy class…"
              required
            />
          </label>
          <div className="field-row">
            <label className="field">
              <span>Price (€)</span>
              <input
                type="number"
                min={1}
                value={form.price}
                onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))}
                placeholder="350000"
                required
              />
            </label>
            <label className="field">
              <span>Area (m²)</span>
              <input
                type="number"
                min={1}
                value={form.areaM2}
                onChange={(e) => setForm((f) => ({ ...f, areaM2: e.target.value }))}
                placeholder="72"
                required
              />
            </label>
            <label className="field">
              <span>Rooms</span>
              <input
                type="number"
                min={1}
                max={20}
                value={form.rooms}
                onChange={(e) => setForm((f) => ({ ...f, rooms: e.target.value }))}
                required
              />
            </label>
          </div>
          <label className="field">
            <span>Type</span>
            <select
              value={form.type}
              onChange={(e) =>
                setForm((f) => ({ ...f, type: e.target.value as Listing['type'] }))
              }
            >
              <option value="apartment">Apartment</option>
              <option value="house">House</option>
              <option value="studio">Studio</option>
              <option value="loft">Loft</option>
            </select>
          </label>
          <button type="submit" className="btn btn--primary">
            Save listing
          </button>
        </form>
      )}
    </div>
  )
}
