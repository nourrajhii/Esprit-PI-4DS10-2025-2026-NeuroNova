from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.apartment import Apartment
from app.models.quote import Quote
from app.models.recommendation import Recommendation
from app.schemas.advisor_schema import CompareRequest, CompareResponse
from app.schemas.quote_schema import QuoteRequest, QuoteResponse
from app.services.scoring_service import compute_apartment_score
from app.services.quote_service import estimate_quote
import traceback
from fastapi import HTTPException
from app.schemas.price_prediction_schema import (
    PricePredictionRequest,
    PricePredictionResponse,
    ModelInfoResponse
)
from app.services.price_prediction_service import predict_price, get_model_info
from app.schemas.recommendation_schema_v2 import RecommendRequest, RecommendResponse
from app.services.recommendation_service_v2 import get_recommendations
from app.schemas.market_insights_schema import MarketInsightsResponse
from app.services.market_insights_service import get_market_insights
from app.routes.advisor import router as advisor_router
from typing import List


router = APIRouter(prefix="/advisor", tags=["Advisor"])


@router.post("/compare", response_model=CompareResponse)
def compare_apartments(payload: CompareRequest, db: Session = Depends(get_db)):
    apartment_a = db.query(Apartment).filter(Apartment.id == payload.apartment_a_id).first()
    apartment_b = db.query(Apartment).filter(Apartment.id == payload.apartment_b_id).first()

    if not apartment_a or not apartment_b:
        raise HTTPException(status_code=404, detail="Un ou deux appartements sont introuvables.")

    score_a = compute_apartment_score(
        float(apartment_a.price),
        payload.budget,
        float(apartment_a.surface_m2 or 0),
        int(apartment_a.rooms or 0),
        int(apartment_a.bathrooms or 0),
    )

    score_b = compute_apartment_score(
        float(apartment_b.price),
        payload.budget,
        float(apartment_b.surface_m2 or 0),
        int(apartment_b.rooms or 0),
        int(apartment_b.bathrooms or 0),
    )

    total_cost_a = float(apartment_a.price)
    total_cost_b = float(apartment_b.price)

    details = {
        "budget_ok_a": total_cost_a <= payload.budget,
        "budget_ok_b": total_cost_b <= payload.budget,
        "price_diff": round(total_cost_a - total_cost_b, 2),
        "surface_ratio_a": round(float(apartment_a.surface_m2 or 0) / float(apartment_a.price or 1), 6),
        "surface_ratio_b": round(float(apartment_b.surface_m2 or 0) / float(apartment_b.price or 1), 6),
    }

    if score_a >= score_b:
        recommended_id = apartment_a.id
        reason = (
            f"Le bien A est recommandé avec un score de {score_a} contre {score_b} pour le bien B, "
            f"car il offre un meilleur équilibre entre budget, surface et confort."
        )
    else:
        recommended_id = apartment_b.id
        reason = (
            f"Le bien B est recommandé avec un score de {score_b} contre {score_a} pour le bien A, "
            f"car il offre un meilleur équilibre entre budget, surface et confort."
        )

    recommendation = Recommendation(
        user_id=payload.user_id,
        apartment_a_id=apartment_a.id,
        apartment_b_id=apartment_b.id,
        budget=payload.budget,
        score_a=score_a,
        score_b=score_b,
        recommended_apartment_id=recommended_id,
        reason_text=reason,
        total_cost_a=total_cost_a,
        total_cost_b=total_cost_b
    )

    db.add(recommendation)
    db.commit()

    return CompareResponse(
        apartment_a_id=apartment_a.id,
        apartment_b_id=apartment_b.id,
        score_a=score_a,
        score_b=score_b,
        total_cost_a=total_cost_a,
        total_cost_b=total_cost_b,
        recommended_apartment_id=recommended_id,
        reason=reason,
        details=details
    )


@router.post("/quote", response_model=QuoteResponse)
def generate_quote(payload: QuoteRequest, db: Session = Depends(get_db)):
    try:
        apartment = db.query(Apartment).filter(Apartment.id == payload.apartment_id).first()

        if not apartment:
            raise HTTPException(status_code=404, detail="Appartement introuvable.")

        result = estimate_quote(float(apartment.surface_m2 or 0), "medium")

        quote = Quote(
            user_id=payload.user_id,
            apartment_id=apartment.id,
            project_type=payload.project_type,
            surface_m2=float(apartment.surface_m2 or 0),
            subtotal_materials=float(result["subtotal_materials"]),
            subtotal_labor=float(result["subtotal_labor"]),
            subtotal_equipment=float(result["subtotal_equipment"]),
            contingency_cost=float(result["contingency_cost"]),
            total_cost=float(result["total_cost"])
        )

        db.add(quote)
        db.commit()
        db.refresh(quote)

        return QuoteResponse(
            apartment_id=apartment.id,
            project_type=payload.project_type,
            subtotal_materials=float(result["subtotal_materials"]),
            subtotal_labor=float(result["subtotal_labor"]),
            subtotal_equipment=float(result["subtotal_equipment"]),
            contingency_cost=float(result["contingency_cost"]),
            total_cost=float(result["total_cost"])
        )

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Quote generation failed: {str(e)}")
    
router = APIRouter(prefix="/advisor", tags=["Advisor"])

@router.post("/predict-price", response_model=PricePredictionResponse)
def predict_apartment_price(payload: PricePredictionRequest):
    try:
        # Appeler la fonction de prédiction de prix
        result = predict_price(
            surface_m2=payload.surface_m2,
            rooms=payload.rooms,
            bathrooms=payload.bathrooms,
            city=payload.city,
            property_type=payload.property_type,
            transaction_type=payload.transaction_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur dans la prédiction du prix : {str(e)}")
    
    # Retourner le résultat de la prédiction
    return result
 
@router.get("/model-info", response_model=ModelInfoResponse)
def get_prediction_model_info():
    """
    Retourne les métadonnées du modèle :
    villes connues, prix min/max/moyen, prix au m² médian du marché.
    """
    try:
        return get_model_info()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
@router.post("/recommend", response_model=List[Apartment])
def recommend_apartments_route(budget: float, db: Session = Depends(get_db)):
    """
    Cette route recommande des appartements en fonction du budget de l'utilisateur et de leur score.
    """
    all_apts = db.query(Apartment).all()  # Récupère tous les appartements de la base
    market_data = get_market_insights(db)  # Récupère les statistiques du marché

    recommended_apts = recommend_apartments(budget, all_apts, "Tunis", market_data)

    return recommended_apts
@router.get("/market-insights", response_model=MarketInsightsResponse)
def market_insights(db: Session = Depends(get_db)):
    """
    Analyse complète du marché immobilier basée sur les données de la BDD.
 
    Retourne :
    - **global_stats** : prix moyen, médian, prix/m², surface moyenne
    - **distribution_prix** : répartition des biens par tranche de prix
    - **stats_par_rooms** : statistiques par nombre de pièces
    - **top_opportunites** : 5 biens avec le meilleur rapport surface/prix
    - **top_premium** : 5 biens avec le prix/m² le plus élevé
    - **market_indicators** : % biens premium, % accessibles, fourchette typique
    """
    result = get_market_insights(db)
 
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
 
    return result
 