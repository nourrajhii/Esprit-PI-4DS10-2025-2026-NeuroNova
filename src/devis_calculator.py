"""
DevisCalculator v9.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nouveautés v9.0 :
  - Gestion des étages : surface_habitable × nombre_etages
  - Poste "escalier" ajouté automatiquement si nb_etages > 1
    (prix par volée d'escalier, forfait pour structures métalliques/béton)
  - Nouveaux types de projets commerciaux :
      hotel, foyer, centre_esthetique, salle_sport, clinique, bureau,
      salle_fetes, entrepot
  - estimate_surfaces() accepte nombre_etages en paramètre
  - build_devis() dispatch sur les nouveaux types
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


from .devis_calculator_builders import DevisCalculatorBuilders


class DevisCalculator(DevisCalculatorBuilders):

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
            if isinstance(val, float) and (val != val):
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

        df["titre"] = df.apply(
            lambda r: r["titre_raw"] if r["titre_raw"] else r["categorie"].capitalize(),
            axis=1
        )
        df["titre_lower"] = df["titre"].str.lower()

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
        if self._df is None or self._df.empty:
            return []

        df = self._df.copy()

        if categories:
            cats = [c.lower() for c in categories]
            df_cat = df[df["categorie"].isin(cats)]
            df = df_cat if not df_cat.empty else df

        if price_min_filter is not None:
            df = df[df["prix"] >= price_min_filter]
        if price_max_filter is not None:
            df = df[df["prix"] <= price_max_filter]

        if df.empty:
            return []

        kws_lower = [k.lower() for k in keywords]
        df = df.copy()
        df["_score"] = df["titre_lower"].apply(
            lambda titre: sum(1 for kw in kws_lower if kw in titre)
        )
        if categories:
            cats = [c.lower() for c in categories]
            df["_score"] += df["categorie"].apply(
                lambda c: 1 if c in cats else 0
            )

        df = df[df["_score"] > 0].sort_values("_score", ascending=False)

        if df.empty:
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
    # POSTE ESCALIER (helper réutilisable)
    # ──────────────────────────────────────────────────────────────────────────

    def _add_escalier(self, postes: dict, nombre_etages: int,
                      type_projet: str = "construction"):
        """
        Ajoute le(s) poste(s) escalier si nombre_etages > 1.
        - nb_volées = nombre_etages - 1  (une volée entre chaque paire de niveaux)
        - Hôtels/ERP ≥ 3 niveaux : double cage d'escalier (obligation réglementaire)
        - Fallback forfait si absent du dataset.
        """
        nb_volees = nombre_etages - 1   # volées par cage

        # Double cage obligatoire pour hôtel/ERP avec ≥ 3 niveaux
        nb_cages = 2 if (type_projet in ("hotel", "foyer", "clinique", "bureau",
                                          "salle_fetes") and nombre_etages >= 3) else 1

        r = self.best(
            ["escalier", "béton", "marche", "volée"],
            categories=["construction"],
        ) or self.best(
            ["escalier", "marches", "structure"],
            categories=["menuiserie"],
        )

        nb_total_volees = nb_volees * nb_cages
        cage_label = f"{nb_cages} cage{'s' if nb_cages > 1 else ''} × {nb_volees} volée{'s' if nb_volees > 1 else ''}"

        # Prix plancher réaliste : une volée d'escalier béton en Tunisie = 1 000–3 000 DT
        PRIX_MIN_REALISTE = 1_000   # DT/volée
        PRIX_MID_REALISTE = 1_800
        PRIX_MAX_REALISTE = 3_000

        # Si dataset retourne un prix trop bas (marche/m² au lieu de volée), forcer forfait
        use_dataset = r and r.get("mid", 0) >= 800

        if use_dataset:
            postes["escalier"] = self._poste(
                f"Escalier(s) béton/marbre — {cage_label} ({nb_total_volees} volées total)",
                nb_total_volees, "volée", r,
            )
        else:
            postes["escalier"] = {
                "description": f"Escalier(s) béton/marbre — {cage_label} ({nb_total_volees} volées total)",
                "quantite":    nb_total_volees,
                "unite":       "volée",
                "prix_min_u":  PRIX_MIN_REALISTE,
                "prix_mid_u":  PRIX_MID_REALISTE,
                "prix_max_u":  PRIX_MAX_REALISTE,
                "cout_min":    round(nb_total_volees * PRIX_MIN_REALISTE),
                "cout_mid":    round(nb_total_volees * PRIX_MID_REALISTE),
                "cout_max":    round(nb_total_volees * PRIX_MAX_REALISTE),
                "fourchette":  f"{PRIX_MIN_REALISTE:,} – {PRIX_MAX_REALISTE:,} DT/volée".replace(",", " "),
                "source":      "Prix marché tunisien 2025",
            }

    # ──────────────────────────────────────────────────────────────────────────
    # SURFACES — accepte nombre_etages
    # ──────────────────────────────────────────────────────────────────────────

    def estimate_surfaces(self, terrain_m2: float, pieces: dict,
                          nombre_etages: int = 1) -> dict:
        """
        Calcule les surfaces du projet.

        Règles surfaces extérieures :
          parking  = 10% du terrain (20% si ≥3 niveaux)
          jardin   = 0% si non demandé
                   = 10% si jardin + terrain < 200 m²
                   = 20% si jardin + terrain ≥ 200 m²
          piscine  = 20% piscine + 20% jardin (forcé si piscine)
          emprise  = terrain - parking - jardin - piscine
          plafond  = 60% résidentiel, 65% commerce, 70% entrepôt/industriel
        """
        has_jardin    = bool(pieces.get("jardin",  False))
        has_piscine   = bool(pieces.get("piscine", False))
        nombre_etages = max(1, int(nombre_etages or 1))
        type_projet   = pieces.get("_type_projet", "construction")

        # ── Parking / allée ───────────────────────────────────────────────────
        # Surface fixe réaliste selon taille terrain, pas un ratio aveugle.
        if terrain_m2 <= 150:
            surf_parking = round(terrain_m2 * 0.05, 1)   # 5% petit terrain
        elif terrain_m2 <= 300:
            surf_parking = round(terrain_m2 * 0.08, 1)   # 8% terrain moyen
        elif nombre_etages >= 3:
            surf_parking = round(terrain_m2 * 0.15, 1)   # 15% grand projet multi-niveaux
        else:
            surf_parking = round(terrain_m2 * 0.10, 1)   # 10% standard

        # ── Jardin / Piscine ──────────────────────────────────────────────────
        # Jardin = 0 si non explicitement demandé par l'utilisateur
        if has_piscine:
            surf_piscine = round(terrain_m2 * 0.20, 1)
            surf_jardin  = round(terrain_m2 * 0.15, 1)
        elif has_jardin:
            surf_piscine = 0.0
            surf_jardin  = round(terrain_m2 * (0.15 if terrain_m2 < 300 else 0.20), 1)
        else:
            surf_piscine = 0.0
            surf_jardin  = 0.0   # PAS de jardin si non demandé

        # ── Emprise bâtiment ──────────────────────────────────────────────────
        exterieur    = surf_parking + surf_jardin + surf_piscine
        emprise_brut = round(terrain_m2 - exterieur, 1)

        # Plafond COS selon type de projet
        if type_projet in ("entrepot", "salle_sport", "salle_fetes"):
            max_ratio = 0.70
        elif type_projet in ("cafe_commerce", "mixte_cafe_appart"):
            max_ratio = 0.65
        elif type_projet in ("hotel", "foyer", "bureau", "clinique",
                             "mixte_maison_appart"):
            max_ratio = 0.60
        else:
            max_ratio = 0.60

        emprise_sol = round(min(emprise_brut, terrain_m2 * max_ratio), 1)
        emprise_sol = max(emprise_sol, 20.0)

        # Surface plancher totale (SHON) = emprise × étages
        surf_plancher_total = round(emprise_sol * nombre_etages, 1)

        # Coefficient d'utilisation (circulations, murs, gaines = ~15%)
        surf_utile = round(surf_plancher_total * 0.85, 1)

        cote = math.sqrt(emprise_sol) * 1.2
        return {
            "terrain_total":        terrain_m2,
            "emprise_sol":          emprise_sol,
            "surface_plancher":     surf_plancher_total,   # SHON totale tous niveaux
            "surface_habitable":    surf_utile,            # surface utile (sans circulations)
            "surface_par_etage":    emprise_sol,           # surface d'un seul niveau
            "nombre_etages":        nombre_etages,
            "surface_jardin":       surf_jardin,
            "surface_piscine":      surf_piscine,
            "surface_allee":        surf_parking,
            "surface_murs":         round(cote * 4 * 2.8 * nombre_etages, 1),
            "surface_plafond":      surf_plancher_total,
            "surface_toiture":      round(emprise_sol * 1.15, 1),
            "has_jardin":           has_jardin,
            "has_piscine":          has_piscine,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # DISPATCH
    # ──────────────────────────────────────────────────────────────────────────

    def build_devis(self, surfaces: dict, rag_prices: dict,
                    pieces: dict = None) -> dict:
        mode   = rag_prices.get("_meta", {}).get("mode", "construction")
        pieces = pieces or {}
        nombre_etages = surfaces.get("nombre_etages", 1)

        if mode == "mixte_cafe_appart":
            return self._build_mixte_cafe_appart(surfaces, pieces, nombre_etages)
        elif mode == "mixte_maison_appart":
            return self._build_mixte_maison_appart(surfaces, pieces, nombre_etages)
        elif mode == "renovation":
            return self._build_renovation(surfaces, pieces)
        elif mode == "cafe_commerce":
            return self._build_cafe(surfaces, pieces, nombre_etages)
        elif mode == "hotel":
            return self._build_hotel(surfaces, pieces, nombre_etages)
        elif mode == "foyer":
            return self._build_foyer(surfaces, pieces, nombre_etages)
        elif mode == "centre_esthetique":
            return self._build_centre_esthetique(surfaces, pieces, nombre_etages)
        elif mode == "salle_sport":
            return self._build_salle_sport(surfaces, pieces, nombre_etages)
        elif mode == "clinique":
            return self._build_clinique(surfaces, pieces, nombre_etages)
        elif mode == "bureau":
            return self._build_bureau(surfaces, pieces, nombre_etages)
        elif mode == "salle_fetes":
            return self._build_salle_fetes(surfaces, pieces, nombre_etages)
        elif mode == "entrepot":
            return self._build_entrepot(surfaces, pieces, nombre_etages)
        else:
            return self._build_construction(surfaces, pieces, nombre_etages)

    # ──────────────────────────────────────────────────────────────────────────
    # HELPER INTERNE
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
                             if v.get("source", "") not in ("", "Dataset",
                                                             "Estimation forfaitaire"))
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
        nb_et = surf.get("nombre_etages", 1)
        r = {
            "terrain":           f"{surf['terrain_total']:.0f} m²",
            "surface_plancher":  f"{surf.get('surface_plancher', surf.get('surface_habitable', 0)):.0f} m²",
            "surface_habitable": f"{surf['surface_habitable']:.0f} m²",
            "surface_jardin":    f"{surf['surface_jardin']:.0f} m²",
            "surface_allee":     f"{surf['surface_allee']:.0f} m²",
        }
        if nb_et > 1:
            r["emprise_sol"]     = f"{surf.get('emprise_sol', 0):.0f} m²"
            r["surface_par_etage"] = f"{surf.get('surface_par_etage', surf.get('emprise_sol', 0)):.0f} m²"
        if surf.get("surface_piscine", 0) > 0:
            r["surface_piscine"] = f"{surf['surface_piscine']:.0f} m²"
        return r