'use client'
import Link from 'next/link'
import Image from 'next/image'
import { useState } from 'react'
import { formatTND, formatM2 } from '@/lib/utils'

// Curated fallback photos — always available, never broken
const FALLBACKS = [
  'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=800&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=800&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1583608205776-bfd35f0d9f83?w=800&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&auto=format&fit=crop',
]

function getFallback(id: string) {
  const n = id ? (parseInt(id.slice(-4), 16) || 0) % FALLBACKS.length : 0
  return FALLBACKS[n]
}

interface Listing {
  id: string
  title: string
  price: number
  price_predicted?: boolean
  city: string
  surface_m2?: number
  size?: number
  rooms?: number
  bathrooms?: number
  transaction_type?: string
  property_type?: string
  price_prediction?: { predicted_price_tnd?: number }
  investment?: { verdict?: string; score?: number; roi_5y_pct?: number }
  url?: string
  image_urls?: string[]
}

export default function ListingCard({ listing }: { listing: Listing }) {
  const surface   = listing.surface_m2 || listing.size
  const verdict   = listing.investment?.verdict
  const rawImages = listing.image_urls?.filter(Boolean) ?? []
  // imgIdx tracks which image we're trying; if all fail, use the deterministic Unsplash fallback
  const [imgIdx, setImgIdx]   = useState(0)
  const [useFallback, setUseFallback] = useState(rawImages.length === 0)
  const href = `/listing/${listing.id}?city=${listing.city}&price=${listing.price}&surface=${surface || 100}`

  function handleImgError() {
    if (imgIdx + 1 < rawImages.length) {
      setImgIdx(i => i + 1)  // try next image in the list
    } else {
      setUseFallback(true)   // all failed — use guaranteed Unsplash fallback
    }
  }

  const displaySrc = useFallback ? getFallback(listing.id) : (rawImages[imgIdx] ?? getFallback(listing.id))

  return (
    <div className="property-item mb-30">
      {/* Image */}
      <Link href={href} className="img" style={{ display: 'block', position: 'relative', height: '200px', overflow: 'hidden', backgroundColor: '#e8f0fe' }}>
        <Image
          src={displaySrc}
          alt={listing.title}
          fill
          className="object-cover"
          sizes="(max-width: 768px) 100vw, 33vw"
          onError={handleImgError}
          unoptimized
        />
        {listing.transaction_type && (
          <span style={{
            position: 'absolute', top: 10, left: 10, zIndex: 10,
            background: 'rgba(255,255,255,0.9)', color: '#00204a',
            padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
          }}>
            {listing.transaction_type}
          </span>
        )}
        {verdict && (
          <span style={{
            position: 'absolute', top: 10, right: 10, zIndex: 10,
            background: verdict === 'Excellent' ? '#005555' : verdict === 'Bon' ? '#0284c7' : '#888',
            color: '#fff', padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 700,
          }}>
            {verdict}
          </span>
        )}
        {rawImages.length > 1 && !useFallback && (
          <span style={{
            position: 'absolute', bottom: 8, right: 8, zIndex: 10,
            background: 'rgba(0,0,0,0.5)', color: '#fff', padding: '1px 8px', borderRadius: 20, fontSize: 11,
          }}>
            +{rawImages.length - 1} photos
          </span>
        )}
      </Link>

      {/* Content — overlaps image per template design */}
      <div className="property-content" style={{ position: 'relative', zIndex: 2, background: '#fff', padding: '24px', marginTop: '-70px', boxShadow: '0 1px 4px 0 rgba(0,0,0,0.08)' }}>
        <div className="price mb-2">
          <span>{formatTND(listing.price)}</span>
        </div>
        <p style={{ fontSize: 13, color: '#555', marginBottom: 4, lineHeight: 1.4 }}
           className="line-clamp-2">
          {listing.title}
        </p>
        <span className="city d-block mb-3" style={{ fontSize: 13 }}>{listing.city}</span>

        <div className="specs d-flex mb-4">
          {surface && (
            <span className="d-block d-flex align-items-center me-3">
              <span style={{ fontSize: 13 }}>📐</span>
              <span className="caption" style={{ marginLeft: 4 }}>{formatM2(surface)}</span>
            </span>
          )}
          {listing.rooms && (
            <span className="d-block d-flex align-items-center me-3">
              <span style={{ fontSize: 13 }}>🛏</span>
              <span className="caption" style={{ marginLeft: 4 }}>{listing.rooms} ch.</span>
            </span>
          )}
          {listing.bathrooms && (
            <span className="d-block d-flex align-items-center">
              <span style={{ fontSize: 13 }}>🚿</span>
              <span className="caption" style={{ marginLeft: 4 }}>{listing.bathrooms} sdb</span>
            </span>
          )}
        </div>

        {listing.investment?.roi_5y_pct && (
          <p style={{ fontSize: 12, color: '#005555', marginBottom: 12, fontWeight: 600 }}>
            ROI 5 ans: {listing.investment.roi_5y_pct}%
          </p>
        )}

        <Link href={href} className="btn btn-primary py-2 px-3">
          Voir l&apos;annonce
        </Link>
      </div>
    </div>
  )
}
