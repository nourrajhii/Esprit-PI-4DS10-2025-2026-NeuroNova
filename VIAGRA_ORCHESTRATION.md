# EstateMind — VIAGRA Orchestration Architecture

> **VIAGRA** = **V**irtual **I**ntelligent **A**gent for **G**uided **R**eal-estate **A**dvisor  
> Port: `8000` — Container: `immo-viagra` — Source: `viagra/main.py`

---

## What is VIAGRA?

VIAGRA is the **central orchestrator** of the EstateMind multi-agent AI platform.  
Every user request — whether from the chat interface, the search bar, the listing detail page, or any of the specialized agent pages — flows through VIAGRA first.

VIAGRA's job is to:
1. **Understand** the user's intent and language
2. **Dispatch** the request to the right combination of specialized agents (in parallel)
3. **Cache** expensive results (prices, forecasts, legal responses) in Redis
4. **Synthesize** all agent responses into a single coherent reply
5. **Return** a unified JSON response to the frontend

---

## Architecture Overview

```
Browser / Mobile
      │
      ▼
  Next.js Frontend (port 3001)
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                  VIAGRA Orchestrator (port 8000)         │
│                                                         │
│  1. classify_intent(message)  ──► intent label          │
│  2. detect_language(message)  ──► ar | fr | en          │
│  3. Parallel agent dispatch   ──► asyncio.gather(...)   │
│  4. Redis cache lookup/write  ──► 1h-24h TTL            │
│  5. MongoDB direct query      ──► listings collection   │
│  6. Response synthesis        ──► unified JSON          │
└─────────────────────────────────────────────────────────┘
      │                    │                │
      ▼                    ▼                ▼
  Agent Services        Redis (cache)   MongoDB Atlas
  (ports 8001–8056)    (port 6379)     (dcrawl.listings)
```

---

## Agent Roster

| Agent | Container | Port | Role | Cache TTL |
|-------|-----------|------|------|-----------|
| **Recommender** | `immo-advisor-backend` | 8001 | Personalized property recommendations via Ollama LLM + RAG | — |
| **Devis** | `immo-nour-devis` | 8002 | Construction & renovation cost estimation (Tunisian market) | — |
| **Legal** | `immo-nour2-legal` | 8003 | Tunisian real estate law — contracts, disputes, regulations | 12h |
| **Forecast** | `immo-forecast` | 8004 | Market price forecasts (Prophet/ARIMA) per governorate | 6h |
| **Price Predictor** | `immo-price-predictor` | 8005 | ML price prediction per listing (delegates to dhia) | 1h |
| **Investment Scorer** | `immo-investment-scorer` | 8006 | BUY/HOLD/AVOID verdict + ROI estimate (Gemini AI + rules) | 1h |
| **Geo Advisor** | `immo-geo-advisor` | 8007 | Neighborhood quality score (schools, transport, amenities) | 24h |
| **Lifestyle Match** | `immo-lifestyle-match` | 8010 | Lifestyle profile matching per governorate/city | 24h |
| **DHIA (ML)** | `immo-dhia` | 8055 | Web scraper + ML training pipeline (Mubawab, Menzili) | — |
| **Villa 3D** | `immo-villa3d` | 8056 | Stable Diffusion + LoRA → Tripo3D 3D model generation | — |

---

## Request Lifecycle — Step by Step

### 1. Entry Point: `POST /chat`

```json
{
  "message": "Appartement 3 pièces à Sousse sous 300 000 TND",
  "session_id": "uuid-optional",
  "context": {}
}
```

### 2. Intent Classification (`classify_intent`)

VIAGRA reads keyword patterns from the message and assigns one of these intents:

| Intent | Trigger Keywords | Agents Activated |
|--------|-----------------|------------------|
| `devis` | "devis", "coût travaux", "construction", "rénovation" | Devis (8002) |
| `legal` | "contrat", "loi", "juridique", "permis", "litige", "هيكل" | Legal (8003) |
| `forecast` | "prévision", "évolution", "investir", "rentabilité", "توقع" | Forecast (8004) + Investment (8006) |
| `listing_analysis` | property ID detected in message | Price (8005) + Geo (8007) + Investment (8006) |
| `search` | *(default)* | Recommender (8001) + Price (8005) + Geo (8007) + Forecast (8004) |

### 3. Language Detection (`detect_language`)

Scans for Arabic Unicode ranges and French/English keywords.  
The detected language (`ar`, `fr`, `en`) is passed to every agent and used for response formatting.

### 4. Parallel Agent Dispatch (`asyncio.gather`)

VIAGRA calls all required agents **simultaneously** using `httpx.AsyncClient`:

```python
results = await asyncio.gather(
    call_agent(RECOMMENDER_URL + "/invoke", payload),
    call_agent(PRICE_URL      + "/invoke", payload),
    call_agent(GEO_URL        + "/invoke", payload),
    call_agent(FORECAST_URL   + "/invoke", payload),
    return_exceptions=True,
)
```

Failed agents return `None` and are skipped — the platform **never fails completely** due to a single agent being down.

### 5. Redis Caching

Before calling expensive agents, VIAGRA checks Redis:

```
Key pattern:  "{agent}:{hash(input_params)}"
Example:      "price:abc123def456"
```

Cache TTLs:
- Prices: **1 hour** (market moves slowly within a day)
- Forecasts: **6 hours** (model outputs are stable)
- Geo scores: **24 hours** (neighborhood data rarely changes)
- Legal answers: **12 hours** (law is stable)

### 6. MongoDB Direct Access

For listing search, VIAGRA queries MongoDB **directly** (bypassing the backend for speed):

```python
db = motor.AsyncIOMotorClient(DATABASE_URL)["dcrawl"]
listings = await db.listings.find(query_filter).limit(20).to_list(20)
```

This avoids an extra HTTP hop for the most frequent operation.

### 7. Response Synthesis

VIAGRA merges all agent responses into one structured object:

```json
{
  "summary": "Trouvé 5 biens à Sousse correspondant à votre budget...",
  "agents_used": ["recommender", "price-predictor", "geo-advisor", "forecast"],
  "data": {
    "listings": { "properties": [...], "total_found": 5 },
    "price": { "predicted_price_tnd": 285000, "confidence": 0.82 },
    "geo": { "overall_score": 74, "transport": 80, "schools": 68 },
    "forecast": { "pct_change_12m": 3.2, "trend": "hausse" }
  },
  "follow_up_questions": ["Quels quartiers?", "Voir les prévisions?"],
  "lang": "fr",
  "intent": "search"
}
```

---

## Agent Communication Protocol

All agents expose a standard `/invoke` endpoint:

### Request
```json
POST /invoke
{
  "input": {
    "query": "...",
    "city": "Sousse",
    "budget": 300000,
    "lang": "fr"
  },
  "context": {
    "session_id": "uuid",
    "intent": "search"
  }
}
```

### Response
```json
{
  "output": { ... },
  "agent": "price-predictor",
  "confidence": 0.85,
  "cached": false
}
```

---

## VIAGRA API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Main orchestrator — classifies intent, dispatches agents |
| `POST` | `/search` | Alias for `/chat` |
| `GET`  | `/listing/{id}` | Detail view — price + geo + investment for one property |
| `GET`  | `/forecast/{governorate}` | Market forecast for a governorate |
| `GET`  | `/listings` | Direct DB query: `?city=Sousse&min_price=100000&max_price=400000` |
| `GET`  | `/market/summary` | Aggregated national stats (count, avg price, price/m²) |
| `GET`  | `/health` | Agent status probe — pings all agents |
| `GET`  | `/advisor/...` | Proxy to Recommender agent (8001) |
| `GET`  | `/devis/...` | Proxy to Devis agent (8002) |
| `GET`  | `/legal/...` | Proxy to Legal agent (8003) |
| `GET`  | `/lifestyle/...` | Proxy to Lifestyle agent (8010) |

---

## Villa 3D Agent — Separate Pipeline

The Villa 3D agent (`villa3d`, port 8056) operates **independently** from VIAGRA — it is called directly by the frontend since its jobs are long-running (1–5 minutes) and do not fit the synchronous chat pattern.

### Pipeline A — SD+LoRA → Tripo3D (Terrain to 3D)

```
User uploads terrain image + optional prompt
          │
          ▼
POST /generate2d (villa3d:8056)
          │
          ▼
Stable Diffusion v1.5 + LoRA fine-tuned weights
(lora-villa/pytorch_lora_weights.safetensors)
     strength=0.78, steps=40, guidance=7.5
          │
          ▼ Villa 2D rendered image (512→1024px)
          │
POST /convert3d (villa3d:8056)
          │
          ▼
Tripo3D API — image_to_model
     model: v3.1-20260211
     texture: true, pbr: true
     texture_quality: detailed
     face_limit: 200 000
          │
          ▼
GLB file (base64) → model-viewer renders in browser
```

### Pipeline B — Direct Image → 3D

```
User uploads building photo
          │
POST /convert3d-direct → Tripo3D image_to_model → GLB
```

### Pipeline C — Multiview HD

```
User uploads building photo
          │
POST /convert3d-multiview
          │
Tripo3D generate_multiview_image (4 angles)
          │
Tripo3D multiview_to_model → best geometry GLB
```

### Pipeline D — Text → 3D

```
User types description
          │
POST /generate3d-text → Tripo3D text_to_model → GLB
```

---

## Infrastructure Services

| Service | Role | Port |
|---------|------|------|
| **Redis** | Result cache (TTL 1–24h), session state | 6379 |
| **MongoDB Atlas** | Listings DB (dcrawl.listings, 5 500+ records) | Cloud |
| **MySQL** | Advisor recommendation history | 3306 |
| **ChromaDB** | Vector embeddings for semantic search | 8008 |
| **Ollama** | Local LLM (llama3.2) for advisor + legal agents | 11434 |

---

## Deployment (MLOps)

### Start the full stack

```bash
# Copy env vars
cp .env.example .env
# Edit .env with your MongoDB URI, API keys, etc.

# Start all services
docker compose up -d

# Check status
docker compose ps
docker compose logs -f viagra
```

### Scale individual agents

```bash
# Run 3 instances of the price predictor
docker compose up -d --scale price-predictor=3
```

### Health monitoring

```bash
# VIAGRA reports all agent statuses
curl http://localhost:8000/health
```

### GPU for Villa 3D (optional)

To enable GPU acceleration for Stable Diffusion:

```bash
# Rebuild with CUDA support
docker compose build villa3d --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu121
docker compose up -d villa3d
```

---

## Key Design Decisions

| Decision | Reason |
|----------|--------|
| Parallel agent dispatch via `asyncio.gather` | Minimizes latency — all agents run simultaneously |
| Redis caching with per-agent TTLs | Expensive ML/LLM calls are amortized across users |
| MongoDB direct access in VIAGRA | Avoids an extra HTTP hop for the most common operation |
| Graceful degradation (exceptions=True) | Platform stays alive even if 3–4 agents are down |
| Villa 3D as independent service | Long-running jobs (3–5 min) can't block the chat API |
| Tripo3D v3.1-20260211 as default | Latest model with best geometry + PBR texture quality |
| SD+LoRA fine-tuned on Tunisian villas | Generic SD produces generic buildings — LoRA anchors to local architecture style |
