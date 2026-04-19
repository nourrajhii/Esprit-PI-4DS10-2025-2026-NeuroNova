"""
arima_model.py
Entraîne un modèle SARIMA (auto_arima) sur chaque série temporelle.
Sortie :
  - outputs/models/arima_{serie}.pkl
  - outputs/forecasts/forecast_arima_{serie}.csv
  - outputs/plots/residuals_arima_{serie}.png
"""

import pickle
import warnings
import pandas as pd
import numpy as np
from pathlib import Path

warnings.filterwarnings("ignore")

SERIES_DIR = Path(__file__).parent.parent / "01_data_preparation" / "data" / "series"
MODELS_DIR = Path(__file__).parent / "outputs" / "models"
FORECASTS_DIR = Path(__file__).parent / "outputs" / "forecasts"
PLOTS_DIR = Path(__file__).parent / "outputs" / "plots"
HORIZON_MONTHS = 24


def train_arima(series_path: Path, horizon: int = HORIZON_MONTHS) -> dict:
    stem = series_path.stem.replace("serie_", "")
    df = pd.read_csv(series_path, parse_dates=["ds"])
    df = df.dropna(subset=["y"]).sort_values("ds").reset_index(drop=True)

    if len(df) < 8:
        return {"error": f"Trop peu d'observations ({len(df)}) pour {stem}"}

    try:
        from pmdarima import auto_arima
    except ImportError:
        return {"error": "pmdarima non installé"}

    # ── auto_arima saisonnier ─────────────────────────────────────
    model = auto_arima(
        df["y"],
        start_p=1, start_q=1,
        max_p=3, max_q=3,
        m=12,
        start_P=0, start_Q=0,
        max_P=2, max_Q=2,
        seasonal=True,
        d=None,
        D=None,
        information_criterion="aic",
        error_action="ignore",
        suppress_warnings=True,
        stepwise=True,
        n_fits=30,
    )

    # ── Prévisions avec intervalles de confiance 90% ──────────────
    forecast_vals, conf_int = model.predict(
        n_periods=horizon,
        return_conf_int=True,
        alpha=0.10,
    )

    last_date = df["ds"].iloc[-1]
    future_dates = pd.date_range(last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

    result_df = pd.DataFrame({
        "ds": future_dates,
        "prix_predit": forecast_vals,
        "ic_bas": conf_int[:, 0],
        "ic_haut": conf_int[:, 1],
        "serie": stem,
        "modele": "arima",
    })

    # Ajouter l'historique dans le CSV de prévision
    hist_df = pd.DataFrame({
        "ds": df["ds"],
        "prix_predit": df["y"],
        "ic_bas": np.nan,
        "ic_haut": np.nan,
        "serie": stem,
        "modele": "arima",
    })
    full_df = pd.concat([hist_df, result_df], ignore_index=True)

    # ── Sauvegarde ────────────────────────────────────────────────
    for d in [MODELS_DIR, FORECASTS_DIR, PLOTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    model_path = MODELS_DIR / f"arima_{stem}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    forecast_path = FORECASTS_DIR / f"forecast_arima_{stem}.csv"
    full_df.to_csv(forecast_path, index=False)

    # ── Graphique résidus ─────────────────────────────────────────
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        residuals = model.resid()
        fig, axes = plt.subplots(2, 1, figsize=(10, 6))
        axes[0].plot(df["ds"], residuals)
        axes[0].axhline(0, linestyle="--", color="red", linewidth=0.8)
        axes[0].set_title(f"Résidus ARIMA — {stem}")
        axes[1].hist(residuals, bins=20, edgecolor="black")
        axes[1].set_title("Distribution des résidus")
        plt.tight_layout()
        fig.savefig(PLOTS_DIR / f"residuals_arima_{stem}.png", dpi=80, bbox_inches="tight")
        plt.close(fig)
    except Exception:
        pass

    order = model.order
    seasonal_order = model.seasonal_order
    return {
        "serie": stem,
        "modele": "arima",
        "order": order,
        "seasonal_order": seasonal_order,
        "model_path": str(model_path),
        "forecast_path": str(forecast_path),
        "n_obs": len(df),
        "horizon": horizon,
        "forecast_df": full_df,
    }


def run_all(series_dir: Path = SERIES_DIR) -> list[dict]:
    series_files = sorted(series_dir.glob("serie_*.csv"))
    if not series_files:
        print(f"  Aucune série trouvée dans {series_dir}")
        return []

    results = []
    for i, sf in enumerate(series_files, 1):
        print(f"  [{i}/{len(series_files)}] ARIMA → {sf.stem} …")
        r = train_arima(sf)
        if "error" in r:
            print(f"    ⚠ {r['error']}")
        else:
            print(f"    ✓ ARIMA{r['order']}x{r['seasonal_order']} → {Path(r['model_path']).name}")
        results.append(r)

    return results


if __name__ == "__main__":
    run_all()
