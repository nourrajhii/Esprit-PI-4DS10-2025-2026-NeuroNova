import { Link } from 'react-router-dom'
import { PlusCircle, Trash2, TrendingUp } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useListings, removeUserListing } from '../lib/listingsStore'
import { useFavorites } from '../lib/favoritesStore'

export function Dashboard() {
  const { user } = useAuth()
  const listings = useListings()
  const { count: savedCount } = useFavorites()

  const mine = listings.filter((l) => l.id.startsWith('u-'))

  return (
    <div className="page-dashboard">
      <header className="page-head">
        <h1>Dashboard</h1>
        <p>
          Welcome, <strong>{user?.name}</strong>. Your published listings are stored in this browser
          for the demo.
        </p>
      </header>

      <div className="dash-grid">
        <section className="dash-card">
          <h2>Quick actions</h2>
          <div className="dash-actions">
            <Link to="/post" className="dash-action">
              <PlusCircle size={22} />
              New listing
            </Link>
            <Link to="/browse" className="dash-action dash-action--muted">
              <TrendingUp size={22} />
              Market explore
            </Link>
          </div>
        </section>
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
              <span>Leads</span>
              <strong>—</strong>
            </li>
          </ul>
          <p className="dash-note">
            Connect CRM or database for real pipeline metrics. Saved count uses local favorites.
          </p>
        </section>
      </div>

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
                        if (window.confirm('Remove this listing from the demo?')) removeUserListing(l.id)
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
    </div>
  )
}
