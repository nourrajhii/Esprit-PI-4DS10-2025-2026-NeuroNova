'use client'
import { useState, useRef, useEffect } from 'react'
import SubscriptionGuard from '@/components/SubscriptionGuard'
import { Calculator, Send, RotateCcw, Bot, User, HardHat, ChevronDown, ChevronUp } from 'lucide-react'

const BASE = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8000'

interface DevisItem {
  designation: string
  quantite?: number
  unite?: string
  prix_unitaire?: number
  total?: number
}

interface DevisResponse {
  texte: string
  devis?: {
    total_estime?: number
    items?: DevisItem[]
    surface_m2?: number
    projet?: string
    note?: string
  }
  session_id?: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  devis?: DevisResponse['devis']
}

const QUICK_PROMPTS = [
  "J'ai un terrain de 200m², je veux 3 chambres, cuisine et salle de bain",
  "Devis pour rénovation d'un appartement 100m² à Tunis",
  "Estimation construction villa 300m² avec piscine",
  "Prix matériaux pour une cuisine équipée 15m²",
]

function DevisContent() {
  const [messages, setMessages] = useState<Message[]>([])
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sessionId] = useState(() => `devis-${Date.now()}`)
  const [expandedDevis, setExpandedDevis] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send(text: string) {
    if (!text.trim() || loading) return
    setError('')
    setPrompt('')
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/devis/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: DevisResponse = await res.json()
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.texte || "Devis généré.",
        devis: data.devis,
      }])
    } catch (e: unknown) {
      setError('Erreur de connexion. ' + (e instanceof Error ? e.message : ''))
    } finally {
      setLoading(false)
      textareaRef.current?.focus()
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(prompt) }
  }

  function reset() {
    setMessages([]); setError(''); setPrompt('')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Calculator className="w-6 h-6 text-brand-600" />
            Agent Devis Construction
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Estimez le coût de votre projet immobilier en Tunisie
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={reset}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Nouveau devis
          </button>
        )}
      </div>

      {/* Main chat */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">

        {/* Messages area */}
        <div className="min-h-[400px] max-h-[520px] overflow-y-auto p-4 space-y-4">

          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-72 gap-6">
              <div className="w-16 h-16 rounded-2xl bg-brand-100 flex items-center justify-center">
                <HardHat className="w-8 h-8 text-brand-600" />
              </div>
              <div className="text-center">
                <p className="font-semibold text-slate-700">Décrivez votre projet de construction</p>
                <p className="text-slate-400 text-sm mt-1">Surface, nombre de pièces, type de finition…</p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center max-w-xl">
                {QUICK_PROMPTS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => send(q)}
                    className="text-xs px-3 py-1.5 rounded-full bg-brand-50 text-brand-700 border border-brand-100 hover:bg-brand-100 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-brand-600" />
                </div>
              )}
              <div className={`max-w-[80%] space-y-2`}>
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-brand-600 text-white rounded-tr-sm'
                    : 'bg-slate-100 text-slate-800 rounded-tl-sm'
                }`}>
                  {msg.content}
                </div>

                {/* Devis breakdown */}
                {msg.devis && (
                  <div className="bg-white border border-brand-200 rounded-xl overflow-hidden shadow-sm">
                    <button
                      onClick={() => setExpandedDevis(expandedDevis === i ? null : i)}
                      className="w-full flex items-center justify-between px-4 py-3 bg-brand-50 hover:bg-brand-100 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <Calculator className="w-4 h-4 text-brand-600" />
                        <span className="font-semibold text-brand-700 text-sm">
                          Devis estimatif
                          {msg.devis.surface_m2 ? ` — ${msg.devis.surface_m2}m²` : ''}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        {msg.devis.total_estime != null && (
                          <span className="font-bold text-brand-700">
                            {msg.devis.total_estime.toLocaleString('fr-TN')} TND
                          </span>
                        )}
                        {expandedDevis === i
                          ? <ChevronUp className="w-4 h-4 text-brand-500" />
                          : <ChevronDown className="w-4 h-4 text-brand-500" />
                        }
                      </div>
                    </button>

                    {expandedDevis === i && msg.devis.items && msg.devis.items.length > 0 && (
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-slate-200 bg-slate-50">
                              <th className="text-left px-4 py-2 text-slate-500 font-medium">Désignation</th>
                              <th className="text-right px-4 py-2 text-slate-500 font-medium">Qté</th>
                              <th className="text-right px-4 py-2 text-slate-500 font-medium">Unité</th>
                              <th className="text-right px-4 py-2 text-slate-500 font-medium">P.U (TND)</th>
                              <th className="text-right px-4 py-2 text-slate-500 font-medium">Total</th>
                            </tr>
                          </thead>
                          <tbody>
                            {msg.devis.items.map((item, j) => (
                              <tr key={j} className="border-b border-slate-100 hover:bg-slate-50">
                                <td className="px-4 py-2 text-slate-700">{item.designation}</td>
                                <td className="px-4 py-2 text-right text-slate-600">{item.quantite ?? '—'}</td>
                                <td className="px-4 py-2 text-right text-slate-600">{item.unite ?? '—'}</td>
                                <td className="px-4 py-2 text-right text-slate-600">
                                  {item.prix_unitaire != null ? item.prix_unitaire.toLocaleString('fr-TN') : '—'}
                                </td>
                                <td className="px-4 py-2 text-right font-medium text-slate-800">
                                  {item.total != null ? item.total.toLocaleString('fr-TN') : '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                          {msg.devis.total_estime != null && (
                            <tfoot>
                              <tr className="bg-brand-50 border-t border-brand-200">
                                <td colSpan={4} className="px-4 py-2 font-bold text-brand-700">Total estimé</td>
                                <td className="px-4 py-2 text-right font-bold text-brand-700">
                                  {msg.devis.total_estime.toLocaleString('fr-TN')} TND
                                </td>
                              </tr>
                            </tfoot>
                          )}
                        </table>
                        {msg.devis.note && (
                          <p className="px-4 py-2 text-xs text-slate-400 italic border-t border-slate-100">
                            {msg.devis.note}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 mt-1">
                  <User className="w-4 h-4 text-slate-600" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-brand-600" />
              </div>
              <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-slate-100">
                <div className="flex gap-1">
                  {[0, 1, 2].map(j => (
                    <div key={j} className="w-2 h-2 rounded-full bg-slate-400 animate-bounce"
                      style={{ animationDelay: `${j * 150}ms` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Error */}
        {error && (
          <div className="mx-4 mb-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Input */}
        <div className="border-t border-slate-200 p-4 bg-slate-50">
          <div className="flex gap-3 items-end">
            <textarea
              ref={textareaRef}
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ex: J'ai un terrain de 200m², je veux 3 chambres…"
              rows={2}
              className="flex-1 resize-none rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent"
              disabled={loading}
            />
            <button
              onClick={() => send(prompt)}
              disabled={loading || !prompt.trim()}
              className="flex items-center gap-2 px-4 py-3 bg-brand-600 text-white rounded-xl hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium text-sm"
            >
              <Send className="w-4 h-4" />
              Envoyer
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-2">Entrée pour envoyer · Maj+Entrée pour nouvelle ligne</p>
        </div>
      </div>

      {/* Info box */}
      <div className="bg-brand-50 border border-brand-100 rounded-2xl p-4 text-sm text-brand-800">
        <p className="font-semibold mb-1">À propos de cet agent</p>
        <p className="text-brand-700">
          Cet agent utilise une base de données de prix de matériaux tunisiens 2025 et un modèle RAG
          pour générer des estimations de coûts de construction ou rénovation. Les prix sont indicatifs
          et peuvent varier selon la région et les prestataires.
        </p>
      </div>
    </div>
  )
}

export default function DevisPage() {
  return <SubscriptionGuard><DevisContent /></SubscriptionGuard>
}
