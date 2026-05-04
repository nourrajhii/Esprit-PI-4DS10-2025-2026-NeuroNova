"""
==============================================================================
EstateMind AI Pipeline Orchestrator
==============================================================================
Usage:
    python run_pipeline.py

Runs all ML pipeline stages in sequence:
  Stage 1 │ Clean raw listings          → pipeline/cleaned_listings.csv
  Stage 2 │ Feature engineering         → pipeline/X_train.csv etc.
  Stage 3 │ Train price-prediction model→ models/price_model.joblib
==============================================================================
"""

import asyncio
import logging
import os
import sys
import json
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PIPELINE_DIR = "pipeline"
MODEL_DIR    = "models"


async def run():
    os.makedirs(PIPELINE_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    logger.info("=" * 60)
    logger.info("      EstateMind AI Data Pipeline")
    logger.info("=" * 60)

    # ── Stage 1: Clean ────────────────────────────────────────────────────
    from database.models import init_db
    from processing.cleaner import run_cleaning_pipeline

    await init_db()
    n_clean = await run_cleaning_pipeline()

    if n_clean < 50:
        logger.error(
            f"Only {n_clean} rows passed cleaning — too few for training. "
            "Run a scraping cycle first with `python main.py`."
        )
        sys.exit(1)

    # ── Stage 2: Feature Engineering ──────────────────────────────────────
    from processing.feature_engineering import run_feature_engineering

    fe_result = run_feature_engineering()

    # ── Stage 3: Train / Retrain Model ────────────────────────────────────
    from processing.model_trainer import run_model_training

    model_meta = run_model_training()

    # ── Final Summary ─────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("  PIPELINE COMPLETE ✅")
    logger.info("=" * 60)
    logger.info(f"  Clean rows       : {n_clean}")
    logger.info(f"  Features built   : {fe_result['n_features']}")
    logger.info(f"  Train / Test     : {fe_result['n_train']} / {fe_result['n_test']}")
    logger.info(f"  Model R²         : {model_meta['r2']} (closer to 1.0 = better)")
    logger.info(f"  Model MAPE       : {model_meta['mape_pct']}%  (price error on avg)")
    logger.info("─" * 60)
    logger.info("  Output files:")
    for root_dir in [PIPELINE_DIR, MODEL_DIR]:
        for fname in sorted(os.listdir(root_dir)):
            fpath = os.path.join(root_dir, fname)
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath) / 1024
                logger.info(f"    📄 {root_dir}/{fname:35s} {size:7.1f} KB")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run())
