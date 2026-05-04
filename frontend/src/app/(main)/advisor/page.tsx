'use client'
import { useState, useRef, useEffect } from 'react'
import { MessageSquare, Send, RotateCcw, Bot, User, MapPin, Home, TrendingUp, Loader2, Star } from 'lucide-react'

const BASE = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8000'

interface PropertyItem {
  id: string; title: string; price: number
  city?: string | null; region?: string | null
  property_type?: string | null; surface_m2?: number | null; size?: number | null
  rooms?: number | null; room_count?: number | null
  bathrooms?: number | null; bathroom_count?: number | null
  transaction_type?: string | null; url?: string | null; listing_url?: string | null
  score?: number | null; price_per_m2?: number | null
  detected_sub_type?: string | null; category?: string | null
}

interface AdvisorCriteria {
  transaction_type?: string | null; category?: string | null; city?: string | null
  min_price?: number | null; max_price?: number | null; rooms?: number | null
}

interface MarketStats {
  avg_price?: number | null; median_price?: number | null
  avg_price_per_m2?: number | null; count?: number
}

interface AdvisorResponse {
  natural_response: string; advice: string
  criteria: AdvisorCriteria; is_real_estate_query: boolean
  properties: PropertyItem[]; total_found: number; market_stats: MarketStats
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  data?: AdvisorResponse
}

const QUICK_PROMPTS = [
  'Appartement à louer à Bizerte, 2 chambres, budget 1200 DT',
  'Villa à vendre à Nabeul, budget 450 000 DT',
  'Studio à louer à Tunis centre',
  'Terrain à vendre à Sousse',
  'Appartement neuf à Sfax avec 3 chambres',
]

function fmt(v: number | null | undefined) {
  if (v == null) return '—'
  return new Intl.NumberFormat('fr-TN', { maximumFractionDigits: 0 }).format(v) + ' DT'
}

function getTypeLabel(p: PropertyItem) {
  const raw = p.detected_sub_type || p.property_type || p.category || ''
  const v = raw.toLowerCase()
  if (v.includes('appartement')) return 'Appartement'
  if (v.includes('studio')) return 'Studio'
  if (v.includes('villa')) return 'Villa'
  if (v.includes('maison')) return 'Maison'
  if (v.includes('terrain')) return 'Terrain'
  if (v.includes('bureau')) return 'Bureau'
  if (v.includes('local')) return 'Local'
  return raw || 'Bien'
}

function getTypeEmoji(p: PropertyItem) {
  const v = getTypeLabel(p).toLowerCase()
  if (v === 'terrain') return '🌍'
  if (v === 'villa') return '🏡'
  if (v === 'maison') return '🏠'
  if (v === 'studio') return '🛋️'
  if (v === 'bureau') return '💼'
  if (v === 'local') return '🏬'
  return '🏢'
}

function txBadge(tx: string | null | undefined) {
  const v = String(tx || '').toLowerCase()
  if (v.includes('louer') || v.includes('location')) return 'bg-blue-100 text-blue-700'
  if (v.includes('vendre') || v.includes('vente')) return 'bg-orange-100 text-orange-700'
  return 'bg-slate-100 text-slate-600'
}

function PropertyCard({ p, rank }: { p: PropertyItem; rank: number }) {
  const surface = p.surface_m2 ?? p.size
  const rooms = p.rooms ?? p.room_count
  const baths = p.bathrooms ?? p.bathroom_count
  const url = p.listing_url || p.url
  const city = p.city || p.region || '—'
  const featured = rank === 0

  return (
    <div className={`bg-white rounded-2xl border overflow-hidden hover:shadow-md transition-all duration-200 ${featured ? 'border-brand-300 shadow-md ring-1 ring-brand-100' : 'border-slate-200 shadow-sm'}`}>
      <div className={`h-28 flex items-center justify-center text-4xl ${featured ? 'bg-gradient-to-br from-brand-50 to-brand-100' : 'bg-slate-50'}`}>
        {getTypeEmoji(p)}
      </div>
      <div className="p-3.5">
        <div className="flex flex-wrap gap-1.5 mb-2">
          {featured && (
            <span className="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full bg-brand-600 text-white">
              <Star className="w-3 h-3" /> Recommandé
            </span>
          )}
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${txBadge(p.transaction_type)}`}>
            {p.transaction_type || '—'}
          </span>
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
            {getTypeLabel(p)}
          </span>
        </div>

        <p className="font-semibold text-slate-800 text-sm leading-snug line-clamp-2 mb-1">{p.title}</p>

        <div className="flex items-center gap-1 text-slate-500 text-xs mb-2">
          <MapPin className="w-3 h-3 flex-shrink-0" />{city}
        </div>

        <p className={`font-bold mb-2.5 ${featured ? 'text-xl text-brand-700' : 'text-lg text-brand-600'}`}>
          {fmt(p.price)}
        </p>

        <div className="flex flex-wrap gap-1.5 text-xs text-slate-600 mb-3">
          {surface != null && <span className="bg-slate-100 px-2 py-0.5 rounded-full">{surface} m²</span>}
          {rooms != null && rooms > 0 && <span className="bg-slate-100 px-2 py-0.5 rounded-full">{rooms} pièce{rooms > 1 ? 's' : ''}</span>}
          {baths != null && baths > 0 && <span className="bg-slate-100 px-2 py-0.5 rounded-full">{baths} SDB</span>}
          {p.price_per_m2 != null && (
            <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-semibold">
              {fmt(p.price_per_m2)}/m²
            </span>
          )}
        </div>

        {url ? (
          <a href={url} target="_blank" rel="noopener noreferrer"
            className={`block w-full text-center text-xs font-semibold py-2 rounded-xl transition-colors ${
              featured ? 'bg-brand-600 text-white hover:bg-brand-700' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}>
            Voir l'annonce →
          </a>
        ) : (
          <div className="h-8" />
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, icon: Icon }: { label: string; value: string; icon: React.ElementType }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3 text-center shadow-sm">
      <Icon className="w-4 h-4 text-brand-500 mx-auto mb-1" />
      <p className="text-xs text-slate-500 mb-0.5">{label}</p>
      <p className="text-sm font-bold text-brand-700">{value}</p>
    </div>
  )
}

export default function AdvisorPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant')
  const properties = (lastAssistant?.data?.properties ?? []).sort((a, b) => (b.score ?? -999) - (a.score ?? -999))
  const stats = lastAssistant?.data?.market_stats
  const hasResults = properties.length > 0

  async function send() {
    const text = prompt.trim()
    if (!text || loading) return
    setError('')
    const history = messages.map(m => ({ role: m.role, content: m.content }))
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setPrompt('')
    setLoading(true)

    try {
      const res = await fetch(`${BASE}/advisor/prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: text, conversation_history: [...history, { role: 'user', content: text }] }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: AdvisorResponse = await res.json()

      const parts: string[] = []
      if (!data.is_real_estate_query) {
        parts.push(data.natural_response || "Votre demande ne semble pas liée à l'immobilier.")
      } else {
        if (data.natural_response?.trim()) parts.push(data.natural_response.trim())
        if (data.advice?.trim()) parts.push(`💡 ${data.advice.trim()}`)
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: parts.join('\n\n'),
        data,
      }])
    } catch (e: unknown) {
      setError('Erreur de connexion. ' + (e instanceof Error ? e.message : ''))
    } finally {
      setLoading(false)
      textareaRef.current?.focus()
    }
  }

  function clear() {
    setMessages([]); setError(''); setPrompt('')
  }

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <MessageSquare className="w-6 h-6 text-brand-600" />
            Conseiller IA immobilier
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Décrivez votre recherche en français, arabe ou darija
          </p>
        </div>
        {messages.length > 0 && (
          <button onClick={clear}
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 border border-slate-200 rounded-xl px-3 py-2 hover:bg-slate-50 transition-colors">
            <RotateCcw className="w-4 h-4" /> Nouveau chat
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

        {/* ── LEFT col: chat ── */}
        <div className="xl:col-span-2 flex flex-col gap-4">

          {/* Welcome screen */}
          {messages.length === 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 text-center">
              <div className="w-16 h-16 bg-brand-100 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4">🏠</div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">Comment puis-je vous aider ?</h2>
              <p className="text-slate-500 text-sm mb-6 max-w-md mx-auto">
                Décrivez votre projet immobilier et je trouverai les meilleures offres adaptées à vos critères.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {QUICK_PROMPTS.map((qp, i) => (
                  <button key={i} onClick={() => { setPrompt(qp); textareaRef.current?.focus() }}
                    className="text-xs border border-brand-200 bg-brand-50 text-brand-700 hover:bg-brand-100 px-3 py-2 rounded-full transition-colors text-left max-w-[260px] truncate">
                    {qp}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          {messages.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-4 space-y-4 max-h-[500px] overflow-y-auto">
                {messages.map((msg, i) => (
                  <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.role === 'assistant' && (
                      <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Bot className="w-4 h-4 text-brand-600" />
                      </div>
                    )}
                    <div className={`max-w-[82%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                      msg.role === 'user'
                        ? 'bg-brand-600 text-white rounded-tr-sm'
                        : 'bg-slate-50 text-slate-800 rounded-tl-sm border border-slate-200'
                    }`}>
                      {msg.content}
                    </div>
                    {msg.role === 'user' && (
                      <div className="w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                        <User className="w-4 h-4 text-slate-500" />
                      </div>
                    )}
                  </div>
                ))}

                {loading && (
                  <div className="flex gap-3">
                    <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-brand-600" />
                    </div>
                    <div className="bg-slate-50 border border-slate-200 px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-2 text-sm text-slate-500">
                      <Loader2 className="w-4 h-4 animate-spin text-brand-500" />
                      Recherche en cours…
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            </div>
          )}

          {/* Input box */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
            <textarea
              ref={textareaRef}
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
              rows={3}
              placeholder="Ex: Je cherche un appartement à louer à Tunis avec 2 chambres, budget 1500 DT…"
              disabled={loading}
              className="w-full resize-none border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-400 disabled:opacity-50 bg-slate-50"
            />
            <div className="flex items-center justify-between mt-3">
              <p className="text-xs text-slate-400">Entrée pour envoyer · Shift+Entrée pour nouvelle ligne</p>
              <button onClick={send} disabled={loading || !prompt.trim()}
                className="flex items-center gap-2 bg-brand-600 text-white px-5 py-2 rounded-xl text-sm font-semibold hover:bg-brand-700 transition-colors disabled:opacity-50">
                <Send className="w-4 h-4" /> Envoyer
              </button>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">{error}</div>
          )}

          {/* Criteria + market stats under chat */}
          {lastAssistant?.data?.is_real_estate_query && (
            <div className="space-y-3">
              {/* Criteria pills */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-bold text-slate-700">Critères détectés</h3>
                  <span className="text-xs font-bold px-3 py-1 rounded-full bg-brand-100 text-brand-700">
                    {lastAssistant.data.total_found} résultat{lastAssistant.data.total_found !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {[
                    lastAssistant.data.criteria?.transaction_type,
                    lastAssistant.data.criteria?.category === 'residential' ? 'Résidentiel'
                      : lastAssistant.data.criteria?.category === 'land' ? 'Terrain'
                      : lastAssistant.data.criteria?.category === 'commercial' ? 'Commercial'
                      : lastAssistant.data.criteria?.category,
                    lastAssistant.data.criteria?.city,
                    lastAssistant.data.criteria?.max_price != null ? `Max ${fmt(lastAssistant.data.criteria.max_price)}` : null,
                    lastAssistant.data.criteria?.min_price != null ? `Min ${fmt(lastAssistant.data.criteria.min_price)}` : null,
                    lastAssistant.data.criteria?.rooms != null ? `${lastAssistant.data.criteria.rooms} pièces` : null,
                  ].filter(Boolean).map((pill, i) => (
                    <span key={i} className="text-xs bg-slate-100 text-slate-700 px-3 py-1 rounded-full font-medium">{pill}</span>
                  ))}
                </div>
              </div>

              {/* Market stats */}
              {stats && lastAssistant.data.total_found > 0 && (
                <div className="grid grid-cols-3 gap-3">
                  <StatCard label="Prix moyen" value={fmt(stats.avg_price)} icon={TrendingUp} />
                  <StatCard label="Prix médian" value={fmt(stats.median_price)} icon={Home} />
                  <StatCard label="Prix/m² moyen" value={fmt(stats.avg_price_per_m2)} icon={MapPin} />
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── RIGHT col: property cards ── */}
        <div className="xl:col-span-1">
          {hasResults ? (
            <div className="space-y-4">
              <p className="text-sm font-bold text-slate-700">
                {properties.length} bien{properties.length > 1 ? 's' : ''} trouvé{properties.length > 1 ? 's' : ''}
              </p>
              {properties.map((p, i) => (
                <PropertyCard key={p.id || i} p={p} rank={i} />
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-dashed border-slate-200 p-8 text-center text-slate-400">
              <Home className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm font-medium mb-1">Résultats ici</p>
              <p className="text-xs">Les annonces correspondant à votre recherche apparaîtront dans cette colonne.</p>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
