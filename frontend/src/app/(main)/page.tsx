'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getMarketSummary, getListings, MongoListing } from '@/lib/api'
import { GOVERNORAT_COORDS, formatTND } from '@/lib/utils'
import {
  Search, TrendingUp, MapPin, BarChart2, MessageSquare,
  Grid3X3, ArrowRight, Brain, Box, Scale, Wrench, Zap,
  Building2, Star, ChevronRight,
} from 'lucide-react'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import ListingCard from '@/components/ListingCard'

const DynamicMap = dynamic(() => import('@/components/DynamicMap'), { ssr: false })

interface MarketStats {
  global_stats?: { total_biens?: number; prix_moyen?: number; prix_median?: number; pm2_moyen?: number }
  avg_price?: number; median_price?: number; count?: number; avg_price_per_m2?: number
}

const AGENT_FEATURES = [
  {
    icon: Grid3X3, title: 'Annonces en temps réel', desc: '5 500+ biens disponibles, filtrés et enrichis par IA pour votre recherche.',
    href: '/search',
    gradient: 'linear-gradient(135deg, #0c4a6e 0%, #0369a1 100%)',
    glow: 'rgba(3,105,161,0.35)',
  },
  {
    icon: TrendingUp, title: 'Prévisions Marché', desc: 'Analyse Prophet/ARIMA sur 12 mois par gouvernorat — anticipez les prix.',
    href: '/forecast',
    gradient: 'linear-gradient(135deg, #064e3b 0%, #059669 100%)',
    glow: 'rgba(5,150,105,0.35)',
  },
  {
    icon: MessageSquare, title: 'Conseiller IA Multilingue', desc: 'Chat ar/fr/en pour guider vos décisions d\'achat, vente ou location.',
    href: '/advisor',
    gradient: 'linear-gradient(135deg, #4c1d95 0%, #7c3aed 100%)',
    glow: 'rgba(124,58,237,0.35)',
  },
  {
    icon: Brain, title: 'Prédiction & Scoring', desc: 'Prix IA, verdict BUY/HOLD/AVOID et score investissement sur une page.',
    href: '/predict',
    gradient: 'linear-gradient(135deg, #78350f 0%, #d97706 100%)',
    glow: 'rgba(217,119,6,0.35)',
  },
  {
    icon: BarChart2, title: 'Comparateur de Biens', desc: 'Comparez prix IA, score investissement et qualité du quartier côte-à-côte.',
    href: '/compare',
    gradient: 'linear-gradient(135deg, #831843 0%, #e11d48 100%)',
    glow: 'rgba(225,29,72,0.35)',
  },
  {
    icon: MapPin, title: 'Lifestyle & Quartiers', desc: 'Profil de vie, services, sécurité et valeur de chaque quartier tunisien.',
    href: '/lifestyle',
    gradient: 'linear-gradient(135deg, #134e4a 0%, #0d9488 100%)',
    glow: 'rgba(13,148,136,0.35)',
  },
  {
    icon: Box, title: 'Générateur 3D', desc: 'Transformez une photo ou un texte en modèle 3D interactif via Tripo3D v3.1.',
    href: '/villa3d',
    gradient: 'linear-gradient(135deg, #1e1b4b 0%, #4338ca 100%)',
    glow: 'rgba(67,56,202,0.35)',
  },
  {
    icon: Scale, title: 'Agent Juridique', desc: 'Réponses sur le droit immobilier tunisien — contrats, litiges, réglementations.',
    href: '/legal',
    gradient: 'linear-gradient(135deg, #3b0764 0%, #9333ea 100%)',
    glow: 'rgba(147,51,234,0.35)',
  },
  {
    icon: Wrench, title: 'Devis Travaux', desc: 'Estimation du coût de construction ou rénovation par pièce et surface.',
    href: '/devis',
    gradient: 'linear-gradient(135deg, #172554 0%, #1d4ed8 100%)',
    glow: 'rgba(29,78,216,0.35)',
  },
]

const STAT_CONFIG = [
  { key: 'biens',   label: 'Annonces indexées',  icon: Building2, color: '#38BDF8', bg: 'linear-gradient(135deg,#0c4a6e,#0369a1)' },
  { key: 'avg',     label: 'Prix moyen',          icon: TrendingUp, color: '#34D399', bg: 'linear-gradient(135deg,#064e3b,#059669)' },
  { key: 'median',  label: 'Prix médian',         icon: BarChart2,  color: '#A78BFA', bg: 'linear-gradient(135deg,#4c1d95,#7c3aed)' },
  { key: 'pm2',     label: 'Prix/m² moyen',       icon: Star,       color: '#FCD34D', bg: 'linear-gradient(135deg,#78350f,#d97706)' },
]

export default function HomePage() {
  const router = useRouter()
  const [query, setQuery]               = useState('')
  const [marketStats, setMarketStats]   = useState<MarketStats | null>(null)
  const [latestListings, setLatest]     = useState<MongoListing[]>([])
  const [heroLoaded, setHeroLoaded]     = useState(false)

  useEffect(() => {
    setHeroLoaded(true)
    getMarketSummary().then(d => setMarketStats(d)).catch(() => null)
    getListings({ limit: 9 }).then(d => setLatest(d.listings)).catch(() => null)
  }, [])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    router.push(`/search?q=${encodeURIComponent(query)}`)
  }

  const mapMarkers = Object.entries(GOVERNORAT_COORDS).map(([city, [lat, lng]]) => ({
    lat, lng, popup: `<strong>${city}</strong>`, color: '#0284c7',
  }))

  const totalBiens  = marketStats?.global_stats?.total_biens ?? marketStats?.count
  const avgPrice    = marketStats?.global_stats?.prix_moyen  ?? marketStats?.avg_price
  const medianPrice = marketStats?.global_stats?.prix_median ?? marketStats?.median_price
  const avgPm2      = marketStats?.global_stats?.pm2_moyen   ?? marketStats?.avg_price_per_m2

  const statValues = [
    totalBiens?.toLocaleString('fr-TN') ?? '—',
    avgPrice    ? formatTND(avgPrice)    : '—',
    medianPrice ? formatTND(medianPrice) : '—',
    avgPm2      ? `${Math.round(avgPm2).toLocaleString()} TND` : '—',
  ]

  return (
    <>
      <style>{`
        @keyframes heroFadeUp {
          from { opacity: 0; transform: translateY(32px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes floatA {
          0%,100% { transform: translateY(0px) rotate(0deg); }
          50%      { transform: translateY(-18px) rotate(3deg); }
        }
        @keyframes floatB {
          0%,100% { transform: translateY(0px) rotate(0deg); }
          50%      { transform: translateY(-24px) rotate(-4deg); }
        }
        @keyframes floatC {
          0%,100% { transform: translateY(0px); }
          50%      { transform: translateY(-12px); }
        }
        @keyframes goldShimmer {
          0%   { background-position: -200% center; }
          100% { background-position:  200% center; }
        }
        @keyframes cardIn {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulseRing {
          0%,100% { box-shadow: 0 0 0 0 rgba(212,175,55,0.4); }
          50%      { box-shadow: 0 0 0 12px rgba(212,175,55,0); }
        }
        .hero-content { animation: heroFadeUp 0.9s ease both; }
        .orb-a { animation: floatA 7s ease-in-out infinite; }
        .orb-b { animation: floatB 9s ease-in-out infinite 1.5s; }
        .orb-c { animation: floatC 6s ease-in-out infinite 0.8s; }
        .gold-shimmer {
          background: linear-gradient(90deg,#D4AF37,#FBBF24,#FDE68A,#FBBF24,#D4AF37);
          background-size: 300% auto;
          -webkit-background-clip: text; -webkit-text-fill-color: transparent;
          background-clip: text;
          animation: goldShimmer 4s linear infinite;
        }
        .agent-card {
          transition: transform 0.25s cubic-bezier(.22,.68,0,1.2), box-shadow 0.25s;
          animation: cardIn 0.6s ease both;
        }
        .agent-card:hover {
          transform: translateY(-6px) scale(1.02);
        }
        .search-input::placeholder { color: rgba(255,255,255,0.5); }
        .pulse-dot { animation: pulseRing 2s ease-in-out infinite; }
        .grid-overlay {
          background-image:
            linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
          background-size: 64px 64px;
        }
        .stat-card { transition: transform 0.2s, box-shadow 0.2s; }
        .stat-card:hover { transform: translateY(-4px); box-shadow: 0 20px 40px -10px rgba(0,0,0,0.3) !important; }
        .listing-section-link { transition: color 0.2s; }
        .listing-section-link:hover { color: #0369a1; }
      `}</style>

      {/* ─── HERO ───────────────────────────────────────────────────────── */}
      <section style={{
        background: 'linear-gradient(150deg, #00101f 0%, #00204a 35%, #003366 60%, #004455 85%, #001a33 100%)',
        minHeight: 620,
        position: 'relative',
        overflow: 'hidden',
        margin: '-32px -16px 0',
        padding: '110px 24px 90px',
        display: 'flex',
        alignItems: 'center',
      }}>
        {/* Grid overlay */}
        <div className="grid-overlay" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} />

        {/* Radial glows */}
        <div style={{ position: 'absolute', top: -120, right: -120, width: 500, height: 500, borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,85,85,0.5) 0%, transparent 65%)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', bottom: -100, left: -80, width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(212,175,55,0.18) 0%, transparent 65%)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', top: '40%', left: '50%', transform: 'translate(-50%,-50%)', width: 700, height: 400, background: 'radial-gradient(ellipse, rgba(14,165,233,0.08) 0%, transparent 70%)', pointerEvents: 'none' }} />

        {/* Floating orbs */}
        <div className="orb-a" style={{ position: 'absolute', top: 80, left: '8%', width: 64, height: 64, borderRadius: '50%', background: 'rgba(212,175,55,0.12)', border: '1px solid rgba(212,175,55,0.35)', backdropFilter: 'blur(4px)' }} />
        <div className="orb-b" style={{ position: 'absolute', top: 160, right: '12%', width: 44, height: 44, borderRadius: '50%', background: 'rgba(14,165,233,0.15)', border: '1px solid rgba(14,165,233,0.4)', backdropFilter: 'blur(4px)' }} />
        <div className="orb-c" style={{ position: 'absolute', bottom: 90, left: '22%', width: 88, height: 88, borderRadius: '50%', background: 'rgba(0,85,85,0.2)', border: '1px solid rgba(0,170,170,0.25)', backdropFilter: 'blur(4px)' }} />
        <div className="orb-a" style={{ position: 'absolute', bottom: 140, right: '8%', width: 52, height: 52, borderRadius: '50%', background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.3)', backdropFilter: 'blur(4px)', animationDelay: '3s' }} />

        {/* Decorative corner lines */}
        <div style={{ position: 'absolute', top: 32, left: 32, width: 60, height: 60, borderTop: '2px solid rgba(212,175,55,0.3)', borderLeft: '2px solid rgba(212,175,55,0.3)', borderRadius: '4px 0 0 0', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', bottom: 32, right: 32, width: 60, height: 60, borderBottom: '2px solid rgba(212,175,55,0.3)', borderRight: '2px solid rgba(212,175,55,0.3)', borderRadius: '0 0 4px 0', pointerEvents: 'none' }} />

        {/* Content */}
        <div className={heroLoaded ? 'hero-content' : ''} style={{ maxWidth: 820, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1, textAlign: 'center' }}>

          {/* Badge */}
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: 'rgba(212,175,55,0.12)', border: '1px solid rgba(212,175,55,0.45)', borderRadius: 100, padding: '7px 20px', marginBottom: 28 }}>
            <span className="pulse-dot" style={{ width: 7, height: 7, borderRadius: '50%', background: '#D4AF37', display: 'inline-block', flexShrink: 0 }} />
            <span style={{ color: '#D4AF37', fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
              Plateforme N°1 IA Immobilière en Tunisie
            </span>
          </div>

          {/* Headline */}
          <h1 style={{ fontSize: 'clamp(2.2rem, 5.5vw, 3.75rem)', fontWeight: 900, lineHeight: 1.1, marginBottom: 22, color: '#fff', letterSpacing: '-0.02em' }}>
            L&apos;immobilier tunisien,{' '}
            <br className="hidden sm:block" />
            <span className="gold-shimmer">analysé par l&apos;IA</span>
          </h1>

          {/* Sub-headline */}
          <p style={{ color: 'rgba(255,255,255,0.65)', fontSize: '1.1rem', lineHeight: 1.65, marginBottom: 44, maxWidth: 620, marginLeft: 'auto', marginRight: 'auto' }}>
            Recherchez, évaluez et investissez avec <strong style={{ color: 'rgba(255,255,255,0.9)', fontWeight: 700 }}>9 agents IA spécialisés</strong> — prix, rentabilité, juridique, modélisation 3D, travaux et plus.
          </p>

          {/* Search bar */}
          <form onSubmit={handleSearch} style={{ display: 'flex', maxWidth: 680, margin: '0 auto 36px', background: 'rgba(255,255,255,0.07)', backdropFilter: 'blur(24px)', borderRadius: 18, padding: 6, border: '1px solid rgba(255,255,255,0.18)', boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}>
            <Search style={{ width: 18, height: 18, color: 'rgba(255,255,255,0.4)', margin: 'auto 12px auto 14px', flexShrink: 0 }} />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Appartement 3 pièces à Sousse sous 250 000 TND..."
              className="search-input"
              style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: '#fff', fontSize: 15, padding: '14px 8px', minWidth: 0 }}
            />
            <button type="submit" style={{ background: 'linear-gradient(135deg,#D4AF37,#F59E0B)', color: '#00204a', border: 'none', borderRadius: 13, padding: '13px 28px', fontWeight: 800, fontSize: 14, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 7, whiteSpace: 'nowrap', flexShrink: 0, boxShadow: '0 4px 15px rgba(212,175,55,0.4)' }}>
              Rechercher
            </button>
          </form>

          {/* CTA row */}
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            {[
              { href: '/predict', icon: Brain,  label: 'Agents IA',        style: { background: 'linear-gradient(135deg,#005555,#007777)', boxShadow: '0 4px 20px rgba(0,85,85,0.45)' } },
              { href: '/villa3d', icon: Box,    label: 'Générateur 3D',    style: { background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.22)' } },
              { href: '/search',  icon: Grid3X3, label: 'Voir les annonces', style: { background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.15)' } },
            ].map(({ href, icon: Icon, label, style }) => (
              <Link key={href} href={href} style={{ color: '#fff', padding: '13px 24px', borderRadius: 14, fontWeight: 600, fontSize: 14, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 8, transition: 'opacity 0.2s', ...style }}>
                <Icon style={{ width: 16, height: 16 }} />
                {label}
              </Link>
            ))}
          </div>

          {/* Trust row */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: 32, marginTop: 48, flexWrap: 'wrap' }}>
            {[
              { icon: Zap,       label: 'Réponse en temps réel' },
              { icon: Building2, label: '5 500+ annonces' },
              { icon: Star,      label: '9 agents IA spécialisés' },
            ].map(({ icon: Icon, label }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'rgba(255,255,255,0.55)', fontSize: 13 }}>
                <Icon style={{ width: 15, height: 15, color: '#D4AF37' }} />
                {label}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── MAIN CONTENT ───────────────────────────────────────────────── */}
      <div style={{ maxWidth: '100%', paddingTop: 72 }} className="space-y-20">

        {/* ── Market stats ──────────────────────────────────────────────── */}
        {(totalBiens || avgPrice) && (
          <section>
            <div style={{ textAlign: 'center', marginBottom: 36 }}>
              <p style={{ color: '#0369a1', fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>Marché Immobilier</p>
              <h2 style={{ fontSize: 'clamp(1.5rem,3vw,2.2rem)', fontWeight: 800, color: '#00204a' }}>En chiffres, maintenant</h2>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
              {STAT_CONFIG.map(({ key, label, icon: Icon, bg }, i) => (
                <div key={key} className="stat-card" style={{ background: bg, borderRadius: 22, padding: '28px 24px', color: '#fff', position: 'relative', overflow: 'hidden', boxShadow: '0 10px 30px -5px rgba(0,0,0,0.3)', animationDelay: `${i * 0.1}s` }}>
                  <div style={{ position: 'absolute', top: -12, right: -12, opacity: 0.12 }}>
                    <Icon style={{ width: 80, height: 80 }} />
                  </div>
                  <div style={{ width: 40, height: 40, borderRadius: 12, background: 'rgba(255,255,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
                    <Icon style={{ width: 20, height: 20, color: '#fff' }} />
                  </div>
                  <p style={{ fontSize: '1.7rem', fontWeight: 900, marginBottom: 4, lineHeight: 1 }}>{statValues[i]}</p>
                  <p style={{ fontSize: 12, opacity: 0.75, fontWeight: 500 }}>{label}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Latest listings ───────────────────────────────────────────── */}
        {latestListings.length > 0 && (
          <section>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 28, flexWrap: 'wrap', gap: 12 }}>
              <div>
                <p style={{ color: '#0369a1', fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 6 }}>Dernières annonces</p>
                <h2 style={{ fontSize: 'clamp(1.4rem,2.5vw,2rem)', fontWeight: 800, color: '#00204a', margin: 0 }}>Biens récemment indexés</h2>
              </div>
              <Link href="/search" className="listing-section-link" style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, fontWeight: 600, color: '#0284c7', textDecoration: 'none', padding: '8px 18px', background: '#f0f9ff', borderRadius: 10, border: '1px solid #bae6fd' }}>
                Voir toutes <ChevronRight style={{ width: 16, height: 16 }} />
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {latestListings.map(l => (
                <ListingCard key={l.id} listing={{ ...l, size: l.surface_m2 }} />
              ))}
            </div>
          </section>
        )}

        {/* ── Tunisia map ───────────────────────────────────────────────── */}
        <section>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <p style={{ color: '#0369a1', fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>Couverture nationale</p>
            <h2 style={{ fontSize: 'clamp(1.4rem,2.5vw,2rem)', fontWeight: 800, color: '#00204a' }}>Carte du marché tunisien</h2>
          </div>
          <div style={{ borderRadius: 24, overflow: 'hidden', border: '1px solid #e2e8f0', boxShadow: '0 8px 40px -10px rgba(0,32,74,0.15)', height: 440 }}>
            <DynamicMap center={[33.8869, 9.5375]} zoom={6} markers={mapMarkers} height="440px" />
          </div>
        </section>

        {/* ── Agent features ─────────────────────────────────────────────── */}
        <section style={{ paddingBottom: 40 }}>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <p style={{ color: '#0369a1', fontSize: 12, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>Intelligence artificielle</p>
            <h2 style={{ fontSize: 'clamp(1.6rem,3.5vw,2.4rem)', fontWeight: 900, color: '#00204a', marginBottom: 12 }}>9 Agents IA à votre service</h2>
            <p style={{ color: '#64748b', fontSize: '1rem', maxWidth: 560, margin: '0 auto' }}>
              Une suite complète d&apos;agents spécialisés pour couvrir chaque aspect de votre projet immobilier en Tunisie.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))', gap: 20 }}>
            {AGENT_FEATURES.map(({ icon: Icon, title, desc, href, gradient, glow }, i) => (
              <Link key={href} href={href} style={{ textDecoration: 'none', animationDelay: `${i * 0.07}s` }} className="agent-card">
                <div style={{ background: gradient, borderRadius: 22, padding: '28px 26px 26px', position: 'relative', overflow: 'hidden', boxShadow: `0 12px 40px -8px ${glow}`, height: '100%' }}>
                  {/* Decorative arc */}
                  <div style={{ position: 'absolute', top: -40, right: -40, width: 150, height: 150, borderRadius: '50%', background: 'rgba(255,255,255,0.06)', pointerEvents: 'none' }} />
                  <div style={{ position: 'absolute', top: -10, right: -10, width: 80, height: 80, borderRadius: '50%', background: 'rgba(255,255,255,0.05)', pointerEvents: 'none' }} />

                  {/* Icon */}
                  <div style={{ width: 52, height: 52, borderRadius: 16, background: 'rgba(255,255,255,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20, border: '1px solid rgba(255,255,255,0.25)' }}>
                    <Icon style={{ width: 26, height: 26, color: '#fff' }} />
                  </div>

                  <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff', marginBottom: 10, lineHeight: 1.3 }}>{title}</h3>
                  <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.72)', lineHeight: 1.6, marginBottom: 20 }}>{desc}</p>

                  {/* Arrow */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'rgba(255,255,255,0.6)', fontSize: 12, fontWeight: 600 }}>
                    Explorer <ArrowRight style={{ width: 14, height: 14 }} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* ── Bottom CTA Banner ─────────────────────────────────────────── */}
        <section style={{ marginBottom: 24 }}>
          <div style={{ background: 'linear-gradient(135deg, #00204a 0%, #005555 50%, #003366 100%)', borderRadius: 28, padding: 'clamp(36px,6vw,60px) clamp(24px,6vw,80px)', position: 'relative', overflow: 'hidden', textAlign: 'center' }}>
            <div style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(rgba(255,255,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.03) 1px,transparent 1px)', backgroundSize: '48px 48px', pointerEvents: 'none' }} />
            <div style={{ position: 'absolute', top: -60, right: -60, width: 300, height: 300, borderRadius: '50%', background: 'radial-gradient(circle, rgba(212,175,55,0.15) 0%, transparent 70%)', pointerEvents: 'none' }} />
            <div style={{ position: 'relative', zIndex: 1 }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: 'rgba(212,175,55,0.15)', border: '1px solid rgba(212,175,55,0.4)', borderRadius: 100, padding: '5px 16px', marginBottom: 20 }}>
                <Zap style={{ width: 13, height: 13, color: '#D4AF37' }} />
                <span style={{ color: '#D4AF37', fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Commencez maintenant</span>
              </div>
              <h2 style={{ fontSize: 'clamp(1.6rem,3.5vw,2.4rem)', fontWeight: 900, color: '#fff', marginBottom: 14 }}>
                Trouvez votre bien idéal en Tunisie
              </h2>
              <p style={{ color: 'rgba(255,255,255,0.65)', fontSize: '1rem', marginBottom: 36, maxWidth: 500, margin: '0 auto 36px' }}>
                Laissez nos agents IA analyser le marché pour vous et prendre la meilleure décision immobilière.
              </p>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
                <Link href="/advisor" style={{ background: 'linear-gradient(135deg,#D4AF37,#F59E0B)', color: '#00204a', padding: '14px 32px', borderRadius: 14, fontWeight: 800, fontSize: 15, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 8, boxShadow: '0 6px 24px rgba(212,175,55,0.4)' }}>
                  <MessageSquare style={{ width: 18, height: 18 }} />
                  Parler au conseiller IA
                </Link>
                <Link href="/search" style={{ background: 'rgba(255,255,255,0.1)', color: '#fff', padding: '14px 32px', borderRadius: 14, fontWeight: 700, fontSize: 15, textDecoration: 'none', border: '1px solid rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Grid3X3 style={{ width: 18, height: 18 }} />
                  Parcourir les annonces
                </Link>
              </div>
            </div>
          </div>
        </section>

      </div>
    </>
  )
}
