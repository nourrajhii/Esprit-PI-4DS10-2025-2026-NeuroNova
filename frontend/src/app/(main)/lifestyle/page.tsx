'use client'
import { useState, useEffect, useRef } from 'react'
import SubscriptionGuard from '@/components/SubscriptionGuard'
import { MapPin, Send, RotateCcw, Loader2, Home, TrendingUp, Bus, GraduationCap, ShieldCheck, Leaf, ShoppingBag } from 'lucide-react'

const BASE = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8000'

interface ZoneScore {
  schools_score: number
  shops_score: number
  transport_score: number
  green_score: number
  calm_score_est: number
  safety_score_est: number
  invest_score_est: number
  health_score: number
  parking_score: number
}

interface Zone {
  zone: string
  match_score: number
  lat: number
  lon: number
  scores: ZoneScore
  osm: Record<string, number>
}

interface Listing {
  title: string
  zone: string
  price: number | null
  surface_m2: number | null
  transaction_type: string
  url: string | null
  match_score: number
  lat: number
  lon: number
}

interface Profile {
  lifestyle: string
  budget: number
  priority: string
}

interface MatchResult {
  profile: Profile
  zones: Zone[]
  top_zones: Zone[]
  listings: Listing[]
  has_listings: boolean
}

const QUICK_PROMPTS = [
  "Je suis une famille avec 2 enfants, budget 550 000 DT, quartier calme avec bonnes écoles",
  "Investisseur immobilier, budget 400k DT, fort potentiel plus-value",
  "Étudiant à l'université, budget 200 000 DT, proche transport et commerces",
  "Jeune professionnel, budget 300k DT, actif, proche métro et restaurants",
  "Retraité, budget 400 000 DT, calme et sécurisé avec espaces verts",
]

const LIFESTYLE_LABELS: Record<string, string> = {
  family:    'Famille',
  young_pro: 'Jeune Pro',
  investor:  'Investisseur',
  student:   'Étudiant',
  retired:   'Retraité',
}

const PRIORITY_LABELS: Record<string, string> = {
  safety:     'Sécurité',
  transport:  'Transport',
  schools:    'Écoles',
  amenities:  'Commerces',
  investment: 'Investissement',
}

function scoreColor(score: number) {
  if (score >= 70) return '#16a34a'
  if (score >= 50) return '#d97706'
  return '#dc2626'
}

function scoreBg(score: number) {
  if (score >= 70) return 'bg-green-50 text-green-700 border-green-200'
  if (score >= 50) return 'bg-amber-50 text-amber-700 border-amber-200'
  return 'bg-red-50 text-red-700 border-red-200'
}

const SCORE_DIMS = [
  { key: 'safety_score_est', label: 'Sécurité',  icon: ShieldCheck, color: '#6366f1' },
  { key: 'calm_score_est',   label: 'Calme',      icon: Leaf,        color: '#22c55e' },
  { key: 'schools_score',    label: 'Écoles',     icon: GraduationCap, color: '#f59e0b' },
  { key: 'transport_score',  label: 'Transport',  icon: Bus,         color: '#3b82f6' },
  { key: 'shops_score',      label: 'Commerces',  icon: ShoppingBag, color: '#ec4899' },
  { key: 'invest_score_est', label: 'Invest.',    icon: TrendingUp,  color: '#8b5cf6' },
  { key: 'green_score',      label: 'Nature',     icon: Leaf,        color: '#10b981' },
]

function LifestyleContent() {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<MatchResult | null>(null)
  const [error, setError] = useState('')
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null)
  const mapRef = useRef<HTMLDivElement>(null)
  const leafletMapRef = useRef<any>(null)
  const markersRef = useRef<any[]>([])

  // Load Leaflet dynamically (SSR-safe)
  useEffect(() => {
    if (typeof window === 'undefined') return
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(link)
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.onload = () => initMap()
    document.head.appendChild(script)
  }, [])

  function initMap() {
    if (!mapRef.current || leafletMapRef.current) return
    const L = (window as any).L
    if (!L) return
    const map = L.map(mapRef.current, { zoomControl: true }).setView([36.85, 10.22], 12)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap © CARTO',
      maxZoom: 18,
    }).addTo(map)
    leafletMapRef.current = map
  }

  function renderMap(zones: Zone[]) {
    const L = (window as any).L
    if (!L || !leafletMapRef.current) return
    const map = leafletMapRef.current

    // Clear old markers
    markersRef.current.forEach(m => map.removeLayer(m))
    markersRef.current = []

    zones.forEach(zone => {
      const color = scoreColor(zone.match_score)
      const radius = 8 + zone.match_score / 12

      const circle = L.circleMarker([zone.lat, zone.lon], {
        radius,
        color,
        fillColor: color,
        fillOpacity: 0.75,
        weight: 2,
      })

      circle.bindTooltip(`${zone.zone} — ${zone.match_score.toFixed(0)}/100`, { permanent: false })
      circle.on('click', () => setSelectedZone(zone))
      circle.addTo(map)
      markersRef.current.push(circle)

      // Zone label
      const label = L.divIcon({
        className: '',
        html: `<div style="background:rgba(255,255,255,0.9);border:1px solid #ddd;border-radius:4px;padding:2px 6px;font-size:10px;font-weight:500;color:#333;white-space:nowrap;pointer-events:none">${zone.zone}</div>`,
        iconAnchor: [40, -6],
      })
      const labelMarker = L.marker([zone.lat, zone.lon], { icon: label, interactive: false })
      labelMarker.addTo(map)
      markersRef.current.push(labelMarker)
    })

    // Fit bounds
    if (zones.length > 0) {
      const bounds = L.latLngBounds(zones.map(z => [z.lat, z.lon]))
      map.fitBounds(bounds, { padding: [40, 40] })
    }
  }

  async function search(text: string) {
    if (!text.trim() || loading) return
    setError('')
    setSelectedZone(null)
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/lifestyle/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: text, top_n: 10 }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: MatchResult = await res.json()
      setResult(data)
      setTimeout(() => renderMap(data.zones), 100)
    } catch (e: unknown) {
      setError('Erreur de connexion. ' + (e instanceof Error ? e.message : ''))
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setResult(null)
    setSelectedZone(null)
    setError('')
    setPrompt('')
    // Clear markers
    if (leafletMapRef.current) {
      markersRef.current.forEach(m => leafletMapRef.current.removeLayer(m))
      markersRef.current = []
      leafletMapRef.current.setView([36.85, 10.22], 12)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <MapPin className="w-6 h-6 text-brand-600" />
            ImmoMatch — Lifestyle Match
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Décrivez votre style de vie, l'IA trouve les quartiers qui vous correspondent
          </p>
        </div>
        {result && (
          <button onClick={reset} className="flex items-center gap-1.5 px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">
            <RotateCcw className="w-4 h-4" />
            Nouvelle recherche
          </button>
        )}
      </div>

      {/* Search */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 space-y-3">
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          Décrivez votre profil et vos besoins
        </label>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); search(prompt) } }}
          placeholder="Ex: Je suis une famille avec 2 enfants, budget 550 000 DT, je cherche un quartier calme avec de bonnes écoles et des parcs…"
          rows={3}
          className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent"
          disabled={loading}
        />
        <div className="flex flex-wrap gap-2">
          {QUICK_PROMPTS.map((q, i) => (
            <button key={i} onClick={() => { setPrompt(q); search(q) }}
              className="text-xs px-3 py-1.5 rounded-full bg-brand-50 text-brand-700 border border-brand-100 hover:bg-brand-100 transition-colors">
              {q.slice(0, 45)}…
            </button>
          ))}
        </div>
        <div className="flex justify-end">
          <button onClick={() => search(prompt)} disabled={loading || !prompt.trim()}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 text-white rounded-xl hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium text-sm">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {loading ? 'Analyse en cours…' : 'Trouver mes quartiers'}
          </button>
        </div>
      </div>

      {error && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>
      )}

      {/* Profile chips */}
      {result && (
        <div className="flex flex-wrap gap-3 items-center">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Profil détecté :</span>
          <span className="text-xs px-3 py-1 rounded-full bg-brand-100 text-brand-700 font-medium">
            {LIFESTYLE_LABELS[result.profile.lifestyle] ?? result.profile.lifestyle}
          </span>
          <span className="text-xs px-3 py-1 rounded-full bg-slate-100 text-slate-700 font-medium">
            Budget : {result.profile.budget.toLocaleString('fr-TN')} DT
          </span>
          <span className="text-xs px-3 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-medium">
            Priorité : {PRIORITY_LABELS[result.profile.priority] ?? result.profile.priority}
          </span>
        </div>
      )}

      {/* Main content: map + results */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">

        {/* Map */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden" style={{ height: 520 }}>
          <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
          {!result && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center text-slate-400">
                <MapPin className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">La carte s'affichera après la recherche</p>
              </div>
            </div>
          )}
          {/* Legend */}
          <div className="absolute bottom-4 left-4 bg-white rounded-lg border border-slate-200 shadow-sm p-2.5 text-xs z-10 pointer-events-none">
            <div className="font-semibold text-slate-500 mb-1.5">Score de compatibilité</div>
            {[['#16a34a','≥ 70 — Excellent'],['#d97706','50-69 — Bon'],['#dc2626','< 50 — Moyen']].map(([c,l]) => (
              <div key={l} className="flex items-center gap-1.5 mb-1">
                <div className="w-3 h-3 rounded-full" style={{ background: c }} />
                <span className="text-slate-600">{l}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel */}
        <div className="space-y-4">

          {/* Zone detail popup */}
          {selectedZone && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="flex items-start justify-between p-4 border-b border-slate-100">
                <div>
                  <p className="font-semibold text-slate-800 text-sm">{selectedZone.zone}</p>
                  <p className="text-xs text-slate-400 mt-0.5">Données OSM en temps réel</p>
                </div>
                <div className="text-right">
                  <span className={`text-2xl font-bold`} style={{ color: scoreColor(selectedZone.match_score) }}>
                    {selectedZone.match_score.toFixed(0)}
                  </span>
                  <span className="text-xs text-slate-400">/100</span>
                </div>
              </div>
              <div className="p-4 space-y-2">
                {SCORE_DIMS.map(({ key, label, color }) => {
                  const val = selectedZone.scores[key as keyof ZoneScore] ?? 0
                  return (
                    <div key={key} className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 w-20">{label}</span>
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${val}%`, background: color }} />
                      </div>
                      <span className="text-xs font-medium text-slate-700 w-8 text-right">{val.toFixed(0)}</span>
                    </div>
                  )
                })}
              </div>
              <div className="px-4 pb-4 grid grid-cols-3 gap-2">
                {[
                  ['🏫', 'Écoles', selectedZone.osm.schools_count],
                  ['🚌', 'Transport', selectedZone.osm.transport_count],
                  ['🏪', 'Commerces', selectedZone.osm.shops_count],
                  ['🌳', 'Parcs', selectedZone.osm.green_spaces_count],
                  ['🏥', 'Santé', selectedZone.osm.health_count],
                  ['🅿️', 'Parking', selectedZone.osm.parking_count],
                ].map(([icon, label, val]) => (
                  <div key={label as string} className="bg-slate-50 rounded-lg p-2 text-center">
                    <div className="text-base">{icon}</div>
                    <div className="text-xs text-slate-500">{label}</div>
                    <div className="text-sm font-bold text-slate-800">{val}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top zones list */}
          {result && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Meilleurs quartiers</p>
              </div>
              <div className="divide-y divide-slate-100">
                {result.top_zones.map((zone, i) => (
                  <button key={zone.zone} onClick={() => {
                    setSelectedZone(zone)
                    leafletMapRef.current?.flyTo([zone.lat, zone.lon], 14)
                  }}
                    className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors text-left ${selectedZone?.zone === zone.zone ? 'bg-brand-50' : ''}`}>
                    <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-600 text-xs font-bold flex items-center justify-center flex-shrink-0">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800 truncate">{zone.zone}</p>
                      <div className="flex gap-2 mt-0.5">
                        <span className="text-xs text-slate-400">🏫 {zone.osm.schools_count}</span>
                        <span className="text-xs text-slate-400">🚌 {zone.osm.transport_count}</span>
                        <span className="text-xs text-slate-400">🌳 {zone.osm.green_spaces_count}</span>
                      </div>
                    </div>
                    <div className="flex-shrink-0">
                      <span className={`text-sm font-bold px-2 py-0.5 rounded-lg border ${scoreBg(zone.match_score)}`}>
                        {zone.match_score.toFixed(0)}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Listings */}
      {result && result.has_listings && result.listings.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Annonces correspondantes — {result.listings.length} bien{result.listings.length > 1 ? 's' : ''}
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-px bg-slate-100">
            {result.listings.map((listing, i) => (
              <div key={i} className="bg-white p-4 hover:bg-slate-50 transition-colors">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <p className="text-sm font-medium text-slate-800 leading-tight flex-1 line-clamp-2">{listing.title}</p>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-lg border flex-shrink-0 ${scoreBg(listing.match_score)}`}>
                    {listing.match_score.toFixed(0)}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-xs text-slate-400 mb-2">
                  <MapPin className="w-3 h-3" />
                  {listing.zone}
                </div>
                <div className="flex flex-wrap gap-2">
                  {listing.price != null && (
                    <span className="text-xs px-2 py-0.5 bg-brand-50 text-brand-700 rounded-md font-medium">
                      {listing.price.toLocaleString('fr-TN')} DT
                    </span>
                  )}
                  {listing.surface_m2 != null && (
                    <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded-md">
                      {listing.surface_m2} m²
                    </span>
                  )}
                  {listing.transaction_type && (
                    <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-500 rounded-md">
                      {listing.transaction_type}
                    </span>
                  )}
                </div>
                {listing.url && (
                  <a href={listing.url} target="_blank" rel="noopener noreferrer"
                    className="mt-2 text-xs text-brand-600 hover:underline block">
                    Voir l'annonce →
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Zone scores heatmap-style */}
      {result && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Analyse de tous les quartiers</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="text-left px-4 py-2 font-medium text-slate-500">Quartier</th>
                  <th className="text-right px-3 py-2 font-medium text-slate-500">Score</th>
                  {SCORE_DIMS.map(d => (
                    <th key={d.key} className="text-right px-3 py-2 font-medium text-slate-500">{d.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.zones.slice(0, 13).map((zone, i) => (
                  <tr key={zone.zone}
                    onClick={() => { setSelectedZone(zone); leafletMapRef.current?.flyTo([zone.lat, zone.lon], 14) }}
                    className={`border-b border-slate-50 cursor-pointer hover:bg-slate-50 ${i === 0 ? 'bg-green-50/50' : ''}`}>
                    <td className="px-4 py-2 font-medium text-slate-700">{zone.zone}</td>
                    <td className="px-3 py-2 text-right">
                      <span className="font-bold" style={{ color: scoreColor(zone.match_score) }}>
                        {zone.match_score.toFixed(0)}
                      </span>
                    </td>
                    {SCORE_DIMS.map(d => {
                      const val = zone.scores[d.key as keyof ZoneScore] ?? 0
                      return (
                        <td key={d.key} className="px-3 py-2 text-right">
                          <div className="inline-flex items-center gap-1">
                            <div className="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                              <div className="h-full rounded-full" style={{ width: `${val}%`, background: d.color }} />
                            </div>
                            <span className="text-slate-600 w-7">{val.toFixed(0)}</span>
                          </div>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="bg-brand-50 border border-brand-100 rounded-2xl p-4 text-sm text-brand-800">
        <p className="font-semibold mb-1">À propos de cet agent</p>
        <p className="text-brand-700">
          ImmoMatch analyse votre style de vie avec l'IA et le croise avec des données géospatiales réelles
          (OpenStreetMap / Overpass API) pour noter 13 quartiers tunisiens selon 7 dimensions :
          sécurité, calme, écoles, transports, commerces, investissement, nature.
        </p>
      </div>
    </div>
  )
}

export default function LifestylePage() {
  return <SubscriptionGuard><LifestyleContent /></SubscriptionGuard>
}
