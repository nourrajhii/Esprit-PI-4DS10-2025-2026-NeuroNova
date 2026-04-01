import { useCallback, useEffect, useMemo, useState } from 'react'
import { MOCK_LISTINGS } from '../data/mockListings'
import type { Listing } from '../data/mockListings'

const STORAGE_KEY = 'realstate_user_listings'
const EVENT = 'realstate-listings-updated'

export const USER_LISTING_PLACEHOLDER_IMAGE =
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80'

function readUserListings(): Listing[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as Listing[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeUserListings(listings: Listing[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(listings))
  window.dispatchEvent(new Event(EVENT))
}

export function getMergedListings(): Listing[] {
  const user = readUserListings()
  return [...MOCK_LISTINGS, ...user]
}

export function getListingById(id: string | undefined): Listing | undefined {
  if (!id) return undefined
  return getMergedListings().find((l) => l.id === id)
}

export type NewListingInput = {
  title: string
  city: string
  description: string
  price: number
  areaM2: number
  rooms: number
  type: Listing['type']
  image?: string
}

export function addUserListing(input: NewListingInput): Listing {
  const listing: Listing = {
    id: `u-${crypto.randomUUID()}`,
    title: input.title.trim(),
    city: input.city.trim(),
    description: input.description.trim(),
    price: input.price,
    currency: 'EUR',
    rooms: input.rooms,
    areaM2: input.areaM2,
    type: input.type,
    image: input.image?.trim() || USER_LISTING_PLACEHOLDER_IMAGE,
    publishedAt: new Date().toISOString().slice(0, 10),
  }
  const next = [listing, ...readUserListings()]
  writeUserListings(next)
  return listing
}

export function removeUserListing(id: string): boolean {
  if (!id.startsWith('u-')) return false
  const next = readUserListings().filter((l) => l.id !== id)
  writeUserListings(next)
  return true
}

export function useListings(): Listing[] {
  const [version, setVersion] = useState(0)
  const bump = useCallback(() => setVersion((v) => v + 1), [])

  useEffect(() => {
    window.addEventListener(EVENT, bump)
    window.addEventListener('storage', bump)
    return () => {
      window.removeEventListener(EVENT, bump)
      window.removeEventListener('storage', bump)
    }
  }, [bump])

  return useMemo(() => {
    void version
    return getMergedListings()
  }, [version])
}
