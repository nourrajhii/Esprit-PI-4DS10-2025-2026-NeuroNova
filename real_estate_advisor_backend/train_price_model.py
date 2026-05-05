"""
Script d'entraînement du modèle de prédiction de prix.
À exécuter depuis le dossier real_estate_advisor_backend :

    python train_price_model.py

Génère : app/ml/price_model.pkl
"""

import os
import pickle
import pandas as pd
import numpy as np

CSV_PATH   = "ai_ready_listings.csv"
MODEL_DIR  = "app/ml"
MODEL_PATH = os.path.join(MODEL_DIR, "price_model.pkl")

# ── 1. Chargement ─────────────────────────────────────────────────────────────
print("📂 Chargement du CSV...")
df = pd.read_csv(CSV_PATH)
print(f"   {len(df)} lignes brutes")

# ── 2. Nettoyage ──────────────────────────────────────────────────────────────
# Garder uniquement les vrais prix d'appartements (>= 100 000 DT)
# Les prix < 10 000 sont des prix au m² ou terrains mal scrapés
dfB = df[df["price"] >= 100_000].copy()
dfB = dfB[dfB["rooms"] <= 10]
dfB = dfB[(dfB["surface_m2"] >= 20) & (dfB["surface_m2"] <= 5000)]

BLACKLIST_TITLES = [
    "PROPOS DE CE BIEN", "Dcouvrez des annonces immobilires",
    "les plus rcentes.", "BALLOUCHI.COM",
    "Liste des maisons ou villas vendre", "Liste locaux commerciaux et bureaux vendre",
    "Liste des appartements vendre", "Liste des villas vendre",
    "PROPRITS VENDRE", "Vente", "Dtail du bien",
    "Liste des terrains vendre", "Terrain vendre",
]
dfB = dfB[~dfB["title"].isin(BLACKLIST_TITLES)]
dfB = dfB.drop_duplicates(subset=["price", "surface_m2", "city", "rooms"])

p5, p95 = dfB["price"].quantile(0.05), dfB["price"].quantile(0.95)
dfB = dfB[(dfB["price"] >= p5) & (dfB["price"] <= p95)]

dfB["city"]             = dfB["city"].str.strip().str.title()
dfB["property_type"]    = dfB["property_type"].str.strip().str.lower()
dfB["transaction_type"] = dfB["transaction_type"].str.strip().str.lower()

print(f"   {len(dfB)} biens immobiliers propres")

# ── 3. Statistiques de marché par ville ──────────────────────────────────────
dfB["prix_m2"] = dfB["price"] / dfB["surface_m2"]

market_stats = dfB.groupby("city").agg(
    prix_m2_q25    = ("prix_m2", lambda x: x.quantile(0.25)),
    prix_m2_median = ("prix_m2", "median"),
    prix_m2_q75    = ("prix_m2", lambda x: x.quantile(0.75)),
    prix_m2_mean   = ("prix_m2", "mean"),
    prix_median    = ("price",   "median"),
    count          = ("price",   "count"),
).to_dict(orient="index")

global_stats = {
    "prix_m2_q25":    float(dfB["prix_m2"].quantile(0.25)),
    "prix_m2_median": float(dfB["prix_m2"].median()),
    "prix_m2_q75":    float(dfB["prix_m2"].quantile(0.75)),
    "prix_m2_mean":   float(dfB["prix_m2"].mean()),
    "prix_median":    float(dfB["price"].median()),
    "count":          len(dfB),
}

# ── 4. Facteur de correction par nombre de pièces ────────────────────────────
rooms_factor = {}
global_pm2_med = global_stats["prix_m2_median"]
for r in range(1, 11):
    sub = dfB[dfB["rooms"] == r]["prix_m2"]
    rooms_factor[r] = float(sub.median() / global_pm2_med) if len(sub) >= 5 else 1.0

# ── 5. Affichage ──────────────────────────────────────────────────────────────
print("\n📊 Statistiques de marché :")
for city, stats in market_stats.items():
    print(f"   {city:12s} | {stats['count']:4d} biens "
          f"| {stats['prix_m2_q25']:,.0f}–{stats['prix_m2_median']:,.0f}–"
          f"{stats['prix_m2_q75']:,.0f} DT/m²")

print("\n🔮 Tests de prédiction :")
for surf, rooms, city in [(120, 3, "Tunis"), (80, 2, "Tunis"), (200, 4, "Tunis")]:
    cs   = market_stats.get(city, global_stats)
    fact = rooms_factor.get(rooms, 1.0)
    lo   = cs["prix_m2_q25"]    * fact * surf
    mid  = cs["prix_m2_median"] * fact * surf
    hi   = cs["prix_m2_q75"]    * fact * surf
    print(f"   {surf}m² {rooms}p {city}: {lo:,.0f} → {mid:,.0f} → {hi:,.0f} DT")

# ── 6. Sauvegarde ─────────────────────────────────────────────────────────────
os.makedirs(MODEL_DIR, exist_ok=True)
model_data = {
    "approach":          "market_stats_with_rooms_factor",
    "market_stats":      market_stats,
    "global_stats":      global_stats,
    "rooms_factor":      rooms_factor,
    "cities":            sorted(dfB["city"].unique().tolist()),
    "property_types":    sorted(dfB["property_type"].unique().tolist()),
    "transaction_types": sorted(dfB["transaction_type"].unique().tolist()),
    "n_samples":         len(dfB),
    "price_min":         float(dfB["price"].min()),
    "price_max":         float(dfB["price"].max()),
    "price_mean":        float(dfB["price"].mean()),
}
with open(MODEL_PATH, "wb") as f:
    pickle.dump(model_data, f)

print(f"\n✅ Modèle sauvegardé → {MODEL_PATH}")
print(f"   Basé sur {len(dfB)} biens réels tunisiens")
