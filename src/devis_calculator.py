"""
DevisCalculator v8.0 — Mapping amélioré
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Corrections v8.0 :
  - Suppression du filtre `unite` (colonne souvent absente/cassée dans le dataset)
  - Ajout d'un filtre par catégorie en priorité, puis recherche sans filtre
  - Mots-clés enrichis pour chaque poste
  - Fallback par catégorie si aucun titre ne matche
  - Seuils de prix réalistes par poste
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import math
import pandas as pd

# ── Surfaces standard par pièce (m²) ─────────────────────────────────────────
SURF_PIECE = {
    "chambre":       14,
    "salon":         25,
    "cuisine":       12,
    "salle_de_bain":  6,
    "wc":             3,
    "couloir":        8,
    "entree":         5,
}


def _fmt(v: float) -> str:
    if v is None:
        return "0"
    try:
        f = float(v)
        if f != f:
            return "0"
        return f"{int(round(f)):,}".replace(",", "\u202f")
    except Exception:
        return "0"


def _fmt_dt(v: float) -> str:
    return f"{_fmt(v)} DT"


class DevisCalculator:

    def __init__(self):
        self._df: pd.DataFrame | None = None

    # ──────────────────────────────────────────────────────────────────────────
    # CHARGEMENT
    # ──────────────────────────────────────────────────────────────────────────

    def load_dataset(self, filepath: str):
        ext = str(filepath).lower()
        if ext.endswith(".csv"):
            for enc in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    df = pd.read_csv(filepath, encoding=enc, sep=";")
                    break
                except UnicodeDecodeError:
                    continue
        elif ext.endswith(".xlsx") or ext.endswith(".xlsm"):
            df = pd.read_excel(filepath, engine="openpyxl", header=None)
        else:
            try:
                df = pd.read_excel(filepath, engine="xlrd", header=None)
            except Exception:
                df = pd.read_excel(filepath, engine="openpyxl", header=None)

        # ── Détection du header ────────────────────────────────────────────────
        header_row = 0
        for i, row in df.iterrows():
            cell = str(row.iloc[0]).strip().lower()
            if cell in ("titre", "title"):
                header_row = i
                break

        header_values = df.iloc[header_row].tolist()
        df = df.iloc[header_row + 1:].copy().reset_index(drop=True)
        df.columns = range(len(df.columns))

        # ── Mapping colonnes ───────────────────────────────────────────────────
        COL_MAP = {}
        POSITIONAL = {0: "titre", 1: "categorie", 2: "prix", 3: "prix_min",
                      4: "prix_max", 5: "unite", 6: "ville", 7: "devise",
                      8: "fournisseur", 9: "description", 10: "source"}
        NAME_MAP = {
            "titre": "titre", "title": "titre",
            "categorie": "categorie", "catégorie": "categorie", "category": "categorie",
            "prix (tnd)": "prix", "prix(tnd)": "prix", "prix tnd": "prix",
            "price": "prix", "prix": "prix",
            "prix min": "prix_min", "prix_min": "prix_min", "price min": "prix_min",
            "prix max": "prix_max", "prix_max": "prix_max", "price max": "prix_max",
            "unité": "unite", "unite": "unite", "unit": "unite",
        }
        for idx, h in enumerate(header_values):
            h_lower = str(h).strip().lower() if h is not False else ""
            mapped = NAME_MAP.get(h_lower) or POSITIONAL.get(idx)
            if mapped:
                COL_MAP[idx] = mapped

        df = df.rename(columns=COL_MAP)

        # Colonnes manquantes
        for col, default in [("titre", ""), ("categorie", "construction"),
                              ("prix", None), ("prix_min", None),
                              ("prix_max", None), ("unite", "unité")]:
            if col not in df.columns:
                df[col] = default

        # ── Nettoyage ──────────────────────────────────────────────────────────
        def _clean_title(v) -> str:
            if v is False or v is None:
                return ""
            s = str(v).strip()
            return "" if s.lower() in ("false", "nan", "none") else s

        def _clean_unit(v) -> str:
            if v is False or v is None:
                return "unité"
            s = str(v).strip().lower()
            if s in ("false", "nan", "none", ""):
                return "unité"
            return {"m2": "m²", "unite": "unité", "unites": "unité",
                    "piece": "unité", "pièce": "unité"}.get(s, s)

        def _clean_price(val):
            if val is False or val is None:
                return None
            if isinstance(val, float) and (val != val):  # NaN
                return None
            try:
                import re
                s = str(val).replace(" ", "").replace(",", "").replace("\u202f", "")
                v = float(s)
                return v if 0 < v < 200_000 else None
            except (ValueError, TypeError):
                return None

        def _clean_cat(v) -> str:
            if v is False or v is None:
                return "construction"
            s = str(v).strip().lower()
            if s in ("false", "nan", "none", "", "catégorie"):
                return "construction"
            return (s.replace("rénovation", "renovation")
                     .replace("électricité", "electricite")
                     .replace("plomberie sanitaire", "plomberie"))

        df["titre_raw"]  = df["titre"].apply(_clean_title)
        df["categorie"]  = df["categorie"].apply(_clean_cat)
        df["unite"]      = df["unite"].apply(_clean_unit)
        df["prix"]       = df["prix"].apply(_clean_price)
        df["prix_min"]   = df["prix_min"].apply(_clean_price)
        df["prix_max"]   = df["prix_max"].apply(_clean_price)

        # Titre fallback = catégorie si vide
        df["titre"] = df.apply(
            lambda r: r["titre_raw"] if r["titre_raw"] else r["categorie"].capitalize(),
            axis=1
        )
        df["titre_lower"] = df["titre"].str.lower()

        # Prix moyen si absent mais fourchette présente
        mask = df["prix"].isna() & df["prix_min"].notna() & df["prix_max"].notna()
        df.loc[mask, "prix"] = (
            (df.loc[mask, "prix_min"] + df.loc[mask, "prix_max"]) / 2
        ).round(2)

        df = df[df["prix"].notna() & (df["prix"] > 0)].copy().reset_index(drop=True)
        self._df = df

        print(f"✅ Dataset chargé : {len(df)} lignes valides")
        print(f"   Catégories : {df['categorie'].value_counts().to_dict()}")

    # ──────────────────────────────────────────────────────────────────────────
    # MOTEUR DE RECHERCHE
    # ──────────────────────────────────────────────────────────────────────────

    def search(self, keywords: list, categories: list = None,
               top_n: int = 1, price_min_filter: float = None,
               price_max_filter: float = None) -> list:
        """
        Recherche les meilleures lignes du dataset par score de matching sur les mots-clés.
        
        PLUS de filtre par unité (colonne souvent absente/cassée).
        Filtre optionnel sur les catégories.
        """
        if self._df is None or self._df.empty:
            return []

        df = self._df.copy()

        # Filtre catégorie
        if categories:
            cats = [c.lower() for c in categories]
            df_cat = df[df["categorie"].isin(cats)]
            # Si le filtre catégorie ne laisse rien, on cherche sans filtre
            df = df_cat if not df_cat.empty else df

        # Filtre de prix réaliste
        if price_min_filter is not None:
            df = df[df["prix"] >= price_min_filter]
        if price_max_filter is not None:
            df = df[df["prix"] <= price_max_filter]

        if df.empty:
            return []

        kws_lower = [k.lower() for k in keywords]
        df = df.copy()
        # Score = nb de mots-clés présents dans le titre
        df["_score"] = df["titre_lower"].apply(
            lambda titre: sum(1 for kw in kws_lower if kw in titre)
        )
        # Bonus si match sur la catégorie
        if categories:
            cats = [c.lower() for c in categories]
            df["_score"] += df["categorie"].apply(
                lambda c: 1 if c in cats else 0
            )

        df = df[df["_score"] > 0].sort_values("_score", ascending=False)

        if df.empty:
            # Fallback : retourner la meilleure ligne de la catégorie demandée
            if categories:
                df = self._df[self._df["categorie"].isin([c.lower() for c in categories])].copy()
            if df.empty:
                return []
            df["_score"] = 0

        results = []
        for _, row in df.head(top_n).iterrows():
            prix     = float(row["prix"])
            prix_min = float(row["prix_min"]) if pd.notna(row.get("prix_min")) and row["prix_min"] else round(prix * 0.80)
            prix_max = float(row["prix_max"]) if pd.notna(row.get("prix_max")) and row["prix_max"] else round(prix * 1.25)
            if prix_min > prix_max:
                prix_min, prix_max = prix_max, prix_min
            results.append({
                "titre":     str(row["titre"]),
                "min":       round(prix_min),
                "mid":       round(prix),
                "max":       round(prix_max),
                "unite":     str(row["unite"]),
                "categorie": str(row["categorie"]),
                "score":     int(row.get("_score", 0)),
            })
        return results

    def best(self, keywords: list, categories: list = None,
             price_min_filter: float = None,
             price_max_filter: float = None) -> dict | None:
        results = self.search(keywords, categories=categories, top_n=1,
                              price_min_filter=price_min_filter,
                              price_max_filter=price_max_filter)
        return results[0] if results else None

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS POSTES
    # ──────────────────────────────────────────────────────────────────────────

    def _poste(self, description: str, quantite: float,
               unite_label: str, r: dict) -> dict:
        return {
            "description": description,
            "quantite":    quantite,
            "unite":       unite_label,
            "prix_min_u":  r["min"],
            "prix_mid_u":  r["mid"],
            "prix_max_u":  r["max"],
            "cout_min":    round(quantite * r["min"]),
            "cout_mid":    round(quantite * r["mid"]),
            "cout_max":    round(quantite * r["max"]),
            "fourchette":  f"{_fmt(r['min'])} – {_fmt(r['max'])} DT/{unite_label}",
            "source":      r.get("titre", "")[:80],
        }

    def _poste_ff(self, description: str, r: dict) -> dict:
        return self._poste(description, 1, "forfait", r)

    # ──────────────────────────────────────────────────────────────────────────
    # SURFACES
    # ──────────────────────────────────────────────────────────────────────────

    def estimate_surfaces(self, terrain_m2: float, pieces: dict) -> dict:
        has_jardin  = bool(pieces.get("jardin",  False))
        has_piscine = bool(pieces.get("piscine", False))

        # Règles surfaces :
        #   piscine demandée          → piscine 20% + jardin 20% (= 40% au total)
        #   jardin seul, terrain >200 → jardin 20%
        #   jardin seul, terrain ≤200 → jardin 10%
        #   rien                      → 0%
        if has_piscine:
            ratio_piscine = 0.20
            ratio_jardin  = 0.20   # jardin toujours inclus avec piscine
        elif has_jardin:
            ratio_piscine = 0.00
            ratio_jardin  = 0.20 if terrain_m2 > 200 else 0.10
        else:
            ratio_piscine, ratio_jardin = 0.00, 0.00

        surf_piscine = round(terrain_m2 * ratio_piscine, 1)
        surf_jardin  = round(terrain_m2 * ratio_jardin,  1)
        surf_allee   = round(terrain_m2 * 0.10,          1)
        surf_hab     = max(
            round(terrain_m2 - surf_piscine - surf_jardin - surf_allee, 1),
            20.0
        )

        cote = math.sqrt(surf_hab) * 1.2
        return {
            "terrain_total":     terrain_m2,
            "surface_habitable": surf_hab,
            "surface_jardin":    surf_jardin,
            "surface_piscine":   surf_piscine,
            "surface_allee":     surf_allee,
            "surface_murs":      round(cote * 4 * 2.8, 1),
            "surface_plafond":   surf_hab,
            "surface_toiture":   round(surf_hab * 1.15, 1),
            "has_jardin":        has_jardin,
            "has_piscine":       has_piscine,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # DISPATCH
    # ──────────────────────────────────────────────────────────────────────────

    def build_devis(self, surfaces: dict, rag_prices: dict,
                    pieces: dict = None) -> dict:
        mode   = rag_prices.get("_meta", {}).get("mode", "construction")
        pieces = pieces or {}
        if mode == "renovation":
            return self._build_renovation(surfaces, pieces)
        elif mode == "cafe_commerce":
            return self._build_cafe(surfaces, pieces)
        else:
            return self._build_construction(surfaces, pieces)

    # ──────────────────────────────────────────────────────────────────────────
    # DEVIS CONSTRUCTION
    # ──────────────────────────────────────────────────────────────────────────

    def _nb(self, pieces: dict, *keys) -> int:
        for key in keys:
            v = pieces.get(key, None)
            if v is None:
                continue
            if isinstance(v, bool):
                return int(v)
            try:
                return max(0, int(v))
            except (TypeError, ValueError):
                continue
        return 0

    def _build_construction(self, surf: dict, pieces: dict) -> dict:
        p = {}
        surf_hab     = surf["surface_habitable"]
        surf_jardin  = surf["surface_jardin"]
        surf_piscine = surf["surface_piscine"]
        has_jardin   = surf["has_jardin"]
        has_piscine  = surf["has_piscine"]

        nb_ch  = self._nb(pieces, "chambres", "chambre")
        nb_sal = self._nb(pieces, "salons", "salon") or 1
        nb_sdb = self._nb(pieces, "salle_de_bain", "salles_de_bain") or 1
        nb_wc  = self._nb(pieces, "wc") or 1
        nb_cui = self._nb(pieces, "cuisines", "cuisine") or 1

        nb_fen  = nb_ch + nb_cui + nb_sdb     # 1 fenêtre par chambre/cuisine/SDB
        nb_pf   = nb_sal                       # 1 porte-fenêtre par salon
        nb_pi   = nb_ch + nb_sal + nb_cui + nb_sdb + nb_wc  # 1 porte par pièce
        nb_clim = max(1, nb_ch) + 1

        # ── 1. Gros œuvre ──────────────────────────────────────────────────────
        r = self.best(
            ["construction", "maison", "agrandissement"],
            categories=["construction"],
            price_min_filter=5000  # On veut le prix par 100m², pas le prix au m²
        )
        if r:
            coeff = max(1.0, round(surf_hab / 100, 1))
            p["gros_oeuvre"] = {
                "description": "Gros œuvre — fondations, murs, dalle, charpente",
                "quantite":    coeff,
                "unite":       "tranches 100m²",
                "prix_min_u":  r["min"],
                "prix_mid_u":  r["mid"],
                "prix_max_u":  r["max"],
                "cout_min":    round(coeff * r["min"]),
                "cout_mid":    round(coeff * r["mid"]),
                "cout_max":    round(coeff * r["max"]),
                "fourchette":  f"{_fmt(r['min'])} – {_fmt(r['max'])} DT/tranche",
                "source":      r["titre"],
            }

        # ── 2. Carrelage sol ───────────────────────────────────────────────────
        r = self.best(
            ["carrelage", "sol", "grès", "cérame", "pose"],
            categories=["carrelage"],
            price_max_filter=200  # prix au m²
        )
        if r:
            p["carrelage_sol"] = self._poste(
                f"Carrelage sol — fourniture + pose ({surf_hab:.0f} m²)",
                surf_hab, "m²", r)

        # ── 3. Faïence murale ──────────────────────────────────────────────────
        surf_faience = (nb_sdb * 10) + 8  # 10m² par SDB + 8m² cuisine
        r = self.best(
            ["faïence", "murale", "salle", "bain", "cuisine"],
            categories=["carrelage"],
            price_max_filter=200
        )
        if r:
            p["faience"] = self._poste(
                f"Faïence murale — {nb_sdb} SDB + cuisine ({surf_faience} m²)",
                surf_faience, "m²", r)

        # ── 4. Peinture ────────────────────────────────────────────────────────
        r = self.best(
            ["peinture", "intérieure", "murs", "plafonds", "finitions"],
            categories=["peinture"],
            price_min_filter=500  # forfait, pas le prix au m²
        )
        if r:
            p["peinture"] = self._poste_ff("Peinture intérieure — murs + plafonds (forfait)", r)

        # ── 5. Électricité ─────────────────────────────────────────────────────
        r = self.best(
            ["installation", "électrique", "complète", "maison", "tableau"],
            categories=["electricite"],
        )
        if r:
            p["electricite"] = self._poste_ff("Installation électrique complète (forfait)", r)

        # ── 6. Plomberie ───────────────────────────────────────────────────────
        r = self.best(
            ["plomberie", "réseau", "multicouche", "installation"],
            categories=["plomberie"],
            price_min_filter=500  # réseau complet, pas prix/point d'eau
        )
        if r:
            p["plomberie"] = self._poste_ff("Plomberie complète — SDB, cuisine, WC (forfait)", r)

        # ── 7. Fenêtres ────────────────────────────────────────────────────────
        if nb_fen > 0:
            r = self.best(
                ["fenêtre", "pvc", "aluminium", "double", "vitrage"],
                categories=["menuiserie"],
            )
            if r:
                p["fenetre"] = self._poste(
                    f"Fenêtres PVC/Aluminium — {nb_fen} unités",
                    nb_fen, "unité", r)

        # ── 8. Portes-fenêtres ─────────────────────────────────────────────────
        if nb_pf > 0:
            r = self.best(
                ["porte-fenêtre", "aluminium", "coulissante", "salon"],
                categories=["menuiserie"],
            )
            if r:
                p["porte_fenetre"] = self._poste(
                    f"Porte-fenêtre aluminium salon — {nb_pf} unité",
                    nb_pf, "unité", r)

        # ── 9. Porte blindée ───────────────────────────────────────────────────
        r = self.best(
            ["porte", "blindée", "entrée", "sécurité"],
            categories=["menuiserie"],
        )
        if r:
            p["porte_blindee"] = self._poste(
                "Porte blindée extérieure — entrée principale", 1, "unité", r)

        # ── 10. Portes intérieures ─────────────────────────────────────────────
        if nb_pi > 0:
            r = self.best(
                ["porte", "intérieure", "bois", "chambre"],
                categories=["menuiserie"],
            )
            if r:
                p["porte_interieure"] = self._poste(
                    f"Portes intérieures — {nb_pi} unités", nb_pi, "unité", r)

        # ── 11. Cuisine équipée ────────────────────────────────────────────────
        r = self.best(
            ["cuisine", "équipée", "meubles", "plan", "travail"],
            categories=["estimation_construction"],
            price_min_filter=2000
        )
        if r:
            p["cuisine_equipee"] = self._poste_ff(
                "Cuisine équipée — meubles + plan de travail", r)

        # ── 12. Salle de bain ──────────────────────────────────────────────────
        if nb_sdb > 0:
            r = self.best(
                ["salle", "bain", "douche", "lavabo", "wc", "carrelage"],
                categories=["estimation_construction"],
                price_min_filter=2000
            )
            if r:
                label = (f"Salle de bain complète — {nb_sdb} SDB"
                         if nb_sdb > 1 else "Salle de bain complète")
                p["salle_de_bain"] = self._poste(label, nb_sdb, "unité", r)

        # ── 13. Chauffe-eau ────────────────────────────────────────────────────
        r = self.best(
            ["chauffe-eau", "électrique", "ballon", "cumulus"],
            categories=["estimation_construction"],
        )
        if r:
            p["chauffe_eau"] = self._poste_ff("Chauffe-eau électrique", r)

        # ── 14. Climatisation ──────────────────────────────────────────────────
        r = self.best(
            ["climatiseur", "split", "inverter", "installation"],
            categories=["climatisation"],
            price_max_filter=2000  # prix par unité
        )
        if r:
            p["climatisation"] = self._poste(
                f"Climatisation split — {nb_clim} unités", nb_clim, "unité", r)

        # ── 15. Dressing ───────────────────────────────────────────────────────
        if nb_ch > 0:
            r = self.best(
                ["placard", "dressing", "chambre", "mélaminé"],
                categories=["dressing"],
            )
            if r:
                surf_dressing = nb_ch * 4
                p["dressing"] = self._poste(
                    f"Dressing/placards — {nb_ch} chambres ({surf_dressing} m²)",
                    surf_dressing, "m²", r)

        # ── 16. Raccordement eau ───────────────────────────────────────────────
        r = self.best(
            ["raccordement", "eau", "potable", "sonede", "branchement"],
            categories=["estimation_construction"],
            price_max_filter=1000
        )
        if r:
            p["raccord_eau"] = self._poste_ff("Raccordement eau potable SONEDE", r)

        # ── 17. Raccordement gaz ───────────────────────────────────────────────
        r = self.best(
            ["raccordement", "gaz", "steg", "compteur"],
            categories=["estimation_construction"],
        )
        if r:
            p["raccord_gaz"] = self._poste_ff("Raccordement gaz STEG", r)

        # ── 18. Raccordement électricité ───────────────────────────────────────
        r = self.best(
            ["raccordement", "électricité", "steg", "basse", "tension"],
            categories=["estimation_construction"],
            price_min_filter=500
        )
        if r:
            p["raccord_elec"] = self._poste_ff("Raccordement électricité STEG", r)

        # ── 19. Télésurveillance ───────────────────────────────────────────────
        r = self.best(
            ["télésurveillance", "alarme", "abonnement"],
            categories=["estimation_construction"],
            price_max_filter=500  # prix mensuel
        )
        if r:
            r12 = {**r, "min": r["min"] * 12, "mid": r["mid"] * 12, "max": r["max"] * 12}
            p["securite"] = self._poste_ff("Télésurveillance (12 mois)", r12)

        # ── 20. Jardin ─────────────────────────────────────────────────────────
        if has_jardin and surf_jardin > 0:
            r = self.best(
                ["aménagement", "jardin", "gazon", "pelouse"],
                categories=["jardin"],
            )
            if r:
                p["jardin"] = self._poste(
                    f"Aménagement jardin — {surf_jardin:.0f} m²",
                    surf_jardin, "m²", r)

        # ── 21. Piscine ────────────────────────────────────────────────────────
        if has_piscine and surf_piscine > 0:
            r = self.best(
                ["piscine", "construction", "béton"],
                categories=["construction"],
                price_min_filter=20000
            )
            if r:
                p["piscine"] = self._poste_ff(
                    f"Piscine construction — {surf_piscine:.0f} m²", r)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # DEVIS RÉNOVATION
    # ──────────────────────────────────────────────────────────────────────────

    def _build_renovation(self, surf: dict, pieces: dict) -> dict:
        p        = {}
        surf_hab = surf["surface_habitable"]
        nb_ch    = self._nb(pieces, "chambres", "chambre")
        nb_sdb   = self._nb(pieces, "salle_de_bain", "salles_de_bain") or 1
        nb_clim  = max(1, nb_ch) + 1
        nb_fen   = nb_ch + 2

        r = self.best(["peinture", "intérieure", "murs", "finitions"],
                      categories=["peinture"], price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture rénovation (forfait)", r)

        r = self.best(["carrelage", "sol", "remplacement"], categories=["carrelage"],
                      price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste(
                "Remplacement carrelage sol", surf_hab, "m²", r)

        r = self.best(["faïence", "murale", "salle", "bain"], categories=["carrelage"],
                      price_max_filter=200)
        if r:
            surf_f = nb_sdb * 10 + 8
            p["faience"] = self._poste(
                "Remplacement faïence — SDB + cuisine", surf_f, "m²", r)

        r = self.best(["installation", "électrique", "tableau"],
                      categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Rénovation électrique", r)

        r = self.best(["plomberie", "réseau", "multicouche"], categories=["plomberie"],
                      price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Rénovation plomberie", r)

        r = self.best(["fenêtre", "pvc", "aluminium"], categories=["menuiserie"])
        if r:
            p["fenetres"] = self._poste(
                f"Remplacement fenêtres — {nb_fen} unités", nb_fen, "unité", r)

        r = self.best(["climatiseur", "split", "inverter"],
                      categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(
                f"Climatisation — {nb_clim} unités", nb_clim, "unité", r)

        r = self.best(["cuisine", "équipée", "meubles"],
                      categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["cuisine_equipee"] = self._poste_ff("Rénovation cuisine équipée", r)

        r = self.best(["salle", "bain", "douche", "lavabo"],
                      categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste_ff("Rénovation salle de bain complète", r)

        r = self.best(["faux", "plafond", "ba13"], categories=["renovation"])
        if r:
            p["faux_plafond"] = self._poste(
                f"Faux plafond — {surf_hab:.0f} m²", surf_hab, "m²", r)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # DEVIS CAFÉ / COMMERCE
    # ──────────────────────────────────────────────────────────────────────────

    def _build_cafe(self, surf: dict, pieces: dict) -> dict:
        p        = {}
        surf_hab = surf["surface_habitable"]
        nb_clim  = max(2, round(surf_hab / 25))

        r = self.best(["carrelage", "sol", "pose"], categories=["carrelage"],
                      price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste(
                "Carrelage sol commercial", surf_hab, "m²", r)

        r = self.best(["faïence", "murale"], categories=["carrelage"],
                      price_max_filter=200)
        if r:
            p["faience"] = self._poste_ff("Faïence murale déco", r)

        r = self.best(["peinture", "murs", "finitions"], categories=["peinture"],
                      price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture déco — murs + plafonds", r)

        r = self.best(["installation", "électrique", "tableau"],
                      categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Installation électrique commerce", r)

        r = self.best(["plomberie", "réseau"], categories=["plomberie"],
                      price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Plomberie bar/cuisine/WC", r)

        r = self.best(["climatiseur", "split"], categories=["climatisation"],
                      price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(
                f"Climatisation split — {nb_clim} unités", nb_clim, "unité", r)

        r = self.best(["porte-fenêtre", "aluminium"], categories=["menuiserie"])
        if r:
            p["menuiserie"] = self._poste(
                "Vitrine / porte commerce aluminium — 2 unités", 2, "unité", r)

        r = self.best(["cuisine", "équipée"], categories=["estimation_construction"],
                      price_min_filter=2000)
        if r:
            p["cuisine_equipee"] = self._poste_ff(
                "Équipement cuisine / bar professionnel", r)

        r = self.best(["salle", "bain", "douche", "wc"],
                      categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste_ff("Sanitaires WC / toilettes commerce", r)

        r = self.best(["raccordement", "eau", "sonede"],
                      categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste_ff("Raccordement eau SONEDE", r)

        r = self.best(["raccordement", "électricité", "steg"],
                      categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste_ff("Raccordement électricité STEG", r)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # FINALISATION
    # ──────────────────────────────────────────────────────────────────────────

    def _finalize(self, surf: dict, postes: dict) -> dict:
        if not postes:
            return {
                "resume":   self._resume(surf),
                "postes":   {},
                "total":    {"total_min": 0, "total_mid": 0, "total_max": 0,
                             "total_min_str": "0 DT", "total_mid_str": "0 DT",
                             "total_max_str": "0 DT"},
                "accuracy": {"score": 0, "qualite": "🔴 Aucun poste",
                             "postes_dataset": 0, "postes_total": 0,
                             "detail": "Dataset insuffisant."},
            }

        st_min = sum(v.get("cout_min") or 0 for v in postes.values())
        st_mid = sum(v.get("cout_mid") or 0 for v in postes.values())
        st_max = sum(v.get("cout_max") or 0 for v in postes.values())

        t_min = round(st_min * 1.10)
        t_mid = round(st_mid * 1.10)
        t_max = round(st_max * 1.10)

        total_postes   = len(postes)
        postes_dataset = sum(1 for v in postes.values()
                             if v.get("source", "") not in ("", "Dataset"))
        accuracy_pct   = round(postes_dataset / total_postes * 100) if total_postes else 0

        if accuracy_pct >= 80:
            qualite = "🟢 Excellente"
            note    = "La majorité des prix viennent directement du dataset."
        elif accuracy_pct >= 60:
            qualite = "🟡 Bonne"
            note    = "Plus de la moitié des postes sont issus du dataset."
        elif accuracy_pct >= 40:
            qualite = "🟠 Partielle"
            note    = "Une partie des postes n'avait pas de données dans le dataset."
        else:
            qualite = "🔴 Faible"
            note    = "Peu de postes couverts — enrichir le dataset est recommandé."

        return {
            "resume": self._resume(surf),
            "postes": postes,
            "total": {
                "total_min":     t_min,
                "total_mid":     t_mid,
                "total_max":     t_max,
                "total_min_str": _fmt_dt(t_min),
                "total_mid_str": _fmt_dt(t_mid),
                "total_max_str": _fmt_dt(t_max),
            },
            "accuracy": {
                "score":          accuracy_pct,
                "qualite":        qualite,
                "postes_dataset": postes_dataset,
                "postes_total":   total_postes,
                "detail":         note,
            },
        }

    def _resume(self, surf: dict) -> dict:
        r = {
            "terrain":           f"{surf['terrain_total']:.0f} m²",
            "surface_habitable": f"{surf['surface_habitable']:.0f} m²",
            "surface_jardin":    f"{surf['surface_jardin']:.0f} m²",
            "surface_allee":     f"{surf['surface_allee']:.0f} m²",
        }
        if surf.get("surface_piscine", 0) > 0:
            r["surface_piscine"] = f"{surf['surface_piscine']:.0f} m²"
        return r