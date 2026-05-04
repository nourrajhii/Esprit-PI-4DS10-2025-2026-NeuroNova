'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, getAdminStats, getAdminUsers } from '@/lib/api'
import { Users, Home, MessageSquare, Crown, TrendingUp, MapPin, Loader2 } from 'lucide-react'

interface Stats {
  totals: { listings: number; users: number; contacts: number; activeSubscriptions: number }
  byType: Array<{ type: string; count: string }>
  byStatus: Array<{ status: string; count: string }>
  byRole: Array<{ role: string; count: string }>
  byMonth: Array<{ month: string; count: string }>
  topCities: Array<{ city: string; count: string }>
}

export default function AdminPage() {
  const router = useRouter()
  const [stats, setStats]   = useState<Stats | null>(null)
  const [users, setUsers]   = useState<unknown[]>([])
  const [tab,   setTab]     = useState<'stats' | 'users'>('stats')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMe()
      .then(u => { if (u.role !== 'admin') { router.push('/'); return } })
      .catch(() => router.push('/auth/login'))

    Promise.all([getAdminStats(), getAdminUsers({ limit: 50 })])
      .then(([s, u]) => { setStats(s); setUsers(u.users || []) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [router])

  if (loading) return (
    <div className="flex items-center justify-center mt-32">
      <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
    </div>
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Administration</h1>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        {(['stats', 'users'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}>
            {t === 'stats' ? 'Statistiques' : 'Utilisateurs'}
          </button>
        ))}
      </div>

      {tab === 'stats' && stats && (
        <div className="space-y-6">
          {/* Totals */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: Home,         label: 'Annonces',           value: stats.totals.listings,            color: 'text-blue-600',  bg: 'bg-blue-50' },
              { icon: Users,        label: 'Utilisateurs',       value: stats.totals.users,               color: 'text-purple-600',bg: 'bg-purple-50' },
              { icon: MessageSquare,label: 'Demandes',           value: stats.totals.contacts,            color: 'text-green-600', bg: 'bg-green-50' },
              { icon: Crown,        label: 'Abonnés Premium',    value: stats.totals.activeSubscriptions, color: 'text-amber-600', bg: 'bg-amber-50' },
            ].map(({ icon: Icon, label, value, color, bg }) => (
              <div key={label} className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${color}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-800">{value}</p>
                  <p className="text-xs text-slate-500">{label}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Breakdowns */}
          <div className="grid md:grid-cols-3 gap-4">
            {/* By type */}
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <h3 className="font-semibold text-slate-700 mb-3">Annonces par type</h3>
              {stats.byType.map(r => (
                <div key={r.type} className="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
                  <span className="text-sm text-slate-600 capitalize">{r.type}</span>
                  <span className="text-sm font-semibold text-slate-800">{r.count}</span>
                </div>
              ))}
            </div>

            {/* By role */}
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <h3 className="font-semibold text-slate-700 mb-3">Utilisateurs par rôle</h3>
              {stats.byRole.map(r => (
                <div key={r.role} className="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
                  <span className="text-sm text-slate-600 capitalize">{r.role}</span>
                  <span className="text-sm font-semibold text-slate-800">{r.count}</span>
                </div>
              ))}
            </div>

            {/* Top cities */}
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <h3 className="font-semibold text-slate-700 mb-3 flex items-center gap-1">
                <MapPin className="w-4 h-4 text-brand-600" />
                Top villes
              </h3>
              {stats.topCities.slice(0, 6).map(r => (
                <div key={r.city} className="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
                  <span className="text-sm text-slate-600">{r.city}</span>
                  <span className="text-sm font-semibold text-slate-800">{r.count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Monthly chart (simple bars) */}
          {stats.byMonth.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-1">
                <TrendingUp className="w-4 h-4 text-brand-600" />
                Annonces par mois
              </h3>
              <div className="flex items-end gap-2 h-32">
                {stats.byMonth.map(r => {
                  const maxVal = Math.max(...stats.byMonth.map(x => parseInt(x.count)))
                  const pct = maxVal ? (parseInt(r.count) / maxVal) * 100 : 0
                  return (
                    <div key={r.month} className="flex flex-col items-center flex-1 gap-1">
                      <span className="text-xs text-slate-500">{r.count}</span>
                      <div className="w-full bg-brand-200 rounded-t-sm" style={{ height: `${pct}%`, minHeight: 4 }} />
                      <span className="text-[10px] text-slate-400 rotate-45 origin-left">{r.month.slice(5)}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Users tab */}
      {tab === 'users' && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                {['Nom', 'Email', 'Rôle', 'Actif', 'Inscrit le'].map(h => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-slate-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(users as Array<{ id: string; name: string; email: string; role: string; isActive: boolean; createdAt: string }>).map(u => (
                <tr key={u.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-800">{u.name}</td>
                  <td className="px-4 py-3 text-slate-500">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      u.role === 'admin'    ? 'bg-red-50 text-red-700' :
                      u.role === 'investor' ? 'bg-amber-50 text-amber-700' :
                      u.role === 'seller'   ? 'bg-blue-50 text-blue-700' :
                      'bg-slate-100 text-slate-600'
                    }`}>{u.role}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`w-2 h-2 rounded-full inline-block ${u.isActive ? 'bg-green-500' : 'bg-red-400'}`} />
                  </td>
                  <td className="px-4 py-3 text-slate-400">{new Date(u.createdAt).toLocaleDateString('fr-TN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
