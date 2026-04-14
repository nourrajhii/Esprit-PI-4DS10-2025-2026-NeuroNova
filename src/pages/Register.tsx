import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import type { UserRole } from '../contexts/AuthContext'

export function Register() {
  const { register, user } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('developer_fund')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) navigate('/dashboard', { replace: true })
  }, [user, navigate])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErr('')
    if (!name.trim() || !email.trim()) {
      setErr('Name and email are required.')
      return
    }
    if (password.length < 6) {
      setErr('Use at least 6 characters for the password (demo).')
      return
    }
    setLoading(true)
    try {
      await register(name.trim(), email.trim(), password, role)
      navigate('/dashboard', { replace: true })
    } catch {
      setErr('Could not create account.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Create account</h1>
        <p className="auth-lead">
          Register to publish listings and access the dashboard.
        </p>
        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field">
            <span>Full name</span>
            <input
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Alex Dupont"
            />
          </label>
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </label>
          <label className="field">
            <span>Account type</span>
            <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
              <option value="individual_investor">Individual investor</option>
              <option value="professional_investor">Professional investor</option>
              <option value="real_estate_agency">Real estate agency</option>
              <option value="developer_fund">Property developer & funds</option>
            </select>
          </label>
          {err && <p className="form-error">{err}</p>}
          <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
            {loading ? 'Creating…' : 'Create account'}
          </button>
        </form>
        <p className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
