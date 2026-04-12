from app.services.apartment_classifier_service import classify_apartment_listing


def compute_enriched_score(apt, budget: float, market_data: dict) -> float:
    price = float(apt.price or 0)
    surface = float(apt.surface_m2 or 0)
    rooms = int(apt.rooms or 0)
    bathrooms = int(apt.bathrooms or 0)

    if price <= 0 or surface <= 0:
        return 0.0

    pm2 = price / surface

    global_stats = market_data.get("global_stats", {})
    pm2_median = float(global_stats.get("pm2_median", 1) or 1)
    surface_moyenne = float(global_stats.get("surface_moyenne", 1) or 1)

    # score budget
    if price <= budget:
        budget_score = 40
    else:
        overflow = (price - budget) / budget if budget > 0 else 1
        budget_score = max(0, 40 - overflow * 50)

    # score prix/m²
    pm2_score = max(0, 25 - abs(pm2 - pm2_median) / pm2_median * 25)

    # score surface
    surface_score = min(15, (surface / surface_moyenne) * 15)

    # score confort
    comfort_score = min(10, rooms * 2) + min(10, bathrooms * 2)

    total = budget_score + pm2_score + surface_score + comfort_score
    return round(total, 2)


def recommend_apartments(budget: float, all_apts: list, market_data: dict, limit: int = 5):
    apartments_in_budget = [apt for apt in all_apts if float(apt.price or 0) <= budget]

    if not apartments_in_budget:
        apartments_in_budget = all_apts

    apartment_scores = []
    for apt in apartments_in_budget:
        score = compute_enriched_score(apt, budget, market_data)
        apartment_scores.append((apt, score))

    apartment_scores.sort(key=lambda x: x[1], reverse=True)

    return [apt for apt, _ in apartment_scores[:limit]]


def recommend_apartments_from_prompt(criteria: dict, all_apts: list, market_data: dict, limit: int = 5):
    scored = []

    budget = criteria.get("budget_max") or 999999999

    for apt in all_apts:
        price = float(apt.price or 0)
        surface = float(apt.surface_m2 or 0)
        rooms = int(apt.rooms or 0)
        bathrooms = int(apt.bathrooms or 0)

        if price <= 0 or surface <= 0:
            continue

        base_score = compute_enriched_score(apt, budget, market_data)

        listing_class = classify_apartment_listing(apt.title, apt.property_type, apt.url)

        type_bonus = 0

        if criteria.get("category") and listing_class["category"] == criteria["category"]:
            type_bonus += 20

        if criteria.get("sub_type") and listing_class["sub_type"] == criteria["sub_type"]:
            type_bonus += 15

        if criteria.get("sub_type") == "maison" and listing_class["sub_type"] in ["villa", "duplex"]:
            type_bonus += 10

        if criteria.get("sub_type") == "fonds_de_commerce" and listing_class["sub_type"] in ["fonds_de_commerce", "local_commercial", "commercial"]:
            type_bonus += 10

        score = round(base_score + type_bonus, 2)
        scored.append((apt, score, listing_class))

    scored.sort(key=lambda x: x[1], reverse=True)

    return [item[0] for item in scored[:limit]]