"""
seed_from_csv.py — Importe properties.csv dans la table apartments.

CSV columns: category, room_count, bathroom_count, size, type, price, city, region, log_price
DB  columns: id, title, price, city, property_type, surface_m2, rooms, bathrooms, transaction_type, url

Mapping:
  category       → property_type  (+ classify)
  room_count     → rooms          (-1 → NULL)
  bathroom_count → bathrooms      (-1 → NULL)
  size           → surface_m2     (-1 → NULL)
  type           → transaction_type ("À Vendre"→vente, "À Louer"→location)
  price          → price
  city           → city
  region         → appended to title as "region - category"
"""
import csv
import hashlib
import os

import pymysql

# ── Connection (direct pymysql, no SQLAlchemy to skip cryptography dep) ────────
conn = pymysql.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "advisor"),
    password=os.getenv("DB_PASSWORD", "advisorpass"),
    database=os.getenv("DB_NAME", "real_estate_advisor_db"),
    charset="utf8mb4",
)
cur = conn.cursor()

CSV_PATH = os.path.join(os.path.dirname(__file__), "app", "data", "properties.csv")

CATEGORY_MAP = {
    "Appartements": "appartement",
    "Villas": "villa",
    "Maisons": "maison",
    "Studios": "studio",
    "Duplex": "duplex",
    "Terrains et Fermes": "terrain",
    "Bureaux et Plateaux": "bureau",
    "Magasins, Commerces et Locaux industriels": "local commercial",
    "Locations de vacances": "appartement",
    "Immeubles": "immeuble",
    "Garages et Parkings": "parking",
    "Colocations": "appartement",
}


def map_transaction(raw: str) -> str:
    r = raw.strip()
    if "vendre" in r.lower() or "vente" in r.lower():
        return "vente"
    if "louer" in r.lower() or "location" in r.lower():
        return "location"
    return "vente"


def safe_float(v: str) -> float | None:
    try:
        f = float(v)
        return None if f < 0 else f
    except (ValueError, TypeError):
        return None


def safe_int(v: str) -> int | None:
    try:
        i = int(float(v))
        return None if i < 0 else i
    except (ValueError, TypeError):
        return None


# ── Truncate and reload ────────────────────────────────────────────────────────
print("Truncating apartments table …")
cur.execute("TRUNCATE TABLE apartments")

INSERT_SQL = """
INSERT INTO apartments (id, title, price, city, property_type, surface_m2, rooms, bathrooms, transaction_type, url)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE price=VALUES(price)
"""

batch = []
BATCH_SIZE = 500
total = 0
skipped = 0

with open(CSV_PATH, encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        price = safe_float(row.get("price", ""))
        # Skip invalid prices and clamp to DECIMAL(12,2) max = 9,999,999,999.99
        if price is None or price <= 0 or price > 9_999_999_999:
            skipped += 1
            continue

        category_raw = row.get("category", "").strip()
        prop_type = CATEGORY_MAP.get(category_raw, category_raw.lower() or "appartement")
        city = row.get("city", "").strip() or None
        region = row.get("region", "").strip()
        transaction = map_transaction(row.get("type", ""))
        rooms = safe_int(row.get("room_count", ""))
        baths = safe_int(row.get("bathroom_count", ""))
        surface = safe_float(row.get("size", ""))

        # Build a descriptive title from available data
        tx_label = "À Vendre" if transaction == "vente" else "À Louer"
        rooms_label = f"S+{rooms}" if rooms and rooms > 0 else ""
        parts = [tx_label, category_raw]
        if rooms_label:
            parts.append(rooms_label)
        if region:
            parts.append(region)
        if city and city != region:
            parts.append(city)
        title = " — ".join(parts)

        # Stable ID from content hash
        uid = hashlib.md5(f"{i}|{price}|{city}|{prop_type}|{rooms}|{surface}".encode()).hexdigest()[:24]

        batch.append((uid, title, price, city, prop_type, surface, rooms, baths, transaction, None))

        if len(batch) >= BATCH_SIZE:
            cur.executemany(INSERT_SQL, batch)
            conn.commit()
            total += len(batch)
            print(f"  Inserted {total} rows …", end="\r")
            batch.clear()

if batch:
    cur.executemany(INSERT_SQL, batch)
    conn.commit()
    total += len(batch)

print(f"\nDone. Inserted: {total}, Skipped (no price): {skipped}")
cur.execute("SELECT COUNT(*) FROM apartments")
print(f"Total in DB: {cur.fetchone()[0]}")
cur.close()
conn.close()
