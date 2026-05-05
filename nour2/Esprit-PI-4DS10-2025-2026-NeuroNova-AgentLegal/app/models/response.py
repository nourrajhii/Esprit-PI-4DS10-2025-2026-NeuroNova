"""
app/models/response.py — Modèles Pydantic pour les réponses API

CORRECTIONS v3 :
- MetricItem : ajout des champs NLP (nlp_combined, nlp_tfidf, nlp_jaccard)
  exposés dans la réponse API pour permettre le debug et l'affichage frontend
"""
from pydantic import BaseModel
from typing import Optional


class SourceInfo(BaseModel):
    icon: str
    label: str


class MetricItem(BaseModel):
    rank: int
    source: str
    source_label: str
    source_short: str
    source_icon: str
    raw_score: float
    similarity: float          # score FAISS normalisé seul
    nlp_combined: float = 0.0  # score combiné FAISS + TF-IDF + Jaccard (nouveau)
    nlp_tfidf: float = 0.0     # score TF-IDF normalisé (nouveau)
    nlp_jaccard: float = 0.0   # similarité Jaccard tokens (nouveau)
    score_emoji: str
    score_label: str
    article_refs: list[str]
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    question_type: str
    lang: str
    is_calculation: bool
    from_cache: bool
    hardcoded_source: Optional[SourceInfo] = None
    metrics: list[MetricItem] = []
    cache_similarity: Optional[float] = None
    cache_date: Optional[str] = None
    session_id: Optional[str] = None


class SessionItem(BaseModel):
    session_id: str
    updated_at: str
    message_count: int
    preview: str


class HealthResponse(BaseModel):
    status: str
    faiss_loaded: bool
    cache_entries: int
    version: str = "3.0.0"