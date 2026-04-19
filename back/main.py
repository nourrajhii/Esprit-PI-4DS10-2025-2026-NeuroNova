"""
main.py
FastAPI — routes :
  POST /api/analyze/vente     → agent analyse vente (prix/m²)
  POST /api/analyze/location  → agent analyse location (loyer mensuel)
  GET  /api/zones             → gouvernorats, types, compositions
  GET  /api/health            → statut de l'API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from schemas import (
    VenteRequest, LocationRequest, AgentResponse,
    HealthResponse, ZonesResponse,
)
from agent import analyze_vente, analyze_location
from market_data import NOMS_GOUVERNORATS, TYPES_BIEN, COMPOSITIONS


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = True
    yield


app = FastAPI(
    title="ImmoForecast TN — Agent IA",
    description="Agent d'analyse de marché immobilier tunisien — 24 gouvernorats.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes agent ──────────────────────────────────────────────────────────────

@app.post(
    "/api/analyze/vente",
    response_model=AgentResponse,
    summary="Analyse de marché — mode Vente",
)
async def route_vente(request: VenteRequest):
    """
    Analyse un bien en vente : positionnement marché, prévisions 6/12/18/24 mois,
    indicateur de risque et recommandation contextuelle.
    """
    try:
        result = analyze_vente(
            gouvernorat=request.gouvernorat,
            type_bien=request.type_bien,
            superficie=request.superficie,
            prix_m2_saisi=request.prix_m2_saisi,
        )
        return AgentResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur agent : {e}")


@app.post(
    "/api/analyze/location",
    response_model=AgentResponse,
    summary="Analyse de marché — mode Location",
)
async def route_location(request: LocationRequest):
    """
    Analyse un bien en location : positionnement loyer, prévisions 6/12/18/24 mois,
    indicateur de risque et recommandation propriétaire/locataire.
    """
    try:
        result = analyze_location(
            gouvernorat=request.gouvernorat,
            composition=request.composition,
            loyer_saisi=request.loyer_saisi,
        )
        return AgentResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur agent : {e}")


# ── Routes utilitaires ────────────────────────────────────────────────────────

@app.get("/api/zones", response_model=ZonesResponse, summary="Données de référence")
async def get_zones():
    return ZonesResponse(
        gouvernorats=NOMS_GOUVERNORATS,
        types_bien=TYPES_BIEN,
        compositions=COMPOSITIONS,
    )


@app.get("/api/health", response_model=HealthResponse, summary="Santé de l'API")
async def health():
    return HealthResponse(
        status="ok",
        gouvernorats=len(NOMS_GOUVERNORATS),
        types_bien=TYPES_BIEN,
        compositions=COMPOSITIONS,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
