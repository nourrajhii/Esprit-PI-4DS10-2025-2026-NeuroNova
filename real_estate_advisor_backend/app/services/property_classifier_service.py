from app.services.text_normalizer_service import normalize_text


def classify_property_request(user_prompt: str) -> dict:
    text = normalize_text(user_prompt)

    category = "residential"
    sub_type = None
    allowed_property_types = []

    if any(word in text for word in [
        "studio", "appartement", "duplex", "s+1", "s+2", "s+3", "s+4",
        "falej", "bit", "chqqa", "shqqa",  # Darija: appartement
    ]):
        category = "residential"
        sub_type = "appartement"
        allowed_property_types = ["appartement", "studio", "duplex"]

    elif any(word in text for word in [
        "villa", "maison", "dar",
        "dara", "dar kbira",  # Darija: maison
    ]):
        category = "residential"
        sub_type = "villa"
        allowed_property_types = ["villa", "maison", "maisons et villas"]

    elif any(word in text for word in [
        "terrain", "lot", "ferme", "ardh",  # ardh = terrain en arabe
    ]):
        category = "land"
        sub_type = "terrain"
        allowed_property_types = ["terrain", "ferme", "lot", "terrains et fermes"]

    elif any(word in text for word in ["bureau", "plateau"]):
        category = "commercial"
        sub_type = "bureau"
        allowed_property_types = ["bureau", "plateau", "bureaux et plateaux"]

    elif any(word in text for word in ["magasin", "commerce", "local", "shop"]):
        category = "commercial"
        sub_type = "local"
        allowed_property_types = ["magasin", "commerce", "local", "local commercial"]

    intent = "unknown"
    if any(word in text for word in [
        "louer", "location", "a louer", "a louer", "rent",
        "ekri", "ekra", "nkri", "nkra", "kra", "kri",
    ]):
        intent = "rent"
    elif any(word in text for word in [
        "acheter", "vente", "a vendre", "a vendre", "buy", "sale",
        "chri", "acheteh", "vendeh",
    ]):
        intent = "sale"

    return {
        "category": category,
        "sub_type": sub_type,
        "allowed_property_types": allowed_property_types,
        "intent": intent
    }