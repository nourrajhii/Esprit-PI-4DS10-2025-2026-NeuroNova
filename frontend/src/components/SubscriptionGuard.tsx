'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, getSubscriptionStatus } from '@/lib/api'
import { Crown, Loader2 } from 'lucide-react'
import Link from 'next/link'

interface Props {
  children: React.ReactNode
  /** Allow these roles without subscription check (default: ['admin']) */
  freeRoles?: string[]
}

export default function SubscriptionGuard({ children, freeRoles = ['admin'] }: Props) {
  const router = useRouter()
  const [state, setState] = useState<'loading' | 'ok' | 'no-auth' | 'no-sub'>('loading')

  useEffect(() => {
    getMe()
      .then(user => {
        if (freeRoles.includes(user.role)) { setState('ok'); return }
        if (user.role !== 'investor') { setState('no-auth'); return }
        getSubscriptionStatus()
          .then(s => setState(s?.active ? 'ok' : 'no-sub'))
          .catch(() => setState('no-sub'))
      })
      .catch(() => setState('no-auth'))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Redirect must be in an effect — never during render
  useEffect(() => {
    if (state === 'no-auth') router.push('/auth/login')
  }, [state, router])

  if (state === 'loading' || state === 'no-auth') {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    )
  }

  if (state === 'no-sub') {
    return (
      <div className="max-w-md mx-auto mt-24 text-center space-y-5">
        <div className="w-20 h-20 rounded-full bg-amber-100 flex items-center justify-center mx-auto">
          <Crown className="w-10 h-10 text-amber-600" />
        </div>
        <h1 className="text-2xl font-bold text-slate-800">Accès Investisseur Premium requis</h1>
        <p className="text-slate-500">
          Cette fonctionnalité est réservée aux Investisseurs avec un abonnement actif.
          Souscrivez pour accéder à tous les outils IA.
        </p>
        <Link href="/subscription"
          className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl font-semibold hover:bg-primary-600 transition-colors">
          <Crown className="w-5 h-5" />
          S&apos;abonner — 6 EUR / mois
        </Link>
        <p className="text-xs text-slate-400">Paiement sécurisé via Stripe · Résiliable à tout moment</p>
      </div>
    )
  }

  return <>{children}</>
}
