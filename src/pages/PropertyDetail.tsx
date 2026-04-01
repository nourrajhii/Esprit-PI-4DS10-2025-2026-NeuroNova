import { lazy, Suspense } from 'react'
import { Link, useParams } from 'react-router-dom'
import { MapPin, Maximize2, DoorOpen, Calendar } from 'lucide-react'
import { MOCK_LISTINGS } from '../data/mockListings'

const Property3DPreview = lazy(() =>
  import('../components/Property3DPreview').then((m) => ({ default: m.Property3DPreview })),
)

export function PropertyDetail() {
  const { id } = useParams()
  const listing = MOCK_LISTINGS.find((l) => l.id === id)

  if (!listing) {
    return (
      <div className="page-detail empty-state">
        <h1>Listing not found</h1>
        <Link to="/browse" className="text-link">
          Back to explore
        </Link>
      </div>
    )
  }

  const price = new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: listing.currency,
    maximumFractionDigits: 0,
  }).format(listing.price)

  return (
    <div className="page-detail">
      <Link to="/browse" className="back-link">
        ← All listings
      </Link>
      <div className="detail-hero">
        <img src={listing.image} alt="" className="detail-hero__img" />
        <div className="detail-hero__overlay">
          <span className="detail-badge">{listing.type}</span>
          <h1>{listing.title}</h1>
          <p className="detail-price">{price}</p>
        </div>
      </div>

      <div className="detail-grid">
        <div className="detail-main">
          <p className="detail-desc">{listing.description}</p>
          <ul className="detail-facts">
            <li>
              <MapPin size={18} /> {listing.city}
            </li>
            <li>
              <DoorOpen size={18} /> {listing.rooms} rooms
            </li>
            <li>
              <Maximize2 size={18} /> {listing.areaM2} m²
            </li>
            <li>
              <Calendar size={18} /> Listed {listing.publishedAt}
            </li>
          </ul>
        </div>
        <aside className="detail-aside">
          <h2>Layout preview</h2>
          <p className="detail-aside__note">
            Abstract WebGL room — replace with your GLTF or Matterport embed for production.
          </p>
          <Suspense fallback={<div className="preview-3d preview-3d--loading" aria-hidden />}>
            <Property3DPreview />
          </Suspense>
        </aside>
      </div>
    </div>
  )
}
