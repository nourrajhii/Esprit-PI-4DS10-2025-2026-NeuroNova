"""
cleaning.py
- Remplace -1 → NaN
- Supprime outliers IQR 99% sur prix et superficie
- Normalise les gouvernorats
- Calcule prix/m²
- Sauvegarde master_clean.csv + rapport_qualite.txt
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_FILE = Path(__file__).parent / "data" / "raw" / "master_raw.csv"
CLEAN_DIR = Path(__file__).parent / "data" / "clean"
CLEAN_FILE = CLEAN_DIR / "master_clean.csv"
RAPPORT_FILE = CLEAN_DIR / "rapport_qualite.txt"


def remove_outliers_iqr(df: pd.DataFrame, col: str, q_low: float = 0.005, q_high: float = 0.995) -> pd.DataFrame:
    series = df[col].dropna()
    q1 = series.quantile(q_low)
    q3 = series.quantile(q_high)
    mask = df[col].isna() | ((df[col] >= q1) & (df[col] <= q3))
    return df[mask]


def clean(raw_file: Path = RAW_FILE) -> pd.DataFrame:
    print(f"  Lecture {raw_file.name} …")
    df = pd.read_csv(raw_file, low_memory=False)
    n_init = len(df)

    # ── 1. Remplace valeurs sentinelle -1 par NaN ──────────────────────────
    num_cols = ["prix", "superficie", "nb_chambres", "nb_sdb"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] == -1, col] = np.nan

    # ── 2. Filtres métier basiques ─────────────────────────────────────────
    df = df[df["prix"] > 0]
    df = df[df["type_transaction"].isin(["vente", "location"])]
    n_after_basic = len(df)

    # ── 3. Outliers IQR 99% ───────────────────────────────────────────────
    df = remove_outliers_iqr(df, "prix")
    n_after_prix = len(df)

    df = remove_outliers_iqr(df, "superficie")
    n_after_sup = len(df)

    # ── 4. Prix / m² ──────────────────────────────────────────────────────
    df["prix_m2"] = np.where(
        (df["superficie"] > 0) & df["superficie"].notna(),
        df["prix"] / df["superficie"],
        np.nan,
    )
    df = remove_outliers_iqr(df, "prix_m2")
    n_after_pm2 = len(df)

    # ── 5. Normaliser catégories ───────────────────────────────────────────
    cat_map = {
        "appartement": "appartement",
        "apartment": "appartement",
        "flat": "appartement",
        "villa": "villa",
        "maison": "maison",
        "house": "maison",
        "terrain": "terrain",
        "land": "terrain",
        "bureau": "bureau",
        "office": "bureau",
        "local commercial": "commercial",
        "commercial": "commercial",
        "ferme": "ferme",
        "farm": "ferme",
    }
    df["categorie"] = df["categorie"].str.lower().str.strip().map(
        lambda x: next((v for k, v in cat_map.items() if k in str(x)), x)
    )

    # ── 6. Date annonce → datetime ─────────────────────────────────────────
    df["date_annonce"] = pd.to_datetime(df["date_annonce"], errors="coerce")

    # ── 7. Sauvegarde ─────────────────────────────────────────────────────
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_FILE, index=False)
    print(f"  master_clean.csv sauvegardé — {len(df):,} lignes")

    # ── 8. Rapport qualité ────────────────────────────────────────────────
    lines = [
        "=== RAPPORT QUALITÉ ===",
        f"Lignes initiales          : {n_init:>8,}",
        f"Après filtres métier      : {n_after_basic:>8,}  (-{n_init - n_after_basic:,})",
        f"Après outliers prix       : {n_after_prix:>8,}  (-{n_after_basic - n_after_prix:,})",
        f"Après outliers superficie : {n_after_sup:>8,}  (-{n_after_prix - n_after_sup:,})",
        f"Après outliers prix/m²    : {n_after_pm2:>8,}  (-{n_after_sup - n_after_pm2:,})",
        "",
        "── Valeurs manquantes (%) ─────────────────────",
    ]
    for col in df.columns:
        pct = df[col].isna().mean() * 100
        if pct > 0:
            lines.append(f"  {col:<25} {pct:5.1f}%")
    lines += [
        "",
        "── Distribution gouvernorats ──────────────────",
    ]
    for gov, cnt in df["gouvernorat"].value_counts().head(15).items():
        lines.append(f"  {gov:<30} {cnt:>6,}")
    lines += [
        "",
        "── Distribution catégories ────────────────────",
    ]
    for cat, cnt in df["categorie"].value_counts().items():
        lines.append(f"  {cat:<30} {cnt:>6,}")

    rapport_text = "\n".join(lines)
    RAPPORT_FILE.write_text(rapport_text, encoding="utf-8")
    print(f"  rapport_qualite.txt sauvegardé")
    print(rapport_text)
    return df


if __name__ == "__main__":
    clean()
