from app.services.text_normalizer_service import normalize_text

BAD_TITLES = [
    "vente",
    "location",
    "immobilier",
    "annonces",
    "decouvrez des annonces immobilieres",
    "dcouvrez des annonces immobilires",
    "v061",
    "v254",
    "v259"
]


def is_valid_apartment_for_recommendation(a) -> bool:
    title = normalize_text(getattr(a, "title", ""))
    price = float(getattr(a, "price", 0) or 0)
    surface = float(getattr(a, "surface_m2", 0) or 0)

    if not title or len(title) < 5:
        return False

    if title in BAD_TITLES:
        return False

    if title.startswith("v") and len(title) <= 5:
        return False

    if "annonces" in title and "immobilier" in title:
        return False

    if price <= 0 or surface <= 0:
        return False

    # Valeurs aberrantes
    if surface > 2000 and price < 20000:
        return False

    if price < 5000 and surface > 200:
        return False

    return True