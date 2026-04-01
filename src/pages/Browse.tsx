import { useMemo, useState } from 'react'
import { PropertyCard } from '../components/PropertyCard'
import { useListings } from '../lib/listingsStore'

export function Browse() {
  const listings = useListings()
  const [query, setQuery] = useState('')
  const [city, setCity] = useState('')
  const [type, setType] = useState<string>('all')
  const [maxPrice, setMaxPrice] = useState(900000)

  const cities = useMemo(() => {
    const s = new Set(listings.map((l) => l.city))
    return [...s].sort()
  }, [listings])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return listings.filter((l) => {
      if (q) {
        const blob = `${l.title} ${l.city} ${l.description}`.toLowerCase()
        if (!blob.includes(q)) return false
      }
      if (city && l.city !== city) return false
      if (type !== 'all' && l.type !== type) return false
      if (l.price > maxPrice) return false
      return true
    })
  }, [listings, query, city, type, maxPrice])

  return (
    <div className="page-browse">
      <header className="page-head">
        <h1>Explore</h1>
        <p>Search and filter — your published listings appear here with the demo catalog.</p>
      </header>

      <div className="filters">
        <label className="field field--grow">
          <span>Search</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Title, city, keywords…"
            aria-label="Search listings"
          />
        </label>
        <label className="field">
          <span>City</span>
          <select value={city} onChange={(e) => setCity(e.target.value)}>
            <option value="">All cities</option>
            {cities.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Type</span>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="all">All types</option>
            <option value="apartment">Apartment</option>
            <option value="house">House</option>
            <option value="studio">Studio</option>
            <option value="loft">Loft</option>
          </select>
        </label>
        <label className="field field--grow">
          <span>Max price: {maxPrice.toLocaleString('fr-FR')} €</span>
          <input
            type="range"
            min={150000}
            max={900000}
            step={10000}
            value={maxPrice}
            onChange={(e) => setMaxPrice(Number(e.target.value))}
          />
        </label>
      </div>

      <p className="results-count">{filtered.length} listing(s)</p>
      <div className="property-grid">
        {filtered.map((l, i) => (
          <PropertyCard key={l.id} listing={l} index={i} />
        ))}
      </div>
    </div>
  )
}
