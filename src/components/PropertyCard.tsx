import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { MapPin, Maximize2, DoorOpen } from 'lucide-react'
import type { Listing } from '../data/mockListings'

type Props = { listing: Listing; index?: number }

function formatPrice(n: number, currency: string) {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(n)
}

export function PropertyCard({ listing, index = 0 }: Props) {
  return (
    <motion.article
      className="property-card"
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.45, delay: index * 0.06 }}
    >
      <Link to={`/property/${listing.id}`} className="property-card__link">
        <div className="property-card__media">
          <img src={listing.image} alt="" loading="lazy" />
          <span className="property-card__badge">{listing.type}</span>
        </div>
        <div className="property-card__body">
          <h3 className="property-card__title">{listing.title}</h3>
          <p className="property-card__loc">
            <MapPin size={14} aria-hidden />
            {listing.city}
          </p>
          <div className="property-card__meta">
            <span>
              <DoorOpen size={14} aria-hidden />
              {listing.rooms} rooms
            </span>
            <span>
              <Maximize2 size={14} aria-hidden />
              {listing.areaM2} m²
            </span>
          </div>
          <p className="property-card__price">
            {formatPrice(listing.price, listing.currency)}
          </p>
        </div>
      </Link>
    </motion.article>
  )
}
