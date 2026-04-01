import { useState } from 'react'
import { Link } from 'react-router-dom'

export function PostListing() {
  const [title, setTitle] = useState('')
  const [city, setCity] = useState('')
  const [submitted, setSubmitted] = useState(false)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitted(true)
  }

  return (
    <div className="page-post">
      <header className="page-head">
        <h1>Publish a listing</h1>
        <p>
          Demo form — wire fields to your API, add image upload, and moderation before go-live.
        </p>
      </header>

      {submitted ? (
        <div className="success-banner">
          <p>
            <strong>Draft received (demo).</strong> In production, this would create a record and
            notify your team.
          </p>
          <Link to="/dashboard" className="text-link">
            Go to dashboard →
          </Link>
        </div>
      ) : (
        <form className="post-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Title</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Bright 2BR near central station"
              required
            />
          </label>
          <label className="field">
            <span>City</span>
            <input
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="e.g. Bordeaux"
              required
            />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea rows={5} placeholder="Key facts, condition, energy class…" />
          </label>
          <div className="field-row">
            <label className="field">
              <span>Price (€)</span>
              <input type="number" min={0} placeholder="350000" />
            </label>
            <label className="field">
              <span>Area (m²)</span>
              <input type="number" min={0} placeholder="72" />
            </label>
          </div>
          <button type="submit" className="btn btn--primary">
            Submit draft
          </button>
        </form>
      )}
    </div>
  )
}
