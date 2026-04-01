import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import '../lib/mapIcons'
import { coordsForCity } from '../data/cityCoords'
import { useListings } from '../lib/listingsStore'

const FR_CENTER: [number, number] = [46.603354, 1.888334]
const DEFAULT_ZOOM = 5.5

export function MapPage() {
  const listings = useListings()

  const markers = useMemo(
    () =>
      listings.map((l) => ({
        id: l.id,
        title: l.title,
        city: l.city,
        price: new Intl.NumberFormat('fr-FR', {
          style: 'currency',
          currency: l.currency,
          maximumFractionDigits: 0,
        }).format(l.price),
        position: coordsForCity(l.city) as [number, number],
      })),
    [listings],
  )

  return (
    <div className="page-map">
      <header className="page-head">
        <h1>Map</h1>
        <p>Listings by city — coordinates come from a static lookup; plug geocoding for precision.</p>
      </header>
      <div className="map-wrap">
        <MapContainer
          center={FR_CENTER}
          zoom={DEFAULT_ZOOM}
          className="map-leaflet"
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {markers.map((m) => (
            <Marker key={m.id} position={m.position}>
              <Popup>
                <strong>{m.title}</strong>
                <br />
                {m.city} · {m.price}
                <br />
                <Link to={`/property/${m.id}`} className="text-link">
                  View listing
                </Link>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}
