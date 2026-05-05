import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
from pathlib import Path


class MaterialVectorStore:
    def __init__(self, persist_dir: str = "./chroma_db"):
        # Use EphemeralClient (in-memory) — PersistentClient's Rust HNSW backend
        # is incompatible with ChromaDB ≥1.x on some platforms. The dataset is
        # small (< 100 rows) so re-indexing on startup takes < 5 s.
        self.client = chromadb.EphemeralClient()

        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )

        self.collection = self.client.get_or_create_collection(
            name="materiaux_construction",
            embedding_function=self.embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def is_populated(self) -> bool:
        return self.collection.count() > 0

    def index_dataset(self, df: pd.DataFrame):
        """Indexe tout le dataset dans ChromaDB."""
        if self.is_populated():
            print("✅ Base vectorielle déjà indexée, skip.")
            return

        print(f"📥 Indexation de {len(df)} matériaux...")

        batch_size = 500
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]

            metadatas = []
            for _, row in batch.iterrows():
                meta = {
                    "title":        str(row["title_clean"])[:200],
                    "category":     str(row["category"]),
                    "price":        float(row["price"]),
                    "unit":         str(row["unit"]),
                    "price_display": str(row["price_display"])[:200],
                    "source_type":  str(row["source_type"]),
                    "city":         str(row.get("city", "Tunisie")),
                    "supplier":     str(row.get("supplier", ""))[:100],
                }
                # Stocker price_min / price_max si disponibles
                if pd.notna(row.get("price_min")) and float(row["price_min"]) > 0:
                    meta["price_min"] = float(row["price_min"])
                if pd.notna(row.get("price_max")) and float(row["price_max"]) > 0:
                    meta["price_max"] = float(row["price_max"])
                metadatas.append(meta)

            self.collection.add(
                ids=[f"mat_{idx}" for idx in batch.index],
                documents=batch["text_for_embedding"].tolist(),
                metadatas=metadatas,
            )
            print(f"   Lot {i//batch_size + 1}/{(len(df)-1)//batch_size + 1} indexé")

        print(f"✅ Indexation terminée: {self.collection.count()} documents")

    def search(self, query: str, n_results: int = 10,
               category_filter: str = None) -> list[dict]:
        """Recherche sémantique dans les matériaux."""
        where = {"category": category_filter} if category_filter else None

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        return [
            {
                "document":        doc,
                "metadata":        meta,
                "relevance_score": 1 - dist,
            }
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]