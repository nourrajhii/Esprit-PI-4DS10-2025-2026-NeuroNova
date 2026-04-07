"""
app/services/vector_store.py — Singleton FAISS + utilitaires sources

CORRECTIFS :
- _db_cache initialisé au démarrage via init_db() appelé dans main.py startup
- get_db() ne recharge JAMAIS depuis le disque si déjà chargé (vrai singleton)
- reset_db_cache() force le rechargement uniquement à la demande
"""
import json
import re

from app.core.config import DB_DIR, SOURCE_MAP_FILE
from app.services.hardcoded import SOURCE_REGISTRY


# ── Singleton ──────────────────────────────────────────────────────────────────

_db_cache = None
_db_initialized = False   # distingue "pas encore chargé" de "échec de chargement"


def init_db():
    """
    À appeler UNE SEULE FOIS au démarrage (dans startup_event).
    Charge FAISS en mémoire. Les appels suivants à get_db() retournent
    directement l'objet sans toucher le disque.
    """
    global _db_cache, _db_initialized
    if _db_initialized:
        return _db_cache
    _db_initialized = True
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_ollama import OllamaEmbeddings
        from app.core.config import EMBED_MODEL

        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        _db_cache = FAISS.load_local(
            str(DB_DIR),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        print(f"✅ Base FAISS chargée depuis {DB_DIR}")
    except Exception as e:
        print(f"⚠️ Base FAISS non disponible : {e}")
        _db_cache = None
    return _db_cache


def get_db():
    """
    Retourne l'instance FAISS déjà en mémoire.
    Si init_db() n'a pas encore été appelé, l'appelle une première fois.
    """
    global _db_initialized
    if not _db_initialized:
        return init_db()
    return _db_cache


def reset_db_cache():
    """Force le rechargement de la base FAISS au prochain appel."""
    global _db_cache, _db_initialized
    _db_cache = None
    _db_initialized = False


# ── Registre dynamique (source_map.json) ──────────────────────────────────────

def load_dynamic_sources() -> dict:
    if not SOURCE_MAP_FILE.exists():
        return {}
    try:
        with open(SOURCE_MAP_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        return {
            fname: {
                "icon":  info.get("icon", "📄"),
                "label": info.get("label", fname),
                "short": info.get("short", info.get("label", fname)),
            }
            for fname, info in raw.items()
        }
    except Exception:
        return {}


def get_source_info(file_name: str) -> dict:
    dynamic = load_dynamic_sources()
    if file_name in dynamic:
        return dynamic[file_name]
    if file_name in SOURCE_REGISTRY:
        return SOURCE_REGISTRY[file_name]
    nom = file_name.replace(".pdf", "").replace(".txt", "").replace("_", " ").title()
    return {"icon": "📄", "label": nom, "short": nom}


# ── Scoring FAISS ──────────────────────────────────────────────────────────────

def normalize_score(raw_score: float) -> float:
    return round(1.0 / (1.0 + raw_score), 3)


def score_label(sim: float) -> tuple[str, str]:
    if sim >= 0.85:
        return "🟢", "Excellent"
    if sim >= 0.65:
        return "🟡", "Bon"
    if sim >= 0.45:
        return "🟠", "Modéré"
    return "🔴", "Faible"


def extract_article_refs(text: str) -> list[str]:
    refs = []
    for a in re.findall(r'[Aa]rticle\s+(\d+)', text)[:3]:
        refs.append(f"Art. {a}")
    for a in re.findall(r'الفصل\s+(\d+)', text)[:3]:
        refs.append(f"ف. {a}")
    if 'COC' in text:
        refs.append("COC")
    return list(dict.fromkeys(refs))