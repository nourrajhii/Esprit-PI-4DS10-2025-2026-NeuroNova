def estimate_quote(surface_m2: float, renovation_level: str | None) -> dict:
    if renovation_level == "low":
        material_rate = 50
    elif renovation_level == "medium":
        material_rate = 120
    elif renovation_level == "high":
        material_rate = 220
    else:
        material_rate = 80

    subtotal_materials = surface_m2 * material_rate
    subtotal_labor = subtotal_materials * 0.30
    subtotal_equipment = subtotal_materials * 0.08
    contingency_cost = (subtotal_materials + subtotal_labor + subtotal_equipment) * 0.10
    total_cost = subtotal_materials + subtotal_labor + subtotal_equipment + contingency_cost

    return {
        "subtotal_materials": round(subtotal_materials, 2),
        "subtotal_labor": round(subtotal_labor, 2),
        "subtotal_equipment": round(subtotal_equipment, 2),
        "contingency_cost": round(contingency_cost, 2),
        "total_cost": round(total_cost, 2)
    }