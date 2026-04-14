import type { ListingType } from '@prisma/client'

export type PriceEstimateInput = {
  city: string
  type: string
  areaM2: number
  rooms?: number
}

export function estimatePrice(input: PriceEstimateInput): {
  estimate: number
  currency: string
  confidence: number
  assumptions: string[]
} {
  // Simple demo heuristic (replace with ML model / real data later).
  const area = Math.max(1, input.areaM2)
  const typeAdj: Record<string, number> = {
    studio: 0.92,
    apartment: 1.0,
    house: 1.22,
    loft: 1.08,
  }

  const basePerM2 = input.city.toLowerCase().includes('paris') ? 6200 : 3600
  const typeMultiplier = typeAdj[input.type] ?? 1.0

  const roomsFactor = input.rooms ? 1 + Math.min(0.12, (input.rooms - 1) * 0.03) : 1
  const raw = basePerM2 * area * typeMultiplier * roomsFactor

  const estimate = Math.round(raw / 1000) * 1000

  const completeness = (input.rooms ? 1 : 0) + 1
  const confidence = Math.round((0.55 + completeness * 0.12) * 100) / 100

  return {
    estimate,
    currency: 'EUR',
    confidence: Math.min(0.9, Math.max(0.4, confidence)),
    assumptions: [
      'Demo heuristic using city center baseline and property type multiplier.',
      'Replace with ML/market data for production.',
    ],
  }
}

