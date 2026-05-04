'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useState, useEffect, useRef } from 'react'
import {
  Home, Search, BarChart2, MessageSquare, GitCompare, Building2,
  Calculator, Scale, MapPin, Brain, LogIn, LogOut,
  UserPlus, LayoutDashboard, Crown, ChevronDown, Box, Lock,
  TrendingUp, Menu, X,
} from 'lucide-react'
import { getMe, logout, getSubscriptionStatus, BackendUser } from '@/lib/api'

const PUBLIC_LINKS = [
  { href: '/',       label: 'Accueil',    icon: Home },
  { href: '/search', label: 'Annonces',   icon: Search },
]

const PREMIUM_LINKS = [
  { href: '/forecast',  label: 'Marché',     icon: TrendingUp,    roles: ['investor', 'admin'] },
  { href: '/predict',   label: 'Agents IA',  icon: Brain,         roles: ['investor', 'admin'] },
  { href: '/villa3d',   label: 'Villa 3D',   icon: Box,           roles: ['investor', 'admin'] },
  { href: '/compare',   label: 'Comparer',   icon: GitCompare,    roles: ['investor', 'admin'] },
  { href: '/devis',     label: 'Devis',      icon: Calculator,    roles: ['investor', 'admin'] },
  { href: '/advisor',   label: 'Conseiller', icon: MessageSquare, roles: ['investor', 'seller', 'admin'] },
  { href: '/lifestyle', label: 'Lifestyle',  icon: MapPin,        roles: ['investor', 'admin'] },
  { href: '/legal',     label: 'Juridique',  icon: Scale,         roles: ['investor', 'seller', 'admin', 'user'] },
]

export default function Navbar() {
  const path   = usePathname()
  const router = useRouter()
  const [user,       setUser]       = useState<BackendUser | null>(null)
  const [subActive,  setSubActive]  = useState(false)
  const [menuOpen,   setMenuOpen]   = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const dropRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getMe().then(u => {
      setUser(u)
      if (u.role === 'investor') {
        getSubscriptionStatus()
          .then(s => setSubActive(s?.active ?? false))
          .catch(() => setSubActive(false))
      } else if (u.role === 'admin') {
        setSubActive(true)
      }
    }).catch(() => setUser(null))
  }, [path])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  async function handleLogout() {
    await logout()
    setUser(null)
    setSubActive(false)
    router.push('/')
  }

  function canAccessPremium(link: typeof PREMIUM_LINKS[0]) {
    if (!user) return false
    if (!link.roles.includes(user.role)) return false
    if (user.role === 'investor') return subActive
    return true
  }

  const visiblePremium = PREMIUM_LINKS.filter(canAccessPremium)
  const investorLocked = user?.role === 'investor' && !subActive

  const isActive = (href: string) =>
    href === '/' ? path === '/' : path.startsWith(href)

  return (
    <>
      <nav className="sticky top-0 z-50 bg-slate-950 border-b border-slate-800/60 shadow-[0_1px_20px_rgba(0,0,0,0.4)]">
        <div className="max-w-7xl mx-auto px-4 lg:px-6">
          <div className="flex items-center justify-between h-16">

            {/* ── Logo ── */}
            <Link href="/" className="flex items-center gap-2.5 flex-shrink-0 group">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-lg group-hover:shadow-amber-500/30 transition-shadow">
                <Building2 className="w-4 h-4 text-white" strokeWidth={2.5} />
              </div>
              <span className="font-bold text-white text-[15px] tracking-tight">
                Estate<span className="text-amber-400">Mind</span>
              </span>
            </Link>

            {/* ── Desktop nav ── */}
            <div className="hidden lg:flex items-center gap-0.5 flex-1 ml-8">
              {PUBLIC_LINKS.map(({ href, label, icon: Icon }) => (
                <Link key={href} href={href}
                  className={cn(
                    'flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-[13px] font-medium transition-all',
                    isActive(href)
                      ? 'bg-white/10 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  )}>
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </Link>
              ))}

              {visiblePremium.length > 0 && (
                <div className="w-px h-5 bg-slate-700 mx-1.5" />
              )}

              {visiblePremium.map(({ href, label, icon: Icon }) => (
                <Link key={href} href={href}
                  className={cn(
                    'flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-[13px] font-medium transition-all',
                    isActive(href)
                      ? 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30'
                      : 'text-slate-400 hover:text-amber-300 hover:bg-amber-500/8'
                  )}>
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </Link>
              ))}

              {(user?.role === 'user' || investorLocked) && (
                <Link href="/subscription"
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[13px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 hover:border-amber-400/40 transition-all ml-1">
                  {investorLocked ? <Lock className="w-3.5 h-3.5" /> : <Crown className="w-3.5 h-3.5" />}
                  {investorLocked ? 'Activer' : 'Premium'}
                </Link>
              )}
            </div>

            {/* ── Auth ── */}
            <div className="flex items-center gap-2 flex-shrink-0 ml-4">
              {user ? (
                <div className="relative" ref={dropRef}>
                  <button
                    onClick={() => setMenuOpen(o => !o)}
                    className="flex items-center gap-2 pl-1 pr-3 py-1.5 rounded-xl text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5 transition-all"
                  >
                    <div className={cn(
                      'w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm shadow-inner',
                      user.role === 'investor' && subActive
                        ? 'bg-gradient-to-br from-amber-400 to-amber-600 text-white'
                        : user.role === 'admin'
                        ? 'bg-gradient-to-br from-red-500 to-red-700 text-white'
                        : 'bg-slate-700 text-slate-200'
                    )}>
                      {user.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="hidden md:block text-left">
                      <p className="text-[13px] font-semibold text-white leading-none mb-0.5 max-w-[90px] truncate">{user.name}</p>
                      <p className="text-[11px] text-slate-500 capitalize leading-none flex items-center gap-1">
                        {user.role}
                        {user.role === 'investor' && subActive && <Crown className="w-2.5 h-2.5 text-amber-400" />}
                      </p>
                    </div>
                    <ChevronDown className={cn('w-3 h-3 text-slate-500 transition-transform', menuOpen && 'rotate-180')} />
                  </button>

                  {menuOpen && (
                    <div className="absolute right-0 top-full mt-2 w-56 bg-slate-900 border border-slate-700/60 rounded-2xl shadow-2xl shadow-black/50 py-2 z-50 overflow-hidden">
                      {/* User header */}
                      <div className="px-4 py-3 border-b border-slate-800">
                        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-widest mb-1 flex items-center gap-1">
                          {user.role}
                          {user.role === 'investor' && subActive && <Crown className="w-3 h-3 text-amber-400" />}
                        </p>
                        <p className="text-sm text-white font-medium truncate">{user.name}</p>
                        <p className="text-xs text-slate-500 truncate">{user.email}</p>
                      </div>

                      <div className="py-1">
                        {(user.role === 'seller' || user.role === 'admin') && (
                          <Link href="/dashboard" onClick={() => setMenuOpen(false)}
                            className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-300 hover:text-white hover:bg-white/5 transition-colors">
                            <LayoutDashboard className="w-4 h-4 text-slate-500" /> Tableau de bord
                          </Link>
                        )}

                        {user.role === 'admin' && (
                          <Link href="/admin" onClick={() => setMenuOpen(false)}
                            className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-300 hover:text-white hover:bg-white/5 transition-colors">
                            <LayoutDashboard className="w-4 h-4 text-red-400" /> Admin
                          </Link>
                        )}

                        {(user.role === 'user' || investorLocked) && (
                          <Link href="/subscription" onClick={() => setMenuOpen(false)}
                            className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 transition-colors">
                            <Crown className="w-4 h-4" />
                            {investorLocked ? "Activer l'abonnement" : 'Devenir Investisseur'}
                          </Link>
                        )}
                      </div>

                      <div className="border-t border-slate-800 pt-1">
                        <button onClick={handleLogout}
                          className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-slate-400 hover:text-red-400 hover:bg-red-500/5 transition-colors">
                          <LogOut className="w-4 h-4" /> Déconnexion
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Link href="/auth/login"
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-[13px] font-medium text-slate-400 hover:text-white hover:bg-white/5 transition-all">
                    <LogIn className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Connexion</span>
                  </Link>
                  <Link href="/auth/register"
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-[13px] font-semibold bg-gradient-to-r from-amber-500 to-amber-600 text-white hover:from-amber-400 hover:to-amber-500 transition-all shadow-lg shadow-amber-500/20">
                    <UserPlus className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Inscription</span>
                  </Link>
                </div>
              )}

              {/* Mobile menu toggle */}
              <button
                onClick={() => setMobileOpen(o => !o)}
                className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors ml-1"
              >
                {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </div>

        {/* ── Mobile drawer ── */}
        {mobileOpen && (
          <div className="lg:hidden border-t border-slate-800 bg-slate-950 pb-4">
            <div className="max-w-7xl mx-auto px-4 pt-3 space-y-0.5">
              {PUBLIC_LINKS.map(({ href, label, icon: Icon }) => (
                <Link key={href} href={href} onClick={() => setMobileOpen(false)}
                  className={cn(
                    'flex items-center gap-2.5 px-3.5 py-3 rounded-xl text-sm font-medium transition-all',
                    isActive(href) ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'
                  )}>
                  <Icon className="w-4 h-4" /> {label}
                </Link>
              ))}

              {visiblePremium.length > 0 && (
                <div className="pt-2 pb-1">
                  <p className="px-3.5 text-[10px] font-semibold text-slate-600 uppercase tracking-widest mb-1">Premium</p>
                  {visiblePremium.map(({ href, label, icon: Icon }) => (
                    <Link key={href} href={href} onClick={() => setMobileOpen(false)}
                      className={cn(
                        'flex items-center gap-2.5 px-3.5 py-3 rounded-xl text-sm font-medium transition-all',
                        isActive(href) ? 'bg-amber-500/15 text-amber-300' : 'text-slate-400 hover:text-amber-300 hover:bg-amber-500/8'
                      )}>
                      <Icon className="w-4 h-4" /> {label}
                    </Link>
                  ))}
                </div>
              )}

              {(user?.role === 'user' || investorLocked) && (
                <Link href="/subscription" onClick={() => setMobileOpen(false)}
                  className="flex items-center gap-2.5 px-3.5 py-3 rounded-xl text-sm font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 mt-2">
                  <Crown className="w-4 h-4" />
                  {investorLocked ? "Activer l'abonnement" : 'Devenir Investisseur Premium'}
                </Link>
              )}
            </div>
          </div>
        )}
      </nav>
    </>
  )
}
