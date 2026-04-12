"""
mlflow_tracking.py
Log params, métriques et artifacts pour chaque run de modélisation via MLflow.
"""

import json
import os
from pathlib import Path

BEST_MODEL_FILE = Path(__file__).parent.parent / "02_modeling" / "outputs" / "best_model.json"
MODELS_DIR = Path(__file__).parent.parent / "02_modeling" / "outputs" / "models"
FORECASTS_DIR = Path(__file__).parent.parent / "02_modeling" / "outputs" / "forecasts"
PLOTS_DIR = Path(__file__).parent.parent / "02_modeling" / "outputs" / "plots"

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT_NAME = "immo-forecast-tunisia"


def log_all_runs():
    try:
        import mlflow
        import mlflow.sklearn
        import mlflow.keras
    except ImportError:
        print("  MLflow non installé — pip install mlflow")
        return

    if not BEST_MODEL_FILE.exists():
        print(f"  {BEST_MODEL_FILE} introuvable. Lancez d'abord run_modeling.py")
        return

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    with open(BEST_MODEL_FILE, "r", encoding="utf-8") as f:
        summary = json.load(f)

    series_results = summary.get("series", {})
    print(f"  Logging {len(series_results)} séries dans MLflow …")

    for serie, meta in series_results.items():
        # Un run par modèle concurrent
        for model_metrics in meta.get("all_metrics", []):
            modele = model_metrics["modele"]
            with mlflow.start_run(run_name=f"{serie}_{modele}"):
                # Params
                mlflow.log_param("serie", serie)
                mlflow.log_param("modele", modele)
                parts = serie.split("_")
                if len(parts) >= 3:
                    mlflow.log_param("gouvernorat", parts[0])
                    mlflow.log_param("categorie", "_".join(parts[1:-1]))
                    mlflow.log_param("type_transaction", parts[-1])

                # Métriques
                mlflow.log_metric("mae", model_metrics["mae"])
                mlflow.log_metric("rmse", model_metrics["rmse"])
                mlflow.log_metric("mape", model_metrics["mape"])
                mlflow.log_metric("is_best", 1 if modele == meta["best_model"] else 0)

                # Artifacts modèle
                model_path = Path(model_metrics["model_path"])
                if model_path.exists():
                    mlflow.log_artifact(str(model_path), artifact_path="model")

                # Forecast CSV
                fc_path = FORECASTS_DIR / f"forecast_{modele}_{serie}.csv"
                if fc_path.exists():
                    mlflow.log_artifact(str(fc_path), artifact_path="forecasts")

                # Plots
                for plot_file in PLOTS_DIR.glob(f"*{serie}*.png"):
                    mlflow.log_artifact(str(plot_file), artifact_path="plots")

        print(f"    ✓ {serie} → best={meta['best_model']} MAPE={meta['best_mape']}%")

    print(f"\n  Tous les runs loggés sur {MLFLOW_TRACKING_URI}")
    print(f"  Expérience : {EXPERIMENT_NAME}")


if __name__ == "__main__":
    log_all_runs()
