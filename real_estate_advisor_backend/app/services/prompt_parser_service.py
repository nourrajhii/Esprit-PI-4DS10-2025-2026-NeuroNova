import json
import re
from app.services.ollama_service import ask_ollama_json
from app.services.text_normalizer_service import normalize_text
from app.services.property_classifier_service import classify_property_request


KNOWN_CITIES = [
    "tunis", "ariana", "ben arous", "manouba", "bizerte", "sousse", "sfax",
    "nabeul", "monastir", "mahdia", "gabes", "medenine", "kairouan",
    "djerba", "hammamet", "mornag", "rades", "megrine", "ezzahra",
    "la marsa", "lac", "lafayette", "soukra", "carthage", "sidi bou said",
    "ennasr", "el menzah", "el manar", "cite el khadhra", "raoued"
]

REAL_ESTATE_KEYWORDS = [
    "appartement", "studio", "duplex", "villa", "maison", "dar",
    "terrain", "lot", "ferme", "bureau", "plateau", "local", "commerce",
    "magasin", "entrepot", "entrepôt", "immobilier",
    "s+1", "s+2", "s+3", "s+4",
    "louer", "location", "a louer", "à louer",
    "acheter", "vente", "a vendre", "à vendre",
    "rent", "sale", "buy"
]


def is_real_estate_query(user_prompt: str) -> bool:
    text = normalize_text(user_prompt)
    return any(keyword in text for keyword in REAL_ESTATE_KEYWORDS)


def extract_city_from_prompt(user_prompt: str) -> str | None:
    text = normalize_text(user_prompt)

    for city in KNOWN_CITIES:
        if city in text:
            city_map = {
                "la marsa": "Tunis",
                "lac": "Tunis",
                "lafayette": "Tunis",
                "soukra": "Tunis",
                "carthage": "Tunis",
                "sidi bou said": "Tunis",
                "ennasr": "Ariana",
                "el menzah": "Tunis",
                "el manar": "Tunis",
                "cite el khadhra": "Tunis",
                "raoued": "Ariana",
                "manouba": "Manouba",
                "ben arous": "Ben Arous",
                "bizerte": "Bizerte",
                "sousse": "Sousse",
                "sfax": "Sfax",
                "nabeul": "Nabeul",
                "tunis": "Tunis",
                "ariana": "Ariana",
            }
            return city_map.get(city, city.title())

    return None


def extract_rooms_from_prompt(user_prompt: str) -> int | None:
    text = normalize_text(user_prompt)

    s_match = re.search(r"\bs\+?\s*(\d)\b", text)
    if s_match:
        return int(s_match.group(1))

    room_match = re.search(r"(\d+)\s*(chambre|chambres|piece|pieces|pi[eè]ces)", text)
    if room_match:
        return int(room_match.group(1))

    if "studio" in text:
        return 1

    return None


def extract_budget_from_prompt(user_prompt: str) -> tuple[float | None, float | None]:
    text = normalize_text(user_prompt)
    values = [float(v.replace(",", ".")) for v in re.findall(r"\d+(?:[.,]\d+)?", text)]
    values = [v for v in values if v >= 100]

    if not values:
        return None, None

    if "entre" in text and len(values) >= 2:
        return min(values[0], values[1]), max(values[0], values[1])

    if any(k in text for k in ["budget", "max", "maximum", "jusqu", "moins de", "pas plus"]):
        return None, max(values)

    return None, max(values)


def normalize_transaction(value: str | None, prompt: str = "") -> str | None:
    v = normalize_text(value or "")
    p = normalize_text(prompt)

    if v in ["location", "a louer", "à louer", "louer", "rent"]:
        return "location"
    if v in ["vente", "a vendre", "à vendre", "acheter", "buy", "sale"]:
        return "vente"

    if any(x in p for x in ["louer", "location", "a louer", "à louer", "rent"]):
        return "location"
    if any(x in p for x in ["vendre", "vente", "acheter", "a vendre", "à vendre", "sale", "buy"]):
        return "vente"

    return None


def parse_user_prompt(user_prompt: str) -> dict:
    if not is_real_estate_query(user_prompt):
        return {
            "intent": "other",
            "city": None,
            "property_type": None,
            "budget_max": None,
            "budget_min": None,
            "rooms": None,
            "bathrooms": None,
            "transaction_type": None,
            "compare": False,
            "top_k": 5,
            "category": None,
            "sub_type": None,
            "allowed_property_types": [],
            "intent_mode": None,
            "is_real_estate_query": False,
        }

    raw = ""
    parsed = {}

    try:
        raw = ask_ollama_json(user_prompt)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end != -1:
            parsed = json.loads(raw[start:end])
    except Exception:
        parsed = {}

    classification = classify_property_request(user_prompt)

    fallback_budget_min, fallback_budget_max = extract_budget_from_prompt(user_prompt)
    fallback_city = extract_city_from_prompt(user_prompt)
    fallback_rooms = extract_rooms_from_prompt(user_prompt)

    transaction_type = normalize_transaction(parsed.get("transaction_type"), user_prompt)
    if not transaction_type:
        transaction_type = "location" if classification["intent"] == "rent" else "vente" if classification["intent"] == "sale" else None

    return {
        "intent": parsed.get("intent", "recommend"),
        "city": parsed.get("city") or fallback_city,
        "property_type": parsed.get("property_type"),
        "budget_max": parsed.get("budget_max") if parsed.get("budget_max") is not None else fallback_budget_max,
        "budget_min": parsed.get("budget_min") if parsed.get("budget_min") is not None else fallback_budget_min,
        "rooms": parsed.get("rooms") if parsed.get("rooms") is not None else fallback_rooms,
        "bathrooms": parsed.get("bathrooms"),
        "transaction_type": transaction_type,
        "compare": parsed.get("compare", False),
        "top_k": parsed.get("top_k", 5),
        "category": classification["category"],
        "sub_type": classification["sub_type"],
        "allowed_property_types": classification["allowed_property_types"],
        "intent_mode": classification["intent"],
        "is_real_estate_query": True,
    }