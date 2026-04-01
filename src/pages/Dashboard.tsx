import { Link } from 'react-router-dom'
import { PlusCircle, TrendingUp } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export function Dashboard() {
  const { user } = useAuth()

  return (
    <div className="page-dashboard">
      <header className="page-head">
        <h1>Dashboard</h1>
        <p>
          Welcome, <strong>{user?.name}</strong>. This panel is ready for analytics and listing
          management.
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
          <h2>Pipeline (demo)</h2>
          <ul className="dash-list">
            <li>
              <span>Drafts</span>
              <strong>0</strong>
            </li>
            <li>
              <span>Live</span>
              <strong>0</strong>
            </li>
            <li>
              <span>Leads</span>
              <strong>—</strong>
            </li>
          </ul>
          <p className="dash-note">
            Connect CRM or database to show real counts. Add WebSockets for live lead alerts.
          </p>
        </section>
      </div>
    </div>
  )
}
