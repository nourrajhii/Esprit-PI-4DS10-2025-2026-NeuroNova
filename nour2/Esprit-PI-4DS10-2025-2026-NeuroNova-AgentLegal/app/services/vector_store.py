"""
app/services/vector_store.py — Singleton FAISS + BM25 fallback

Quand Ollama (nomic-embed-text) est disponible : FAISS vectoriel.
Quand Ollama est absent : BM25Retriever pur Python/numpy,
  API identique à FAISS (similarity_search_with_score).
"""
import json
import re
import math
from collections import Counter
from typing import List, Tuple, Any
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from app.core.config import DB_DIR, DATA_DIR, SOURCE_MAP_FILE, OLLAMA_BASE_URL, EMBED_MODEL
from app.services.hardcoded import SOURCE_REGISTRY


# ── BM25 pur Python ───────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    text = text.lower()
    # normalize French accented characters
    import unicodedata as _ud
    text = ''.join(c for c in _ud.normalize('NFD', text) if _ud.category(c) != 'Mn' or ord(c) > 0x036F)
    # supprime diacritiques arabes
    text = re.sub(r'[ؐ-ًؚ-ٟ]', '', text)
    # normalise alef
    text = re.sub(r'[أإآٱ]', 'ا', text)
    text = re.sub(r'[^\w\s؀-ۿ]', ' ', text)
    tokens = text.split()
    STOP_FR = {'le','la','les','de','du','des','un','une','et','en','que','qui',
               'est','dans','pour','sur','par','avec','ce','au','aux','ou','je',
               'tu','il','elle','nous','vous','ils','pas','plus','se','son','sa'}
    STOP_AR = {'في','من','إلى','على','عن','مع','هذا','هذه','ذلك','التي','الذي',
               'أن','كان','قد','لا','ما','هو','هي','لم','لن','كل','بعض','و','أو'}
    return [t for t in tokens if len(t) >= 2 and t not in STOP_FR and t not in STOP_AR]


class BM25Index:
    """
    BM25 index avec API compatible FAISS similarity_search_with_score.
    Charge tous les documents depuis les fichiers TXT et PDF du dossier data/.
    """
    K1 = 1.5
    B  = 0.75

    def __init__(self):
        self.docs: List[Document] = []
        self.tokenized: List[List[str]] = []
        self.df: Counter = Counter()
        self.avgdl: float = 0.0
        self._load_documents()
        self._build_index()

    def _load_documents(self):
        """Charge tous les fichiers TXT et PDF depuis data/."""
        from app.core.config import CHUNK_SIZE, CHUNK_OVERLAP, SEPARATORS
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                separators=SEPARATORS,
            )
        except Exception:
            splitter = None

        def _split(text: str, metadata: dict) -> List[Document]:
            if splitter:
                return splitter.create_documents([text], metadatas=[metadata])
            # fallback simple : découpage par paragraphes
            chunks = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
            return [Document(page_content=c, metadata=metadata) for c in chunks]

        # Dossiers TXT thématiques
        for subdir, parent in [('droit_reel','droit_reel'),('loi','loi'),('loi_location','loi_location')]:
            d = DATA_DIR / subdir
            if not d.exists():
                continue
            for fpath in sorted(d.glob('*.txt')):
                try:
                    text = fpath.read_text(encoding='utf-8')
                    self.docs.extend(_split(text, {'file': fpath.name, 'parent': parent, 'source': str(fpath)}))
                except Exception:
                    pass

        # PDFs
        for fname in ['COC.pdf', 'urbanisme.pdf', 'مجلة الحقوق العينية.pdf']:
            fpath = DATA_DIR / fname
            if not fpath.exists():
                continue
            try:
                import fitz
                text = ''
                doc = fitz.open(str(fpath))
                for page in doc:
                    text += page.get_text()
                doc.close()
                self.docs.extend(_split(text, {'file': fname, 'parent': fname, 'source': str(fpath)}))
            except Exception:
                pass

        print(f"✅ BM25 chargé : {len(self.docs)} chunks depuis data/")

    def _build_index(self):
        self.tokenized = [_tokenize(d.page_content) for d in self.docs]
        N = len(self.tokenized)
        if N == 0:
            return
        total_len = sum(len(t) for t in self.tokenized)
        self.avgdl = total_len / N
        for tokens in self.tokenized:
            for term in set(tokens):
                self.df[term] += 1

    def _bm25_score(self, query_tokens: List[str], doc_idx: int) -> float:
        N = len(self.docs)
        if N == 0:
            return 0.0
        tokens = self.tokenized[doc_idx]
        dl = len(tokens)
        tf_map = Counter(tokens)
        score = 0.0
        for term in query_tokens:
            tf = tf_map.get(term, 0)
            if tf == 0:
                continue
            df = self.df.get(term, 0)
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
            tf_norm = (tf * (self.K1 + 1)) / (tf + self.K1 * (1 - self.B + self.B * dl / max(self.avgdl, 1)))
            score += idf * tf_norm
        return score

    def similarity_search_with_score(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        q_tokens = _tokenize(query)
        if not q_tokens or not self.docs:
            return []

        # Detect if query is Arabic (>15% Arabic chars)
        arabic_chars = len(re.findall(r'[؀-ۿ]', query))
        is_arabic_query = arabic_chars > len(query) * 0.15

        scores = [(i, self._bm25_score(q_tokens, i)) for i in range(len(self.docs))]

        # Boost Arabic documents when query is in Arabic
        if is_arabic_query:
            boosted = []
            for idx, s in scores:
                doc_text = self.docs[idx].page_content
                doc_arabic = len(re.findall(r'[؀-ۿ]', doc_text))
                arabic_ratio = doc_arabic / max(len(doc_text), 1)
                boost = 1.5 if arabic_ratio > 0.3 else 1.0
                boosted.append((idx, s * boost))
            scores = boosted

        scores.sort(key=lambda x: x[1], reverse=True)
        # Retourne (doc, distance) — distance = 1/(1+score) pour compatibilité normalize_score()
        results = []
        for idx, s in scores[:k]:
            dist = 1.0 / (1.0 + s) if s > 0 else 9.9
            results.append((self.docs[idx], dist))
        return results


# ── Singleton ─────────────────────────────────────────────────────────────────

_db_cache = None
_db_initialized = False


def _ollama_available() -> bool:
    try:
        import requests as _req
        from app.core.config import OLLAMA_BASE_URL, EMBED_MODEL
        r = _req.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        return any(EMBED_MODEL in m for m in models)
    except Exception:
        return False


def init_db():
    global _db_cache, _db_initialized
    if _db_initialized:
        return _db_cache
    _db_initialized = True

    # ── Chemin 1 : FAISS + Ollama ─────────────────────────────
    if _ollama_available():
        try:
            from langchain_community.vectorstores import FAISS
            from langchain_ollama import OllamaEmbeddings
            embeddings = OllamaEmbeddings(model=EMBED_MODEL)
            _db_cache = FAISS.load_local(
                str(DB_DIR),
                embeddings,
                allow_dangerous_deserialization=True,
            )
            print(f"✅ FAISS + Ollama chargé depuis {DB_DIR}")
            return _db_cache
        except Exception as e:
            print(f"⚠️ FAISS Ollama échoué : {e}")

    # ── Chemin 2 : BM25 pur Python ─────────────────────────────
    print("⚠️ Ollama absent — BM25 pur Python activé")
    try:
        _db_cache = BM25Index()
    except Exception as e:
        print(f"⚠️ BM25 échoué : {e}")
        _db_cache = None
    return _db_cache


def get_db():
    global _db_initialized
    if not _db_initialized:
        return init_db()
    return _db_cache


def reset_db_cache():
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
    nom = (
        file_name
        .replace(".pdf", "")
        .replace(".txt", "")
        .replace("_", " ")
        .title()
    )
    return {"icon": "📄", "label": nom, "short": nom}


# ── Scoring ────────────────────────────────────────────────────────────────────

def normalize_score(raw_score: float) -> float:
    """Distance → similarité [0,1] : 1/(1+dist)"""
    return round(1.0 / (1.0 + raw_score), 3)


def normalize_score_cosine(raw_score: float) -> float:
    return round((raw_score + 1.0) / 2.0, 3)


def score_label(sim: float) -> tuple[str, str]:
    if sim >= 0.80:
        return "🟢", "Excellent"
    if sim >= 0.60:
        return "🟡", "Bon"
    if sim >= 0.40:
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
