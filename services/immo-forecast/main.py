"""
IMMO-FORECAST — Agent IA de prévision immobilière tunisienne (port 8004).
Endpoints:
  POST /invoke                   → interface /invoke standard (pour VIAGRA)
  POST /api/analyze/vente        → analyse vente (prix/m²)
  POST /api/analyze/location     → analyse location (loyer mensuel)
  GET  /api/villes/{gov}         → villes + coordonnées
  GET  /api/zones                → gouvernorats, types, standings
  GET  /forecast/{governorat}    → prévisions simple (legacy VIAGRA)
  GET  /health
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agent import analyze_vente, analyze_location
from market_data import NOMS_GOUVERNORATS, TYPES_BIEN, COMPOSITIONS, GOUVERNORATS
from geo_data import VILLES_PAR_GOUVERNORAT, COORDS_VILLES, STANDINGS

app = FastAPI(title="ImmoForecast TN — Agent IA v3")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Pydantic schemas ──────────────────────────────────────────────────────────

class VenteRequest(BaseModel):
    gouvernorat: str
    ville: str = ""
    quartier: str = ""
    standing: str = "intermédiaire"
    type_bien: str = "appartement"
    superficie: float = 100
    prix_m2_saisi: float
    attributs_bien: list[str] = []
    services_proximite: list[str] = []

class LocationRequest(BaseModel):
    gouvernorat: str
    ville: str = ""
    quartier: str = ""
    standing: str = "intermédiaire"
    composition: str = "S+2"
    loyer_saisi: float
    attributs_bien: list[str] = []
    services_proximite: list[str] = []

class InvokeRequest(BaseModel):
    input: dict
    context: dict = {}

# ── /invoke (VIAGRA standard) ─────────────────────────────────────────────────

@app.post("/invoke")
def invoke(req: InvokeRequest):
    inp = req.input
    gouvernorat = inp.get("governorat", inp.get("gouvernorat", inp.get("region", "Tunis")))
    mode = inp.get("mode", "vente")

    if mode == "location":
        result = analyze_location(
            gouvernorat=gouvernorat,
            ville=inp.get("ville", ""),
            quartier=inp.get("quartier", ""),
            standing=inp.get("standing", "intermédiaire"),
            composition=inp.get("composition", "S+2"),
            loyer_saisi=float(inp.get("loyer_saisi", inp.get("loyer", 1200))),
            attributs_bien=inp.get("attributs_bien", []),
            services_proximite=inp.get("services_proximite", []),
        )
    else:
        # Default: vente — also handles legacy {governorat, months} calls
        gov_data = GOUVERNORATS.get(gouvernorat, GOUVERNORATS.get("Tunis", {}))
        prix_ref = gov_data.get("prix_moyen_m2", {}).get("appartement", 2500)
        result = analyze_vente(
            gouvernorat=gouvernorat,
            ville=inp.get("ville", ""),
            quartier=inp.get("quartier", ""),
            standing=inp.get("standing", "intermédiaire"),
            type_bien=inp.get("type_bien", "appartement"),
            superficie=float(inp.get("superficie", 100)),
            prix_m2_saisi=float(inp.get("prix_m2_saisi", inp.get("prix_m2", prix_ref))),
            attributs_bien=inp.get("attributs_bien", []),
            services_proximite=inp.get("services_proximite", []),
        )

    # Build legacy-compatible output for VIAGRA
    h12 = result["horizons"]["12"]
    h24 = result["horizons"]["24"]
    series = [
        {
            "month": p["date"][:7],
            "price_per_m2_tnd": round(p["prix_predit"]),
            "demand_index": round(50 + (p["prix_predit"] - result["valeur_saisie"]) / result["valeur_saisie"] * 100, 1),
            "trend": result["tendance"],
        }
        for p in result["points"][:12]
    ]
    return {
        "output": {
            "gouvernorat": gouvernorat,
            "forecast_months": 12,
            "current_price_per_m2": result["valeur_saisie"],
            "forecasted_price_per_m2": round(h12["valeur"]),
            "pct_change_12m": round(h12["variation_pct"], 1),
            "signal": "BUY" if h24["variation_pct"] > 4 else "HOLD" if h24["variation_pct"] > 0 else "WAIT",
            "series": series,
            "full_report": result,
        },
        "agent": "immo-forecast",
        "confidence": 0.80,
    }

# ── /api/analyze/* (full agent API) ──────────────────────────────────────────

@app.post("/api/analyze/vente")
def route_vente(request: VenteRequest):
    try:
        return analyze_vente(
            gouvernorat=request.gouvernorat,
            ville=request.ville,
            quartier=request.quartier,
            standing=request.standing,
            type_bien=request.type_bien,
            superficie=request.superficie,
            prix_m2_saisi=request.prix_m2_saisi,
            attributs_bien=request.attributs_bien,
            services_proximite=request.services_proximite,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur agent : {e}")

@app.post("/api/analyze/location")
def route_location(request: LocationRequest):
    try:
        return analyze_location(
            gouvernorat=request.gouvernorat,
            ville=request.ville,
            quartier=request.quartier,
            standing=request.standing,
            composition=request.composition,
            loyer_saisi=request.loyer_saisi,
            attributs_bien=request.attributs_bien,
            services_proximite=request.services_proximite,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur agent : {e}")

# ── Geo / zones ───────────────────────────────────────────────────────────────

@app.get("/api/villes/{gouvernorat}")
def get_villes(gouvernorat: str):
    villes = VILLES_PAR_GOUVERNORAT.get(gouvernorat, [])
    if not villes:
        for k, v in VILLES_PAR_GOUVERNORAT.items():
            if k.lower() in gouvernorat.lower() or gouvernorat.lower() in k.lower():
                villes = v
                break
    coords: dict[str, list[float]] = {}
    for v in villes:
        if v in COORDS_VILLES:
            lat, lng = COORDS_VILLES[v]
            coords[v] = [lat, lng]
    return {"gouvernorat": gouvernorat, "villes": villes, "coords": coords}

@app.get("/api/zones")
def get_zones():
    return {
        "gouvernorats": NOMS_GOUVERNORATS,
        "types_bien": TYPES_BIEN,
        "compositions": COMPOSITIONS,
        "standings": STANDINGS,
    }

# ── Legacy GET /forecast/{governorat} (VIAGRA proxy) ─────────────────────────

@app.get("/forecast/{governorat}")
def forecast_get(governorat: str, months: int = 12):
    gov_data = GOUVERNORATS.get(governorat, GOUVERNORATS.get("Tunis", {}))
    prix_ref = gov_data.get("prix_moyen_m2", {}).get("appartement", 2500)
    result = analyze_vente(
        gouvernorat=governorat, ville="", quartier="", standing="intermédiaire",
        type_bien="appartement", superficie=100, prix_m2_saisi=prix_ref,
        attributs_bien=[], services_proximite=[],
    )
    series = [
        {
            "month": p["date"][:7],
            "price_per_m2_tnd": round(p["prix_predit"]),
            "demand_index": round(min(max(30, 60 + (p["prix_predit"] - prix_ref) / prix_ref * 200), 100), 1),
            "trend": result["tendance"],
        }
        for p in result["points"][:months]
    ]
    return {"governorat": governorat, "series": series}

@app.get("/governorats")
def list_governorats():
    return {"governorats": NOMS_GOUVERNORATS}

@app.get("/health")
def health():
    return {"status": "ok", "agent": "immo-forecast"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
