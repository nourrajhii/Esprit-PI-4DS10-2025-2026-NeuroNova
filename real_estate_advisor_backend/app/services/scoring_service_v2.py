def compute_smart_score(apartment, criteria, market_data):
    price = float(apartment.price or 0)
    surface = float(apartment.surface_m2 or 0)
    rooms = int(apartment.rooms or 0)

    budget = criteria.get("budget_max") or price

    # 1. Score budget
    if price <= budget:
        budget_score = 1 - (price / budget)
    else:
        budget_score = -1

    # 2. prix / m²
    if surface > 0:
        pm2 = price / surface
        market_pm2 = market_data["global_stats"]["pm2_median"]
        pm2_score = 1 - (pm2 / market_pm2)
    else:
        pm2_score = 0

    # 3. surface
    surface_score = min(surface / 200, 1)

    # 4. rooms
    rooms_score = min(rooms / 5, 1)

    # score final pondéré
    final_score = (
        budget_score * 0.4 +
        pm2_score * 0.3 +
        surface_score * 0.2 +
        rooms_score * 0.1
    )

    return round(final_score * 100, 2)