# EstateMind — Technical Architecture

## Overview

EstateMind is a multi-agent AI platform for the Tunisian real-estate market. It combines scraped listing data, machine-learning price models, RAG legal knowledge, and generative 3D visualization into a single product accessible via a Next.js web app.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT — Next.js 14                             │
│  /search  /predict  /advisor  /legal  /devis  /forecast  /villa3d       │
└──────────────┬──────────────────────────────────────────────────────────┘
               │  HTTP  (NEXT_PUBLIC_ORCHESTRATOR_URL = :8000)
               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              VIAGRA — FastAPI Orchestrator  (port 8000)                 │
│  • Intent classification (fr / ar / en)                                 │
│  • Agent fan-out (asyncio.gather)                                        │
│  • Redis cache (TTL: 1h price · 6h forecast · 12h legal · 24h geo)      │
│  • Direct MongoDB Atlas access for /listings & /dhia/invest-scan         │
│  • Gemini 2.0 Flash-Lite for market summaries                            │
└──┬───┬──────┬──────┬──────┬──────┬──────┬──────┬───────────────────────┘
   │   │      │      │      │      │      │      │
   ▼   ▼      ▼      ▼      ▼      ▼      ▼      ▼
 :8055 :8001  :8002  :8003  :8004  :8005  :8006  :8007  :8010
 dhia  advis  nour   nour2  fore   price  invest geo    life
       or     devis  legal  cast   pred   scorer adv    style
```

---

## Services

### 1. VIAGRA — Orchestrator (`:8000`)
**Tech:** FastAPI · httpx · motor (async MongoDB) · redis.asyncio  
**File:** `viagra/main.py`

The central router. Every frontend call flows through here. Responsibilities:
- **Intent detection** — regex + keyword classifier routes to the correct downstream agent(s)
- **Parallel dispatch** — `asyncio.gather()` fans out to multiple agents simultaneously
- **Redis caching** — avoids redundant ML calls; keyed by `{type}:{city|hash}`
- **MongoDB direct** — queries `dcrawl.listings` directly for `/listings` and `/dhia/invest-scan`
- **Fallbacks** — each agent call is wrapped; a timeout or error returns `null` and the orchestrator continues with partial data
- **Gemini integration** — market summaries via REST call to `generativelanguage.googleapis.com`

Key endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/chat` | POST | Main conversational entry point — routes by intent |
| `/dhia/predict` | POST | ML price prediction (dhia → fallback price-predictor) |
| `/dhia/invest` | POST | Investment scoring (dhia → fallback investment-scorer) |
| `/dhia/invest-scan` | POST | Scan MongoDB, score all listings, return BUY/HOLD/AVOID list + Gemini |
| `/listings` | GET | Paginated MongoDB listing query with validity filtering |
| `/advisor/*` | proxy | Real-estate advisor chatbot |
| `/devis/*` | proxy | Construction cost estimator |
| `/legal/*` | proxy | Legal RAG chatbot |
| `/forecast/*` | proxy | Market forecast agent |
| `/lifestyle/*` | proxy | Lifestyle matching agent |

---

### 2. Dhia Agent (`:8055`)
**Tech:** FastAPI · scikit-learn / XGBoost · Gemini API · MongoDB Atlas  
**File:** `dhia/`

Dhia's service is the ML backbone:
- **`/invoke` with `intent: "predict"`** — runs a trained regression model (price per m²) and asks Gemini to generate a structured markdown investment report
- **`/invoke` with `intent: "invest"`** — scores an investment opportunity (rental yield, appreciation, 5-year ROI) and produces a Gemini-powered action report
- **Data source:** Scrapes `ballouchi.com` / `darcom.tn` into MongoDB Atlas `dcrawl.listings`

Scoring formula (`_quick_score`):
```python
score = min(100, int(rental_yield * 600 + appreciation * 400 + surface_bonus))
verdict = "BUY" if score >= 70 else "HOLD" if score >= 50 else "AVOID"
```

---

### 3. Real-Estate Advisor (`:8001`)
**Tech:** FastAPI · Ollama (phi3:mini) · MongoDB Atlas · LangChain  
**File:** `real_estate_advisor_backend/`

- Conversational property search agent
- Retrieves matching listings from MongoDB using semantic/keyword search
- Uses Ollama `phi3:mini` for local inference (no external API cost)
- Returns `properties[]` + `natural_response` markdown

---

### 4. Nour — Devis Agent (`:8002`)
**Tech:** FastAPI · httpx · custom cost model  
**File:** `nour/Esprit-PI-4DS10-2025-2026-NeuroNova-Agent_Devis/`

- Construction cost estimator for Tunisian market
- Takes `surface_m2`, `city`, `project_type` → returns itemized devis (gros-oeuvre, second-oeuvre, finitions) in TND
- Regional coefficients for 24 Tunisian governorats
- `/invoke` adapter wraps the internal `/chat` endpoint for the VIAGRA contract

---

### 5. Nour2 — Legal Agent (`:8003`)
**Tech:** FastAPI · FAISS (in-memory) · Ollama + Gemini fallback · LangChain RAG  
**File:** `nour2/Esprit-PI-4DS10-2025-2026-NeuroNova-AgentLegal/`

- RAG chatbot for Tunisian real-estate law
- Knowledge base: COC, Code des Droits Réels, Code de l'Urbanisme, Fiscalité immobilière 2025
- **Retrieval:** FAISS vector store (sentence-transformers embeddings), top-k chunks
- **Generation:** Ollama local LLM → Gemini 2.0 Flash fallback if Ollama unavailable
- 12-hour Redis cache keyed by `legal:{hash(question)}`

---

### 6. ImmoForecast (`:8004`)
**Tech:** FastAPI · scikit-learn / Prophet  
**File:** `services/immo-forecast/`

- 12-month price trend predictions per governorat
- Trained on historical transaction data + current listings
- Returns: `pct_change_12m`, `signal` (Acheter / Attendre / Éviter), `confidence`

---

### 7. Price Predictor (`:8005`)
**Tech:** FastAPI · heuristic model  
**File:** `services/price-predictor/`

- Fallback price estimation when dhia ML is unavailable
- Per-city price/m² coefficients × surface × room-bonus
- Covers 15 Tunisian cities with empirically calibrated multipliers

---

### 8. Investment Scorer (`:8006`)
**Tech:** FastAPI · Gemini API  
**File:** `services/investment-scorer/`

- Generates full Gemini markdown investment analysis report
- Input: city, price, surface_m2 → Output: verdict, score, ROI, Gemini narrative

---

### 9. Geo Advisor (`:8007`)
**Tech:** FastAPI  
**File:** `services/geo-advisor/`

- Returns neighborhood context for a given city
- Static knowledge base of Tunisian real-estate zones, POIs, infrastructure score

---

### 10. Lifestyle Match (`:8010`)
**Tech:** FastAPI · OSM Overpass API  
**File:** `services/lifestyle-match/`

- Matches user lifestyle criteria to Tunisian zones
- Enriches zones with OpenStreetMap POI data (schools, hospitals, beaches, souks)

---

### 11. Villa3D API (`:8056`)
**Tech:** FastAPI · PyTorch · Stable Diffusion v1.5 · LoRA · Tripo3D v2 API  
**File:** `travail finale/api_service.py` + `mesh_generation_agent.py`

Four generation pipelines:

| Mode | Endpoint | Flow |
|---|---|---|
| Text → 3D | `/generate3d-text` | Prompt → Tripo3D `text_to_model` → GLB |
| Photo → 3D | `/convert3d-direct` | Image → remove_background → Tripo3D `image_to_model` v3.1 → GLB |
| Photo → 3D HD | `/convert3d-multiview` | Image → `generate_multiview_image` (4 angles) → `multiview_to_model` → GLB |
| Terrain → Villa | `/generate2d` + `/convert3d` | Terrain image → SD v1.5 + LoRA villa → clean facade → Tripo3D `image_to_model` → GLB |

**Tripo3D integration (`MeshGenerationAgent`):**
- Uploads image as `file_token`
- Polls task until `status == "success"` (5s interval, 300s timeout)
- Downloads GLB from `output.pbr_model` URL
- Returns `{ url: "/download/{filename}", filename, size_kb }` — served directly via FastAPI `FileResponse`

**SD + LoRA pipeline:**
- Base: `runwayml/stable-diffusion-v1-5` (CPU inference)
- LoRA weights: `lora-villa/pytorch_lora_weights.safetensors` (fine-tuned on villa dataset)
- `strength=0.65` preserves input structure; `guidance_scale=8.5` for sharp architecture
- Output upscaled to 1024×1024 before Tripo3D upload

---

### 12. Node.js Backend (`:4000`)
**Tech:** Express · Mongoose · JWT · Stripe · Nodemailer · Twilio  
**File:** `backend/`

Handles everything non-AI:
- **Auth:** JWT access tokens (15 min) + refresh tokens (7 days)
- **Users & subscriptions:** MongoDB `users` collection; Stripe webhooks update `subscription.plan`
- **Listings:** CRUD for user-saved listings; soft-delete
- **Notifications:** Email (Nodemailer/SMTP) + WhatsApp (Twilio)
- **File uploads:** multer → `backend/uploads/`

---

### 13. Frontend (`:3001`)
**Tech:** Next.js 14 (App Router) · React 18 · TypeScript · Tailwind CSS · Lucide icons  
**File:** `frontend/`

Key pages:

| Route | Purpose |
|---|---|
| `/` | Landing — market stats, hero |
| `/search` | Conversational property search (VIAGRA `/chat`) |
| `/predict` | Price prediction · Investment scoring · Opportunity scanner |
| `/advisor` | AI real-estate advisor chat |
| `/legal` | Legal RAG chatbot |
| `/devis` | Construction cost estimator |
| `/forecast` | Market forecast per governorat |
| `/lifestyle` | Lifestyle zone matching |
| `/villa3d` | 3D building generator (text/photo/terrain modes) |
| `/architecture` | Interactive 3D architecture explorer |
| `/annonces` | Listing browse + filter |

**GLB viewer:** `@google/model-viewer@3.4.0` web component loaded dynamically; `src` is a direct URL to `http://localhost:8056/download/{filename}` (not base64).

---

## Data Flow — Investment Scan

```
User: city=Tunis, budget=300,000 TND
         │
         ▼
VIAGRA /dhia/invest-scan
  → MongoDB query: price ∈ [180k, 420k], city~Tunis, limit 200
  → Filter: _is_valid_doc (removes scraper garbage)
  → _quick_score each listing:
       score = rental_yield*600 + appreciation*400 + surface_bonus
       verdict = BUY(≥70) / HOLD(≥50) / AVOID
  → Sort: BUY first, then score desc
  → Top-20 returned
  → Gemini Flash-Lite: 3-sentence market synthesis
         │
         ▼
Frontend: OpportunityCard grid + verdicts + Gemini summary
```

---

## Data Flow — Price Prediction

```
User: city=Sousse, surface=120m², rooms=3
         │
         ▼
VIAGRA /dhia/predict
  ├─ Try dhia :8055 /invoke (intent=predict, timeout 8s)
  │    → ML model → Gemini markdown report
  │    → Returns { ml_price, report, model }
  │
  └─ Fallback: price-predictor :8005 /invoke
       → price = BASE_M2 * city_mult * room_bonus * surface
       → Formats markdown report locally
       → Returns same shape
         │
         ▼
Frontend: MarkdownReport renders the Gemini/heuristic analysis
```

---

## Data Flow — Legal RAG

```
User: "Quels sont les droits du locataire en Tunisie?"
         │
         ▼
VIAGRA /legal/chat → nour2 :8003 /invoke
  → FAISS retrieval: top-5 chunks from COC + Code Droits Réels
  → LLM (Ollama phi3:mini OR Gemini Flash fallback)
       prompt = system_prompt + retrieved_chunks + user_question
  → Structured answer with legal citations
  → 12h Redis cache
         │
         ▼
Frontend: Legal chat interface with source references
```

---

## Infrastructure

| Component | Technology | Notes |
|---|---|---|
| Container runtime | Docker Compose | Single `docker-compose.yml` orchestrates all 13 services |
| Network | bridge `immo-net` | All agents communicate via service name DNS |
| Caching | Redis 7-alpine | Shared by VIAGRA; disabled gracefully if unreachable |
| Vector DB | FAISS (in-process) | Embedded in nour2; built once with `build_db.py` |
| Relational DB | MySQL 8 | User accounts, subscriptions (backend) |
| Document DB | MongoDB Atlas | Scraped listings (`dcrawl.listings`) — ~200k+ records |
| LLM (local) | Ollama phi3:mini | Runs on host; accessed via `host.docker.internal:11434` |
| LLM (cloud) | Gemini 2.0 Flash-Lite | Fallback + summaries; `GEMINI_API_KEY` env var |
| 3D API | Tripo3D v3.1 | `TRIPO_API_KEY` env var; model `v3.1-20260211` |

---

## Agent Communication Contract

All agents expose a `/invoke` endpoint following this contract:

```
POST /invoke
{
  "input": { ...agent-specific fields },
  "context": { "session_id": "...", "lang": "fr" }
}

→ 200 OK
{
  "output": { ...agent-specific result },
  "agent": "agent-name",
  "confidence": 0.0–1.0
}
```

VIAGRA calls agents via `call_agent(client, agent_name, payload)` which resolves the URL from `AGENT_URLS` and POSTs to `/invoke`.

---

## Security Notes

- JWT tokens signed with `JWT_SECRET` (RS256 recommended in production)
- CORS: `allow_origins=["*"]` in development — restrict to frontend domain in production
- MongoDB Atlas: IP whitelist + connection string with `tlsAllowInvalidCertificates=true` (dev only)
- Stripe webhooks verified with `STRIPE_WEBHOOK_SECRET`
- No user PII stored in Redis cache keys

---

## Development Quick-Start

```bash
# 1. Copy environment
cp .env.example .env
# Fill: DATABASE_URL, GEMINI_API_KEY, TRIPO_API_KEY, STRIPE_*, JWT_*, SMTP_*

# 2. Start all services
docker compose up --build

# 3. Or run locally (no Docker)
cd viagra && python main.py                    # port 8000
cd travail\ finale && python api_service.py   # port 8056 (SD loads in background)
cd frontend && npm run dev                     # port 3000

# 4. Build legal knowledge base (once)
cd nour2/... && python build_db.py
```

---

*Generated 2026-05-04 — EstateMind v2.0*
