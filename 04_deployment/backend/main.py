"""
main.py
FastAPI — routes :
  POST /api/predict  → prévision de prix immobilier
  GET  /api/health   → statut de l'API
  GET  /api/zones    → listes des zones, types, transactions disponibles
"""

import json
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import ForecastRequest, ForecastResponse, HealthResponse, ZonesResponse
from predictor import predict, load_best_model_index, MODEL_DIR, BEST_MODEL_JSON

import os

BEST_MODEL_JSON_PATH = Path(os.getenv("BEST_MODEL_JSON", BEST_MODEL_JSON))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm-up : charger l'index au démarrage
    try:
        index = load_best_model_index()
        app.state.n_series = len(index.get("series", {}))
        app.state.global_best = index.get("global_best_model", "N/A")
    except Exception:
        app.state.n_series = 0
        app.state.global_best = "N/A"
    yield


app = FastAPI(
    title="immo-forecast API",
    description="Prévision de prix immobiliers tunisiens sur 24 mois.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/predict", response_model=ForecastResponse, summary="Prévision de prix")
async def predict_endpoint(request: ForecastRequest):
    """
    Reçoit les caractéristiques du bien et retourne la courbe de prévision sur l'horizon demandé.
    """
    try:
        result = predict(
            zone=request.zone,
            type_bien=request.type_bien,
            type_transaction=request.type_transaction,
            prix_estime_actuel=request.prix_estime_actuel,
            horizon_mois=request.horizon_mois,
        )
        return ForecastResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"Modèle non disponible : {e}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne : {e}")


@app.get("/api/health", response_model=HealthResponse, summary="Santé de l'API")
async def health():
    n_models = len(list(MODEL_DIR.glob("*.pkl"))) + len(list(MODEL_DIR.glob("*.keras"))) if MODEL_DIR.exists() else 0
    return HealthResponse(
        status="ok" if n_models > 0 else "degraded",
        models_loaded=n_models,
        best_model_global=getattr(app.state, "global_best", "N/A"),
    )


@app.get("/api/zones", response_model=ZonesResponse, summary="Zones et types disponibles")
async def get_zones():
    index = load_best_model_index()
    series_keys = list(index.get("series", {}).keys())

    zones, types_bien, types_tx = set(), set(), set()
    for key in series_keys:
        parts = key.split("_")
        if len(parts) >= 3:
            zones.add(parts[0].title())
            types_tx.add(parts[-1])
            types_bien.add("_".join(parts[1:-1]))

    # Si pas de données encore, valeurs par défaut
    if not zones:
        zones = {"Tunis", "Sfax", "Sousse", "Nabeul", "Ariana", "Ben Arous", "Monastir", "Bizerte"}
        types_bien = {"appartement", "villa", "maison", "terrain", "bureau"}
        types_tx = {"vente", "location"}

    return ZonesResponse(
        zones=sorted(zones),
        types_bien=sorted(types_bien),
        types_transaction=sorted(types_tx),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
