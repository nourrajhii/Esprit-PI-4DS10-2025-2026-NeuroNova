# EstateMind — AI Real Estate Platform

Tunisian real-estate investment platform powered by multi-agent AI.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Next.js Frontend  (port 3000)                      │
│  frontend/                                          │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │  VIAGRA Orchestrator    │  port 8000
        │  viagra/main.py         │
        │  Routes all AI calls    │
        └──┬──────────┬───────────┘
           │          │
   ┌───────▼──┐  ┌────▼──────────┐
   │ Dhia ML  │  │ Villa3D API   │  port 8056
   │ dhia/    │  │ travail finale│
   │ Predict  │  │ SD+LoRA+Tripo │
   └──────────┘  └───────────────┘
```

## Quick Start (Local)

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB Atlas connection string (in `.env`)
- Tripo3D API key (in `.env`)

### 1. Clone & configure
```bash
git clone https://github.com/nourrajhii/Esprit-PI-4DS10-2025-2026-NeuroNova.git -b estate-mind/deploy
cd Esprit-PI-4DS10-2025-2026-NeuroNova
cp .env.example .env
# Edit .env with your keys
```

### 2. Install dependencies
```bash
# Frontend
cd frontend && npm install && cd ..

# VIAGRA orchestrator
cd viagra && pip install -r requirements.txt && cd ..

# Villa3D API
cd "travail finale" && pip install -r requirements.txt && cd ..
```

### 3. LoRA model weights (Villa3D only)
The LoRA weights (`travail finale/lora-villa/`) are **not in git** (3.3 GB).
Contact the team or download from shared storage, then place at:
```
travail finale/lora-villa/pytorch_lora_weights.safetensors
```
Villa3D works without LoRA — the Text→3D and Photo→3D modes use Tripo3D directly.

### 4. Start all services
**Windows:** double-click `start-dev.bat`

Or manually in 3 terminals:
```bash
cd viagra && python main.py
cd "travail finale" && python api_service.py
cd frontend && npm run dev
```

Open http://localhost:3000

## Docker Deployment

```bash
cp .env.example .env   # configure secrets
docker-compose up -d
```

| Service | Port | Container |
|---------|------|-----------|
| Frontend (Next.js) | 3000 | frontend |
| VIAGRA Orchestrator | 8000 | viagra |
| Villa3D API | 8056 | villa3d |
| Backend API | 5000 | backend |

## Branch Structure

| Branch | Contents | Use |
|--------|----------|-----|
| `estate-mind/deploy` | Full platform | **Deploy from here** |
| `estate-mind/frontend` | Next.js app only | Frontend work |
| `estate-mind/ai-agents` | Python AI services | AI/ML work |
| `main` | Team integration | Merge point |

## Environment Variables

See `.env.example` for all required variables:
- `MONGODB_URI` — MongoDB Atlas connection
- `TRIPO_API_KEY` — Tripo3D API key (3D generation)
- `GEMINI_API_KEY` — Google Gemini (investment analysis)
- `STRIPE_SECRET_KEY` — Stripe payments
- `JWT_SECRET` — Auth token signing

## Project Structure

```
Estate Mind/
├── frontend/          # Next.js 14 app (Tailwind, map, 3D viewer)
├── viagra/            # VIAGRA AI orchestrator (FastAPI, port 8000)
├── travail finale/    # Villa3D API (SD v1.5 + LoRA + Tripo3D, port 8056)
├── dhia/              # ML price prediction pipeline
├── backend/           # Node.js REST API (MongoDB, auth, Stripe)
├── services/          # AI microservices (price, geo, investment...)
├── nour/              # Agent Devis (construction quotes)
├── Oumeima/           # ImmoMatch agent
├── docker-compose.yml # Full-stack Docker deployment
├── .env.example       # Environment variable template
└── start-dev.bat      # Windows one-click dev launcher
```
