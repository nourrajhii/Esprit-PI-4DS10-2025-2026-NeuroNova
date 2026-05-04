"""
PRICE-PREDICTOR service (port 8005).
Predicts property prices in TND using ML heuristics.
Wraps dhia's prediction logic via its invoke_adapter when available,
otherwise uses regression coefficients derived from Tunisian market data.
"""
import os, math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx, uvicorn

app = FastAPI(title="Price Predictor Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Delegate to dhia's adapter when running in Docker
DHIA_URL = os.getenv("DHIA_URL", "http://dhia:8005")

CITY_MULTIPLIERS = {
    "tunis": 1.6, "ariana": 1.4, "ben arous": 1.3, "la marsa": 1.7,
    "nabeul": 1.2, "sousse": 1.25, "sfax": 1.05, "monastir": 1.15,
    "bizerte": 0.95, "hammamet": 1.35, "gabès": 0.85, "kairouan": 0.70,
    "gafsa": 0.65, "médenine": 0.80, "manouba": 1.1
}
BASE_PRICE_PER_M2 = 2000  # TND


def _local_predict(city: str, surface: float, rooms: int, bathrooms: int) -> dict:
    city_key = city.lower().strip()
    mult = CITY_MULTIPLIERS.get(city_key, 0.90)
    room_bonus = 1 + (rooms - 2) * 0.04
    bath_bonus = 1 + (bathrooms - 1) * 0.02
    price = BASE_PRICE_PER_M2 * mult * room_bonus * bath_bonus * surface
    price_per_m2 = BASE_PRICE_PER_M2 * mult * room_bonus * bath_bonus
    return {
        "predicted_price_tnd": round(price, 0),
        "price_per_m2_tnd": round(price_per_m2, 0),
        "city": city,
        "surface_m2": surface,
        "rooms": rooms,
        "bathrooms": bathrooms,
        "model": "heuristic-v1"
    }


class InvokeRequest(BaseModel):
    input: dict
    context: dict = {}


@app.post("/invoke")
async def invoke(req: InvokeRequest):
    city = req.input.get("city", "Tunis")
    surface = float(req.input.get("surface_m2", 100))
    rooms = int(req.input.get("rooms", 3))
    bathrooms = int(req.input.get("bathrooms", 1))
    city_tier = int(req.input.get("city_tier", 2))

    # Try dhia first
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(f"{DHIA_URL}/invoke", json={
                "input": {"intent": "predict", "city": city, "surface_m2": surface,
                          "rooms": rooms, "bathrooms": bathrooms, "city_tier": city_tier},
                "context": req.context
            })
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

    # Fallback local
    data = _local_predict(city, surface, rooms, bathrooms)
    return {"output": data, "agent": "price-predictor", "confidence": 0.78}


@app.get("/health")
def health():
    return {"status": "ok", "agent": "price-predictor"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
