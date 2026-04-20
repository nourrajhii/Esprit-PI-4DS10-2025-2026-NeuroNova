"""
price_predictor.py — Modèle ML de prédiction du total devis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Modèle : GradientBoosting (principal) + Ridge (ensemble 30%)
Blend  : total_final = (1-α)×règles_RAG + α×prédiction_ML
         α=0.35 par défaut (35% ML, 65% règles)

Utilisation :
  predictor = DevisPredictor(blend_alpha=0.35)
  predictor.train(historique_df)   # ou bootstrap synthétique
  devis_ajusté = predictor.adjust_devis(devis, surfaces, pieces, type_projet)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score


# ── Encodages catégoriels ────────────────────────────────────────────────────

TYPE_ENCODING = {
    "construction":        1,
    "villa":               2,
    "appartement":         3,
    "renovation":          4,
    "cafe_commerce":       5,
    "mixte_cafe_appart":   6,
    "mixte_maison_appart": 7,
    "hotel":               8,
    "foyer":               9,
    "centre_esthetique":   10,
    "salle_sport":         11,
    "clinique":            12,
    "bureau":              13,
    "salle_fetes":         14,
    "entrepot":            15,
}

QUALITE_ENCODING = {"economique": 0, "standard": 1, "premium": 2}

FEATURE_NAMES = [
    "terrain_m2", "surface_habitable", "surface_plancher", "nombre_etages",
    "nb_chambres", "nb_salons", "nb_cuisines", "nb_sdb",
    "has_jardin", "has_piscine", "has_dressing",
    "type_projet_enc", "qualite_enc",
    "total_mid_rules",
    "ratio_densite",
]


def _encode_type(t: str) -> int:
    return TYPE_ENCODING.get(str(t).lower(), 1)


def _encode_qualite(q: str) -> int:
    return QUALITE_ENCODING.get(str(q).lower(), 1)


def extract_features(
    surfaces: dict,
    pieces: dict,
    devis_total: dict,
    type_projet: str = "construction",
    qualite: str = "standard",
) -> np.ndarray:
    """Transforme les dicts du calculateur en vecteur numpy (1, 15)."""
    terrain       = float(surfaces.get("terrain_total", 0))
    surf_hab      = float(surfaces.get("surface_habitable", 0))
    surf_plancher = float(surfaces.get("surface_plancher", surf_hab))
    nb_etages     = float(surfaces.get("nombre_etages", 1))
    surf_jardin   = float(surfaces.get("surface_jardin", 0))
    surf_piscine  = float(surfaces.get("surface_piscine", 0))

    nb_ch  = float(pieces.get("chambres", 0) or 0)
    nb_sl  = float(pieces.get("salons", 0) or 0)
    nb_cu  = float(pieces.get("cuisines", 0) or 0)
    nb_sdb = float(pieces.get("salles_de_bain", 0) or pieces.get("salle_de_bain", 0) or 0)

    has_jardin   = 1.0 if (pieces.get("jardin") or surf_jardin > 0) else 0.0
    has_piscine  = 1.0 if (pieces.get("piscine") or surf_piscine > 0) else 0.0
    has_dressing = 1.0 if pieces.get("dressing") else 0.0

    type_enc    = float(_encode_type(type_projet))
    qualite_enc = float(_encode_qualite(qualite))
    total_mid   = float(devis_total.get("total_mid", 0))

    return np.array([[
        terrain, surf_hab, surf_plancher, nb_etages,
        nb_ch, nb_sl, nb_cu, nb_sdb,
        has_jardin, has_piscine, has_dressing,
        type_enc, qualite_enc,
        total_mid,
        surf_plancher / max(terrain, 1),
    ]])


class DevisPredictor:
    """
    Modèle ML qui affine le total calculé par les règles RAG.

    Paramètres
    ----------
    blend_alpha : float
        Poids donné à la prédiction ML (0=règles pures, 1=ML pur).
        Recommandé : 0.20 au départ, 0.35 après ~50 vrais devis.
    """

    MODEL_PATH = Path("./models/devis_predictor.pkl")

    def __init__(self, blend_alpha: float = 0.35):
        self.blend_alpha   = blend_alpha
        self._gb_mid: Optional[Pipeline] = None
        self._gb_min: Optional[Pipeline] = None
        self._gb_max: Optional[Pipeline] = None
        self._ridge_mid: Optional[Pipeline] = None
        self.is_trained    = False
        self.train_score   = None
        self.n_samples     = 0

    # ── Construction des pipelines ────────────────────────────────────────────

    @staticmethod
    def _make_gb() -> Pipeline:
        return Pipeline([
            ("scaler", StandardScaler()),
            ("gb", GradientBoostingRegressor(
                n_estimators=200, learning_rate=0.08,
                max_depth=4, subsample=0.85,
                min_samples_leaf=2, random_state=42,
            )),
        ])

    @staticmethod
    def _make_ridge() -> Pipeline:
        return Pipeline([
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=1.0)),
        ])

    # ── Entraînement ─────────────────────────────────────────────────────────

    def train(self, historique, cv: int = 3):
        """
        Entraîne sur un historique de devis réels.

        Colonnes attendues dans le DataFrame / liste de dicts :
          terrain_m2, surface_habitable, surface_plancher, nombre_etages,
          nb_chambres, nb_salons, nb_cuisines, nb_sdb,
          has_jardin, has_piscine, has_dressing,
          type_projet_enc, qualite_enc, total_mid_rules, ratio_densite,
          reel_total_min, reel_total_mid, reel_total_max   ← cibles
        """
        df = pd.DataFrame(historique) if isinstance(historique, list) else historique.copy()

        if len(df) < 5:
            print(f"⚠️  Historique trop petit ({len(df)} échantillons) — entraînement ignoré.")
            return

        X     = df[FEATURE_NAMES].values.astype(float)
        y_mid = df["reel_total_mid"].values.astype(float)
        y_min = df["reel_total_min"].values.astype(float)
        y_max = df["reel_total_max"].values.astype(float)

        self._gb_mid    = self._make_gb().fit(X, y_mid)
        self._gb_min    = self._make_gb().fit(X, y_min)
        self._gb_max    = self._make_gb().fit(X, y_max)
        self._ridge_mid = self._make_ridge().fit(X, y_mid)

        cv_actual = min(cv, len(df))
        if cv_actual >= 2:
            scores = cross_val_score(self._make_gb(), X, y_mid, cv=cv_actual, scoring="r2")
            self.train_score = round(float(scores.mean()), 3)

        self.is_trained = True
        self.n_samples  = len(df)
        print(f"✅ Predictor ML entraîné — {self.n_samples} devis | R²={self.train_score}")

    # ── Prédiction ────────────────────────────────────────────────────────────

    def predict(
        self,
        surfaces: dict,
        pieces: dict,
        devis_total: dict,
        type_projet: str = "construction",
        qualite: str = "standard",
    ) -> dict:
        """Retourne les totaux prédits (min / mid / max) avec métadonnées."""
        if not self.is_trained:
            raise RuntimeError("Modèle non entraîné. Appelez .train() d'abord.")

        X = extract_features(surfaces, pieces, devis_total, type_projet, qualite)

        pred_mid_gb    = float(self._gb_mid.predict(X)[0])
        pred_mid_ridge = float(self._ridge_mid.predict(X)[0])
        pred_mid = round(pred_mid_gb * 0.70 + pred_mid_ridge * 0.30)
        pred_min = round(float(self._gb_min.predict(X)[0]))
        pred_max = round(float(self._gb_max.predict(X)[0]))

        pred_min = min(pred_min, pred_mid)
        pred_max = max(pred_max, pred_mid)

        r2 = self.train_score
        confidence = "haute" if (r2 and r2 >= 0.80) else ("moyenne" if (r2 and r2 >= 0.60) else "faible")

        return {
            "pred_min":   pred_min,
            "pred_mid":   pred_mid,
            "pred_max":   pred_max,
            "confidence": confidence,
            "r2_score":   r2,
            "n_train":    self.n_samples,
        }

    # ── Ajustement devis ──────────────────────────────────────────────────────

    def adjust_devis(
        self,
        devis: dict,
        surfaces: dict,
        pieces: dict,
        type_projet: str = "construction",
        qualite: str = "standard",
    ) -> dict:
        """
        Blend la prédiction ML avec les totaux calculés par les règles.
        Retourne une copie du devis avec les totaux ajustés et un bloc
        'prediction' contenant les détails ML.
        """
        if not self.is_trained:
            return devis

        import copy
        devis_out = copy.deepcopy(devis)

        total_rules = devis_out.get("total", {})
        t_min_r = float(total_rules.get("total_min", 0))
        t_mid_r = float(total_rules.get("total_mid", 0))
        t_max_r = float(total_rules.get("total_max", 0))

        pred  = self.predict(surfaces, pieces, total_rules, type_projet, qualite)
        alpha = self.blend_alpha

        adj_min = round((1 - alpha) * t_min_r + alpha * pred["pred_min"])
        adj_mid = round((1 - alpha) * t_mid_r + alpha * pred["pred_mid"])
        adj_max = round((1 - alpha) * t_max_r + alpha * pred["pred_max"])

        adj_min = min(adj_min, adj_mid)
        adj_max = max(adj_max, adj_mid)

        def _fmt_dt(v: float) -> str:
            return f"{int(round(float(v))):,}".replace(",", "\u202f") + " DT"

        devis_out["total"].update({
            "total_min":     adj_min,
            "total_mid":     adj_mid,
            "total_max":     adj_max,
            "total_min_str": _fmt_dt(adj_min),
            "total_mid_str": _fmt_dt(adj_mid),
            "total_max_str": _fmt_dt(adj_max),
        })

        devis_out["prediction"] = {
            "ml_min":      pred["pred_min"],
            "ml_mid":      pred["pred_mid"],
            "ml_max":      pred["pred_max"],
            "rules_min":   int(t_min_r),
            "rules_mid":   int(t_mid_r),
            "rules_max":   int(t_max_r),
            "blend_alpha": alpha,
            "confidence":  pred["confidence"],
            "r2_score":    pred["r2_score"],
            "n_train":     pred["n_train"],
            "model":       "GradientBoosting + Ridge (ensemble)",
        }

        return devis_out

    # ── Persistance ──────────────────────────────────────────────────────────

    def save(self, path=None):
        if not self.is_trained:
            raise RuntimeError("Rien à sauvegarder — modèle non entraîné.")
        p = Path(path or self.MODEL_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            pickle.dump(self, f, protocol=5)
        print(f"💾 Predictor sauvegardé → {p}")

    @classmethod
    def load(cls, path=None) -> "DevisPredictor":
        p = Path(path or cls.MODEL_PATH)
        if not p.exists():
            raise FileNotFoundError(f"Modèle introuvable : {p}")
        with open(p, "rb") as f:
            obj = pickle.load(f)
        print(f"📦 Predictor chargé — n={obj.n_samples}, R²={obj.train_score}")
        return obj

    # ── Données synthétiques (bootstrap) ─────────────────────────────────────

    @staticmethod
    def generate_synthetic_history(n: int = 200, seed: int = 42) -> pd.DataFrame:
        """
        Génère un jeu d'entraînement synthétique.
        À remplacer progressivement par de vrais devis réels.
        """
        rng = np.random.default_rng(seed)

        COST_M2 = {
            1: 750, 2: 900, 3: 680, 4: 400, 5: 850,
            6: 820, 7: 780, 8: 950, 9: 650, 10: 700,
            11: 600, 12: 1000, 13: 720, 14: 650, 15: 380,
        }
        QUALITE_FACTOR = {0: 0.80, 1: 1.00, 2: 1.30}

        records = []
        for _ in range(n):
            terrain     = int(rng.integers(150, 1200))
            nb_etages   = int(rng.choice([1, 2, 3], p=[0.55, 0.30, 0.15]))
            type_enc    = int(rng.choice(list(COST_M2.keys())))
            qualite_enc = int(rng.choice([0, 1, 2], p=[0.20, 0.60, 0.20]))

            emprise       = int(round(terrain * rng.uniform(0.45, 0.65)))
            surf_plancher = emprise * nb_etages
            surf_hab      = int(round(surf_plancher * 0.85))
            nb_ch         = int(rng.integers(1, 6))
            nb_sl         = int(rng.integers(1, 3))
            nb_cu         = int(rng.integers(1, nb_sl + 1))
            nb_sdb        = int(rng.integers(1, nb_ch + 1))
            has_jardin    = int(rng.random() < 0.40)
            has_piscine   = int(rng.random() < 0.10)
            has_dressing  = int(rng.random() < 0.25)
            ratio         = surf_plancher / max(terrain, 1)

            cost_m2        = COST_M2[type_enc] * QUALITE_FACTOR[qualite_enc]
            base           = surf_plancher * cost_m2
            extras         = has_jardin * 12_000 + has_piscine * 45_000 + has_dressing * 5_000
            total_mid_rules = int(round(base + extras))

            noise    = float(rng.normal(1.0, 0.12))
            reel_mid = int(round(total_mid_rules * noise))
            reel_min = int(round(reel_mid * rng.uniform(0.80, 0.92)))
            reel_max = int(round(reel_mid * rng.uniform(1.08, 1.25)))

            records.append({
                "terrain_m2":        terrain,
                "surface_habitable": surf_hab,
                "surface_plancher":  surf_plancher,
                "nombre_etages":     nb_etages,
                "nb_chambres":       nb_ch,
                "nb_salons":         nb_sl,
                "nb_cuisines":       nb_cu,
                "nb_sdb":            nb_sdb,
                "has_jardin":        has_jardin,
                "has_piscine":       has_piscine,
                "has_dressing":      has_dressing,
                "type_projet_enc":   type_enc,
                "qualite_enc":       qualite_enc,
                "total_mid_rules":   total_mid_rules,
                "ratio_densite":     ratio,
                "reel_total_min":    reel_min,
                "reel_total_mid":    reel_mid,
                "reel_total_max":    reel_max,
            })

        return pd.DataFrame(records)