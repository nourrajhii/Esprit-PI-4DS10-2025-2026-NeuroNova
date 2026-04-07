from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import hashlib
import datetime
import logging
import re

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Catégories de matériaux de construction tunisiens
# ─────────────────────────────────────────────────────────────────────────────
MATERIAL_CATEGORIES = {
    "ciment": ["ciment", "cement", "portland", "colle ciment"],
    "sable": ["sable", "gravier", "granu", "agrégat", "ballast"],
    "fer": ["fer", "acier", "rond à béton", "armature", "ferraille", "HA", "treillis"],
    "brique": ["brique", "bloc", "parpaing", "hourdis", "tuile"],
    "bois": ["bois", "coffrage", "contreplaqué", "madrier", "planche"],
    "peinture": ["peinture", "enduit", "ravalement", "badigeon"],
    "carrelage": ["carrelage", "faïence", "marbre", "granit", "mosaïque"],
    "isolation": ["isolant", "laine de roche", "polystyrène", "polyuréthane"],
    "plomberie": ["tuyau", "pvc", "robinet", "sanitaire", "plomberie"],
    "electricite": ["câble", "fil électrique", "tableau", "gaine", "disjoncteur"],
    "porte_fenetre": ["porte", "fenêtre", "aluminium", "menuiserie", "volet"],
    "toiture": ["tuile", "zinc", "tôle", "toiture", "charpente", "étanchéité"],
    "beton": ["béton", "mortier", "chape", "dallage"],
    "echafaudage": ["échafaudage", "étai", "coffrage"],
}

# Unités de mesure fréquentes pour les matériaux
MATERIAL_UNITS = ["kg", "tonne", "t", "sac", "m²", "m³", "ml", "unité", "pièce", "palette", "botte", "rouleau"]

# Villes/régions de Tunisie
TUNISIA_REGIONS = [
    "Tunis", "Ariana", "Ben Arous", "Manouba", "Nabeul", "Zaghouan",
    "Bizerte", "Béja", "Jendouba", "Kef", "Siliana", "Sousse",
    "Monastir", "Mahdia", "Sfax", "Kairouan", "Kasserine", "Sidi Bouzid",
    "Gabès", "Medenine", "Tataouine", "Gafsa", "Tozeur", "Kébili"
]


class BaseMaterialScraper(ABC):
    """
    Classe de base pour les scrapers de matériaux de construction.
    Adaptée depuis BaseScraper immobilier.
    """

    def __init__(self, website_config: Dict[str, Any]):
        self.config = website_config
        self.base_url = website_config.get('base_url', '')
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'fr-FR,fr;q=0.9,ar;q=0.8,en;q=0.7'
        }

    # ── méthodes abstraites ───────────────────────────────────────────────────

    @abstractmethod
    def fetch_listing_pages(self) -> List[str]:
        """Retourne les URLs des pages de catalogue/catégories."""
        pass

    @abstractmethod
    def extract_listing_links(self, page_url: str) -> List[str]:
        """Extrait les liens vers les fiches produit depuis une page catalogue."""
        pass

    @abstractmethod
    def extract_listing_data(self, product_url: str) -> Dict[str, Any]:
        """Extrait les données d'une fiche produit (prix, unité, catégorie…)."""
        pass

    # ── normalisation ─────────────────────────────────────────────────────────

    def normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalise les champs numériques, détecte la catégorie et calcule le hash.
        """
        # Prix
        if 'price' in data and data['price']:
            data['price'] = self._clean_numeric(str(data['price']))

        # Prix par unité (facultatif mais utile pour comparer)
        if 'price_per_unit' in data and data['price_per_unit']:
            data['price_per_unit'] = self._clean_numeric(str(data['price_per_unit']))

        # Quantité
        if 'quantity' in data and data['quantity']:
            data['quantity'] = self._clean_numeric(str(data['quantity']))

        # Détection automatique de la catégorie si absente
        if not data.get('category'):
            data['category'] = self._detect_category(
                data.get('title', '') + ' ' + data.get('description', '')
            )

        # Détection de l'unité si absente
        if not data.get('unit'):
            data['unit'] = self._detect_unit(
                data.get('title', '') + ' ' + data.get('description', '')
            )

        data['currency'] = data.get('currency', 'TND')
        data['scraped_at'] = datetime.datetime.utcnow()
        data['data_hash'] = self.generate_hash(data)
        return data

    # ── helpers ───────────────────────────────────────────────────────────────

    def _clean_numeric(self, val: str) -> float:
        try:
            cleaned = re.sub(r'[^\d.]', '', val.replace(',', '.'))
            return float(cleaned) if cleaned else 0.0
        except Exception:
            return 0.0

    def _detect_category(self, text: str) -> str:
        """Détecte la catégorie du matériau depuis le texte."""
        text_lower = text.lower()
        for category, keywords in MATERIAL_CATEGORIES.items():
            if any(kw.lower() in text_lower for kw in keywords):
                return category
        return "autre"

    def _detect_unit(self, text: str) -> str:
        """Détecte l'unité de mesure depuis le texte."""
        text_lower = text.lower()
        for unit in MATERIAL_UNITS:
            # Cherche l'unité précédée ou suivie d'un chiffre
            if re.search(rf'\d\s*{re.escape(unit)}|{re.escape(unit)}\b', text_lower):
                return unit
        return "unité"

    def generate_hash(self, data: Dict[str, Any]) -> str:
        hash_str = (
            f"{data.get('title', '')}|"
            f"{data.get('price', 0)}|"
            f"{data.get('unit', '')}|"
            f"{data.get('listing_url', '')}"
        )
        return hashlib.md5(hash_str.encode()).hexdigest()