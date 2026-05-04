"""
INVESTMENT-SCORER service (port 8006).
Scores listings as BUY / HOLD / AVOID with full Gemini AI report.
"""
import os
import json
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Investment Scorer Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DHIA_URL       = os.getenv("DHIA_URL", "http://dhia:8005")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

RENTAL_YIELD_BY_CITY = {
    "tunis": 0.055, "ariana": 0.050, "sousse": 0.060, "sfax": 0.052,
    "nabeul": 0.065, "monastir": 0.058, "hammamet": 0.070, "bizerte": 0.048,
    "gabès": 0.045, "gabes": 0.045, "kairouan": 0.042, "la marsa": 0.050,
    "manouba": 0.047, "ben arous": 0.048, "zaghouan": 0.043, "beja": 0.040,
    "jendouba": 0.038, "kef": 0.038, "siliana": 0.037, "gafsa": 0.040,
    "kasserine": 0.038, "sidi bouzid": 0.036, "mahdia": 0.055,
    "djerba": 0.072, "tozeur": 0.050, "tataouine": 0.035,
}
APPRECIATION_BY_CITY = {
    "tunis": 0.06, "ariana": 0.055, "nabeul": 0.07, "sousse": 0.065,
    "sfax": 0.04, "monastir": 0.055, "hammamet": 0.075, "la marsa": 0.065,
    "djerba": 0.08, "bizerte": 0.045, "mahdia": 0.055, "manouba": 0.045,
    "ben arous": 0.050, "gabes": 0.035, "gabès": 0.035,
}
MARKET_CONTEXT = {
    "tunis":    "capitale économique, demande locative élevée, quartiers prisés: Lac, Manar, Berges",
    "ariana":   "proche Tunis, développement résidentiel actif, accès autoroute",
    "sousse":   "hub touristique et économique, fort potentiel locatif saisonnier",
    "sfax":     "2e ville économique, marché stable, industrie diversifiée",
    "nabeul":   "zone touristique Cap Bon, forte saisonnalité, valeur croissante",
    "monastir": "aéroport international, tourisme, immobilier résidentiel solide",
    "hammamet": "destination premium, forte demande étrangère, villas haut de gamme",
    "djerba":   "île touristique, forte rentabilité saisonnière, attrait international",
    "la marsa": "banlieue nord de Tunis, prestige, prix élevés mais stables",
    "bizerte":  "zone industrielle portuaire, développement en cours, prix accessibles",
}


def _score(price: float, city: str, surface: float, property_type: str) -> dict:
    city_key        = city.lower().strip()
    rental_yield    = RENTAL_YIELD_BY_CITY.get(city_key, 0.046)
    appreciation    = APPRECIATION_BY_CITY.get(city_key, 0.035)
    annual_rent     = price * rental_yield
    total_roi_5y    = (rental_yield + appreciation) * 5
    surface_bonus   = 15 if surface > 120 else 8 if surface > 60 else 0
    score = min(100, int((rental_yield * 600) + (appreciation * 400) + surface_bonus))

    if score >= 70:   verdict, color = "BUY",  "green"
    elif score >= 50: verdict, color = "HOLD", "orange"
    else:             verdict, color = "AVOID","red"

    return {
        "verdict":             verdict,
        "score":               score,
        "color":               color,
        "rental_yield_pct":    round(rental_yield * 100, 2),
        "annual_rent_est_tnd": round(annual_rent, 0),
        "appreciation_pct":    round(appreciation * 100, 2),
        "roi_5y_pct":          round(total_roi_5y * 100, 1),
        "city":                city,
        "price_tnd":           price,
        "surface_m2":          surface,
        "property_type":       property_type,
    }


async def _gemini_report(scoring: dict, property_type: str) -> str:
    """Call Gemini 1.5 Flash to generate a full investment report."""
    if not GEMINI_API_KEY:
        return ""
    city         = scoring["city"]
    price        = scoring["price_tnd"]
    surface      = scoring["surface_m2"]
    verdict      = scoring["verdict"]
    score        = scoring["score"]
    roi_5y       = scoring["roi_5y_pct"]
    rent_est     = scoring["annual_rent_est_tnd"]
    rental_yield = scoring["rental_yield_pct"]
    appreciation = scoring["appreciation_pct"]
    context      = MARKET_CONTEXT.get(city.lower(), f"marché immobilier de {city}")

    prompt = f"""Tu es un analyste immobilier expert spécialisé sur le marché tunisien.

Génère un rapport d'investissement complet et structuré en français pour ce bien :

## Données du bien
- Type : {property_type}
- Ville : {city}
- Prix : {price:,.0f} TND
- Surface : {surface:.0f} m²
- Prix/m² : {price/surface:.0f} TND/m² (si surface > 0)

## Scoring IA
- Verdict : **{verdict}**
- Score : {score}/100
- Rendement locatif estimé : {rental_yield}%
- Loyer annuel estimé : {rent_est:,.0f} TND
- Appréciation immobilière annuelle : {appreciation}%
- ROI cumulé sur 5 ans : {roi_5y}%

## Contexte marché {city}
{context}

---

Rédige un rapport structuré avec ces sections (utilise ## pour les titres) :

## 1. Synthèse exécutive
(2-3 phrases sur le verdict et les points clés)

## 2. Analyse du marché à {city}
(dynamiques locales, tendances prix, demande locative)

## 3. Analyse financière détaillée
(rendement brut/net estimé, cash-flow mensuel, comparaison taux immobilier TN)

## 4. Facteurs de risque
(risques à considérer : liquidité, vacance locative, risques macro)

## 5. Stratégie recommandée
(comment optimiser cet investissement : type de locataire cible, travaux, financement)

## 6. Verdict final
(recommandation claire en 1-2 phrases)

Sois précis, professionnel, et utilise des chiffres concrets. Maximum 600 mots."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                data = r.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        print(f"[Gemini] error: {exc}")
    return ""


class InvokeRequest(BaseModel):
    input: dict
    context: dict = {}


@app.post("/invoke")
async def invoke(req: InvokeRequest):
    price         = float(req.input.get("price", req.input.get("budget", 300000)))
    city          = req.input.get("city", "Tunis")
    surface       = float(req.input.get("surface_m2", req.input.get("surface", 100)))
    property_type = req.input.get("property_type", "appartement")

    scoring = _score(price, city, surface, property_type)

    # Try dhia invest endpoint for additional ML data
    dhia_output = None
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(f"{DHIA_URL}/invoke", json={
                "input": {"intent": "invest", "budget": price, "city": city},
                "context": req.context,
            })
            if resp.status_code == 200:
                dhia_output = resp.json()
        except Exception:
            pass

    # Generate full Gemini report
    report = await _gemini_report(scoring, property_type)

    if dhia_output:
        dhia_output["output"]["scoring"]   = scoring
        dhia_output["output"]["report"]    = report
        dhia_output["output"].update(scoring)
        return dhia_output

    return {
        "output": {**scoring, "report": report},
        "agent":      "investment-scorer",
        "confidence": 0.85,
    }


@app.get("/health")
def health():
    return {
        "status":          "ok",
        "agent":           "investment-scorer",
        "gemini_enabled":  bool(GEMINI_API_KEY),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8006)
