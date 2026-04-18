from app.services.text_normalizer_service import normalize_text


def classify_property_request(user_prompt: str) -> dict:
    text = normalize_text(user_prompt)

    category = "residential"
    sub_type = None
    allowed_property_types = []

    if any(word in text for word in ["studio", "appartement", "duplex", "s+1", "s+2", "s+3", "s+4"]):
        category = "residential"
        sub_type = "appartement"
        allowed_property_types = ["appartement", "studio", "duplex"]

    elif any(word in text for word in ["villa", "maison", "dar"]):
        category = "residential"
        sub_type = "villa"
        allowed_property_types = ["villa", "maison"]

    elif any(word in text for word in ["terrain", "lot", "ferme"]):
        category = "land"
        sub_type = "terrain"
        allowed_property_types = ["terrain", "ferme", "lot"]

    elif any(word in text for word in ["bureau", "plateau"]):
        category = "commercial"
        sub_type = "bureau"
        allowed_property_types = ["bureau", "plateau"]

    elif any(word in text for word in ["magasin", "commerce", "local", "shop"]):
        category = "commercial"
        sub_type = "local"
        allowed_property_types = ["magasin", "commerce", "local"]

    intent = "unknown"
    if any(word in text for word in ["louer", "location", "a louer", "à louer", "rent", "ekra", "nkara"]):
        intent = "rent"
    elif any(word in text for word in ["acheter", "vente", "a vendre", "à vendre", "buy", "sale"]):
        intent = "sale"

    return {
        "category": category,
        "sub_type": sub_type,
        "allowed_property_types": allowed_property_types,
        "intent": intent
    }