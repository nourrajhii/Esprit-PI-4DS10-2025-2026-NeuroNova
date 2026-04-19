"""
retrain_pipeline.py
Réentraîne tous les modèles sur les nouvelles données disponibles.
Usage : python retrain_pipeline.py [--series-dir path] [--model prophet|arima|lstm|all]
"""

import argparse
import sys
import time
from pathlib import Path

# Ajouter les modules au path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "01_data_preparation"))
sys.path.insert(0, str(ROOT / "02_modeling"))


def retrain(series_dir: Path, model: str = "all"):
    start = time.time()
    print("=" * 60)
    print(f"  RÉENTRAÎNEMENT — modèle={model}")
    print("=" * 60)

    if model in ("all", "prophet"):
        print("\n[Prophet] Réentraînement …")
        from prophet_model import run_all as run_prophet
        results = run_prophet(series_dir)
        ok = sum(1 for r in results if "error" not in r)
        print(f"  ✓ {ok}/{len(results)} modèles Prophet réentraînés")

    if model in ("all", "arima"):
        print("\n[ARIMA] Réentraînement …")
        from arima_model import run_all as run_arima
        results = run_arima(series_dir)
        ok = sum(1 for r in results if "error" not in r)
        print(f"  ✓ {ok}/{len(results)} modèles ARIMA réentraînés")

    if model in ("all", "lstm"):
        print("\n[LSTM] Réentraînement …")
        from lstm_model import run_all as run_lstm
        results = run_lstm(series_dir)
        ok = sum(1 for r in results if "error" not in r)
        print(f"  ✓ {ok}/{len(results)} modèles LSTM réentraînés")

    print("\n[Évaluation] Réévaluation et sélection …")
    from evaluation import run_evaluation
    summary = run_evaluation(series_dir)

    elapsed = time.time() - start
    print(f"\n  Réentraînement terminé en {elapsed:.1f}s")
    if summary:
        print(f"  Meilleur modèle global : {summary.get('global_best_model', 'N/A').upper()}")

    # Log dans MLflow si disponible
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from mlflow_tracking import log_all_runs
        print("\n[MLflow] Logging des nouveaux runs …")
        log_all_runs()
    except Exception as e:
        print(f"  [MLflow] Non disponible : {e}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Réentraînement du pipeline immo-forecast")
    parser.add_argument(
        "--series-dir",
        type=Path,
        default=ROOT / "01_data_preparation" / "data" / "series",
        help="Dossier contenant les séries temporelles",
    )
    parser.add_argument(
        "--model",
        choices=["prophet", "arima", "lstm", "all"],
        default="all",
        help="Modèle(s) à réentraîner",
    )
    args = parser.parse_args()
    retrain(args.series_dir, args.model)


if __name__ == "__main__":
    main()
