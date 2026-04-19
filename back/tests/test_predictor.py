"""
test_predictor.py
Tests unitaires du module predictor.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock


MOCK_INDEX = {
    "global_best_model": "prophet",
    "series": {
        "tunis_appartement_vente": {
            "best_model": "prophet",
            "best_mape": 8.4,
            "best_mae": 120.0,
            "best_rmse": 180.0,
            "model_path": "/fake/prophet_tunis_appartement_vente.pkl",
        }
    },
}


def test_slug():
    from predictor import slug
    assert slug("Tunis") == "tunis"
    assert slug("Béja") == "beja"
    assert slug("Ben Arous") == "ben_arous"
    assert slug("À Vendre") == "a_vendre"


def test_find_serie_key_exact():
    with patch("predictor.load_best_model_index", return_value=MOCK_INDEX):
        from predictor import find_serie_key
        key = find_serie_key("Tunis", "appartement", "vente")
        assert key == "tunis_appartement_vente"


def test_find_serie_key_fallback():
    with patch("predictor.load_best_model_index", return_value=MOCK_INDEX):
        from predictor import find_serie_key
        # Zone connue mais type inconnu → fallback sur la seule série
        key = find_serie_key("Tunis", "chalet", "vente")
        assert key is not None


def test_find_serie_key_empty_index():
    with patch("predictor.load_best_model_index", return_value={}):
        from predictor import find_serie_key
        key = find_serie_key("Sfax", "villa", "vente")
        assert key is None


def test_predict_no_model_raises(tmp_path):
    """Vérifie qu'une erreur est levée si aucun modèle n'est disponible."""
    with patch("predictor.load_best_model_index", return_value=MOCK_INDEX), \
         patch("predictor.MODEL_DIR", tmp_path):  # dossier vide
        from predictor import predict
        with pytest.raises((FileNotFoundError, Exception)):
            predict("Tunis", "appartement", "vente", 3500, 24)
