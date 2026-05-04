'use client'
import { useState, useEffect } from 'react'
import { subscribeInvestor, getSubscriptionStatus, getMe } from '@/lib/api'
import { Crown, CheckCircle2, Zap, Bell, TrendingUp, Scale, Calculator, Box } from 'lucide-react'
import { useRouter } from 'next/navigation'

const FEATURES = [
  { icon: TrendingUp,   text: 'Prévisions du marché immobilier sur 12 mois par gouvernorat' },
  { icon: Bell,         text: 'Alertes instantanées pour chaque nouvelle annonce de vente' },
  { icon: Zap,          text: 'Agents IA : prédiction de prix & scoring investissement' },
  { icon: Scale,        text: 'Assistant juridique immobilier tunisien' },
  { icon: Calculator,   text: 'Estimation devis construction & rénovation' },
  { icon: Box,          text: 'Générateur de villas 3D (Stable Diffusion + Triverse.ai)' },
  { icon: CheckCircle2, text: 'Comparaison avancée de biens immobiliers' },
]

export default function SubscriptionPage() {
  const router  = useRouter()
  const [loading, setLoading]   = useState(false)
  const [status, setStatus]     = useState<{ active: boolean; plan?: string; currentPeriodEnd?: string } | null>(null)
  const [error, setError]       = useState('')

  useEffect(() => {
    getMe().catch(() => router.push('/auth/login'))
    getSubscriptionStatus().then(setStatus).catch(() => null)
  }, [router])

  async function handleSubscribe() {
    setError('')
    setLoading(true)
    try {
      const { url } = await subscribeInvestor()
      window.location.href = url
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur lors de la redirection Stripe')
      setLoading(false)
    }
  }

  if (status?.active) {
    return (
      <div className="max-w-lg mx-auto mt-16 text-center">
        <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-5">
          <CheckCircle2 className="w-10 h-10 text-green-600" />
        </div>
        <h1 className="text-2xl font-bold text-slate-800">Abonnement actif</h1>
        <p className="text-slate-500 mt-2">Vous bénéficiez d&apos;un accès Investisseur Premium complet.</p>
        {status.currentPeriodEnd && (
          <p className="text-sm text-slate-400 mt-1">
            Prochain renouvellement : {new Date(status.currentPeriodEnd).toLocaleDateString('fr-TN')}
          </p>
        )}
        <button onClick={() => router.push('/')}
          className="mt-6 px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-600 transition-colors">
          Accéder à la plateforme
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-xl mx-auto mt-8 space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex items-center gap-2 bg-amber-100 text-amber-700 px-4 py-1.5 rounded-full text-sm font-semibold mb-4">
          <Crown className="w-4 h-4" />
          Investisseur Premium
        </div>
        <h1 className="text-3xl font-bold text-slate-900">Accès complet EstateMind</h1>
        <p className="text-slate-500 mt-2">Toutes les fonctionnalités IA débloquées + alertes en temps réel</p>
      </div>

      {/* Price card */}
      <div className="bg-white rounded-2xl border-2 border-primary-200 shadow-sm p-8">
        <div className="text-center mb-6">
          <div className="text-5xl font-bold text-primary">6 <span className="text-2xl font-normal text-slate-500">EUR</span></div>
          <div className="text-slate-500 text-sm mt-1">par mois — Résiliable à tout moment</div>
        </div>

        <div className="space-y-3">
          {FEATURES.map(({ icon: Icon, text }) => (
            <div key={text} className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary-50 flex items-center justify-center flex-shrink-0">
                <Icon className="w-4 h-4 text-primary" />
              </div>
              <span className="text-sm text-slate-700">{text}</span>
            </div>
          ))}
        </div>

        {error && (
          <div className="mt-4 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>
        )}

        <button onClick={handleSubscribe} disabled={loading}
          className="mt-6 w-full flex items-center justify-center gap-2 px-6 py-4 bg-primary text-white rounded-xl font-semibold text-base hover:bg-primary-600 disabled:opacity-50 transition-colors">
          <Crown className="w-5 h-5" />
          {loading ? 'Redirection vers Stripe…' : "S'abonner — 6 EUR / mois"}
        </button>

        <p className="text-xs text-slate-400 text-center mt-3">Paiement sécurisé via Stripe</p>
      </div>
    </div>
  )
}
