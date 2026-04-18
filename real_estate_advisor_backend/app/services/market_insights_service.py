"""
app/services/market_insights_service.py

Service d'analyse de marché immobilier.
Calcule des statistiques, tendances et détecte les opportunités depuis la BDD.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models.apartment import Apartment
from typing import Optional


# ── Titres parasites à ignorer ────────────────────────────────────────────────
BLACKLIST_TITLES = {
    "propos de ce bien", "dcouvrez des annonces immobilires",
    "les plus rcentes.", "ballouchi.com",
    "liste des maisons ou villas vendre",
    "liste locaux commerciaux et bureaux vendre",
    "liste des appartements vendre", "liste des villas vendre",
    "proprits vendre", "vente", "dtail du bien",
    "liste des terrains vendre", "terrain vendre",
    "les annonces des locaux commerciaux vendre",
    "les annonces des locaux pour professionnels vendre",
}


def _is_valid_apt(apt) -> bool:
    title = (apt.title or "").lower().strip()
    if any(bl in title for bl in BLACKLIST_TITLES):
        return False
    price   = float(apt.price      or 0)
    surface = float(apt.surface_m2 or 0)
    rooms   = int(apt.rooms        or 0)
    # ✅ Seuil abaissé à 1000 DT pour couvrir location + vente
    return price >= 1_000 and 10 <= surface <= 10_000 and rooms <= 20


def _percentile(values: list, p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = int(len(sorted_v) * p / 100)
    return float(sorted_v[min(idx, len(sorted_v) - 1)])


def get_market_insights(db: Session) -> dict:
    """
    Retourne une analyse complète du marché immobilier depuis la BDD.

    Inclut :
    - Statistiques globales (prix moyen, médian, prix/m²)
    - Distribution par tranche de prix
    - Statistiques par nombre de pièces
    - Top 5 meilleures opportunités (meilleur rapport qualité/prix)
    - Top 5 biens premium (prix/m² le plus élevé)
    - Indicateurs de marché (tension, accessibilité)
    """

    # ── 1. Récupération et filtrage ───────────────────────────────────────────
    all_apts = db.query(Apartment).limit(2000).all()
    apts     = [a for a in all_apts if _is_valid_apt(a)]

    if not apts:
        return {"error": "Aucune donnée disponible"}

    prices    = [float(a.price      or 0) for a in apts]
    surfaces  = [float(a.surface_m2 or 0) for a in apts]
    pm2_list  = [p / s for p, s in zip(prices, surfaces) if s > 0]
    n         = len(apts)

    # ── 2. Statistiques globales ──────────────────────────────────────────────
    avg_price    = sum(prices) / n
    median_price = _percentile(prices, 50)
    avg_pm2      = sum(pm2_list) / len(pm2_list)
    median_pm2   = _percentile(pm2_list, 50)
    avg_surface  = sum(surfaces) / n

    global_stats = {
        "total_biens":      n,
        "prix_moyen":       round(avg_price,   2),
        "prix_median":      round(median_price, 2),
        "prix_min":         round(min(prices),  2),
        "prix_max":         round(max(prices),  2),
        "pm2_moyen":        round(avg_pm2,      2),
        "pm2_median":       round(median_pm2,   2),
        "pm2_q25":          round(_percentile(pm2_list, 25), 2),
        "pm2_q75":          round(_percentile(pm2_list, 75), 2),
        "surface_moyenne":  round(avg_surface,  2),
        "surface_mediane":  round(_percentile(surfaces, 50), 2),
    }

    # ── 3. Distribution par tranche de prix ──────────────────────────────────
    tranches = {
        "< 150k":     0,
        "150k–300k":  0,
        "300k–500k":  0,
        "500k–800k":  0,
        "800k–1M":    0,
        "> 1M":       0,
    }
    for p in prices:
        if   p < 150_000:   tranches["< 150k"]    += 1
        elif p < 300_000:   tranches["150k–300k"] += 1
        elif p < 500_000:   tranches["300k–500k"] += 1
        elif p < 800_000:   tranches["500k–800k"] += 1
        elif p < 1_000_000: tranches["800k–1M"]   += 1
        else:               tranches["> 1M"]       += 1

    distribution = [
        {"tranche": k, "count": v, "pct": round(v / n * 100, 1)}
        for k, v in tranches.items()
    ]

    # ── 4. Stats par nombre de pièces ────────────────────────────────────────
    from collections import defaultdict
    rooms_data = defaultdict(list)
    for apt in apts:
        r = int(apt.rooms or 0)
        if 1 <= r <= 8:
            rooms_data[r].append({
                "price":   float(apt.price      or 0),
                "surface": float(apt.surface_m2 or 0),
                "pm2":     float(apt.price or 0) / float(apt.surface_m2 or 1),
            })

    stats_par_rooms = []
    for r in sorted(rooms_data.keys()):
        items = rooms_data[r]
        pr    = [i["price"]   for i in items]
        pm2s  = [i["pm2"]     for i in items]
        surfs = [i["surface"] for i in items]
        stats_par_rooms.append({
            "rooms":           r,
            "count":           len(items),
            "prix_median":     round(_percentile(pr,   50), 2),
            "pm2_median":      round(_percentile(pm2s, 50), 2),
            "surface_mediane": round(_percentile(surfs,50), 2),
        })

    # ── 5. Top 5 opportunités (meilleur rapport surface/prix) ─────────────────
    apt_scores = []
    for apt in apts:
        price   = float(apt.price      or 0)
        surface = float(apt.surface_m2 or 0)
        if price <= 0 or surface <= 0:
            continue
        # Score opportunité = surface / prix (m² par DT) normalisé
        opp_score = surface / price
        apt_scores.append((apt, opp_score))

    apt_scores.sort(key=lambda x: x[1], reverse=True)
    top_opportunities = [
        {
            "id":          a.id,
            "title":       (a.title or "")[:60],
            "price":       float(a.price      or 0),
            "surface_m2":  float(a.surface_m2 or 0),
            "rooms":       int(a.rooms        or 0),
            "pm2":         round(float(a.price or 0) / float(a.surface_m2 or 1), 2),
            "url":         a.url or "",
        }
        for a, _ in apt_scores[:5]
    ]

    # ── 6. Top 5 premium (prix/m² le plus élevé) ────────────────────────────
    apt_pm2 = []
    for apt in apts:
        price   = float(apt.price      or 0)
        surface = float(apt.surface_m2 or 0)
        if surface > 0:
            apt_pm2.append((apt, price / surface))

    apt_pm2.sort(key=lambda x: x[1], reverse=True)
    top_premium = [
        {
            "id":         a.id,
            "title":      (a.title or "")[:60],
            "price":      float(a.price      or 0),
            "surface_m2": float(a.surface_m2 or 0),
            "rooms":      int(a.rooms        or 0),
            "pm2":        round(pm2, 2),
            "url":        a.url or "",
        }
        for a, pm2 in apt_pm2[:5]
    ]

    # ── 7. Indicateurs de marché ─────────────────────────────────────────────
    # Tension : ratio biens > 500k vs total
    above_500k = sum(1 for p in prices if p >= 500_000)
    tension_pct = round(above_500k / n * 100, 1)

    # Accessibilité : % de biens sous 300k (accessible classe moyenne)
    accessible = sum(1 for p in prices if p <= 300_000)
    accessible_pct = round(accessible / n * 100, 1)

    # Fourchette typique (IQR)
    iqr_low  = round(_percentile(prices, 25), 2)
    iqr_high = round(_percentile(prices, 75), 2)

    market_indicators = {
        "biens_premium_pct":    tension_pct,       # % > 500k
        "biens_accessibles_pct": accessible_pct,   # % < 300k
        "fourchette_typique": {
            "min": iqr_low,
            "max": iqr_high,
        },
        "pm2_fourchette": {
            "bas":   round(_percentile(pm2_list, 25), 2),
            "mid":   round(_percentile(pm2_list, 50), 2),
            "haut":  round(_percentile(pm2_list, 75), 2),
        },
    }

    return {
        "global_stats":       global_stats,
        "distribution_prix":  distribution,
        "stats_par_rooms":    stats_par_rooms,
        "top_opportunites":   top_opportunities,
        "top_premium":        top_premium,
        "market_indicators":  market_indicators,
    }
