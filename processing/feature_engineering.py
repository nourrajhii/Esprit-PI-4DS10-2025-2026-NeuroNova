"""
==============================================================================
EstateMind AI Feature Engineering Layer
==============================================================================
Stage 2 of the ML pipeline.

Responsibilities:
  - Load cleaned_listings.csv from Stage 1.
  - Derive rich features for a price-prediction model.
  - Encode categoricals (Label / One-Hot depending on cardinality).
  - Scale numerics (StandardScaler / RobustScaler).
  - Split into train / test sets.
  - Output Final ready-to-train files:
        pipeline/X_train.csv   pipeline/X_test.csv
        pipeline/y_train.csv   pipeline/y_test.csv
        pipeline/feature_names.txt
        pipeline/feature_report.csv   (for inspection / EDA)
==============================================================================
"""

import logging
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, RobustScaler

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Tunisian city tier mapping (for a numeric "location value" feature)
# ─────────────────────────────────────────────────────────────────────────────
CITY_TIER = {
    # Prime locations
    "Les Berges du Lac": 5, "Les Berges du Lac 2": 5,
    "La Marsa": 5, "Carthage": 5, "Sidi Bou Said": 5,
    "Ennasr": 4, "El Menzah": 4, "El Manar": 4,
    # Tunis urban
    "Tunis": 3, "Ariana": 3, "Ben Arous": 3, "Manouba": 3,
    "Soukra": 3, "Ain Zaghouan": 3, "El Omrane": 3,
    # Coastal secondary
    "Sousse": 2, "Hammamet": 2, "Nabeul": 2, "Monastir": 2,
    "Mahdia": 2, "Sfax": 2, "Bizerte": 2,
    # Interior / rural
    "Kairouan": 1, "Kasserine": 1, "Sidi Bouzid": 1,
    "Gabes": 1, "Medenine": 1, "Tataouine": 1, "Gafsa": 1,
}

AXE_CATEGORIES = ["appartement", "villa", "maison", "studio", "duplex", "triplex"]

def _city_tier(city: str) -> int:
    return CITY_TIER.get(city, 2)   # Default tier 2 for unlisted cities

def _property_tier(prop: str) -> int:
    """Assign rough luxury tier to property type."""
    tiers = {"villa": 5, "duplex": 4, "triplex": 4, "maison": 3,
             "appartement": 2, "studio": 1, "local_commercial": 2,
             "bureau": 2, "terrain": 1, "parking": 1}
    return tiers.get(prop, 2)

def run_feature_engineering():
    """
    Loads pipeline/cleaned_listings.csv; enriches features; exports train/test.
    """
    import os
    os.makedirs("pipeline", exist_ok=True)

    logger.info("─" * 60)
    logger.info("STAGE 2 │ Feature Engineering Starting…")

    df = pd.read_csv("pipeline/cleaned_listings.csv")
    n_raw = len(df)
    logger.info(f"  Loaded {n_raw} cleaned rows.")

    # ── Focus ML Model exclusively on VENTE (Sales) ───────────────────────
    df = df[df["transaction_type"] == "vente"].copy()
    logger.info(f"  Filtered to {len(df)} 'vente' (sales) listings for pricing model.")
    
    # ── Duplicate & Fraud Removal (DSO 2) ─────────────────────────────────
    df_valid = df[(df['price'] > 5000) & (df['surface_m2'] > 10)]
    duplicates = df_valid[df_valid.duplicated(subset=['city', 'surface_m2', 'price', 'rooms', 'bathrooms'], keep=False)]
    df = df.drop(duplicates.index)
    logger.info(f"  Dropped {len(duplicates)} duplicate/spam listings (DSO Fraud Detection).")

    # ── IQR Outlier Removal (belt-and-suspenders after cleaning) ─────────
    for col in ["price", "surface_m2"]:
        Q1, Q3 = df[col].quantile(0.05), df[col].quantile(0.95)
        df = df[(df[col] >= Q1) & (df[col] <= Q3)]
    logger.info(f"  After IQR filter: {len(df)} rows")

    # ── Derived numeric features ──────────────────────────────────────────
    df["price_per_m2"]   = (df["price"] / df["surface_m2"]).round(2)
    df["log_price"]      = np.log1p(df["price"])          # Target for model
    df["log_surface"]    = np.log1p(df["surface_m2"])
    df["rooms_per_m2"]   = (df["rooms"] / df["surface_m2"]).round(4)
    df["total_rooms"]    = df["rooms"] + df["bathrooms"]
    df["city_tier"]      = df["city"].apply(_city_tier)
    df["prop_tier"]      = df["property_type"].apply(_property_tier)
    df["is_sale"]        = (df["transaction_type"] == "vente").astype(int)
    df["is_apartment"]   = (df["property_type"] == "appartement").astype(int)
    df["is_villa"]       = (df["property_type"] == "villa").astype(int)
    df["is_studio"]      = (df["property_type"] == "studio").astype(int)

    # ── Categoricals: Low-cardinality → One-Hot ───────────────────────────
    prop_dummies = pd.get_dummies(df["property_type"], prefix="type", drop_first=False)
    txn_dummies  = pd.get_dummies(df["transaction_type"], prefix="txn", drop_first=True)

    # ── Categoricals: High-cardinality City → Label Encode ────────────────
    le_city = LabelEncoder()
    df["city_encoded"] = le_city.fit_transform(df["city"])

    # ── Assemble final feature matrix ─────────────────────────────────────
    feature_cols = [
        "surface_m2", "log_surface", "rooms", "bathrooms", "total_rooms",
        "rooms_per_m2", "city_tier", "prop_tier", "city_encoded",
        "is_sale", "is_apartment", "is_villa", "is_studio",
    ]

    X = pd.concat([df[feature_cols], prop_dummies, txn_dummies], axis=1)
    y = df["log_price"]     # Predict log(price); convert back with np.expm1()

    # ── Scale numeric columns ─────────────────────────────────────────────
    scaler = RobustScaler()
    numeric_to_scale = [
        "surface_m2", "log_surface", "rooms", "bathrooms",
        "total_rooms", "rooms_per_m2",
    ]
    X[numeric_to_scale] = scaler.fit_transform(X[numeric_to_scale])

    # ── Train / Test split ────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    # ── Save outputs ──────────────────────────────────────────────────────
    X_train.to_csv("pipeline/X_train.csv", index=False)
    X_test.to_csv("pipeline/X_test.csv",  index=False)
    y_train.to_csv("pipeline/y_train.csv", index=False, header=["log_price"])
    y_test.to_csv("pipeline/y_test.csv",   index=False, header=["log_price"])

    feature_names = list(X.columns)
    with open("pipeline/feature_names.txt", "w") as f:
        f.write("\n".join(feature_names))

    # ── Feature report ────────────────────────────────────────────────────
    report = X_train.describe().T
    report["missing_%"] = (X.isnull().sum() / len(X) * 100).round(2)
    report.to_csv("pipeline/feature_report.csv")

    logger.info(f"  ✅ Features built  : {len(feature_names)} columns")
    logger.info(f"  ✅ Train samples   : {len(X_train)}")
    logger.info(f"  ✅ Test  samples   : {len(X_test)}")
    logger.info("STAGE 2 │ Complete → pipeline/X_train.csv, X_test.csv, y_*.csv")
    logger.info("─" * 60)

    return {
        "n_features":  len(feature_names),
        "n_train":     len(X_train),
        "n_test":      len(X_test),
        "feature_names": feature_names,
    }
