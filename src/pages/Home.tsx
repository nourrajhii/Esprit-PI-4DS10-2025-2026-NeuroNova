import { lazy, Suspense } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Box, Layers, Shield } from 'lucide-react'
import { PropertyCard } from '../components/PropertyCard'
import { MOCK_LISTINGS } from '../data/mockListings'

const Property3DPreview = lazy(() =>
  import('../components/Property3DPreview').then((m) => ({ default: m.Property3DPreview })),
)

export function Home() {
  const featured = MOCK_LISTINGS.slice(0, 3)

  return (
    <div className="page-home">
      <section className="hero">
        <div className="hero__copy">
          <motion.p
            className="eyebrow"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            For investors & buyers
          </motion.p>
          <motion.h1
            className="hero__title"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.05 }}
          >
            Property search,
            <br />
            <span className="hero__accent">engineered</span> for clarity.
          </motion.h1>
          <motion.p
            className="hero__lead"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            Browse curated listings, preview spatial layouts in 3D, and publish announcements —
            one surface built in React for speed and a credible investor demo.
          </motion.p>
          <motion.div
            className="hero__cta"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.28, duration: 0.45 }}
          >
            <Link to="/browse" className="btn btn--primary btn--lg">
              Explore listings
              <ArrowRight size={20} />
            </Link>
            <Link to="/register" className="btn btn--outline btn--lg">
              Create account
            </Link>
          </motion.div>
        </div>
        <motion.div
          className="hero__visual"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.65, delay: 0.1 }}
        >
          <Suspense fallback={<div className="preview-3d preview-3d--loading" aria-hidden />}>
            <Property3DPreview />
          </Suspense>
        </motion.div>
      </section>

      <section className="pillars">
        <h2 className="section-title">Why REAL stands out</h2>
        <div className="pillar-grid">
          <article className="pillar">
            <Box className="pillar__icon" size={28} strokeWidth={1.5} />
            <h3>3D spatial preview</h3>
            <p>
              WebGL preview you can extend with GLTF floor plans, BIM exports, or embedded tours —
              not just static photos.
            </p>
          </article>
          <article className="pillar">
            <Layers className="pillar__icon" size={28} strokeWidth={1.5} />
            <h3>Structured announcements</h3>
            <p>
              Listings carry consistent fields for rooms, area, and type — ready to sync with CRM or
              MLS-style feeds.
            </p>
          </article>
          <article className="pillar">
            <Shield className="pillar__icon" size={28} strokeWidth={1.5} />
            <h3>Account-ready</h3>
            <p>
              Sign-in, sign-up, and protected routes are wired for you to plug in real auth and
              persistence.
            </p>
          </article>
        </div>
      </section>

      <section className="featured">
        <div className="featured__head">
          <h2 className="section-title">Featured listings</h2>
          <Link to="/browse" className="text-link">
            View all
            <ArrowRight size={16} />
          </Link>
        </div>
        <div className="property-grid">
          {featured.map((l, i) => (
            <PropertyCard key={l.id} listing={l} index={i} />
          ))}
        </div>
      </section>
    </div>
  )
}
