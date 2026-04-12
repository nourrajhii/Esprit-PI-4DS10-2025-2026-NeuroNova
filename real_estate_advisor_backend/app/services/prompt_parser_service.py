import json
from app.services.ollama_service import ask_ollama
from app.services.property_classifier_service import classify_property_request


def parse_user_prompt(user_prompt: str) -> dict:
    system_prompt = f"""
Tu es un assistant immobilier.
Analyse le prompt utilisateur et retourne uniquement un JSON valide.
Ne retourne aucun texte supplémentaire.

Format JSON attendu :
{{
  "intent": "recommend" ou "compare",
  "city": "string ou null",
  "property_type": "string ou null",
  "budget_max": number ou null,
  "budget_min": number ou null,
  "rooms": number ou null,
  "bathrooms": number ou null,
  "transaction_type": "vente" ou "location" ou null,
  "compare": true ou false,
  "top_k": 5
}}

Prompt utilisateur :
{user_prompt}
"""

    raw = ask_ollama(system_prompt)

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        cleaned = raw[start:end]
        parsed = json.loads(cleaned)
    except Exception:
        parsed = {
            "intent": "recommend",
            "city": None,
            "property_type": None,
            "budget_max": None,
            "budget_min": None,
            "rooms": None,
            "bathrooms": None,
            "transaction_type": None,
            "compare": False,
            "top_k": 5,
        }

    classification = classify_property_request(user_prompt)

    transaction_type = parsed.get("transaction_type")
    if not transaction_type:
        transaction_type = "location" if classification["intent"] == "rent" else "vente"

    return {
        "intent": parsed.get("intent", "recommend"),
        "city": parsed.get("city"),
        "property_type": parsed.get("property_type"),
        "budget_max": parsed.get("budget_max"),
        "budget_min": parsed.get("budget_min"),
        "rooms": parsed.get("rooms"),
        "bathrooms": parsed.get("bathrooms"),
        "transaction_type": transaction_type,
        "compare": parsed.get("compare", False),
        "top_k": parsed.get("top_k", 5),
        "category": classification["category"],
        "sub_type": classification["sub_type"],
        "allowed_property_types": classification["allowed_property_types"],
        "intent_mode": classification["intent"]
    }