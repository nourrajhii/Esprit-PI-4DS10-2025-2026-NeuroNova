"""
app/api/routes/admin.py — Routes d'administration

AJOUT :
- POST /admin/reload-llm : recrée l'instance LLM (utile si Ollama a redémarré)
"""
from fastapi import APIRouter
from app.services.vector_store import reset_db_cache, get_db, init_db
from app.services.cache import clear_cache, cache_stats

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/reload-db")
async def reload_db():
    """Force le rechargement de la base FAISS depuis le disque."""
    reset_db_cache()
    db = init_db()
    return {
        "reloaded": db is not None,
        "message":  "Base FAISS rechargée." if db else "Échec rechargement — vérifiez ./db/",
    }


@router.post("/reload-llm")
async def reload_llm():
    """Recrée l'instance LLM Ollama (utile si Ollama a redémarré)."""
    from app.services.llm import reset_llm, get_llm
    reset_llm()
    try:
        get_llm()
        return {"reloaded": True, "message": "LLM réinitialisé avec succès."}
    except Exception as e:
        return {"reloaded": False, "message": f"Échec : {e}"}


@router.post("/clear-cache")
async def admin_clear_cache():
    """Vide entièrement le cache de réponses."""
    clear_cache()
    return {"cleared": True, "message": "Cache vidé."}


@router.get("/cache-stats")
async def admin_cache_stats():
    """Retourne les statistiques du cache."""
    return cache_stats()