"""
ollama_service.py — Appel Ollama robuste avec retry et fallback.

Expose :
  ask_ollama_json(user_prompt) → str   (réponse brute du LLM, attendue en JSON)
  check_ollama_health()        → dict
"""
import os
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "phi3:mini")
OLLAMA_TIMEOUT  = int(os.getenv("OLLAMA_TIMEOUT",  "120"))
OLLAMA_RETRIES  = int(os.getenv("OLLAMA_RETRIES",  "2"))

_SYSTEM_PROMPT = """\
Tu es un assistant immobilier tunisien expert.
Analyse la demande utilisateur et réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après.
Pas de markdown, pas de backticks, pas de commentaires.

Format exact :
{
  "intent": "recommend",
  "city": null,
  "property_type": null,
  "budget_max": null,
  "budget_min": null,
  "rooms": null,
  "bathrooms": null,
  "transaction_type": null,
  "compare": false,
  "top_k": 5
}

Règles :
- "intent" : "recommend" (défaut) ou "compare"
- "city" : ville ou quartier (Soukra/Marsa/Carthage/El Menzah = "Tunis")
- "property_type" : "appartement", "villa", "maison", "studio", "duplex", "terrain", "bureau", "local commercial"
- "budget_max" / "budget_min" : entier en DT, null si absent
- "rooms" : S+1→2, S+2→3, S+3→4, S+4→5 ; nombre de pièces
- "transaction_type" : "location" si louer/rent/ekra ; "vente" si acheter/achat/buy ; null sinon
- "compare" : true si comparaison explicite demandée
- Comprends français, arabe tunisien (nheb=veux, tounes=Tunis, ekra=louer, mahich ghalia=pas cher, dar=maison)
"""


def _post_with_retry(url: str, payload: dict) -> dict:
    last_exc: Exception | None = None
    for attempt in range(OLLAMA_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"[Ollama] Connexion refusée — Ollama est-il lancé ?")
            last_exc = e
            break  # inutile de réessayer
        except requests.exceptions.Timeout as e:
            logger.warning(f"[Ollama] Timeout (tentative {attempt + 1}/{OLLAMA_RETRIES + 1})")
            last_exc = e
        except Exception as e:
            logger.warning(f"[Ollama] Erreur: {e}")
            last_exc = e
        if attempt < OLLAMA_RETRIES:
            time.sleep(1.5 * (attempt + 1))
    raise ConnectionError(
        f"Ollama inaccessible après {OLLAMA_RETRIES + 1} tentative(s) : {last_exc}"
    )


def ask_ollama_json(user_prompt: str) -> str:
    """
    Envoie le prompt à Ollama via /api/chat et retourne la réponse brute (attendue en JSON).
    Lève ConnectionError si Ollama est indisponible.
    """
    payload = {
        "model":  OLLAMA_MODEL,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 250,
            "num_ctx":     1024,
        },
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
    }
    data = _post_with_retry(f"{OLLAMA_BASE_URL}/api/chat", payload)
    raw  = data.get("message", {}).get("content", "").strip()
    logger.info(f"[Ollama] Réponse brute : {raw[:200]}")
    return raw


def check_ollama_health() -> dict:
    """Vérifie la disponibilité d'Ollama et liste les modèles chargés."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {
            "online":        True,
            "models":        models,
            "current_model": OLLAMA_MODEL,
            "base_url":      OLLAMA_BASE_URL,
        }
    except Exception as e:
        return {
            "online":        False,
            "error":         str(e),
            "current_model": OLLAMA_MODEL,
            "base_url":      OLLAMA_BASE_URL,
        }