import type { Listing } from '../data/mockListings'

const STORAGE_KEY = 'realstate_imported_listings'
const EVENT = 'realstate-imported-listings-updated'

export function readImportedListings(): Listing[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as Listing[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function writeImportedListings(listings: Listing[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(listings))
  window.dispatchEvent(new Event(EVENT))
}

export function clearImportedListings() {
  localStorage.removeItem(STORAGE_KEY)
  window.dispatchEvent(new Event(EVENT))
}

export function subscribeImportedListings(cb: () => void) {
  const handler = () => cb()
  window.addEventListener(EVENT, handler)
  window.addEventListener('storage', handler)
  return () => {
    window.removeEventListener(EVENT, handler)
    window.removeEventListener('storage', handler)
  }
}

