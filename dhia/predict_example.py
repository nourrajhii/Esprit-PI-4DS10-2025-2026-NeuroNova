"""
==============================================================================
EstateMind │ AI Price Predictor Tool
==============================================================================
This script demonstrates how to use your trained GBM model to estimate 
the price of any Tunisian property.
==============================================================================
"""

import pandas as pd
import numpy as np
import joblib
import json
import os

MODEL_PATH = "models/price_model.joblib"
META_PATH  = "models/model_metadata.json"

def get_prediction(surface, rooms, bathrooms, city_tier, is_sale=1):
    """
    surface: float (m2)
    rooms: int
    bathrooms: int
    city_tier: int (1=Rural, 3=Urban, 5=Prime Lac/Marsa)
    is_sale: 1 for Vente, 0 for Location
    """
    if not os.path.exists(MODEL_PATH):
        print("❌ Error: Model not found. Run 'python run_pipeline.py' first.")
        return

    # Load essentials
    model = joblib.load(MODEL_PATH)
    with open(META_PATH, 'r') as f:
        meta = json.load(f)
    
    # Prepare input features mapping
    # Note: Model log-transforms surface internally if trained that way, 
    # but here we follow the feature names saved in metadata.
    features = {
        "surface_m2": surface,
        "log_surface": np.log1p(surface),
        "rooms": rooms,
        "bathrooms": bathrooms,
        "total_rooms": rooms + bathrooms,
        "rooms_per_m2": rooms / surface if surface > 0 else 0,
        "city_tier": city_tier,
        "prop_tier": 2, # default tier
        "is_sale": is_sale,
        "is_apartment": 1, # assumption for example
        "is_villa": 0,
        "is_studio": 0,
        "city_encoded": 0 # simplified
    }

    # Create DF with exact columns used during training
    X = pd.DataFrame([features]).reindex(columns=meta['features'], fill_value=0)
    
    # Predict in log space then convert back
    log_price = model.predict(X)[0]
    real_price = np.expm1(log_price)
    
    return real_price

if __name__ == "__main__":
    print("🏠 --- Tunisian Real Estate Price Estimator ---")
    
    # Example input
    S = 120
    R = 3
    B = 2
    T = 5 # Prime location (Lac)
    
    price = get_prediction(surface=S, rooms=R, bathrooms=B, city_tier=T)
    
    if price:
        print(f"\nProperty Specs:")
        print(f" - Surface : {S} m²")
        print(f" - Rooms   : {R} (S+{R-1})")
        print(f" - Location: Tier {T} (Luxury Prime)")
        print(f" - Type    : Vente")
        print(f"\n💰 Estimated Price: {price:,.0f} TND")
        print("-----------------------------------------------")
