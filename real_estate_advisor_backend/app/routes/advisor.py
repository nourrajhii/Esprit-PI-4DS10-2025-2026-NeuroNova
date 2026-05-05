"""
routes/advisor.py — Endpoint principal de l'agent conseiller immobilier.
Now backed by MongoDB Atlas (dcrawl.listings) instead of MySQL.

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
from pymongo.collection import Collection

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from app.database import get_db
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


# ── Thin adapter: wraps a MongoDB dict as attribute-accessible object ─────────
class AptAdapter:
    """Wraps a MongoDB listing document so existing services can access .price etc."""
    def __init__(self, doc: dict):
        self._doc = doc
        raw_id = doc.get("_id", "")
        self.id = str(raw_id)
        self.title = doc.get("title", "") or ""
        self.price = float(doc.get("price") or 0)
        self.city = doc.get("city") or doc.get("zone") or ""
        self.property_type = doc.get("property_type") or ""
        self.surface_m2 = float(doc.get("surface_m2") or 0)
        self.url = doc.get("listing_url") or doc.get("url") or ""
        self.image_urls = doc.get("image_urls") or []
        self.description = doc.get("description") or ""

        # Infer transaction_type from title/url when DB field is missing
        raw_tx = doc.get("transaction_type") or ""
        if not raw_tx:
            t = (self.title + " " + self.url).lower()
            if any(x in t for x in ["à louer", "a louer", "location", "louer", "rent"]):
                raw_tx = "location"
            elif any(x in t for x in ["à vendre", "a vendre", "vente", "vendre", "sale"]):
                raw_tx = "vente"
        self.transaction_type = raw_tx

        # Extract rooms from S+N notation in title when DB field is 0
        raw_rooms = int(doc.get("rooms") or 0)
        if raw_rooms == 0:
            import re as _re
            m = _re.search(r"\bs\+?\s*(\d)\b", self.title.lower())
            if m:
                raw_rooms = int(m.group(1))
            else:
                m2 = _re.search(r"(\d+)\s*(?:chambre|pièce|piece)", self.title.lower())
                if m2:
                    raw_rooms = int(m2.group(1))
        self.rooms = raw_rooms

        # Extract surface from title when DB field is 0
        raw_surf = float(doc.get("surface_m2") or 0)
        if raw_surf == 0:
            import re as _re
            m = _re.search(r"(\d+)\s*m[²2]", self.title)
            if m:
                raw_surf = float(m.group(1))
        self.surface_m2 = raw_surf

        self.bathrooms = int(doc.get("bathrooms") or 0)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _format_transaction_label(value: str | None) -> str | None:
    if not value:
        return None
    v = value.lower()
    if "location" in v or "louer" in v or "rent" in v:
        return "À Louer"
    if "vente" in v or "vendre" in v or "sale" in v or "vend" in v:
        return "À Vendre"
    return value


def _normalize_transaction_from_context(
    transaction_type: str | None,
    title: str,
    url: str,
) -> str:
    sources = " ".join([
        normalize_text(transaction_type or ""),
        normalize_text(title or ""),
        normalize_text(url or ""),
    ])
    if any(kw in sources for kw in ["location", "louer", "a louer", "rent"]):
        return "À Louer"
    return "À Vendre"


def _build_property_dict(apt: AptAdapter, score: float) -> dict:
    raw_title = apt.title or ""
    raw_url   = apt.url   or ""
    raw_type  = apt.property_type or ""

    listing_class  = classify_apartment_listing(raw_title, raw_type, raw_url)
    detected_rooms = detect_rooms_from_text(raw_title)
    final_rooms    = detected_rooms if detected_rooms is not None else apt.rooms

    price   = apt.price
    surface = apt.surface_m2
    ppm2    = round(price / surface, 2) if surface > 0 else None

    transaction = _normalize_transaction_from_context(
        apt.transaction_type, raw_title, raw_url
    )

    return {
        "id":                apt.id,
        "title":             raw_title,
        "price":             price,
        "city":              apt.city,
        "region":            apt.city,
        "property_type":     listing_class["sub_type"] or listing_class["category"],
        "surface_m2":        surface,
        "size":              surface,
        "rooms":             final_rooms,
        "room_count":        final_rooms,
        "bathrooms":         apt.bathrooms,
        "bathroom_count":    apt.bathrooms,
        "transaction_type":  transaction,
        "url":               raw_url,
        "listing_url":       raw_url,
        "category":          listing_class["category"],
        "detected_category": listing_class["category"],
        "detected_sub_type": listing_class["sub_type"],
        "price_per_m2":      ppm2,
        "score":             round(score, 2),
        "image_urls":        apt.image_urls,
        "description":       apt.description,
    }


def _compute_market_stats(properties: list[dict]) -> dict:
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


# ── Progressive-relaxation filter pipeline ───────────────────────────────────
_RELAXATION_NOTE = ""  # module-level, reset per request


def _filter_with_fallbacks(all_apts: list, criteria: dict) -> tuple[list, str]:
    """Returns (results, relaxation_note)."""
    global _RELAXATION_NOTE
    _RELAXATION_NOTE = ""

    def _valid(apts):
        return [a for a in apts if is_valid_apartment_for_recommendation(a)]

    result = _valid(filter_apartments_by_criteria(all_apts, criteria))
    if result:
        return result, ""

    # Fallback 1 — rooms tolerance ±1 (keep budget strict)
    logger.info("[Advisor] Fallback 1 — tolérance pièces ±1")
    r1 = criteria.copy()
    if r1.get("rooms") is not None:
        r1["rooms_tolerance"] = 1
    result = _valid(filter_apartments_by_criteria(all_apts, r1))
    if result:
        note = "Certains résultats ont ±1 pièce(s) par rapport à votre demande." if criteria.get("rooms") else ""
        return result, note

    # Fallback 2 — sous-type relâché (keep city + budget strict)
    logger.info("[Advisor] Fallback 2 — sous-type relâché")
    r2 = r1.copy()
    r2["allowed_property_types"] = []
    result = _valid(filter_apartments_by_criteria(all_apts, r2))
    if result:
        return result, "Le type de bien a été élargi pour trouver des alternatives proches."

    # Fallback 3 — budget +15 % (only if budget was set)
    if criteria.get("budget_max"):
        logger.info("[Advisor] Fallback 3 — budget +15 %")
        r3 = r2.copy()
        r3["budget_max"] = criteria["budget_max"] * 1.15
        r3["rooms_tolerance"] = 1
        result = _valid(filter_apartments_by_criteria(all_apts, r3))
        if result:
            return result, f"Aucun bien trouvé dans votre budget strict. Les résultats affichés sont jusqu'à 15 % au-dessus de votre budget de {int(criteria['budget_max']):,} DT.".replace(",", " ")

    # Fallback 4 — ville ignorée
    logger.info("[Advisor] Fallback 4 — ville ignorée")
    r4 = r2.copy()
    r4["city"] = None
    result = _valid(filter_apartments_by_criteria(all_apts, r4))
    city = criteria.get("city", "")
    note = f"Aucun bien trouvé à {city}. Voici des biens similaires dans d'autres villes." if city else ""
    return result, note


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post("/prompt", response_model=PromptAdvisorResponse)
def advisor_from_prompt(payload: PromptRequest, col: Collection = Depends(get_db)):
    try:
        criteria = parse_user_prompt(payload.prompt)
        logger.info(f"[Advisor] Critères extraits : {criteria}")

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

        # Load listings from MongoDB (cap at 3000 for better coverage)
        docs = list(col.find({}, limit=3000))
        if not docs:
            raise HTTPException(status_code=503, detail="Aucun bien en base de données.")

        all_apts = [AptAdapter(d) for d in docs]

        filtered, relaxation_note = _filter_with_fallbacks(all_apts, criteria)

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

        market_data = get_market_insights(col)
        if "error" in market_data:
            market_data = {}

        scored = sorted(
            [(a, compute_smart_score(a, criteria, market_data) if market_data else 0.0)
             for a in filtered],
            key=lambda x: x[1],
            reverse=True,
        )

        top_k      = max(1, int(criteria.get("top_k") or 8))
        top_scored = scored[:top_k]

        properties = [_build_property_dict(a, s) for a, s in top_scored]
        natural, advice = generate_natural_response(criteria, properties, None)

        # Prepend relaxation note so user knows when criteria were loosened
        if relaxation_note:
            natural = f"⚠️ {relaxation_note}\n\n{natural}"

        return {
            "natural_response":   natural,
            "advice":             advice,
            "criteria":           _build_criteria_output(criteria),
            "is_real_estate_query": True,
            "properties":         properties,
            "total_found":        len(filtered),
            "market_stats":       _compute_market_stats(properties),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Advisor] Erreur inattendue : {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"advisor_from_prompt failed: {str(e)}")


@router.get("/market-insights")
def market_insights(col: Collection = Depends(get_db)):
    data = get_market_insights(col)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data


@router.get("/health")
def advisor_health():
    return check_ollama_health()
