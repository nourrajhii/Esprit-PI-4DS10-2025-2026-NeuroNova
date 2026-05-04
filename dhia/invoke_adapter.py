"""
Thin /invoke adapter for dhia price-predictor + investment-scorer.
Wraps existing api.py logic without touching core files.
Run: uvicorn invoke_adapter:app --host 0.0.0.0 --port 8005
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn, sys, os

sys.path.insert(0, os.path.dirname(__file__))
from rag_backend import run_prediction_agent, run_investment_agent

app = FastAPI(title="Dhia Price+Investment /invoke adapter")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class InvokeRequest(BaseModel):
    input: dict
    context: dict = {}


@app.post("/invoke")
def invoke(req: InvokeRequest):
    intent = req.input.get("intent", "predict")
    try:
        if intent == "invest":
            data = run_investment_agent(
                budget=req.input["budget"],
                city=req.input.get("city")
            )
            return {"output": data, "agent": "investment-scorer", "confidence": 0.85}
        else:
            data = run_prediction_agent(
                city=req.input["city"],
                surface=req.input["surface_m2"],
                rooms=req.input.get("rooms", 3),
                baths=req.input.get("bathrooms", 1),
                tier=req.input.get("city_tier", 2)
            )
            return {"output": data, "agent": "price-predictor", "confidence": 0.80}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", "agent": "dhia"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8055)
