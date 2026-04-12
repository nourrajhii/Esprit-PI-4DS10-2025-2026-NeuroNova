"""
schemas.py
Modèles Pydantic v2 pour l'API FastAPI.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ForecastRequest(BaseModel):
    zone: str = Field(..., description="Gouvernorat tunisien (ex: Tunis, Sfax)")
    type_bien: str = Field(..., description="Catégorie du bien (appartement, villa, terrain, …)")
    type_transaction: str = Field(..., description="vente ou location")
    prix_estime_actuel: float = Field(..., gt=0, description="Prix actuel estimé en TND/m²")
    horizon_mois: int = Field(default=24, ge=1, le=60, description="Horizon de prévision en mois")

    @field_validator("type_transaction")
    @classmethod
    def validate_transaction(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("vente", "location"):
            raise ValueError("type_transaction doit être 'vente' ou 'location'")
        return v

    @field_validator("type_bien")
    @classmethod
    def validate_type_bien(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("zone")
    @classmethod
    def validate_zone(cls, v: str) -> str:
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "zone": "Tunis",
                "type_bien": "appartement",
                "type_transaction": "vente",
                "prix_estime_actuel": 3500,
                "horizon_mois": 24,
            }
        }
    }


class ForecastPoint(BaseModel):
    date: str
    prix_predit: float
    ic_bas: Optional[float] = None
    ic_haut: Optional[float] = None


class ForecastResume(BaseModel):
    prix_j12: float = Field(..., description="Prix prédit à +12 mois (TND/m²)")
    prix_j24: float = Field(..., description="Prix prédit à +24 mois (TND/m²)")
    variation_pct_12: float = Field(..., description="Variation % à +12 mois")
    variation_pct_24: float = Field(..., description="Variation % à +24 mois")
    tendance: str = Field(..., description="hausse, baisse ou stable")


class ForecastResponse(BaseModel):
    zone: str
    type_bien: str
    type_transaction: str
    modele_utilise: str
    mape_test: Optional[float] = None
    serie_utilisee: str
    points: list[ForecastPoint]
    resume: ForecastResume

    model_config = {
        "json_schema_extra": {
            "example": {
                "zone": "Tunis",
                "type_bien": "appartement",
                "type_transaction": "vente",
                "modele_utilise": "prophet",
                "mape_test": 8.4,
                "serie_utilisee": "tunis_appartement_vente",
                "points": [
                    {"date": "2025-05-01", "prix_predit": 3612.0, "ic_bas": 3200.0, "ic_haut": 4024.0}
                ],
                "resume": {
                    "prix_j12": 3750.0,
                    "prix_j24": 3950.0,
                    "variation_pct_12": 7.1,
                    "variation_pct_24": 12.9,
                    "tendance": "hausse",
                },
            }
        }
    }


class HealthResponse(BaseModel):
    status: str
    models_loaded: int
    best_model_global: Optional[str] = None


class ZonesResponse(BaseModel):
    zones: list[str]
    types_bien: list[str]
    types_transaction: list[str]
