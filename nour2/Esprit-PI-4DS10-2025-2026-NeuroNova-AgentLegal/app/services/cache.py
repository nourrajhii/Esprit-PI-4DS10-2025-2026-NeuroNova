"""
app/services/cache.py — Cache JSON de réponses (similarité Jaccard)
"""
import json
import os
import re
import hashlib
from datetime import datetime

from app.core.config import CACHE_DIR, CACHE_SIMILARITY_THRESHOLD, MAX_CACHE_ENTRIES

CACHE_FILE = CACHE_DIR / "responses.json"


# ── Normalisation ──────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[\u0610-\u061A\u064B-\u065F]', '', text)
    text = re.sub(r'[أإآٱ]', 'ا', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _tokenize(text: str) -> set:
    return {t for t in _normalize(text).split() if len(t) >= 2}


def _similarity(q1: str, q2: str) -> float:
    t1, t2 = _tokenize(q1), _tokenize(q2)
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)


def _question_hash(question: str) -> str:
    return hashlib.md5(_normalize(question).encode()).hexdigest()[:12]


# ── Persistence ────────────────────────────────────────────────────────────────

def _load_cache() -> list:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not CACHE_FILE.exists():
        return []
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_cache(entries: list):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if len(entries) > MAX_CACHE_ENTRIES:
        entries = entries[-MAX_CACHE_ENTRIES:]
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


# ── API publique ───────────────────────────────────────────────────────────────

def lookup(question: str) -> dict | None:
    entries = _load_cache()
    if not entries:
        return None
    best_sim, best_entry = 0.0, None
    for entry in entries:
        sim = _similarity(question, entry.get("question", ""))
        if sim > best_sim:
            best_sim, best_entry = sim, entry
    if best_sim >= CACHE_SIMILARITY_THRESHOLD and best_entry:
        result = dict(best_entry.get("result", {}))
        result.update({
            "from_cache":        True,
            "cache_similarity":  round(best_sim, 3),
            "cache_date":        best_entry.get("timestamp", ""),
            "original_question": best_entry.get("question", ""),
        })
        return result
    return None


def store(question: str, result: dict):
    if result.get("from_cache"):
        return
    # Never cache empty or fallback-only answers — wait for a real LLM response
    answer = result.get("answer", "")
    if not answer or not answer.strip():
        return
    if "⚠️ *Réponse extraite directement" in answer or "⚠️ *هذه إجابة تلقائية" in answer:
        return
    entries = _load_cache()
    q_hash = _question_hash(question)
    safe_result = _sanitize_result(result)
    for entry in entries:
        if entry.get("hash") == q_hash:
            entry["result"] = safe_result
            entry["timestamp"] = datetime.now().isoformat()
            entry["hits"] = entry.get("hits", 0) + 1
            _save_cache(entries)
            return
    entries.append({
        "hash":      q_hash,
        "question":  question,
        "timestamp": datetime.now().isoformat(),
        "hits":      0,
        "result":    safe_result,
    })
    _save_cache(entries)


def _sanitize_result(result: dict) -> dict:
    safe = {}
    for k, v in result.items():
        if k == "metrics" and isinstance(v, list):
            safe[k] = [{mk: mv for mk, mv in m.items() if mk != "_doc"} for m in v]
        elif k != "_doc":
            safe[k] = v
    return safe


def cache_stats() -> dict:
    entries = _load_cache()
    if not entries:
        return {"total": 0, "most_asked": None, "most_hits": 0}
    most_asked = max(entries, key=lambda e: e.get("hits", 0), default=None)
    return {
        "total":      len(entries),
        "most_asked": most_asked.get("question", "") if most_asked else None,
        "most_hits":  most_asked.get("hits", 0) if most_asked else 0,
    }


def clear_cache():
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
