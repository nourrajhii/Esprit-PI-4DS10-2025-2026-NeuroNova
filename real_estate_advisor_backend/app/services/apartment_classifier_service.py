from app.services.text_normalizer_service import normalize_text


def classify_apartment_listing(title: str, property_type: str, url: str = "") -> dict:
    text = " ".join([
        normalize_text(title or ""),
        normalize_text(property_type or ""),
        normalize_text(url or "")
    ])

    result = {
        "category": None,
        "sub_type": None
    }

    # LAND
    if any(x in text for x in ["terrain", "lotissement", "terrain agricole", "lot"]):
        result["category"] = "land"
        result["sub_type"] = "terrain"
        return result

    # COMMERCIAL
    if any(x in text for x in [
        "fonds de commerce", "fond de commerce", "local commercial",
        "bureau", "magasin", "boutique", "commerce", "immeuble commercial"
    ]):
        result["category"] = "commercial"

        if "fonds de commerce" in text or "fond de commerce" in text:
            result["sub_type"] = "fonds_de_commerce"
        elif "bureau" in text:
            result["sub_type"] = "bureau"
        elif any(x in text for x in ["local commercial", "magasin", "boutique", "commerce"]):
            result["sub_type"] = "local_commercial"
        else:
            result["sub_type"] = "commercial"

        return result

    # RESIDENTIAL
    if any(x in text for x in [
        "villa", "maison", "appartement", "studio", "duplex", "s+1", "s+2", "s+3", "s+4"
    ]):
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

    # fallback
    result["category"] = "unknown"
    result["sub_type"] = "unknown"
    return result