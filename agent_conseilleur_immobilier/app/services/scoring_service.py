def compute_budget_score(price: float, budget: float) -> float:
    if price <= budget:
        return 40.0
    overflow = (price - budget) / budget
    return max(0, 40 - overflow * 50)


def compute_value_score(price: float, surface_m2: float) -> float:
    if not price or price <= 0 or not surface_m2:
        return 0
    ratio = surface_m2 / price
    return min(25, ratio * 100000)


def compute_rooms_score(rooms: int) -> float:
    if not rooms:
        return 0
    return min(15, rooms * 3)


def compute_bathrooms_score(bathrooms: int) -> float:
    if not bathrooms:
        return 0
    return min(10, bathrooms * 3)


def compute_apartment_score(price: float, budget: float, surface_m2: float, rooms: int, bathrooms: int) -> float:
    total = (
        compute_budget_score(price, budget)
        + compute_value_score(price, surface_m2)
        + compute_rooms_score(rooms)
        + compute_bathrooms_score(bathrooms)
    )
    return round(total, 2)