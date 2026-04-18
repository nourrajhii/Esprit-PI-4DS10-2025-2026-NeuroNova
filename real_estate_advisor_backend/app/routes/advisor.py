"""
routes/advisor.py — Endpoint principal de l'agent conseiller immobilier.

Contrat de sortie /advisor/prompt :
{
  "natural_response": str,
  "advice":           str,
  "criteria":         dict,
  "is_real_estate_query": bool,
  "properties":       list[dict],
  "total_found":      int,
  "market_stats":     dict,
}
"""
import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.apartment import Apartment
from app.schemas.prompt_schema import PromptRequest, PromptAdvisorResponse
from app.services.apartment_classifier_service import classify_apartment_listing
from app.services.apartment_quality_service import is_valid_apartment_for_recommendation
from app.services.listing_feature_service import detect_rooms_from_text
from app.services.market_insights_service import get_market_insights
from app.services.ollama_service import check_ollama_health
from app.services.prompt_parser_service import parse_user_prompt
from app.services.prompt_recommendation_service import filter_apartments_by_criteria
from app.services.prompt_response_service import generate_natural_response
from app.services.scoring_service_v2 import compute_smart_score
from app.services.text_normalizer_service import normalize_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advisor", tags=["Advisor"])


# ── Helpers ───────────────────────────────────────────────────────────────────
def _format_transaction_label(value: str | None) -> str | None:
    """Normalise la transaction_type pour l'affichage frontend."""
    if not value:
        return None
    v = value.lower()
    if "location" in v or "louer" in v:
        return "À Louer"
    if "vente" in v or "vendre" in v:
        return "À Vendre"
    return value


def _normalize_transaction_from_context(
    transaction_type: str | None,
    title: str,
    url: str,
) -> str:
    """
    Déduit la transaction_type la plus probable en croisant
    la valeur ORM, le titre et l'URL de l'annonce.
    """
    sources = " ".join([
        normalize_text(transaction_type or ""),
        normalize_text(title or ""),
        normalize_text(url or ""),
    ])
    if any(kw in sources for kw in ["location", "louer", "a louer"]):
        return "À Louer"
    return "À Vendre"


def _build_property_dict(apt, score: float) -> dict:
    """Convertit un objet Apartment ORM + score en dict sérialisable."""
    raw_title = apt.title or ""
    raw_url   = apt.url   or ""
    raw_type  = apt.property_type or ""

    listing_class  = classify_apartment_listing(raw_title, raw_type, raw_url)
    detected_rooms = detect_rooms_from_text(raw_title)
    final_rooms    = detected_rooms if detected_rooms is not None else int(apt.rooms or 0)

    price   = float(apt.price    or 0)
    surface = float(apt.surface_m2 or 0)
    ppm2    = round(price / surface, 2) if surface > 0 else None

    transaction = _normalize_transaction_from_context(
        apt.transaction_type, raw_title, raw_url
    )

    return {
        "id":                str(apt.id),
        "title":             raw_title,
        "price":             price,
        "city":              apt.city,
        "region":            apt.city,       # région = ville si non disponible séparément
        "property_type":     listing_class["sub_type"] or listing_class["category"],
        "surface_m2":        surface,
        "size":              surface,         # alias pour compatibilité frontend
        "rooms":             final_rooms,
        "room_count":        final_rooms,     # alias
        "bathrooms":         int(apt.bathrooms or 0),
        "bathroom_count":    int(apt.bathrooms or 0),  # alias
        "transaction_type":  transaction,
        "url":               raw_url,
        "listing_url":       raw_url,         # alias
        "category":          listing_class["category"],
        "detected_category": listing_class["category"],
        "detected_sub_type": listing_class["sub_type"],
        "price_per_m2":      ppm2,
        "score":             round(score, 2),
    }


def _compute_market_stats(properties: list[dict]) -> dict:
    """Calcule les statistiques de marché sur les résultats renvoyés."""
    prices   = [p["price"] for p in properties if p.get("price")]
    surfaces = [p["size"]  for p in properties if p.get("size")]
    ppm2     = [p["price_per_m2"] for p in properties if p.get("price_per_m2")]

    if not prices:
        return {}

    sorted_p = sorted(prices)
    n = len(sorted_p)

    return {
        "avg_price":        round(sum(prices) / n, 2),
        "min_price":        min(prices),
        "max_price":        max(prices),
        "median_price":     sorted_p[n // 2],
        "avg_size":         round(sum(surfaces) / len(surfaces), 2) if surfaces else None,
        "avg_price_per_m2": round(sum(ppm2) / len(ppm2), 2) if ppm2 else None,
        "count":            n,
    }


def _build_criteria_output(criteria: dict) -> dict:
    """Formate les critères pour la réponse JSON finale."""
    return {
        "transaction_type": _format_transaction_label(criteria.get("transaction_type")),
        "category":         criteria.get("category"),
        "city":             criteria.get("city"),
        "region":           None,
        "min_price":        criteria.get("budget_min"),
        "max_price":        criteria.get("budget_max"),
        "rooms":            criteria.get("rooms"),
        "min_size":         None,
        "max_size":         None,
    }


# ── Pipeline de filtrage avec relaxations progressives ───────────────────────
def _filter_with_fallbacks(
    all_apts: list,
    criteria: dict,
) -> list:
    """
    Applique le filtrage strict puis des relaxations progressives
    jusqu'à obtenir des résultats valides.
    """
    def _valid(apts):
        return [a for a in apts if is_valid_apartment_for_recommendation(a)]

    # Filtre strict
    result = _valid(filter_apartments_by_criteria(all_apts, criteria))
    if result:
        return result

    # Relaxation 1 : budget +25 %
    logger.info("[Advisor] Fallback 1 — budget +25 %")
    r1 = criteria.copy()
    if r1.get("budget_max"):
        r1["budget_max"] = r1["budget_max"] * 1.25
    result = _valid(filter_apartments_by_criteria(all_apts, r1))
    if result:
        return result

    # Relaxation 2 : tolérance sur les pièces
    logger.info("[Advisor] Fallback 2 — tolérance pièces ±1")
    r2 = criteria.copy()
    if r2.get("rooms") is not None:
        r2["rooms_tolerance"] = 1
    result = _valid(filter_apartments_by_criteria(all_apts, r2))
    if result:
        return result

    # Relaxation 3 : sous-type moins strict
    logger.info("[Advisor] Fallback 3 — sous-type relâché")
    r3 = criteria.copy()
    r3["allowed_property_types"] = []
    result = _valid(filter_apartments_by_criteria(all_apts, r3))
    if result:
        return result

    # Relaxation 4 : ignorer la ville
    logger.info("[Advisor] Fallback 4 — ville ignorée")
    r4 = criteria.copy()
    r4["city"] = None
    result = _valid(filter_apartments_by_criteria(all_apts, r4))
    return result  # vide = aucun résultat possible


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post("/prompt", response_model=PromptAdvisorResponse)
def advisor_from_prompt(payload: PromptRequest, db: Session = Depends(get_db)):
    """
    Analyse un prompt en langage naturel (fr / darija / mélange) et
    retourne les biens les mieux adaptés avec réponse explicative.
    """
    try:
        # 1. Extraction des critères (Ollama + fallbacks regex)
        criteria = parse_user_prompt(payload.prompt)
        logger.info(f"[Advisor] Critères extraits : {criteria}")

        # 2. Demande hors-immobilier
        if criteria.get("is_real_estate_query") is False:
            return {
                "natural_response":   "Votre demande ne semble pas liée à l'immobilier.",
                "advice":             "Essayez une recherche comme : appartement à louer à Tunis, villa à vendre à Nabeul ou terrain à Sousse.",
                "criteria":           {},
                "is_real_estate_query": False,
                "properties":         [],
                "total_found":        0,
                "market_stats":       {},
            }

        # 3. Charger les biens
        all_apts = db.query(Apartment).all()
        if not all_apts:
            raise HTTPException(status_code=503, detail="Aucun bien en base de données.")

        # 4. Filtrage + relaxations
        filtered = _filter_with_fallbacks(all_apts, criteria)

        # 5. Aucun résultat après tous les fallbacks
        if not filtered:
            natural, advice = generate_natural_response(criteria, [], None)
            return {
                "natural_response":   natural,
                "advice":             advice,
                "criteria":           _build_criteria_output(criteria),
                "is_real_estate_query": True,
                "properties":         [],
                "total_found":        0,
                "market_stats":       {},
            }

        # 6. Scoring intelligent
        market_data = get_market_insights(db)
        if "error" in market_data:
            market_data = {}

        scored = sorted(
            [(a, compute_smart_score(a, criteria, market_data) if market_data else 0.0)
             for a in filtered],
            key=lambda x: x[1],
            reverse=True,
        )

        # 7. Top-k
        top_k      = max(1, int(criteria.get("top_k") or 5))
        top_scored = scored[:top_k]

        # 8. Construction des dicts de résultats
        properties = [_build_property_dict(a, s) for a, s in top_scored]

        # 9. Réponse naturelle
        natural, advice = generate_natural_response(criteria, properties, None)

        return {
            "natural_response":   natural,
            "advice":             advice,
            "criteria":           _build_criteria_output(criteria),
            "is_real_estate_query": True,
            "properties":         properties,
            "total_found":        len(properties),
            "market_stats":       _compute_market_stats(properties),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Advisor] Erreur inattendue : {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"advisor_from_prompt failed: {str(e)}")


@router.get("/market-insights")
def market_insights(db: Session = Depends(get_db)):
    """Statistiques globales du marché immobilier."""
    data = get_market_insights(db)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.get("/health")
def advisor_health():
    """Vérifie la connexion à Ollama."""
    return check_ollama_health()