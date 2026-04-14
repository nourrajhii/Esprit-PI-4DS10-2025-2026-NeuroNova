"""
RAGRetriever v4.0
- Détection automatique du mode : construction / rénovation / café / appartement /
  villa / duplex / hotel / foyer / centre_esthetique / salle_sport /
  clinique / bureau / salle_fetes / entrepot
- Requêtes adaptées par mode et par postes demandés
- Requête escalier ajoutée pour tous les projets multi-étages
- Prix formatés avec ESPACE comme séparateur de milliers (ex: 12 500 DT)
- Filtre catégories : estimation_construction, construction, renovation
- Nettoyage des prix aberrants (valeurs encodées min-max concaténées)
"""

from .vector_store import MaterialVectorStore


def fmt_price(value) -> str:
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if v == int(v):
            return f"{int(v):,}".replace(",", "\u202f")
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
    "escalier":         "escalier béton marches volée prix construction Tunis",
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
    "escalier":         "escalier béton marches volée prix construction Tunis",
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
    "escalier":         "escalier béton marches volée prix construction Tunis",
}

QUERIES_VILLA = {**QUERIES_CONSTRUCTION,
    "piscine":   "piscine construction prix Tunis",
    "jardin":    "aménagement jardin extérieur prix Tunis",
}

QUERIES_HOTEL = {
    "gros_oeuvre":      "construction hôtel résidence structure béton prix m² Tunis",
    "carrelage_sol":    "carrelage sol hôtel chambre couloir prix m² Tunis",
    "faience_mur":      "faïence salle de bain hôtel chambre prix m²",
    "peinture":         "peinture hôtel chambre couloir intérieur prix m² Tunis",
    "electricite":      "installation électrique hôtel tableau général prix Tunis",
    "plomberie":        "plomberie hôtel réseau chambres prix Tunis",
    "menuiserie":       "fenêtre porte chambre hôtel PVC aluminium prix unité Tunis",
    "salle_de_bain":    "salle de bain hôtel douche lavabo wc prix unité Tunis",
    "climatisation":    "climatiseur split hôtel chambre prix Tunis",
    "raccordements":    "raccordement eau électricité hôtel Tunis",
    "securite":         "télésurveillance alarme hôtel sécurité prix Tunis",
    "escalier":         "escalier béton marches volée prix construction Tunis",
}

QUERIES_FOYER = {
    "gros_oeuvre":      "construction foyer résidence étudiante béton prix m² Tunis",
    "carrelage_sol":    "carrelage sol résidence couloir chambre prix m² Tunis",
    "peinture":         "peinture résidence intérieur couloir prix m² Tunis",
    "electricite":      "installation électrique résidence tableau prix Tunis",
    "plomberie":        "plomberie résidence salle de bain partagée prix Tunis",
    "salle_de_bain":    "salle de bain commune douche lavabo prix Tunis",
    "climatisation":    "climatiseur split résidence prix Tunis",
    "cuisine_equipee":  "cuisine commune équipée résidence prix Tunis",
    "raccordements":    "raccordement eau électricité résidence Tunis",
    "securite":         "alarme accès contrôle résidence sécurité prix Tunis",
    "escalier":         "escalier béton marches volée prix construction Tunis",
}

QUERIES_CENTRE_ESTHETIQUE = {
    "carrelage_sol":    "carrelage sol spa salon esthétique prix m² Tunis",
    "faience_mur":      "faïence murale hammam spa décoration prix m²",
    "peinture":         "peinture déco spa salon esthétique prix m² Tunis",
    "electricite":      "installation électrique salon commerce tableau prix Tunis",
    "plomberie":        "plomberie cabine soin hammam douche prix Tunis",
    "salle_de_bain":    "cabine soin douche hammam création prix Tunis",
    "climatisation":    "climatiseur split salon commerce prix Tunis",
    "menuiserie":       "vitrine façade aluminium salon commerce prix Tunis",
    "raccordements":    "raccordement eau électricité local commercial Tunis",
    "escalier":         "escalier béton marches volée prix construction Tunis",
}

QUERIES_SALLE_SPORT = {
    "carrelage_sol":    "carrelage sol antidérapant salle sport gym prix m² Tunis",
    "peinture":         "peinture salle sport murs résistante prix m² Tunis",
    "electricite":      "installation électrique salle sport éclairage tableau prix Tunis",
    "plomberie":        "plomberie vestiaires douches salle sport prix Tunis",
    "salle_de_bain":    "vestiaires douches salle sport création prix Tunis",
    "climatisation":    "climatisation ventilation salle sport gym prix Tunis",
    "menuiserie":       "porte façade aluminium salle sport prix Tunis",
    "raccordements":    "raccordement eau électricité triphasé Tunis",
    "escalier":         "escalier béton marches volée prix construction Tunis",
}

QUERIES_CLINIQUE = {
    "carrelage_sol":    "carrelage sol médical clinique cabinet prix m² Tunis",
    "faience_mur":      "faïence murale clinique cabinet médical hygiène prix m²",
    "peinture":         "peinture époxy lessivable clinique prix m² Tunis",
    "electricite":      "installation électrique clinique cabinet médical tableau prix Tunis",
    "plomberie":        "plomberie clinique cabinet médical évier stérilisation prix Tunis",
    "salle_de_bain":    "sanitaires WC cabinet médical prix Tunis",
    "climatisation":    "climatiseur split clinique cabinet prix Tunis",
    "menuiserie":       "porte cabinet médical aluminium prix Tunis",
    "raccordements":    "raccordement eau électricité local médical Tunis",
    "escalier":         "escalier béton marches volée prix construction Tunis",
}

QUERIES_BUREAU = {
    "carrelage_sol":    "carrelage sol bureau open space prix m² Tunis",
    "peinture":         "peinture bureau open space intérieure prix m² Tunis",
    "faux_plafond":     "faux plafond bureau open space prix m² Tunis",
    "electricite":      "installation électrique bureau câblage réseau tableau prix Tunis",
    "plomberie":        "plomberie bureau WC cuisine équipée prix Tunis",
    "climatisation":    "climatiseur split bureau prix Tunis",
    "menuiserie":       "façade vitrée porte aluminium bureau prix Tunis",
    "salle_de_bain":    "WC sanitaires bureau prix Tunis",
    "raccordements":    "raccordement eau électricité bureau Tunis",
    "securite":         "alarme accès badge bureau sécurité prix Tunis",
    "escalier":         "escalier béton marches volée prix construction Tunis",
}

QUERIES_SALLE_FETES = {
    "carrelage_sol":    "carrelage sol salle fêtes réception mariage prix m² Tunis",
    "peinture":         "peinture décorative salle fêtes ornementale prix m² Tunis",
    "faux_plafond":     "faux plafond décoratif salle fêtes prix m² Tunis",
    "electricite":      "installation électrique salle fêtes éclairage scénique prix Tunis",
    "plomberie":        "plomberie salle fêtes bar WC cuisine traiteur prix Tunis",
    "climatisation":    "climatisation grande salle fêtes prix Tunis",
    "menuiserie":       "portail porte entrée salle fêtes aluminium prix Tunis",
    "cuisine_equipee":  "cuisine traiteur office équipé salle fêtes prix Tunis",
    "salle_de_bain":    "WC sanitaires invités salle fêtes prix Tunis",
    "raccordements":    "raccordement eau électricité salle fêtes Tunis",
    "escalier":         "escalier béton marches volée prix construction Tunis",
}

QUERIES_ENTREPOT = {
    "gros_oeuvre":      "construction entrepôt hangar béton métal prix m² Tunis",
    "dalle_beton":      "dalle béton sol industriel entrepôt prix m² Tunis",
    "electricite":      "installation électrique industrielle entrepôt tableau prix Tunis",
    "plomberie":        "plomberie entrepôt point eau WC prix Tunis",
    "climatisation":    "ventilation climatisation entrepôt prix Tunis",
    "menuiserie":       "portail industriel porte entrepôt aluminium prix Tunis",
    "raccordements":    "raccordement eau électricité triphasé entrepôt Tunis",
    "escalier":         "escalier métal industriel mezzanine prix Tunis",
}

# ─── Mapping mots-clés → postes rénovation ───────────────────────────────────

_RENOV_KEYWORDS = {
    "peinture":       ["peinture", "peindre", "repeindre"],
    "carrelage_sol":  ["carrelage", "carrel", "sol", "revêtement sol"],
    "faience_mur":    ["faïence", "faience", "mural", "carrelage mural"],
    "isolation":      ["isolation", "isoler", "thermique", "acoustique"],
    "ciment_beton":   ["ciment", "chape", "béton", "beton", "ragréage"],
    "electricite":    ["électricité", "electricite", "électrique", "câblage", "tableau"],
    "plomberie":      ["plomberie", "plombier", "tuyau", "robinet"],
    "climatisation":  ["climatisation", "clim", "climatiseur"],
    "menuiserie":     ["fenêtre", "fenetre", "porte", "menuiserie", "pvc", "aluminium"],
    "cuisine_equipee":["cuisine"],
    "salle_de_bain":  ["salle de bain", "douche", "baignoire", "lavabo", "wc"],
    "faux_plafond":   ["plafond", "faux plafond"],
}

# ─── Mapping mode → dict de requêtes ─────────────────────────────────────────

_MODE_QUERIES = {
    "renovation":        None,          # géré spécialement
    "cafe_commerce":     QUERIES_CAFE_COMMERCE,
    "villa":             QUERIES_VILLA,
    "appartement":       QUERIES_APPARTEMENT,
    "hotel":             QUERIES_HOTEL,
    "foyer":             QUERIES_FOYER,
    "centre_esthetique": QUERIES_CENTRE_ESTHETIQUE,
    "salle_sport":       QUERIES_SALLE_SPORT,
    "clinique":          QUERIES_CLINIQUE,
    "bureau":            QUERIES_BUREAU,
    "salle_fetes":       QUERIES_SALLE_FETES,
    "entrepot":          QUERIES_ENTREPOT,
    "construction":      QUERIES_CONSTRUCTION,
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
        if any(k in txt for k in ["hôtel", "hotel", "résidence hôtelière", "appart-hôtel"]):
            return "hotel"
        if any(k in txt for k in ["foyer", "résidence étudiante", "internat", "maison de retraite"]):
            return "foyer"
        if any(k in txt for k in ["esthétique", "esthetique", "spa", "hammam",
                                   "salon de beauté", "centre esthétique"]):
            return "centre_esthetique"
        if any(k in txt for k in ["salle de sport", "gym", "fitness", "musculation"]):
            return "salle_sport"
        if any(k in txt for k in ["clinique", "cabinet médical", "dentiste", "pharmacie"]):
            return "clinique"
        if any(k in txt for k in ["bureau", "bureaux", "open space", "coworking", "siège social"]):
            return "bureau"
        if any(k in txt for k in ["salle des fêtes", "salle de mariage",
                                   "salle de réception", "salle fêtes"]):
            return "salle_fetes"
        if any(k in txt for k in ["entrepôt", "entrepot", "hangar", "dépôt"]):
            return "entrepot"
        if any(k in txt for k in ["café", "cafe", "restaurant", "commerce",
                                   "boutique", "magasin", "local commercial"]):
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
        return found if found else list(_RENOV_KEYWORDS.keys())

    # ── Recherche principale ───────────────────────────────────────────────────
    def get_prices_for_project(self, project_description: str) -> dict:
        """
        Lance les recherches RAG adaptées au mode et type de projet.
        Retourne un dict {poste: [hits]} avec prix nettoyés et formatés.
        """
        mode = self._detect_mode(project_description)
        print(f"   Mode détecté : {mode}")

        if mode == "renovation":
            postes  = self._detect_renovation_postes(project_description)
            queries = {k: v for k, v in QUERIES_RENOVATION.items() if k in postes}
            if not queries:
                queries = QUERIES_RENOVATION
        else:
            queries = _MODE_QUERIES.get(mode, QUERIES_CONSTRUCTION)

        # Ajouter requête escalier si multi-étages mentionné
        txt = project_description.lower()
        if any(k in txt for k in ["étage", "etage", "niveau", "escalier", "duplex", "triplex"]):
            if "escalier" not in queries:
                queries = {**queries, "escalier": "escalier béton marches volée prix construction Tunis"}

        results = {}
        for poste, query in queries.items():
            hits = self.vs.search(query, n_results=12)
            results[poste] = [
                self._format_hit(h)
                for h in hits
                if h["relevance_score"] > 0.18
            ]

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
            "price_fmt":     fmt_price(price),
            "price_min_fmt": fmt_price(price_min),
            "price_max_fmt": fmt_price(price_max),
            "unit":          unit,
            "price_display": self._display(price, price_min, price_max, unit),
            "category":      meta.get("category", ""),
            "relevance":     round(h["relevance_score"], 3),
        }

    def _clean(self, value) -> float | None:
        if value is None:
            return None
        try:
            v = float(value)
            return v if (0 < v < 150_000) else None
        except (ValueError, TypeError):
            return None

    def _display(self, price, p_min, p_max, unit) -> str:
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
        hits = self.vs.search(category, n_results=n, category_filter=category)
        return [self._format_hit(h) for h in hits]