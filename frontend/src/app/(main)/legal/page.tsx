'use client'
import { useState, useRef, useEffect } from 'react'
import { Scale, Send, RotateCcw, Bot, User, BookOpen } from 'lucide-react'

const BASE = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8000'

interface MetricItem {
  rank: number
  source: string
  source_label: string
  source_short: string
  source_icon: string
  nlp_combined: number
  similarity: number
  snippet: string
}

interface LegalResponse {
  answer: string
  question_type?: string
  lang?: string
  is_calculation?: boolean
  from_cache?: boolean
  session_id?: string
  hardcoded_source?: { icon?: string; label?: string; title?: string; law?: string }
  metrics?: MetricItem[]
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  meta?: {
    question_type?: string
    lang?: string
    from_cache?: boolean
    is_calculation?: boolean
    hardcoded_source?: LegalResponse['hardcoded_source']
    metrics?: MetricItem[]
  }
}

const QUICK_PROMPTS = [
  "Quel est le rôle du notaire dans une transaction immobilière?",
  "Comment fonctionne l'hypothèque en droit tunisien?",
  "Quelles taxes s'appliquent à la vente d'un bien immobilier?",
  "Procédure pour obtenir un permis de construire",
  "ما هو دور كاتب العدل في البيع العقاري؟",
  "ما هي الضرائب المطبقة على بيع العقار في تونس؟",
]

const TYPE_LABELS: Record<string, string> = {
  fiscal:       'Fiscal',
  documents:    'Documents',
  expulsion:    'Expulsion',
  bailleur:     'Bail',
  plus_value:   'Plus-value',
  legalite_bien:'Légalité',
  chitchat:     'Conversation',
  rag:          'Droit',
  coc:          'COC',
  droits_reels: 'Droits réels',
  urbanisme:    'Urbanisme',
  general:      'Général',
}

export default function LegalPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sessionId, setSessionId] = useState<string | undefined>(undefined)
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
      const res = await fetch(`${BASE}/legal/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text, session_id: sessionId, k: 3 }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: LegalResponse = await res.json()
      if (data.session_id && !sessionId) setSessionId(data.session_id)
      const answer = data.answer?.trim()
      if (!answer) {
        setError("L'agent juridique n'a pas retourné de réponse. Vérifiez qu'Ollama tourne ou que GEMINI_API_KEY est configuré.")
        setMessages(prev => prev.slice(0, -1))
        return
      }
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: answer,
        meta: {
          question_type: data.question_type,
          lang: data.lang,
          from_cache: data.from_cache,
          is_calculation: data.is_calculation,
          hardcoded_source: data.hardcoded_source,
          metrics: data.metrics,
        },
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
    setMessages([]); setError(''); setPrompt(''); setSessionId(undefined)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Scale className="w-6 h-6 text-brand-600" />
            Assistant Juridique Immobilier
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Droit immobilier tunisien — COC, Droits Réels, Fiscalité 2025
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={reset}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Nouvelle session
          </button>
        )}
      </div>

      {/* Main chat */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">

        {/* Messages area */}
        <div className="min-h-[400px] max-h-[560px] overflow-y-auto p-4 space-y-4">

          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-72 gap-6">
              <div className="w-16 h-16 rounded-2xl bg-brand-100 flex items-center justify-center">
                <BookOpen className="w-8 h-8 text-brand-600" />
              </div>
              <div className="text-center">
                <p className="font-semibold text-slate-700">Posez votre question juridique</p>
                <p className="text-slate-400 text-sm mt-1">
                  Droits réels, contrats, fiscalité, permis de construire…
                </p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center max-w-xl">
                {QUICK_PROMPTS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => send(q)}
                    dir={/[؀-ۿ]/.test(q) ? 'rtl' : 'ltr'}
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
              <div className="max-w-[82%] space-y-1.5">
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-brand-600 text-white rounded-tr-sm'
                    : 'bg-slate-100 text-slate-800 rounded-tl-sm'
                }`} dir={msg.meta?.lang === 'ar' ? 'rtl' : 'ltr'}>
                  {msg.content}
                </div>

                {/* Meta badges */}
                {msg.meta && msg.role === 'assistant' && (
                  <div className="flex flex-wrap gap-1.5 px-1">
                    {msg.meta.question_type && msg.meta.question_type !== 'chitchat' && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-600 border border-brand-100">
                        {TYPE_LABELS[msg.meta.question_type] ?? msg.meta.question_type}
                      </span>
                    )}
                    {msg.meta.from_cache && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                        cache
                      </span>
                    )}
                    {msg.meta.is_calculation && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 border border-amber-100">
                        calcul
                      </span>
                    )}
                    {msg.meta.hardcoded_source && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                        {msg.meta.hardcoded_source.icon} {msg.meta.hardcoded_source.label ?? msg.meta.hardcoded_source.title ?? ''}
                      </span>
                    )}
                    {msg.meta.metrics && msg.meta.metrics.length > 0 && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-100">
                        📚 {msg.meta.metrics.length} source{msg.meta.metrics.length > 1 ? 's' : ''}
                        {' · '}{(msg.meta.metrics[0].nlp_combined * 100).toFixed(0)}% pertinent
                      </span>
                    )}
                    {msg.meta.lang === 'ar' && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-100">
                        عربي
                      </span>
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
              placeholder="Ex: Quels sont les droits d'un locataire en cas d'expulsion?"
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

      {/* Disclaimer */}
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-sm">
        <p className="font-semibold text-amber-800 mb-1">Avertissement légal</p>
        <p className="text-amber-700">
          Les informations fournies sont à titre indicatif et basées sur le droit immobilier tunisien
          (COC, Code des Droits Réels, Fiscalité 2025). Elles ne constituent pas un avis juridique.
          Consultez un notaire ou avocat pour toute décision importante.
        </p>
      </div>
    </div>
  )
}
