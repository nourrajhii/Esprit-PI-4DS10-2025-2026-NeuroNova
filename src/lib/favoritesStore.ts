import { useCallback, useEffect, useMemo, useState } from 'react'

const STORAGE_KEY = 'realstate_favorites'
const EVENT = 'realstate-favorites-updated'

function readIds(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as string[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeIds(ids: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids))
  window.dispatchEvent(new Event(EVENT))
}

export function toggleFavoriteId(id: string) {
  const cur = readIds()
  const has = cur.includes(id)
  const next = has ? cur.filter((x) => x !== id) : [...cur, id]
  writeIds(next)
  return !has
}

export function useFavorites() {
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

  const ids = useMemo(() => {
    void version
    return readIds()
  }, [version])

  const has = useCallback(
    (id: string) => ids.includes(id),
    [ids],
  )

  const toggle = useCallback((id: string) => {
    toggleFavoriteId(id)
  }, [])

  return { favoriteIds: ids, has, toggle, count: ids.length }
}
