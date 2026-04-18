from app.services.text_normalizer_service import normalize_text


def normalize_transaction(value: str | None) -> str | None:
    if not value:
        return None

    v = normalize_text(value)

    if v in ["location", "a louer", "à louer", "louer", "rent"]:
        return "location"

    if v in ["vente", "a vendre", "à vendre", "acheter", "buy", "sale"]:
        return "vente"

    return v


def filter_apartments_by_criteria(apartments, criteria: dict):
    results = []

    wanted_city = normalize_text(criteria.get("city")) if criteria.get("city") else None
    wanted_transaction = normalize_transaction(criteria.get("transaction_type"))
    wanted_rooms = criteria.get("rooms")
    budget_max = criteria.get("budget_max")
    budget_min = criteria.get("budget_min")
    allowed_types = [normalize_text(x) for x in criteria.get("allowed_property_types", [])]
    rooms_tolerance = criteria.get("rooms_tolerance", 0)

    for a in apartments:
        title = normalize_text(getattr(a, "title", ""))
        city = normalize_text(getattr(a, "city", ""))
        url = normalize_text(getattr(a, "url", ""))
        transaction = normalize_transaction(getattr(a, "transaction_type", ""))
        property_type = normalize_text(getattr(a, "property_type", ""))

        # Ville stricte
        if wanted_city:
            city_match = (
                wanted_city in city or
                wanted_city in title or
                wanted_city in url
            )
            if not city_match:
                continue

        # Transaction stricte
        if wanted_transaction and transaction != wanted_transaction:
            continue

        # Type strict si fourni
        if allowed_types:
            type_match = any(
                t in property_type or t in title or t in url
                for t in allowed_types
            )
            if not type_match:
                continue

        price = float(getattr(a, "price", 0) or 0)
        if budget_min is not None and price < budget_min:
            continue
        if budget_max is not None and price > budget_max:
            continue

        rooms = int(getattr(a, "rooms", 0) or 0)
        if wanted_rooms is not None:
            if abs(rooms - wanted_rooms) > rooms_tolerance:
                continue

        results.append(a)

    return results