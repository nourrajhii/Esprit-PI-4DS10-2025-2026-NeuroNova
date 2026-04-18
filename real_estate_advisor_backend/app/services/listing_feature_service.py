import re
from app.services.text_normalizer_service import normalize_text


def detect_rooms_from_text(title: str) -> int | None:
    text = normalize_text(title)

    # détecte s+1, s+2, s+3...
    match = re.search(r"s\s*\+\s*(\d+)", text)
    if match:
        try:
            return int(match.group(1)) + 1
        except Exception:
            return None

    # fallback simple "3 pieces"
    match = re.search(r"(\d+)\s*piece", text)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return None

    return None


def detect_transaction_from_text(title: str, url: str = "") -> str | None:
    text = normalize_text((title or "") + " " + (url or ""))

    if any(x in text for x in ["a louer", "alouer", "louer", "location", "rent"]):
        return "location"

    if any(x in text for x in ["a vendre", "avendre", "vendre", "vente", "buy"]):
        return "vente"

    return None