/**
 * Central place for future backend calls. Replace base URL via Vite env.
 */
const base = import.meta.env.VITE_API_BASE_URL ?? ''

export async function healthCheck(): Promise<{ ok: boolean }> {
  if (!base) return { ok: false }
  try {
    const r = await fetch(`${base.replace(/\/$/, '')}/health`, {
      signal: AbortSignal.timeout(5000),
    })
    return { ok: r.ok }
  } catch {
    return { ok: false }
  }
}

export const api = {
  baseUrl: base,
  healthCheck,
}
