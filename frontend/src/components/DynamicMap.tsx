'use client'
import { useEffect, useRef } from 'react'

interface Marker {
  lat: number
  lng: number
  label?: string
  popup?: string
  color?: string
}

interface Props {
  center?: [number, number]
  zoom?: number
  markers?: Marker[]
  height?: string
}

export default function DynamicMap({ center = [33.8869, 9.5375], zoom = 6, markers = [], height = '400px' }: Props) {
  const mapRef      = useRef<HTMLDivElement>(null)
  const mapInstance = useRef<unknown>(null)

  // ── Init map ONCE ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (mapInstance.current) return
    if (!mapRef.current) return

    // Clean any leftover Leaflet state on the container
    if ((mapRef.current as unknown as Record<string, unknown>)._leaflet_id) {
      (mapRef.current as unknown as Record<string, unknown>)._leaflet_id = null
    }

    import('leaflet').then((L) => {
      if (!mapRef.current) return
      if (mapInstance.current) return

      // Fix default marker icons
      delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
        iconUrl:       'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
        shadowUrl:     'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
      })

      const map = L.map(mapRef.current, { center, zoom })
      mapInstance.current = map

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
      }).addTo(map)

      markers.forEach(({ lat, lng, popup, color }) => {
        const marker = L.circleMarker([lat, lng], {
          radius: 8,
          fillColor: color || '#00204a',
          color: '#fff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.85,
        }).addTo(map)
        if (popup) marker.bindPopup(popup)
      })
    })

    return () => {
      if (mapInstance.current) {
        ;(mapInstance.current as { remove: () => void }).remove()
        mapInstance.current = null
      }
    }
  }, []) // runs once only

  // ── React to center/zoom prop changes ─────────────────────────────────────
  useEffect(() => {
    if (mapInstance.current && center) {
      ;(mapInstance.current as { setView: (c: [number, number], z: number) => void })
        .setView(center, zoom)
    }
  }, [center, zoom])

  return <div ref={mapRef} style={{ height, width: '100%', borderRadius: '0.75rem' }} />
}
