import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import '../lib/mapIcons'
import { coordsForCity } from '../data/cityCoords'
import { useListings } from '../lib/listingsStore'

const TN_CENTER: [number, number] = [34.0, 9.0]
const DEFAULT_ZOOM = 6.5

export function MapPage() {
  const listings = useListings()

  const markers = useMemo(
    () =>
      listings.map((l) => ({
        id: l.id,
        title: l.title,
        city: l.city,
        externalUrl: l.externalUrl,
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
        <p>Tunisia-only map — markers are placed by city name (static lookup). Add geocoding for exact addresses.</p>
      </header>
      <div className="map-wrap">
        <MapContainer
          center={TN_CENTER}
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
                {m.externalUrl ? (
                  <a className="text-link" href={m.externalUrl} target="_blank" rel="noreferrer">
                    Open source →
                  </a>
                ) : (
                  <Link to={`/property/${m.id}`} className="text-link">
                    View listing →
                  </Link>
                )}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}
