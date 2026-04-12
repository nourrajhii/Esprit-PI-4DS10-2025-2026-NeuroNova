from app.services.ollama_service import ask_ollama


def generate_natural_response(
    criteria: dict,
    recommended_apartments: list[dict],
    comparison_result: dict | None = None
) -> str:
    property_label = criteria.get("sub_type") or criteria.get("property_type") or "bien immobilier"
    city_label = criteria.get("city") or "n'importe quelle ville"
    budget_max = criteria.get("budget_max")
    transaction_type = criteria.get("transaction_type") or "non précisé"

    if not recommended_apartments:
        return (
            f"Aucun bien ne correspond exactement à votre recherche. "
            f"J’ai compris que vous cherchez un {property_label} à {city_label}, "
            f"en transaction de type {transaction_type}, "
            f"avec un budget maximum de {budget_max if budget_max is not None else 'non précisé'} DT. "
            f"Essayez d’élargir la ville, le type de bien ou le budget."
        )

    top = recommended_apartments[0]

    fallback_response = (
        f"J’ai trouvé {len(recommended_apartments)} bien(s) correspondant à votre recherche de "
        f"{property_label} à {city_label}. "
        f"La meilleure option actuellement est « {top['title']} », "
        f"au prix de {top.get('price')} DT."
    )

    try:
        short_prompt = f"""
Rédige une réponse courte et professionnelle en français.

Critères :
{criteria}

Top résultat :
{top}

Comparaison :
{comparison_result}

Réponse courte seulement.
"""
        return ask_ollama(short_prompt)
    except Exception:
        return fallback_response