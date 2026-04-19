"""
feature_engineering.py
- Agrégation mensuelle médiane prix/m² par (gouvernorat, categorie, type_transaction)
- Simulation 18 mois d'historique quand les données sont trop récentes
- Test ADF de stationnarité
- Sauvegarde data/series/serie_{zone}_{type}_{tx}.csv au format Prophet (ds, y)
- Sauvegarde rapport_stats.txt
"""

import warnings
import re
import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

CLEAN_FILE = Path(__file__).parent / "data" / "clean" / "master_clean.csv"
SERIES_DIR = Path(__file__).parent / "data" / "series"
RAPPORT_FILE = Path(__file__).parent / "data" / "clean" / "rapport_stats.txt"

MIN_OBS = 6          # nombre minimal d'observations mensuelles pour conserver une série
SIMULATION_MONTHS = 18  # mois d'historique simulés si insuffisant


def slug(text: str) -> str:
    """Convertit un texte en slug utilisable dans un nom de fichier."""
    text = str(text).lower().strip()
    text = re.sub(r"[éèêë]", "e", text)
    text = re.sub(r"[àâä]", "a", text)
    text = re.sub(r"[ùûü]", "u", text)
    text = re.sub(r"[ôö]", "o", text)
    text = re.sub(r"[îï]", "i", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def simulate_history(last_value: float, n_months: int, trend: float = 0.003, noise: float = 0.02) -> pd.Series:
    """Génère n_months de données simulées antérieures à last_value."""
    rng = np.random.default_rng(42)
    values = [last_value]
    for _ in range(n_months - 1):
        prev = values[-1]
        values.append(prev / (1 + trend + rng.normal(0, noise)))
    values.reverse()
    return pd.Series(values)


def adf_test(series: pd.Series) -> dict:
    """Retourne les résultats du test ADF."""
    try:
        result = adfuller(series.dropna(), autolag="AIC")
        return {
            "statistic": round(result[0], 4),
            "p_value": round(result[1], 4),
            "is_stationary": result[1] < 0.05,
        }
    except Exception:
        return {"statistic": None, "p_value": None, "is_stationary": None}


def build_series(clean_file: Path = CLEAN_FILE) -> list[dict]:
    print(f"  Lecture {clean_file.name} …")
    df = pd.read_csv(clean_file, low_memory=False)

    # Colonnes nécessaires
    df["date_annonce"] = pd.to_datetime(df["date_annonce"], errors="coerce")
    df = df.dropna(subset=["prix_m2", "gouvernorat", "categorie", "type_transaction"])
    df = df[df["prix_m2"] > 0]

    # Période mensuelle
    df["mois"] = df["date_annonce"].dt.to_period("M")

    # Agrégation
    agg = (
        df.groupby(["gouvernorat", "categorie", "type_transaction", "mois"])["prix_m2"]
        .median()
        .reset_index()
    )
    agg["mois"] = agg["mois"].dt.to_timestamp()

    SERIES_DIR.mkdir(parents=True, exist_ok=True)

    rapport_lines = ["=== RAPPORT STATISTIQUES SÉRIES TEMPORELLES ===", ""]
    series_meta = []

    groups = agg.groupby(["gouvernorat", "categorie", "type_transaction"])

    for (gov, cat, tx), grp in groups:
        grp = grp.sort_values("mois").reset_index(drop=True)
        n_real = len(grp)

        # Compléter avec simulation si insuffisant
        if n_real < MIN_OBS:
            if n_real == 0:
                continue
            need = SIMULATION_MONTHS - n_real
            first_val = grp["prix_m2"].iloc[0]
            sim_values = simulate_history(first_val, need + 1)[:-1]
            first_date = grp["mois"].iloc[0]
            sim_dates = pd.date_range(end=first_date - pd.DateOffset(months=1), periods=need, freq="MS")
            sim_df = pd.DataFrame({"mois": sim_dates, "prix_m2": sim_values.values, "simulated": True})
            grp["simulated"] = False
            grp = pd.concat([sim_df, grp], ignore_index=True).sort_values("mois")

        # Format Prophet : ds, y
        prophet_df = pd.DataFrame({
            "ds": grp["mois"].values,
            "y": grp["prix_m2"].values,
        })

        # Test ADF
        adf = adf_test(prophet_df["y"])

        # Sauvegarde
        fname = f"serie_{slug(gov)}_{slug(cat)}_{slug(tx)}.csv"
        fpath = SERIES_DIR / fname
        prophet_df.to_csv(fpath, index=False)

        meta = {
            "fichier": fname,
            "gouvernorat": gov,
            "categorie": cat,
            "type_transaction": tx,
            "n_obs": len(prophet_df),
            "n_obs_reels": n_real,
            "prix_median": round(prophet_df["y"].median(), 2),
            "adf_statistic": adf["statistic"],
            "adf_p_value": adf["p_value"],
            "is_stationary": adf["is_stationary"],
        }
        series_meta.append(meta)

        rapport_lines.append(
            f"{gov} | {cat} | {tx} → {len(prophet_df)} obs "
            f"(réels={n_real}) | médiane={meta['prix_median']:.0f} TND/m² "
            f"| ADF p={adf['p_value']} {'✓' if adf['is_stationary'] else '~'}"
        )

    # Sauvegarde rapport
    rapport_lines += [
        "",
        f"Total séries générées : {len(series_meta)}",
        f"Séries stationnaires  : {sum(1 for m in series_meta if m['is_stationary'])}",
    ]
    rapport_text = "\n".join(rapport_lines)
    RAPPORT_FILE.write_text(rapport_text, encoding="utf-8")
    print(rapport_text)
    print(f"\n  {len(series_meta)} séries sauvegardées dans {SERIES_DIR}")
    return series_meta


if __name__ == "__main__":
    build_series()
