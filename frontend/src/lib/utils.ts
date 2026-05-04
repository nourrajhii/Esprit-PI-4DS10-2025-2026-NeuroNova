import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatTND(amount: number | undefined | null): string {
  if (amount == null) return 'N/A'
  return new Intl.NumberFormat('fr-TN', { style: 'currency', currency: 'TND', maximumFractionDigits: 0 }).format(amount)
}

export function formatM2(surface: number | undefined | null): string {
  if (surface == null) return 'N/A'
  return `${surface.toLocaleString('fr-TN')} m²`
}

export const GOVERNORATS = [
  'Tunis','Ariana','Ben Arous','Manouba','Nabeul','Zaghouan','Bizerte',
  'Béja','Jendouba','Kef','Siliana','Sousse','Monastir','Mahdia',
  'Sfax','Kairouan','Kasserine','Sidi Bouzid','Gabès','Médenine',
  'Tataouine','Gafsa','Tozeur','Kébili',
]

export const TUNISIA_CENTER: [number, number] = [33.8869, 9.5375]

export const GOVERNORAT_COORDS: Record<string, [number, number]> = {
  'Tunis':      [36.8190, 10.1658],
  'Ariana':     [36.8665, 10.1647],
  'Sousse':     [35.8245, 10.6346],
  'Sfax':       [34.7406, 10.7603],
  'Nabeul':     [36.4561, 10.7376],
  'Monastir':   [35.7778, 10.8262],
  'Bizerte':    [37.2746, 9.8739],
  'Hammamet':   [36.3998, 10.6166],
  'Gabès':      [33.8814, 10.0982],
  'Kairouan':   [35.6781, 10.0965],
  'Médenine':   [33.3549, 10.5055],
  'Gafsa':      [34.4211, 8.7757],
}
