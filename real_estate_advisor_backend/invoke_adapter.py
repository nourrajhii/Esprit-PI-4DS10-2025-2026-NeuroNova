"""
/invoke adapter for real_estate_advisor_backend.
Mounts the existing advisor router — entry point for Docker.
Now backed by MongoDB Atlas instead of MySQL.
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from app.routes.advisor import router as advisor_router, AptAdapter
from app.database import get_db

app = FastAPI(title="Advisor + /invoke")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(advisor_router)


class InvokeRequest(BaseModel):
    input: dict
    context: dict = {}


@app.post("/invoke")
def invoke(req: InvokeRequest, col=Depends(get_db)):
    from app.services.prompt_parser_service import parse_user_prompt
    from app.services.prompt_recommendation_service import filter_apartments_by_criteria
    from app.services.scoring_service_v2 import compute_smart_score
    from app.services.market_insights_service import get_market_insights
    from app.services.prompt_response_service import generate_natural_response
    from app.services.apartment_quality_service import is_valid_apartment_for_recommendation

    prompt = req.input.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="input.prompt is required")

    try:
        criteria = parse_user_prompt(prompt)

        docs = list(col.find({}, limit=2000))
        if not docs:
            return {"output": {"natural_response": "Aucun bien disponible.", "properties": [], "total_found": 0}, "agent": "recommender", "confidence": 0.5}

        all_apts = [AptAdapter(d) for d in docs]
        filtered = [a for a in filter_apartments_by_criteria(all_apts, criteria) if is_valid_apartment_for_recommendation(a)]

        market_data = get_market_insights(col)
        if "error" in market_data:
            market_data = {}

        scored = sorted(
            [(a, compute_smart_score(a, criteria, market_data) if market_data else 0.0) for a in filtered],
            key=lambda x: x[1], reverse=True
        )[:int(criteria.get("top_k") or 5)]

        properties = []
        for apt, score in scored:
            surface = apt.surface_m2
            price = apt.price
            properties.append({
                "id":             apt.id,
                "title":          apt.title,
                "price":          price,
                "city":           apt.city,
                "surface_m2":     surface,
                "size":           surface,
                "rooms":          apt.rooms,
                "bathrooms":      apt.bathrooms,
                "transaction_type": apt.transaction_type,
                "url":            apt.url,
                "image_urls":     apt.image_urls,
                "score":          round(score, 2),
                "price_per_m2":   round(price / surface, 2) if surface > 0 else None,
            })

        natural, advice = generate_natural_response(criteria, properties, None)
        return {
            "output": {
                "natural_response":   natural,
                "advice":             advice,
                "properties":         properties,
                "total_found":        len(properties),
                "is_real_estate_query": True,
            },
            "agent": "recommender",
            "confidence": 0.90,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", "agent": "recommender"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
