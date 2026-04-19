"""
run_data_pipeline.py
Orchestre les 3 étapes du pipeline de données :
  1. ingestion.py   → master_raw.csv
  2. cleaning.py    → master_clean.csv + rapport_qualite.txt
  3. feature_engineering.py → data/series/*.csv + rapport_stats.txt
"""

import sys
import time
from pathlib import Path

# Assure que le dossier parent est dans le path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion import ingest
from cleaning import clean
from feature_engineering import build_series


def run_pipeline():
    start = time.time()
    print("=" * 60)
    print("  PIPELINE DONNÉES — immo-forecast")
    print("=" * 60)

    # ── Étape 1 : Ingestion ───────────────────────────────────────
    print("\n[1/3] Ingestion des sources …")
    t0 = time.time()
    master_raw = ingest()
    print(f"      ✓ {len(master_raw):,} lignes ingérées en {time.time()-t0:.1f}s")

    # ── Étape 2 : Nettoyage ───────────────────────────────────────
    print("\n[2/3] Nettoyage et normalisation …")
    t0 = time.time()
    master_clean = clean()
    print(f"      ✓ {len(master_clean):,} lignes propres en {time.time()-t0:.1f}s")

    # ── Étape 3 : Ingénierie des features ─────────────────────────
    print("\n[3/3] Construction des séries temporelles …")
    t0 = time.time()
    series_meta = build_series()
    print(f"      ✓ {len(series_meta)} séries générées en {time.time()-t0:.1f}s")

    # ── Résumé ────────────────────────────────────────────────────
    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"  Pipeline terminé en {elapsed:.1f}s")
    print(f"  Lignes brutes   : {len(master_raw):,}")
    print(f"  Lignes propres  : {len(master_clean):,}")
    print(f"  Séries créées   : {len(series_meta)}")
    print("=" * 60)

    return master_raw, master_clean, series_meta


if __name__ == "__main__":
    run_pipeline()
