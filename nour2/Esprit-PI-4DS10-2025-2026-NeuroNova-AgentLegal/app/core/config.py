"""
app/core/config.py — Configuration centrale de l'API

CORRECTIFS PERFORMANCE :
- LLM_MAX_TOKENS réduit à 250 (au lieu de 350) — le format 3-5 points tient en 200 tokens
- FAISS_K réduit à 3 par défaut (cohérent avec request.py)
"""
import os
from pathlib import Path

# ── Chemins ──────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parents[2]
DB_DIR          = BASE_DIR / "db"
DATA_DIR        = BASE_DIR / "data"
MEMORY_DIR      = BASE_DIR / "memory"
CACHE_DIR       = BASE_DIR / "cache"
SOURCE_MAP_FILE = BASE_DIR / "source_map.json"

# ── Ollama ───────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
EMBED_MODEL     = "nomic-embed-text"
LLM_MODEL       = "llama3.2:3b"
LLM_TEMPERATURE = 0.05
LLM_MAX_TOKENS  = 250   # réduit de 350 → 250 : ~30% plus rapide, suffisant pour 3-5 points

# ── FAISS ────────────────────────────────────────────────────
FAISS_K              = 3      # réduit de 5 → 3 : moins de chunks bruités, plus rapide
SIMILARITY_SEUIL     = 0.65
SIMILARITY_SEUIL_LOW = 0.40

# ── Cache ────────────────────────────────────────────────────
CACHE_SIMILARITY_THRESHOLD = 0.92
MAX_CACHE_ENTRIES           = 500

# ── Mémoire ──────────────────────────────────────────────────
MAX_CHARS_BEFORE_SUMMARY = 3000
CONTEXT_WINDOW           = 6
SUMMARY_KEEP_LAST        = 2

# ── Chunking ─────────────────────────────────────────────────
CHUNK_SIZE    = 900
CHUNK_OVERLAP = 200
SEPARATORS = [
    "\n================================================================\n",
    "\n\nالفصل ", "\n\nArticle ",
    "\nالفصل ",  "\nArticle ",
    "\n\n", "\n", ".", " ",
]

# ── Types qui ne nécessitent PAS FAISS (hardcodé suffit) ─────
# Only keep types that have complete hardcoded rules and no useful PDF content
SELF_CONTAINED_TYPES = {
    "fiscal",      # complete tax rate table hardcoded
    "plus_value",  # complete calculation formula hardcoded
}