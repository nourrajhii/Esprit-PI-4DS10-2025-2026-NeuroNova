"""
app/services/market_insights_service.py

Market analysis — now reads from a MongoDB collection (pymongo) instead of SQLAlchemy.
The collection parameter is a pymongo Collection object yielded by get_db().
"""
from collections import defaultdict


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


def _is_valid(doc) -> bool:
    title = (doc.get("title") or "").lower().strip()
    if any(bl in title for bl in BLACKLIST_TITLES):
        return False
    price   = float(doc.get("price")      or 0)
    surface = float(doc.get("surface_m2") or 0)
    rooms   = int(doc.get("rooms")        or 0)
    return price >= 1_000 and 10 <= surface <= 10_000 and rooms <= 20


def _percentile(values: list, p: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = int(len(sorted_v) * p / 100)
    return float(sorted_v[min(idx, len(sorted_v) - 1)])


def get_market_insights(col) -> dict:
    """
    Accepts a pymongo Collection and returns full market analysis.
    """
    all_docs = list(col.find({}, limit=2000))
    docs = [d for d in all_docs if _is_valid(d)]

    if not docs:
        return {"error": "Aucune donnée disponible"}

    prices   = [float(d.get("price")      or 0) for d in docs]
    surfaces = [float(d.get("surface_m2") or 0) for d in docs]
    pm2_list = [p / s for p, s in zip(prices, surfaces) if s > 0]
    n        = len(docs)

    avg_price    = sum(prices) / n
    median_price = _percentile(prices, 50)
    avg_pm2      = sum(pm2_list) / len(pm2_list) if pm2_list else 0
    median_pm2   = _percentile(pm2_list, 50)
    avg_surface  = sum(surfaces) / n

    global_stats = {
        "total_biens":      n,
        "prix_moyen":       round(avg_price,    2),
        "prix_median":      round(median_price,  2),
        "prix_min":         round(min(prices),   2),
        "prix_max":         round(max(prices),   2),
        "pm2_moyen":        round(avg_pm2,       2),
        "pm2_median":       round(median_pm2,    2),
        "pm2_q25":          round(_percentile(pm2_list, 25), 2),
        "pm2_q75":          round(_percentile(pm2_list, 75), 2),
        "surface_moyenne":  round(avg_surface,   2),
        "surface_mediane":  round(_percentile(surfaces, 50), 2),
    }

    tranches = {"< 150k": 0, "150k–300k": 0, "300k–500k": 0,
                "500k–800k": 0, "800k–1M": 0, "> 1M": 0}
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

    rooms_data: dict = defaultdict(list)
    for d in docs:
        r = int(d.get("rooms") or 0)
        if 1 <= r <= 8:
            p = float(d.get("price") or 0)
            s = float(d.get("surface_m2") or 1)
            rooms_data[r].append({"price": p, "surface": s, "pm2": p / s})

    stats_par_rooms = []
    for r in sorted(rooms_data.keys()):
        items = rooms_data[r]
        pr    = [i["price"]   for i in items]
        pm2s  = [i["pm2"]     for i in items]
        surfs = [i["surface"] for i in items]
        stats_par_rooms.append({
            "rooms":           r,
            "count":           len(items),
            "prix_median":     round(_percentile(pr,    50), 2),
            "pm2_median":      round(_percentile(pm2s,  50), 2),
            "surface_mediane": round(_percentile(surfs, 50), 2),
        })

    apt_scores = []
    for d in docs:
        p = float(d.get("price") or 0)
        s = float(d.get("surface_m2") or 0)
        if p > 0 and s > 0:
            apt_scores.append((d, s / p))
    apt_scores.sort(key=lambda x: x[1], reverse=True)

    top_opportunities = [
        {
            "id":         str(d.get("_id", "")),
            "title":      (d.get("title") or "")[:60],
            "price":      float(d.get("price") or 0),
            "surface_m2": float(d.get("surface_m2") or 0),
            "rooms":      int(d.get("rooms") or 0),
            "pm2":        round(float(d.get("price") or 0) / float(d.get("surface_m2") or 1), 2),
            "url":        d.get("listing_url") or d.get("url") or "",
            "image_urls": d.get("image_urls") or [],
        }
        for d, _ in apt_scores[:5]
    ]

    apt_pm2 = []
    for d in docs:
        p = float(d.get("price") or 0)
        s = float(d.get("surface_m2") or 0)
        if s > 0:
            apt_pm2.append((d, p / s))
    apt_pm2.sort(key=lambda x: x[1], reverse=True)

    top_premium = [
        {
            "id":         str(d.get("_id", "")),
            "title":      (d.get("title") or "")[:60],
            "price":      float(d.get("price") or 0),
            "surface_m2": float(d.get("surface_m2") or 0),
            "rooms":      int(d.get("rooms") or 0),
            "pm2":        round(pm2, 2),
            "url":        d.get("listing_url") or d.get("url") or "",
            "image_urls": d.get("image_urls") or [],
        }
        for d, pm2 in apt_pm2[:5]
    ]

    above_500k     = sum(1 for p in prices if p >= 500_000)
    accessible     = sum(1 for p in prices if p <= 300_000)

    market_indicators = {
        "biens_premium_pct":     round(above_500k / n * 100, 1),
        "biens_accessibles_pct": round(accessible  / n * 100, 1),
        "fourchette_typique":    {"min": round(_percentile(prices, 25), 2),
                                  "max": round(_percentile(prices, 75), 2)},
        "pm2_fourchette":        {"bas":  round(_percentile(pm2_list, 25), 2),
                                  "mid":  round(_percentile(pm2_list, 50), 2),
                                  "haut": round(_percentile(pm2_list, 75), 2)},
    }

    return {
        "global_stats":      global_stats,
        "distribution_prix": distribution,
        "stats_par_rooms":   stats_par_rooms,
        "top_opportunites":  top_opportunities,
        "top_premium":       top_premium,
        "market_indicators": market_indicators,
    }
