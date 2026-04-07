def build_reason(total_cost_a: float, total_cost_b: float, budget: float) -> str:
    if total_cost_a <= budget and total_cost_b <= budget:
        if total_cost_a < total_cost_b:
            return "L'appartement A respecte le budget et coûte moins cher au total."
        return "L'appartement B respecte le budget et coûte moins cher au total."

    if total_cost_a <= budget and total_cost_b > budget:
        return "L'appartement A est recommandé car il respecte le budget alors que B le dépasse."

    if total_cost_b <= budget and total_cost_a > budget:
        return "L'appartement B est recommandé car il respecte le budget alors que A le dépasse."

    if total_cost_a < total_cost_b:
        return "Les deux dépassent le budget, mais l'appartement A reste le choix le moins coûteux."
    return "Les deux dépassent le budget, mais l'appartement B reste le choix le moins coûteux."
def build_detailed_reason(a, b, score_a, score_b, budget):
    reasons = []

    # 1. Budget
    if a.price <= budget and b.price > budget:
        reasons.append("il respecte votre budget contrairement au bien B")
    elif b.price <= budget and a.price > budget:
        reasons.append("le bien B respecte mieux le budget")
    elif a.price < b.price:
        reasons.append("il est moins cher que le bien B")

    # 2. Surface / prix
    if a.surface_m2 and b.surface_m2:
        ratio_a = a.surface_m2 / a.price if a.price else 0
        ratio_b = b.surface_m2 / b.price if b.price else 0

        if ratio_a > ratio_b:
            reasons.append("il offre une meilleure surface par rapport au prix")

    # 3. Rooms
    if (a.rooms or 0) > (b.rooms or 0):
        reasons.append("il propose plus de pièces")

    # 4. Bathrooms
    if (a.bathrooms or 0) > (b.bathrooms or 0):
        reasons.append("il dispose de plus de salles de bain")

    # fallback
    if not reasons:
        reasons.append("il présente un meilleur score global")

    return (
        f"Le bien A est recommandé avec un score de {score_a} contre {score_b} pour le bien B, "
        + "car " + ", ".join(reasons) + "."
    )
def compute_enriched_score(apt, city_avg_price, city_avg_surface, market_data):
    # Comparaison avec le prix moyen au m² du marché
    price_per_m2 = apt['price'] / apt['surface_m2']
    price_per_m2_ratio = price_per_m2 / city_avg_price

    # Bonus en fonction de la surface par rapport à la moyenne du marché
    surface_ratio = apt['surface_m2'] / city_avg_surface

    # Calcul du score basé sur ces critères
    score = (price_per_m2_ratio * 0.4) + (surface_ratio * 0.3) + (apt['rooms'] * 0.2) + (apt['bathrooms'] * 0.1)
    
    # Appliquer un facteur supplémentaire pour la localisation (exemple : quartier prisé)
    if apt['city'] in market_data['premium_cities']:
        score *= 1.2  # Bonus pour les quartiers populaires

    return score

def recommend_apartments(budget, all_apts, city, market_data):
    # Filtrer les appartements qui rentrent dans le budget
    apartments_in_budget = [apt for apt in all_apts if apt['price'] <= budget]

    # Calculer le score enrichi pour chaque appartement
    apartment_scores = []
    for apt in apartments_in_budget:
        score = compute_enriched_score(apt, market_data['avg_price_per_m2'][city], market_data['avg_surface'][city], market_data)
        apartment_scores.append((apt, score))

    # Trier les appartements par score (le meilleur score en premier)
    apartment_scores.sort(key=lambda x: x[1], reverse=True)

    # Retourner les appartements triés par pertinence
    return [apt for apt, score in apartment_scores]