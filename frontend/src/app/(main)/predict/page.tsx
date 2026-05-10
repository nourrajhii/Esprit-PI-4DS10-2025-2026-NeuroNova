'use client'
import { useState } from 'react'
import { getDhiaPredict, getDhiaInvest, getDhiaInvestScan } from '@/lib/api'
import SubscriptionGuard from '@/components/SubscriptionGuard'
import { formatTND } from '@/lib/utils'
import {
  Loader2, TrendingUp, BarChart2, Sparkles, Brain,
  MapPin, Ruler, BedDouble, DollarSign, RefreshCw,
  Search, ExternalLink, CheckCircle, AlertTriangle, XCircle,
  ChevronDown, ChevronUp, Building2, FileText, Download,
  ArrowUpRight, ArrowDownRight, Activity, Home, Calendar,
} from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend, ReferenceLine,
} from 'recharts'

const BASE = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8000'

const GOVERNORATS = [
  'Tunis','Ariana','Ben Arous','Manouba','Nabeul','Sousse','Monastir',
  'Sfax','Bizerte','Hammamet','La Marsa','Gabès','Kairouan','Médenine',
  'Gafsa','Tozeur','Mahdia','Zaghouan','Sidi Bouzid','Kasserine',
]

interface RoiPoint {
  year: number
  value_tnd: number
  cumulative_rent_tnd: number
  total_gain_tnd: number
  roi_pct: number
}
interface Comparable {
  label: string
  price_per_m2: number
  estimated_price: number
}
interface PredictResult {
  report?: string
  ml_price?: number
  price_low?: number
  price_high?: number
  price_per_m2?: number
  city_avg_per_m2?: number
  national_avg_per_m2?: number
  city_multiplier?: number
  city?: string
  surface_m2?: number
  rooms?: number
  rental_yield_pct?: number
  annual_rent_tnd?: number
  monthly_rent_tnd?: number
  annual_appreciation_pct?: number
  market_position?: 'above' | 'below' | 'average'
  roi_projection?: RoiPoint[]
  comparables?: Comparable[]
  model?: string
  error?: string
}
interface InvestScoring {
  verdict?: string; score?: number; roi_5y_pct?: number
  annual_rent_est_tnd?: number; rental_yield_pct?: number
}
interface InvestResult extends InvestScoring {
  report?: string; scoring?: InvestScoring; error?: string
}
interface Opportunity {
  id: string; title: string; price: number; city: string
  surface_m2: number | null; rooms: number | null
  property_type: string | null; transaction_type: string | null
  listing_url: string | null; thumbnail: string | null
  verdict: 'BUY' | 'HOLD' | 'AVOID'; score: number
  rental_yield_pct: number; annual_rent_est_tnd: number; roi_5y_pct: number
}
interface ScanResult {
  opportunities: Opportunity[]; total_scanned: number
  buys: number; holds: number; avoids: number; gemini_summary: string
  filter: { city: string; budget_range: [number, number] }
}

function MarkdownReport({ text }: { text: string }) {
  return (
    <div className="space-y-1.5 text-sm">
      {text.split('\n').map((line, i) => {
        const isH1 = line.startsWith('# ')
        const isH2 = line.startsWith('## ')
        const isH3 = line.startsWith('### ')
        const isBullet = /^[\*\-] /.test(line)
        const isRule = line.startsWith('---')
        const clean = line
          .replace(/^#{1,3}\s/, '')
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\*(.*?)\*/g, '<em>$1</em>')
          .replace(/`(.*?)`/g, '<code class="bg-slate-100 px-1 rounded text-xs">$1</code>')
        if (!clean.trim()) return <div key={i} className="h-1" />
        if (isRule) return <hr key={i} className="border-slate-200 my-2" />
        if (isH1) return <h2 key={i} className="font-bold text-slate-900 text-base mt-4 mb-1" dangerouslySetInnerHTML={{ __html: clean }} />
        if (isH2) return <h3 key={i} className="font-bold text-brand-700 text-sm mt-3 mb-1" dangerouslySetInnerHTML={{ __html: clean }} />
        if (isH3) return <h4 key={i} className="font-semibold text-slate-700 text-sm mt-2" dangerouslySetInnerHTML={{ __html: clean }} />
        if (isBullet) return (
          <div key={i} className="flex gap-2 items-start">
            <span className="text-brand-400 mt-0.5 shrink-0">•</span>
            <p className="text-slate-600 text-xs" dangerouslySetInnerHTML={{ __html: clean.replace(/^[\*\-]\s/, '') }} />
          </div>
        )
        if (line.startsWith('|')) {
          const cells = line.split('|').filter(c => c.trim() && !c.match(/^[\s\-:]+$/))
          if (cells.length === 0) return null
          return (
            <div key={i} className="flex gap-2 border-b border-slate-100 py-1">
              {cells.map((c, j) => (
                <span key={j} className={`text-xs flex-1 ${j === 0 ? 'font-medium text-slate-700' : 'text-slate-600'}`}
                  dangerouslySetInnerHTML={{ __html: c.trim().replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
              ))}
            </div>
          )
        }
        return <p key={i} className="text-slate-600 text-xs leading-relaxed" dangerouslySetInnerHTML={{ __html: clean }} />
      })}
    </div>
  )
}

// ── Helpers for the rich prediction view ─────────────────────────────────────

function MarketPositionBadge({ pos }: { pos: 'above' | 'below' | 'average' }) {
  if (pos === 'above') return (
    <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-100 text-amber-800 text-xs font-bold border border-amber-200">
      <ArrowUpRight className="w-3.5 h-3.5" /> Au-dessus du marché
    </span>
  )
  if (pos === 'below') return (
    <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-100 text-emerald-800 text-xs font-bold border border-emerald-200">
      <ArrowDownRight className="w-3.5 h-3.5" /> Sous le marché — opportunité
    </span>
  )
  return (
    <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold border border-slate-200">
      <Activity className="w-3.5 h-3.5" /> Aligné sur le marché
    </span>
  )
}

const ACCENT_CLASSES: Record<string, string> = {
  brand:   'bg-brand-50    text-brand-700    border-brand-100',
  indigo:  'bg-indigo-50   text-indigo-700   border-indigo-100',
  emerald: 'bg-emerald-50  text-emerald-700  border-emerald-100',
  violet:  'bg-violet-50   text-violet-700   border-violet-100',
  slate:   'bg-slate-50    text-slate-700    border-slate-200',
}

function KpiCard({ icon, label, value, accent }: { icon: React.ReactNode; label: string; value: string; accent: string }) {
  const cls = ACCENT_CLASSES[accent] ?? ACCENT_CLASSES.slate
  return (
    <div className={`rounded-xl border p-3 ${cls}`}>
      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider opacity-80">
        {icon} <span className="truncate">{label}</span>
      </div>
      <p className="mt-1 text-sm font-black text-slate-900">{value}</p>
    </div>
  )
}

// ── CSV (UTF-8 BOM so Excel opens it cleanly) ────────────────────────────────
function downloadPredictionCsv(
  r: PredictResult,
  inputs: { city: string; surface: string; rooms: string }
) {
  const esc = (v: string | number | undefined | null) => {
    const s = String(v ?? '')
    return s.includes(',') || s.includes('"') || s.includes('\n')
      ? `"${s.replace(/"/g, '""')}"`
      : s
  }
  const rows: (string | number)[][] = []
  rows.push(['EstateMind — Rapport de Prédiction'])
  rows.push(['Généré le', new Date().toLocaleString('fr-TN')])
  rows.push([])
  rows.push(['BIEN ANALYSÉ'])
  rows.push(['Ville',      inputs.city])
  rows.push(['Surface m²', inputs.surface])
  rows.push(['Chambres',   inputs.rooms])
  rows.push([])
  rows.push(['ESTIMATION'])
  rows.push(['Prix estimé (TND)',          r.ml_price ?? ''])
  rows.push(['Fourchette basse (TND)',     r.price_low ?? ''])
  rows.push(['Fourchette haute (TND)',     r.price_high ?? ''])
  rows.push(['Prix au m² (TND)',           r.price_per_m2 ?? ''])
  rows.push(['Moyenne ville TND/m²',       r.city_avg_per_m2 ?? ''])
  rows.push(['Moyenne nationale TND/m²',   r.national_avg_per_m2 ?? ''])
  rows.push(['Coefficient localisation',   r.city_multiplier ?? ''])
  rows.push(['Positionnement marché',      r.market_position ?? ''])
  rows.push([])
  rows.push(['LOCATION & RENDEMENT'])
  rows.push(['Loyer mensuel estimé (TND)', r.monthly_rent_tnd ?? ''])
  rows.push(['Loyer annuel estimé (TND)',  r.annual_rent_tnd ?? ''])
  rows.push(['Rendement brut (%)',         r.rental_yield_pct ?? ''])
  rows.push(['Appréciation /an (%)',       r.annual_appreciation_pct ?? ''])
  rows.push([])
  rows.push(['PROJECTION DE VALEUR (10 ANS)'])
  rows.push(['Année', 'Valeur (TND)', 'Loyer cumulé (TND)', 'Gain total (TND)', 'ROI (%)'])
  for (const p of r.roi_projection ?? []) {
    rows.push([p.year, p.value_tnd, p.cumulative_rent_tnd, p.total_gain_tnd, p.roi_pct])
  }
  rows.push([])
  rows.push(['COMPARABLES'])
  rows.push(['Référence', 'Prix au m² (TND)', 'Prix estimé total (TND)'])
  for (const c of r.comparables ?? []) {
    rows.push([c.label, c.price_per_m2, c.estimated_price])
  }
  rows.push([])
  rows.push(['Modèle', r.model ?? ''])
  rows.push(['Source', 'EstateMind — Données marché tunisien 2025'])

  const csv = rows.map(row => row.map(esc).join(',')).join('\r\n')
  const BOM = '﻿'   // Force Excel UTF-8
  const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const stamp = new Date().toISOString().slice(0, 10)
  a.download = `estatemind-prediction-${inputs.city.toLowerCase().replace(/\s+/g, '-')}-${stamp}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function VerdictBadge({ verdict }: { verdict: string }) {
  if (verdict === 'BUY') return (
    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold border border-emerald-200">
      <CheckCircle className="w-3 h-3" /> BUY
    </span>
  )
  if (verdict === 'AVOID') return (
    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-100 text-red-700 text-xs font-bold border border-red-200">
      <XCircle className="w-3 h-3" /> AVOID
    </span>
  )
  return (
    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-100 text-amber-700 text-xs font-bold border border-amber-200">
      <AlertTriangle className="w-3 h-3" /> HOLD
    </span>
  )
}

function OpportunityCard({ opp }: { opp: Opportunity }) {
  const [open, setOpen] = useState(false)
  const scoreBg = opp.verdict === 'BUY' ? 'bg-emerald-500' : opp.verdict === 'AVOID' ? 'bg-red-400' : 'bg-amber-400'

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow">
      <div className="flex gap-3 p-3">
        {opp.thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={opp.thumbnail} alt="" className="w-20 h-20 object-cover rounded-lg flex-shrink-0" onError={e => { (e.target as HTMLImageElement).style.display='none' }} />
        ) : (
          <div className="w-20 h-20 rounded-lg flex-shrink-0 bg-slate-100 flex items-center justify-center">
            <Building2 className="w-8 h-8 text-slate-300" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-semibold text-slate-800 leading-snug line-clamp-2">{opp.title}</p>
            <div className={`flex-shrink-0 w-10 h-10 rounded-full ${scoreBg} flex items-center justify-center text-white font-bold text-xs`}>
              {opp.score}
            </div>
          </div>
          <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-500">
            <MapPin className="w-3 h-3" /> {opp.city}
            {opp.surface_m2 && <><span>·</span><span>{opp.surface_m2} m²</span></>}
            {opp.rooms && <><span>·</span><span>{opp.rooms} ch.</span></>}
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-1.5">
            <span className="text-sm font-bold text-brand-700">{opp.price.toLocaleString('fr-TN')} TND</span>
            <VerdictBadge verdict={opp.verdict} />
          </div>
        </div>
      </div>

      <button onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-3 py-2 border-t border-slate-100 bg-slate-50 hover:bg-slate-100 text-xs text-slate-600 font-medium transition-colors">
        <span className="flex gap-3">
          <span>Rendement {opp.rental_yield_pct}%</span>
          <span>·</span>
          <span>ROI 5 ans {opp.roi_5y_pct}%</span>
          <span>·</span>
          <span>Loyer ~{Math.round(opp.annual_rent_est_tnd / 12).toLocaleString('fr-TN')} TND/mois</span>
        </span>
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {open && (
        <div className="px-3 py-3 border-t border-slate-100 space-y-2.5">
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: 'Rendement brut', val: `${opp.rental_yield_pct}%` },
              { label: 'ROI 5 ans', val: `${opp.roi_5y_pct}%` },
              { label: 'Loyer annuel estimé', val: `${opp.annual_rent_est_tnd.toLocaleString('fr-TN')} TND` },
            ].map(({ label, val }) => (
              <div key={label} className="bg-slate-50 rounded-lg p-2 text-center">
                <p className="text-[10px] text-slate-500">{label}</p>
                <p className="text-xs font-bold text-slate-800 mt-0.5">{val}</p>
              </div>
            ))}
          </div>
          {opp.listing_url && (
            <a href={opp.listing_url} target="_blank" rel="noopener noreferrer"
              className="flex items-center justify-center gap-1.5 text-xs text-brand-600 hover:text-brand-700 hover:underline">
              <ExternalLink className="w-3 h-3" /> Voir l&apos;annonce originale
            </a>
          )}
        </div>
      )}
    </div>
  )
}

function PredictContent() {
  const [city, setCity]     = useState('Tunis')
  const [surface, setSurface] = useState('100')
  const [rooms, setRooms]   = useState('3')
  const [budget, setBudget] = useState('300000')

  const [predResult,   setPredResult]   = useState<PredictResult | null>(null)
  const [investResult, setInvestResult] = useState<InvestResult | null>(null)
  const [predLoading,  setPredLoading]  = useState(false)
  const [investLoading,setInvestLoading]= useState(false)

  // ── Investment scanner state ───────────────────────────────────────────────
  const [scanCity,    setScanCity]    = useState('')
  const [scanBudget,  setScanBudget]  = useState('1000000')
  const [scanMinBudget, setScanMinBudget] = useState('50000')
  const [scanTx,      setScanTx]      = useState('')
  const [scanResult,  setScanResult]  = useState<ScanResult | null>(null)
  const [scanLoading, setScanLoading] = useState(false)
  const [scanError,   setScanError]   = useState('')

  const runPredict = async () => {
    setPredLoading(true); setPredResult(null)
    try {
      const r = await getDhiaPredict(city, Number(surface), Number(rooms))
      setPredResult((r?.output ?? r) as PredictResult)
    } catch (e) { setPredResult({ error: String(e) }) }
    finally { setPredLoading(false) }
  }

  const [investScan,    setInvestScan]    = useState<ScanResult | null>(null)

  const runInvest = async () => {
    setInvestLoading(true); setInvestResult(null); setInvestScan(null)
    try {
      // Run single-property scoring + real-listings scan in parallel
      const [r, scanData] = await Promise.all([
        getDhiaInvest(city, Number(budget)),
        getDhiaInvestScan({
          city,
          min_budget: Math.round(Number(budget) * 0.6),
          budget: Math.round(Number(budget) * 1.4),
          top_n: 12,
        }).catch(() => null),
      ])
      setInvestResult((r?.output ?? r) as InvestResult)
      if (scanData) setInvestScan(scanData)
    } catch (e) { setInvestResult({ error: String(e) }) }
    finally { setInvestLoading(false) }
  }

  const runBoth = async () => { await Promise.all([runPredict(), runInvest()]) }

  const runScan = async () => {
    setScanLoading(true); setScanResult(null); setScanError('')
    try {
      const d = await getDhiaInvestScan({
        city: scanCity, budget: Number(scanBudget),
        min_budget: Number(scanMinBudget), top_n: 20,
        transaction_type: scanTx,
      })
      setScanResult(d)
    } catch (e) { setScanError(String(e)) }
    finally { setScanLoading(false) }
  }

  // ── derived values for single-property invest panel ────────────────────────
  const investReport = investResult?.report as string | undefined
  const verdict      = (investResult?.verdict   ?? investResult?.scoring?.verdict)   as string | undefined
  const score        = (investResult?.score     ?? investResult?.scoring?.score)     as number | undefined
  const roi5y        = (investResult?.roi_5y_pct ?? investResult?.scoring?.roi_5y_pct) as number | undefined
  const annRent      = (investResult?.annual_rent_est_tnd ?? investResult?.scoring?.annual_rent_est_tnd) as number | undefined
  const renYield     = (investResult?.rental_yield_pct ?? investResult?.scoring?.rental_yield_pct) as number | undefined

  const verdictColor =
    verdict === 'BUY'   ? 'bg-emerald-100 text-emerald-800 border-emerald-200' :
    verdict === 'AVOID' ? 'bg-red-100 text-red-800 border-red-200' :
                          'bg-amber-100 text-amber-800 border-amber-200'

  return (
    <div className="space-y-8">

      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 bg-brand-100 rounded-2xl flex items-center justify-center shrink-0">
          <Brain className="w-6 h-6 text-brand-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Agent Prédiction & Investissement</h1>
          <p className="text-slate-500 text-sm mt-1">
            Prédiction de prix IA · Scoring investissement · Scanner d&apos;opportunités en temps réel
          </p>
        </div>
      </div>

      {/* ── Single-property panels ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Prediction panel */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="bg-gradient-to-r from-brand-600 to-brand-500 px-6 py-4 flex items-center gap-3">
            <TrendingUp className="w-5 h-5 text-white" />
            <div>
              <h2 className="font-bold text-white">Agent Prédiction de Prix</h2>
              <p className="text-brand-200 text-xs">ML regression + rapport Gemini</p>
            </div>
          </div>
          <div className="p-5 space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Ville</label>
                <select value={city} onChange={e => setCity(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400">
                  {GOVERNORATS.map(g => <option key={g}>{g}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Surface (m²)</label>
                <input type="number" value={surface} onChange={e => setSurface(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Chambres</label>
                <input type="number" value={rooms} onChange={e => setRooms(e.target.value)} min={1} max={10}
                  className="w-full border border-slate-300 rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400" />
              </div>
            </div>
            <button onClick={runPredict} disabled={predLoading}
              className="w-full flex items-center justify-center gap-2 bg-brand-600 text-white py-2.5 rounded-xl text-sm font-semibold hover:bg-brand-700 transition-colors disabled:opacity-50">
              {predLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              {predLoading ? 'Analyse en cours…' : 'Estimer le prix'}
            </button>

            {predResult?.error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{String(predResult.error)}</div>
            )}

            {predResult && !predLoading && !predResult.error && (
              <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">

                {/* Hero: main estimate with range + CSV download */}
                <div className="bg-gradient-to-br from-brand-50 via-white to-indigo-50 rounded-xl border border-brand-100 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-brand-600 mb-0.5">Prix estimé</p>
                      <p className="text-2xl font-black text-slate-900">{formatTND(predResult.ml_price ?? 0)}</p>
                      {predResult.price_low !== undefined && predResult.price_high !== undefined && (
                        <p className="text-[11px] text-slate-500 mt-1">
                          Fourchette : <span className="font-semibold text-slate-700">{formatTND(predResult.price_low)}</span> — <span className="font-semibold text-slate-700">{formatTND(predResult.price_high)}</span>
                        </p>
                      )}
                    </div>
                    <button onClick={() => downloadPredictionCsv(predResult, { city, surface, rooms })}
                      title="Télécharger Excel/CSV"
                      className="flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-[11px] font-semibold px-2.5 py-1.5 rounded-lg transition-colors shrink-0">
                      <Download className="w-3 h-3" /> CSV
                    </button>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {predResult.market_position && (
                      <MarketPositionBadge pos={predResult.market_position} />
                    )}
                    <span className="text-[11px] text-slate-500">{surface} m² · {rooms} ch. · {city}</span>
                  </div>
                </div>

                {/* KPI cards */}
                <div className="grid grid-cols-2 gap-2">
                  <KpiCard icon={<DollarSign className="w-3.5 h-3.5"/>} label="Prix au m²" value={`${(predResult.price_per_m2 ?? 0).toLocaleString('fr-TN')} TND`} accent="brand" />
                  <KpiCard icon={<MapPin className="w-3.5 h-3.5"/>}     label={`Moy. ${predResult.city ?? city}`} value={`${(predResult.city_avg_per_m2 ?? 0).toLocaleString('fr-TN')} TND/m²`} accent="indigo" />
                  <KpiCard icon={<Home className="w-3.5 h-3.5"/>}       label="Loyer mensuel" value={`${(predResult.monthly_rent_tnd ?? 0).toLocaleString('fr-TN')} TND`} accent="emerald" />
                  <KpiCard icon={<TrendingUp className="w-3.5 h-3.5"/>} label="Rendement brut" value={`${predResult.rental_yield_pct ?? 0}%`} accent="emerald" />
                  <KpiCard icon={<ArrowUpRight className="w-3.5 h-3.5"/>} label="Apprec. /an" value={`+${predResult.annual_appreciation_pct ?? 0}%`} accent="violet" />
                  <KpiCard icon={<Activity className="w-3.5 h-3.5"/>}   label="Moy. nationale" value={`${(predResult.national_avg_per_m2 ?? 0).toLocaleString('fr-TN')} TND/m²`} accent="slate" />
                </div>

                {/* ROI projection chart */}
                {predResult.roi_projection && predResult.roi_projection.length > 0 && (
                  <div className="bg-white border border-slate-200 rounded-xl p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-violet-600" />
                        <h3 className="text-xs font-bold text-slate-800">Projection valeur (10 ans)</h3>
                      </div>
                    </div>
                    <ResponsiveContainer width="100%" height={180}>
                      <LineChart data={predResult.roi_projection} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 9 }} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                        <Tooltip
                          formatter={(value: number) => [`${value.toLocaleString('fr-TN')} TND`]}
                          contentStyle={{ fontSize: 11, borderRadius: 8 }}
                        />
                        <Legend wrapperStyle={{ fontSize: 10 }} />
                        <ReferenceLine y={predResult.ml_price} stroke="#94a3b8" strokeDasharray="4 4" />
                        <Line type="monotone" dataKey="value_tnd" name="Valeur" stroke="#7c3aed" strokeWidth={2} dot={{ r: 2 }} />
                        <Line type="monotone" dataKey="cumulative_rent_tnd" name="Loyer cumulé" stroke="#10b981" strokeWidth={2} dot={{ r: 2 }} />
                      </LineChart>
                    </ResponsiveContainer>
                    {predResult.roi_projection.length >= 11 && (
                      <div className="mt-2 grid grid-cols-2 gap-2 text-center">
                        <div className="bg-violet-50 rounded-lg py-1.5 border border-violet-100">
                          <p className="text-[9px] text-violet-700 font-semibold">5 ANS</p>
                          <p className="text-xs font-bold text-violet-900">{formatTND(predResult.roi_projection[5].value_tnd)}</p>
                          <p className="text-[9px] text-emerald-600 font-semibold">+{predResult.roi_projection[5].roi_pct}%</p>
                        </div>
                        <div className="bg-violet-50 rounded-lg py-1.5 border border-violet-100">
                          <p className="text-[9px] text-violet-700 font-semibold">10 ANS</p>
                          <p className="text-xs font-bold text-violet-900">{formatTND(predResult.roi_projection[10].value_tnd)}</p>
                          <p className="text-[9px] text-emerald-600 font-semibold">+{predResult.roi_projection[10].roi_pct}%</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Comparables chart */}
                {predResult.comparables && predResult.comparables.length > 0 && (
                  <div className="bg-white border border-slate-200 rounded-xl p-3">
                    <div className="flex items-center gap-1.5 mb-2">
                      <BarChart2 className="w-3.5 h-3.5 text-brand-600" />
                      <h3 className="text-xs font-bold text-slate-800">Comparables (TND/m²)</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={[
                        { label: 'Votre bien', value: predResult.price_per_m2 ?? 0 },
                        ...predResult.comparables.map(c => ({ label: c.label, value: c.price_per_m2 })),
                      ]} margin={{ top: 5, right: 8, left: 0, bottom: 30 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="label" tick={{ fontSize: 9 }} angle={-15} textAnchor="end" height={45} interval={0} />
                        <YAxis tick={{ fontSize: 9 }} tickFormatter={(v) => `${(v/1000).toFixed(1)}k`} />
                        <Tooltip
                          formatter={(value: number) => [`${value.toLocaleString('fr-TN')} TND/m²`]}
                          contentStyle={{ fontSize: 11, borderRadius: 8 }}
                        />
                        <Bar dataKey="value" fill="#3b82f6" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Comparables table */}
                {predResult.comparables && predResult.comparables.length > 0 && (
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                    <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-slate-600" />
                      <h3 className="text-xs font-bold text-slate-800">Détail des comparables</h3>
                    </div>
                    <table className="w-full text-xs">
                      <thead className="text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/50">
                        <tr>
                          <th className="text-left px-3 py-1.5 font-semibold">Réf.</th>
                          <th className="text-right px-3 py-1.5 font-semibold">TND/m²</th>
                          <th className="text-right px-3 py-1.5 font-semibold">Total</th>
                          <th className="text-right px-3 py-1.5 font-semibold">Δ</th>
                        </tr>
                      </thead>
                      <tbody>
                        {predResult.comparables.map((c, i) => {
                          const diff = predResult.ml_price ? ((c.estimated_price - predResult.ml_price) / predResult.ml_price) * 100 : 0
                          return (
                            <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
                              <td className="px-3 py-1.5 text-slate-700">{c.label}</td>
                              <td className="px-3 py-1.5 text-right font-medium text-slate-800">{c.price_per_m2.toLocaleString('fr-TN')}</td>
                              <td className="px-3 py-1.5 text-right font-medium text-slate-800">{formatTND(c.estimated_price)}</td>
                              <td className={`px-3 py-1.5 text-right font-bold ${diff > 0 ? 'text-emerald-600' : diff < 0 ? 'text-red-500' : 'text-slate-400'}`}>
                                {diff > 0 ? '+' : ''}{diff.toFixed(1)}%
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Markdown report */}
                {predResult.report && (
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                    <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-brand-600" />
                      <h3 className="text-xs font-bold text-slate-800">Rapport d&apos;analyse</h3>
                    </div>
                    <div className="p-3 max-h-72 overflow-y-auto">
                      <MarkdownReport text={predResult.report} />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Investment scoring panel */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="bg-gradient-to-r from-emerald-600 to-emerald-500 px-6 py-4 flex items-center gap-3">
            <BarChart2 className="w-5 h-5 text-white" />
            <div>
              <h2 className="font-bold text-white">Agent Scoring Investissement</h2>
              <p className="text-emerald-200 text-xs">BUY / HOLD / AVOID + ROI + rapport Gemini</p>
            </div>
          </div>
          <div className="p-5 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Ville</label>
                <select value={city} onChange={e => setCity(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400">
                  {GOVERNORATS.map(g => <option key={g}>{g}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1 block">Budget (TND)</label>
                <input type="number" value={budget} onChange={e => setBudget(e.target.value)} step={10000}
                  className="w-full border border-slate-300 rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />
              </div>
            </div>
            <button onClick={runInvest} disabled={investLoading}
              className="w-full flex items-center justify-center gap-2 bg-emerald-600 text-white py-2.5 rounded-xl text-sm font-semibold hover:bg-emerald-700 transition-colors disabled:opacity-50">
              {investLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart2 className="w-4 h-4" />}
              {investLoading ? 'Analyse en cours…' : 'Analyser l\'investissement'}
            </button>
            
            {investResult && !investLoading && (
              <div className="mt-6">
                {investResult?.error && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
                    {String(investResult.error)}
                  </div>
                )}
                
                {!investResult.error && (
                  <div className="bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {/* Header with main stats */}
                    <div className={`px-6 py-5 flex flex-wrap gap-6 items-center justify-between border-b ${verdictColor} border-b-slate-200`}>
                      <div className="flex items-center gap-4">
                        <div className="bg-white/90 backdrop-blur px-4 py-2 rounded-xl shadow-sm border border-slate-200/50">
                          <p className="text-[10px] uppercase tracking-wider font-bold opacity-60">Verdict Agent</p>
                          <p className="text-2xl font-black">{verdict}</p>
                        </div>
                        <div className="h-10 w-[1px] bg-slate-300/30 hidden sm:block" />
                        <div>
                          <p className="text-[10px] uppercase tracking-wider font-bold opacity-60">Score IA</p>
                          <p className="text-xl font-bold">{score}/100</p>
                        </div>
                      </div>

                      <div className="flex gap-6">
                        {roi5y !== undefined && (
                          <div className="text-right">
                            <p className="text-[10px] uppercase tracking-wider font-bold opacity-60">ROI Estimé (5 ans)</p>
                            <p className="text-xl font-bold text-emerald-600">+{roi5y}%</p>
                          </div>
                        )}
                        {renYield !== undefined && (
                          <div className="text-right">
                            <p className="text-[10px] uppercase tracking-wider font-bold opacity-60">Rendement Annuel</p>
                            <p className="text-xl font-bold text-indigo-600">{renYield}%</p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Main Content: The Full Report */}
                    <div className="p-8">
                      <div className="flex items-center gap-2 mb-6 text-indigo-900">
                        <FileText className="w-5 h-5" />
                        <h2 className="text-lg font-bold">Rapport d&apos;Analyse d&apos;Investissement</h2>
                      </div>
                      
                      {investReport ? (
                        <div className="prose prose-slate max-w-none">
                          <MarkdownReport text={investReport} />
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center py-12 text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                          <Sparkles className="w-8 h-8 mb-2 opacity-20" />
                          <p className="text-sm">Génération du rapport détaillé en cours...</p>
                        </div>
                      )}

                      {/* Secondary Stats */}
                      <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                          <p className="text-xs font-bold text-slate-500 uppercase mb-1">Estimation Loyer</p>
                          <p className="text-lg font-bold text-slate-900">{annRent ? formatTND(annRent) : '--'} <span className="text-sm font-normal text-slate-500">/ an</span></p>
                        </div>
                        <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                          <p className="text-xs font-bold text-slate-500 uppercase mb-1">Localisation</p>
                          <p className="text-lg font-bold text-slate-900">{city} <span className="text-sm font-normal text-slate-500">Tunisie</span></p>
                        </div>
                      </div>

                      {/* Real listings scan attached to invest result */}
                      {investScan && (
                        <div className="mt-8 border-t border-slate-100 pt-6">
                          <div className="flex items-center gap-2 mb-3">
                            <Search className="w-4 h-4 text-emerald-600" />
                            <h3 className="text-sm font-bold text-slate-800">
                              Opportunités réelles à {city} — budget ±40%
                            </h3>
                            <span className="ml-auto text-xs text-slate-400">{investScan.total_scanned} biens analysés</span>
                          </div>

                          {/* Verdict counters */}
                          <div className="grid grid-cols-3 gap-2 mb-4">
                            {[
                              { label: 'BUY', val: investScan.buys,   cls: 'bg-emerald-50 border-emerald-200 text-emerald-700' },
                              { label: 'HOLD', val: investScan.holds, cls: 'bg-amber-50  border-amber-200  text-amber-700'  },
                              { label: 'AVOID', val: investScan.avoids,cls: 'bg-red-50   border-red-200    text-red-700'    },
                            ].map(({ label, val, cls }) => (
                              <div key={label} className={`rounded-xl border p-2 text-center ${cls}`}>
                                <p className="text-xl font-black">{val}</p>
                                <p className="text-[10px] font-semibold">{label}</p>
                              </div>
                            ))}
                          </div>

                          {/* Gemini synthesis */}
                          {investScan.gemini_summary && (
                            <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
                              <p className="text-xs font-semibold text-emerald-700 mb-1 flex items-center gap-1.5">
                                <Sparkles className="w-3.5 h-3.5" /> Conseil Gemini sur les opportunités trouvées
                              </p>
                              <p className="text-xs text-emerald-900 leading-relaxed">{investScan.gemini_summary}</p>
                            </div>
                          )}

                          {/* Opportunity cards */}
                          <div className="space-y-2">
                            {investScan.opportunities.slice(0, 12).map(opp => (
                              <OpportunityCard key={opp.id} opp={opp} />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Run both button */}
      <div className="flex justify-center">
        <button onClick={runBoth} disabled={predLoading || investLoading}
          className="flex items-center gap-2 bg-slate-800 text-white px-8 py-3 rounded-2xl text-sm font-semibold hover:bg-slate-900 transition-colors disabled:opacity-50 shadow-lg">
          {(predLoading || investLoading)
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Analyse en cours…</>
            : <><RefreshCw className="w-4 h-4" /> Lancer les deux agents</>}
        </button>
      </div>

      {/* ── INVESTMENT SCANNER ─────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-4 flex items-center gap-3">
          <Search className="w-5 h-5 text-white" />
          <div>
            <h2 className="font-bold text-white">Scanner d&apos;Opportunités Immobilières</h2>
            <p className="text-violet-200 text-xs">Analyse en temps réel de la base de données — BUY/HOLD/AVOID sur chaque bien</p>
          </div>
        </div>

        <div className="p-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Ville / Gouvernorat</label>
              <input value={scanCity} onChange={e => setScanCity(e.target.value)}
                placeholder="Tous (laisser vide)"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Budget min (TND)</label>
              <input type="number" value={scanMinBudget} onChange={e => setScanMinBudget(e.target.value)} step={10000}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Budget max (TND)</label>
              <input type="number" value={scanBudget} onChange={e => setScanBudget(e.target.value)} step={50000}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 mb-1 block">Type de transaction</label>
              <select value={scanTx} onChange={e => setScanTx(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400">
                <option value="">Tous</option>
                <option value="vente">Vente</option>
                <option value="location">Location</option>
              </select>
            </div>
          </div>

          <button onClick={runScan} disabled={scanLoading}
            className="w-full flex items-center justify-center gap-2 bg-violet-600 text-white py-3 rounded-xl text-sm font-semibold hover:bg-violet-700 transition-colors disabled:opacity-50 mb-5">
            {scanLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {scanLoading ? 'Scan en cours — analyse de chaque bien…' : 'Lancer le scan du marché'}
          </button>

          {scanError && (
            <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{scanError}</div>
          )}

          {scanResult && (
            <div className="space-y-5">
              {/* Stats bar */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: 'Biens analysés', val: scanResult.total_scanned, color: 'text-slate-800' },
                  { label: 'BUY', val: scanResult.buys, color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200' },
                  { label: 'HOLD', val: scanResult.holds, color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
                  { label: 'AVOID', val: scanResult.avoids, color: 'text-red-700', bg: 'bg-red-50 border-red-200' },
                ].map(({ label, val, color, bg }) => (
                  <div key={label} className={`rounded-xl border p-3 text-center ${bg ?? 'bg-slate-50 border-slate-200'}`}>
                    <p className={`text-2xl font-black ${color}`}>{val}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{label}</p>
                  </div>
                ))}
              </div>

              {/* Gemini synthesis */}
              {scanResult.gemini_summary && (
                <div className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3">
                  <p className="text-xs font-semibold text-violet-700 mb-1 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" /> Synthèse Gemini — Analyse du marché
                  </p>
                  <p className="text-sm text-violet-900 leading-relaxed">{scanResult.gemini_summary}</p>
                </div>
              )}

              {/* Opportunities grid */}
              {scanResult.opportunities.length > 0 ? (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-violet-600" />
                    Top {scanResult.opportunities.length} opportunités — triées par score
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    {scanResult.opportunities.map(opp => (
                      <OpportunityCard key={opp.id} opp={opp} />
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-center text-slate-400 text-sm py-8">Aucune opportunité trouvée avec ces critères.</p>
              )}
            </div>
          )}
        </div>
      </div>

    </div>
  )
}

export default function PredictPage() {
  return <SubscriptionGuard><PredictContent /></SubscriptionGuard>
}
