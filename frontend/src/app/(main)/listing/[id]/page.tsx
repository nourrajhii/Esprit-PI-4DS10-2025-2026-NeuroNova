'use client'
import { useState, useEffect, Suspense } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { getListingById, getListingDetail, getDhiaPredict, getDhiaInvest, chat, MongoListing } from '@/lib/api'
import { formatTND, formatM2 } from '@/lib/utils'
import InvestmentBadge from '@/components/InvestmentBadge'
import RadarChart from '@/components/RadarChart'
import {
  Loader2, TrendingUp, Scale, Hammer, MapPin, BedDouble,
  Bath, Ruler, ChevronLeft, ChevronRight, Phone, Building2,
  Sparkles, BarChart2, ArrowLeft, ExternalLink, Tag,
  CheckCircle2, Home,
} from 'lucide-react'

function MarkdownText({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const isH2 = line.startsWith('## ')
        const isH3 = line.startsWith('### ')
        const isBullet = line.startsWith('* ') || line.startsWith('- ')
        const clean = line.replace(/^#{1,3}\s/, '').replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\*(.*?)\*/g, '<em>$1</em>')
        if (!clean.trim()) return <div key={i} className="h-2" />
        if (isH2) return <h3 key={i} className="font-bold text-slate-800 text-sm mt-3" dangerouslySetInnerHTML={{ __html: clean }} />
        if (isH3) return <h4 key={i} className="font-semibold text-slate-700 text-sm mt-2" dangerouslySetInnerHTML={{ __html: clean }} />
        if (isBullet) return <li key={i} className="text-xs text-slate-600 ml-4 list-disc" dangerouslySetInnerHTML={{ __html: clean.replace(/^[*-]\s/, '') }} />
        return <p key={i} className="text-xs text-slate-600" dangerouslySetInnerHTML={{ __html: clean }} />
      })}
    </div>
  )
}

function Gallery({ images, title }: { images: string[]; title: string }) {
  const [idx, setIdx] = useState(0)
  const [err, setErr] = useState<Record<number, boolean>>({})
  const valid = images.filter((_, i) => !err[i])

  if (!valid.length) return (
    <div className="h-96 bg-gradient-to-br from-slate-100 to-slate-200 rounded-2xl flex flex-col items-center justify-center gap-3">
      <Home className="w-16 h-16 text-slate-300" />
      <p className="text-slate-400 text-sm">Pas de photos disponibles</p>
    </div>
  )

  return (
    <div className="space-y-3">
      {/* Main image */}
      <div className="relative h-[420px] rounded-2xl overflow-hidden bg-slate-100 shadow-sm group">
        <Image
          src={images[idx]}
          alt={`${title} — photo ${idx + 1}`}
          fill
          className="object-cover transition-transform duration-500 group-hover:scale-[1.02]"
          sizes="(max-width: 1024px) 100vw, 60vw"
          unoptimized
          onError={() => setErr(e => ({ ...e, [idx]: true }))}
          priority
        />
        {/* Gradient overlay bottom */}
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/40 to-transparent pointer-events-none" />
        {images.length > 1 && (
          <>
            <button
              onClick={() => setIdx(i => (i - 1 + images.length) % images.length)}
              className="absolute left-3 top-1/2 -translate-y-1/2 bg-white/90 backdrop-blur-sm text-slate-700 rounded-full p-2.5 shadow-lg opacity-0 group-hover:opacity-100 transition-all hover:bg-white"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              onClick={() => setIdx(i => (i + 1) % images.length)}
              className="absolute right-3 top-1/2 -translate-y-1/2 bg-white/90 backdrop-blur-sm text-slate-700 rounded-full p-2.5 shadow-lg opacity-0 group-hover:opacity-100 transition-all hover:bg-white"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
            <span className="absolute bottom-3 right-4 text-xs bg-black/60 text-white px-2.5 py-1 rounded-full backdrop-blur-sm font-medium">
              {idx + 1} / {images.length}
            </span>
          </>
        )}
      </div>
      {/* Thumbnail strip */}
      {images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          {images.map((src, i) => !err[i] && (
            <button key={i} onClick={() => setIdx(i)}
              className={`relative w-20 h-14 shrink-0 rounded-xl overflow-hidden border-2 transition-all ${i === idx ? 'border-primary shadow-md scale-[1.03]' : 'border-transparent opacity-70 hover:opacity-100'}`}
            >
              <Image src={src} alt={`thumb ${i + 1}`} fill className="object-cover" unoptimized onError={() => setErr(e => ({ ...e, [i]: true }))} />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function StatPill({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5">
      <Icon className="w-4 h-4 text-primary shrink-0" />
      <div>
        <p className="text-[10px] text-slate-400 uppercase tracking-wide leading-none mb-0.5">{label}</p>
        <p className="text-sm font-semibold text-slate-700 leading-none">{value}</p>
      </div>
    </div>
  )
}

function ListingContent() {
  const { id } = useParams<{ id: string }>()
  const params = useSearchParams()
  const city    = params.get('city')    || 'Tunis'
  const price   = parseFloat(params.get('price')   || '300000')
  const surface = parseFloat(params.get('surface') || '100')

  const [listing,     setListing]     = useState<MongoListing | null>(null)
  const [agentData,   setAgentData]   = useState<Record<string, unknown> | null>(null)
  const [dhiaReport,  setDhiaReport]  = useState<string | null>(null)
  const [dhiaInvest,  setDhiaInvest]  = useState<string | null>(null)
  const [loading,     setLoading]     = useState(true)
  const [dhiaLoading, setDhiaLoading] = useState(false)
  const [activeTab,   setActiveTab]   = useState<'overview' | 'prediction' | 'devis' | 'legal'>('overview')
  const [devisQuery,  setDevisQuery]  = useState('')
  const [devisResult, setDevisResult] = useState<string | null>(null)
  const [legalQuery,  setLegalQuery]  = useState('')
  const [legalResult, setLegalResult] = useState<string | null>(null)
  const [chatLoading, setChatLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getListingById(id).catch(() => null),
      getListingDetail(id, city, price, surface).catch(() => null),  // VIAGRA optional
    ]).then(([mongoDoc, agents]) => {
      setListing(mongoDoc)
      setAgentData(agents)
      // Auto-load investment report
      const c = mongoDoc?.city || city
      const p = mongoDoc?.price || price
      const s = mongoDoc?.surface_m2 || mongoDoc?.surface || surface
      const pt = (mongoDoc as unknown as Record<string, unknown>)?.property_type as string || 'appartement'
      getDhiaInvest(c, p, s, pt).then(inv => {
        const report = inv?.output?.report || inv?.output?.scoring?.report || null
        const rawInvest = inv?.output?.scoring || inv?.output
        setDhiaReport(prev => prev)  // keep prediction report separate
        setDhiaInvest(report)
        // Merge richer scoring data if available
        if (rawInvest && agents) {
          setAgentData(prev => prev ? { ...prev, investment: rawInvest } : prev)
        }
      }).catch(() => null)
    }).finally(() => setLoading(false))
  }, [id])

  const loadDhia = async () => {
    if (dhiaReport) return
    setDhiaLoading(true)
    try {
      const [pred, inv] = await Promise.all([
        getDhiaPredict(listing?.city || city, listing?.surface_m2 || surface, listing?.rooms || 3).catch(() => null),
        getDhiaInvest(listing?.city || city, listing?.price || price).catch(() => null),
      ])
      setDhiaReport(pred?.output?.report || pred?.output?.ml_price?.toString() || 'Rapport indisponible.')
      setDhiaInvest(inv?.output?.report || JSON.stringify(inv?.output, null, 2) || null)
    } finally { setDhiaLoading(false) }
  }

  const handleDevis = async () => {
    if (!devisQuery.trim()) return
    setChatLoading(true)
    try {
      const res = await chat(devisQuery, undefined, { city: listing?.city || city })
      setDevisResult(res?.data?.devis?.texte || res?.summary || 'Estimation indisponible.')
    } catch { setDevisResult("Erreur lors de la connexion à l'agent devis.") }
    finally { setChatLoading(false) }
  }

  const handleLegal = async () => {
    if (!legalQuery.trim()) return
    setChatLoading(true)
    try {
      const res = await chat(legalQuery)
      setLegalResult(res?.data?.legal?.answer || res?.summary || 'Réponse indisponible.')
    } catch { setLegalResult("Erreur lors de la connexion à l'agent juridique.") }
    finally { setChatLoading(false) }
  }

  const priceData  = agentData?.price     as Record<string, unknown> | undefined
  const investData = agentData?.investment as Record<string, unknown> | undefined
  const geoData    = agentData?.geo        as Record<string, unknown> | undefined

  const displayCity    = listing?.city       || city
  const displayPrice   = listing?.price      || price   // price is already estimated in API route if 0
  const displaySurface = listing?.surface_m2 || surface
  const displayTitle   = listing?.title      || `Annonce #${id}`
  const images         = listing?.image_urls  || []

  if (loading) return (
    <div className="flex flex-col items-center justify-center py-32 gap-4">
      <Loader2 className="w-10 h-10 text-primary animate-spin" />
      <p className="text-slate-500 text-sm">Chargement du bien...</p>
    </div>
  )

  const tabs = [
    { key: 'overview',   label: 'Vue d\'ensemble', icon: TrendingUp },
    { key: 'prediction', label: 'Analyse IA',       icon: Sparkles },
    { key: 'devis',      label: 'Travaux',          icon: Hammer },
    { key: 'legal',      label: 'Juridique',        icon: Scale },
  ] as const

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-16">

      {/* ── Breadcrumb ─────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link href="/search" className="flex items-center gap-1.5 hover:text-primary transition-colors">
          <ArrowLeft className="w-4 h-4" /> Annonces
        </Link>
        <span>/</span>
        <span className="text-slate-400">{displayCity}</span>
        <span>/</span>
        <span className="text-slate-700 font-medium truncate max-w-xs">{displayTitle}</span>
      </div>

      {/* ── Main grid ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* Left — Gallery + Details */}
        <div className="lg:col-span-3 space-y-5">
          <Gallery images={images} title={displayTitle} />

          {/* Description */}
          {listing?.description && (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <h3 className="font-semibold text-slate-800 mb-3">Description</h3>
              <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{listing.description}</p>
            </div>
          )}

          {/* Contact row (mobile) */}
          <div className="lg:hidden bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
            <p className="text-2xl font-bold text-primary">
              {formatTND(displayPrice)}
            </p>
            <div className="flex flex-wrap gap-2">
              {listing?.phone && (
                <a href={`tel:${listing.phone}`} className="flex items-center gap-1.5 text-sm bg-emerald-600 text-white px-4 py-2 rounded-xl hover:bg-emerald-700 transition-colors font-medium">
                  <Phone className="w-4 h-4" /> Appeler
                </a>
              )}
              {listing?.listing_url && (
                <a href={listing.listing_url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-sm bg-slate-100 text-slate-700 px-4 py-2 rounded-xl hover:bg-slate-200 transition-colors">
                  <ExternalLink className="w-4 h-4" /> Annonce originale
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Right — Sticky info card */}
        <div className="lg:col-span-2">
          <div className="sticky top-6 space-y-4">

            {/* Price card */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              {/* Transaction type */}
              {listing?.transaction_type && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold bg-primary/10 text-primary px-2.5 py-1 rounded-lg mb-3">
                  <Tag className="w-3 h-3" />
                  {listing.transaction_type}
                </span>
              )}

              <h1 className="text-lg font-bold text-slate-800 leading-snug mb-1">{displayTitle}</h1>
              <div className="flex items-center gap-1.5 text-sm text-slate-500 mb-4">
                <MapPin className="w-3.5 h-3.5" />{displayCity}
              </div>

              <div className="flex items-end gap-2 mb-4">
                <p className="text-3xl font-extrabold text-primary leading-none">{formatTND(displayPrice)}</p>
              </div>

              {/* Specs */}
              <div className="grid grid-cols-2 gap-2 mb-4">
                {displaySurface > 0 && <StatPill icon={Ruler}    label="Surface"  value={formatM2(displaySurface)} />}
                {(listing?.rooms ?? 0) > 0 && <StatPill icon={BedDouble} label="Chambres" value={`${listing!.rooms} ch.`} />}
                {(listing?.bathrooms ?? 0) > 0 && <StatPill icon={Bath} label="Sdb" value={`${listing!.bathrooms} sdb`} />}
                {listing?.property_type && <StatPill icon={Building2} label="Type" value={listing.property_type} />}
              </div>

              {/* Contact */}
              <div className="hidden lg:flex flex-col gap-2">
                {listing?.phone && (
                  <a href={`tel:${listing.phone}`}
                    className="flex items-center justify-center gap-2 bg-emerald-600 text-white font-semibold py-3 rounded-xl hover:bg-emerald-700 transition-colors">
                    <Phone className="w-4 h-4" /> Appeler {listing.phone}
                  </a>
                )}
                {listing?.agency_owner && (
                  <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl">
                    <Building2 className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{listing.agency_owner}</span>
                  </div>
                )}
                {listing?.listing_url && (
                  <a href={listing.listing_url} target="_blank" rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 text-sm text-slate-600 bg-slate-100 py-2.5 rounded-xl hover:bg-slate-200 transition-colors">
                    <ExternalLink className="w-3.5 h-3.5" /> Voir l&apos;annonce originale
                  </a>
                )}
              </div>
            </div>

            {/* Quick investment badge */}
            {investData?.verdict != null && (
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Potentiel investissement</p>
                <InvestmentBadge verdict={String(investData.verdict)} score={Number(investData.score)} size="lg" />
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
                  <div className="bg-slate-50 rounded-lg px-3 py-2">
                    <p className="text-slate-400 mb-0.5">Rendement</p>
                    <p className="font-semibold">{investData.rental_yield_pct as number}%</p>
                  </div>
                  <div className="bg-slate-50 rounded-lg px-3 py-2">
                    <p className="text-slate-400 mb-0.5">ROI 5 ans</p>
                    <p className="font-semibold">{investData.roi_5y_pct as number}%</p>
                  </div>
                </div>
              </div>
            )}

            {/* Quick price estimate */}
            {priceData?.predicted_price_tnd != null && (
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Estimation marché IA</p>
                <p className="text-xl font-bold text-slate-800">{formatTND(priceData.predicted_price_tnd as number)}</p>
                <p className="text-xs text-slate-400 mt-1">{formatTND(priceData.price_per_m2_tnd as number)} / m²</p>
                {displayPrice > 0 && (
                  <div className={`mt-2 flex items-center gap-1.5 text-xs font-medium ${displayPrice <= (priceData.predicted_price_tnd as number) ? 'text-emerald-600' : 'text-orange-500'}`}>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {displayPrice <= (priceData.predicted_price_tnd as number)
                      ? `Bon prix — ${Math.round(((priceData.predicted_price_tnd as number) - displayPrice) / displayPrice * 100)}% sous le marché`
                      : `Prix élevé — ${Math.round((displayPrice - (priceData.predicted_price_tnd as number)) / (priceData.predicted_price_tnd as number) * 100)}% au-dessus`}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Tabs ───────────────────────────────────────────────────────────── */}
      <div className="flex gap-1 bg-slate-100 rounded-2xl p-1.5 overflow-x-auto">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button key={key}
            onClick={() => { setActiveTab(key); if (key === 'prediction') loadDhia() }}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
              activeTab === key ? 'bg-white text-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Icon className="w-4 h-4" />{label}
          </button>
        ))}
      </div>

      {/* ── Overview ───────────────────────────────────────────────────────── */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-primary" /> Estimation prix
            </h3>
            {priceData ? (
              <div className="space-y-2">
                <p className="text-2xl font-bold text-slate-800">{formatTND(priceData.predicted_price_tnd as number)}</p>
                <p className="text-xs text-slate-400">Prix/m² : {formatTND(priceData.price_per_m2_tnd as number)}</p>
                {displayPrice > 0 && (
                  <p className={`text-xs font-medium mt-1 ${displayPrice <= (priceData.predicted_price_tnd as number) ? 'text-emerald-600' : 'text-orange-500'}`}>
                    {displayPrice <= (priceData.predicted_price_tnd as number)
                      ? `✅ ${Math.round(((priceData.predicted_price_tnd as number) - displayPrice) / displayPrice * 100)}% sous le marché`
                      : `⚠️ ${Math.round((displayPrice - (priceData.predicted_price_tnd as number)) / (priceData.predicted_price_tnd as number) * 100)}% au-dessus`}
                  </p>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-slate-400 text-sm">Indisponible</p>
                <button onClick={() => { setActiveTab('prediction'); loadDhia() }}
                  className="text-xs text-primary underline">Voir l&apos;analyse IA →</button>
              </div>
            )}
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4 flex items-center gap-1.5">
              <BarChart2 className="w-4 h-4 text-primary" /> Scoring investissement
            </h3>
            {investData ? (
              <div className="space-y-2">
                <InvestmentBadge verdict={investData.verdict as string} score={investData.score as number} />
                <p className="text-xs text-slate-500">Loyer estimé : <strong>{formatTND(investData.annual_rent_est_tnd as number)}/an</strong></p>
                <p className="text-xs text-slate-500">ROI 5 ans : <strong>{investData.roi_5y_pct as number}%</strong></p>
              </div>
            ) : <p className="text-slate-400 text-sm">Indisponible</p>}
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4 flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-primary" /> Quartier
            </h3>
            {geoData ? (
              <div className="space-y-2">
                <p className="text-2xl font-bold text-slate-800">{geoData.overall_score as number}<span className="text-base font-normal text-slate-400">/100</span></p>
                <div className="space-y-1.5">
                  {Object.entries((geoData.scores as Record<string, number>) || {}).slice(0, 4).map(([k, v]) => (
                    <div key={k} className="flex items-center gap-2">
                      <span className="capitalize text-xs text-slate-500 w-20 truncate">{k}</span>
                      <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                        <div className="bg-primary h-1.5 rounded-full transition-all" style={{ width: `${v}%` }} />
                      </div>
                      <span className="text-xs text-slate-600 w-6 text-right">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : <p className="text-slate-400 text-sm">Indisponible</p>}
          </div>

          {geoData?.radar != null && (
            <div className="md:col-span-3 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
              <RadarChart data={geoData.radar as { axis: string; value: number }[]} title={`Analyse — ${displayCity}`} />
              {geoData.summary != null && <p className="text-sm text-slate-500 mt-3 text-center">{String(geoData.summary)}</p>}
            </div>
          )}

          {/* Full investment report — Gemini AI */}
          {dhiaInvest && (
            <div className="md:col-span-3 bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl border border-slate-700 p-6 shadow-sm text-white">
              <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                <Sparkles className="w-4 h-4" /> Rapport d&apos;investissement complet — Gemini IA
              </h3>
              <div className="max-h-[50vh] overflow-y-auto pr-2 text-slate-200 [&_h3]:text-white [&_h3]:font-bold [&_h3]:text-sm [&_h3]:mt-4 [&_h4]:text-slate-300 [&_h4]:font-semibold [&_h4]:text-xs [&_h4]:mt-3 [&_li]:text-xs [&_li]:text-slate-300 [&_p]:text-xs [&_p]:text-slate-300 [&_p]:leading-relaxed [&_b]:text-white">
                <MarkdownText text={dhiaInvest} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── AI Prediction ──────────────────────────────────────────────────── */}
      {activeTab === 'prediction' && (
        <div className="space-y-4">
          {dhiaLoading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <Loader2 className="w-10 h-10 text-primary animate-spin" />
              <p className="text-slate-500 text-sm">Génération de l&apos;analyse IA en cours...</p>
            </div>
          ) : (
            <>
              {dhiaReport && (
                <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-primary" /> Rapport de valorisation
                  </h3>
                  <div className="max-h-[60vh] overflow-y-auto pr-2"><MarkdownText text={dhiaReport} /></div>
                </div>
              )}
              {dhiaInvest && (
                <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                    <BarChart2 className="w-4 h-4 text-primary" /> Analyse d&apos;investissement
                  </h3>
                  <div className="max-h-[40vh] overflow-y-auto pr-2"><MarkdownText text={dhiaInvest} /></div>
                </div>
              )}
              {!dhiaReport && !dhiaInvest && (
                <div className="text-center py-16 text-slate-400">
                  <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-20" />
                  <p>Rapport indisponible pour ce bien.</p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Devis ──────────────────────────────────────────────────────────── */}
      {activeTab === 'devis' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4 max-w-2xl">
          <div>
            <h3 className="font-semibold text-slate-800 mb-1">Estimation de travaux</h3>
            <p className="text-sm text-slate-500">Décrivez vos besoins pour obtenir une estimation en TND.</p>
          </div>
          <textarea value={devisQuery} onChange={e => setDevisQuery(e.target.value)} rows={4}
            placeholder={`Ex: Rénovation complète de ${Math.round(displaySurface)}m² à ${displayCity}…`}
            className="w-full border border-slate-200 rounded-xl p-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary resize-none bg-slate-50" />
          <button onClick={handleDevis} disabled={chatLoading || !devisQuery.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-primary text-white text-sm font-semibold rounded-xl hover:bg-primary-600 transition-colors disabled:opacity-40">
            {chatLoading && <Loader2 className="w-4 h-4 animate-spin" />} Estimer les coûts
          </button>
          {devisResult && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 text-sm text-slate-700 whitespace-pre-line leading-relaxed">{devisResult}</div>
          )}
        </div>
      )}

      {/* ── Legal ──────────────────────────────────────────────────────────── */}
      {activeTab === 'legal' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4 max-w-2xl">
          <div>
            <h3 className="font-semibold text-slate-800 mb-1">Questions juridiques</h3>
            <p className="text-sm text-slate-500">Droit immobilier tunisien, actes notariés, fiscalité.</p>
          </div>
          <textarea value={legalQuery} onChange={e => setLegalQuery(e.target.value)} rows={4}
            placeholder="Ex: Quels sont les droits d'enregistrement pour un achat à Tunis ?"
            className="w-full border border-slate-200 rounded-xl p-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary resize-none bg-slate-50" />
          <button onClick={handleLegal} disabled={chatLoading || !legalQuery.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-slate-800 text-white text-sm font-semibold rounded-xl hover:bg-slate-700 transition-colors disabled:opacity-40">
            {chatLoading && <Loader2 className="w-4 h-4 animate-spin" />} Obtenir une réponse
          </button>
          {legalResult && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 text-sm text-slate-700 whitespace-pre-line leading-relaxed">{legalResult}</div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ListingPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
      </div>
    }>
      <ListingContent />
    </Suspense>
  )
}
