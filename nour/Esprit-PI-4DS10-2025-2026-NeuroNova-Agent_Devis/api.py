"""
Agent RAG Construction — API FastAPI
Lancer : uvicorn api:app --host 127.0.0.1 --port 8000
Tester  : http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from src.data_loader import load_dataset
from src.vector_store import MaterialVectorStore
from src.rag_retriever import RAGRetriever
from src.devis_calculator import DevisCalculator
from src.agent import ConstructionAgent

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Agent RAG — Devis Construction Tunisie",
    description="API de devis automatique basée sur les prix du marché tunisien 2025",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Schémas Pydantic ─────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

    class Config:
        json_schema_extra = {
            "example": {
                "message": "J'ai un terrain de 600m², je veux 4 chambres, une cuisine et une salle de bain avec jardin",
                "session_id": "user_001"
            }
        }

class ChatResponse(BaseModel):
    texte: str
    devis: Optional[dict] = None
    session_id: str

class SearchRequest(BaseModel):
    query: str
    n_results: Optional[int] = 5
    category: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "query": "carrelage salle de bain prix m²",
                "n_results": 5
            }
        }

class ResetRequest(BaseModel):
    session_id: Optional[str] = "default"

# ─── État global ──────────────────────────────────────────────────────────────
agents: dict = {}
retriever: RAGRetriever = None
calculator: DevisCalculator = None
is_ready = False

# ─── MODÈLE À UTILISER ────────────────────────────────────────────────────────
# Choisir selon votre RAM disponible :
# "tinyllama"    → 637 MB  — fonctionne avec 1.5 GB RAM  ✅ recommandé
# "qwen2.5:0.5b" → 1.1 GB  — un peu meilleur
# "llama3.2:1b"  → 1.8 GB  — bon en français
# "mistral"      → 4.1 GB  — nécessite 4+ GB RAM
OLLAMA_MODEL = "llama3.2:1b"

# ─── Démarrage ────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    global retriever, calculator, is_ready

    print("=" * 60)
    print("[START] Demarrage de l'Agent RAG Construction...")
    print(f"   Modele LLM : {OLLAMA_MODEL}")
    print("=" * 60)

    print("\n[LOAD] Chargement du dataset...")
    df = load_dataset("data/materiaux_cleaned.xlsx")

    print("\n[DB] Initialisation ChromaDB...")
    vector_store = MaterialVectorStore(persist_dir="./chroma_db")
    vector_store.index_dataset(df)

    retriever = RAGRetriever(vector_store)
    calculator = DevisCalculator()
    calculator.load_dataset("data/materiaux_cleaned.xlsx")

    print("\n[ML] Initialisation du modele ML de prediction...")
    calculator.setup_predictor(
        history_path="data/historique_devis.csv",  # optionnel, ignore si absent
        blend_alpha=0.35
    )

    is_ready = True
    print(f"\n[OK] API prete sur http://127.0.0.1:8000")
    print(f"[DOCS] Swagger UI : http://127.0.0.1:8000/docs")
    print("=" * 60)


def get_or_create_agent(session_id: str) -> ConstructionAgent:
    if session_id not in agents:
        agents[session_id] = ConstructionAgent(
            retriever=retriever,
            calculator=calculator,
            model=OLLAMA_MODEL
        )
    return agents[session_id]


# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.get("/", tags=["Statut"])
def root():
    return {
        "status": "online",
        "ready": is_ready,
        "model": OLLAMA_MODEL,
        "endpoints": {
            "POST /chat":   "Envoyer un message → obtenir un devis",
            "POST /search": "Recherche dans le dataset",
            "POST /reset":  "Réinitialiser une conversation",
            "GET  /health": "Statut de l'API",
            "GET  /docs":   "Documentation Swagger interactive"
        }
    }


@app.get("/health", tags=["Statut"])
def health():
    return {
        "status": "ok" if is_ready else "initializing",
        "model": OLLAMA_MODEL,
        "sessions_actives": len(agents)
    }


@app.post("/chat", response_model=ChatResponse, tags=["Agent"])
def chat(request: ChatRequest):
    """
    **Envoyer un message à l'agent de devis.**

    L'agent analyse votre demande, recherche les prix dans le dataset,
    calcule les surfaces et retourne un devis estimatif.

    **Exemple de message :**
    > "J'ai un terrain de 600m², je veux 4 chambres, une cuisine et une salle de bain avec jardin"
    """
    if not is_ready:
        raise HTTPException(
            status_code=503,
            detail="Agent en cours d'initialisation, réessayez dans quelques secondes"
        )
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Le message ne peut pas être vide")

    agent = get_or_create_agent(request.session_id)

    try:
        result = agent.chat(request.message)
        return ChatResponse(
            texte=result["texte"],
            devis=result["devis"],
            session_id=request.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur agent: {str(e)}")


@app.post("/search", tags=["Dataset"])
def search_materials(request: SearchRequest):
    """
    **Recherche directe dans le dataset de matériaux.**

    Retourne les matériaux/prestations les plus proches de votre requête.

    **Catégories disponibles :**
    carrelage, construction, plomberie, electricite, peinture,
    climatisation, isolation, toiture, renovation, estimation_construction
    """
    if not is_ready:
        raise HTTPException(status_code=503, detail="Agent en cours d'initialisation")

    results = retriever.search_specific(request.query, n=request.n_results)
    return {
        "query": request.query,
        "count": len(results),
        "results": results
    }


@app.post("/reset", tags=["Agent"])
def reset_session(request: ResetRequest):
    """**Réinitialiser la conversation** d'une session (efface l'historique)."""
    if request.session_id in agents:
        agents[request.session_id].reset()
        return {"message": f"Session '{request.session_id}' réinitialisée ✅"}
    return {"message": f"Session '{request.session_id}' introuvable (déjà vide)"}


@app.get("/sessions", tags=["Statut"])
def list_sessions():
    """Liste toutes les sessions de conversation actives."""
    return {"sessions": list(agents.keys()), "count": len(agents)}


# ─── Lancement direct ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)