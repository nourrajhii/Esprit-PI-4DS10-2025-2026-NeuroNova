'use client'
import { useState } from 'react'
import { searchListings } from '@/lib/api'
import SubscriptionGuard from '@/components/SubscriptionGuard'
import { formatTND, formatM2 } from '@/lib/utils'
import InvestmentBadge from '@/components/InvestmentBadge'
import RadarChart from '@/components/RadarChart'
import { GitCompare, Search, X, Loader2, Plus } from 'lucide-react'
import ListingCard from '@/components/ListingCard'

interface Listing {
  id: string
  title: string
  price: number
  city: string
  surface_m2?: number
  size?: number
  rooms?: number
  bathrooms?: number
  transaction_type?: string
  property_type?: string
  price_prediction?: { predicted_price_tnd?: number; price_per_m2_tnd?: number }
  investment?: { verdict?: string; score?: number; roi_5y_pct?: number; rental_yield_pct?: number; annual_rent_est_tnd?: number }
  geo?: { overall_score?: number; scores?: Record<string, number>; radar?: { axis: string; value: number }[] }
  url?: string
}

const MAX_COMPARE = 3

function CompareContent() {
  const [selected, setSelected] = useState<Listing[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Listing[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  async function doSearch() {
    if (!searchQuery.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const res = await searchListings(searchQuery)
      setSearchResults(res?.data?.listings?.properties || [])
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  function addToCompare(listing: Listing) {
    if (selected.length >= MAX_COMPARE) return
    if (selected.find(s => s.id === listing.id)) return
    setSelected(prev => [...prev, listing])
  }

  function removeFromCompare(id: string) {
    setSelected(prev => prev.filter(s => s.id !== id))
  }

  const fields = [
    { label: 'Prix', render: (l: Listing) => formatTND(l.price) },
    { label: 'Surface', render: (l: Listing) => formatM2(l.surface_m2 || l.size) },
    { label: 'Ville', render: (l: Listing) => l.city || '—' },
    { label: 'Chambres', render: (l: Listing) => l.rooms ? `${l.rooms} ch.` : '—' },
    { label: 'Prix IA', render: (l: Listing) => formatTND(l.price_prediction?.predicted_price_tnd) },
    { label: 'Prix/m² IA', render: (l: Listing) => l.price_prediction?.price_per_m2_tnd ? `${l.price_prediction.price_per_m2_tnd.toLocaleString()} TND` : '—' },
    { label: 'Verdict', render: (l: Listing) => l.investment?.verdict ? <InvestmentBadge verdict={l.investment.verdict} score={l.investment.score} size="sm" /> : '—' },
    { label: 'ROI 5 ans', render: (l: Listing) => l.investment?.roi_5y_pct ? `${l.investment.roi_5y_pct}%` : '—' },
    { label: 'Rendement locatif', render: (l: Listing) => l.investment?.rental_yield_pct ? `${l.investment.rental_yield_pct}%` : '—' },
    { label: 'Score quartier', render: (l: Listing) => l.geo?.overall_score ? `${l.geo.overall_score}/100` : '—' },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2 mb-1">
          <GitCompare className="w-6 h-6 text-brand-600" /> Comparer des biens
        </h1>
        <p className="text-slate-500 text-sm">Comparez jusqu'à {MAX_COMPARE} biens côte à côte sur tous les critères</p>
      </div>

      {/* Search */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <h2 className="font-semibold text-slate-700">Rechercher des biens à comparer</h2>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doSearch()}
              placeholder="Appartement Tunis, villa Hammamet..."
              className="w-full pl-9 pr-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <button onClick={doSearch} disabled={loading} className="px-5 py-2.5 bg-brand-600 text-white text-sm font-medium rounded-xl hover:bg-brand-700 transition-colors disabled:opacity-50 flex items-center gap-2">
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            Chercher
          </button>
        </div>

        {searched && searchResults.length === 0 && !loading && (
          <p className="text-slate-400 text-sm">Aucun résultat.</p>
        )}

        {searchResults.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-96 overflow-y-auto">
            {searchResults.map(l => (
              <div key={l.id} className="relative">
                <ListingCard listing={l} />
                <button
                  onClick={() => addToCompare(l)}
                  disabled={selected.length >= MAX_COMPARE || !!selected.find(s => s.id === l.id)}
                  className="absolute bottom-4 left-4 right-4 bg-emerald-600 text-white text-xs font-medium py-1.5 rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-40 flex items-center justify-center gap-1"
                >
                  <Plus className="w-3 h-3" />
                  {selected.find(s => s.id === l.id) ? 'Ajouté' : 'Comparer'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Comparison table */}
      {selected.length > 0 && (
        <div className="space-y-6">
          {/* Selected listings header */}
          <div className="grid gap-4" style={{ gridTemplateColumns: `160px repeat(${selected.length}, 1fr)` }}>
            <div />
            {selected.map(l => (
              <div key={l.id} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm relative">
                <button
                  onClick={() => removeFromCompare(l.id)}
                  className="absolute top-2 right-2 text-slate-400 hover:text-red-500 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
                <p className="font-medium text-slate-800 text-sm line-clamp-2 pr-6">{l.title}</p>
                <p className="text-brand-700 font-bold mt-1">{formatTND(l.price)}</p>
                <p className="text-xs text-slate-500">{l.city}</p>
              </div>
            ))}
          </div>

          {/* Comparison rows */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {fields.map(({ label, render }, i) => (
              <div
                key={label}
                className={`grid gap-0 ${i % 2 === 0 ? 'bg-slate-50' : 'bg-white'}`}
                style={{ gridTemplateColumns: `160px repeat(${selected.length}, 1fr)` }}
              >
                <div className="px-4 py-3 text-xs font-semibold text-slate-600 border-r border-slate-100 flex items-center">
                  {label}
                </div>
                {selected.map(l => (
                  <div key={l.id} className="px-4 py-3 text-sm text-slate-700 border-r border-slate-100 last:border-0 flex items-center">
                    {render(l)}
                  </div>
                ))}
              </div>
            ))}
          </div>

          {/* Radar charts */}
          {selected.some(l => l.geo?.radar) && (
            <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${selected.length}, 1fr)` }}>
              {selected.map(l => l.geo?.radar ? (
                <div key={l.id} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <RadarChart data={l.geo.radar} title={`Quartier — ${l.city}`} />
                </div>
              ) : (
                <div key={l.id} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-center text-slate-400 text-sm">
                  Données géo indisponibles
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {selected.length === 0 && !searched && (
        <div className="text-center py-16 text-slate-400">
          <GitCompare className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>Recherchez des biens et ajoutez-les à la comparaison</p>
        </div>
      )}
    </div>
  )
}

export default function ComparePage() {
  return <SubscriptionGuard><CompareContent /></SubscriptionGuard>
}
