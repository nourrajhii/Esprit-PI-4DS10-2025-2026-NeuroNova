"""
test_api.py
Tests d'intégration FastAPI avec httpx.AsyncClient.
Lance l'API en mémoire — ne nécessite pas de modèles réels.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport

# Mock du predictor avant l'import de main
MOCK_RESULT = {
    "zone": "Tunis",
    "type_bien": "appartement",
    "type_transaction": "vente",
    "modele_utilise": "prophet",
    "mape_test": 8.4,
    "serie_utilisee": "tunis_appartement_vente",
    "points": [
        {"date": "2025-05-01", "prix_predit": 3612.0, "ic_bas": 3200.0, "ic_haut": 4024.0},
        {"date": "2025-06-01", "prix_predit": 3650.0, "ic_bas": 3230.0, "ic_haut": 4070.0},
    ] * 12,
    "resume": {
        "prix_j12": 3750.0,
        "prix_j24": 3950.0,
        "variation_pct_12": 7.1,
        "variation_pct_24": 12.9,
        "tendance": "hausse",
    },
}


@pytest.fixture
def mock_predict():
    with patch("predictor.predict", return_value=MOCK_RESULT), \
         patch("predictor.load_best_model_index", return_value={"series": {"tunis_appartement_vente": {}}, "global_best_model": "prophet"}), \
         patch("predictor.MODEL_DIR") as mock_dir:
        mock_dir.glob.return_value = [MagicMock()]
        mock_dir.exists.return_value = True
        yield


@pytest.fixture
async def client(mock_predict):
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "models_loaded" in data


@pytest.mark.asyncio
async def test_predict_success(client):
    payload = {
        "zone": "Tunis",
        "type_bien": "appartement",
        "type_transaction": "vente",
        "prix_estime_actuel": 3500,
        "horizon_mois": 24,
    }
    resp = await client.post("/api/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "points" in data
    assert "resume" in data
    assert data["modele_utilise"] == "prophet"
    assert data["resume"]["tendance"] in ("hausse", "baisse", "stable")


@pytest.mark.asyncio
async def test_predict_invalid_transaction(client):
    payload = {
        "zone": "Tunis",
        "type_bien": "appartement",
        "type_transaction": "swap",  # invalide
        "prix_estime_actuel": 3500,
    }
    resp = await client.post("/api/predict", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_predict_negative_price(client):
    payload = {
        "zone": "Tunis",
        "type_bien": "appartement",
        "type_transaction": "vente",
        "prix_estime_actuel": -100,
    }
    resp = await client.post("/api/predict", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_zones(client):
    resp = await client.get("/api/zones")
    assert resp.status_code == 200
    data = resp.json()
    assert "zones" in data
    assert "types_bien" in data
    assert "types_transaction" in data
