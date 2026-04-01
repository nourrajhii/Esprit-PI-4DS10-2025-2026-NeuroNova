import { useMemo, useState } from 'react'
import { PropertyCard } from '../components/PropertyCard'
import { MOCK_LISTINGS } from '../data/mockListings'

export function Browse() {
  const [city, setCity] = useState('')
  const [type, setType] = useState<string>('all')
  const [maxPrice, setMaxPrice] = useState(800000)

  const cities = useMemo(() => {
    const s = new Set(MOCK_LISTINGS.map((l) => l.city))
    return [...s].sort()
  }, [])

  const filtered = useMemo(() => {
    return MOCK_LISTINGS.filter((l) => {
      if (city && l.city !== city) return false
      if (type !== 'all' && l.type !== type) return false
      if (l.price > maxPrice) return false
      return true
    })
  }, [city, type, maxPrice])

  return (
    <div className="page-browse">
      <header className="page-head">
        <h1>Explore</h1>
        <p>Filter demo listings — connect your API for live inventory.</p>
      </header>

      <div className="filters">
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
