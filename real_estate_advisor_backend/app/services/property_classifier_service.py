def classify_property_request(text: str) -> dict:
    text = (text or "").lower()

    result = {
        "category": None,
        "sub_type": None,
        "intent": "buy",
        "allowed_property_types": []
    }

    # intent
    if any(x in text for x in ["location", "louer", "à louer", "a louer", "locatif"]):
        result["intent"] = "rent"
    elif any(x in text for x in ["acheter", "achat", "à vendre", "a vendre", "vente"]):
        result["intent"] = "buy"

    # commercial
    if any(x in text for x in [
        "fonds de commerce", "fond de commerce", "local commercial",
        "bureau", "magasin", "commerce", "boutique"
    ]):
        result["category"] = "commercial"

        if "fonds de commerce" in text or "fond de commerce" in text:
            result["sub_type"] = "fonds_de_commerce"
            result["allowed_property_types"] = [
                "fonds de commerce", "fond de commerce", "commerce",
                "local commercial", "magasin", "boutique"
            ]
            return result

        if "bureau" in text:
            result["sub_type"] = "bureau"
            result["allowed_property_types"] = ["bureau", "office"]
            return result

        if any(x in text for x in ["local commercial", "magasin", "boutique", "commerce"]):
            result["sub_type"] = "local_commercial"
            result["allowed_property_types"] = [
                "local commercial", "commerce", "magasin", "boutique"
            ]
            return result

    # land
    if any(x in text for x in ["terrain", "lotissement", "lot", "terrain agricole"]):
        result["category"] = "land"
        result["sub_type"] = "terrain"
        result["allowed_property_types"] = [
            "terrain", "lotissement", "terrain agricole", "lot"
        ]
        return result

    # residential
    if any(x in text for x in ["villa", "appartement", "maison", "studio", "duplex", "s+1", "s+2", "s+3", "s+4"]):
        result["category"] = "residential"

        if "villa" in text:
            result["sub_type"] = "villa"
            result["allowed_property_types"] = ["villa", "maison", "duplex"]
            return result

        if "maison" in text:
            result["sub_type"] = "maison"
            result["allowed_property_types"] = ["maison", "villa", "duplex"]
            return result

        if "duplex" in text:
            result["sub_type"] = "duplex"
            result["allowed_property_types"] = ["duplex", "villa", "maison", "appartement"]
            return result

        # par défaut logement
        result["sub_type"] = "appartement"
        result["allowed_property_types"] = ["appartement", "studio", "duplex"]
        return result

    return result