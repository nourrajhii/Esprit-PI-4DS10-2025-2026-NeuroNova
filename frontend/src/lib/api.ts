const BASE    = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8000'
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL  || 'http://localhost:4000'

// ─── Auth helpers ─────────────────────────────────────────────────────────────

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('accessToken')
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function register(data: { name: string; email: string; password: string; phone?: string; role?: string }) {
  const res = await fetch(`${BACKEND}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Erreur inscription') }
  const body = await res.json()
  if (typeof window !== 'undefined') {
    localStorage.setItem('accessToken',  body.accessToken)
    localStorage.setItem('refreshToken', body.refreshToken)
  }
  return body
}

export async function login(email: string, password: string) {
  const res = await fetch(`${BACKEND}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Erreur connexion') }
  const body = await res.json()
  if (typeof window !== 'undefined') {
    localStorage.setItem('accessToken',  body.accessToken)
    localStorage.setItem('refreshToken', body.refreshToken)
  }
  return body
}

export async function logout() {
  await fetch(`${BACKEND}/auth/logout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
  }).catch(() => null)
  if (typeof window !== 'undefined') {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
  }
}

export async function getMe() {
  const res = await fetch(`${BACKEND}/auth/me`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Non authentifié')
  return res.json() as Promise<BackendUser>
}

// ─── Backend Listings (with auth) ────────────────────────────────────────────

export async function getBackendListings(params: {
  city?: string; type?: string; min_price?: number; max_price?: number
  min_surface?: number; max_surface?: number; rooms?: number; status?: string
  page?: number; limit?: number; sort?: string; order?: string
} = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) q.set(k, String(v)) })
  const res = await fetch(`${BACKEND}/listings?${q}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Erreur récupération annonces')
  return res.json() as Promise<{ total: number; page: number; listings: BackendListing[] }>
}

export async function getBackendListing(id: string) {
  const res = await fetch(`${BACKEND}/listings/${id}`)
  if (!res.ok) throw new Error('Annonce introuvable')
  return res.json() as Promise<BackendListing>
}

export async function getPublicListings(params: {
  city?: string; type?: string; min_price?: number; max_price?: number
  min_surface?: number; rooms?: number; q?: string; page?: number; limit?: number
} = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) q.set(k, String(v)) })
  const res = await fetch(`${BACKEND}/listings?${q}`)
  if (!res.ok) throw new Error('Erreur récupération annonces')
  return res.json() as Promise<{ total: number; page: number; listings: BackendListing[] }>
}

export async function createListing(data: FormData) {
  const res = await fetch(`${BACKEND}/listings`, {
    method: 'POST',
    headers: authHeaders(),
    body: data,
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Erreur création annonce') }
  return res.json()
}

export async function updateListing(id: string, data: FormData) {
  const res = await fetch(`${BACKEND}/listings/${id}`, {
    method: 'PUT',
    headers: authHeaders(),
    body: data,
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Erreur modification') }
  return res.json()
}

export async function deleteListing(id: string) {
  const res = await fetch(`${BACKEND}/listings/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Erreur suppression') }
  return res.json()
}

export async function getMyListings() {
  const res = await fetch(`${BACKEND}/listings/mine`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Erreur récupération de vos annonces')
  return res.json() as Promise<BackendListing[]>
}

// ─── Subscription (Stripe) ────────────────────────────────────────────────────

export async function subscribeInvestor() {
  const res = await fetch(`${BACKEND}/subscription/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Erreur abonnement') }
  return res.json() as Promise<{ url: string; sessionId: string }>
}

export async function getSubscriptionStatus() {
  const res = await fetch(`${BACKEND}/subscription/status`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Erreur statut abonnement')
  return res.json() as Promise<{ active: boolean; status: string; plan: string; currentPeriodEnd: string }>
}

export async function verifySubscriptionSession(sessionId: string) {
  const res = await fetch(`${BACKEND}/subscription/verify?session_id=${sessionId}`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Erreur vérification session')
  return res.json()
}

// ─── Contacts ─────────────────────────────────────────────────────────────────

export async function sendContact(listingId: string, message: string, phone?: string) {
  const res = await fetch(`${BACKEND}/contacts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ listingId, message, phone }),
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Erreur envoi demande') }
  return res.json()
}

export async function getReceivedContacts() {
  const res = await fetch(`${BACKEND}/contacts/received`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Erreur demandes reçues')
  return res.json()
}

export async function getSentContacts() {
  const res = await fetch(`${BACKEND}/contacts/sent`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Erreur demandes envoyées')
  return res.json()
}

// ─── Admin ────────────────────────────────────────────────────────────────────

export async function getAdminStats() {
  const res = await fetch(`${BACKEND}/admin/stats`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Accès refusé ou erreur serveur')
  return res.json()
}

export async function getAdminUsers(params: { page?: number; limit?: number; role?: string; search?: string } = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) q.set(k, String(v)) })
  const res = await fetch(`${BACKEND}/admin/users?${q}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Erreur liste utilisateurs')
  return res.json()
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface BackendUser {
  id: string
  name: string
  email: string
  phone?: string
  role: 'admin' | 'seller' | 'investor' | 'user'
  isActive: boolean
  createdAt: string
}

export interface BackendListing {
  _id: string
  id: string
  title: string
  description?: string
  type: 'vente' | 'location'
  transaction_type?: string
  price: number
  surface?: number
  surface_m2?: number
  rooms?: number
  bathrooms?: number
  property_type?: string
  city: string
  address?: string
  images: string[]
  image_urls?: string[]
  status: 'active' | 'pending' | 'sold' | 'rented'
  seller?: string
  owner?: { id: string; name: string; email: string; phone?: string }
  source?: 'seller' | 'scraped'
  createdAt: string
}

export async function chat(message: string, sessionId?: string, context: Record<string, unknown> = {}) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, context }),
  })
  if (!res.ok) throw new Error(`Orchestrator error: ${res.status}`)
  return res.json()
}

export async function searchListings(prompt: string, filters: Record<string, unknown> = {}) {
  const res = await fetch(`${BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, filters }),
  })
  if (!res.ok) throw new Error(`Search error: ${res.status}`)
  return res.json()
}

export async function getListings(params: {
  city?: string
  min_price?: number
  max_price?: number
  rooms?: number
  transaction_type?: string
  limit?: number
  skip?: number
  q?: string
  by_gov?: boolean
} = {}) {
  const qs = new URLSearchParams()
  if (params.city)             qs.set('city',             params.city)
  if (params.min_price)        qs.set('min_price',        String(params.min_price))
  if (params.max_price)        qs.set('max_price',        String(params.max_price))
  if (params.rooms)            qs.set('rooms',            String(params.rooms))
  if (params.transaction_type) qs.set('transaction_type', params.transaction_type)
  if (params.limit)            qs.set('limit',            String(params.limit))
  if (params.skip)             qs.set('skip',             String(params.skip))
  if (params.q)                qs.set('q',                params.q)
  if (params.by_gov)           qs.set('by_gov',           '1')

  // Always use internal Next.js API route → direct MongoDB connection
  const res = await fetch(`/api/listings?${qs}`)
  if (!res.ok) throw new Error(`Listings error: ${res.status}`)
  return res.json() as Promise<{ listings: MongoListing[]; total: number; skip: number; limit: number }>
}

export async function getListingById(id: string) {
  // Internal route first (direct MongoDB), fallback to backend
  const res = await fetch(`/api/listings/${id}`)
  if (res.ok) return res.json() as Promise<MongoListing>
  // Fallback to express backend (user-uploaded listings)
  const res2 = await fetch(`${BACKEND}/listings/${id}`)
  if (!res2.ok) throw new Error(`Listing error: ${res2.status}`)
  return res2.json() as Promise<MongoListing>
}

export async function getDhiaPredict(city: string, surface: number, rooms: number) {
  const res = await fetch(`${BASE}/dhia/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ city, surface_m2: surface, rooms }),
  })
  if (!res.ok) throw new Error(`Dhia predict error: ${res.status}`)
  return res.json()
}

export async function getDhiaInvest(city: string, budget: number, surface?: number, propertyType?: string) {
  const res = await fetch(`${BASE}/dhia/invest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ city, budget, surface_m2: surface, property_type: propertyType }),
  })
  if (!res.ok) throw new Error(`Dhia invest error: ${res.status}`)
  return res.json()
}

export async function getDhiaInvestScan(params: {
  city?: string, budget?: number, min_budget?: number, top_n?: number, transaction_type?: string
}) {
  const res = await fetch(`${BASE}/dhia/invest-scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) throw new Error(`Dhia invest scan error: ${res.status}`)
  return res.json()
}

export async function getListingDetail(id: string, city = 'Tunis', price = 300000, surface = 100) {
  const params = new URLSearchParams({ city, price: String(price), surface: String(surface) })
  const res = await fetch(`${BASE}/listing/${id}?${params}`)
  if (!res.ok) throw new Error(`Listing error: ${res.status}`)
  return res.json()
}

export async function getForecast(governorat: string, months = 12) {
  const res = await fetch(`${BASE}/forecast/${encodeURIComponent(governorat)}?months=${months}`)
  if (!res.ok) throw new Error(`Forecast error: ${res.status}`)
  return res.json()
}

export async function getMarketSummary() {
  // Internal route → direct MongoDB aggregation
  const res = await fetch('/api/market/summary')
  if (!res.ok) throw new Error(`Market summary error: ${res.status}`)
  return res.json()
}

export async function getHealth() {
  const res = await fetch(`${BASE}/health`)
  if (!res.ok) throw new Error(`Health error: ${res.status}`)
  return res.json()
}

export interface MongoListing {
  _id?: string
  id: string
  title: string
  price: number
  city: string
  surface_m2?: number
  surface?: number
  rooms?: number
  bathrooms?: number
  property_type?: string
  transaction_type?: string
  type?: string
  listing_url?: string
  image_urls?: string[]
  images?: string[]
  description?: string
  agency_owner?: string
  phone?: string
  source?: string
}
