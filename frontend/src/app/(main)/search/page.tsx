'use client'
import { useState, useEffect, useCallback, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { searchListings, getListings, MongoListing } from '@/lib/api'
import ListingCard from '@/components/ListingCard'
import { GOVERNORATS, GOVERNORAT_COORDS } from '@/lib/utils'
import { Search, SlidersHorizontal, Loader2, Grid3X3, Sparkles, ChevronLeft, ChevronRight } from 'lucide-react'
import dynamic from 'next/dynamic'

const DynamicMap = dynamic(() => import('@/components/DynamicMap'), { ssr: false })

interface AiListing {
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
  price_prediction?: { predicted_price_tnd?: number }
  investment?: { verdict?: string; score?: number; roi_5y_pct?: number }
  url?: string
  image_urls?: string[]
}

const PAGE_SIZE = 12

function mongoToCard(l: MongoListing) {
  return {
    id: l._id || l.id,
    title: l.title,
    price: l.price,
    city: l.city,
    surface_m2: l.surface_m2 ?? l.surface,
    rooms: l.rooms,
    bathrooms: l.bathrooms,
    property_type: l.property_type,
    transaction_type: l.transaction_type ?? l.type,
    image_urls: l.image_urls?.length ? l.image_urls : l.images,
  }
}

function SearchContent() {
  const params = useSearchParams()
  const initialQ = params.get('q') || ''

  const [tab, setTab] = useState<'browse' | 'ai'>(initialQ ? 'ai' : 'browse')

  // ── AI Search state ───────────────────────────────────────────────────────
  const [query, setQuery] = useState(initialQ)
  const [aiListings, setAiListings] = useState<AiListing[]>([])
  const [summary, setSummary] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiSearched, setAiSearched] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({ city: '', max_price: '', min_size: '', transaction_type: '' })

  // ── Browse state ──────────────────────────────────────────────────────────
  const [browseListings, setBrowseListings] = useState<MongoListing[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [browseLoading, setBrowseLoading] = useState(false)
  const [browseFilters, setBrowseFilters] = useState({
    city: '', min_price: '', max_price: '', rooms: '', type: '',
  })

  // ── Load browse on mount and filter change ────────────────────────────────
  const loadBrowse = useCallback(async (pg: number) => {
    setBrowseLoading(true)
    try {
      const data = await getListings({
        city:             browseFilters.city      || undefined,
        transaction_type: browseFilters.type      || undefined,
        min_price:        browseFilters.min_price  ? Number(browseFilters.min_price)  : undefined,
        max_price:        browseFilters.max_price  ? Number(browseFilters.max_price)  : undefined,
        rooms:            browseFilters.rooms      ? Number(browseFilters.rooms)      : undefined,
        limit:            PAGE_SIZE,
        skip:             pg * PAGE_SIZE,
      })
      setBrowseListings(data.listings)
      setTotal(data.total)
    } catch (e) {
      console.error(e)
    } finally {
      setBrowseLoading(false)
    }
  }, [browseFilters])

  useEffect(() => {
    if (tab === 'browse') loadBrowse(page)
  }, [tab, page, loadBrowse])

  useEffect(() => {
    setPage(0)
  }, [browseFilters])

  // ── AI search ─────────────────────────────────────────────────────────────
  async function doSearch(q: string) {
    if (!q.trim()) return
    setAiLoading(true)
    setAiSearched(true)
    try {
      const data = await searchListings(q, filters)
      setAiListings(data?.data?.listings?.properties || [])
      setSummary(data?.summary || '')
    } catch (e) {
      console.error(e)
    } finally {
      setAiLoading(false)
    }
  }

  useEffect(() => {
    if (initialQ) doSearch(initialQ)
  }, [])

  // ── Map markers ───────────────────────────────────────────────────────────
  const mapMarkers = (tab === 'ai' ? aiListings : browseListings).slice(0, 20).map(l => {
    const coords = GOVERNORAT_COORDS[l.city] || GOVERNORAT_COORDS['Tunis'] || [36.819, 10.166]
    const verdict = (l as AiListing).investment?.verdict
    return {
      lat: coords[0] + (Math.random() - 0.5) * 0.04,
      lng: coords[1] + (Math.random() - 0.5) * 0.04,
      popup: `<b>${l.title}</b><br>${l.price?.toLocaleString()} TND`,
      color: verdict === 'BUY' ? '#10b981' : verdict === 'AVOID' ? '#ef4444' : '#0284c7',
    }
  })

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-6">
      {/* Tab switcher */}
      <div className="flex gap-1 bg-slate-100 rounded-xl p-1 w-fit">
        <button
          onClick={() => setTab('browse')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
            tab === 'browse' ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <Grid3X3 className="w-4 h-4" /> Toutes les annonces
        </button>
        <button
          onClick={() => setTab('ai')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
            tab === 'ai' ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          <Sparkles className="w-4 h-4" /> Recherche IA
        </button>
      </div>

      {/* ── BROWSE TAB ─────────────────────────────────────────────────────── */}
      {tab === 'browse' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <h1 className="text-2xl font-bold text-slate-800">
              Annonces immobilières
              {total > 0 && <span className="ml-2 text-base font-normal text-slate-400">({total.toLocaleString()} biens)</span>}
            </h1>
          </div>

          {/* Browse filters */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-2 md:grid-cols-5 gap-3">
            <select
              value={browseFilters.city}
              onChange={e => setBrowseFilters(f => ({ ...f, city: e.target.value }))}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">Tous les gouvernorats</option>
              {GOVERNORATS.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
            <select
              value={browseFilters.type}
              onChange={e => setBrowseFilters(f => ({ ...f, type: e.target.value }))}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">Tout type</option>
              <option value="vente">À Vendre</option>
              <option value="location">À Louer</option>
            </select>
            <input
              type="number" placeholder="Prix min (TND)"
              value={browseFilters.min_price}
              onChange={e => setBrowseFilters(f => ({ ...f, min_price: e.target.value }))}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            <input
              type="number" placeholder="Prix max (TND)"
              value={browseFilters.max_price}
              onChange={e => setBrowseFilters(f => ({ ...f, max_price: e.target.value }))}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            <input
              type="number" placeholder="Nb chambres"
              value={browseFilters.rooms}
              onChange={e => setBrowseFilters(f => ({ ...f, rooms: e.target.value }))}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          {browseLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
              <span className="ml-3 text-slate-500">Chargement des annonces...</span>
            </div>
          ) : (
            <div className="flex flex-col lg:flex-row gap-6">
              <div className="flex-1 space-y-4">
                {browseListings.length === 0 ? (
                  <div className="text-center py-12 text-slate-400">
                    <Grid3X3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p>Aucune annonce pour ces critères.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                    {browseListings.map(l => (
                      <ListingCard key={l._id || l.id} listing={mongoToCard(l)} />
                    ))}
                  </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-3 pt-2">
                    <button
                      onClick={() => setPage(p => Math.max(0, p - 1))}
                      disabled={page === 0}
                      className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-30 transition-colors"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-sm text-slate-600">
                      Page {page + 1} / {totalPages}
                    </span>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                      disabled={page === totalPages - 1}
                      className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-30 transition-colors"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>

              {/* Map */}
              {browseListings.length > 0 && (
                <div className="lg:w-80 xl:w-96">
                  <div className="sticky top-20 rounded-2xl overflow-hidden border border-slate-200 shadow-sm" style={{ height: 500 }}>
                    <DynamicMap center={[35.5, 9.5]} zoom={6} markers={mapMarkers} height="500px" />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── AI SEARCH TAB ──────────────────────────────────────────────────── */}
      {tab === 'ai' && (
        <div className="space-y-4">
          <h1 className="text-2xl font-bold text-slate-800">Recherche intelligente</h1>
          <form onSubmit={e => { e.preventDefault(); doSearch(query) }} className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Appartement 3 pièces à Sousse sous 250 000 TND..."
                className="w-full pl-9 pr-4 py-3 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
              />
            </div>
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className="px-4 py-3 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors"
            >
              <SlidersHorizontal className="w-4 h-4 text-slate-600" />
            </button>
            <button type="submit" className="px-6 py-3 bg-brand-600 text-white font-medium rounded-xl hover:bg-brand-700 transition-colors">
              Chercher
            </button>
          </form>

          {showFilters && (
            <div className="bg-white border border-slate-200 rounded-xl p-4 grid grid-cols-2 md:grid-cols-4 gap-3">
              <select
                value={filters.city}
                onChange={e => setFilters(f => ({ ...f, city: e.target.value }))}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="">Tous les gouvernorats</option>
                {GOVERNORATS.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
              <select
                value={filters.transaction_type}
                onChange={e => setFilters(f => ({ ...f, transaction_type: e.target.value }))}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="">Transaction</option>
                <option value="À Vendre">À Vendre</option>
                <option value="À Louer">À Louer</option>
              </select>
              <input
                type="number" placeholder="Prix max (TND)"
                value={filters.max_price}
                onChange={e => setFilters(f => ({ ...f, max_price: e.target.value }))}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <input
                type="number" placeholder="Surface min (m²)"
                value={filters.min_size}
                onChange={e => setFilters(f => ({ ...f, min_size: e.target.value }))}
                className="border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          )}

          {aiLoading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
              <span className="ml-3 text-slate-500">Analyse IA en cours...</span>
            </div>
          )}

          {!aiLoading && aiSearched && (
            <div className="flex flex-col lg:flex-row gap-6">
              <div className="flex-1">
                {summary && (
                  <div className="bg-brand-50 border border-brand-200 rounded-xl p-4 mb-4 text-sm text-brand-800 flex items-start gap-2">
                    <Sparkles className="w-4 h-4 mt-0.5 shrink-0" />
                    {summary}
                  </div>
                )}
                {aiListings.length === 0 ? (
                  <div className="text-center py-12 text-slate-400">
                    <Search className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p>Aucun bien trouvé. Essayez d&apos;élargir vos critères.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                    {aiListings.map(l => <ListingCard key={l.id} listing={l} />)}
                  </div>
                )}
              </div>
              {aiListings.length > 0 && (
                <div className="lg:w-80 xl:w-96">
                  <div className="sticky top-20 rounded-2xl overflow-hidden border border-slate-200 shadow-sm" style={{ height: 500 }}>
                    <DynamicMap center={[35.5, 9.5]} zoom={6} markers={mapMarkers} height="500px" />
                  </div>
                </div>
              )}
            </div>
          )}

          {!aiSearched && !aiLoading && (
            <div className="text-center py-16 text-slate-400">
              <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Décrivez le bien que vous cherchez en langage naturel</p>
              <p className="text-xs mt-1">Ex: &ldquo;Villa avec piscine à Hammamet sous 800 000 TND&rdquo;</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center py-16"><Loader2 className="w-8 h-8 text-brand-600 animate-spin" /></div>}>
      <SearchContent />
    </Suspense>
  )
}
