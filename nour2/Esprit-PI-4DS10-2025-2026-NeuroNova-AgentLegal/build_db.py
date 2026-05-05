"""
build_db.py — Construction de la base vectorielle FAISS
Indexe les fragments thématiques depuis data/droit_reel/, data/loi/, data/loi_location/
ainsi que les PDFs (COC, urbanisme).

Lancer dans l'ordre :
    1. python fragment_legal_files.py   ← fragmente les TXT
    2. python build_db.py               ← construit FAISS
    3. uvicorn app.main:app --reload    ← démarre l'API
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import DB_DIR, DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, SEPARATORS, EMBED_MODEL

try:
    import fitz
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
except ImportError as e:
    print(f"❌ Dépendance manquante : {e}")
    print("   pip install -r requirements.txt")
    sys.exit(1)


def _get_embeddings():
    """Ollama nomic-embed-text si dispo, sinon TF-IDF pur numpy."""
    import os, math, hashlib, re
    from collections import Counter
    from typing import List

    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    try:
        import requests as _req
        r = _req.get(f"{ollama_url}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        if any(EMBED_MODEL in m for m in models):
            from langchain_ollama import OllamaEmbeddings
            print(f"✅ Embedding : Ollama ({EMBED_MODEL})")
            return OllamaEmbeddings(model=EMBED_MODEL)
    except Exception:
        pass

    print("⚠️  Ollama absent — TF-IDF numpy embedding (dim=512)")

    class TfidfEmbeddings:
        DIM = 512
        def _embed(self, text: str) -> List[float]:
            text = text.lower()
            text = re.sub(r'[^\w\s؀-ۿ]', ' ', text)
            tokens = [t for t in text.split() if len(t) >= 2]
            if not tokens:
                return [0.0] * self.DIM
            freq = Counter(tokens)
            total = len(tokens)
            vec = [0.0] * self.DIM
            for token, count in freq.items():
                tf = count / total
                h = int(hashlib.md5(token.encode()).hexdigest(), 16)
                idx = h % self.DIM
                idf = math.log(1 + 1.0 / (1 + count))
                vec[idx] += tf * idf
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            return [x / norm for x in vec]
        def embed_documents(self, texts: List[str]) -> List[List[float]]:
            return [self._embed(t) for t in texts]
        def embed_query(self, text: str) -> List[float]:
            return self._embed(text)

    return TfidfEmbeddings()

# ── Sources PDF (pas de fragmentation nécessaire) ─────────────────────────────
PDF_FILES = [
    (DATA_DIR / "COC.pdf",       "COC.pdf"),
    (DATA_DIR / "urbanisme.pdf", "urbanisme.pdf"),
]

# ── Dossiers de fragments TXT ─────────────────────────────────────────────────
TXT_FRAGMENT_DIRS = [
    (DATA_DIR / "droit_reel",   "droit_reel"),
    (DATA_DIR / "loi",          "loi"),
    (DATA_DIR / "loi_location", "loi_location"),
]


def load_pdf(filepath) -> str:
    text = ""
    try:
        doc = fitz.open(str(filepath))
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"❌ Erreur PDF {filepath}: {e}")
    return text


def build():
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
    )
    all_docs = []

    # ── Fragments TXT (thématiques) ───────────────────────────
    for frag_dir, source_name in TXT_FRAGMENT_DIRS:
        if not frag_dir.exists():
            print(f"⚠️  Dossier introuvable : {frag_dir}")
            print(f"   👉 Lancez d'abord : python fragment_legal_files.py")
            continue

        fragment_files = sorted(frag_dir.glob("*.txt"))
        if not fragment_files:
            print(f"⚠️  Dossier vide : {frag_dir}")
            continue

        dir_chunks = 0
        for fpath in fragment_files:
            with open(fpath, encoding="utf-8") as f:
                text = f.read()
            if not text.strip():
                continue
            docs = splitter.create_documents(
                [text],
                metadatas=[{
                    "source": str(fpath),
                    "file":   fpath.name,       # ex: 02_propriete.txt
                    "parent": source_name,       # ex: droit_reel
                }]
            )
            all_docs.extend(docs)
            dir_chunks += len(docs)

        print(f"✅ [{source_name}] : {len(fragment_files)} fragments → {dir_chunks} chunks")

    # ── PDFs ──────────────────────────────────────────────────
    for filepath, fname in PDF_FILES:
        if not filepath.exists():
            print(f"⚠️  PDF non trouvé : {filepath} — ignoré")
            continue
        text = load_pdf(filepath)
        if not text.strip():
            print(f"⚠️  PDF vide : {filepath}")
            continue
        docs = splitter.create_documents(
            [text],
            metadatas=[{"source": str(filepath), "file": fname}]
        )
        all_docs.extend(docs)
        print(f"✅ PDF : {fname} → {len(docs)} chunks")

    if not all_docs:
        print("\n❌ Aucun document chargé. Vérifiez data/ et lancez fragment_legal_files.py d'abord.")
        return

    print(f"\n📚 Total : {len(all_docs)} chunks — génération embeddings (peut prendre 2-5 min)…")
    embeddings = _get_embeddings()
    db = FAISS.from_documents(all_docs, embeddings)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    db.save_local(str(DB_DIR))
    print(f"\n✅ Base FAISS sauvegardée dans {DB_DIR}/")
    print(f"🚀 Lancez maintenant : uvicorn app.main:app --reload --port 8000")


if __name__ == "__main__":
    print("=" * 60)
    print("🏗️  Construction base FAISS — Droit immobilier tunisien")
    print("=" * 60)
    build()
