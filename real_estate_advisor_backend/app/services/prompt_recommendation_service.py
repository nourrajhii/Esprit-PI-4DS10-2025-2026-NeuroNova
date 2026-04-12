from app.models.apartment import Apartment
from app.services.text_normalizer_service import normalize_text
from app.services.apartment_classifier_service import classify_apartment_listing


def matches_city(apartment_city: str, target_city: str) -> bool:
    apt_city = normalize_text(apartment_city)
    tgt_city = normalize_text(target_city)

    if not apt_city or not tgt_city:
        return False

    return tgt_city in apt_city or apt_city in tgt_city


def matches_property_type(apartment_property_type: str, allowed_property_types: list[str]) -> bool:
    apt_type = normalize_text(apartment_property_type)

    if not apt_type:
        return False

    for allowed in allowed_property_types:
        allowed_norm = normalize_text(allowed)
        if allowed_norm in apt_type or apt_type in allowed_norm:
            return True

    return False


def matches_transaction_type(apartment_transaction_type: str, wanted_transaction_type: str) -> bool:
    apt_tx = normalize_text(apartment_transaction_type)
    wanted_tx = normalize_text(wanted_transaction_type)

    if not apt_tx or not wanted_tx:
        return False

    if wanted_tx == "vente":
        vente_aliases = ["vente", "a vendre", "avendre", "vendre", "buy"]
        return any(alias in apt_tx for alias in vente_aliases)

    if wanted_tx == "location":
        location_aliases = ["location", "a louer", "alouer", "louer", "rent", "location saisonniere"]
        return any(alias in apt_tx for alias in location_aliases)

    return wanted_tx in apt_tx


def filter_apartments_by_criteria(apartments: list[Apartment], criteria: dict) -> list[Apartment]:
    results = apartments

    if criteria.get("city"):
        filtered = [a for a in results if a.city and matches_city(a.city, criteria["city"])]
        if filtered:
            results = filtered

    if criteria.get("category") or criteria.get("sub_type"):
        filtered = [
        a for a in results
        if matches_requested_type(a, criteria)
    ]
    if filtered:
        results = filtered

    if criteria.get("transaction_type"):
        filtered = [
            a for a in results
            if a.transaction_type and matches_transaction_type(a.transaction_type, criteria["transaction_type"])
        ]
        if filtered:
            results = filtered

    if criteria.get("budget_max") is not None:
        filtered = [
            a for a in results
            if float(a.price or 0) <= float(criteria["budget_max"])
        ]
        if filtered:
            results = filtered

    if criteria.get("budget_min") is not None:
        filtered = [
            a for a in results
            if float(a.price or 0) >= float(criteria["budget_min"])
        ]
        if filtered:
            results = filtered

    if criteria.get("rooms") is not None:
        filtered = [
            a for a in results
            if int(a.rooms or 0) >= int(criteria["rooms"])
        ]
        if filtered:
            results = filtered

    if criteria.get("bathrooms") is not None:
        filtered = [
            a for a in results
            if int(a.bathrooms or 0) >= int(criteria["bathrooms"])
        ]
        if filtered:
            results = filtered

    return results
def matches_requested_type(apartment, criteria: dict) -> bool:
    listing_class = classify_apartment_listing(
        title=apartment.title,
        property_type=apartment.property_type,
        url=apartment.url
    )

    requested_category = criteria.get("category")
    requested_sub_type = criteria.get("sub_type")

    if requested_category and listing_class["category"] != requested_category:
        return False

    if requested_sub_type:
        # cas souples
        if requested_sub_type == "maison" and listing_class["sub_type"] in ["maison", "villa", "duplex"]:
            return True

        if requested_sub_type == "terrain" and listing_class["sub_type"] == "terrain":
            return True

        if requested_sub_type == "fonds_de_commerce" and listing_class["sub_type"] in ["fonds_de_commerce", "local_commercial", "commercial"]:
            return True

        if requested_sub_type == listing_class["sub_type"]:
            return True

        return False

    return True