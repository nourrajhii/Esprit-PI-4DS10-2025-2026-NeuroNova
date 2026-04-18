"""
prompt_response_service.py — Génération de réponses naturelles professionnelles.
 
Retourne TOUJOURS un tuple (natural_response: str, advice: str)
conforme au contrat attendu par routes/advisor.py.
"""
from __future__ import annotations
 
 
# ── Helpers de formatage ──────────────────────────────────────────────────────
def _fmt_price(value) -> str:
    try:
        return f"{int(float(value)):,} DT".replace(",", " ")
    except (TypeError, ValueError):
        return "prix non renseigné"
 
 
def _fmt_surface(value) -> str:
    try:
        s = float(value)
        return f"{s:g} m²" if s > 0 else ""
    except (TypeError, ValueError):
        return ""
 
 
def _label_type(criteria: dict) -> str:
    sub = (criteria.get("sub_type") or criteria.get("property_type") or "").lower()
    labels = {
        "appartement":       "appartement",
        "villa":             "villa",
        "maison":            "maison",
        "studio":            "studio",
        "duplex":            "duplex",
        "terrain":           "terrain",
        "bureau":            "bureau",
        "local_commercial":  "local commercial",
        "fonds_de_commerce": "fonds de commerce",
    }
    return labels.get(sub, sub or "bien immobilier")
 
 
def _label_transaction(tx: str | None) -> str:
    if not tx:
        return "non précisée"
    tx_lower = tx.lower()
    if "location" in tx_lower or "louer" in tx_lower:
        return "en location"
    if "vente" in tx_lower or "vendre" in tx_lower:
        return "en vente"
    return tx
 
 
def _score_label(score: float) -> str:
    if score >= 88:
        return "excellent"
    if score >= 75:
        return "très bon"
    if score >= 60:
        return "correct"
    return "acceptable"
 
 
def _budget_label(criteria: dict) -> str:
    bmin = criteria.get("budget_min")
    bmax = criteria.get("budget_max")
    if bmin and bmax:
        return f"budget entre {_fmt_price(bmin)} et {_fmt_price(bmax)}"
    if bmax:
        return f"budget max. {_fmt_price(bmax)}"
    if bmin:
        return f"budget min. {_fmt_price(bmin)}"
    return ""
 
 
# ── Fonction principale ───────────────────────────────────────────────────────
def generate_natural_response(
    criteria: dict,
    recommended_apartments: list[dict],
    comparison_result=None,
) -> tuple[str, str]:
    """
    Génère une réponse naturelle et un conseil distincts.
 
    Returns:
        (natural_response, advice) — toujours un tuple de deux chaînes.
    """
    city        = criteria.get("city") or "la zone recherchée"
    tx_label    = _label_transaction(criteria.get("transaction_type"))
    sub_type    = _label_type(criteria)
    budget_info = _budget_label(criteria)
 
    # ── Cas aucun résultat ────────────────────────────────────────────────────
    if not recommended_apartments:
        natural = (
            f"Je n'ai pas trouvé de bien correspondant exactement à votre recherche "
            f"de {sub_type} {tx_label} à {city}"
            + (f" ({budget_info})" if budget_info else "") + "."
        )
        advice = (
            "Essayez d'élargir légèrement le budget, la zone géographique ou "
            "le type de bien pour obtenir davantage d'options."
        )
        return natural, advice
 
    # ── Cas avec résultats ────────────────────────────────────────────────────
    count = len(recommended_apartments)
    best  = recommended_apartments[0]
 
    price   = best.get("price")
    surface = best.get("surface_m2") or best.get("size")
    rooms   = best.get("rooms") or best.get("room_count")
    baths   = best.get("bathrooms") or best.get("bathroom_count")
    ppm2    = best.get("price_per_m2")
    score   = best.get("score", 0)
    loc     = best.get("city") or city
    region  = best.get("region")
    title   = best.get("title") or "Annonce sélectionnée"
 
    # Résumé de recherche
    natural = (
        f"J'ai trouvé {count} bien{'s' if count > 1 else ''} correspondant "
        f"à votre recherche de {sub_type} {tx_label} à {city}"
        + (f" ({budget_info})" if budget_info else "") + "."
    )
 
    # Conseil sur le meilleur bien
    loc_full = loc
    if region and region != loc:
        loc_full = f"{region}, {loc}"
 
    advice_parts = [
        f"La meilleure option ({_score_label(score)}) est «\u202f{title}\u202f», "
        f"située à {loc_full}"
    ]
 
    if price:
        advice_parts.append(f"proposée à {_fmt_price(price)}")
 
    details = []
    if surface:
        details.append(f"{_fmt_surface(surface)}")
    if rooms and int(rooms) > 0:
        details.append(f"{rooms} pièce{'s' if int(rooms) > 1 else ''}")
    if baths and int(baths) > 0:
        details.append(f"{baths} SDB")
    if details:
        advice_parts.append("avec " + ", ".join(details))
 
    if ppm2:
        advice_parts.append(f"soit {_fmt_price(ppm2)}/m²")
 
    advice = ", ".join(advice_parts) + (
        ". Vérifiez l'emplacement exact, l'état du bien et la cohérence "
        "du prix au m² avant toute décision."
    )
 
    # Comparaison optionnelle
    if comparison_result:
        a_id = comparison_result.get("apartment_a_id")
        b_id = comparison_result.get("apartment_b_id")
        win  = comparison_result.get("recommended_apartment_id")
        advice += (
            f" Une comparaison a été effectuée entre les biens ID\u202f{a_id} "
            f"et ID\u202f{b_id} : le bien ID\u202f{win} est recommandé."
        )
 
    return natural, advice