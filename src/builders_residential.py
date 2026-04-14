"""
builders_residential.py — Devis résidentiels
─────────────────────────────────────────────────────────────────────────────
Contient :
  _build_construction     — maison / villa / appartement plain-pied ou étages
  _build_renovation       — rénovation complète
  _build_mixte_maison_appart — maison RDC + appartements aux étages

Importé comme mixin par DevisCalculatorBuilders.
─────────────────────────────────────────────────────────────────────────────
"""

import math

SURF_PIECE = {
    "chambre": 14, "salon": 25, "cuisine": 12,
    "salle_de_bain": 6, "wc": 3, "couloir": 8, "entree": 5,
}


def _fmt(v: float) -> str:
    if v is None:
        return "0"
    try:
        f = float(v)
        return "0" if f != f else f"{int(round(f)):,}".replace(",", "\u202f")
    except Exception:
        return "0"


def _fmt_dt(v: float) -> str:
    return f"{_fmt(v)} DT"


class BuildersResidential:
    """Mixin — projets résidentiels."""

    # ──────────────────────────────────────────────────────────────────────────
    # CONSTRUCTION / VILLA / APPARTEMENT
    # ──────────────────────────────────────────────────────────────────────────

    def _build_construction(self, surf: dict, pieces: dict,
                            nombre_etages: int = 1) -> dict:
        p = {}
        surf_hab     = surf["surface_habitable"]
        surf_jardin  = surf["surface_jardin"]
        surf_piscine = surf["surface_piscine"]
        has_jardin   = surf["has_jardin"]
        has_piscine  = surf["has_piscine"]

        nb_ch  = self._nb(pieces, "chambres", "chambre")
        nb_sal = self._nb(pieces, "salons", "salon")
        nb_sdb = self._nb(pieces, "salle_de_bain", "salles_de_bain")
        nb_wc  = self._nb(pieces, "wc")
        nb_cui = self._nb(pieces, "cuisines", "cuisine")

        nb_sal = nb_sal or (1 if nb_ch > 0 else 0)
        nb_cui = nb_cui or 1
        nb_sdb = nb_sdb or 1
        nb_fen  = nb_ch + nb_sdb + nb_cui + nb_sal
        nb_pf   = nb_sal
        nb_pi   = nb_ch + nb_sdb + nb_cui + nb_sal + nb_wc
        nb_clim = max(1, nb_ch) + nb_sal
        nb_entrees = 1

        r = self.best(["construction", "maison", "agrandissement"],
                      categories=["construction"], price_min_filter=5000)
        if r:
            coeff = max(1.0, round(surf_hab / 100, 1))
            p["gros_oeuvre"] = {
                "description": "Gros œuvre — fondations, murs, dalle, charpente",
                "quantite": coeff, "unite": "tranches 100m²",
                "prix_min_u": r["min"], "prix_mid_u": r["mid"], "prix_max_u": r["max"],
                "cout_min": round(coeff * r["min"]),
                "cout_mid": round(coeff * r["mid"]),
                "cout_max": round(coeff * r["max"]),
                "fourchette": f"{_fmt(r['min'])} – {_fmt(r['max'])} DT/tranche",
                "source": r["titre"],
            }

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages)

        r = self.best(["carrelage", "sol", "grès", "cérame", "pose"],
                      categories=["carrelage"], price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste(
                f"Carrelage sol — fourniture + pose ({surf_hab:.0f} m²)",
                surf_hab, "m²", r)

        surf_faience = (nb_sdb * 10) + 8
        r = self.best(["faïence", "murale", "salle", "bain", "cuisine"],
                      categories=["carrelage"], price_max_filter=200)
        if r:
            p["faience"] = self._poste(
                f"Faïence murale — {nb_sdb} SDB + cuisine ({surf_faience} m²)",
                surf_faience, "m²", r)

        r = self.best(["peinture", "intérieure", "murs", "plafonds", "finitions"],
                      categories=["peinture"], price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture intérieure — murs + plafonds (forfait)", r)

        r = self.best(["installation", "électrique", "complète", "maison", "tableau"],
                      categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Installation électrique complète (forfait)", r)

        r = self.best(["plomberie", "réseau", "multicouche", "installation"],
                      categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Plomberie complète — SDB, cuisine, WC (forfait)", r)

        if nb_fen > 0:
            r = self.best(["fenêtre", "pvc", "aluminium", "double", "vitrage"],
                          categories=["menuiserie"])
            if r:
                p["fenetre"] = self._poste(
                    f"Fenêtres PVC/Aluminium — {nb_fen} unités", nb_fen, "unité", r)

        if nb_pf > 0:
            r = self.best(["porte-fenêtre", "aluminium", "coulissante", "salon"],
                          categories=["menuiserie"])
            if r:
                p["porte_fenetre"] = self._poste(
                    f"Porte-fenêtre aluminium salon — {nb_pf} unité", nb_pf, "unité", r)

        r = self.best(["porte", "blindée", "entrée", "sécurité"], categories=["menuiserie"])
        if r:
            p["porte_blindee"] = self._poste("Porte blindée extérieure — entrée principale", 1, "unité", r)

        if nb_pi > 0:
            r = self.best(["porte", "intérieure", "bois", "chambre"], categories=["menuiserie"])
            if r:
                p["porte_interieure"] = self._poste(
                    f"Portes intérieures — {nb_pi} unités", nb_pi, "unité", r)

        r = self.best(["cuisine", "équipée", "meubles", "plan", "travail"],
                      categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["cuisine_equipee"] = self._poste(
                "Cuisine équipée — meubles + plan de travail", max(1, nb_cui), "unité", r)

        if nb_sdb > 0:
            r = self.best(["salle", "bain", "douche", "lavabo", "wc", "carrelage"],
                          categories=["estimation_construction"], price_min_filter=2000)
            if r:
                label = (f"Salle de bain complète — {nb_sdb} SDB"
                         if nb_sdb > 1 else "Salle de bain complète")
                p["salle_de_bain"] = self._poste(label, nb_sdb, "unité", r)

        r = self.best(["chauffe-eau", "électrique", "ballon", "cumulus"],
                      categories=["estimation_construction"])
        if r:
            qty_chauffe_eau = max(1, nb_sdb if nb_sdb > 0 else nb_cui)
            p["chauffe_eau"] = self._poste(
                f"Chauffe-eau électrique — {qty_chauffe_eau} unités", qty_chauffe_eau, "unité", r)

        r = self.best(["climatiseur", "split", "inverter", "installation"],
                      categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(
                f"Climatisation split — {nb_clim} unités", nb_clim, "unité", r)

        if nb_ch > 0:
            r = self.best(["placard", "dressing", "chambre", "mélaminé"], categories=["dressing"])
            if r:
                surf_dressing = nb_ch * 5
                p["dressing"] = self._poste(
                    f"Dressing/placards — {nb_ch} chambres ({surf_dressing} m²)",
                    surf_dressing, "m²", r)

        r = self.best(["raccordement", "eau", "potable", "sonede", "branchement"],
                      categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste(
                f"Raccordement eau potable SONEDE — {nb_entrees} compteur{'s' if nb_entrees > 1 else ''}",
                nb_entrees, "forfait", r)

        r = self.best(["raccordement", "gaz", "steg", "compteur"],
                      categories=["estimation_construction"])
        if r:
            p["raccord_gaz"] = self._poste(
                f"Raccordement gaz STEG — {nb_entrees} compteur{'s' if nb_entrees > 1 else ''}",
                nb_entrees, "forfait", r)

        r = self.best(["raccordement", "électricité", "steg", "basse", "tension"],
                      categories=["estimation_construction"], price_min_filter=500)
        if r:
            p["raccord_elec"] = self._poste(
                f"Raccordement électricité STEG — {nb_entrees} compteur{'s' if nb_entrees > 1 else ''}",
                nb_entrees, "forfait", r)

        r = self.best(["télésurveillance", "alarme", "abonnement"],
                      categories=["estimation_construction"], price_max_filter=500)
        if r:
            r12 = {**r, "min": r["min"] * 12, "mid": r["mid"] * 12, "max": r["max"] * 12}
            p["securite"] = self._poste_ff("Télésurveillance (12 mois)", r12)

        if has_jardin and surf_jardin > 0:
            r = self.best(["aménagement", "jardin", "gazon", "pelouse"], categories=["jardin"])
            if r:
                p["jardin"] = self._poste(
                    f"Aménagement jardin — {surf_jardin:.0f} m²", surf_jardin, "m²", r)

        if has_piscine and surf_piscine > 0:
            r = self.best(["piscine", "construction", "béton"],
                          categories=["construction"], price_min_filter=20000)
            if r:
                p["piscine"] = self._poste_ff(f"Piscine construction — {surf_piscine:.0f} m²", r)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # RÉNOVATION
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
            p["carrelage_sol"] = self._poste("Remplacement carrelage sol", surf_hab, "m²", r)

        r = self.best(["faïence", "murale", "salle", "bain"], categories=["carrelage"],
                      price_max_filter=200)
        if r:
            surf_f = nb_sdb * 10 + 8
            p["faience"] = self._poste("Remplacement faïence — SDB + cuisine", surf_f, "m²", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
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
    # MIXTE : MAISON/LOGEMENT RDC + APPARTEMENTS AUX ÉTAGES
    # ──────────────────────────────────────────────────────────────────────────

    def _build_mixte_maison_appart(self, surf: dict, pieces: dict,
                                    nombre_etages: int = 1) -> dict:
        """
        Projet résidentiel multi-niveaux : chaque niveau = un logement indépendant.
        Les pièces sont déjà totalisées par l'agent NLP.
        """
        p = {}

        _nb_ap_stored = pieces.get("_nb_appartements")
        if _nb_ap_stored is not None:
            try:
                nb_appart = max(1, int(_nb_ap_stored))
            except (TypeError, ValueError):
                nb_appart = max(1, nombre_etages - 1)
        else:
            nb_appart = max(1, nombre_etages - 1)

        emprise_sol = surf.get("emprise_sol", surf["surface_habitable"] / max(1, nombre_etages))
        surf_rdc           = round(emprise_sol * 0.85)
        surf_par_ap        = round(emprise_sol * 0.85)
        surf_apparts_total = surf_par_ap * nb_appart
        surf_totale        = surf_rdc + surf_apparts_total

        # Pièces PAR appartement (telles que décrites dans le prompt)
        nb_ch_par_ap  = self._nb(pieces, "chambres", "chambre")
        nb_sal_par_ap = self._nb(pieces, "salons", "salon")
        nb_cui_par_ap = self._nb(pieces, "cuisines", "cuisine")
        nb_sdb_par_ap = self._nb(pieces, "salle_de_bain", "salles_de_bain")
        nb_wc_par_ap  = self._nb(pieces, "wc")

        # Valeurs minimales par appartement
        if nb_sal_par_ap == 0:
            nb_sal_par_ap = 1
        if nb_cui_par_ap == 0:
            nb_cui_par_ap = 1
        if nb_sdb_par_ap == 0:
            nb_sdb_par_ap = 1

        # Totaux pour TOUS les appartements
        nb_ch  = nb_ch_par_ap  * nb_appart
        nb_sal = nb_sal_par_ap * nb_appart
        nb_cui = nb_cui_par_ap * nb_appart
        nb_sdb = nb_sdb_par_ap * nb_appart
        nb_wc  = nb_wc_par_ap  * nb_appart

        nb_fen    = nb_ch + nb_cui + nb_sdb + nb_sal
        nb_pf     = nb_sal
        nb_pi     = nb_ch + nb_sal + nb_cui + nb_sdb + nb_wc
        nb_clim   = nb_ch + nb_sal
        nb_entrees = nb_appart + 1  # 1 entrée par appartement + 1 pour la maison RDC

        r = self.best(["construction", "maison", "agrandissement"],
                      categories=["construction"], price_min_filter=5000)
        if r:
            coeff = max(1.0, round(surf_totale / 100, 1))
            coeff_struct = round(coeff * (1 + (nombre_etages - 1) * 0.12), 1)
            p["gros_oeuvre"] = {
                "description": (f"Gros œuvre — RDC maison ({surf_rdc} m²) "
                                f"+ {nb_appart} appart. ({surf_par_ap} m²/appart.)"),
                "quantite": coeff_struct, "unite": "tranches 100m²",
                "prix_min_u": r["min"], "prix_mid_u": r["mid"], "prix_max_u": r["max"],
                "cout_min": round(coeff_struct * r["min"]),
                "cout_mid": round(coeff_struct * r["mid"]),
                "cout_max": round(coeff_struct * r["max"]),
                "fourchette": f"{_fmt(r['min'])} – {_fmt(r['max'])} DT/tranche",
                "source": r["titre"],
            }

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages)

        r = self.best(["carrelage", "sol", "pose"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste(
                f"Carrelage sol — RDC ({surf_rdc} m²) + {nb_appart} apparts ({surf_apparts_total} m²) = {surf_totale} m²",
                surf_totale, "m²", r)

        surf_faience = (nb_sdb * 10) + (nb_cui * 8)
        r = self.best(["faïence", "murale", "salle", "bain"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["faience"] = self._poste(
                f"Faïence murale — {nb_sdb} SDB + {nb_cui} cuisines ({surf_faience} m²)",
                surf_faience, "m²", r)

        r = self.best(["peinture", "intérieure", "murs"], categories=["peinture"], price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture intérieure — RDC + appartements", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = {
                "description": f"Électricité — {nombre_etages} tableaux (1 par niveau)",
                "quantite": nombre_etages, "unite": "niveau",
                "prix_min_u": r["min"], "prix_mid_u": r["mid"], "prix_max_u": r["max"],
                "cout_min": round(nombre_etages * r["min"]),
                "cout_mid": round(nombre_etages * r["mid"]),
                "cout_max": round(nombre_etages * r["max"]),
                "fourchette": f"{_fmt(r['min'])} – {_fmt(r['max'])} DT/niveau",
                "source": r.get("titre", ""),
            }

        r = self.best(["plomberie", "réseau", "multicouche"], categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = {
                "description": f"Plomberie — {nombre_etages} niveaux ({nb_sdb} SDB + {nb_cui} cuisines)",
                "quantite": nombre_etages, "unite": "niveau",
                "prix_min_u": r["min"], "prix_mid_u": r["mid"], "prix_max_u": r["max"],
                "cout_min": round(nombre_etages * r["min"]),
                "cout_mid": round(nombre_etages * r["mid"]),
                "cout_max": round(nombre_etages * r["max"]),
                "fourchette": f"{_fmt(r['min'])} – {_fmt(r['max'])} DT/niveau",
                "source": r.get("titre", ""),
            }

        r = self.best(["climatiseur", "split", "inverter"], categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(
                f"Climatisation — {nb_clim} unités ({nb_ch} chambres + {nb_sal} séjours)",
                nb_clim, "unité", r)

        r = self.best(["cuisine", "équipée", "meubles"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["cuisine_equipee"] = self._poste(
                f"Cuisines équipées — {nb_cui} unités",
                nb_cui, "unité", r)

        r = self.best(["salle", "bain", "douche", "lavabo"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste(
                f"Salles de bain complètes — {nb_sdb} unités", nb_sdb, "unité", r)

        r = self.best(["chauffe-eau", "électrique", "ballon"], categories=["estimation_construction"])
        if r:
            qty_chauffe_eau = max(1, nb_sdb if nb_sdb > 0 else nb_appart)
            p["chauffe_eau"] = self._poste(
                f"Chauffe-eau électrique — {qty_chauffe_eau} unités", qty_chauffe_eau, "unité", r)

        if nb_fen > 0:
            r = self.best(["fenêtre", "pvc", "aluminium"], categories=["menuiserie"])
            if r:
                p["fenetre"] = self._poste(
                    f"Fenêtres PVC/Aluminium — {nb_fen} unités", nb_fen, "unité", r)

        if nb_pf > 0:
            r = self.best(["porte-fenêtre", "aluminium", "coulissante"], categories=["menuiserie"])
            if r:
                p["porte_fenetre"] = self._poste(
                    f"Portes-fenêtres salons — {nb_pf} unités", nb_pf, "unité", r)

        r = self.best(["porte", "blindée", "entrée"], categories=["menuiserie"])
        if r:
            p["porte_blindee"] = self._poste(
                f"Portes blindées — {nb_entrees} entrées indépendantes",
                nb_entrees, "unité", r)

        if nb_pi > 0:
            r = self.best(["porte", "intérieure", "bois"], categories=["menuiserie"])
            if r:
                p["porte_interieure"] = self._poste(
                    f"Portes intérieures — {nb_pi} unités", nb_pi, "unité", r)

        if nb_ch > 0:
            r = self.best(["placard", "dressing", "chambre"], categories=["dressing"])
            if r:
                surf_dr = nb_ch * 4
                p["dressing"] = self._poste(
                    f"Dressing/placards — {nb_ch} chambres ({surf_dr} m²)",
                    surf_dr, "m²", r)

        r = self.best(["raccordement", "eau", "sonede"], categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste(
                f"Raccordement eau SONEDE — {nb_entrees} compteurs", nb_entrees, "forfait", r)

        r = self.best(["raccordement", "gaz", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_gaz"] = self._poste(
                f"Raccordement gaz STEG — {nb_entrees} compteurs", nb_entrees, "forfait", r)

        r = self.best(["raccordement", "électricité", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste(
                f"Raccordement électricité STEG — {nb_entrees} compteurs", nb_entrees, "forfait", r)

        r = self.best(["télésurveillance", "alarme"], categories=["estimation_construction"], price_max_filter=500)
        if r:
            r12 = {**r, "min": r["min"] * 12, "mid": r["mid"] * 12, "max": r["max"] * 12}
            p["securite"] = self._poste_ff("Télésurveillance (12 mois)", r12)

        return self._finalize(surf, p)