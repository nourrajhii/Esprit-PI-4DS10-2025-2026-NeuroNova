/** Approximate city centers (Tunisia) for map markers — extend as you add regions. */
export const CITY_COORDS: Record<string, [number, number]> = {
  Tunis: [36.8065, 10.1815],
  Ariana: [36.8625, 10.1956],
  'Ben Arous': [36.7435, 10.231],
  Manouba: [36.8078, 10.1011],
  Soukra: [36.87, 10.27],
  'La Soukra': [36.87, 10.27],
  Chotrana: [36.9, 10.15],
  'Chotrana 1': [36.9, 10.15],
  'Chotrana 2': [36.9, 10.15],
  'Chotrana 3': [36.9, 10.15],
  Sfax: [34.7406, 10.7603],
  Sousse: [35.8256, 10.6369],
  Nabeul: [36.4561, 10.7376],
  Hammamet: [36.4, 10.6167],
  Bizerte: [37.2746, 9.8739],
  Gabes: [33.8815, 10.0982],
  Gafsa: [34.425, 8.7842],
  Kairouan: [35.6781, 10.0963],
  Monastir: [35.7643, 10.8113],
  Mahdia: [35.5047, 11.0622],
  Jendouba: [36.5011, 8.78],
  Beja: [36.7256, 9.1817],
  Kef: [36.1742, 8.7049],
  Tozeur: [33.9197, 8.1335],
  Medenine: [33.3549, 10.5055],
  Tataouine: [32.9297, 10.4518],
  Djerba: [33.8076, 10.8451],
  Zarzis: [33.5031, 11.1102],
}

/** Fallback — center of Tunisia */
export const DEFAULT_COORDS: [number, number] = [34.0, 9.0]

export function coordsForCity(city: string): [number, number] {
  const normalized = city.trim().toLowerCase()
  const key = Object.keys(CITY_COORDS).find((k) => {
    const kk = k.toLowerCase()
    return kk === normalized || normalized.includes(kk) || kk.includes(normalized)
  })
  if (key) return CITY_COORDS[key]
  return DEFAULT_COORDS
}
