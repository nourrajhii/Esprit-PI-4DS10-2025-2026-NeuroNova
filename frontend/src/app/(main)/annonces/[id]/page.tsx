'use client'
import { useState, useEffect, Suspense } from 'react'
import { useParams } from 'next/navigation'
import Image from 'next/image'
import { getBackendListing, sendContact, BackendListing } from '@/lib/api'
import { formatTND, formatM2 } from '@/lib/utils'
import {
  Loader2, MapPin, BedDouble, Ruler, Phone, Building2,
  ChevronLeft, ChevronRight, Send, CheckCircle,
} from 'lucide-react'

function ImageGallery({ images, title }: { images: string[]; title: string }) {
  const [idx, setIdx] = useState(0)

  if (!images.length) {
    return (
      <div className="h-64 bg-gradient-to-br from-primary-50 to-primary-100 rounded-2xl flex items-center justify-center">
        <span className="text-6xl">🏠</span>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="relative h-72 rounded-2xl overflow-hidden bg-slate-100">
        <Image src={images[idx]} alt={`${title} — photo ${idx + 1}`} fill className="object-cover" unoptimized />
        {images.length > 1 && (
          <>
            <button
              onClick={() => setIdx(i => (i - 1 + images.length) % images.length)}
              className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/40 text-white rounded-full p-1.5 hover:bg-black/60 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIdx(i => (i + 1) % images.length)}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/40 text-white rounded-full p-1.5 hover:bg-black/60 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <span className="absolute bottom-2 right-3 text-xs bg-black/50 text-white px-2 py-0.5 rounded-full">
              {idx + 1} / {images.length}
            </span>
          </>
        )}
      </div>
      {images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {images.map((src, i) => (
            <button
              key={i}
              onClick={() => setIdx(i)}
              className={`relative w-16 h-12 shrink-0 rounded-lg overflow-hidden border-2 transition-colors ${i === idx ? 'border-primary' : 'border-transparent'}`}
            >
              <Image src={src} alt={`thumb ${i + 1}`} fill className="object-cover" unoptimized />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function AnnonceContent() {
  const { id } = useParams<{ id: string }>()
  const [listing, setListing]   = useState<BackendListing | null>(null)
  const [loading, setLoading]   = useState(true)
  const [message, setMessage]   = useState('')
  const [phone,   setPhone]     = useState('')
  const [sending, setSending]   = useState(false)
  const [sent,    setSent]      = useState(false)
  const [error,   setError]     = useState('')

  useEffect(() => {
    setLoading(true)
    getBackendListing(id)
      .then(setListing)
      .catch(() => setListing(null))
      .finally(() => setLoading(false))
  }, [id])

  async function handleContact(e: React.FormEvent) {
    e.preventDefault()
    if (!message.trim()) return
    setSending(true)
    setError('')
    try {
      await sendContact(id, message, phone || undefined)
      setSent(true)
      setMessage('')
      setPhone('')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erreur envoi du message')
    } finally {
      setSending(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="w-8 h-8 text-primary animate-spin" />
      <span className="ml-3 text-slate-500">Chargement de l'annonce...</span>
    </div>
  )

  if (!listing) return (
    <div className="text-center py-20 text-slate-400">
      <Building2 className="w-16 h-16 mx-auto mb-4 opacity-30" />
      <p className="text-lg font-medium">Annonce introuvable</p>
      <p className="text-sm mt-2">Cette annonce n'existe plus ou a été supprimée.</p>
    </div>
  )

  const statusLabel: Record<string, string> = {
    active:  'Disponible',
    pending: 'En attente',
    sold:    'Vendu',
    rented:  'Loué',
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-6">
          <div className="flex flex-col lg:flex-row gap-6">
            <div className="lg:w-1/2">
              <ImageGallery images={listing.images} title={listing.title} />
            </div>

            <div className="lg:w-1/2 space-y-4">
              <div>
                <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
                  <MapPin className="w-4 h-4" />{listing.city}
                  <span className={`ml-2 text-xs px-2 py-0.5 rounded-full font-medium ${
                    listing.type === 'vente' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
                  }`}>
                    {listing.type === 'vente' ? 'À vendre' : 'À louer'}
                  </span>
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                    {statusLabel[listing.status] ?? listing.status}
                  </span>
                </div>
                <h1 className="text-xl font-bold text-slate-800 leading-snug">{listing.title}</h1>
              </div>

              <p className="text-3xl font-bold" style={{ color: 'var(--color-secondary)' }}>
                {formatTND(listing.price)}
              </p>

              <div className="flex flex-wrap gap-4 text-sm text-slate-600">
                {listing.surface != null && listing.surface > 0 && (
                  <span className="flex items-center gap-1.5">
                    <Ruler className="w-4 h-4 text-slate-400" />{formatM2(listing.surface)}
                  </span>
                )}
                {listing.rooms != null && listing.rooms > 0 && (
                  <span className="flex items-center gap-1.5">
                    <BedDouble className="w-4 h-4 text-slate-400" />{listing.rooms} ch.
                  </span>
                )}
                {listing.address && (
                  <span className="flex items-center gap-1.5">
                    <MapPin className="w-4 h-4 text-slate-400" />{listing.address}
                  </span>
                )}
              </div>

              {listing.owner?.phone && (
                <a href={`tel:${listing.owner.phone}`}
                  className="flex items-center gap-1.5 text-xs bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-lg hover:bg-emerald-100 transition-colors w-fit">
                  <Phone className="w-3.5 h-3.5" />{listing.owner.phone}
                </a>
              )}

              {listing.description && (
                <p className="text-sm text-slate-600 border-t border-slate-100 pt-3">
                  {listing.description}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Contact form */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">Contacter le vendeur</h2>

        {sent ? (
          <div className="flex items-center gap-3 text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-xl p-4">
            <CheckCircle className="w-5 h-5 shrink-0" />
            <p className="text-sm font-medium">Votre message a été envoyé au vendeur avec succès.</p>
          </div>
        ) : (
          <form onSubmit={handleContact} className="space-y-4">
            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">{error}</p>
            )}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Message *</label>
              <textarea
                value={message}
                onChange={e => setMessage(e.target.value)}
                rows={4}
                required
                placeholder="Bonjour, je suis intéressé(e) par cette annonce. Pourriez-vous me donner plus d'informations ?"
                className="w-full border border-slate-300 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Téléphone (optionnel)</label>
              <input
                type="tel"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                placeholder="+216 XX XXX XXX"
                className="w-full border border-slate-300 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <button
              type="submit"
              disabled={sending || !message.trim()}
              className="flex items-center gap-2 px-6 py-3 bg-primary text-white font-medium rounded-xl hover:bg-primary-600 transition-colors disabled:opacity-50"
            >
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Envoyer le message
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

export default function AnnoncePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    }>
      <AnnonceContent />
    </Suspense>
  )
}
