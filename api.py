from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from rag_backend import run_prediction_agent, run_investment_agent

app = FastAPI(title="EstateMind AI API")

# Enable CORS for the Vitrine page
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PricingRequest(BaseModel):
    city: str
    surface_m2: float
    rooms: int
    bathrooms: int
    city_tier: int

class InvestmentRequest(BaseModel):
    budget: float
    city: str = None

@app.post("/api/predict")
def predict_price(req: PricingRequest):
    try:
        res = run_prediction_agent(
            city=req.city,
            surface=req.surface_m2,
            rooms=req.rooms,
            baths=req.bathrooms,
            tier=req.city_tier
        )
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/invest")
def invest(req: InvestmentRequest):
    try:
        res = run_investment_agent(budget=req.budget, city=req.city)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
