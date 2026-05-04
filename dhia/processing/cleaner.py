"""
==============================================================================
EstateMind AI Data Cleaning Layer
==============================================================================
Stage 1 of the ML pipeline.

Responsibilities:
  - Fetch raw listings from MongoDB.
  - Filter to Tunisia-only listings (blacklist international keywords).
  - Remove corrupted / placeholder records (bad price, surface, etc.).
  - Normalize free-text fields (strip emojis, extra spaces, etc.).
  - Output → Cleaned Pandas DataFrame passed to feature_engineering.py.
==============================================================================
"""

import logging
import re
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Geography filters
# ─────────────────────────────────────────────────────────────────────────────
TUNISIA_KEYWORDS = [
    "tunis", "ariana", "ben arous", "manouba", "nabeul", "sousse", "monastir",
    "mahdia", "sfax", "kairouan", "kasserine", "sidi bouzid", "gabes", "medenine",
    "tataouine", "gafsa", "tozeur", "kebili", "bizerte", "beja", "jendouba",
    "kef", "siliana", "zaghouan", "tunisie", "tunisia", "djerba", "hammamet",
    "marsa", "lac", "ennasr", "menzah", "cite olympique", "el menzah",
    "charguia", "el aouina", "jardins el menzah"
]

EXCLUDED_KEYWORDS = [
    "paris", "marseille", "lyon", "nice", "nantes", "strasbourg", "montpellier",
    "bordeaux", "lille", "rennes", "toulouse", "france", "belgique", "maroc",
    "algerie", "casablanca", "alger", "espagne", "italie", "canada",
]

# ─────────────────────────────────────────────────────────────────────────────
# Type mappings for normalization
# ─────────────────────────────────────────────────────────────────────────────
PROPERTY_TYPE_MAP = {
    "appartement": "appartement",
    "appart": "appartement",
    "appt": "appartement",
    "villa": "villa",
    "maison": "maison",
    "local commercial": "local_commercial",
    "local": "local_commercial",
    "studio": "studio",
    "bureau": "bureau",
    "terrain": "terrain",
    "lot": "terrain",
    "parking": "parking",
    "duplex": "duplex",
    "triplex": "triplex",
    "chalet": "chalet",
}

TRANSACTION_TYPE_MAP = {
    "vente": "vente",
    "sale": "vente",
    "achat": "vente",
    "à vendre": "vente",
    "location": "location",
    "louer": "location",
    "rent": "location",
    "à louer": "location",
}

CITY_NORMALIZER = {
    "lac 1": "Les Berges du Lac",
    "lac 2": "Les Berges du Lac 2",
    "berges du lac": "Les Berges du Lac",
    "marsa": "La Marsa",
    "el menzah": "El Menzah",
    "menzah": "El Menzah",
    "el manar": "El Manar",
    "ennasr": "Ennasr",
    "la soukra": "Soukra",
    "ain zaghouan": "Ain Zaghouan",
    "ariana": "Ariana",
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _is_tunisian(title: str, description: str, city: str) -> bool:
    text = f"{title} {description} {city}".lower()
    has_tn = any(kw in text for kw in TUNISIA_KEYWORDS)
    is_foreign = any(kw in text for kw in EXCLUDED_KEYWORDS)
    return has_tn and not is_foreign

def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    # Remove emojis and non-printable characters
    text = re.sub(r'[^\x20-\x7Eàâäéèêëîïôùûüçœæ\u0600-\u06FF\s]', '', text)
    # Collapse whitespace
    return re.sub(r'\s+', ' ', text).strip()

def _normalize_city(city: Optional[str]) -> str:
    if not city:
        return "Unknown"
    key = city.lower().strip()
    return CITY_NORMALIZER.get(key, city.strip().title())

def _map_property_type(raw: Optional[str]) -> str:
    if not raw:
        return "appartement"
    raw_l = raw.lower().strip()
    for k, v in PROPERTY_TYPE_MAP.items():
        if k in raw_l:
            return v
    return raw_l

def _map_transaction_type(raw: Optional[str]) -> str:
    if not raw:
        return "vente"
    raw_l = raw.lower().strip()
    for k, v in TRANSACTION_TYPE_MAP.items():
        if k in raw_l:
            return v
    return raw_l

# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline function
# ─────────────────────────────────────────────────────────────────────────────
async def run_cleaning_pipeline() -> int:
    """
    Fetches raw listings from MongoDB, cleans them, and saves a standardized
    intermediate CSV: cleaned_listings.csv

    Returns the number of listings that passed all filters.
    """
    from database.models import Listing
    logger.info("─" * 60)
    logger.info("STAGE 1 │ Data Cleaning Starting…")

    all_listings = await Listing.find_all().to_list()
    logger.info(f"  Fetched {len(all_listings)} raw listings from MongoDB.")

    cleaned_rows = []
    rejected = {"not_tn": 0, "bad_price": 0, "bad_surface": 0}

    for item in all_listings:
        title = _clean_text(item.title)
        desc  = _clean_text(item.description or "")
        city  = _normalize_city(item.city)
        price = item.price or 0.0

        # ── Infer Transaction Type (DSO Metadata Fix) ─────────────────────
        txn = _map_transaction_type(item.transaction_type)
        if txn == "vente": # Double check
            txt = f"{title} {desc} {item.listing_url}".lower()
            if "louer" in txt or "location" in txt or price < 20000:
                txn = "location"

        # ── Geography filter ──────────────────────────────────────────────
        if not _is_tunisian(title, desc, city):
            rejected["not_tn"] += 1
            continue

        # ── Quality thresholds ────────────────────────────────────────────
        price = item.price or 0.0
        # Tunisian real estate: 500 TND min (cheap land), 5M TND max (luxury villa)
        if not (500 <= price <= 5_000_000):
            rejected["bad_price"] += 1
            continue

        surface = item.surface_m2 or 0.0
        # Reasonable residential range: 20m² (studio) to 1000m² (large villa)
        if not (20 <= surface <= 1_000):
            rejected["bad_surface"] += 1
            continue

        rooms = item.rooms or 0
        # Max 15 rooms — anything above is a scraping error
        if rooms < 0 or rooms > 15:
            rooms = max(1, min(rooms, 15))

        bathrooms = max(1, min(item.bathrooms or 1, 10))  # cap bathrooms at 10
        cleaned_rows.append({
            "id":               str(item.id),
            "title":            title,
            "price":            price,
            "city":             city,
            "zone":             _clean_text(item.zone) or city,
            "property_type":    _map_property_type(item.property_type),
            "transaction_type": txn,
            "surface_m2":       surface,
            "rooms":            max(rooms, 1),
            "bathrooms":        bathrooms,
            "description":      desc,
            "listing_url":      item.listing_url,
        })

    df = pd.DataFrame(cleaned_rows)
    df.to_csv("pipeline/cleaned_listings.csv", index=False, encoding="utf-8")

    logger.info(f"  ✅ Kept  : {len(df)}")
    logger.info(f"  ❌ Rejected (not Tunisia)  : {rejected['not_tn']}")
    logger.info(f"  ❌ Rejected (bad price)    : {rejected['bad_price']}")
    logger.info(f"  ❌ Rejected (bad surface)  : {rejected['bad_surface']}")
    logger.info("STAGE 1 │ Complete → pipeline/cleaned_listings.csv")
    logger.info("─" * 60)
    return len(df)
