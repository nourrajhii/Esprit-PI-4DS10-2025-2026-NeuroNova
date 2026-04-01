export type Listing = {
  id: string
  title: string
  city: string
  price: number
  currency: string
  rooms: number
  areaM2: number
  type: 'apartment' | 'house' | 'studio' | 'loft'
  image: string
  description: string
  publishedAt: string
}

export const MOCK_LISTINGS: Listing[] = [
  {
    id: '1',
    title: 'Glass corner loft — harbor view',
    city: 'Marseille',
    price: 485000,
    currency: 'EUR',
    rooms: 3,
    areaM2: 92,
    type: 'loft',
    image:
      'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&q=80',
    description:
      'Double-height living, smart climate, and a private terrace. Ideal for remote work with fiber.',
    publishedAt: '2026-03-18',
  },
  {
    id: '2',
    title: 'Quiet courtyard apartment',
    city: 'Lyon',
    price: 312000,
    currency: 'EUR',
    rooms: 2,
    areaM2: 58,
    type: 'apartment',
    image:
      'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&q=80',
    description:
      'South light, oak floors, bike storage. Near metro B and fresh market.',
    publishedAt: '2026-03-22',
  },
  {
    id: '3',
    title: 'Family house with garden lab',
    city: 'Toulouse',
    price: 620000,
    currency: 'EUR',
    rooms: 5,
    areaM2: 140,
    type: 'house',
    image:
      'https://images.unsplash.com/photo-1600596542815-ffad4b1533a9?w=800&q=80',
    description:
      'PV-ready roof, rainwater recovery, insulated workshop. School district A.',
    publishedAt: '2026-03-28',
  },
  {
    id: '4',
    title: 'Micro-studio + shared roof',
    city: 'Paris',
    price: 198000,
    currency: 'EUR',
    rooms: 1,
    areaM2: 24,
    type: 'studio',
    image:
      'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800&q=80',
    description:
      'Optimized storage wall, acoustic treatment, concierge. Perfect first buy.',
    publishedAt: '2026-03-29',
  },
]
