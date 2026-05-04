"""
agent.py
Agent d'analyse de marché immobilier tunisien v3.

Formule unifiée à 4 facteurs :
  prix_base            = prix_ref_gouvernorat[type] × coeff_standing
  prix_reference_ajuste = prix_base × (1 + score_attributs) × (1 + score_proximite)
  → compare valeur_saisie vs prix_reference_ajuste pour le positionnement marché
  → projette depuis valeur_saisie avec le taux de croissance du gouvernorat
"""

import pandas as pd
from market_data import GOUVERNORATS
from geo_data import (
    STANDING_COEFFS,
    calc_score_attributs,
    calc_score_proximite,
    get_coords,
)


# ── Utilitaires ───────────────────────────────────────────────────────────────

def _get_gov(gouvernorat: str) -> dict:
    if gouvernorat in GOUVERNORATS:
        return GOUVERNORATS[gouvernorat]
    for k, v in GOUVERNORATS.items():
        if k.lower() in gouvernorat.lower() or gouvernorat.lower() in k.lower():
            return v
    return GOUVERNORATS["Tunis"]


def _compound(base: float, rate: float, months: int) -> float:
    return round(base * (1 + rate) ** months, 2)


def _var_pct(new_val: float, base: float) -> float:
    if base == 0:
        return 0.0
    return round((new_val - base) / base * 100, 1)


def _risk_label(gov: dict) -> str:
    r, v = gov["risque"], gov["volatilite"]
    if r == "faible" and v < 0.045:
        return "Faible"
    elif r in ("modéré",) or v < 0.070:
        return "Modéré"
    return "Élevé"


def _tendance(var24: float) -> str:
    if var24 > 2:
        return "hausse"
    elif var24 < -2:
        return "baisse"
    return "stable"


def _build_points(base: float, rate: float, volatilite: float) -> list[dict]:
    dates = pd.date_range(
        pd.Timestamp.now().normalize() + pd.DateOffset(months=1),
        periods=24,
        freq="MS",
    )
    points = []
    for i, d in enumerate(dates, start=1):
        prix = _compound(base, rate, i)
        ic = prix * volatilite * (i / 24) ** 0.5
        points.append({
            "date": d.strftime("%Y-%m-%d"),
            "prix_predit": round(prix, 2),
            "ic_bas": round(prix - ic, 2),
            "ic_haut": round(prix + ic, 2),
        })
    return points


# ── Positionnement marché ─────────────────────────────────────────────────────

def _statut_vente(prix_saisi: float, prix_ref: float) -> tuple[float, str]:
    d = _var_pct(prix_saisi, prix_ref)
    if d < -15:
        s = "très sous-évalué"
    elif d < -5:
        s = "sous-évalué"
    elif d <= 5:
        s = "dans la moyenne du marché"
    elif d <= 20:
        s = "légèrement surévalué"
    else:
        s = "fortement surévalué"
    return round(d, 1), s


def _statut_location(loyer_saisi: float, loyer_ref: float) -> tuple[float, str]:
    d = _var_pct(loyer_saisi, loyer_ref)
    if d < -20:
        s = "très en dessous du marché"
    elif d < -8:
        s = "en dessous du marché"
    elif d <= 8:
        s = "aligné avec le marché"
    elif d <= 25:
        s = "au-dessus du marché"
    else:
        s = "bien au-dessus du marché"
    return round(d, 1), s


# ── Recommandations ───────────────────────────────────────────────────────────

def _reco_vente(
    gouvernorat: str, ville: str, type_bien: str, statut: str,
    tendance: str, diff_pct: float, risque: str, taux_annuel: float,
    standing: str, score_prox: float,
) -> str:
    ta = round(taux_annuel * 100, 1)
    loc = f"{ville}, {gouvernorat}" if ville else gouvernorat
    prox_note = (
        f" Le score de proximité (+{score_prox*100:.0f}%) reflète la bonne desserte du quartier."
        if score_prox > 0.05 else ""
    )

    conseils = {
        "très sous-évalué": (
            f"Opportunité rare : ce {type_bien} en {standing} à {loc} est affiché {diff_pct:+.1f}% "
            f"sous la valeur de référence ajustée. Avec {ta}%/an de croissance estimée, "
            f"cet écart se comble généralement en 6–12 mois.{prox_note}"
        ),
        "sous-évalué": (
            f"Bonne entrée de marché : ce {type_bien} en {standing} à {loc} est {diff_pct:+.1f}% "
            f"sous la référence ajustée ({ta}%/an). Cet écart représente une marge de sécurité "
            f"favorable à l'acquisition.{prox_note}"
        ),
        "dans la moyenne du marché": (
            f"Prix cohérent avec la référence {standing} pour ce {type_bien} à {loc} "
            f"(écart : {diff_pct:+.1f}%). "
            + (f"La tendance haussière ({ta}%/an) favorise l'achat maintenant."
               if tendance == "hausse"
               else f"Tendance : {tendance} ({ta}%/an). Une négociation modérée (3–5%) reste envisageable.")
            + prox_note
        ),
        "légèrement surévalué": (
            f"Ce {type_bien} est {diff_pct:+.1f}% au-dessus de la référence {standing} à {loc}. "
            f"Une négociation de 5–10% est recommandée. Si le bien présente des atouts "
            f"distinctifs non pris en compte (étage, vue, finitions premium), la prime peut "
            f"se justifier partiellement.{prox_note}"
        ),
        "fortement surévalué": (
            f"Attention : ce {type_bien} dépasse de {diff_pct:+.1f}% la référence {standing} "
            f"à {loc}. Ce niveau ne se justifie que par des caractéristiques exceptionnelles. "
            f"Faites expertiser le bien et négociez fermement avant toute décision.{prox_note}"
        ),
    }
    base = conseils.get(statut, f"Prix à {diff_pct:+.1f}% de la référence à {loc}.")
    if risque == "Élevé":
        base += " ⚠ Ce marché présente une volatilité élevée — diversifiez vos placements."
    elif risque == "Modéré":
        base += " Le marché local affiche une volatilité modérée à surveiller."
    return base


def _reco_location(
    gouvernorat: str, ville: str, composition: str, statut: str,
    tendance: str, diff_pct: float, risque: str, taux_annuel: float,
    standing: str, score_prox: float,
) -> str:
    ta = round(taux_annuel * 100, 1)
    loc = f"{ville}, {gouvernorat}" if ville else gouvernorat
    prox_note = (
        f" Les services de proximité détectés (+{score_prox*100:.0f}%) valorisent ce bien."
        if score_prox > 0.05 else ""
    )

    if statut in ("très en dessous du marché", "en dessous du marché"):
        reco = (
            f"Ce loyer ({diff_pct:+.1f}% vs référence {standing}) est sous-valorisé "
            f"pour un {composition} à {loc}. Propriétaire : révisez à la hausse au renouvellement. "
            f"Locataire : sécurisez ce logement, c'est une opportunité dans ce marché en {tendance}."
            + prox_note
        )
    elif statut == "aligné avec le marché":
        reco = (
            f"Loyer aligné avec la référence {standing} pour un {composition} à {loc} "
            f"(écart : {diff_pct:+.1f}%). Tendance {tendance} ({ta}%/an) : "
            f"anticipez une progression régulière du loyer de marché sur 24 mois." + prox_note
        )
    else:
        reco = (
            f"Ce loyer dépasse la référence {standing} de {diff_pct:+.1f}% pour un {composition} "
            f"à {loc}. Propriétaire : ce positionnement peut allonger les délais. "
            f"Locataire : négociez ou explorez d'autres options dans ce gouvernorat." + prox_note
        )
    if risque == "Élevé":
        reco += " ⚠ Volatilité élevée : les loyers peuvent fluctuer significativement."
    return reco


# ── Points d'entrée publics ───────────────────────────────────────────────────

def analyze_vente(
    gouvernorat: str,
    ville: str,
    quartier: str,
    standing: str,
    type_bien: str,
    superficie: float,
    prix_m2_saisi: float,
    attributs_bien: list[str],
    services_proximite: list[str],
) -> dict:
    gov = _get_gov(gouvernorat)
    rate = gov["taux_vente_mensuel"]
    rate_annuel = (1 + rate) ** 12 - 1

    type_key = type_bien.lower() if type_bien.lower() in gov["prix_moyen_m2"] else "appartement"
    prix_ref_gov = gov["prix_moyen_m2"][type_key]

    # Niveau 2 : standing géographique
    coeff_standing = STANDING_COEFFS.get(standing, 1.0)
    prix_base = prix_ref_gov * coeff_standing

    # Niveau 3A : attributs du bien
    attributs_actifs = calc_score_attributs("vente", attributs_bien)
    score_attributs = sum(attributs_actifs.values())

    # Niveau 3B : services de proximité
    services_detectes = calc_score_proximite(services_proximite)
    score_proximite = sum(services_detectes.values())

    # Prix de référence ajusté (fair value)
    prix_reference_ajuste = prix_base * (1 + score_attributs) * (1 + score_proximite)

    # Positionnement
    diff_pct, statut = _statut_vente(prix_m2_saisi, prix_reference_ajuste)

    # Prévisions depuis le prix saisi par l'utilisateur
    h6  = _compound(prix_m2_saisi, rate, 6)
    h12 = _compound(prix_m2_saisi, rate, 12)
    h18 = _compound(prix_m2_saisi, rate, 18)
    h24 = _compound(prix_m2_saisi, rate, 24)

    var24 = _var_pct(h24, prix_m2_saisi)
    tend = _tendance(var24)
    risque = _risk_label(gov)
    reco = _reco_vente(
        gouvernorat, ville, type_bien, statut, tend,
        diff_pct, risque, rate_annuel, standing, score_proximite,
    )

    coords = get_coords(ville, gouvernorat)

    return {
        "mode":                   "vente",
        "gouvernorat":            gouvernorat,
        "ville":                  ville,
        "quartier":               quartier,
        "standing":               standing,
        "type_bien":              type_bien,
        "composition":            None,
        "superficie":             superficie,
        "valeur_saisie":          prix_m2_saisi,
        "valeur_totale_actuelle": round(prix_m2_saisi * superficie, 2),
        "prix_base":              round(prix_base, 2),
        "prix_reference_ajuste":  round(prix_reference_ajuste, 2),
        "prix_moyen_marche":      round(prix_reference_ajuste, 2),
        "diff_vs_marche_pct":     diff_pct,
        "statut_prix":            statut,
        "coeff_standing":         coeff_standing,
        "score_attributs":        round(score_attributs, 4),
        "score_proximite":        round(score_proximite, 4),
        "attributs_actifs":       attributs_actifs,
        "services_detectes":      services_detectes,
        "taux_mensuel":           rate,
        "taux_annuel":            round(rate_annuel * 100, 2),
        "horizons": {
            "6":  {"valeur": h6,  "variation_pct": _var_pct(h6,  prix_m2_saisi)},
            "12": {"valeur": h12, "variation_pct": _var_pct(h12, prix_m2_saisi)},
            "18": {"valeur": h18, "variation_pct": _var_pct(h18, prix_m2_saisi)},
            "24": {"valeur": h24, "variation_pct": _var_pct(h24, prix_m2_saisi)},
        },
        "tendance":       tend,
        "risque":         risque,
        "tension":        gov["tension"],
        "analyse_marche": gov["description"],
        "facteurs":       gov["facteurs"],
        "recommandation": reco,
        "points":         _build_points(prix_m2_saisi, rate, gov["volatilite"]),
        "lat":            coords[0] if coords else None,
        "lng":            coords[1] if coords else None,
    }


def analyze_location(
    gouvernorat: str,
    ville: str,
    quartier: str,
    standing: str,
    composition: str,
    loyer_saisi: float,
    attributs_bien: list[str],
    services_proximite: list[str],
) -> dict:
    gov = _get_gov(gouvernorat)
    rate = gov["taux_location_mensuel"]
    rate_annuel = (1 + rate) ** 12 - 1

    comp = composition if composition in gov["loyers_moyens"] else "S+2"
    loyer_ref_gov = gov["loyers_moyens"][comp]

    # Niveau 2 : standing
    coeff_standing = STANDING_COEFFS.get(standing, 1.0)
    loyer_base = loyer_ref_gov * coeff_standing

    # Niveau 3A : attributs
    attributs_actifs = calc_score_attributs("location", attributs_bien)
    score_attributs = sum(attributs_actifs.values())

    # Niveau 3B : proximité
    services_detectes = calc_score_proximite(services_proximite)
    score_proximite = sum(services_detectes.values())

    # Loyer de référence ajusté
    loyer_reference_ajuste = loyer_base * (1 + score_attributs) * (1 + score_proximite)

    # Positionnement
    diff_pct, statut = _statut_location(loyer_saisi, loyer_reference_ajuste)

    # Prévisions depuis le loyer saisi
    h6  = _compound(loyer_saisi, rate, 6)
    h12 = _compound(loyer_saisi, rate, 12)
    h18 = _compound(loyer_saisi, rate, 18)
    h24 = _compound(loyer_saisi, rate, 24)

    var24 = _var_pct(h24, loyer_saisi)
    tend = _tendance(var24)
    risque = _risk_label(gov)
    reco = _reco_location(
        gouvernorat, ville, comp, statut, tend,
        diff_pct, risque, rate_annuel, standing, score_proximite,
    )

    coords = get_coords(ville, gouvernorat)

    return {
        "mode":                   "location",
        "gouvernorat":            gouvernorat,
        "ville":                  ville,
        "quartier":               quartier,
        "standing":               standing,
        "type_bien":              None,
        "composition":            comp,
        "superficie":             None,
        "valeur_saisie":          loyer_saisi,
        "valeur_totale_actuelle": None,
        "prix_base":              round(loyer_base, 2),
        "prix_reference_ajuste":  round(loyer_reference_ajuste, 2),
        "prix_moyen_marche":      round(loyer_reference_ajuste, 2),
        "diff_vs_marche_pct":     diff_pct,
        "statut_prix":            statut,
        "coeff_standing":         coeff_standing,
        "score_attributs":        round(score_attributs, 4),
        "score_proximite":        round(score_proximite, 4),
        "attributs_actifs":       attributs_actifs,
        "services_detectes":      services_detectes,
        "taux_mensuel":           rate,
        "taux_annuel":            round(rate_annuel * 100, 2),
        "horizons": {
            "6":  {"valeur": h6,  "variation_pct": _var_pct(h6,  loyer_saisi)},
            "12": {"valeur": h12, "variation_pct": _var_pct(h12, loyer_saisi)},
            "18": {"valeur": h18, "variation_pct": _var_pct(h18, loyer_saisi)},
            "24": {"valeur": h24, "variation_pct": _var_pct(h24, loyer_saisi)},
        },
        "tendance":       tend,
        "risque":         risque,
        "tension":        gov["tension"],
        "analyse_marche": gov["description"],
        "facteurs":       gov["facteurs"],
        "recommandation": reco,
        "points":         _build_points(loyer_saisi, rate, gov["volatilite"]),
        "lat":            coords[0] if coords else None,
        "lng":            coords[1] if coords else None,
    }
