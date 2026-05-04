"""
Thin /invoke adapter for nour devis agent.
Wraps existing /chat endpoint without touching core logic.
Run: uvicorn invoke_adapter:app --host 0.0.0.0 --port 8002
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx, uvicorn, os

app = FastAPI(title="Nour Devis /invoke adapter")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DEVIS_BASE = os.getenv("DEVIS_INTERNAL_URL", "http://localhost:8009")


class InvokeRequest(BaseModel):
    input: dict
    context: dict = {}


@app.post("/invoke")
async def invoke(req: InvokeRequest):
    message = req.input.get("message", "")
    session_id = req.context.get("session_id", "default")
    lang = req.context.get("lang", "fr")

    if not message:
        # Build message from structured input if provided
        surface = req.input.get("surface_m2")
        project_type = req.input.get("project_type", "construction")
        city = req.input.get("city", "Tunis")
        if surface:
            message = f"Devis pour {project_type} de {surface}m² à {city}"
        else:
            raise HTTPException(status_code=400, detail="input.message or input.surface_m2 required")

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{DEVIS_BASE}/chat",
                json={"message": message, "session_id": session_id}
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Devis agent unreachable: {e}")

    raw_devis = data.get("devis") or {}
    detail = raw_devis.get("detail", {})
    # Transform to the format expected by the frontend
    items = []
    if detail.get("gros_oeuvre_tnd"):
        items.append({"designation": "Gros œuvre", "unite": "m²", "quantite": raw_devis.get("surface_m2"), "prix_unitaire": None, "total": detail["gros_oeuvre_tnd"]})
    if detail.get("second_oeuvre_tnd"):
        items.append({"designation": "Second œuvre", "unite": "m²", "quantite": raw_devis.get("surface_m2"), "prix_unitaire": None, "total": detail["second_oeuvre_tnd"]})
    if detail.get("finitions_tnd"):
        items.append({"designation": "Finitions & équipements", "unite": "m²", "quantite": raw_devis.get("surface_m2"), "prix_unitaire": None, "total": detail["finitions_tnd"]})

    devis_out = {
        "total_estime":     raw_devis.get("total_tnd"),
        "surface_m2":       raw_devis.get("surface_m2"),
        "projet":           f"Construction {raw_devis.get('standing','intermédiaire')} à {raw_devis.get('city','Tunis')}",
        "items":            items,
        "note":             f"Fourchette: {raw_devis.get('fourchette_basse',0):,} — {raw_devis.get('fourchette_haute',0):,} TND · Coeff localisation {raw_devis.get('coeff_localisation',1)}",
    }

    return {
        "output": {
            "texte": data.get("texte", ""),
            "devis": devis_out,
            "session_id": data.get("session_id", session_id)
        },
        "agent": "devis",
        "confidence": 0.88
    }


@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get(f"{DEVIS_BASE}/health")
            return {"status": "ok", "upstream": r.json()}
        except Exception as e:
            return {"status": "degraded", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
