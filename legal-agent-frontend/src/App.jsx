import { useMemo, useRef, useEffect, useState } from 'react'

const API_BASE_URL =
  typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL
    ? import.meta.env.VITE_API_BASE_URL
    : 'http://127.0.0.1:8000'

const API_ENDPOINT = '/chat'

/* ─── tiny SVG icons ─── */
const IconScale = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3v18M3 12h18"/><circle cx="12" cy="12" r="9"/>
  </svg>
)
const IconSend = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
)
const IconRefresh = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
)
const IconBook = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
  </svg>
)
const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
)
const IconWifi = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>
  </svg>
)

/* ─── accuracy badge color ─── */
function accuracyColor(val) {
  if (!val && val !== 0) return { bg: '#f1ebe2', text: '#9c8f7a', border: '#ddd2c3' }
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (n >= 0.8) return { bg: '#e8f5e9', text: '#2e7d32', border: '#a5d6a7' }
  if (n >= 0.5) return { bg: '#fff8e1', text: '#b68918', border: '#ffe082' }
  return { bg: '#fce4ec', text: '#c62828', border: '#ef9a9a' }
}

function formatAccuracy(val) {
  if (!val && val !== 0) return null
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (!isNaN(n)) return `${Math.round(n * 100)}%`
  return String(val)
}

/* ─── Source card — format MetricItem du backend ─── */
function SourceCard({ source, index }) {
  const [open, setOpen] = useState(false)

  // Champs MetricItem : source_label, source_icon, source_short,
  // similarity, score_emoji, score_label, article_refs, snippet
  const label     = source.source_label || source.title || source.source || `Source ${index + 1}`
  const icon      = source.source_icon  || '📄'
  const simPct    = source.similarity != null ? Math.round(source.similarity * 100) : null
  const scoreEmoji = source.score_emoji || ''
  const articles  = Array.isArray(source.article_refs) ? source.article_refs : []
  const snippet   = source.snippet || source.page_content || source.content || ''

  return (
    <div style={{
      background: '#fbf8f3',
      border: '1px solid #ddd2c3',
      borderRadius: 12,
      overflow: 'hidden',
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 14px', background: 'none', border: 'none', cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        {/* Rank badge */}
        <span style={{
          minWidth: 22, height: 22, borderRadius: 6, background: '#f6edd8',
          border: '1px solid #ddd2c3', display: 'grid', placeItems: 'center',
          fontSize: 11, fontWeight: 700, color: '#c89b1f', flexShrink: 0,
        }}>{source.rank ?? index + 1}</span>

        {/* Icon */}
        <span style={{ fontSize: 15, flexShrink: 0 }}>{icon}</span>

        {/* Label */}
        <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: '#0f1b2d', lineHeight: 1.3 }}>
          {label}
        </span>

        {/* Similarity score */}
        {simPct != null && (
          <span style={{
            fontSize: 11, fontWeight: 700, padding: '2px 8px',
            borderRadius: 99, background: '#f6edd8', color: '#b28b35',
            border: '1px solid #e8d6a3', flexShrink: 0,
          }}>
            {scoreEmoji} {simPct}%
          </span>
        )}

        <span style={{ color: '#9c8f7a', fontSize: 12, transform: open ? 'rotate(180deg)' : 'none', transition: '.2s', flexShrink: 0 }}>▼</span>
      </button>

      {open && (
        <div style={{ padding: '0 14px 14px', borderTop: '1px solid #f1ebe2' }}>
          {/* Snippet */}
          {snippet && (
            <p style={{ margin: '10px 0 0', fontSize: 13, color: '#5f6773', lineHeight: 1.65, fontStyle: 'italic' }}>
              {snippet}
            </p>
          )}

          {/* Article refs */}
          {articles.length > 0 && (
            <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {articles.map((ref, i) => (
                <span key={i} style={{
                  fontSize: 11, padding: '2px 8px', borderRadius: 99,
                  background: '#fff8e1', color: '#b68918', border: '1px solid #ffe082', fontWeight: 600,
                }}>
                  {ref}
                </span>
              ))}
            </div>
          )}

          {/* Score label + raw score */}
          {source.score_label && (
            <p style={{ margin: '8px 0 0', fontSize: 11, color: '#9c8f7a' }}>
              Pertinence : <strong style={{ color: '#0f1b2d' }}>{source.score_label}</strong>
              {source.raw_score != null && ` · score brut ${source.raw_score}`}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Message bubble ─── */
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  const meta = msg.meta || {}
  const acc = formatAccuracy(meta.accuracy ?? meta.confidence)
  const accStyle = accuracyColor(meta.accuracy ?? meta.confidence)
  const sources = meta.metrics || []

  return (
    <div style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      gap: 12,
      alignItems: 'flex-start',
      animation: 'fadeUp .35s ease both',
    }}>
      {/* Avatar */}
      <div style={{
        minWidth: 36, height: 36, borderRadius: 12,
        background: isUser ? '#c89b1f' : '#f1ebe2',
        border: `1px solid ${isUser ? '#b68918' : '#ddd2c3'}`,
        display: 'grid', placeItems: 'center',
        color: isUser ? '#fff' : '#c89b1f',
        fontSize: 14, fontWeight: 700,
        boxShadow: '0 2px 8px rgba(15,27,45,0.07)',
      }}>
        {isUser ? 'V' : <IconScale />}
      </div>

      <div style={{ flex: 1, maxWidth: '78%' }}>
        {/* Role label */}
        <div style={{
          fontSize: 11, fontWeight: 700, letterSpacing: '.08em',
          textTransform: 'uppercase', color: '#9c8f7a', marginBottom: 6,
          textAlign: isUser ? 'right' : 'left',
        }}>
          {isUser ? 'Vous' : 'Assistant juridique'}
        </div>

        {/* Bubble */}
        <div style={{
          background: isUser ? 'linear-gradient(135deg, #c89b1f, #b68918)' : '#fbf8f3',
          border: `1px solid ${isUser ? 'transparent' : '#ddd2c3'}`,
          borderRadius: isUser ? '20px 4px 20px 20px' : '4px 20px 20px 20px',
          padding: '16px 20px',
          color: isUser ? '#fff' : '#0f1b2d',
          fontSize: 15, lineHeight: 1.7,
          boxShadow: '0 4px 16px rgba(15,27,45,0.06)',
        }}>
          <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>

          {/* Meta badges row */}
          {!isUser && (acc || meta.lang || meta.question_type || meta.from_cache || meta.is_calculation || meta.hardcoded_source) && (
            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: 7, marginTop: 14,
              paddingTop: 12, borderTop: '1px solid #f1ebe2',
            }}>
              {acc && (
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 5,
                  fontSize: 12, fontWeight: 700, padding: '4px 10px', borderRadius: 99,
                  background: accStyle.bg, color: accStyle.text, border: `1px solid ${accStyle.border}`,
                }}>
                  <IconCheck /> Précision: {acc}
                </span>
              )}
              {meta.hardcoded_source && (
                <span style={{ fontSize: 12, padding: '4px 10px', borderRadius: 99, background: '#f6edd8', color: '#7a5c00', border: '1px solid #e8d6a3', fontWeight: 600 }}>
                  {meta.hardcoded_source.icon} {meta.hardcoded_source.label}
                </span>
              )}
              {meta.lang && (
                <span style={{ fontSize: 12, padding: '4px 10px', borderRadius: 99, background: '#eef2fb', color: '#3b5bdb', border: '1px solid #c5d0f5', fontWeight: 600 }}>
                  🌐 {meta.lang.toUpperCase()}
                </span>
              )}
              {meta.question_type && meta.question_type !== 'chitchat' && (
                <span style={{ fontSize: 12, padding: '4px 10px', borderRadius: 99, background: '#f3f0ff', color: '#6741d9', border: '1px solid #d0bfff', fontWeight: 600 }}>
                  📋 {meta.question_type}
                </span>
              )}
              {meta.from_cache && (
                <span style={{ fontSize: 12, padding: '4px 10px', borderRadius: 99, background: '#e8f5e9', color: '#2e7d32', border: '1px solid #a5d6a7', fontWeight: 600 }}>
                  ⚡ Cache {meta.cache_similarity != null ? `· ${Math.round(meta.cache_similarity * 100)}%` : ''}
                </span>
              )}
              {meta.is_calculation && (
                <span style={{ fontSize: 12, padding: '4px 10px', borderRadius: 99, background: '#fff8e1', color: '#b68918', border: '1px solid #ffe082', fontWeight: 600 }}>
                  🔢 Calcul
                </span>
              )}
            </div>
          )}
        </div>

        {/* Sources section — metrics FAISS */}
        {!isUser && sources.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 7,
              fontSize: 12, fontWeight: 700, color: '#9c8f7a', marginBottom: 8,
              textTransform: 'uppercase', letterSpacing: '.07em',
            }}>
              <IconBook /> {sources.length} source{sources.length > 1 ? 's' : ''} juridique{sources.length > 1 ? 's' : ''}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {sources.map((s, i) => <SourceCard key={i} source={s} index={i} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── Typing indicator ─── */
function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
      <div style={{
        minWidth: 36, height: 36, borderRadius: 12,
        background: '#f1ebe2', border: '1px solid #ddd2c3',
        display: 'grid', placeItems: 'center', color: '#c89b1f',
      }}>
        <IconScale />
      </div>
      <div style={{
        background: '#fbf8f3', border: '1px solid #ddd2c3',
        borderRadius: '4px 20px 20px 20px',
        padding: '16px 20px', display: 'flex', gap: 6, alignItems: 'center',
      }}>
        {[0, 1, 2].map(i => (
          <span key={i} style={{
            width: 7, height: 7, borderRadius: '50%', background: '#c89b1f',
            display: 'block', animation: `bounce .8s ${i * .15}s infinite ease-in-out`,
          }} />
        ))}
      </div>
    </div>
  )
}

/* ─── Main App ─── */
export default function App() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([{
    role: 'assistant',
    content: 'Bonjour 👋 Je suis votre assistant juridique immobilier tunisien. Posez-moi votre question sur le droit immobilier, les taxes, les enregistrements ou tout autre sujet juridique.',
  }])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [backendStatus, setBackendStatus] = useState(null) // null = untested
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const bottomRef = useRef(null)
  const textareaRef = useRef(null)
  const apiUrl = useMemo(() => `${API_BASE_URL}${API_ENDPOINT}`, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const testBackend = async () => {
    setBackendStatus('checking')
    try {
      const res = await fetch(`${API_BASE_URL}/health`)
      if (!res.ok) { setBackendStatus('error'); return }
      const data = await res.json()
      setBackendStatus(data?.status === 'ok' ? { ok: true, faiss: data.faiss_loaded } : 'error')
    } catch {
      setBackendStatus('offline')
    }
  }

  const sendQuestion = async (e) => {
    e?.preventDefault()
    const clean = question.trim()
    if (!clean || loading) return
    setError('')
    setLoading(true)
    setMessages(prev => [...prev, { role: 'user', content: clean }])
    setQuestion('')

    try {
      const payload = { question: clean, k: 3 }
      if (sessionId) payload.session_id = sessionId

      const res = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        let detail = `Erreur ${res.status}`
        try { const d = await res.json(); detail = d?.detail || detail } catch { const t = await res.text(); if (t) detail = t }
        throw new Error(detail)
      }

      const data = await res.json()
      if (data?.session_id) setSessionId(data.session_id)

      // Backend retourne data.metrics (liste MetricItem) + data.hardcoded_source
      const metrics = Array.isArray(data?.metrics) ? data.metrics : []
      const hardcodedSrc = data?.hardcoded_source ?? null

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data?.answer || data?.response || data?.text || 'Aucune réponse reçue.',
        meta: {
          lang: data?.lang,
          question_type: data?.question_type,
          from_cache: data?.from_cache,
          is_calculation: data?.is_calculation,
          accuracy: data?.accuracy ?? data?.confidence ?? data?.score,
          metrics,
          hardcoded_source: hardcodedSrc,
          cache_similarity: data?.cache_similarity,
          cache_date: data?.cache_date,
        },
      }])
    } catch (err) {
      const msg = err?.message || "Impossible de contacter le backend."
      setError(msg)
      setMessages(prev => [...prev, { role: 'assistant', content: `❌ ${msg}` }])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuestion() }
  }

  const reset = () => {
    setMessages([{ role: 'assistant', content: 'Nouvelle conversation démarrée. Comment puis-je vous aider ?' }])
    setSessionId(''); setQuestion(''); setError('')
  }

  const statusEl = () => {
    if (backendStatus === null) return <span style={{ color: '#9c8f7a' }}>Non testé</span>
    if (backendStatus === 'checking') return <span style={{ color: '#b68918' }}>⏳ Vérification…</span>
    if (backendStatus === 'offline' || backendStatus === 'error') return <span style={{ color: '#c62828' }}>⚠️ Inaccessible</span>
    return <span style={{ color: '#2e7d32' }}>✅ OK {backendStatus.faiss ? '· FAISS chargé' : '· FAISS absent'}</span>
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,600&family=DM+Sans:wght@400;500;600&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
          --bg: #f6f2eb; --surface: #fbf8f3; --surface2: #f1ebe2;
          --border: #ddd2c3; --primary: #c89b1f; --primary-dark: #b68918;
          --primary-soft: #f6edd8; --text: #0f1b2d; --soft: #5f6773; --muted: #9c8f7a;
          --shadow: 0 8px 28px rgba(15,27,45,0.08);
        }
        html, body, #root { height: 100%; background: var(--bg); font-family: 'DM Sans', sans-serif; color: var(--text); }
        @keyframes fadeUp { from { opacity:0; transform:translateY(10px) } to { opacity:1; transform:translateY(0) } }
        @keyframes bounce { 0%,80%,100%{transform:scale(.6)} 40%{transform:scale(1)} }
        textarea:focus { outline: none; border-color: var(--primary) !important; box-shadow: 0 0 0 3px rgba(200,155,31,.15) !important; }
        ::-webkit-scrollbar { width: 6px } ::-webkit-scrollbar-track { background: transparent }
        ::-webkit-scrollbar-thumb { background: #ddd2c3; border-radius: 99px }
      `}</style>

      <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

        {/* ── Sidebar ── */}
        <aside style={{
          width: sidebarOpen ? 270 : 0,
          minWidth: sidebarOpen ? 270 : 0,
          overflow: 'hidden',
          transition: 'width .3s ease, min-width .3s ease',
          background: 'var(--surface)',
          borderRight: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column',
          height: '100vh',
        }}>
          <div style={{ padding: '24px 20px 20px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 12, background: 'var(--primary-soft)',
                border: '1px solid var(--border)', display: 'grid', placeItems: 'center',
                color: 'var(--primary)', boxShadow: 'var(--shadow)',
              }}>
                <IconScale />
              </div>
              <div>
                <div style={{ fontFamily: "'Playfair Display', serif", fontWeight: 700, fontSize: 17, lineHeight: 1.1 }}>Legal Agent</div>
                <div style={{ fontSize: 11, color: 'var(--muted)', letterSpacing: '.05em' }}>Droit immobilier TN</div>
              </div>
            </div>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '18px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>


        

            {/* Session card */}
            <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 14, padding: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.08em', color: 'var(--muted)', marginBottom: 6 }}>Session</div>
              <code style={{ fontSize: 11, color: 'var(--soft)', display: 'block', wordBreak: 'break-all', marginBottom: 10 }}>
                {sessionId || 'Aucune session active'}
              </code>
              <button onClick={reset} style={{
                width: '100%', padding: '8px 0', borderRadius: 10,
                border: '1px solid var(--border)', background: 'var(--surface)',
                color: 'var(--text)', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                transition: '.2s',
              }}
                onMouseEnter={e => e.currentTarget.style.background = '#f1ebe2'}
                onMouseLeave={e => e.currentTarget.style.background = 'var(--surface)'}
              >
                <IconRefresh /> Nouvelle conversation
              </button>
            </div>

          
          </div>
        </aside>

        {/* ── Main ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {/* Top bar */}
          <header style={{
            background: 'rgba(251,248,243,.94)', backdropFilter: 'blur(12px)',
            borderBottom: '1px solid var(--border)', padding: '14px 24px',
            display: 'flex', alignItems: 'center', gap: 14, flexShrink: 0,
          }}>
            <button onClick={() => setSidebarOpen(o => !o)} style={{
              width: 38, height: 38, borderRadius: 10, border: '1px solid var(--border)',
              background: 'var(--surface)', cursor: 'pointer', display: 'grid', placeItems: 'center',
              color: 'var(--soft)', fontSize: 16, transition: '.2s',
            }}
              title="Sidebar"
            >☰</button>
            <div>
              <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 700, lineHeight: 1.1 }}>
                Assistant <em style={{ color: 'var(--primary)', fontStyle: 'italic' }}>juridique</em> immobilier
              </h1>
              <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Droit immobilier tunisien</p>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <button onClick={reset} style={{
                padding: '8px 16px', borderRadius: 10, border: '1px solid var(--border)',
                background: 'var(--surface)', color: 'var(--text)', fontSize: 13, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                transition: '.2s',
              }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--surface2)'}
                onMouseLeave={e => e.currentTarget.style.background = 'var(--surface)'}
              >
                <IconRefresh /> Réinitialiser
              </button>
            </div>
          </header>

          {/* Chat area */}
          <div style={{
            flex: 1, overflowY: 'auto', padding: '28px 28px 12px',
            display: 'flex', flexDirection: 'column', gap: 24,
          }}>
            {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>

          {/* Composer */}
          <div style={{
            padding: '16px 24px 24px',
            background: 'rgba(251,248,243,.96)', backdropFilter: 'blur(12px)',
            borderTop: '1px solid var(--border)',
          }}>
            {error && (
              <div style={{
                marginBottom: 10, padding: '10px 14px', borderRadius: 10,
                background: '#fce4ec', border: '1px solid #ef9a9a', color: '#c62828', fontSize: 13,
              }}>⚠️ {error}</div>
            )}
            <div style={{
              display: 'flex', gap: 12, alignItems: 'flex-end',
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderRadius: 18, padding: '12px 12px 12px 18px',
              boxShadow: '0 4px 20px rgba(15,27,45,.07)',
              transition: 'border-color .2s, box-shadow .2s',
            }}>
              <textarea
                ref={textareaRef}
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Posez votre question juridique… (Entrée pour envoyer, Shift+Entrée pour retour à la ligne)"
                rows={3}
                style={{
                  flex: 1, border: 'none', background: 'transparent', resize: 'none',
                  fontSize: 15, color: 'var(--text)', lineHeight: 1.6, fontFamily: 'inherit',
                  maxHeight: 160, minHeight: 60,
                }}
              />
              <button
                onClick={sendQuestion}
                disabled={loading || !question.trim()}
                style={{
                  width: 44, height: 44, borderRadius: 13, border: 'none',
                  background: loading || !question.trim() ? '#e8d6a3' : 'var(--primary)',
                  color: loading || !question.trim() ? '#b28b35' : '#fff',
                  display: 'grid', placeItems: 'center', cursor: loading || !question.trim() ? 'not-allowed' : 'pointer',
                  transition: '.2s', boxShadow: !loading && question.trim() ? '0 4px 14px rgba(200,155,31,.35)' : 'none',
                  flexShrink: 0,
                }}
                onMouseEnter={e => { if (!loading && question.trim()) e.currentTarget.style.background = 'var(--primary-dark)' }}
                onMouseLeave={e => { if (!loading && question.trim()) e.currentTarget.style.background = 'var(--primary)' }}
              >
                <IconSend />
              </button>
            </div>
            <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 8, textAlign: 'center' }}>
              Entrée pour envoyer · Shift+Entrée pour saut de ligne · Les réponses sont à titre informatif uniquement
            </p>
          </div>
        </div>
      </div>
    </>
  )
}