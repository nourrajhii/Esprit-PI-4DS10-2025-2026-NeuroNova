"""
Standalone devis (construction quote) service — port 8009
Returns structured cost estimates for Tunisian construction projects.
No ML/LLM dependencies required.
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Devis Construction Tunisie")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Cost data per m² (TND, 2025 market) by standing
COSTS = {
    "économique":    {"gros_oeuvre": 380, "second_oeuvre": 180, "finitions": 120},
    "intermédiaire": {"gros_oeuvre": 480, "second_oeuvre": 240, "finitions": 200},
    "haut_standing": {"gros_oeuvre": 620, "second_oeuvre": 340, "finitions": 320},
}

CITY_COEFF = {
    "Tunis": 1.15, "Ariana": 1.12, "Ben Arous": 1.10, "Manouba": 1.05,
    "Nabeul": 1.08, "Hammamet": 1.10, "Sousse": 1.08, "Monastir": 1.05,
    "Sfax": 1.02, "Bizerte": 1.00, "La Marsa": 1.15, "default": 1.00,
}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


def estimate(surface: float, standing: str = "intermédiaire", city: str = "Tunis") -> dict:
    c = COSTS.get(standing, COSTS["intermédiaire"])
    coeff = CITY_COEFF.get(city, CITY_COEFF["default"])
    total_per_m2 = (c["gros_oeuvre"] + c["second_oeuvre"] + c["finitions"]) * coeff
    total = total_per_m2 * surface
    return {
        "surface_m2": surface,
        "standing": standing,
        "city": city,
        "coeff_localisation": coeff,
        "detail": {
            "gros_oeuvre_tnd":  round(c["gros_oeuvre"]  * coeff * surface),
            "second_oeuvre_tnd": round(c["second_oeuvre"] * coeff * surface),
            "finitions_tnd":    round(c["finitions"]    * coeff * surface),
        },
        "total_tnd":       round(total),
        "prix_m2_tnd":     round(total_per_m2),
        "fourchette_basse": round(total * 0.90),
        "fourchette_haute": round(total * 1.15),
    }


def parse_request(msg: str) -> tuple[float, str, str]:
    """Extract surface, standing and city from free-text message."""
    import re
    surface = 100.0
    m = re.search(r"(\d+)\s*m[²2]", msg)
    if m:
        surface = float(m.group(1))

    standing = "intermédiaire"
    if "économique" in msg.lower() or "eco" in msg.lower():
        standing = "économique"
    elif "haut" in msg.lower() or "luxe" in msg.lower() or "premium" in msg.lower():
        standing = "haut_standing"

    city = "Tunis"
    for c in CITY_COEFF:
        if c.lower() in msg.lower():
            city = c
            break

    return surface, standing, city


def build_report(d: dict) -> str:
    det = d["detail"]
    return (
        f"## Devis Construction — {d['surface_m2']} m² à {d['city']}\n\n"
        f"**Standing:** {d['standing']}  |  **Coeff localisation:** {d['coeff_localisation']}\n\n"
        f"### Décomposition des coûts\n"
        f"| Poste | Montant |\n"
        f"|---|---|\n"
        f"| Gros œuvre | {det['gros_oeuvre_tnd']:,} TND |\n"
        f"| Second œuvre | {det['second_oeuvre_tnd']:,} TND |\n"
        f"| Finitions | {det['finitions_tnd']:,} TND |\n\n"
        f"### Estimation totale\n"
        f"- **Prix au m²:** {d['prix_m2_tnd']:,} TND/m²\n"
        f"- **Total estimé:** {d['total_tnd']:,} TND\n"
        f"- **Fourchette:** {d['fourchette_basse']:,} — {d['fourchette_haute']:,} TND\n\n"
        f"*Estimation basée sur les prix du marché tunisien 2025.*"
    )


@app.post("/chat")
def chat(req: ChatRequest):
    surface, standing, city = parse_request(req.message)
    d = estimate(surface, standing, city)
    return {
        "texte":      build_report(d),
        "devis":      d,
        "session_id": req.session_id,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "devis-standalone"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8009)
