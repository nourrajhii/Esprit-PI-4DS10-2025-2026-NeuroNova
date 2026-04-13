"""
schemas.py
Modèles Pydantic v2 pour l'API FastAPI — agent immobilier tunisien.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

from market_data import TYPES_BIEN, COMPOSITIONS


# ── Requêtes ──────────────────────────────────────────────────────────────────

class VenteRequest(BaseModel):
    gouvernorat: str = Field(..., description="Gouvernorat tunisien")
    type_bien: str = Field(..., description="appartement, villa, maison, terrain, bureau")
    superficie: float = Field(..., gt=0, description="Superficie en m²")
    prix_m2_saisi: float = Field(..., gt=0, description="Prix au m² saisi par l'utilisateur (TND)")

    @field_validator("gouvernorat")
    @classmethod
    def validate_gouvernorat(cls, v: str) -> str:
        return v.strip()

    @field_validator("type_bien")
    @classmethod
    def validate_type_bien(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in TYPES_BIEN:
            raise ValueError(f"type_bien doit être parmi : {TYPES_BIEN}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "gouvernorat": "Tunis",
                "type_bien": "appartement",
                "superficie": 90,
                "prix_m2_saisi": 3200,
            }
        }
    }


class LocationRequest(BaseModel):
    gouvernorat: str = Field(..., description="Gouvernorat tunisien")
    composition: str = Field(..., description="S+1, S+2, S+3 ou S+4")
    loyer_saisi: float = Field(..., gt=0, description="Loyer mensuel actuel en TND")

    @field_validator("gouvernorat")
    @classmethod
    def validate_gouvernorat(cls, v: str) -> str:
        return v.strip()

    @field_validator("composition")
    @classmethod
    def validate_composition(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in COMPOSITIONS:
            raise ValueError(f"composition doit être parmi : {COMPOSITIONS}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "gouvernorat": "Sousse",
                "composition": "S+2",
                "loyer_saisi": 1200,
            }
        }
    }


# ── Réponse agent ─────────────────────────────────────────────────────────────

class HorizonData(BaseModel):
    valeur: float
    variation_pct: float


class ForecastPoint(BaseModel):
    date: str
    prix_predit: float
    ic_bas: Optional[float] = None
    ic_haut: Optional[float] = None


class AgentResponse(BaseModel):
    mode: str                               # "vente" | "location"
    gouvernorat: str
    type_bien: Optional[str] = None         # vente seulement
    composition: Optional[str] = None       # location seulement
    superficie: Optional[float] = None      # vente seulement
    valeur_saisie: float                    # prix/m² ou loyer
    valeur_totale_actuelle: Optional[float] = None  # vente : prix_m2 × superficie
    prix_moyen_marche: float                # référence marché
    diff_vs_marche_pct: float               # % vs moyenne marché
    statut_prix: str                        # "sous-évalué" etc.
    taux_mensuel: float
    taux_annuel: float                      # en %
    horizons: dict[str, HorizonData]        # "6", "12", "18", "24"
    tendance: str                           # "hausse" | "baisse" | "stable"
    risque: str                             # "Faible" | "Modéré" | "Élevé"
    tension: str                            # tension immobilière locale
    analyse_marche: str                     # paragraphe contextuel
    facteurs: list[str]                     # facteurs clés du marché
    recommandation: str                     # texte généré
    points: list[ForecastPoint]             # série mensuelle 24 mois


# ── Réponse health / zones ────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    gouvernorats: int
    types_bien: list[str]
    compositions: list[str]


class ZonesResponse(BaseModel):
    gouvernorats: list[str]
    types_bien: list[str]
    compositions: list[str]


# ── Anciens schémas (rétrocompatibilité /api/predict) ────────────────────────

class ForecastRequest(BaseModel):
    zone: str = Field(..., description="Gouvernorat tunisien (ex: Tunis, Sfax)")
    type_bien: str = Field(..., description="Catégorie du bien")
    type_transaction: str = Field(..., description="vente ou location")
    prix_estime_actuel: float = Field(..., gt=0)
    horizon_mois: int = Field(default=24, ge=1, le=60)

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


class ForecastResume(BaseModel):
    prix_j6: float
    prix_j12: float
    prix_j18: float
    prix_j24: float
    variation_pct_6: float
    variation_pct_12: float
    variation_pct_18: float
    variation_pct_24: float
    tendance: str


class ForecastResponse(BaseModel):
    zone: str
    type_bien: str
    type_transaction: str
    modele_utilise: str
    mape_test: Optional[float] = None
    serie_utilisee: str
    points: list[ForecastPoint]
    resume: ForecastResume
