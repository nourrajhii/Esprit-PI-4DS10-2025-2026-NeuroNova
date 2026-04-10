"""
RAGRetriever v3.0
- Détection automatique du mode : construction / rénovation / café / appartement / villa / duplex / hotel / foyer
- Requêtes adaptées par mode et par postes demandés
- Prix formatés avec ESPACE comme séparateur de milliers (ex: 12 500 DT)
- Filtre catégories : estimation_construction, construction, renovation
- Nettoyage des prix aberrants (valeurs encodées min-max concaténées)
"""

from .vector_store import MaterialVectorStore


def fmt_price(value) -> str:
    """
    Formate un nombre avec espace tous les 3 chiffres.
    Ex: 12500  → '12 500'
        1500.5 → '1 500.50'
    """
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if v == int(v):
            return f"{int(v):,}".replace(",", "\u202f")   # espace fine insécable
        return f"{v:,.2f}".replace(",", "\u202f")
    except (ValueError, TypeError):
        return str(value)


# ─── Requêtes par mode ────────────────────────────────────────────────────────

QUERIES_CONSTRUCTION = {
    "gros_oeuvre":      "maison parpaings briques construction fondations dalle prix m² Tunis",
    "ciment_beton":     "béton chape ciment réalisation sol prix m² Tunis",
    "carrelage_sol":    "carrelage sol grès cérame pose prix m² Tunis",
    "faience_mur":      "faïence carrelage mural salle de bain cuisine prix m²",
    "isolation":        "isolation thermique acoustique murs plancher prix m² Tunis",
    "peinture":         "peinture intérieure murs plafonds prix m² Tunis",
    "electricite":      "installation électrique complète maison tableau Tunis prix",
    "plomberie":        "plomberie installation salle de bain robinetterie prix Tunis",
    "menuiserie":       "fenêtre porte-fenêtre PVC aluminium prix unité Tunis",
    "cuisine_equipee":  "cuisine équipée classique prix installation Tunis",
    "salle_de_bain":    "salle de bain douche lavabo WC création prix Tunis",
    "climatisation":    "climatiseur split inverter prix installation Tunis",
    "chauffe_eau":      "chauffe-eau électrique prix Tunis",
    "raccordements":    "raccordement eau gaz électricité assainissement Tunis",
    "securite":         "alarme télésurveillance prix installation Tunis",
    "toiture":          "toiture tuiles couverture prix m² Tunis",
}

QUERIES_RENOVATION = {
    "peinture":          "peinture rénovation intérieure murs plafonds prix m² Tunis",
    "carrelage_sol":     "remplacement carrelage sol rénovation prix m² Tunis",
    "faience_mur":       "remplacement faïence murale rénovation salle de bain prix m²",
    "isolation":         "isolation thermique rénovation murs prix m² Tunis",
    "ciment_beton":      "ragréage chape béton rénovation sol prix m²",
    "electricite":       "mise aux normes électrique rénovation tableau prix Tunis",
    "plomberie":         "rénovation plomberie salle de bain robinetterie prix Tunis",
    "menuiserie":        "remplacement fenêtre porte PVC aluminium rénovation prix Tunis",
    "cuisine_equipee":   "rénovation cuisine équipée prix Tunis",
    "salle_de_bain":     "rénovation salle de bain douche lavabo prix Tunis",
    "climatisation":     "installation climatiseur split rénovation prix Tunis",
    "faux_plafond":      "faux plafond rénovation plâtre prix m² Tunis",
    "carrelage_ext":     "carrelage extérieur terrasse rénovation prix m² Tunis",
}

QUERIES_CAFE_COMMERCE = {
    "gros_oeuvre":      "aménagement local commercial construction prix m² Tunis",
    "carrelage_sol":    "carrelage sol commercial restaurant café prix m² Tunis",
    "faience_mur":      "faïence mural décoration café restaurant prix m²",
    "peinture":         "peinture décoration intérieure commerce café prix m² Tunis",
    "electricite":      "installation électrique commerce restaurant tableau Tunis prix",
    "plomberie":        "plomberie bar café restaurant évier prix Tunis",
    "climatisation":    "climatisation commerce restaurant café split prix Tunis",
    "menuiserie":       "porte vitrine fenêtre commerce aluminium prix Tunis",
    "cuisine_equipee":  "cuisine professionnelle café restaurant équipement prix Tunis",
    "salle_de_bain":    "toilettes WC commerce sanitaires prix Tunis",
    "securite":         "alarme télésurveillance commerce prix installation Tunis",
    "isolation":        "isolation acoustique thermique commerce prix m² Tunis",
    "raccordements":    "raccordement eau gaz électricité local commercial Tunis",
}

QUERIES_APPARTEMENT = {
    "gros_oeuvre":      "appartement construction structure dalle prix m² Tunis",
    "ciment_beton":     "chape béton appartement sol prix m²",
    "carrelage_sol":    "carrelage sol appartement pose prix m² Tunis",
    "faience_mur":      "faïence salle de bain appartement prix m²",
    "peinture":         "peinture appartement intérieure prix m² Tunis",
    "electricite":      "installation électrique appartement tableau Tunis prix",
    "plomberie":        "plomberie appartement salle de bain Tunis prix",
    "menuiserie":       "fenêtre PVC aluminium appartement prix unité Tunis",
    "cuisine_equipee":  "cuisine équipée appartement prix Tunis",
    "salle_de_bain":    "salle de bain appartement création prix Tunis",
    "climatisation":    "climatiseur split appartement prix Tunis",
    "chauffe_eau":      "chauffe-eau électrique appartement prix Tunis",
    "raccordements":    "raccordement réseau eau électricité appartement Tunis",
    "securite":         "alarme appartement prix installation Tunis",
}

# Alias villa / duplex → construction avec quelques extras
QUERIES_VILLA = {**QUERIES_CONSTRUCTION,
    "piscine":   "piscine construction prix Tunis",
    "jardin":    "aménagement jardin extérieur prix Tunis",
}

# ─── Mapping mots-clés → postes rénovation ───────────────────────────────────

_RENOV_KEYWORDS = {
    "peinture":      ["peinture", "peindre", "repeindre"],
    "carrelage_sol": ["carrelage", "carrel", "sol", "revêtement sol"],
    "faience_mur":   ["faïence", "faience", "mural", "carrelage mural"],
    "isolation":     ["isolation", "isoler", "thermique", "acoustique"],
    "ciment_beton":  ["ciment", "chape", "béton", "beton", "ragréage"],
    "electricite":   ["électricité", "electricite", "électrique", "câblage", "tableau"],
    "plomberie":     ["plomberie", "plombier", "tuyau", "robinet"],
    "climatisation": ["climatisation", "clim", "climatiseur"],
    "menuiserie":    ["fenêtre", "fenetre", "porte", "menuiserie", "pvc", "aluminium"],
    "cuisine_equipee":["cuisine"],
    "salle_de_bain": ["salle de bain", "douche", "baignoire", "lavabo", "wc"],
    "faux_plafond":  ["plafond", "faux plafond"],
}


class RAGRetriever:
    def __init__(self, vector_store: MaterialVectorStore):
        self.vs = vector_store

    # ── Détection du mode projet ───────────────────────────────────────────────
    def _detect_mode(self, description: str) -> str:
        txt = description.lower()
        if any(k in txt for k in ["rénov", "renov", "refaire", "repeindre",
                                   "remplacer", "moderniser", "restaurer",
                                   "mise à jour", "rafraîch"]):
            return "renovation"
        if any(k in txt for k in ["café", "cafe", "restaurant", "commerce",
                                   "boutique", "magasin", "local commercial", "bureau"]):
            return "cafe_commerce"
        if any(k in txt for k in ["villa",]):
            return "villa"
        if any(k in txt for k in ["appartement", "appart", "studio", "f2", "f3", "f4"]):
            return "appartement"
        return "construction"

    # ── Détection des postes en mode rénovation ────────────────────────────────
    def _detect_renovation_postes(self, description: str) -> list[str]:
        txt = description.lower()
        found = [poste for poste, keys in _RENOV_KEYWORDS.items()
                 if any(k in txt for k in keys)]
        return found if found else list(_RENOV_KEYWORDS.keys())   # tout si non précisé

    # ── Recherche principale ───────────────────────────────────────────────────
    def get_prices_for_project(self, project_description: str) -> dict:
        """
        Lance les recherches RAG adaptées au mode et type de projet.
        Retourne un dict {poste: [hits]} avec prix nettoyés et formatés.
        """
        mode = self._detect_mode(project_description)
        print(f"   Mode détecté : {mode}")

        if mode == "renovation":
            postes = self._detect_renovation_postes(project_description)
            queries = {k: v for k, v in QUERIES_RENOVATION.items() if k in postes}
            if not queries:
                queries = QUERIES_RENOVATION
        elif mode == "cafe_commerce":
            queries = QUERIES_CAFE_COMMERCE
        elif mode == "villa":
            queries = QUERIES_VILLA
        elif mode == "appartement":
            queries = QUERIES_APPARTEMENT
        else:
            queries = QUERIES_CONSTRUCTION

        results = {}
        for poste, query in queries.items():
            hits = self.vs.search(query, n_results=12)
            results[poste] = [
                self._format_hit(h)
                for h in hits
                if h["relevance_score"] > 0.18
            ]

        # Méta transmise au calculator
        results["_meta"] = {
            "mode":            mode,
            "postes_demandes": list(queries.keys()),
        }
        return results

    # ── Formatage d'un hit ─────────────────────────────────────────────────────
    def _format_hit(self, h: dict) -> dict:
        meta      = h["metadata"]
        price     = self._clean(meta.get("price"))
        price_min = self._clean(meta.get("price_min"))
        price_max = self._clean(meta.get("price_max"))
        unit      = meta.get("unit", "unité")

        return {
            "title":         meta.get("title", ""),
            "price":         price,
            "price_min":     price_min,
            "price_max":     price_max,
            # Versions formatées (espace tous les 3 chiffres)
            "price_fmt":     fmt_price(price),
            "price_min_fmt": fmt_price(price_min),
            "price_max_fmt": fmt_price(price_max),
            "unit":          unit,
            "price_display": self._display(price, price_min, price_max, unit),
            "category":      meta.get("category", ""),
            "relevance":     round(h["relevance_score"], 3),
        }

    def _clean(self, value) -> float | None:
        """Supprime les valeurs nulles, négatives ou aberrantes (> 150 000)."""
        if value is None:
            return None
        try:
            v = float(value)
            return v if (0 < v < 150_000) else None
        except (ValueError, TypeError):
            return None

    def _display(self, price, p_min, p_max, unit) -> str:
        """Affichage lisible : '1 200 – 3 500 DT/m²' ou '~850 DT/unité'"""
        if p_min and p_max:
            return f"{fmt_price(p_min)} – {fmt_price(p_max)} DT/{unit}"
        if price:
            return f"~{fmt_price(price)} DT/{unit}"
        return "Prix non disponible"

    # ── Recherche libre ────────────────────────────────────────────────────────
    def search_specific(self, query: str, n: int = 5) -> list[dict]:
        hits = self.vs.search(query, n_results=n)
        return [self._format_hit(h) for h in hits]

    # ── Recherche par catégorie ────────────────────────────────────────────────
    def search_by_category(self, category: str, n: int = 10) -> list[dict]:
        """category = 'construction' | 'renovation' | 'estimation_construction'"""
        hits = self.vs.search(category, n_results=n, category_filter=category)
        return [self._format_hit(h) for h in hits]