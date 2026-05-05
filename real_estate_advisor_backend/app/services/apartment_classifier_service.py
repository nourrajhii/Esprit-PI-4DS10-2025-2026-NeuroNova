"""
apartment_classifier_service.py — Classification automatique des annonces immobilières.

Détecte la catégorie (residential / commercial / land) et le sous-type
(appartement, villa, maison, studio, duplex, terrain, bureau, local_commercial…)
à partir du titre, du type de propriété et de l'URL de l'annonce.
"""
from app.services.text_normalizer_service import normalize_text

# Termes qui disqualifient un bien comme résidentiel
_BLACKLIST_RESIDENTIAL = [
    "entrepot", "entrepôt", "hangar", "depot", "dépôt",
    "usine", "atelier", "exploitation", "agricole",
    "parking", "garage", "parc industriel", "zone industrielle",
    # "ferme" removed — "terrains et fermes" is a valid land category
]

# Termes terrain
_TERRAIN_KW = ["terrain", "terrains", "lotissement", "terrain agricole", "lot", "ferme"]

# Termes commercial
_COMMERCIAL_KW = [
    "fonds de commerce", "fond de commerce", "local commercial",
    "bureau", "magasin", "boutique", "commerce", "immeuble commercial",
]

# Termes résidentiel
_RESIDENTIAL_KW = [
    "villa", "maison", "appartement", "studio", "duplex",
    "s+1", "s+2", "s+3", "s+4", "s 1", "s 2", "s 3", "s 4",
]


def classify_apartment_listing(
    title: str,
    property_type: str,
    url: str = "",
) -> dict:
    """
    Retourne un dict {"category": str, "sub_type": str}.

    category : "residential" | "commercial" | "land" | "unknown"
    sub_type : "appartement" | "villa" | "maison" | "studio" | "duplex" |
               "terrain" | "bureau" | "local_commercial" | "fonds_de_commerce" |
               "commercial" | "autre" | "unknown"
    """
    text = " ".join([
        normalize_text(title        or ""),
        normalize_text(property_type or ""),
        normalize_text(url          or ""),
    ])

    result: dict[str, str | None] = {"category": None, "sub_type": None}

    # 1. Blacklist non-résidentiel
    if any(kw in text for kw in _BLACKLIST_RESIDENTIAL):
        result["category"] = "commercial"
        result["sub_type"] = "autre"
        return result

    # 2. Terrain
    if any(kw in text for kw in _TERRAIN_KW):
        result["category"] = "land"
        result["sub_type"] = "terrain"
        return result

    # 3. Commercial
    if any(kw in text for kw in _COMMERCIAL_KW):
        result["category"] = "commercial"
        if "fonds de commerce" in text or "fond de commerce" in text:
            result["sub_type"] = "fonds_de_commerce"
        elif "bureau" in text:
            result["sub_type"] = "bureau"
        elif any(kw in text for kw in ["local commercial", "magasin", "boutique", "commerce"]):
            result["sub_type"] = "local_commercial"
        else:
            result["sub_type"] = "commercial"
        return result

    # 4. Résidentiel
    if any(kw in text for kw in _RESIDENTIAL_KW):
        result["category"] = "residential"
        if "villa" in text:
            result["sub_type"] = "villa"
        elif "maison" in text:
            result["sub_type"] = "maison"
        elif "duplex" in text:
            result["sub_type"] = "duplex"
        elif "studio" in text:
            result["sub_type"] = "studio"
        else:
            result["sub_type"] = "appartement"
        return result

    # 5. Fallback
    result["category"] = "unknown"
    result["sub_type"]  = "unknown"
    return result