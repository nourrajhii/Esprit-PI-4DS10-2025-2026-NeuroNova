"""
schemas.py
Modèles Pydantic v2 — agent immobilier tunisien v3.
Supporte 3 niveaux géographiques, attributs du bien et services de proximité.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

from market_data import TYPES_BIEN, COMPOSITIONS
from geo_data import STANDING_COEFFS, ATTRIBUTS_VENTE, ATTRIBUTS_LOCATION, SERVICES_PROXIMITE


# ── Requêtes ──────────────────────────────────────────────────────────────────

class VenteRequest(BaseModel):
    gouvernorat:        str          = Field(..., description="Gouvernorat tunisien")
    ville:              str          = Field(default="", description="Ville / délégation")
    quartier:           str          = Field(default="", description="Quartier (texte libre)")
    standing:           str          = Field(default="intermédiaire",
                                              description="Standing du quartier")
    type_bien:          str          = Field(..., description="appartement | villa | maison | terrain | bureau")
    superficie:         float        = Field(..., gt=0, description="Superficie en m²")
    prix_m2_saisi:      float        = Field(..., gt=0, description="Prix au m² saisi (TND)")
    attributs_bien:     list[str]    = Field(default_factory=list,
                                              description="Attributs cochés (garage, piscine…)")
    services_proximite: list[str]    = Field(default_factory=list,
                                              description="Services détectés via carte Overpass")

    @field_validator("gouvernorat", "ville", "quartier", mode="before")
    @classmethod
    def strip_str(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("standing", mode="before")
    @classmethod
    def validate_standing(cls, v: str) -> str:
        v = v.strip().lower() if isinstance(v, str) else v
        return v if v in STANDING_COEFFS else "intermédiaire"

    @field_validator("type_bien", mode="before")
    @classmethod
    def validate_type_bien(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in TYPES_BIEN:
            raise ValueError(f"type_bien doit être parmi : {TYPES_BIEN}")
        return v

    @field_validator("attributs_bien", mode="before")
    @classmethod
    def filter_attributs(cls, v: list) -> list:
        return [a for a in v if a in ATTRIBUTS_VENTE]

    @field_validator("services_proximite", mode="before")
    @classmethod
    def filter_services(cls, v: list) -> list:
        return [s for s in v if s in SERVICES_PROXIMITE]

    model_config = {
        "json_schema_extra": {
            "example": {
                "gouvernorat": "Tunis",
                "ville": "La Marsa",
                "quartier": "Plage",
                "standing": "résidentiel",
                "type_bien": "appartement",
                "superficie": 90,
                "prix_m2_saisi": 3200,
                "attributs_bien": ["garage", "terrasse"],
                "services_proximite": ["supermarche", "transport"],
            }
        }
    }


class LocationRequest(BaseModel):
    gouvernorat:        str          = Field(..., description="Gouvernorat tunisien")
    ville:              str          = Field(default="", description="Ville / délégation")
    quartier:           str          = Field(default="", description="Quartier (texte libre)")
    standing:           str          = Field(default="intermédiaire")
    composition:        str          = Field(..., description="S+1 | S+2 | S+3 | S+4")
    loyer_saisi:        float        = Field(..., gt=0, description="Loyer mensuel actuel (TND)")
    attributs_bien:     list[str]    = Field(default_factory=list)
    services_proximite: list[str]    = Field(default_factory=list)

    @field_validator("gouvernorat", "ville", "quartier", mode="before")
    @classmethod
    def strip_str(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("standing", mode="before")
    @classmethod
    def validate_standing(cls, v: str) -> str:
        v = v.strip().lower() if isinstance(v, str) else v
        return v if v in STANDING_COEFFS else "intermédiaire"

    @field_validator("composition", mode="before")
    @classmethod
    def validate_composition(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in COMPOSITIONS:
            raise ValueError(f"composition doit être parmi : {COMPOSITIONS}")
        return v

    @field_validator("attributs_bien", mode="before")
    @classmethod
    def filter_attributs(cls, v: list) -> list:
        return [a for a in v if a in ATTRIBUTS_LOCATION]

    @field_validator("services_proximite", mode="before")
    @classmethod
    def filter_services(cls, v: list) -> list:
        return [s for s in v if s in SERVICES_PROXIMITE]

    model_config = {
        "json_schema_extra": {
            "example": {
                "gouvernorat": "Sousse",
                "ville": "Sousse Centre",
                "quartier": "Corniche",
                "standing": "résidentiel",
                "composition": "S+2",
                "loyer_saisi": 1200,
                "attributs_bien": ["meuble", "clim"],
                "services_proximite": ["transport", "pharmacie"],
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
    # Identité
    mode:                   str
    gouvernorat:            str
    ville:                  str
    quartier:               str
    standing:               str
    type_bien:              Optional[str]   = None
    composition:            Optional[str]   = None
    superficie:             Optional[float] = None
    # Prix saisi
    valeur_saisie:          float
    valeur_totale_actuelle: Optional[float] = None
    # Référence marché ajustée
    prix_base:              float           # prix gouvernorat × coeff standing
    prix_reference_ajuste:  float           # prix_base × (1+attributs) × (1+proximite)
    prix_moyen_marche:      float           # alias = prix_reference_ajuste
    diff_vs_marche_pct:     float
    statut_prix:            str
    # Décomposition des scores
    coeff_standing:         float
    score_attributs:        float
    score_proximite:        float
    attributs_actifs:       dict[str, float]
    services_detectes:      dict[str, float]
    # Taux de croissance
    taux_mensuel:           float
    taux_annuel:            float           # en %
    # Prévisions
    horizons:               dict[str, HorizonData]
    tendance:               str
    risque:                 str
    tension:                str
    # Analyse
    analyse_marche:         str
    facteurs:               list[str]
    recommandation:         str
    # Série mensuelle 24 mois
    points:                 list[ForecastPoint]
    # Coordonnées géographiques
    lat:                    Optional[float] = None
    lng:                    Optional[float] = None


# ── Endpoints utilitaires ─────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:       str
    gouvernorats: int
    types_bien:   list[str]
    compositions: list[str]


class ZonesResponse(BaseModel):
    gouvernorats: list[str]
    types_bien:   list[str]
    compositions: list[str]
    standings:    list[str]


class VillesResponse(BaseModel):
    gouvernorat: str
    villes:      list[str]
    coords:      dict[str, list[float]]  # ville -> [lat, lng]


# ── Rétrocompatibilité /api/predict ──────────────────────────────────────────

class ForecastRequest(BaseModel):
    zone:                str   = Field(...)
    type_bien:           str   = Field(...)
    type_transaction:    str   = Field(...)
    prix_estime_actuel:  float = Field(..., gt=0)
    horizon_mois:        int   = Field(default=24, ge=1, le=60)

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
    zone:             str
    type_bien:        str
    type_transaction: str
    modele_utilise:   str
    mape_test:        Optional[float] = None
    serie_utilisee:   str
    points:           list[ForecastPoint]
    resume:           ForecastResume
