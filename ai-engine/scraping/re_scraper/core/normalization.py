# re_scraper/core/normalization.py
import re

def clean_text(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()

def parse_number(s: str | None) -> float | None:
    """
    Exemples:
      "250 000" -> 250000
      "250,5" -> 250.5
    """
    if not s:
        return None
    s = s.replace("\u202f", " ").replace("\xa0", " ")
    s = s.replace(" ", "")
    s = s.replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None

def parse_price_tnd(raw: str | None) -> int | None:
    v = parse_number(raw)
    if v is None:
        return None
    # prix ML: int
    return int(round(v))

def parse_area_m2(raw: str | None) -> float | None:
    return parse_number(raw)

def infer_listing_type(text: str) -> str:
    t = clean_text(text).lower()
    if any(k in t for k in ["à louer", "location", "louer", "par mois"]):
        return "rent"
    if any(k in t for k in ["à vendre", "vente", "vendre"]):
        return "sale"
    return "unknown"
