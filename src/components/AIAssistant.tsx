import { useState, useRef, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  HardHat,
  MessageCircle,
  Scale,
  Send,
  Sparkles,
  TrendingUp,
  X,
} from 'lucide-react'

type Msg = { id: string; role: 'user' | 'assistant'; text: string }

function replyTo(input: string): string {
  const q = input.toLowerCase()
  if (/price|cost|€|eur|budget/.test(q))
    return 'For budget fit, filter by city and sort by price. Typical ranges in our demo data: studios from ~€198k, lofts to ~€485k. Connect a pricing API later for live comparables.'
  if (/3d|three|visual|view/.test(q))
    return 'The 3D block uses React Three Fiber: orbit controls, PBR materials, and environment lighting. Swap the sketch for your GLTF floor plans or Matterport embed.'
  if (/account|login|sign|register/.test(q))
    return 'Accounts here are a front-end demo (localStorage). Wire this to your backend (OAuth2, magic link, or email/password) and replace the mock token.'
  if (/invest|roi|yield/.test(q))
    return 'Investor mode can layer cap-rate estimates, occupancy, and risk tags. Plug in your spreadsheet model or BI API for real numbers.'
  if (/post|publish|listing|announce/.test(q))
    return 'Signed-in users can open Publish to draft a listing. Persist posts to your API and add image upload + moderation before production.'
  if (/map|carte|marker|geo/.test(q))
    return 'Open Map to see listings pinned by city using a static coordinate lookup. Replace with geocoding or exact lat/lng from your database for production.'
  return 'I am REAL’s assistant shell. Ask about 3D previews, accounts, publishing, budgets, or investor workflows — or connect an LLM API to this panel.'
}

export function AIAssistant() {
  type AssistantKind = 'legal' | 'advisor' | 'developer'
  const [open, setOpen] = useState(false)
  const [kind, setKind] = useState<AssistantKind>('advisor')
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: '0',
      role: 'assistant',
      text: 'Hi — choose an assistant and ask your question.',
    },
  ])
  const [draft, setDraft] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  function detectTunisiaLegal(q: string) {
    const s = q.toLowerCase()
    return /tunisie|tunis|jurid|immobilier|immobiliere|loi|code|bail|vente|agence/.test(s)
  }

  function scenarioFromText(q: string): 'sale' | 'lease' | 'agency' | 'developer' {
    const s = q.toLowerCase()
    if (/bail|rent|loyer|lease|locat/.test(s)) return 'lease'
    if (/agence|commission|mandat|intermediaire|intermed/.test(s)) return 'agency'
    if (/developer|promoteur|fund|fonds|develop/.test(s)) return 'developer'
    return 'sale'
  }

  async function send() {
    const text = draft.trim()
    if (!text) return

    const assistantId = crypto.randomUUID()
    const userMsg: Msg = { id: crypto.randomUUID(), role: 'user', text }
    setMessages((m) => [
      ...m,
      userMsg,
      { id: assistantId, role: 'assistant', text: 'Thinking…' },
    ])
    setDraft('')

    try {
      let next = replyTo(text)

      if (kind === 'legal' || detectTunisiaLegal(text)) {
        const scenario = scenarioFromText(text)
        const r = await fetch('http://localhost:4000/ai/legal-assistant', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            jurisdiction: 'Tunisia',
            scenario,
            question: text,
          }),
        })

        if (r.ok) {
          const data = (await r.json()) as {
            answer: string
            disclaimer: string
          }
          next = `${data.answer}\n\n${data.disclaimer}`
        } else {
          next = 'Legal assistant is available, but the backend returned an error.'
        }
      } else if (kind === 'advisor') {
        next =
          'Investor advisor (demo):\n' +
          '- Tell me: city, budget, and target (rental yield vs capital gain).\n' +
          '- I can propose a shortlist strategy (filters + due diligence checklist) and the KPIs to track.\n\n' +
          'Ask: “I have 300k€ in Tunis, I want rental yield” or “I want a flip in Sousse”.'
      } else if (kind === 'developer') {
        next =
          'Developer assistant (demo):\n' +
          '- I can help you structure listings for projects (units, stages, documents, availability).\n' +
          '- I can suggest what to automate (3D pipeline, approvals, lead routing, CRM sync).\n\n' +
          'Ask: “How to publish 50 units quickly?” or “What data fields should we require for a new project?”'
      }

      setMessages((m) => m.map((msg) => (msg.id === assistantId ? { ...msg, text: next } : msg)))
    } catch {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === assistantId
            ? { ...msg, text: 'Network error. Please try again.' }
            : msg,
        ),
      )
    }
  }

  return (
    <>
      <motion.button
        type="button"
        className="ai-fab"
        onClick={() => setOpen(true)}
        aria-label="Open assistant"
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.98 }}
        style={{ display: open ? 'none' : 'flex' }}
      >
        <Sparkles size={20} />
        Assistant
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.aside
            className="ai-panel"
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 380, damping: 28 }}
            role="dialog"
            aria-label="AI assistant"
          >
            <div className="ai-panel__head">
              <div className="ai-panel__title">
                {kind === 'legal' ? (
                  <Scale size={20} aria-hidden />
                ) : kind === 'advisor' ? (
                  <TrendingUp size={20} aria-hidden />
                ) : (
                  <HardHat size={20} aria-hidden />
                )}
                <span>
                  {kind === 'legal'
                    ? 'Legal assistant'
                    : kind === 'advisor'
                      ? 'Investor advisor'
                      : 'Developer assistant'}
                </span>
              </div>
              <button
                type="button"
                className="icon-btn"
                onClick={() => setOpen(false)}
                aria-label="Close assistant"
              >
                <X size={20} />
              </button>
            </div>
            <div className="ai-panel__switch">
              <button
                type="button"
                className={`ai-chip${kind === 'legal' ? ' ai-chip--active' : ''}`}
                onClick={() => setKind('legal')}
              >
                <Scale size={16} /> Juridique
              </button>
              <button
                type="button"
                className={`ai-chip${kind === 'advisor' ? ' ai-chip--active' : ''}`}
                onClick={() => setKind('advisor')}
              >
                <TrendingUp size={16} /> Conseiller
              </button>
              <button
                type="button"
                className={`ai-chip${kind === 'developer' ? ' ai-chip--active' : ''}`}
                onClick={() => setKind('developer')}
              >
                <HardHat size={16} /> Dev
              </button>
            </div>
            <div className="ai-panel__messages">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`ai-msg ai-msg--${m.role}`}
                >
                  {m.role === 'assistant' && <MessageCircle size={14} className="ai-msg__ico" />}
                  <p>{m.text}</p>
                </div>
              ))}
              <div ref={endRef} />
            </div>
            <form
              className="ai-panel__form"
              onSubmit={(e) => {
                e.preventDefault()
                send()
              }}
            >
              <input
                type="text"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Ask about listings, 3D, or accounts…"
                autoComplete="off"
                aria-label="Message"
              />
              <button type="submit" className="btn btn--primary ai-panel__send" aria-label="Send">
                <Send size={18} />
              </button>
            </form>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  )
}
