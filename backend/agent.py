"""
agent.py
Agent d'analyse de marché immobilier tunisien.
Génère des prévisions contextuelles, positionnement marché et recommandations.
Deux modes entièrement séparés : vente (prix/m²) et location (loyer mensuel).
"""

import pandas as pd
from market_data import GOUVERNORATS, TYPES_BIEN, COMPOSITIONS


# ── Utilitaires ───────────────────────────────────────────────────────────────

def _get_gov(gouvernorat: str) -> dict:
    """Résoud le nom du gouvernorat (exact → partiel → fallback Tunis)."""
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
    """Génère les 24 points mensuels pour le graphique."""
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


# ── Positionnement ────────────────────────────────────────────────────────────

def _statut_vente(prix_saisi: float, prix_moyen: float) -> tuple[float, str]:
    d = _var_pct(prix_saisi, prix_moyen)
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


def _statut_location(loyer_saisi: float, loyer_moyen: float) -> tuple[float, str]:
    d = _var_pct(loyer_saisi, loyer_moyen)
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

def _reco_vente(gouvernorat: str, type_bien: str, statut: str, tendance: str,
                diff_pct: float, risque: str, taux_annuel: float) -> str:
    ta = round(taux_annuel * 100, 1)
    conseils = {
        "très sous-évalué": (
            f"Opportunité rare : ce {type_bien} est affiché {diff_pct:+.1f}% sous la moyenne du marché à {gouvernorat}. "
            f"Avec un taux de croissance annuel estimé à {ta}%, nous recommandons d'agir rapidement. "
            f"Ce différentiel de prix se comble généralement en 6 à 12 mois."
        ),
        "sous-évalué": (
            f"Bonne entrée de marché : le prix est {diff_pct:+.1f}% sous la moyenne à {gouvernorat}. "
            f"Dans un contexte de marché en {tendance} ({ta}%/an), "
            f"cet écart représente une marge de sécurité favorable à l'achat."
        ),
        "dans la moyenne du marché": (
            f"Prix cohérent avec le marché local à {gouvernorat} (écart : {diff_pct:+.1f}%). "
            f"Avec une tendance de {tendance} à {ta}%/an, "
            + ("le moment est favorable à l'acquisition." if tendance == "hausse"
               else "une négociation modérée (3-5%) reste envisageable.")
        ),
        "légèrement surévalué": (
            f"Le bien est affiché {diff_pct:+.1f}% au-dessus du prix moyen à {gouvernorat}. "
            f"Une négociation de 5 à 10% est conseillée. "
            f"Si le bien présente des atouts distinctifs (vue, standing, étage élevé), "
            f"la prime peut se justifier partiellement."
        ),
        "fortement surévalué": (
            f"Attention : le prix dépasse de {diff_pct:+.1f}% la moyenne du marché à {gouvernorat}. "
            f"Ce niveau ne se justifie que par des caractéristiques exceptionnelles. "
            f"Faites expertiser le bien et négociez fermement avant toute décision."
        ),
    }
    base = conseils.get(statut, f"Prix à {diff_pct:+.1f}% de la moyenne de {gouvernorat}.")
    if risque == "Élevé":
        base += " ⚠ Ce marché présente une volatilité élevée — diversifiez vos placements immobiliers."
    elif risque == "Modéré":
        base += " Le marché local affiche une volatilité modérée à surveiller."
    return base


def _reco_location(gouvernorat: str, composition: str, statut: str, tendance: str,
                   diff_pct: float, risque: str, taux_annuel: float) -> str:
    ta = round(taux_annuel * 100, 1)
    if statut in ("très en dessous du marché", "en dessous du marché"):
        reco = (
            f"Ce loyer ({diff_pct:+.1f}% vs marché) est sous-valorisé pour un {composition} à {gouvernorat}. "
            f"Propriétaire : envisagez une révision à la hausse au prochain renouvellement de bail. "
            f"Locataire : sécurisez ce logement — c'est une bonne affaire dans ce marché en {tendance}."
        )
    elif statut == "aligné avec le marché":
        reco = (
            f"Loyer aligné avec le marché pour un {composition} à {gouvernorat} (écart : {diff_pct:+.1f}%). "
            f"Avec une tendance de {tendance} ({ta}%/an), "
            f"anticipez une progression régulière du loyer de marché sur 24 mois."
        )
    else:
        reco = (
            f"Ce loyer dépasse le marché de {diff_pct:+.1f}% pour un {composition} à {gouvernorat}. "
            f"Propriétaire : ce positionnement peut allonger les délais de location. "
            f"Locataire : négociez ou explorez d'autres options dans ce gouvernorat."
        )
    if risque == "Élevé":
        reco += " ⚠ Volatilité élevée dans ce marché : les loyers peuvent fluctuer significativement."
    return reco


# ── Points d'entrée publics ───────────────────────────────────────────────────

def analyze_vente(
    gouvernorat: str,
    type_bien: str,
    superficie: float,
    prix_m2_saisi: float,
) -> dict:
    """
    Analyse en mode Vente.
    Unité : prix au m² en TND.
    """
    gov = _get_gov(gouvernorat)
    rate = gov["taux_vente_mensuel"]
    rate_annuel = (1 + rate) ** 12 - 1

    type_key = type_bien.lower()
    if type_key not in gov["prix_moyen_m2"]:
        type_key = "appartement"

    prix_moyen_m2 = gov["prix_moyen_m2"][type_key]
    diff_pct, statut = _statut_vente(prix_m2_saisi, prix_moyen_m2)

    h6  = _compound(prix_m2_saisi, rate, 6)
    h12 = _compound(prix_m2_saisi, rate, 12)
    h18 = _compound(prix_m2_saisi, rate, 18)
    h24 = _compound(prix_m2_saisi, rate, 24)

    var24 = _var_pct(h24, prix_m2_saisi)
    tend = _tendance(var24)
    risque = _risk_label(gov)
    reco = _reco_vente(gouvernorat, type_bien, statut, tend, diff_pct, risque, rate_annuel)

    return {
        "mode": "vente",
        "gouvernorat": gouvernorat,
        "type_bien": type_bien,
        "composition": None,
        "superficie": superficie,
        "valeur_saisie": prix_m2_saisi,
        "valeur_totale_actuelle": round(prix_m2_saisi * superficie, 2),
        "prix_moyen_marche": prix_moyen_m2,
        "diff_vs_marche_pct": diff_pct,
        "statut_prix": statut,
        "taux_mensuel": rate,
        "taux_annuel": round(rate_annuel * 100, 2),
        "horizons": {
            "6":  {"valeur": h6,  "variation_pct": _var_pct(h6,  prix_m2_saisi)},
            "12": {"valeur": h12, "variation_pct": _var_pct(h12, prix_m2_saisi)},
            "18": {"valeur": h18, "variation_pct": _var_pct(h18, prix_m2_saisi)},
            "24": {"valeur": h24, "variation_pct": _var_pct(h24, prix_m2_saisi)},
        },
        "tendance": tend,
        "risque": risque,
        "tension": gov["tension"],
        "analyse_marche": gov["description"],
        "facteurs": gov["facteurs"],
        "recommandation": reco,
        "points": _build_points(prix_m2_saisi, rate, gov["volatilite"]),
    }


def analyze_location(
    gouvernorat: str,
    composition: str,
    loyer_saisi: float,
) -> dict:
    """
    Analyse en mode Location.
    Unité : loyer mensuel en TND selon composition (S+1 / S+2 / S+3 / S+4).
    """
    gov = _get_gov(gouvernorat)
    rate = gov["taux_location_mensuel"]
    rate_annuel = (1 + rate) ** 12 - 1

    comp = composition if composition in gov["loyers_moyens"] else "S+2"
    loyer_moyen = gov["loyers_moyens"][comp]
    diff_pct, statut = _statut_location(loyer_saisi, loyer_moyen)

    h6  = _compound(loyer_saisi, rate, 6)
    h12 = _compound(loyer_saisi, rate, 12)
    h18 = _compound(loyer_saisi, rate, 18)
    h24 = _compound(loyer_saisi, rate, 24)

    var24 = _var_pct(h24, loyer_saisi)
    tend = _tendance(var24)
    risque = _risk_label(gov)
    reco = _reco_location(gouvernorat, comp, statut, tend, diff_pct, risque, rate_annuel)

    return {
        "mode": "location",
        "gouvernorat": gouvernorat,
        "type_bien": None,
        "composition": comp,
        "superficie": None,
        "valeur_saisie": loyer_saisi,
        "valeur_totale_actuelle": None,
        "prix_moyen_marche": loyer_moyen,
        "diff_vs_marche_pct": diff_pct,
        "statut_prix": statut,
        "taux_mensuel": rate,
        "taux_annuel": round(rate_annuel * 100, 2),
        "horizons": {
            "6":  {"valeur": h6,  "variation_pct": _var_pct(h6,  loyer_saisi)},
            "12": {"valeur": h12, "variation_pct": _var_pct(h12, loyer_saisi)},
            "18": {"valeur": h18, "variation_pct": _var_pct(h18, loyer_saisi)},
            "24": {"valeur": h24, "variation_pct": _var_pct(h24, loyer_saisi)},
        },
        "tendance": tend,
        "risque": risque,
        "tension": gov["tension"],
        "analyse_marche": gov["description"],
        "facteurs": gov["facteurs"],
        "recommandation": reco,
        "points": _build_points(loyer_saisi, rate, gov["volatilite"]),
    }
