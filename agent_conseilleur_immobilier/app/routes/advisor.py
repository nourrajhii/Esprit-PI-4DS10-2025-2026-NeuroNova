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