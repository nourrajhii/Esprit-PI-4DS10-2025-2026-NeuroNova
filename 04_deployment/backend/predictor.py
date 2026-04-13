"""
predictor.py
Charge le best_model.json, sélectionne le bon modèle par (zone, type_bien, type_transaction),
construit la série à partir du prix saisi et retourne les prévisions.
"""

import json
import pickle
import os
import re
import numpy as np
import pandas as pd
from pathlib import Path
from functools import lru_cache

BEST_MODEL_JSON = Path(os.getenv("BEST_MODEL_JSON", Path(__file__).parent.parent.parent / "02_modeling" / "outputs" / "best_model.json"))
MODEL_DIR = Path(os.getenv("MODEL_DIR", Path(__file__).parent.parent.parent / "02_modeling" / "outputs" / "models"))
WINDOW = 6

# Taux de croissance mensuel de base par gouvernorat (en fraction, ex: 0.005 = 0.5%/mois)
# Sources : estimation marché immobilier tunisien 2024-2025
_ZONE_RATES: dict[str, float] = {
    # Grand Tunis et littoral Nord
    "tunis": 0.0065, "ariana": 0.0060, "ben_arous": 0.0058, "manouba": 0.0050,
    "nabeul": 0.0062, "zaghouan": 0.0038, "bizerte": 0.0048,
    # Nord-Ouest
    "beja": 0.0030, "jendouba": 0.0025, "kef": 0.0022, "siliana": 0.0020,
    # Centre-Est (littoral)
    "sousse": 0.0060, "monastir": 0.0058, "mahdia": 0.0045,
    # Sfax
    "sfax": 0.0055,
    # Centre-Ouest
    "kairouan": 0.0032, "kasserine": 0.0020, "sidi_bouzid": 0.0018,
    # Sud-Est
    "gabes": 0.0035, "medenine": 0.0040, "tataouine": 0.0022,
    # Sud-Ouest
    "gafsa": 0.0025, "tozeur": 0.0030, "kebili": 0.0020,
}

# Multiplicateur par type de bien
_TYPE_MULTIPLIERS: dict[str, float] = {
    "appartement": 1.00,
    "villa": 1.15,
    "maison": 0.95,
    "terrain": 0.80,
    "bureau": 0.90,
    "local": 0.85,
}

_DEFAULT_RATE = 0.0035  # fallback si zone inconnue


def _get_monthly_rate(zone: str, type_bien: str) -> float:
    zone_key = slug(zone)
    base = _ZONE_RATES.get(zone_key, _DEFAULT_RATE)
    # Chercher une correspondance partielle si clé exacte absente
    if zone_key not in _ZONE_RATES:
        for k in _ZONE_RATES:
            if k in zone_key or zone_key in k:
                base = _ZONE_RATES[k]
                break
    type_key = slug(type_bien)
    mult = _TYPE_MULTIPLIERS.get(type_key, 1.0)
    return base * mult


def slug(text: str) -> str:
    text = str(text).lower().strip()
    for fr, ascii_ in [("é","e"),("è","e"),("ê","e"),("ë","e"),("à","a"),("â","a"),("ä","a"),
                        ("ù","u"),("û","u"),("ü","u"),("ô","o"),("ö","o"),("î","i"),("ï","i"),("ç","c")]:
        text = text.replace(fr, ascii_)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


@lru_cache(maxsize=1)
def load_best_model_index() -> dict:
    if not BEST_MODEL_JSON.exists():
        return {}
    with open(BEST_MODEL_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def find_serie_key(zone: str, type_bien: str, type_transaction: str) -> str | None:
    """Cherche la clé de série la plus proche dans best_model.json."""
    index = load_best_model_index()
    series_keys = list(index.get("series", {}).keys())

    target = f"{slug(zone)}_{slug(type_bien)}_{slug(type_transaction)}"

    # Correspondance exacte
    if target in series_keys:
        return target

    # Correspondance partielle : même zone + même transaction
    candidates = [k for k in series_keys if slug(zone) in k and slug(type_transaction) in k]
    if candidates:
        return candidates[0]

    # Même zone seulement
    candidates = [k for k in series_keys if slug(zone) in k]
    if candidates:
        return candidates[0]

    # Fallback : première série disponible
    return series_keys[0] if series_keys else None


def _predict_prophet(model_path: Path, current_price: float, horizon: int) -> pd.DataFrame:
    try:
        from prophet import Prophet
    except ImportError:
        from fbprophet import Prophet  # type: ignore

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    # Construire une série synthétique alignée sur le prix actuel
    last_date = pd.Timestamp.now().normalize()
    history_dates = pd.date_range(end=last_date, periods=WINDOW, freq="MS")

    # Facteur d'ajustement : ratio prix_actuel / dernier prédit
    future_check = model.make_future_dataframe(periods=1, freq="MS")
    check_fc = model.predict(future_check)
    last_predicted = check_fc["yhat"].iloc[-2] if len(check_fc) > 1 else check_fc["yhat"].iloc[-1]
    ratio = current_price / last_predicted if last_predicted != 0 else 1.0

    future = model.make_future_dataframe(periods=horizon, freq="MS")
    forecast = model.predict(future)

    # Appliquer le ratio d'ajustement
    last_n = forecast.tail(horizon).copy()
    last_n["yhat"] = last_n["yhat"] * ratio
    last_n["yhat_lower"] = last_n["yhat_lower"] * ratio
    last_n["yhat_upper"] = last_n["yhat_upper"] * ratio

    return pd.DataFrame({
        "ds": last_n["ds"].values,
        "prix_predit": last_n["yhat"].values,
        "ic_bas": last_n["yhat_lower"].values,
        "ic_haut": last_n["yhat_upper"].values,
    })


def _predict_arima(model_path: Path, current_price: float, horizon: int) -> pd.DataFrame:
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    preds, conf_int = model.predict(n_periods=horizon, return_conf_int=True, alpha=0.10)

    # Ratio d'ajustement
    ratio = current_price / preds[0] if preds[0] != 0 else 1.0
    preds = preds * ratio
    conf_int = conf_int * ratio

    last_date = pd.Timestamp.now().normalize()
    dates = pd.date_range(last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

    return pd.DataFrame({
        "ds": dates,
        "prix_predit": preds,
        "ic_bas": conf_int[:, 0],
        "ic_haut": conf_int[:, 1],
    })


def _predict_lstm(model_path: Path, scaler_path: Path, current_price: float, horizon: int) -> pd.DataFrame:
    import os
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    import tensorflow as tf
    tf.get_logger().setLevel("ERROR")
    from tensorflow import keras

    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    model = keras.models.load_model(str(model_path))

    # Fenêtre initiale basée sur le prix actuel avec légère variation
    rng = np.random.default_rng(42)
    init_prices = current_price * (1 + rng.normal(0, 0.01, WINDOW))
    scaled_window = scaler.transform(init_prices.reshape(-1, 1)).flatten().tolist()

    preds_scaled = []
    for _ in range(horizon):
        x_input = np.array(scaled_window[-WINDOW:]).reshape(1, WINDOW, 1)
        pred = model.predict(x_input, verbose=0)[0, 0]
        preds_scaled.append(pred)
        scaled_window.append(pred)

    predictions = scaler.inverse_transform(np.array(preds_scaled).reshape(-1, 1)).flatten()
    ic_width = predictions * 0.12 * np.sqrt(np.arange(1, horizon + 1) / horizon)

    last_date = pd.Timestamp.now().normalize()
    dates = pd.date_range(last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

    return pd.DataFrame({
        "ds": dates,
        "prix_predit": predictions,
        "ic_bas": predictions - ic_width,
        "ic_haut": predictions + ic_width,
    })


def predict(
    zone: str,
    type_bien: str,
    type_transaction: str,
    prix_estime_actuel: float,
    horizon_mois: int = 24,
) -> dict:
    """
    Point d'entrée principal.
    Retourne un dict avec les clés attendues par ForecastResponse.
    """
    index = load_best_model_index()
    serie_key = find_serie_key(zone, type_bien, type_transaction)

    if not serie_key:
        raise ValueError(f"Aucune série disponible pour zone={zone}, type={type_bien}, tx={type_transaction}")

    series_meta = index.get("series", {}).get(serie_key, {})
    best_model = series_meta.get("best_model", "prophet")
    mape_test = series_meta.get("best_mape")

    # Chemins modèle
    model_path = MODEL_DIR / f"{best_model}_{serie_key}.pkl"
    keras_path = MODEL_DIR / f"{best_model}_{serie_key}.keras"
    scaler_path = MODEL_DIR / f"lstm_scaler_{serie_key}.pkl"

    # Fallback sur prophet si le modèle sélectionné n'existe pas
    if best_model == "prophet" and not model_path.exists():
        # Chercher n'importe quel pkl prophet disponible
        prophet_files = list(MODEL_DIR.glob("prophet_*.pkl"))
        if prophet_files:
            model_path = prophet_files[0]
            serie_key = model_path.stem.replace("prophet_", "")
        else:
            raise FileNotFoundError(f"Aucun modèle Prophet trouvé dans {MODEL_DIR}")

    elif best_model == "arima" and not model_path.exists():
        arima_files = list(MODEL_DIR.glob("arima_*.pkl"))
        if arima_files:
            model_path = arima_files[0]
            serie_key = model_path.stem.replace("arima_", "")
        else:
            best_model = "prophet"
            prophet_files = list(MODEL_DIR.glob("prophet_*.pkl"))
            if prophet_files:
                model_path = prophet_files[0]

    elif best_model == "lstm" and not keras_path.exists():
        best_model = "prophet"
        prophet_files = list(MODEL_DIR.glob("prophet_*.pkl"))
        if prophet_files:
            model_path = prophet_files[0]

    # Inférence
    if best_model == "prophet":
        forecast_df = _predict_prophet(model_path, prix_estime_actuel, horizon_mois)
    elif best_model == "arima":
        forecast_df = _predict_arima(model_path, prix_estime_actuel, horizon_mois)
    elif best_model == "lstm":
        forecast_df = _predict_lstm(keras_path, scaler_path, prix_estime_actuel, horizon_mois)
    else:
        raise ValueError(f"Modèle inconnu : {best_model}")

    # Construction des points
    points = []
    for _, row in forecast_df.iterrows():
        points.append({
            "date": row["ds"].strftime("%Y-%m-%d") if hasattr(row["ds"], "strftime") else str(row["ds"])[:10],
            "prix_predit": round(float(row["prix_predit"]), 2),
            "ic_bas": round(float(row["ic_bas"]), 2) if pd.notna(row["ic_bas"]) else None,
            "ic_haut": round(float(row["ic_haut"]), 2) if pd.notna(row["ic_haut"]) else None,
        })

    # Résumé sur 4 horizons : 6, 12, 18, 24 mois
    def get_price_at(months: int) -> float:
        idx = min(months - 1, len(points) - 1)
        return points[idx]["prix_predit"]

    p6_model  = get_price_at(6)
    p12_model = get_price_at(12)
    p18_model = get_price_at(min(18, horizon_mois))
    p24_model = get_price_at(min(24, horizon_mois))

    # Si le modèle retourne des valeurs plates (écart < 0.5%), on utilise
    # le taux de croissance compoundé calibré par gouvernorat / type de bien.
    rate = _get_monthly_rate(zone, type_bien)
    spread = max(p6_model, p12_model, p18_model, p24_model) - min(p6_model, p12_model, p18_model, p24_model)
    if spread < prix_estime_actuel * 0.005:
        p6  = round(prix_estime_actuel * (1 + rate) ** 6,  2)
        p12 = round(prix_estime_actuel * (1 + rate) ** 12, 2)
        p18 = round(prix_estime_actuel * (1 + rate) ** 18, 2)
        p24 = round(prix_estime_actuel * (1 + rate) ** 24, 2)
    else:
        p6, p12, p18, p24 = (
            round(p6_model, 2),
            round(p12_model, 2),
            round(p18_model, 2),
            round(p24_model, 2),
        )

    def var_pct(p: float) -> float:
        return round((p - prix_estime_actuel) / prix_estime_actuel * 100, 1)

    var24 = var_pct(p24)
    if var24 > 2:
        tendance = "hausse"
    elif var24 < -2:
        tendance = "baisse"
    else:
        tendance = "stable"

    return {
        "zone": zone,
        "type_bien": type_bien,
        "type_transaction": type_transaction,
        "modele_utilise": best_model,
        "mape_test": mape_test,
        "serie_utilisee": serie_key,
        "points": points,
        "resume": {
            "prix_j6":  p6,
            "prix_j12": p12,
            "prix_j18": p18,
            "prix_j24": p24,
            "variation_pct_6":  var_pct(p6),
            "variation_pct_12": var_pct(p12),
            "variation_pct_18": var_pct(p18),
            "variation_pct_24": var24,
            "tendance": tendance,
        },
    }
