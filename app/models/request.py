"""
app/models/request.py — Modèles Pydantic pour les requêtes API

CORRECTIFS :
- k : valeur par défaut réduite à 3 (moins de chunks = réponse plus rapide)
- k=0 ou absent ne provoque plus d'erreur 422
- question : strip automatique via validator
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="La question juridique")
    session_id: Optional[str] = Field(None, description="ID de session pour la mémoire conversationnelle")
    # k réduit à 3 par défaut : récupère moins de chunks FAISS → réponse plus rapide
    # Le RAG filtre déjà par seuil de similarité, 3 chunks pertinents > 5 chunks bruités
    k: int = Field(3, ge=1, le=20, description="Nombre de chunks FAISS à récupérer")

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "Quels sont les droits d'enregistrement pour un bien à 300 000 DT ?",
                    "session_id": "session_20250101_120000",
                    "k": 3
                },
                {
                    "question": "ما هي إجراءات طرد مستأجر لم يدفع الإيجار؟",
                    "k": 3
                }
            ]
        }
    }