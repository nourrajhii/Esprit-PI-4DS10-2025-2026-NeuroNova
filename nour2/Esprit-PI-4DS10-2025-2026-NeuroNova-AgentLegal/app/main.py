"""
app/main.py — Point d'entrée FastAPI

CORRECTIFS :
- Appel à init_db() au startup (charge FAISS UNE SEULE FOIS en mémoire)
- Appel à get_llm() au startup (initialise OllamaLLM UNE SEULE FOIS)
- La première requête ne subira plus de latence de chargement
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.admin import router as admin_router
from app.services.vector_store import init_db, get_db
from app.services.cache import cache_stats
from app.models.response import HealthResponse

app = FastAPI(
    title="Assistant Juridique Immobilier Tunisien",
    description=(
        "API RAG pour le droit immobilier tunisien — "
        "COC, Code des Droits Réels, Urbanisme, Fiscalité 2025"
    ),
    version="2.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(admin_router)


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    db = get_db()
    stats = cache_stats()
    return HealthResponse(
        status="ok",
        faiss_loaded=db is not None,
        cache_entries=stats["total"],
    )


# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    print("[Legal] Demarrage de l'API juridique tunisienne...")

    # 1. Charger FAISS en mémoire une seule fois
    db = init_db()
    if db:
        print("[Legal] Base FAISS prete")
    else:
        print("[Legal] Base FAISS absente — lancez build_db.py d'abord")

    # 2. Pré-initialiser le LLM (évite la latence à la première requête)
    try:
        from app.services.llm import get_llm
        get_llm()
        print("[Legal] LLM Ollama pret")
    except Exception as e:
        print(f"[Legal] LLM non disponible au demarrage: {e}")
        print("[Legal] Gemini sera utilise comme fallback si GEMINI_API_KEY est defini.")