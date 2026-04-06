"""
app/schemas/market_insights_schema.py
"""

from pydantic import BaseModel
from typing import List


class GlobalStats(BaseModel):
    total_biens:     int
    prix_moyen:      float
    prix_median:     float
    prix_min:        float
    prix_max:        float
    pm2_moyen:       float
    pm2_median:      float
    pm2_q25:         float
    pm2_q75:         float
    surface_moyenne: float
    surface_mediane: float


class PrixTranche(BaseModel):
    tranche: str
    count:   int
    pct:     float


class StatsRooms(BaseModel):
    rooms:           int
    count:           int
    prix_median:     float
    pm2_median:      float
    surface_mediane: float


class ApartmentBrief(BaseModel):
    id:         str
    title:      str
    price:      float
    surface_m2: float
    rooms:      int
    pm2:        float
    url:        str


class Fourchette(BaseModel):
    min: float
    max: float


class Pm2Fourchette(BaseModel):
    bas:  float
    mid:  float
    haut: float


class MarketIndicators(BaseModel):
    biens_premium_pct:     float
    biens_accessibles_pct: float
    fourchette_typique:    Fourchette
    pm2_fourchette:        Pm2Fourchette


class MarketInsightsResponse(BaseModel):
    global_stats:      GlobalStats
    distribution_prix: List[PrixTranche]
    stats_par_rooms:   List[StatsRooms]
    top_opportunites:  List[ApartmentBrief]
    top_premium:       List[ApartmentBrief]
    market_indicators: MarketIndicators
