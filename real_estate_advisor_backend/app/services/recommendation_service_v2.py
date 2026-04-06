from typing import List
from sqlalchemy.orm import Session
from app.models.apartment import Apartment
 
 
W_BUDGET  = 0.40
W_SURFACE = 0.25
W_ROOMS   = 0.20
W_CITY    = 0.10
W_BATHS   = 0.05
 
 
def _score_budget(price: float, budget: float) -> float:
    if price <= 0:
        return 0.0
    if price <= budget:
        ratio = price / budget
        return 0.6 + 0.4 * ratio
    else:
        overflow = (price - budget) / budget
        return max(0.0, 1.0 - overflow * 2)
 
 
def _score_surface(apt_surface: float, wanted: float) -> float:
    if apt_surface <= 0 or wanted <= 0:
        return 0.0
    ratio = apt_surface / wanted
    if 0.7 <= ratio <= 1.3:
        return 1.0 - abs(1.0 - ratio) / 0.3
    elif ratio < 0.7:
        return max(0.0, ratio / 0.7 * 0.5)
    else:
        return max(0.0, 1.0 - (ratio - 1.3) / 2)
 
 
def _score_rooms(apt_rooms: int, wanted: int) -> float:
    diff = abs(apt_rooms - wanted)
    if diff == 0:   return 1.0
    if diff == 1:   return 0.7
    if diff == 2:   return 0.4
    return max(0.0, 0.2 - diff * 0.05)
 
 
def _score_city(apt_city: str, wanted: str) -> float:
    if not apt_city or not wanted:
        return 0.3
    return 1.0 if apt_city.strip().lower() == wanted.strip().lower() else 0.3
 
 
def _score_bathrooms(apt_baths: int, wanted: int) -> float:
    return max(0.0, 1.0 - abs(apt_baths - wanted) * 0.3)
 
 
BLACKLIST_TITLES = {
    "propos de ce bien", "dcouvrez des annonces immobilires",
    "les plus rcentes.", "ballouchi.com",
    "liste des maisons ou villas vendre",
    "liste locaux commerciaux et bureaux vendre",
    "liste des appartements vendre", "liste des villas vendre",
    "proprits vendre", "vente", "dtail du bien",
    "liste des terrains vendre", "terrain vendre",
    "les annonces des locaux commerciaux vendre",
    "les annonces des locaux pour professionnels vendre",
    "ayoub immobilier hammamet",
}
 
 
def _is_valid(apt, transaction_type: str) -> bool:
    title = (apt.title or "").lower().strip()
    if any(bl in title for bl in BLACKLIST_TITLES):
        return False
    price   = float(apt.price      or 0)
    surface = float(apt.surface_m2 or 0)
    rooms   = int(apt.rooms        or 0)
    if price   < 50_000:  return False
    if surface < 30 or surface > 5000: return False
    if rooms   > 20:      return False
    if transaction_type:
        if transaction_type.lower() not in (apt.transaction_type or "").lower():
            return False
    return True
 
 
def get_recommendations(
    db: Session,
    budget: float,
    surface_m2: float,
    rooms: int,
    city: str,
    bathrooms: int = 1,
    transaction_type: str = "vente",
    top_n: int = 5,
) -> List[dict]:
    """
    Scoring multi-critères pondéré :
      budget 40% | surface 25% | pièces 20% | ville 10% | sdb 5%
    """
    all_apts = db.query(Apartment).limit(2000).all()
    valid    = [a for a in all_apts if _is_valid(a, transaction_type)]
 
    if not valid:
        return []
 
    scored = []
    for apt in valid:
        price     = float(apt.price      or 0)
        surface   = float(apt.surface_m2 or 0)
        apt_rooms = int(apt.rooms        or 0)
        apt_baths = int(apt.bathrooms    or 0)
 
        sb = _score_budget(price, budget)
        ss = _score_surface(surface, surface_m2)
        sr = _score_rooms(apt_rooms, rooms)
        sc = _score_city(apt.city or "", city)
        sba= _score_bathrooms(apt_baths, bathrooms)
 
        total = W_BUDGET*sb + W_SURFACE*ss + W_ROOMS*sr + W_CITY*sc + W_BATHS*sba
 
        scored.append({
            "apartment":    apt,
            "score":        round(total * 100, 1),
            "budget_ok":    price <= budget,
            "score_detail": {
                "budget":  round(sb  * 100, 1),
                "surface": round(ss  * 100, 1),
                "rooms":   round(sr  * 100, 1),
                "city":    round(sc  * 100, 1),
                "baths":   round(sba * 100, 1),
            },
        })
 
    scored.sort(key=lambda x: x["score"], reverse=True)
 
    results = []
    for rank, item in enumerate(scored[:top_n], start=1):
        apt = item["apartment"]
        results.append({
            "rank":             rank,
            "score":            item["score"],
            "budget_ok":        item["budget_ok"],
            "score_detail":     item["score_detail"],
            "id":               apt.id,
            "title":            apt.title            or "",
            "price":            float(apt.price      or 0),
            "city":             apt.city             or "",
            "surface_m2":       float(apt.surface_m2 or 0),
            "rooms":            int(apt.rooms        or 0),
            "bathrooms":        int(apt.bathrooms    or 0),
            "transaction_type": apt.transaction_type or "",
            "url":              apt.url              or "",
            "price_diff":       round(float(apt.price or 0) - budget, 2),
        })
 
    return results
 