"""
builders_commercial.py — Devis commerciaux & équipements
─────────────────────────────────────────────────────────────────────────────
Contient :
  _build_cafe              — café / commerce / restaurant
  _build_hotel             — hôtel / résidence hôtelière
  _build_foyer             — foyer / résidence étudiante
  _build_centre_esthetique — spa / hammam / salon beauté
  _build_salle_sport       — gym / fitness
  _build_clinique          — clinique / cabinet médical
  _build_bureau            — bureaux / open space
  _build_salle_fetes       — salle de réception
  _build_entrepot          — entrepôt / hangar
  _build_mixte_cafe_appart — café RDC + appartements aux étages

Importé comme mixin par DevisCalculatorBuilders.
─────────────────────────────────────────────────────────────────────────────
"""


def _fmt(v: float) -> str:
    if v is None:
        return "0"
    try:
        f = float(v)
        return "0" if f != f else f"{int(round(f)):,}".replace(",", "\u202f")
    except Exception:
        return "0"


class BuildersCommercial:
    """Mixin — projets commerciaux & équipements."""

    # ──────────────────────────────────────────────────────────────────────────
    # CAFÉ / COMMERCE
    # ──────────────────────────────────────────────────────────────────────────

    def _build_cafe(self, surf: dict, pieces: dict, nombre_etages: int = 1) -> dict:
        p        = {}
        surf_hab = surf["surface_habitable"]
        nb_clim  = max(2, round(surf_hab / 25))

        r = self.best(["carrelage", "sol", "pose"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste("Carrelage sol commercial", surf_hab, "m²", r)

        r = self.best(["faïence", "murale"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["faience"] = self._poste_ff("Faïence murale déco", r)

        r = self.best(["peinture", "murs", "finitions"], categories=["peinture"], price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture déco — murs + plafonds", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Installation électrique commerce", r)

        r = self.best(["plomberie", "réseau"], categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Plomberie bar/cuisine/WC", r)

        r = self.best(["climatiseur", "split"], categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(
                f"Climatisation split — {nb_clim} unités", nb_clim, "unité", r)

        r = self.best(["porte-fenêtre", "aluminium"], categories=["menuiserie"])
        if r:
            p["menuiserie"] = self._poste("Vitrine / porte commerce aluminium — 2 unités", 2, "unité", r)

        r = self.best(["cuisine", "équipée"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["cuisine_equipee"] = self._poste_ff("Équipement cuisine / bar professionnel", r)

        r = self.best(["salle", "bain", "douche", "wc"],
                      categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste_ff("Sanitaires WC / toilettes commerce", r)

        r = self.best(["raccordement", "eau", "sonede"],
                      categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste_ff("Raccordement eau SONEDE", r)

        r = self.best(["raccordement", "électricité", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste_ff("Raccordement électricité STEG", r)

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # HÔTEL
    # ──────────────────────────────────────────────────────────────────────────

    def _build_hotel(self, surf: dict, pieces: dict, nombre_etages: int = 1) -> dict:
        p             = {}
        surf_plancher = surf.get("surface_plancher", surf["surface_habitable"])
        surf_hab      = surf["surface_habitable"]
        emprise       = surf.get("emprise_sol", surf_hab / max(1, nombre_etages))

        guest_floors  = max(1, nombre_etages - 1)
        nb_ch_total   = self._nb(pieces, "chambres", "chambre")
        nb_sdb_input  = self._nb(pieces, "salle_de_bain", "salles_de_bain")
        nb_salons     = self._nb(pieces, "salons", "salon") or 1
        nb_cui        = self._nb(pieces, "cuisines", "cuisine") or 1

        if nb_ch_total == 0:
            nb_ch_total = max(4, round(emprise / 25)) * guest_floors

        nb_sdb_privatives = nb_sdb_input if nb_sdb_input >= nb_ch_total else nb_ch_total
        nb_sdb_communes   = max(1, nombre_etages)
        nb_sdb_total      = nb_sdb_privatives + nb_sdb_communes

        nb_fen_total    = nb_ch_total + nb_sdb_privatives + nb_cui + nb_salons + nb_sdb_communes
        nb_pf_total     = nb_salons
        nb_portes_total = nb_ch_total + nb_sdb_privatives + nb_sdb_communes + nb_cui + nb_salons
        nb_clim         = nb_ch_total + max(2, nb_salons + guest_floors - 1)

        r = self.best(["construction", "maison", "agrandissement"],
                      categories=["construction"], price_min_filter=5000)
        if r:
            coeff = max(1.0, round(surf_plancher / 100, 1))
            coeff_struct = round(coeff * (1 + (nombre_etages - 1) * 0.15), 1)
            p["gros_oeuvre"] = {
                "description": f"Gros œuvre — structure {nombre_etages} niveau(x) ({emprise:.0f} m² emprise, {surf_plancher:.0f} m² plancher)",
                "quantite": coeff_struct, "unite": "tranches 100m²",
                "prix_min_u": r["min"], "prix_mid_u": r["mid"], "prix_max_u": r["max"],
                "cout_min": round(coeff_struct * r["min"]),
                "cout_mid": round(coeff_struct * r["mid"]),
                "cout_max": round(coeff_struct * r["max"]),
                "fourchette": f"{_fmt(r['min'])} – {_fmt(r['max'])} DT/tranche",
                "source": r["titre"],
            }

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages, type_projet="hotel")

        if nombre_etages >= 4:
            p["ascenseur"] = {
                "description": f"Ascenseur hydraulique — {nombre_etages} niveaux (ERP obligatoire)",
                "quantite": 1, "unite": "forfait",
                "prix_min_u": 35_000, "prix_mid_u": 55_000, "prix_max_u": 90_000,
                "cout_min": 35_000, "cout_mid": 55_000, "cout_max": 90_000,
                "fourchette": "35 000 – 90 000 DT",
                "source": "Estimation forfaitaire",
            }

        r = self.best(["carrelage", "sol", "pose"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste(
                f"Carrelage sol — {nombre_etages} niveaux ({surf_plancher:.0f} m²)",
                surf_plancher, "m²", r)

        r = self.best(["faïence", "murale", "salle", "bain"], categories=["carrelage"], price_max_filter=200)
        if r:
            surf_f = nb_sdb_privatives * 8 + nb_sdb_communes * 12 + nb_cui * 15
            p["faience"] = self._poste(
                f"Faïence — {nb_sdb_privatives} SDB priv. + {nb_sdb_communes} WC communs + {nb_cui} cuisine(s) ({surf_f} m²)",
                surf_f, "m²", r)

        r = self.best(["peinture", "murs", "finitions"], categories=["peinture"], price_min_filter=5, price_max_filter=50)
        if not r:
            r = {"min": 5, "mid": 8, "max": 12, "titre": "Prix marché tunisien 2025"}
        p["peinture"] = self._poste(
            f"Peinture intérieure — {nombre_etages} niveaux ({surf_plancher:.0f} m²)",
            surf_plancher, "m²", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = {
                "description": f"Électricité — {nombre_etages} tableaux (1/niveau) + {nb_ch_total} points chambre",
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
                "description": f"Plomberie — réseau vertical {nombre_etages} niveaux ({nb_sdb_total} SDB + {nb_cui} cuisine)",
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
                f"Climatisation split — {nb_clim} unités ({nb_ch_total} chambres + {max(0, nb_clim - nb_ch_total)} espaces communs)",
                nb_clim, "unité", r)

        r = self.best(["salle", "bain", "douche", "lavabo"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain_privative"] = self._poste(
                f"SDB privatives — {nb_sdb_privatives} unités (1/chambre)",
                nb_sdb_privatives, "unité", r)

        r = self.best(["chauffe-eau", "électrique", "ballon"], categories=["estimation_construction"])
        if r:
            p["chauffe_eau"] = self._poste(
                f"Chauffe-eau électrique — {nb_sdb_privatives} unités",
                nb_sdb_privatives, "unité", r)

        if nb_sdb_communes > 0:
            r2 = self.best(["salle", "bain", "douche", "wc"], categories=["estimation_construction"], price_min_filter=500)
            if r2:
                p["sdb_communes"] = self._poste(
                    f"WC communs — {nb_sdb_communes} blocs (1/niveau)",
                    nb_sdb_communes, "unité", r2)

        r = self.best(["cuisine", "équipée", "meubles"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["cuisine_equipee"] = self._poste(
                f"Cuisine(s) équipée(s) — {nb_cui} unité(s)", nb_cui, "unité", r)

        r = self.best(["fenêtre", "pvc", "aluminium", "double", "vitrage"], categories=["menuiserie"])
        if r:
            p["fenetre"] = self._poste(
                f"Fenêtres aluminium — {nb_fen_total} unités", nb_fen_total, "unité", r)

        if nb_pf_total > 0:
            r = self.best(["porte-fenêtre", "aluminium", "coulissante"], categories=["menuiserie"])
            if r:
                p["porte_fenetre"] = self._poste(
                    f"Porte(s)-fenêtre aluminium — {nb_pf_total} unité(s)", nb_pf_total, "unité", r)

        r = self.best(["porte", "intérieure", "bois", "chambre"], categories=["menuiserie"])
        if r:
            p["porte_interieure"] = self._poste(
                f"Portes intérieures — {nb_portes_total} unités", nb_portes_total, "unité", r)

        r = self.best(["porte", "blindée", "entrée", "sécurité"], categories=["menuiserie"])
        if r:
            p["porte_blindee"] = self._poste("Porte blindée entrée principale", 1, "unité", r)

        r = self.best(["raccordement", "eau", "sonede"], categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste_ff("Raccordement eau SONEDE", r)

        r = self.best(["raccordement", "électricité", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste_ff("Raccordement électricité STEG (triphasé)", r)

        r = self.best(["télésurveillance", "alarme"], categories=["estimation_construction"], price_max_filter=500)
        if r:
            r12 = {**r, "min": r["min"] * 12, "mid": r["mid"] * 12, "max": r["max"] * 12}
            p["securite"] = self._poste_ff("Sécurité + vidéosurveillance (12 mois)", r12)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # FOYER
    # ──────────────────────────────────────────────────────────────────────────
    # FOYER
    # ──────────────────────────────────────────────────────────────────────────

    def _build_foyer(self, surf: dict, pieces: dict, nombre_etages: int = 1) -> dict:
        p        = {}
        surf_hab = surf["surface_habitable"]
        nb_ch    = self._nb(pieces, "chambres", "chambre") or max(8, round(surf_hab / 15))
        nb_sdb   = max(2, round(nb_ch / 3))
        nb_clim  = max(2, round(surf_hab / 40))

        r = self.best(["construction", "maison", "agrandissement"],
                      categories=["construction"], price_min_filter=5000)
        if r:
            coeff = max(1.0, round(surf_hab / 100, 1))
            p["gros_oeuvre"] = {
                "description": f"Gros œuvre — foyer {nombre_etages} niveau(x)",
                "quantite": coeff, "unite": "tranches 100m²",
                "prix_min_u": r["min"], "prix_mid_u": r["mid"], "prix_max_u": r["max"],
                "cout_min": round(coeff * r["min"]),
                "cout_mid": round(coeff * r["mid"]),
                "cout_max": round(coeff * r["max"]),
                "fourchette": f"{_fmt(r['min'])} – {_fmt(r['max'])} DT/tranche",
                "source": r["titre"],
            }

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages, type_projet="foyer")

        r = self.best(["carrelage", "sol", "pose"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste(f"Carrelage sol — {surf_hab:.0f} m²", surf_hab, "m²", r)

        r = self.best(["peinture", "intérieure", "murs"], categories=["peinture"], price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture intérieure (forfait)", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Installation électrique complète", r)

        r = self.best(["plomberie", "réseau", "multicouche"], categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Plomberie — réseau complet", r)

        r = self.best(["salle", "bain", "douche", "lavabo"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste(f"Salles de bain communes — {nb_sdb} unités", nb_sdb, "unité", r)

        r = self.best(["climatiseur", "split"], categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(f"Climatisation — {nb_clim} unités", nb_clim, "unité", r)

        r = self.best(["cuisine", "équipée", "meubles"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["cuisine_equipee"] = self._poste_ff("Cuisine commune équipée", r)

        r = self.best(["télésurveillance", "alarme"], categories=["estimation_construction"], price_max_filter=500)
        if r:
            r12 = {**r, "min": r["min"] * 12, "mid": r["mid"] * 12, "max": r["max"] * 12}
            p["securite"] = self._poste_ff("Sécurité + accès contrôlé (12 mois)", r12)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # CENTRE ESTHÉTIQUE
    # ──────────────────────────────────────────────────────────────────────────

    def _build_centre_esthetique(self, surf: dict, pieces: dict, nombre_etages: int = 1) -> dict:
        p        = {}
        surf_hab = surf["surface_habitable"]
        nb_cabines = self._nb(pieces, "chambres", "chambre") or max(4, round(surf_hab / 15))
        nb_clim  = max(2, round(surf_hab / 20))

        for kw, label in [
            (["carrelage", "sol", "pose"], f"Carrelage sol — {surf_hab:.0f} m²"),
        ]:
            r = self.best(kw, categories=["carrelage"], price_max_filter=200)
            if r:
                p["carrelage_sol"] = self._poste(label, surf_hab, "m²", r)

        r = self.best(["faïence", "murale"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["faience"] = self._poste(f"Faïence murale — {nb_cabines} cabines", nb_cabines * 12, "m²", r)

        r = self.best(["peinture", "murs", "finitions"], categories=["peinture"], price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture déco — murs + plafonds", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Électricité (éclairage ambiance inclus)", r)

        r = self.best(["plomberie", "réseau", "multicouche"], categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Plomberie — cabines, douches, hammam", r)

        r = self.best(["salle", "bain", "douche", "lavabo"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste(f"Cabines soins / douches — {nb_cabines} unités", nb_cabines, "unité", r)

        r = self.best(["climatiseur", "split"], categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(f"Climatisation — {nb_clim} unités", nb_clim, "unité", r)

        r = self.best(["porte-fenêtre", "aluminium"], categories=["menuiserie"])
        if r:
            p["menuiserie"] = self._poste("Vitrine / façade aluminium — 2 unités", 2, "unité", r)

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages)

        r = self.best(["raccordement", "eau", "sonede"], categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste_ff("Raccordement eau SONEDE", r)

        r = self.best(["raccordement", "électricité", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste_ff("Raccordement électricité STEG", r)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # SALLE DE SPORT
    # ──────────────────────────────────────────────────────────────────────────

    def _build_salle_sport(self, surf: dict, pieces: dict, nombre_etages: int = 1) -> dict:
        p        = {}
        surf_hab = surf["surface_habitable"]
        nb_clim  = max(3, round(surf_hab / 30))
        nb_sdb   = self._nb(pieces, "salles_de_bain", "salle_de_bain") or max(2, round(surf_hab / 80))

        r = self.best(["carrelage", "sol", "pose"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste(f"Sol salle de sport — {surf_hab:.0f} m²", surf_hab, "m²", r)

        r = self.best(["peinture", "murs", "finitions"], categories=["peinture"], price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture murs (résistante humidité)", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Électricité — éclairage intense + prises", r)

        r = self.best(["plomberie", "réseau"], categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Plomberie — vestiaires, douches", r)

        r = self.best(["salle", "bain", "douche", "lavabo"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste(f"Vestiaires / douches — {nb_sdb} unités", nb_sdb, "unité", r)

        r = self.best(["climatiseur", "split"], categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(f"Climatisation — {nb_clim} unités", nb_clim, "unité", r)

        r = self.best(["porte-fenêtre", "aluminium"], categories=["menuiserie"])
        if r:
            p["menuiserie"] = self._poste("Façade / portes aluminium — 2 unités", 2, "unité", r)

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages)

        r = self.best(["raccordement", "eau", "sonede"], categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste_ff("Raccordement eau SONEDE", r)

        r = self.best(["raccordement", "électricité", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste_ff("Raccordement électricité STEG (triphasé)", r)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # CLINIQUE
    # ──────────────────────────────────────────────────────────────────────────

    def _build_clinique(self, surf: dict, pieces: dict, nombre_etages: int = 1) -> dict:
        p        = {}
        surf_hab = surf["surface_habitable"]
        nb_cab   = self._nb(pieces, "chambres", "chambre") or max(3, round(surf_hab / 20))
        nb_sdb   = max(1, round(nb_cab / 2))
        nb_clim  = nb_cab + 2

        r = self.best(["carrelage", "sol", "pose"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste(f"Carrelage sol médical — {surf_hab:.0f} m²", surf_hab, "m²", r)

        r = self.best(["faïence", "murale"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["faience"] = self._poste(f"Faïence murale — {nb_cab} cabinets", nb_cab * 10, "m²", r)

        r = self.best(["peinture", "murs", "finitions"], categories=["peinture"], price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture époxy / lessivable (hygiène)", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Électricité — tableau + prises spécialisées", r)

        r = self.best(["plomberie", "réseau", "multicouche"], categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Plomberie — évier, WC, stérilisation", r)

        r = self.best(["salle", "bain", "douche", "lavabo"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste(f"Sanitaires / WC — {nb_sdb} unités", nb_sdb, "unité", r)

        r = self.best(["climatiseur", "split"], categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(f"Climatisation — {nb_clim} unités", nb_clim, "unité", r)

        r = self.best(["porte", "intérieure", "bois"], categories=["menuiserie"])
        if r:
            p["porte_interieure"] = self._poste(f"Portes cabinets — {nb_cab} unités", nb_cab, "unité", r)

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages, type_projet="clinique")

        r = self.best(["raccordement", "eau", "sonede"], categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste_ff("Raccordement eau SONEDE", r)

        r = self.best(["raccordement", "électricité", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste_ff("Raccordement électricité STEG", r)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # BUREAUX
    # ──────────────────────────────────────────────────────────────────────────

    def _build_bureau(self, surf: dict, pieces: dict, nombre_etages: int = 1) -> dict:
        p        = {}
        surf_hab = surf["surface_habitable"]
        nb_clim  = max(2, round(surf_hab / 30))
        nb_sdb   = max(1, round(surf_hab / 100))

        r = self.best(["carrelage", "sol", "pose"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste(f"Carrelage sol bureau — {surf_hab:.0f} m²", surf_hab, "m²", r)

        r = self.best(["peinture", "murs", "finitions"], categories=["peinture"], price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture murs + plafonds (forfait)", r)

        r = self.best(["faux", "plafond", "ba13"], categories=["renovation"])
        if r:
            p["faux_plafond"] = self._poste(f"Faux plafond suspendu — {surf_hab:.0f} m²", surf_hab, "m²", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Électricité — tableau + câblage réseau + prises", r)

        r = self.best(["plomberie", "réseau"], categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Plomberie — WC, cuisine équipée", r)

        r = self.best(["climatiseur", "split"], categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(f"Climatisation — {nb_clim} unités", nb_clim, "unité", r)

        r = self.best(["porte-fenêtre", "aluminium"], categories=["menuiserie"])
        if r:
            p["menuiserie"] = self._poste("Façade vitrée / portes aluminium — 2 unités", 2, "unité", r)

        r = self.best(["salle", "bain", "douche", "wc"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste(f"WC / sanitaires — {nb_sdb} unités", nb_sdb, "unité", r)

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages, type_projet="bureau")

        r = self.best(["raccordement", "électricité", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste_ff("Raccordement électricité STEG", r)

        r = self.best(["télésurveillance", "alarme"], categories=["estimation_construction"], price_max_filter=500)
        if r:
            r12 = {**r, "min": r["min"] * 12, "mid": r["mid"] * 12, "max": r["max"] * 12}
            p["securite"] = self._poste_ff("Système de sécurité accès (12 mois)", r12)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # SALLE DES FÊTES
    # ──────────────────────────────────────────────────────────────────────────

    def _build_salle_fetes(self, surf: dict, pieces: dict, nombre_etages: int = 1) -> dict:
        p        = {}
        surf_hab = surf["surface_habitable"]
        nb_clim  = max(4, round(surf_hab / 40))
        nb_sdb   = max(2, round(surf_hab / 150))

        r = self.best(["carrelage", "sol", "grès", "cérame"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["carrelage_sol"] = self._poste(f"Carrelage sol salle — {surf_hab:.0f} m²", surf_hab, "m²", r)

        r = self.best(["peinture", "murs", "finitions"], categories=["peinture"], price_min_filter=500)
        if r:
            p["peinture"] = self._poste_ff("Peinture déco — murs + plafonds ornementaux", r)

        r = self.best(["faux", "plafond", "ba13"], categories=["renovation"])
        if r:
            p["faux_plafond"] = self._poste(f"Faux plafond décoratif — {surf_hab:.0f} m²", surf_hab, "m²", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Électricité — éclairage scénique + sono", r)

        r = self.best(["plomberie", "réseau"], categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Plomberie — bar, cuisine traiteur, WC", r)

        r = self.best(["climatiseur", "split"], categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(f"Climatisation grande capacité — {nb_clim} unités", nb_clim, "unité", r)

        r = self.best(["porte-fenêtre", "aluminium"], categories=["menuiserie"])
        if r:
            p["menuiserie"] = self._poste("Portes principales / entrée aluminium — 3 unités", 3, "unité", r)

        r = self.best(["salle", "bain", "wc"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste(f"Sanitaires / WC invités — {nb_sdb} blocs", nb_sdb, "unité", r)

        r = self.best(["cuisine", "équipée"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["cuisine_equipee"] = self._poste_ff("Cuisine traiteur / office équipé", r)

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages, type_projet="salle_fetes")

        r = self.best(["raccordement", "eau", "sonede"], categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste_ff("Raccordement eau SONEDE", r)

        r = self.best(["raccordement", "électricité", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste_ff("Raccordement électricité STEG (triphasé)", r)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # ENTREPÔT
    # ──────────────────────────────────────────────────────────────────────────

    def _build_entrepot(self, surf: dict, pieces: dict, nombre_etages: int = 1) -> dict:
        p        = {}
        surf_hab = surf["surface_habitable"]
        nb_clim  = max(1, round(surf_hab / 100))

        r = self.best(["construction", "maison", "agrandissement"],
                      categories=["construction"], price_min_filter=5000)
        if r:
            r_ent = {**r, "min": round(r["min"] * 0.6), "mid": round(r["mid"] * 0.6),
                     "max": round(r["max"] * 0.7)}
            coeff = max(1.0, round(surf_hab / 100, 1))
            p["gros_oeuvre"] = {
                "description": "Gros œuvre — structure béton/métal, dalle, couverture",
                "quantite": coeff, "unite": "tranches 100m²",
                "prix_min_u": r_ent["min"], "prix_mid_u": r_ent["mid"], "prix_max_u": r_ent["max"],
                "cout_min": round(coeff * r_ent["min"]),
                "cout_mid": round(coeff * r_ent["mid"]),
                "cout_max": round(coeff * r_ent["max"]),
                "fourchette": f"{_fmt(r_ent['min'])} – {_fmt(r_ent['max'])} DT/tranche",
                "source": r["titre"],
            }

        r = self.best(["carrelage", "sol", "pose"], categories=["carrelage"], price_max_filter=100)
        if r:
            p["dalle_beton"] = self._poste(f"Dalle béton / sol industriel — {surf_hab:.0f} m²", surf_hab, "m²", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = self._poste_ff("Électricité industrielle — tableau + éclairage", r)

        r = self.best(["plomberie", "réseau"], categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = self._poste_ff("Plomberie — WC, point d'eau", r)

        r = self.best(["climatiseur", "split"], categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(f"Ventilation / clim — {nb_clim} unités", nb_clim, "unité", r)

        r = self.best(["porte-fenêtre", "aluminium"], categories=["menuiserie"])
        if r:
            p["menuiserie"] = self._poste("Portail industriel + porte accès — 2 unités", 2, "unité", r)

        if nombre_etages > 1:
            self._add_escalier(p, nombre_etages)

        r = self.best(["raccordement", "eau", "sonede"], categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste_ff("Raccordement eau SONEDE", r)

        r = self.best(["raccordement", "électricité", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste_ff("Raccordement électricité STEG (triphasé)", r)

        return self._finalize(surf, p)

    # ──────────────────────────────────────────────────────────────────────────
    # MIXTE : CAFÉ RDC + APPARTEMENTS
    # ──────────────────────────────────────────────────────────────────────────

    def _build_mixte_cafe_appart(self, surf: dict, pieces: dict,
                                  nombre_etages: int = 1) -> dict:
        """
        Café au RDC + appartements aux étages.

        Règles de comptage demandées par l'utilisateur pour les appartements :
        - 1 chambre = 1 fenêtre + 1 porte intérieure + 1 dressing
        - 1 salle de bain = 1 fenêtre + 1 porte intérieure
        - 1 salon = 1 fenêtre + 1 porte intérieure + 1 porte-fenêtre
        - 1 cuisine = 1 fenêtre + 1 porte intérieure
        """
        p = {}

        nb_appart = max(1, int(pieces.get("_nb_appartements") or max(1, nombre_etages - 1)))
        if nombre_etages >= 3 and nb_appart == 1:
            nb_appart = max(2, nombre_etages - 1)
        emprise_sol = surf.get("emprise_sol", surf["surface_habitable"] / max(1, nombre_etages))

        surf_rdc           = round(emprise_sol * 0.85)
        surf_par_ap        = round(emprise_sol * 0.85)
        surf_apparts_total = surf_par_ap * nb_appart
        surf_totale        = surf_rdc + surf_apparts_total

        nb_ch  = self._nb(pieces, "chambres", "chambre")
        nb_sal = self._nb(pieces, "salons", "salon")
        nb_cui = self._nb(pieces, "cuisines", "cuisine")
        nb_sdb = self._nb(pieces, "salle_de_bain", "salles_de_bain")
        nb_wc  = self._nb(pieces, "wc")

        if nb_sal == 0 and nb_appart > 0:
            nb_sal = nb_appart
        if nb_cui == 0 and nb_appart > 0:
            nb_cui = nb_appart
        if nb_sdb == 0 and nb_appart > 0:
            nb_sdb = nb_appart

        nb_fen_appart = nb_ch + nb_sdb + nb_cui + nb_sal
        nb_pi         = nb_ch + nb_sdb + nb_cui + nb_sal + nb_wc
        nb_pf         = nb_sal
        nb_dressing_ch = nb_ch

        nb_clim_cafe   = 2
        nb_clim_appart = nb_appart * 2
        nb_clim_total  = nb_clim_cafe + nb_clim_appart
        nb_unites      = 1 + nb_appart

        r = self.best(["construction", "maison", "agrandissement"],
                      categories=["construction"], price_min_filter=5000)
        if r:
            coeff = max(1.0, round(surf_totale / 100, 1))
            coeff_struct = round(coeff * (1 + (nombre_etages - 1) * 0.12), 1)
            p["gros_oeuvre"] = {
                "description": (f"Gros œuvre — RDC ({surf_rdc} m² café) "
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
                f"Carrelage sol — RDC café ({surf_rdc} m²) + {nb_appart} apparts ({surf_apparts_total} m²) = {surf_totale} m²",
                surf_totale, "m²", r)

        surf_faience = (nb_sdb * 10) + (nb_cui * 8)
        r = self.best(["faïence", "murale", "salle", "bain"], categories=["carrelage"], price_max_filter=200)
        if r:
            p["faience"] = self._poste(
                f"Faïence murale — {nb_sdb} SDB + {nb_cui} cuisines apparts ({surf_faience} m²)",
                surf_faience, "m²", r)

        r = self.best(["peinture", "murs", "finitions"], categories=["peinture"],
                      price_min_filter=5, price_max_filter=50)
        if not r:
            r = {"min": 5, "mid": 8, "max": 12, "titre": "Prix marché tunisien 2025"}
        p["peinture"] = self._poste(
            f"Peinture intérieure — café ({surf_rdc} m²) + {nb_appart} apparts ({surf_apparts_total} m²)",
            surf_totale, "m²", r)

        r = self.best(["installation", "électrique", "tableau"], categories=["electricite"])
        if r:
            p["electricite"] = {
                "description": f"Électricité — {nb_unites} tableaux indépendants (1 café + {nb_appart} apparts)",
                "quantite": nb_unites, "unite": "unité",
                "prix_min_u": r["min"], "prix_mid_u": r["mid"], "prix_max_u": r["max"],
                "cout_min": round(nb_unites * r["min"]),
                "cout_mid": round(nb_unites * r["mid"]),
                "cout_max": round(nb_unites * r["max"]),
                "fourchette": f"{_fmt(r['min'])} – {_fmt(r['max'])} DT/unité",
                "source": r.get("titre", ""),
            }

        r = self.best(["plomberie", "réseau", "multicouche"], categories=["plomberie"], price_min_filter=500)
        if r:
            p["plomberie"] = {
                "description": f"Plomberie — {nb_unites} réseaux ({nb_sdb} SDB + {nb_cui} cuisines + bar café)",
                "quantite": nb_unites, "unite": "unité",
                "prix_min_u": r["min"], "prix_mid_u": r["mid"], "prix_max_u": r["max"],
                "cout_min": round(nb_unites * r["min"]),
                "cout_mid": round(nb_unites * r["mid"]),
                "cout_max": round(nb_unites * r["max"]),
                "fourchette": f"{_fmt(r['min'])} – {_fmt(r['max'])} DT/unité",
                "source": r.get("titre", ""),
            }

        r = self.best(["climatiseur", "split", "inverter"], categories=["climatisation"], price_max_filter=2000)
        if r:
            p["climatisation"] = self._poste(
                f"Climatisation — {nb_clim_cafe} café + {nb_clim_appart} apparts ({nb_clim_total} total)",
                nb_clim_total, "unité", r)

        r = self.best(["cuisine", "équipée", "meubles"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["cuisine_appart"] = self._poste(
                f"Cuisines équipées appartements — {nb_cui} unité{'s' if nb_cui > 1 else ''}",
                nb_cui, "unité", r)

        r = self.best(["cuisine", "équipée"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            r_bar = {**r, "min": round(r["min"] * 1.5), "mid": round(r["mid"] * 1.5), "max": round(r["max"] * 2)}
            p["cuisine_cafe"] = self._poste_ff("Équipement bar/cuisine professionnelle — RDC café", r_bar)

        r = self.best(["salle", "bain", "douche", "lavabo"], categories=["estimation_construction"], price_min_filter=2000)
        if r:
            p["salle_de_bain"] = self._poste(
                f"Salles de bain — {nb_sdb} unité{'s' if nb_sdb > 1 else ''} (appartements)",
                nb_sdb, "unité", r)

        r2 = self.best(["salle", "bain", "douche", "wc"], categories=["estimation_construction"], price_min_filter=500)
        if r2:
            p["sanitaires_cafe"] = self._poste_ff("WC / sanitaires publics — RDC café", r2)

        if nb_fen_appart > 0:
            r = self.best(["fenêtre", "pvc", "aluminium"], categories=["menuiserie"])
            if r:
                p["fenetre"] = self._poste(
                    f"Fenêtres PVC/Aluminium appartements — {nb_fen_appart} unités",
                    nb_fen_appart, "unité", r)

        if nb_pf > 0:
            r = self.best(["porte-fenêtre", "aluminium", "coulissante"], categories=["menuiserie"])
            if r:
                p["porte_fenetre"] = self._poste(
                    f"Portes-fenêtres salons appartements — {nb_pf} unité{'s' if nb_pf > 1 else ''}",
                    nb_pf, "unité", r)

        r = self.best(["porte-fenêtre", "aluminium", "coulissante"], categories=["menuiserie"])
        if r:
            p["vitrine_cafe"] = self._poste("Vitrine / façade aluminium café — 2 unités", 2, "unité", r)

        r = self.best(["porte", "blindée", "entrée"], categories=["menuiserie"])
        if r:
            p["porte_blindee"] = self._poste(
                f"Portes blindées — {nb_unites} unités (1 café + {nb_appart} apparts)",
                nb_unites, "unité", r)

        if nb_pi > 0:
            r = self.best(["porte", "intérieure", "bois", "chambre"], categories=["menuiserie"])
            if r:
                p["porte_interieure"] = self._poste(
                    f"Portes intérieures appartements — {nb_pi} unités",
                    nb_pi, "unité", r)

        if nb_dressing_ch > 0:
            r = self.best(["placard", "dressing", "chambre"], categories=["dressing"])
            if r:
                surf_dr = nb_dressing_ch * 4
                p["dressing"] = self._poste(
                    f"Dressing/placards — {nb_dressing_ch} chambres ({surf_dr} m²)",
                    surf_dr, "m²", r)

        r = self.best(["raccordement", "eau", "sonede"], categories=["estimation_construction"], price_max_filter=1000)
        if r:
            p["raccord_eau"] = self._poste(
                f"Raccordements eau SONEDE — {nb_unites} compteurs",
                nb_unites, "forfait", r)

        r = self.best(["raccordement", "gaz", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_gaz"] = self._poste(
                f"Raccordements gaz STEG — {nb_unites} compteurs",
                nb_unites, "forfait", r)

        r = self.best(["raccordement", "électricité", "steg"], categories=["estimation_construction"])
        if r:
            p["raccord_elec"] = self._poste(
                f"Raccordements électricité STEG — {nb_unites} compteurs",
                nb_unites, "forfait", r)

        return self._finalize(surf, p)

