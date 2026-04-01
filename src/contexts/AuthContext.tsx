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
}

const STORAGE_KEY = 'realstate_auth'

function readStored(): User | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as User
    if (!parsed?.email || !parsed?.token) return null
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
  register: (name: string, email: string, password: string) => Promise<void>
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
    await new Promise((r) => setTimeout(r, 400))
    const name = email.split('@')[0].replace(/[._]/g, ' ')
    const token = btoa(`${email}:${Date.now()}`)
    setUser({ email, name: name.charAt(0).toUpperCase() + name.slice(1), token })
  }, [])

  const register = useCallback(
    async (name: string, email: string, _password: string) => {
      await new Promise((r) => setTimeout(r, 500))
      const token = btoa(`${email}:${Date.now()}`)
      setUser({ email, name, token })
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
