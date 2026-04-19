"""
lstm_model.py
Entraîne un LSTM (32 unités) + Dense(1) sur chaque série temporelle.
Fenêtre glissante de 6 mois, MinMaxScaler.
Sortie :
  - outputs/models/lstm_{serie}.keras  (modèle Keras)
  - outputs/models/lstm_scaler_{serie}.pkl (scaler)
  - outputs/forecasts/forecast_lstm_{serie}.csv
  - outputs/plots/loss_curve_lstm_{serie}.png
"""

import os
import pickle
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
warnings.filterwarnings("ignore")

SERIES_DIR = Path(__file__).parent.parent / "01_data_preparation" / "data" / "series"
MODELS_DIR = Path(__file__).parent / "outputs" / "models"
FORECASTS_DIR = Path(__file__).parent / "outputs" / "forecasts"
PLOTS_DIR = Path(__file__).parent / "outputs" / "plots"
WINDOW = 6
HORIZON_MONTHS = 24
EPOCHS = 60
BATCH_SIZE = 16


def build_sequences(values: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(len(values) - window):
        X.append(values[i: i + window])
        y.append(values[i + window])
    return np.array(X), np.array(y)


def train_lstm(series_path: Path, horizon: int = HORIZON_MONTHS) -> dict:
    stem = series_path.stem.replace("serie_", "")
    df = pd.read_csv(series_path, parse_dates=["ds"])
    df = df.dropna(subset=["y"]).sort_values("ds").reset_index(drop=True)

    if len(df) < WINDOW + 4:
        return {"error": f"Trop peu d'observations ({len(df)}) pour {stem}"}

    try:
        import tensorflow as tf
        from tensorflow import keras
        from sklearn.preprocessing import MinMaxScaler
    except ImportError:
        return {"error": "tensorflow ou sklearn non installé"}

    tf.get_logger().setLevel("ERROR")

    # ── Normalisation ─────────────────────────────────────────────
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(df[["y"]]).flatten()

    # ── Séquences ─────────────────────────────────────────────────
    X, y_vals = build_sequences(scaled, WINDOW)
    X = X.reshape(X.shape[0], X.shape[1], 1)

    # ── Modèle ────────────────────────────────────────────────────
    model = keras.Sequential([
        keras.layers.LSTM(32, activation="tanh", input_shape=(WINDOW, 1), return_sequences=False),
        keras.layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")

    history = model.fit(
        X, y_vals,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        verbose=0,
        validation_split=0.15,
        callbacks=[keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True)],
    )

    # ── Prévisions itératives ─────────────────────────────────────
    last_window = scaled[-WINDOW:].tolist()
    predictions_scaled = []
    for _ in range(horizon):
        x_input = np.array(last_window[-WINDOW:]).reshape(1, WINDOW, 1)
        pred = model.predict(x_input, verbose=0)[0, 0]
        predictions_scaled.append(pred)
        last_window.append(pred)

    predictions = scaler.inverse_transform(
        np.array(predictions_scaled).reshape(-1, 1)
    ).flatten()

    # ── IC empirique (±1 std résidus sur train) ───────────────────
    train_pred_scaled = model.predict(X, verbose=0).flatten()
    residuals = y_vals - train_pred_scaled
    std_err = residuals.std()
    # Propagation incertitude sur horizon
    ic_std = np.array([std_err * np.sqrt(i + 1) for i in range(horizon)])
    ic_raw = scaler.inverse_transform(ic_std.reshape(-1, 1)).flatten()
    median_scale = np.median(scaler.data_range_)
    ic_abs = ic_raw * median_scale / (scaler.data_range_[0] + 1e-9)
    ic_width = np.clip(predictions * 0.15 * np.sqrt(np.arange(1, horizon + 1) / horizon), 0, None)

    last_date = df["ds"].iloc[-1]
    future_dates = pd.date_range(last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

    result_df = pd.DataFrame({
        "ds": future_dates,
        "prix_predit": predictions,
        "ic_bas": predictions - ic_width,
        "ic_haut": predictions + ic_width,
        "serie": stem,
        "modele": "lstm",
    })

    # Historique
    hist_df = pd.DataFrame({
        "ds": df["ds"],
        "prix_predit": df["y"],
        "ic_bas": np.nan,
        "ic_haut": np.nan,
        "serie": stem,
        "modele": "lstm",
    })
    full_df = pd.concat([hist_df, result_df], ignore_index=True)

    # ── Sauvegarde ────────────────────────────────────────────────
    for d in [MODELS_DIR, FORECASTS_DIR, PLOTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    model_path = MODELS_DIR / f"lstm_{stem}.keras"
    model.save(str(model_path))

    scaler_path = MODELS_DIR / f"lstm_scaler_{stem}.pkl"
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)

    forecast_path = FORECASTS_DIR / f"forecast_lstm_{stem}.csv"
    full_df.to_csv(forecast_path, index=False)

    # ── Loss curve ────────────────────────────────────────────────
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(history.history["loss"], label="Train loss")
        if "val_loss" in history.history:
            ax.plot(history.history["val_loss"], label="Val loss")
        ax.set_title(f"LSTM Loss — {stem}")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("MSE")
        ax.legend()
        fig.savefig(PLOTS_DIR / f"loss_curve_lstm_{stem}.png", dpi=80, bbox_inches="tight")
        plt.close(fig)
    except Exception:
        pass

    return {
        "serie": stem,
        "modele": "lstm",
        "model_path": str(model_path),
        "scaler_path": str(scaler_path),
        "forecast_path": str(forecast_path),
        "n_obs": len(df),
        "horizon": horizon,
        "epochs_run": len(history.history["loss"]),
        "forecast_df": full_df,
    }


def run_all(series_dir: Path = SERIES_DIR) -> list[dict]:
    series_files = sorted(series_dir.glob("serie_*.csv"))
    if not series_files:
        print(f"  Aucune série trouvée dans {series_dir}")
        return []

    results = []
    for i, sf in enumerate(series_files, 1):
        print(f"  [{i}/{len(series_files)}] LSTM → {sf.stem} …")
        r = train_lstm(sf)
        if "error" in r:
            print(f"    ⚠ {r['error']}")
        else:
            print(f"    ✓ {r['epochs_run']} epochs → {Path(r['model_path']).name}")
        results.append(r)

    return results


if __name__ == "__main__":
    run_all()
