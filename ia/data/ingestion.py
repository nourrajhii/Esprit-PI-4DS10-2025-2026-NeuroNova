"""
ingestion.py
Charge les 3 CSV sources et les aligne sur un schéma commun 12 colonnes.
Sortie : data/raw/master_raw.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path(__file__).parent / "data" / "raw"
OUT_FILE = RAW_DIR / "master_raw.csv"

COMMON_COLS = [
    "source",
    "date_annonce",
    "gouvernorat",
    "categorie",        # terrain, appartement, villa, maison, ...
    "type_transaction", # vente, location
    "prix",
    "superficie",
    "nb_chambres",
    "nb_sdb",
    "currency",
    "titre",
    "description",
]

GOUVERNORAT_ALIASES: dict[str, str] = {
    "tunis": "Tunis",
    "ariana": "Ariana",
    "ben arous": "Ben Arous",
    "manouba": "Manouba",
    "nabeul": "Nabeul",
    "zaghouan": "Zaghouan",
    "bizerte": "Bizerte",
    "béja": "Béja",
    "beja": "Béja",
    "jendouba": "Jendouba",
    "kef": "Le Kef",
    "le kef": "Le Kef",
    "siliana": "Siliana",
    "sousse": "Sousse",
    "monastir": "Monastir",
    "mahdia": "Mahdia",
    "sfax": "Sfax",
    "kairouan": "Kairouan",
    "kasserine": "Kasserine",
    "sidi bouzid": "Sidi Bouzid",
    "gabès": "Gabès",
    "gabes": "Gabès",
    "medenine": "Médenine",
    "médenine": "Médenine",
    "tataouine": "Tataouine",
    "gafsa": "Gafsa",
    "tozeur": "Tozeur",
    "kébili": "Kébili",
    "kebili": "Kébili",
    "hammamet": "Nabeul",
    "la marsa": "Tunis",
    "sidi bou said": "Tunis",
    "carthage": "Tunis",
    "lac": "Tunis",
}


def normalize_gouvernorat(raw: str) -> str:
    if pd.isna(raw):
        return np.nan
    raw_lower = str(raw).strip().lower()
    for alias, gov in GOUVERNORAT_ALIASES.items():
        if alias in raw_lower:
            return gov
    return str(raw).strip().title()


def load_property_prices(path: Path) -> pd.DataFrame:
    """Property_Prices_in_Tunisia.csv"""
    df = pd.read_csv(path, low_memory=False)
    out = pd.DataFrame()
    out["source"] = "property_prices_tn"
    out["date_annonce"] = pd.NaT
    out["gouvernorat"] = df["region"].apply(normalize_gouvernorat)
    out["categorie"] = df["category"].str.lower().str.strip()
    out["type_transaction"] = df["type"].map(
        {"À Vendre": "vente", "À Louer": "location", "A Vendre": "vente", "A Louer": "location"}
    ).fillna(df["type"].str.lower())
    out["prix"] = pd.to_numeric(df["price"], errors="coerce")
    out["superficie"] = pd.to_numeric(df["size"].replace(-1, np.nan), errors="coerce")
    out["nb_chambres"] = pd.to_numeric(df["room_count"].replace(-1, np.nan), errors="coerce")
    out["nb_sdb"] = pd.to_numeric(df["bathroom_count"].replace(-1, np.nan), errors="coerce")
    out["currency"] = "TND"
    out["titre"] = np.nan
    out["description"] = np.nan
    return out


def load_scraping(path: Path) -> pd.DataFrame:
    """SCRAPING.csv"""
    df = pd.read_csv(path, low_memory=False)
    out = pd.DataFrame()
    out["source"] = "scraping"
    out["date_annonce"] = pd.to_datetime(df["date"], errors="coerce")
    location = df["city"].fillna(df["location"])
    out["gouvernorat"] = location.apply(normalize_gouvernorat)
    out["categorie"] = df["category"].str.lower().str.strip()
    out["type_transaction"] = df["transaction"].map(
        {"vente": "vente", "location": "location", "À Vendre": "vente", "À Louer": "location"}
    ).fillna(df["transaction"].str.lower())
    out["prix"] = pd.to_numeric(df["price"], errors="coerce")
    out["superficie"] = pd.to_numeric(df["superficie"], errors="coerce")
    out["nb_chambres"] = pd.to_numeric(df["chambres"], errors="coerce")
    out["nb_sdb"] = pd.to_numeric(df["salles_de_bains"], errors="coerce")
    out["currency"] = df["currency"].fillna("TND")
    out["titre"] = df["titles"].astype(str)
    out["description"] = df["descriptions"].astype(str)
    return out


def load_listings(path: Path) -> pd.DataFrame:
    """real_estate_tn_listings.csv"""
    df = pd.read_csv(path, low_memory=False)
    out = pd.DataFrame()
    out["source"] = "listings"
    out["date_annonce"] = pd.to_datetime(df["first_seen"], errors="coerce")
    city_col = "location.city" if "location.city" in df.columns else "city"
    out["gouvernorat"] = df[city_col].apply(normalize_gouvernorat)
    out["categorie"] = df["property_type"].str.lower().str.strip()
    out["type_transaction"] = df["listing_type"].map(
        {"sale": "vente", "rent": "location", "À Vendre": "vente", "À Louer": "location"}
    ).fillna(df["listing_type"].str.lower())
    price_col = "price.value" if "price.value" in df.columns else "price"
    out["prix"] = pd.to_numeric(df[price_col], errors="coerce")
    out["superficie"] = pd.to_numeric(df["area_m2"], errors="coerce")
    out["nb_chambres"] = np.nan
    out["nb_sdb"] = np.nan
    out["currency"] = "TND"
    out["titre"] = np.nan
    out["description"] = np.nan
    return out


def ingest(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    frames = []

    pp_path = raw_dir / "Property_Prices_in_Tunisia.csv"
    sc_path = raw_dir / "SCRAPING.csv"
    li_path = raw_dir / "real_estate_tn_listings.csv"

    if pp_path.exists():
        print(f"  Chargement {pp_path.name} …")
        frames.append(load_property_prices(pp_path))
    else:
        print(f"  [AVERTISSEMENT] {pp_path.name} introuvable — ignoré")

    if sc_path.exists():
        print(f"  Chargement {sc_path.name} …")
        frames.append(load_scraping(sc_path))
    else:
        print(f"  [AVERTISSEMENT] {sc_path.name} introuvable — ignoré")

    if li_path.exists():
        print(f"  Chargement {li_path.name} …")
        frames.append(load_listings(li_path))
    else:
        print(f"  [AVERTISSEMENT] {li_path.name} introuvable — ignoré")

    if not frames:
        raise FileNotFoundError(
            f"Aucun CSV source trouvé dans {raw_dir}. "
            "Placez-y Property_Prices_in_Tunisia.csv, SCRAPING.csv et real_estate_tn_listings.csv."
        )

    master = pd.concat(frames, ignore_index=True)[COMMON_COLS]
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    master.to_csv(OUT_FILE, index=False)
    print(f"  master_raw.csv sauvegardé — {len(master):,} lignes")
    return master


if __name__ == "__main__":
    ingest()
