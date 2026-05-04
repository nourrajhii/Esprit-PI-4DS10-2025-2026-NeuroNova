"""
==============================================================================
EstateMind AI Model Trainer — Stage 3 of the Pipeline
==============================================================================
Strategy:
  - Uses a Gradient Boosting Regressor (best accuracy on tabular data).
  - On every pipeline run, the model is RETRAINED on the full growing dataset.
    This means each new scraping cycle makes the model smarter automatically.
  - Persists the trained model to models/price_model.joblib via joblib.
  - Appends a performance log to models/training_log.csv so you can track
    how accuracy improves over time as more data is collected.
  - Target variable: log_price  →  use np.expm1(prediction) to get TND price.
==============================================================================
"""

import logging
import os
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

logger = logging.getLogger(__name__)

MODEL_DIR     = "models"
MODEL_PATH    = os.path.join(MODEL_DIR, "price_model.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")
TRAIN_LOG     = os.path.join(MODEL_DIR, "training_log.csv")

PIPELINE_DIR  = "pipeline"


def _load_data():
    X_train = pd.read_csv(f"{PIPELINE_DIR}/X_train.csv")
    X_test  = pd.read_csv(f"{PIPELINE_DIR}/X_test.csv")
    y_train = pd.read_csv(f"{PIPELINE_DIR}/y_train.csv").squeeze()
    y_test  = pd.read_csv(f"{PIPELINE_DIR}/y_test.csv").squeeze()
    return X_train, X_test, y_train, y_test


def _evaluate(model, X_test, y_test) -> dict:
    """Compute metrics in log-space and in original TND space."""
    y_pred_log  = model.predict(X_test)
    y_pred_tnd  = np.expm1(y_pred_log)
    y_true_tnd  = np.expm1(y_test)

    mae_log  = mean_absolute_error(y_test, y_pred_log)
    rmse_log = np.sqrt(mean_squared_error(y_test, y_pred_log))
    r2       = r2_score(y_test, y_pred_log)

    # Mean Absolute Percentage Error in TND space
    mape = np.mean(np.abs((y_true_tnd - y_pred_tnd) / (y_true_tnd + 1e-8))) * 100

    return {
        "mae_log":  round(mae_log,  4),
        "rmse_log": round(rmse_log, 4),
        "r2":       round(r2,       4),
        "mape_pct": round(mape,     2),
    }


def run_model_training() -> dict:
    """
    Trains (or re-trains) the price prediction model on the latest pipeline data.

    Returns a dictionary with performance metrics.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    logger.info("─" * 60)
    logger.info("STAGE 3 │ Model Training Starting…")

    X_train, X_test, y_train, y_test = _load_data()
    n_train = len(X_train)
    n_test  = len(X_test)
    n_features = X_train.shape[1]

    logger.info(f"  Training on {n_train} samples | {n_features} features")

    # ── Model: Gradient Boosting ──────────────────────────────────────────
    # Best balance of accuracy vs. training time for this dataset size.
    # n_estimators: more trees = more accuracy; already good at 400.
    # learning_rate: lower = more stable, combined with more trees.
    # max_depth: 4–5 is ideal for tabular real-estate data.
    model = GradientBoostingRegressor(
        n_estimators=400,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        min_samples_leaf=5,
        random_state=42,
        verbose=0,
    )
    model.fit(X_train, y_train)

    # ── Evaluate ──────────────────────────────────────────────────────────
    metrics = _evaluate(model, X_test, y_test)

    logger.info(f"  R²  Score  : {metrics['r2']:.4f}  (1.0 = perfect)")
    logger.info(f"  MAPE       : {metrics['mape_pct']:.1f}%  (lower = better)")
    logger.info(f"  MAE (log)  : {metrics['mae_log']:.4f}")
    logger.info(f"  RMSE (log) : {metrics['rmse_log']:.4f}")

    # ── Feature Importance ────────────────────────────────────────────────
    fi = pd.Series(
        model.feature_importances_,
        index=X_train.columns
    ).sort_values(ascending=False)

    top5 = fi.head(5)
    logger.info("  Top 5 most predictive features:")
    for feat, score in top5.items():
        logger.info(f"    {feat:25s} {score:.4f}")

    fi_df = fi.reset_index()
    fi_df.columns = ["feature", "importance"]
    fi_df.to_csv(f"{MODEL_DIR}/feature_importance.csv", index=False)

    # ── Save Model ────────────────────────────────────────────────────────
    joblib.dump(model, MODEL_PATH)

    # ── Save Metadata ─────────────────────────────────────────────────────
    metadata = {
        "trained_at": datetime.now().isoformat(),
        "n_train":    n_train,
        "n_test":     n_test,
        "n_features": n_features,
        "features":   list(X_train.columns),
        **metrics,
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    # ── Append to Training Log ────────────────────────────────────────────
    log_row = {"timestamp": datetime.now().isoformat(), "n_samples": n_train, **metrics}
    log_df  = pd.DataFrame([log_row])
    if os.path.exists(TRAIN_LOG):
        existing = pd.read_csv(TRAIN_LOG)
        log_df = pd.concat([existing, log_df], ignore_index=True)
    log_df.to_csv(TRAIN_LOG, index=False)

    logger.info(f"  ✅ Model saved → {MODEL_PATH}")
    logger.info(f"  ✅ Training log updated → {TRAIN_LOG}  ({len(log_df)} runs)")
    logger.info("STAGE 3 │ Complete")
    logger.info("─" * 60)

    return metadata


def predict_price(features: dict) -> float:
    """
    Helper: predict a single property price.
    Pass a dict of feature values (same columns as X_train).
    Returns the predicted price in TND.

    Example:
        predict_price({
            "surface_m2": 120, "log_surface": ..., "rooms": 3,
            "bathrooms": 2, "city_tier": 4, ...
        })
    """
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("No trained model found. Run run_pipeline.py first.")

    model      = joblib.load(MODEL_PATH)
    feature_names = json.load(open(METADATA_PATH))["features"]

    row = pd.DataFrame([features]).reindex(columns=feature_names, fill_value=0)
    log_pred = model.predict(row)[0]
    return round(float(np.expm1(log_pred)), 2)
