'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { register } from '@/lib/api'
import { Building2, UserPlus } from 'lucide-react'

export default function RegisterPage() {
  const router = useRouter()
  const [form, setForm] = useState({ name: '', email: '', password: '', phone: '', role: 'user' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function set(k: string) { return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm(f => ({ ...f, [k]: e.target.value })) }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password.length < 6) return setError('Mot de passe trop court (min. 6 caractères)')
    setLoading(true)
    try {
      await register(form)
      router.push('/')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur inscription')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 text-primary font-bold text-2xl mb-2">
            <Building2 className="w-7 h-7" />
            EstateMind
          </div>
          <h1 className="text-2xl font-bold text-slate-800">Créer un compte</h1>
          <p className="text-slate-500 text-sm mt-1">Rejoignez la plateforme immobilière N°1 en Tunisie</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          {error && (
            <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nom complet</label>
            <input type="text" required value={form.name} onChange={set('name')}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Mohamed Ben Ali" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input type="email" required value={form.email} onChange={set('email')}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="votre@email.com" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Mot de passe</label>
            <input type="password" required value={form.password} onChange={set('password')}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Min. 6 caractères" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Téléphone <span className="text-slate-400">(optionnel)</span></label>
            <input type="tel" value={form.phone} onChange={set('phone')}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="+216 XX XXX XXX" />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Je suis…</label>
            <select value={form.role} onChange={set('role')}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
              <option value="user">Utilisateur — consultation des services</option>
              <option value="seller">Propriétaire / Vendeur — publier des annonces</option>
              <option value="investor">Investisseur — accès aux agents IA &amp; analyses</option>
            </select>
          </div>

          <button type="submit" disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-white rounded-xl font-medium text-sm hover:bg-primary-600 disabled:opacity-50 transition-colors">
            <UserPlus className="w-4 h-4" />
            {loading ? 'Création…' : 'Créer mon compte'}
          </button>

          <p className="text-center text-sm text-slate-500">
            Déjà un compte ?{' '}
            <Link href="/auth/login" className="text-primary font-medium hover:underline">Se connecter</Link>
          </p>
        </form>
      </div>
    </div>
  )
}
