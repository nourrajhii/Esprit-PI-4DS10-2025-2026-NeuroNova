"""
DataLoader v4.0 — Corrigé
- Lecture robuste des colonnes françaises y compris colonnes sans header (False)
- Mapping positionnel en fallback si les noms de colonnes sont absents ou False
- Nettoyage des prix aberrants
- Unité correctement extraite (colonne 5 dans l'ancien fichier avait header=False)
"""

import pandas as pd
import numpy as np
import re

# ── Seuils de prix réalistes pour le marché tunisien 2025 ─────────────────────
PRICE_GLOBAL_MAX = 200_000
PRICE_GLOBAL_MIN = 1

# ── Mapping colonnes françaises → noms internes ────────────────────────────────
COL_NAME_MAP = {
    "titre":          "title",
    "title":          "title",
    "categorie":      "category",
    "catégorie":      "category",
    "category":       "category",
    "cat":            "category",
    "prix (tnd)":     "price",
    "prix(tnd)":      "price",
    "prix tnd":       "price",
    "price":          "price",
    "prix":           "price",
    "prix min":       "price_min",
    "prix_min":       "price_min",
    "price min":      "price_min",
    "min":            "price_min",
    "prix max":       "price_max",
    "prix_max":       "price_max",
    "price max":      "price_max",
    "max":            "price_max",
    "unité":          "unit",
    "unite":          "unit",
    "unité":          "unit",
    "unit":           "unit",
    "ville":          "city",
    "city":           "city",
    "devise":         "devise",
    "fournisseur":    "supplier",
    "supplier":       "supplier",
    "description":    "description",
    "source":         "source_type",
}

# Ordre positionnel attendu si les headers sont absents/invalides
# (titre, categorie, prix, prix_min, prix_max, unite, ville, devise, fournisseur, description, source)
POSITIONAL_MAP = {
    0: "title",
    1: "category",
    2: "price",
    3: "price_min",
    4: "price_max",
    5: "unit",
    6: "city",
    7: "devise",
    8: "supplier",
    9: "description",
    10: "source_type",
}


def _clean_price(value) -> float | None:
    """Nettoie et valide une valeur de prix."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, bool):
        return None
    try:
        s = str(value).strip()
        s = re.sub(r"[\s,'\u00a0\u202f]", "", s)
        v = float(s)
    except (ValueError, TypeError):
        return None

    if v < PRICE_GLOBAL_MIN or v > PRICE_GLOBAL_MAX:
        return None
    return v


def _fmt_price_display(price, price_min, price_max, unit) -> str:
    """Génère un affichage lisible."""
    def _sp(v):
        if v is None:
            return ""
        try:
            return f"{int(round(float(v))):,}".replace(",", "\u202f")
        except Exception:
            return str(v)
    unit = unit or "unité"
    if price_min and price_max:
        return f"{_sp(price_min)} – {_sp(price_max)} DT/{unit}"
    elif price:
        return f"~{_sp(price)} DT/{unit}"
    return "Prix non disponible"


def _normalize_unit(val) -> str:
    """Normalise l'unité : False → 'unité', 'unite' → 'unité', etc."""
    if val is None or val is False or (isinstance(val, float) and np.isnan(val)):
        return "unité"
    s = str(val).strip().lower()
    if s in ("false", "", "nan", "none"):
        return "unité"
    unit_map = {
        "m2": "m²", "m2\r": "m²",
        "unite": "unité", "unites": "unité",
        "piece": "unité", "pièce": "unité",
        "piece(s)": "unité",
    }
    return unit_map.get(s, s)


def load_dataset(filepath: str) -> pd.DataFrame:
    """
    Charge, nettoie et prépare le dataset matériaux.
    Gère les fichiers avec colonnes sans header (valeur False) via mapping positionnel.
    """
    ext = str(filepath).lower()
    if ext.endswith('.xlsx') or ext.endswith('.xlsm'):
        df_raw = pd.read_excel(filepath, engine='openpyxl', header=None)
    else:
        try:
            df_raw = pd.read_excel(filepath, engine='xlrd', header=None)
        except Exception:
            df_raw = pd.read_excel(filepath, engine='openpyxl', header=None)

    # ── Détection de la ligne header ──────────────────────────────────────────
    # On cherche la ligne qui contient "Titre" ou "titre" ou "title" dans la 1ère colonne
    header_row = 0
    for i, row in df_raw.iterrows():
        cell = str(row.iloc[0]).strip().lower()
        if cell in ("titre", "title"):
            header_row = i
            break

    header_values = [str(v).strip().lower() if v is not False else "" 
                     for v in df_raw.iloc[header_row].tolist()]

    # ── Construction du mapping colonnes → noms internes ─────────────────────
    col_rename = {}
    for col_idx, col_label in enumerate(header_values):
        internal = COL_NAME_MAP.get(col_label)
        if not internal:
            # Essai sur le nom de colonne brut (int index depuis pandas)
            internal = POSITIONAL_MAP.get(col_idx)
        if internal:
            col_rename[col_idx] = internal

    # Extraire les données (lignes après le header)
    df = df_raw.iloc[header_row + 1:].copy().reset_index(drop=True)
    df.columns = range(len(df.columns))

    # Renommer selon le mapping
    rename_map = {k: v for k, v in col_rename.items() if k < len(df.columns)}
    df = df.rename(columns=rename_map)

    # Colonnes obligatoires manquantes
    defaults = {
        "title": "",
        "category": "construction",
        "description": "",
        "price": None,
        "price_min": None,
        "price_max": None,
        "unit": "unité",
        "city": "Tunis",
        "supplier": "",
        "source_type": "dataset_reconstruit",
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default

    # ── Nettoyage des titres : False → "" ─────────────────────────────────────
    def _clean_title(v) -> str:
        if v is False or v is None:
            return ""
        s = str(v).strip()
        return "" if s.lower() in ("false", "nan", "none") else s

    df["title_clean"] = df["title"].apply(_clean_title)

    # ── Normalisation catégorie ───────────────────────────────────────────────
    def _clean_cat(v) -> str:
        if v is False or v is None:
            return "construction"
        s = str(v).strip().lower()
        if s in ("false", "nan", "none", ""):
            return "construction"
        s = (s.replace("rénovation", "renovation")
              .replace("électricité", "electricite")
              .replace("plomberie sanitaire", "plomberie")
              .replace("catégorie", "construction"))
        return s

    df["category"] = df["category"].apply(_clean_cat)

    # ── Normalisation unité ───────────────────────────────────────────────────
    df["unit"] = df["unit"].apply(_normalize_unit)

    # ── Nettoyage des prix ────────────────────────────────────────────────────
    df["price"]     = df["price"].apply(_clean_price)
    df["price_min"] = df["price_min"].apply(_clean_price)
    df["price_max"] = df["price_max"].apply(_clean_price)

    # Si price_min > price_max → inverser
    mask_swap = (df["price_min"].notna() & df["price_max"].notna() &
                 (df["price_min"] > df["price_max"]))
    if mask_swap.any():
        df.loc[mask_swap, ["price_min", "price_max"]] = (
            df.loc[mask_swap, ["price_max", "price_min"]].values
        )

    # Si prix principal absent mais fourchette présente → moyenne
    missing_price = df["price"].isna() & df["price_min"].notna() & df["price_max"].notna()
    df.loc[missing_price, "price"] = (
        (df.loc[missing_price, "price_min"] + df.loc[missing_price, "price_max"]) / 2
    ).round(2)

    # ── Pour les lignes sans titre, on crée un titre depuis la catégorie ──────
    no_title = df["title_clean"] == ""
    df.loc[no_title, "title_clean"] = df.loc[no_title, "category"].str.capitalize()

    # Garder uniquement les lignes avec prix valide
    df = df[df["price"].notna() & (df["price"] > 0)].copy()

    # ── Affichage prix ────────────────────────────────────────────────────────
    df["price_display"] = df.apply(
        lambda row: _fmt_price_display(
            row["price"], row.get("price_min"), row.get("price_max"), row.get("unit")
        ),
        axis=1,
    )

    # ── Texte pour embedding ──────────────────────────────────────────────────
    desc_col = df.get("description", pd.Series([""] * len(df)))
    df["text_for_embedding"] = (
        df["title_clean"]
        + " | " + df["category"]
        + " | " + df["unit"]
        + " | " + desc_col.fillna("").astype(str)
    )

    df = df.reset_index(drop=True)

    print(f"✅ Dataset chargé : {len(df)} lignes valides")
    print(f"   Catégories : {df['category'].value_counts().to_dict()}")
    pct = df["price_min"].notna().mean() * 100
    print(f"   Lignes avec fourchette min/max : {pct:.1f}%")
    print(f"   Lignes avec titre descriptif : {(df['title_clean'] != df['category'].str.capitalize()).sum()}")

    return df