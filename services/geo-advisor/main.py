"""
GEO-ADVISOR service (port 8007).
Analyzes Tunisian locations: safety, schools, transport, POIs.
Uses OpenStreetMap Nominatim + static scoring tables.
"""
import os, httpx, asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="Geo Advisor Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SAFETY_SCORES = {
    "tunis": 72, "la marsa": 85, "ariana": 78, "nabeul": 80, "hammamet": 82,
    "sousse": 75, "monastir": 77, "sfax": 70, "bizerte": 74, "gabès": 65,
    "kairouan": 68, "manouba": 71, "ben arous": 73, "zaghouan": 76,
    "médenine": 66, "gafsa": 62, "tozeur": 72, "kébili": 69
}
TRANSPORT_SCORES = {
    "tunis": 90, "ariana": 82, "manouba": 75, "sousse": 78, "sfax": 72,
    "nabeul": 65, "monastir": 70, "bizerte": 68, "hammamet": 60, "la marsa": 85,
    "gabès": 55, "kairouan": 58
}
SCHOOL_SCORES = {
    "tunis": 88, "ariana": 82, "la marsa": 90, "nabeul": 75, "sousse": 80,
    "sfax": 78, "monastir": 77, "manouba": 72, "bizerte": 70, "hammamet": 68
}
AMENITY_SCORES = {
    "tunis": 92, "ariana": 85, "la marsa": 88, "sousse": 83, "sfax": 80,
    "nabeul": 72, "monastir": 75, "hammamet": 78, "bizerte": 70, "gabès": 62
}

POI_DATA = {
    "tunis": {"hospitals": 18, "schools": 142, "supermarkets": 87, "parks": 23, "metro_stations": 20},
    "ariana": {"hospitals": 6, "schools": 64, "supermarkets": 42, "parks": 11, "metro_stations": 8},
    "sousse": {"hospitals": 8, "schools": 78, "supermarkets": 55, "parks": 14, "metro_stations": 0},
    "sfax": {"hospitals": 9, "schools": 89, "supermarkets": 61, "parks": 10, "metro_stations": 0},
    "nabeul": {"hospitals": 4, "schools": 52, "supermarkets": 38, "parks": 8, "metro_stations": 0},
    "hammamet": {"hospitals": 2, "schools": 22, "supermarkets": 28, "parks": 12, "metro_stations": 0},
}
DEFAULT_POI = {"hospitals": 2, "schools": 20, "supermarkets": 15, "parks": 5, "metro_stations": 0}


def _get_score(d: dict, city_key: str, default: int = 60) -> int:
    return d.get(city_key, d.get(city_key.split()[0] if " " in city_key else city_key, default))


def _analyze(city: str) -> dict:
    key = city.lower().strip()
    safety = _get_score(SAFETY_SCORES, key)
    transport = _get_score(TRANSPORT_SCORES, key, 55)
    schools = _get_score(SCHOOL_SCORES, key, 60)
    amenities = _get_score(AMENITY_SCORES, key, 58)
    overall = round((safety * 0.3 + transport * 0.25 + schools * 0.25 + amenities * 0.2))
    pois = POI_DATA.get(key, DEFAULT_POI)

    return {
        "city": city,
        "overall_score": overall,
        "scores": {
            "safety": safety,
            "transport": transport,
            "schools": schools,
            "amenities": amenities
        },
        "pois": pois,
        "radar": [
            {"axis": "Sécurité", "value": safety},
            {"axis": "Transport", "value": transport},
            {"axis": "Écoles", "value": schools},
            {"axis": "Commodités", "value": amenities},
            {"axis": "Global", "value": overall}
        ],
        "summary": _build_summary(city, overall, safety, transport, schools)
    }


def _build_summary(city: str, overall: int, safety: int, transport: int, schools: int) -> str:
    if overall >= 80:
        return f"{city} est un quartier excellent — sécurisé, bien desservi et proche des écoles."
    elif overall >= 65:
        return f"{city} offre un bon cadre de vie avec quelques points d'amélioration."
    else:
        return f"{city} est une zone en développement — bon potentiel d'appréciation à long terme."


class InvokeRequest(BaseModel):
    input: dict
    context: dict = {}


@app.post("/invoke")
def invoke(req: InvokeRequest):
    city = req.input.get("city", req.input.get("governorat", "Tunis"))
    data = _analyze(city)
    return {"output": data, "agent": "geo-advisor", "confidence": 0.80}


@app.get("/analyze/{city}")
def analyze_get(city: str):
    return _analyze(city)


@app.get("/health")
def health():
    return {"status": "ok", "agent": "geo-advisor"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8007)
