from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.prompt_schema import PromptRequest, PromptAdvisorResponse
from app.services.prompt_parser_service import parse_user_prompt
from app.services.prompt_recommendation_service import filter_apartments_by_criteria
from app.services.prompt_response_service import generate_natural_response
from app.services.recommendation_service import recommend_apartments
from app.services.scoring_service import compute_apartment_score
from app.models.apartment import Apartment
from app.services.market_insights_service import get_market_insights
from app.database import get_db
from app.services.recommendation_service import recommend_apartments_from_prompt
from app.services.apartment_classifier_service import classify_apartment_listing 
router = APIRouter(prefix="/advisor", tags=["Advisor"])
 
 
import traceback

@router.post("/prompt", response_model=PromptAdvisorResponse)
def advisor_from_prompt(payload: PromptRequest, db: Session = Depends(get_db)):
    try:
        # 1. Parser le prompt utilisateur avec Ollama
        criteria = parse_user_prompt(payload.prompt)

        # 2. Charger tous les biens
        all_apts = db.query(Apartment).all()

        # 3. Filtrage intelligent initial
        filtered_apts = filter_apartments_by_criteria(all_apts, criteria)

        # 4. Fallback progressif si aucun résultat
        if not filtered_apts:
            relaxed_criteria = criteria.copy()
            relaxed_criteria["transaction_type"] = None
            filtered_apts = filter_apartments_by_criteria(all_apts, relaxed_criteria)

        if not filtered_apts:
            relaxed_criteria = criteria.copy()
            relaxed_criteria["allowed_property_types"] = []
            filtered_apts = filter_apartments_by_criteria(all_apts, relaxed_criteria)

        if not filtered_apts:
            relaxed_criteria = criteria.copy()
            relaxed_criteria["city"] = None
            filtered_apts = filter_apartments_by_criteria(all_apts, relaxed_criteria)

        # 5. Charger les market insights
        market_data = get_market_insights(db)
        if "error" in market_data:
            raise HTTPException(status_code=404, detail=market_data["error"])

        # 6. Recommandation des meilleurs biens
        recommended_apts = recommend_apartments_from_prompt(
    criteria=criteria,
    all_apts=filtered_apts,
    market_data=market_data,
    limit=criteria.get("top_k", 5)
)

        # 7. Transformer en dictionnaires pour la réponse
        recommended_dicts = [
    {
        "id": a.id,
        "title": a.title,
        "price": float(a.price or 0),
        "city": a.city,
        "property_type": a.property_type,
        "surface_m2": float(a.surface_m2 or 0),
        "rooms": int(a.rooms or 0),
        "bathrooms": int(a.bathrooms or 0),
        "transaction_type": a.transaction_type,
        "url": a.url,
        "detected_category": classify_apartment_listing(a.title, a.property_type, a.url)["category"],
        "detected_sub_type": classify_apartment_listing(a.title, a.property_type, a.url)["sub_type"]
    }
    for a in recommended_apts
]
        # 8. Comparaison optionnelle
        comparison_result = None

        if criteria.get("compare") and len(recommended_apts) >= 2:
            a = recommended_apts[0]
            b = recommended_apts[1]
            budget = criteria.get("budget_max") or 999999999

            score_a = compute_apartment_score(
                float(a.price or 0),
                budget,
                float(a.surface_m2 or 0),
                int(a.rooms or 0),
                int(a.bathrooms or 0),
            )

            score_b = compute_apartment_score(
                float(b.price or 0),
                budget,
                float(b.surface_m2 or 0),
                int(b.rooms or 0),
                int(b.bathrooms or 0),
            )

            comparison_result = {
                "apartment_a_id": a.id,
                "apartment_b_id": b.id,
                "score_a": score_a,
                "score_b": score_b,
                "recommended_apartment_id": a.id if score_a >= score_b else b.id
            }

        # 9. Réponse naturelle
        natural_response = generate_natural_response(criteria, recommended_dicts, comparison_result)

        return {
            "parsed_criteria": criteria,
            "recommended_apartments": recommended_dicts,
            "comparison_result": comparison_result,
            "natural_response": natural_response
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"advisor_from_prompt failed: {str(e)}")
@router.get("/debug/property-types")
def debug_property_types(db: Session = Depends(get_db)):
    all_apts = db.query(Apartment).all()

    values = sorted(list({
        (a.property_type or "").strip()
        for a in all_apts
        if a.property_type
    }))

    return {"property_types": values[:200]}


@router.get("/debug/cities")
def debug_cities(db: Session = Depends(get_db)):
    all_apts = db.query(Apartment).all()

    values = sorted(list({
        (a.city or "").strip()
        for a in all_apts
        if a.city
    }))

    return {"cities": values[:200]}


@router.get("/debug/transaction-types")
def debug_transaction_types(db: Session = Depends(get_db)):
    all_apts = db.query(Apartment).all()

    values = sorted(list({
        (a.transaction_type or "").strip()
        for a in all_apts
        if a.transaction_type
    }))

    return {"transaction_types": values[:200]}