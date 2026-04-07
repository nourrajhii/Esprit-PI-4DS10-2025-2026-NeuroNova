"""
Pipeline de nettoyage - exports/materiaux.xls
Opérations :
  1. Supprimer les colonnes entièrement vides (100% NaN)
  2. Supprimer les lignes avec price = 0
  3. Supprimer les doublons globaux (title + category + subcategory + price)
  4. Supprimer les doublons carrelage (title + category + price)
  5. Corriger les prix illogiques (min+max collés) -> remplacer par la moyenne
  6. Normaliser les prix (Min-Max entre 0 et 1)
  7. Trier par category (ordre alphabétique A → Z)
"""

import os
import pandas as pd

# ── Chemins ───────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH  = os.path.join(BASE_DIR, "exports", "materiaux.xls")
OUTPUT_CSV  = os.path.join(BASE_DIR, "exports", "materiaux_cleaned.csv")
OUTPUT_XLSX = os.path.join(BASE_DIR, "exports", "materiaux_cleaned.xlsx")
# ─────────────────────────────────────────────────────────────

SEUIL_PRIX_ILLOGIQUE = 1_000_000

# Chargement
df = pd.read_excel(INPUT_PATH, engine='calamine')
print(f"[CHARGEMENT]  {df.shape[0]} lignes x {df.shape[1]} colonnes")

# ── ÉTAPE 1 : Supprimer les colonnes entièrement vides ────────
cols_vides = [col for col in df.columns if df[col].isna().all()]
df.drop(columns=cols_vides, inplace=True)
print(f"[ÉTAPE 1]     Colonnes vides supprimées : {cols_vides if cols_vides else 'aucune'}")

# ── ÉTAPE 2 : Supprimer les lignes avec price = 0 ─────────────
n = len(df)
df = df[df['price'] != 0].reset_index(drop=True)
print(f"[ÉTAPE 2]     Lignes price=0 supprimées : {n - len(df)}")

# ── ÉTAPE 3 : Doublons globaux (title + category + subcategory + price) ───
n = len(df)
df.drop_duplicates(subset=['title', 'category', 'subcategory', 'price'], keep='first', inplace=True)
df.reset_index(drop=True, inplace=True)
print(f"[ÉTAPE 3]     Doublons globaux supprimés : {n - len(df)}")

# ── ÉTAPE 4 : Doublons carrelage (title + category + price) ──
n = len(df)
non_carrelage = df[df['category'] != 'carrelage']
carrelage     = df[df['category'] == 'carrelage'].drop_duplicates(
                    subset=['title', 'category', 'price'], keep='first')
df = pd.concat([non_carrelage, carrelage]).sort_index().reset_index(drop=True)
print(f"[ÉTAPE 4]     Doublons carrelage supprimés : {n - len(df)}")

# ── ÉTAPE 5 : Corriger les prix illogiques ────────────────────
def corriger_prix(val):
    if val >= SEUIL_PRIX_ILLOGIQUE:
        s = str(int(val))
        mid = len(s) // 2
        return (int(s[:mid]) + int(s[mid:])) / 2
    return val

n_corriges = (df['price'] >= SEUIL_PRIX_ILLOGIQUE).sum()
df['price'] = df['price'].apply(corriger_prix)
print(f"[ÉTAPE 5]     Prix illogiques corrigés : {n_corriges} valeurs")

# ── ÉTAPE 6 : Normalisation Min-Max ───────────────────────────
def minmax(col):
    mn, mx = col.min(), col.max()
    return (col - mn) / (mx - mn) if mx != mn else col * 0

df['price_norm']     = minmax(df['price'])
df['price_min_norm'] = minmax(df['price_min'])
df['price_max_norm'] = minmax(df['price_max'])
print(f"[ÉTAPE 6]     Colonnes normalisées : price_norm, price_min_norm, price_max_norm")

# ── ÉTAPE 7 : Trier par category (ordre alphabétique A → Z) ──
df.sort_values('category', ascending=True, inplace=True)
df.reset_index(drop=True, inplace=True)
print(f"[ÉTAPE 7]     Trié par category (A → Z)")

print(f"\n[RÉSULTAT]    {df.shape[0]} lignes x {df.shape[1]} colonnes")

# Export
df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
df.to_excel(OUTPUT_XLSX, index=False)
print(f"[EXPORT]      → {OUTPUT_CSV}")
print(f"[EXPORT]      → {OUTPUT_XLSX}")
print("\n✅ Pipeline terminée.")