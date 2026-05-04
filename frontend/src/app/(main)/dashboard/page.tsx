'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, getMyListings, getReceivedContacts, deleteListing, BackendUser, BackendListing } from '@/lib/api'
import { Plus, Trash2, Eye, MessageSquare, Home, TrendingUp, Users, Loader2 } from 'lucide-react'
import Link from 'next/link'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser]         = useState<BackendUser | null>(null)
  const [listings, setListings] = useState<BackendListing[]>([])
  const [contacts, setContacts] = useState<unknown[]>([])
  const [loading, setLoading]   = useState(true)
  const [tab, setTab]           = useState<'listings' | 'contacts'>('listings')

  useEffect(() => {
    getMe()
      .then(u => {
        if (!['seller', 'admin'].includes(u.role)) { router.push('/'); return }
        setUser(u)
        return Promise.all([getMyListings(), getReceivedContacts()])
      })
      .then(results => {
        if (!results) return
        setListings(results[0])
        setContacts(results[1])
      })
      .catch(() => router.push('/auth/login'))
      .finally(() => setLoading(false))
  }, [router])

  async function handleDelete(id: string) {
    if (!confirm('Supprimer cette annonce ?')) return
    await deleteListing(id)
    setListings(l => l.filter(x => x.id !== id))
  }

  if (loading) return (
    <div className="flex items-center justify-center mt-32">
      <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Tableau de bord</h1>
          <p className="text-slate-500 text-sm">Bonjour, {user?.name}</p>
        </div>
        <Link href="/dashboard/new"
          className="flex items-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-xl text-sm font-medium hover:bg-brand-700 transition-colors">
          <Plus className="w-4 h-4" />
          Nouvelle annonce
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: Home,         label: 'Mes annonces', value: listings.length },
          { icon: MessageSquare,label: 'Demandes reçues', value: (contacts as unknown[]).length },
          { icon: TrendingUp,   label: 'Annonces actives', value: listings.filter(l => l.status === 'active').length },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-brand-50 flex items-center justify-center">
              <Icon className="w-5 h-5 text-brand-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800">{value}</p>
              <p className="text-xs text-slate-500">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        {(['listings', 'contacts'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}>
            {t === 'listings' ? 'Mes annonces' : 'Demandes reçues'}
          </button>
        ))}
      </div>

      {/* Listings tab */}
      {tab === 'listings' && (
        <div className="space-y-3">
          {listings.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Home className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p>Aucune annonce publiée</p>
              <Link href="/dashboard/new" className="mt-3 inline-block text-brand-600 text-sm font-medium hover:underline">
                Créer ma première annonce →
              </Link>
            </div>
          ) : listings.map(l => (
            <div key={l.id} className="bg-white rounded-xl border border-slate-200 p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                {l.images?.[0] ? (
                  <img src={l.images[0]} className="w-14 h-14 rounded-lg object-cover" alt="" />
                ) : (
                  <div className="w-14 h-14 rounded-lg bg-slate-100 flex items-center justify-center">
                    <Home className="w-6 h-6 text-slate-400" />
                  </div>
                )}
                <div>
                  <p className="font-semibold text-slate-800 text-sm">{l.title}</p>
                  <p className="text-xs text-slate-500">{l.city} · {l.type} · {Number(l.price).toLocaleString('fr-TN')} TND</p>
                  <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full font-medium ${
                    l.status === 'active'  ? 'bg-green-50 text-green-700' :
                    l.status === 'pending' ? 'bg-amber-50 text-amber-700' :
                    l.status === 'sold'    ? 'bg-blue-50 text-blue-700'   :
                    'bg-slate-100 text-slate-600'
                  }`}>{l.status}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Link href={`/dashboard/edit/${l.id}`}
                  className="p-2 rounded-lg hover:bg-slate-100 text-slate-600 transition-colors">
                  <Eye className="w-4 h-4" />
                </Link>
                <button onClick={() => handleDelete(l.id)}
                  className="p-2 rounded-lg hover:bg-red-50 text-red-500 transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Contacts tab */}
      {tab === 'contacts' && (
        <div className="space-y-3">
          {(contacts as Array<{id: string; message: string; phone?: string; status: string; createdAt: string; sender?: {name: string; email: string}; listing?: {title: string; city: string}}>).length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <MessageSquare className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p>Aucune demande reçue</p>
            </div>
          ) : (contacts as Array<{id: string; message: string; phone?: string; status: string; createdAt: string; sender?: {name: string; email: string}; listing?: {title: string; city: string}}>).map(c => (
            <div key={c.id} className="bg-white rounded-xl border border-slate-200 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-slate-800 text-sm">{c.sender?.name || 'Anonyme'}</p>
                  <p className="text-xs text-slate-400">{c.sender?.email} {c.phone && `· ${c.phone}`}</p>
                  <p className="text-xs text-slate-400 mt-0.5">Annonce : {c.listing?.title} · {c.listing?.city}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  c.status === 'pending' ? 'bg-amber-50 text-amber-700' :
                  c.status === 'read'    ? 'bg-blue-50 text-blue-700'   :
                  'bg-green-50 text-green-700'
                }`}>{c.status}</span>
              </div>
              <p className="mt-2 text-sm text-slate-600 bg-slate-50 rounded-lg px-3 py-2">{c.message}</p>
              <p className="text-xs text-slate-400 mt-1">{new Date(c.createdAt).toLocaleString('fr-TN')}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
