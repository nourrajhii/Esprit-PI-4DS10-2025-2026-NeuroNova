/** Approximate city centers (France) for map markers — extend as you add regions. */
export const CITY_COORDS: Record<string, [number, number]> = {
  Marseille: [43.2965, 5.3698],
  Lyon: [45.764, 4.8357],
  Toulouse: [43.6047, 1.4442],
  Paris: [48.8566, 2.3522],
  Bordeaux: [44.8378, -0.5792],
  Nice: [43.7102, 7.262],
  Nantes: [47.2184, -1.5536],
  Strasbourg: [48.5734, 7.7521],
  Lille: [50.6292, 3.0573],
}

/** Fallback — center of metropolitan France */
export const DEFAULT_COORDS: [number, number] = [46.603354, 1.888334]

export function coordsForCity(city: string): [number, number] {
  const key = Object.keys(CITY_COORDS).find(
    (k) => k.toLowerCase() === city.trim().toLowerCase(),
  )
  if (key) return CITY_COORDS[key]
  return DEFAULT_COORDS
}
