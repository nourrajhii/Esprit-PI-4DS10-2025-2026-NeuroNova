"""
evaluation.py
- Train/Test split temporel 80/20 pour chaque série
- Calcule MAE, RMSE, MAPE pour Prophet, ARIMA, LSTM
- Sélectionne automatiquement le meilleur modèle par MAPE
- Sauvegarde best_model.json par série
"""

import json
import pickle
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")

SERIES_DIR = Path(__file__).parent.parent / "01_data_preparation" / "data" / "series"
MODELS_DIR = Path(__file__).parent / "outputs" / "models"
FORECASTS_DIR = Path(__file__).parent / "outputs" / "forecasts"
BEST_MODEL_FILE = Path(__file__).parent / "outputs" / "best_model.json"


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def evaluate_prophet(series_path: Path, train_df: pd.DataFrame, test_df: pd.DataFrame) -> dict | None:
    stem = series_path.stem.replace("serie_", "")
    model_path = MODELS_DIR / f"prophet_{stem}.pkl"
    if not model_path.exists():
        return None
    try:
        from prophet import Prophet
    except ImportError:
        try:
            from fbprophet import Prophet  # type: ignore
        except ImportError:
            return None

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    future = model.make_future_dataframe(periods=len(test_df), freq="MS")
    forecast = model.predict(future)
    preds = forecast.set_index("ds")["yhat"].reindex(test_df["ds"]).values
    y_true = test_df["y"].values

    mask = ~np.isnan(preds) & ~np.isnan(y_true)
    if mask.sum() == 0:
        return None

    return {
        "modele": "prophet",
        "mae": mae(y_true[mask], preds[mask]),
        "rmse": rmse(y_true[mask], preds[mask]),
        "mape": mape(y_true[mask], preds[mask]),
        "model_path": str(model_path),
    }


def evaluate_arima(series_path: Path, train_df: pd.DataFrame, test_df: pd.DataFrame) -> dict | None:
    stem = series_path.stem.replace("serie_", "")
    model_path = MODELS_DIR / f"arima_{stem}.pkl"
    if not model_path.exists():
        return None

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    try:
        preds, _ = model.predict(n_periods=len(test_df), return_conf_int=True, alpha=0.10)
    except Exception:
        return None

    y_true = test_df["y"].values
    mask = ~np.isnan(preds) & ~np.isnan(y_true)
    if mask.sum() == 0:
        return None

    return {
        "modele": "arima",
        "mae": mae(y_true[mask], preds[mask]),
        "rmse": rmse(y_true[mask], preds[mask]),
        "mape": mape(y_true[mask], preds[mask]),
        "model_path": str(model_path),
    }


def evaluate_lstm(series_path: Path, train_df: pd.DataFrame, test_df: pd.DataFrame) -> dict | None:
    stem = series_path.stem.replace("serie_", "")
    model_path = MODELS_DIR / f"lstm_{stem}.keras"
    scaler_path = MODELS_DIR / f"lstm_scaler_{stem}.pkl"
    if not model_path.exists() or not scaler_path.exists():
        return None

    try:
        import os
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
        import tensorflow as tf
        tf.get_logger().setLevel("ERROR")
        from tensorflow import keras
    except ImportError:
        return None

    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    model = keras.models.load_model(str(model_path))
    WINDOW = 6

    # Reconstruire la fenêtre depuis les derniers points du train
    scaled_train = scaler.transform(train_df[["y"]]).flatten()
    if len(scaled_train) < WINDOW:
        return None

    last_window = scaled_train[-WINDOW:].tolist()
    preds_scaled = []
    for _ in range(len(test_df)):
        x_input = np.array(last_window[-WINDOW:]).reshape(1, WINDOW, 1)
        pred = model.predict(x_input, verbose=0)[0, 0]
        preds_scaled.append(pred)
        last_window.append(pred)

    preds = scaler.inverse_transform(np.array(preds_scaled).reshape(-1, 1)).flatten()
    y_true = test_df["y"].values

    mask = ~np.isnan(preds) & ~np.isnan(y_true)
    if mask.sum() == 0:
        return None

    return {
        "modele": "lstm",
        "mae": mae(y_true[mask], preds[mask]),
        "rmse": rmse(y_true[mask], preds[mask]),
        "mape": mape(y_true[mask], preds[mask]),
        "model_path": str(model_path),
    }


def evaluate_series(series_path: Path) -> dict | None:
    stem = series_path.stem.replace("serie_", "")
    df = pd.read_csv(series_path, parse_dates=["ds"])
    df = df.dropna(subset=["y"]).sort_values("ds").reset_index(drop=True)

    if len(df) < 8:
        return None

    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    results = []
    for fn in [evaluate_prophet, evaluate_arima, evaluate_lstm]:
        r = fn(series_path, train_df, test_df)
        if r is not None:
            r["serie"] = stem
            results.append(r)

    if not results:
        return None

    # Sélection par MAPE minimum
    best = min(results, key=lambda x: x["mape"])
    return {
        "serie": stem,
        "best_model": best["modele"],
        "best_mape": round(best["mape"], 2),
        "best_mae": round(best["mae"], 2),
        "best_rmse": round(best["rmse"], 2),
        "model_path": best["model_path"],
        "all_metrics": results,
    }


def run_evaluation(series_dir: Path = SERIES_DIR) -> dict:
    series_files = sorted(series_dir.glob("serie_*.csv"))
    if not series_files:
        print(f"  Aucune série trouvée dans {series_dir}")
        return {}

    all_results = {}
    print(f"  Évaluation de {len(series_files)} séries …")

    for i, sf in enumerate(series_files, 1):
        stem = sf.stem.replace("serie_", "")
        print(f"  [{i}/{len(series_files)}] {stem} …")
        r = evaluate_series(sf)
        if r:
            all_results[stem] = r
            print(
                f"    → meilleur : {r['best_model'].upper()} "
                f"| MAPE={r['best_mape']:.1f}% "
                f"| MAE={r['best_mae']:.0f} TND/m²"
            )

    # Modèle global le plus fréquent
    if all_results:
        from collections import Counter
        best_counts = Counter(v["best_model"] for v in all_results.values())
        global_best = best_counts.most_common(1)[0][0]

        summary = {
            "n_series_evaluated": len(all_results),
            "global_best_model": global_best,
            "best_model_distribution": dict(best_counts),
            "series": all_results,
        }

        BEST_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BEST_MODEL_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n  best_model.json sauvegardé")
        print(f"  Modèle le plus souvent sélectionné : {global_best.upper()}")
        return summary

    return {}


if __name__ == "__main__":
    run_evaluation()
