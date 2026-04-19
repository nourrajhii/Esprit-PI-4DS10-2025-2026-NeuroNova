"""
prophet_model.py
Entraîne un modèle Prophet sur chaque série temporelle.
Sortie :
  - outputs/models/prophet_{serie}.pkl
  - outputs/forecasts/forecast_prophet_{serie}.csv
  - outputs/plots/composantes_prophet_{serie}.png
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


def train_prophet(series_path: Path, horizon: int = HORIZON_MONTHS) -> dict:
    """
    Entraîne Prophet sur la série donnée.
    Retourne un dict avec le modèle, les prévisions et les métriques.
    """
    try:
        from prophet import Prophet
    except ImportError:
        from fbprophet import Prophet  # type: ignore

    stem = series_path.stem.replace("serie_", "")
    df = pd.read_csv(series_path, parse_dates=["ds"])
    df = df.dropna(subset=["y"]).sort_values("ds").reset_index(drop=True)

    if len(df) < 4:
        return {"error": f"Trop peu d'observations ({len(df)}) pour {stem}"}

    # ── Modèle Prophet ────────────────────────────────────────────
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.90,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.15,
    )
    model.fit(df)

    # ── Prévisions ────────────────────────────────────────────────
    future = model.make_future_dataframe(periods=horizon, freq="MS")
    forecast = model.predict(future)

    result_df = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    result_df.columns = ["ds", "prix_predit", "ic_bas", "ic_haut"]
    result_df["serie"] = stem
    result_df["modele"] = "prophet"

    # ── Sauvegarde ────────────────────────────────────────────────
    for d in [MODELS_DIR, FORECASTS_DIR, PLOTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    model_path = MODELS_DIR / f"prophet_{stem}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    forecast_path = FORECASTS_DIR / f"forecast_prophet_{stem}.csv"
    result_df.to_csv(forecast_path, index=False)

    # ── Graphique composantes ─────────────────────────────────────
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig = model.plot_components(forecast)
        fig.savefig(PLOTS_DIR / f"composantes_prophet_{stem}.png", dpi=80, bbox_inches="tight")
        plt.close(fig)
    except Exception:
        pass

    return {
        "serie": stem,
        "modele": "prophet",
        "model_path": str(model_path),
        "forecast_path": str(forecast_path),
        "n_obs": len(df),
        "horizon": horizon,
        "forecast_df": result_df,
    }


def run_all(series_dir: Path = SERIES_DIR) -> list[dict]:
    series_files = sorted(series_dir.glob("serie_*.csv"))
    if not series_files:
        print(f"  Aucune série trouvée dans {series_dir}")
        return []

    results = []
    for i, sf in enumerate(series_files, 1):
        print(f"  [{i}/{len(series_files)}] Prophet → {sf.stem} …")
        r = train_prophet(sf)
        if "error" in r:
            print(f"    ⚠ {r['error']}")
        else:
            print(f"    ✓ modèle sauvegardé : {Path(r['model_path']).name}")
        results.append(r)

    return results


if __name__ == "__main__":
    run_all()
