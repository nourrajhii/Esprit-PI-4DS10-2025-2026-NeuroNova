"""
app/services/price_prediction_service.py

Service de prédiction de prix basé sur les statistiques de marché tunisien.
Chargé une seule fois au démarrage de l'application (singleton).
"""

import os
import pickle
from typing import Optional

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "price_model.pkl")

_model_data: Optional[dict] = None


def _load_model() -> dict:
    global _model_data
    if _model_data is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Modèle introuvable : {MODEL_PATH}\n"
                "Exécutez d'abord : python train_price_model.py"
            )
        with open(MODEL_PATH, "rb") as f:
            _model_data = pickle.load(f)
    return _model_data


def predict_price(
    surface_m2: float,
    rooms: int,
    city: str,
    property_type: str,
    transaction_type: str,
    bathrooms: int = 1,
) -> dict:
    """
    Prédit le prix d'un bien immobilier à partir des statistiques du marché.

    Retourne :
    {
        "predicted_price":   336000.0,          # médiane
        "confidence_range": {"min": 208284.0, "max": 485581.0},
        "price_per_m2":      2800.0,
        "market_data": {
            "city_known":       True,
            "n_comparables":    316,
            "market_pm2_low":   1549.0,
            "market_pm2_mid":   2500.0,
            "market_pm2_high":  3612.0,
        }
    }
    """
    data         = _load_model()
    market_stats = data["market_stats"]
    global_stats = data["global_stats"]
    rooms_factor = data["rooms_factor"]

    city_clean = city.strip().title()
    city_known = city_clean in market_stats

    city_data = market_stats.get(city_clean, global_stats)

    pm2_q25    = city_data["prix_m2_q25"]
    pm2_median = city_data["prix_m2_median"]
    pm2_q75    = city_data["prix_m2_q75"]

    rooms_clamped = min(max(rooms, 1), 10)
    factor        = rooms_factor.get(rooms_clamped, 1.0)

    price_low  = pm2_q25    * factor * surface_m2
    price_mid  = pm2_median * factor * surface_m2
    price_high = pm2_q75    * factor * surface_m2

    return {
        "predicted_price":  round(price_mid, 2),
        "confidence_range": {
            "min": round(price_low,  2),
            "max": round(price_high, 2),
        },
        "price_per_m2": round(pm2_median * factor, 2),
        "market_data": {
            "city_known":      city_known,
            "n_comparables":   city_data.get("count", global_stats["count"]),
            "market_pm2_low":  round(pm2_q25,    2),
            "market_pm2_mid":  round(pm2_median, 2),
            "market_pm2_high": round(pm2_q75,    2),
        },
    }


def get_model_info() -> dict:
    """Retourne les métadonnées du modèle et les statistiques du marché."""
    data = _load_model()
    return {
        "cities":            data["cities"],
        "property_types":    data["property_types"],
        "transaction_types": data["transaction_types"],
        "n_samples":         data["n_samples"],
        "price_min":         data["price_min"],
        "price_max":         data["price_max"],
        "price_mean":        data["price_mean"],
        "market_pm2_median": round(data["global_stats"]["prix_m2_median"], 2),
    }
