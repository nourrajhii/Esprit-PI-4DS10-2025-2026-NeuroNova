import re
import unicodedata


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = str(text).strip().lower()
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )
    text = re.sub(r"\s+", " ", text)
    return text