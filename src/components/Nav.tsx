import { Link, NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Building2, LayoutDashboard, LogIn, LogOut, Map, PlusCircle, Search } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `nav-link${isActive ? ' nav-link--active' : ''}`

export function Nav() {
  const { user, logout } = useAuth()

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Link to="/" className="brand">
          <motion.span
            className="brand__mark"
            whileHover={{ rotate: [0, -4, 4, 0] }}
            transition={{ duration: 0.45 }}
          >
            <Building2 size={22} strokeWidth={2} />
          </motion.span>
          <span className="brand__text">
            <span className="brand__name">REAL</span>
            <span className="brand__tag">property intelligence</span>
          </span>
        </Link>

        <nav className="site-nav" aria-label="Primary">
          <NavLink to="/browse" className={linkClass}>
            <Search size={18} aria-hidden />
            Explore
          </NavLink>
          <NavLink to="/map" className={linkClass}>
            <Map size={18} aria-hidden />
            Map
          </NavLink>
          {user && (
            <>
              <NavLink to="/post" className={linkClass}>
                <PlusCircle size={18} aria-hidden />
                Publish
              </NavLink>
              <NavLink to="/dashboard" className={linkClass}>
                <LayoutDashboard size={18} aria-hidden />
                Dashboard
              </NavLink>
            </>
          )}
        </nav>

        <div className="site-header__auth">
          {user ? (
            <>
              <span className="user-pill" title={user.email}>
                {user.name}
              </span>
              <button type="button" className="btn btn--ghost" onClick={logout}>
                <LogOut size={18} />
                Sign out
              </button>
            </>
          ) : (
            <Link to="/login" className="btn btn--primary">
              <LogIn size={18} />
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
