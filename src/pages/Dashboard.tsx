import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Heart,
  Upload,
  LayoutGrid,
  PlusCircle,
  Sparkles,
  Trash2,
  TrendingUp,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useListings, removeUserListing } from '../lib/listingsStore'
import { useFavorites } from '../lib/favoritesStore'
import { PropertyCard } from '../components/PropertyCard'

export function Dashboard() {
  const { user } = useAuth()
  const listings = useListings()
  const { favoriteIds, count: savedCount } = useFavorites()

  const mine = listings.filter((l) => l.id.startsWith('u-'))
  const saved = useMemo(() => {
    if (favoriteIds.length === 0) return []
    const set = new Set(favoriteIds)
    return listings.filter((l) => set.has(l.id))
  }, [favoriteIds, listings])

  type Tab = 'overview' | 'listings' | 'saved' | 'ai'
  const [tab, setTab] = useState<Tab>('overview')

  const [aiCity, setAiCity] = useState('Paris')
  const [aiType, setAiType] = useState<'apartment' | 'house' | 'studio' | 'loft'>('apartment')
  const [aiArea, setAiArea] = useState(70)
  const [aiRooms, setAiRooms] = useState(2)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiResult, setAiResult] = useState<null | { estimate: number; confidence: number }>(null)

  async function runPriceEstimate() {
    setAiLoading(true)
    setAiResult(null)
    try {
      const r = await fetch('http://localhost:4000/ai/price-estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city: aiCity, type: aiType, areaM2: aiArea, rooms: aiRooms }),
      })
      const data = (await r.json()) as { estimate: number; confidence: number }
      setAiResult(data)
    } finally {
      setAiLoading(false)
    }
  }

  const roleLabel = user?.role
    ? user.role === 'professional_investor'
      ? 'Professional investor'
      : user.role === 'real_estate_agency'
        ? 'Real estate agency'
        : user.role === 'developer_fund'
          ? 'Property developer & funds'
          : 'Individual investor'
    : '—'

  return (
    <div className="page-dashboard">
      <header className="page-head">
        <h1>Dashboard</h1>
        <p>
          Welcome, <strong>{user?.name}</strong>. This is your professional workspace (demo data). Role: <strong>{roleLabel}</strong>.
        </p>
      </header>

      <div className="dash-shell">
        <aside className="dash-sidebar">
          <div className="dash-sidebar__title">Navigation</div>
          <button
            type="button"
            className={`dash-tab-btn${tab === 'overview' ? ' dash-tab-btn--active' : ''}`}
            onClick={() => setTab('overview')}
          >
            <span className="dash-tab-btn__left">
              <TrendingUp size={18} />
              Overview
            </span>
          </button>
          <button
            type="button"
            className={`dash-tab-btn${tab === 'listings' ? ' dash-tab-btn--active' : ''}`}
            onClick={() => setTab('listings')}
          >
            <span className="dash-tab-btn__left">
              <LayoutGrid size={18} />
              Your listings
            </span>
            <span className="dash-tab-btn__badge">{mine.length}</span>
          </button>
          <button
            type="button"
            className={`dash-tab-btn${tab === 'saved' ? ' dash-tab-btn--active' : ''}`}
            onClick={() => setTab('saved')}
          >
            <span className="dash-tab-btn__left">
              <Heart size={18} />
              Saved
            </span>
            <span className="dash-tab-btn__badge">{savedCount}</span>
          </button>
          <button
            type="button"
            className={`dash-tab-btn${tab === 'ai' ? ' dash-tab-btn--active' : ''}`}
            onClick={() => setTab('ai')}
          >
            <span className="dash-tab-btn__left">
              <Sparkles size={18} />
              AI tools
            </span>
          </button>

          <div className="dash-sidebar__cta">
            <Link to="/post" className="btn btn--primary btn--block">
              <PlusCircle size={18} /> Publish
            </Link>
            <Link to="/import" className="btn btn--ghost btn--block" style={{ marginTop: 10 }}>
              <Upload size={18} /> Import CSV
            </Link>
            <Link to="/browse" className="btn btn--ghost btn--block" style={{ marginTop: 10 }}>
              Explore market
            </Link>
          </div>
        </aside>

        <section className="dash-content">
          {tab === 'overview' && (
            <div className="dash-grid">
              <section className="dash-card">
                <h2>Snapshot</h2>
                <ul className="dash-list">
                  <li>
                    <span>Your listings</span>
                    <strong>{mine.length}</strong>
                  </li>
                  <li>
                    <span>Saved</span>
                    <strong>{savedCount}</strong>
                  </li>
                  <li>
                    <span>Activity</span>
                    <strong>{mine.length + savedCount > 0 ? 'Active' : 'New'}</strong>
                  </li>
                </ul>
                <p className="dash-note">
                  In production, backend audit will show revisions/modifications. This demo keeps data
                  locally in your browser.
                </p>
              </section>

              <section className="dash-card">
                <h2>Professional workflow</h2>
                <div className="dash-actions">
                  <Link to="/post" className="dash-action">
                    <PlusCircle size={22} />
                    Publish a listing
                  </Link>
                  <Link to="/map" className="dash-action dash-action--muted">
                    <TrendingUp size={22} />
                    View market map
                  </Link>
                  <button type="button" className="dash-action dash-action--muted" onClick={() => setTab('ai')}>
                    <Sparkles size={22} />
                    Run price estimate
                  </button>
                </div>
              </section>
            </div>
          )}

          {tab === 'listings' && (
            <section className="dash-table-wrap">
              <h2 className="dash-table-title">Your listings</h2>
              {mine.length === 0 ? (
                <p className="dash-empty">
                  No listings yet.{' '}
                  <Link to="/post" className="text-link">
                    Publish one
                  </Link>
                  .
                </p>
              ) : (
                <table className="dash-table">
                  <thead>
                    <tr>
                      <th>Title</th>
                      <th>City</th>
                      <th>Price</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {mine.map((l) => (
                      <tr key={l.id}>
                        <td>
                          <Link to={`/property/${l.id}`} className="text-link">
                            {l.title}
                          </Link>
                        </td>
                        <td>{l.city}</td>
                        <td>
                          {new Intl.NumberFormat('fr-FR', {
                            style: 'currency',
                            currency: l.currency,
                            maximumFractionDigits: 0,
                          }).format(l.price)}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn btn--ghost btn--icon"
                            aria-label={`Delete ${l.title}`}
                            onClick={() => {
                              if (
                                window.confirm(
                                  'Remove this listing from the demo? (local only)',
                                )
                              )
                                removeUserListing(l.id)
                            }}
                          >
                            <Trash2 size={18} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          )}

          {tab === 'saved' && (
            <section>
              <h2 className="dash-table-title">Saved listings</h2>
              {saved.length === 0 ? (
                <p className="dash-empty">No saved listings yet. Heart a property to keep it here.</p>
              ) : (
                <div className="property-grid">
                  {saved.map((l, i) => (
                    <PropertyCard key={l.id} listing={l} index={i} />
                  ))}
                </div>
              )}
            </section>
          )}

          {tab === 'ai' && (
            <section className="dash-card">
              <h2>AI price estimate (demo)</h2>
              <p className="dash-note">
                This calls your Node backend endpoint <code>/ai/price-estimate</code>. It works
                without login.
              </p>

              <div className="filters" style={{ marginBottom: 0 }}>
                <label className="field field--grow">
                  <span>City</span>
                  <input value={aiCity} onChange={(e) => setAiCity(e.target.value)} />
                </label>
                <label className="field">
                  <span>Type</span>
                  <select value={aiType} onChange={(e) => setAiType(e.target.value as any)}>
                    <option value="apartment">Apartment</option>
                    <option value="house">House</option>
                    <option value="studio">Studio</option>
                    <option value="loft">Loft</option>
                  </select>
                </label>
                <label className="field">
                  <span>Area (m²)</span>
                  <input
                    type="number"
                    value={aiArea}
                    min={10}
                    onChange={(e) => setAiArea(Number(e.target.value))}
                  />
                </label>
                <label className="field">
                  <span>Rooms</span>
                  <input
                    type="number"
                    value={aiRooms}
                    min={1}
                    onChange={(e) => setAiRooms(Number(e.target.value))}
                  />
                </label>
              </div>

              <div style={{ marginTop: 14 }}>
                <button type="button" className="btn btn--primary" disabled={aiLoading} onClick={runPriceEstimate}>
                  <Sparkles size={18} /> {aiLoading ? 'Estimating…' : 'Estimate price'}
                </button>
              </div>

              {aiResult && (
                <div className="success-banner" style={{ marginTop: 16 }}>
                  <p style={{ marginBottom: 8 }}>
                    <strong>Estimated price:</strong>{' '}
                    {new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(
                      aiResult.estimate,
                    )}{' '}
                    €
                  </p>
                  <p className="dash-note">
                    Confidence: <strong>{Math.round(aiResult.confidence * 100)}%</strong>
                  </p>
                </div>
              )}
            </section>
          )}
        </section>
      </div>
    </div>
  )
}
