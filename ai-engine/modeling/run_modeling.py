"""
run_modeling.py
Orchestre les 3 modèles de forecasting + l'évaluation :
  1. Prophet
  2. ARIMA (auto_arima)
  3. LSTM
  4. Évaluation + sélection du meilleur modèle
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from prophet_model import run_all as run_prophet
from arima_model import run_all as run_arima
from lstm_model import run_all as run_lstm
from evaluation import run_evaluation


def run_modeling():
    start = time.time()
    print("=" * 60)
    print("  PIPELINE MODÉLISATION — immo-forecast")
    print("=" * 60)

    # ── 1. Prophet ────────────────────────────────────────────────
    print("\n[1/4] Entraînement Prophet …")
    t0 = time.time()
    prophet_results = run_prophet()
    ok = sum(1 for r in prophet_results if "error" not in r)
    print(f"      ✓ {ok}/{len(prophet_results)} modèles Prophet en {time.time()-t0:.1f}s")

    # ── 2. ARIMA ──────────────────────────────────────────────────
    print("\n[2/4] Entraînement ARIMA …")
    t0 = time.time()
    arima_results = run_arima()
    ok = sum(1 for r in arima_results if "error" not in r)
    print(f"      ✓ {ok}/{len(arima_results)} modèles ARIMA en {time.time()-t0:.1f}s")

    # ── 3. LSTM ───────────────────────────────────────────────────
    print("\n[3/4] Entraînement LSTM …")
    t0 = time.time()
    lstm_results = run_lstm()
    ok = sum(1 for r in lstm_results if "error" not in r)
    print(f"      ✓ {ok}/{len(lstm_results)} modèles LSTM en {time.time()-t0:.1f}s")

    # ── 4. Évaluation ─────────────────────────────────────────────
    print("\n[4/4] Évaluation et sélection du meilleur modèle …")
    t0 = time.time()
    summary = run_evaluation()
    print(f"      ✓ Évaluation terminée en {time.time()-t0:.1f}s")

    # ── Résumé ────────────────────────────────────────────────────
    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"  Modélisation terminée en {elapsed:.1f}s")
    if summary:
        print(f"  Séries évaluées        : {summary.get('n_series_evaluated', 0)}")
        print(f"  Meilleur modèle global : {summary.get('global_best_model', 'N/A').upper()}")
        dist = summary.get("best_model_distribution", {})
        for m, cnt in dist.items():
            print(f"    {m:<10} : {cnt} série(s)")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    run_modeling()
