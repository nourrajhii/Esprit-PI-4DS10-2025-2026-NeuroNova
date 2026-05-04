import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function sendChat(message, sessionId) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Erreur serveur: ${res.status}`);
  return res.json();
}

async function searchMaterials(query, n_results = 5) {
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, n_results }),
  });
  if (!res.ok) throw new Error(`Erreur serveur: ${res.status}`);
  return res.json();
}

async function resetSession(sessionId) {
  const res = await fetch(`${API_BASE}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  return res.json();
}

// Strip markdown table + trailing summary lines when structured devis exists
function cleanAgentText(text, hasDevis) {
  if (!hasDevis || !text) return text;
  const lines = text.split("\n");
  const tableStart = lines.findIndex(l => /^\s*\|/.test(l));
  if (tableStart === -1) return text;
  const before = lines.slice(0, tableStart).join("\n").trimEnd();
  return before || null;
}

function TypingIndicator() {
  return (
    <div className="message agent">
      <div className="avatar">🏗️</div>
      <div className="bubble typing">
        <span /><span /><span />
      </div>
    </div>
  );
}

function DevisCard({ devis }) {
  if (!devis) return null;

  const postesRaw = devis.postes || {};
  const postesArr = Array.isArray(postesRaw)
    ? postesRaw
    : Object.entries(postesRaw).map(([key, val]) => ({
        key,
        titre: val.description || key,
        quantite: val.quantite,
        unite: val.unite || "",
        cout_min: val.cout_min ?? 0,
        cout_mid: val.cout_mid ?? 0,
        cout_max: val.cout_max ?? 0,
      }));

  if (postesArr.length === 0) return null;

  const total = devis.total || {};
  const resume = devis.resume || {};
  const nbEtages = devis._nombre_etages || 1;

  const fmt = (v) => {
    if (v == null) return "—";
    return Number(v).toLocaleString("fr-TN");
  };

  return (
    <div className="devis-card">
      <div className="devis-header">
        <span className="devis-icon">📋</span>
        <span>Devis Estimatif — Tunisie 2025</span>
        {resume.surface_habitable && (
          <span className="badge">🏗️ {resume.surface_habitable}</span>
        )}
        {nbEtages > 1 && (
          <span className="badge">🏢 {nbEtages} niveaux</span>
        )}
      </div>

      {Object.keys(resume).length > 0 && (
        <div className="devis-resume">
          {resume.terrain && <span>📐 Terrain : <b>{resume.terrain}</b></span>}
          {nbEtages > 1 && resume.emprise_sol && <span>⬜ Emprise/sol : <b>{resume.emprise_sol}</b></span>}
          {nbEtages > 1 && <span>🏢 Niveaux : <b>{nbEtages}</b></span>}
          {nbEtages > 1 && resume.surface_plancher && (
            <span>📏 Surface plancher totale : <b>{resume.surface_plancher}</b></span>
          )}
          {nbEtages > 1 && resume.surface_par_etage && (
            <span>🏠 Surface/niveau : <b>{resume.surface_par_etage}</b></span>
          )}
          {nbEtages === 1 && resume.surface_habitable && (
            <span>🏠 Surface : <b>{resume.surface_habitable}</b></span>
          )}
          {resume.surface_jardin && resume.surface_jardin !== "0 m²" && <span>🌿 Jardin : <b>{resume.surface_jardin}</b></span>}
          {resume.surface_allee && resume.surface_allee !== "0 m²" && <span>🚗 Parking/accès : <b>{resume.surface_allee}</b></span>}
        </div>
      )}

      <div className="devis-table-wrapper">
        <table className="devis-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Poste de travaux</th>
              <th>Qté</th>
              <th className="right">MIN (DT)</th>
              <th className="right">MOY (DT)</th>
              <th className="right">MAX (DT)</th>
            </tr>
          </thead>
          <tbody>
            {postesArr.map((p, i) => (
              <tr key={i}>
                <td className="center dim">{i + 1}</td>
                <td>{p.titre}</td>
                <td className="center">{p.quantite != null ? `${p.quantite} ${p.unite}`.trim() : "—"}</td>
                <td className="right">{fmt(p.cout_min)}</td>
                <td className="right bold">{fmt(p.cout_mid)}</td>
                <td className="right accent">{fmt(p.cout_max)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3} className="total-label">💰 TOTAL ESTIMÉ <small>(imprévus 10% inclus)</small></td>
              <td className="right bold">{fmt(total.total_min)}</td>
              <td className="right bold accent">{fmt(total.total_mid)}</td>
              <td className="right bold">{fmt(total.total_max)}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="devis-range">
        <span>Fourchette : <b>{total.total_min_str || "—"}</b> → <b>{total.total_max_str || "—"}</b></span>
        <span className="recommended">⭐ Recommandé : <b>{total.total_mid_str || "—"}</b></span>
      </div>
    </div>
  );
}

function Message({ msg }) {
  const isAgent = msg.role === "agent";
  const cleanedText = isAgent ? cleanAgentText(msg.text, !!msg.devis) : msg.text;
  return (
    <div className={`message ${msg.role}`}>
      <div className="avatar">{isAgent ? "🏗️" : "👤"}</div>
      <div className="msg-content">
        {cleanedText && (
          <div className="bubble markdown-body">
            <ReactMarkdown
              components={{
                table: ({ node, ...props }) => (
                  <div className="md-table-wrapper">
                    <table {...props} />
                  </div>
                ),
              }}
            >
              {cleanedText}
            </ReactMarkdown>
          </div>
        )}
        {isAgent && msg.devis && <DevisCard devis={msg.devis} />}
      </div>
    </div>
  );
}

function SearchPanel({ onClose }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchMaterials(query, 8);
      setResults(data.results || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>🔍 Recherche Matériaux</h3>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>
      <div className="search-bar">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSearch()}
          placeholder="Ex: carrelage salle de bain, ciment, peinture…"
        />
        <button onClick={handleSearch} disabled={loading}>
          {loading ? "…" : "Chercher"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="results-list">
        {results.map((r, i) => (
          <div key={i} className="result-item">
            <div className="result-title">{r.metadata?.title || r.document}</div>
            <div className="result-meta">
              <span className="tag">{r.metadata?.category}</span>
              <span className="price">{r.metadata?.price_display || `${r.metadata?.price} DT/${r.metadata?.unit}`}</span>
              <span className="score">Score: {(r.relevance_score * 100).toFixed(0)}%</span>
            </div>
          </div>
        ))}
        {results.length === 0 && !loading && query && (
          <p className="empty">Aucun résultat trouvé.</p>
        )}
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  "J'ai un terrain de 200m², je veux construire une maison avec 3 chambres",
  "Estimer le coût de carrelage pour une salle de bain de 8m²",
  "Je veux rénover ma cuisine de 12m², peinture et carrelage",
  "Coût de construction d'un villa de 4 pièces à Tunis",
];

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "agent",
      text: "Bonjour ! Je suis votre assistant devis construction pour la Tunisie 🇹🇳\n\nDécrivez votre projet (surface, pièces, type de travaux) et je vous fournirai une estimation basée sur les prix du marché 2025.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [sessionId] = useState(() => `sess_${Date.now()}`);
  const [apiStatus, setApiStatus] = useState("checking");
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(r => r.json())
      .then(d => setApiStatus(d.status === "ok" ? "online" : "initializing"))
      .catch(() => setApiStatus("offline"));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", text: msg }]);
    setLoading(true);
    try {
      const data = await sendChat(msg, sessionId);
      setMessages(prev => [...prev, {
        role: "agent",
        text: data.texte,
        devis: data.devis,
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: "agent",
        text: `❌ Erreur: ${e.message}. Vérifiez que l'API FastAPI est lancée sur le port 8000.`,
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleReset = async () => {
    await resetSession(sessionId);
    setMessages([{
      role: "agent",
      text: "Conversation réinitialisée. Décrivez votre nouveau projet 🏗️",
    }]);
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="logo">
          <span className="logo-icon">🏗️</span>
          <div>
            <div className="logo-title">DevisAI</div>
            <div className="logo-sub">Construction Tunisie</div>
          </div>
        </div>

        <div className={`api-status ${apiStatus}`}>
          <span className="dot" />
          {apiStatus === "online" ? "API connectée"
            : apiStatus === "initializing" ? "En démarrage…"
            : "API hors ligne"}
        </div>

        <nav className="sidebar-nav">
          <button className={`nav-btn ${!showSearch ? "active" : ""}`} onClick={() => setShowSearch(false)}>
            💬 Chat Devis
          </button>
          <button className={`nav-btn ${showSearch ? "active" : ""}`} onClick={() => setShowSearch(true)}>
            🔍 Recherche Prix
          </button>
          <button className="nav-btn danger" onClick={handleReset}>
            🔄 Nouvelle conversation
          </button>
        </nav>

        <div className="sidebar-footer">
          <p className="footer-note">Prix du marché tunisien 2025</p>
          <p className="footer-note">FastAPI + ChromaDB + RAG</p>
        </div>
      </aside>

      <main className="main">
        {showSearch ? (
          <SearchPanel onClose={() => setShowSearch(false)} />
        ) : (
          <>
            <div className="chat-area">
              {messages.map((msg, i) => (
                <Message key={i} msg={msg} />
              ))}
              {loading && <TypingIndicator />}
              <div ref={bottomRef} />
            </div>

            {messages.length === 1 && (
              <div className="suggestions">
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} className="suggestion-chip" onClick={() => handleSend(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}

            <div className="input-bar">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Décrivez votre projet de construction… (Entrée pour envoyer)"
                rows={2}
                disabled={loading}
              />
              <button
                className="send-btn"
                onClick={() => handleSend()}
                disabled={loading || !input.trim()}
              >
                {loading ? "⏳" : "Envoyer ➤"}
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}