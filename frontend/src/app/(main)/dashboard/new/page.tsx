'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, createListing } from '@/lib/api'
import { GOVERNORATS } from '@/lib/utils'
import { Plus, Loader2 } from 'lucide-react'

export default function NewListingPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const [images,  setImages]  = useState<FileList | null>(null)
  const [form, setForm] = useState({
    title: '', description: '', type: 'vente', price: '',
    surface: '', rooms: '', city: 'Tunis', address: '',
  })

  useEffect(() => {
    getMe().catch(() => router.push('/auth/login'))
  }, [router])

  function set(k: string) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm(f => ({ ...f, [k]: e.target.value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k, v]) => fd.append(k, v))
      if (images) Array.from(images).forEach(f => fd.append('images', f))
      await createListing(fd)
      router.push('/dashboard')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur création')
    } finally {
      setLoading(false)
    }
  }

  const field = (label: string, key: string, props = {}) => (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <input value={(form as Record<string, string>)[key]} onChange={set(key)}
        className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
        {...props} />
    </div>
  )

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Nouvelle annonce</h1>
        <p className="text-slate-500 text-sm mt-1">Publiez votre bien immobilier</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
        {error && <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>}

        {field('Titre *', 'title', { required: true, placeholder: 'Appartement 3 pièces à Sousse' })}

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
          <textarea value={form.description} onChange={set('description')} rows={3}
            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 resize-none"
            placeholder="Décrivez votre bien…" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Type *</label>
            <select value={form.type} onChange={set('type')}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400">
              <option value="vente">Vente</option>
              <option value="location">Location</option>
            </select>
          </div>
          {field('Prix (TND) *', 'price', { required: true, type: 'number', min: 0, placeholder: '350000' })}
        </div>

        <div className="grid grid-cols-2 gap-4">
          {field('Surface (m²)', 'surface', { type: 'number', min: 0, placeholder: '120' })}
          {field('Pièces', 'rooms', { type: 'number', min: 1, placeholder: '3' })}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Ville *</label>
            <select value={form.city} onChange={set('city')}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400">
              {GOVERNORATS.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          {field('Adresse', 'address', { placeholder: 'Rue Habib Bourguiba, Apt 4' })}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Photos (max 10)</label>
          <input type="file" accept="image/*" multiple
            onChange={e => setImages(e.target.files)}
            className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100" />
        </div>

        <button type="submit" disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-brand-600 text-white rounded-xl font-medium text-sm hover:bg-brand-700 disabled:opacity-50 transition-colors">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          {loading ? 'Publication…' : 'Publier l\'annonce'}
        </button>
      </form>
    </div>
  )
}
