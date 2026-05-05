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
    raw_surface = getattr(a, "surface_m2", None)
    surface = float(raw_surface) if raw_surface is not None else None

    if not title or len(title) < 5:
        return False

    if title in BAD_TITLES:
        return False

    if title.startswith("v") and len(title) <= 5:
        return False

    if "annonces" in title and "immobilier" in title:
        return False

    if price <= 0:
        return False

    # Surface NULL is allowed (terrains often have no surface in the data)
    if surface is not None and surface == 0:
        return False

    # Valeurs aberrantes — only apply when surface is known
    if surface is not None and surface > 5000 and price < 5000:
        return False

    return True