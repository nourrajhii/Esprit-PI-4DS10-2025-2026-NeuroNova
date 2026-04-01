import { useState, useRef, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Bot, MessageCircle, Send, Sparkles, X } from 'lucide-react'

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
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: '0',
      role: 'assistant',
      text: 'Hi — I help you navigate listings, 3D previews, and publishing. What are you looking for?',
    },
  ])
  const [draft, setDraft] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  function send() {
    const text = draft.trim()
    if (!text) return
    const userMsg: Msg = { id: crypto.randomUUID(), role: 'user', text }
    setMessages((m) => [...m, userMsg])
    setDraft('')
    setTimeout(() => {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: replyTo(text),
        },
      ])
    }, 320)
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
                <Bot size={20} aria-hidden />
                <span>REAL assistant</span>
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
