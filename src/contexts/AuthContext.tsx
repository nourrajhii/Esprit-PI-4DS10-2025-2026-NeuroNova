import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from 'react'

export type User = {
  email: string
  name: string
  token: string
  role: UserRole
}

export type UserRole =
  | 'individual_investor'
  | 'professional_investor'
  | 'real_estate_agency'
  | 'developer_fund'

const STORAGE_KEY = 'realstate_auth'

function readStored(): User | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as User
    if (!parsed?.email || !parsed?.token) return null
    // Backward compatible: if user was saved without role, assume individual.
    if (!parsed.role) (parsed as unknown as { role?: UserRole }).role = 'individual_investor'
    return parsed
  } catch {
    return null
  }
}

let cache: User | null = readStored()
const listeners = new Set<() => void>()

function setUser(next: User | null) {
  cache = next
  if (next) localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  else localStorage.removeItem(STORAGE_KEY)
  listeners.forEach((l) => l())
}

type AuthContextValue = {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string, role: UserRole) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function subscribe(cb: () => void) {
  listeners.add(cb)
  return () => listeners.delete(cb)
}

function getSnapshot() {
  return cache
}

function getServerSnapshot() {
  return null
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const user = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)

  const login = useCallback(async (email: string, _password: string) => {
    await new Promise((r) => setTimeout(r, 300))

    // Demo auth: we only support one saved user in localStorage.
    const stored = readStored()
    if (!stored || stored.email !== email) {
      throw new Error('Invalid credentials (demo). Please register first.')
    }

    const token = btoa(`${email}:${Date.now()}`)
    setUser({ ...stored, token })
  }, [])

  const register = useCallback(
    async (name: string, email: string, _password: string, role: UserRole) => {
      await new Promise((r) => setTimeout(r, 500))
      const token = btoa(`${email}:${Date.now()}`)
      setUser({ email, name, token, role })
    },
    [],
  )

  const logout = useCallback(() => setUser(null), [])

  const value = useMemo(
    () => ({ user, login, register, logout }),
    [user, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
