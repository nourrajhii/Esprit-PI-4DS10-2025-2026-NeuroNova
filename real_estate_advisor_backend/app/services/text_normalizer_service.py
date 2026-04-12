import unicodedata
import re


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower().strip()

    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text