'use client'
import { useEffect, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { verifySubscriptionSession } from '@/lib/api'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'

function SuccessContent() {
  const params = useSearchParams()
  const router = useRouter()
  const [status, setStatus] = useState<'loading' | 'ok' | 'fail'>('loading')

  useEffect(() => {
    const sid = params.get('session_id')
    if (!sid) { setStatus('fail'); return }
    verifySubscriptionSession(sid)
      .then(d => setStatus(d.success ? 'ok' : 'fail'))
      .catch(() => setStatus('fail'))
  }, [params])

  if (status === 'loading') return (
    <div className="flex flex-col items-center gap-4 mt-32">
      <Loader2 className="w-10 h-10 animate-spin text-primary" />
      <p className="text-slate-500">Confirmation de votre paiement en cours…</p>
    </div>
  )

  if (status === 'ok') return (
    <div className="max-w-sm mx-auto mt-24 text-center space-y-4">
      <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center mx-auto">
        <CheckCircle2 className="w-10 h-10 text-green-600" />
      </div>
      <h1 className="text-2xl font-bold text-slate-800">Abonnement activé !</h1>
      <p className="text-slate-500">
        Bienvenue en tant qu&apos;Investisseur Premium EstateMind.
        Vous recevrez des alertes pour chaque nouvelle annonce de vente.
      </p>
      <button onClick={() => router.push('/')}
        className="px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-600 transition-colors">
        Accéder à la plateforme
      </button>
    </div>
  )

  return (
    <div className="max-w-sm mx-auto mt-24 text-center space-y-4">
      <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center mx-auto">
        <XCircle className="w-10 h-10 text-red-500" />
      </div>
      <h1 className="text-xl font-bold text-slate-800">Paiement non confirmé</h1>
      <p className="text-slate-500 text-sm">Réessayez ou contactez le support.</p>
      <button onClick={() => router.push('/subscription')}
        className="px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-600 transition-colors">
        Retour à l&apos;abonnement
      </button>
    </div>
  )
}

export default function SuccessPage() {
  return <Suspense><SuccessContent /></Suspense>
}
