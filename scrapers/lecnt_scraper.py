"""
lecnt_scraper.py — Scraper pour www.lecnt.com (Le CNT — La Maison du Bien-Vivre)
Site e-commerce tunisien avec catalogue structuré : faïence, carrelage, cuisine, salle de bain.

Structure observée (screenshot) :
  - URL catalogue : https://www.lecnt.com/60062-faience-et-sol-assorti
  - Sections : CUISINE / SALLE DE BAIN / TERRASSE & JARDIN / REVÊTEMENTS SOL ET MUR / BOIS & DÉRIVÉS / PORTE
  - Site PrestaShop-like avec navigation par catégorie
  - Numéro de catégorie dans l'URL (ex: 60062-)
"""
import requests
from bs4 import BeautifulSoup
from core.base_scraper import BaseMaterialScraper, TUNISIA_REGIONS
from typing import List, Dict, Any
from urllib.parse import urljoin
import logging
import re
import json
import time

logger = logging.getLogger(__name__)


class LeCNTScraper(BaseMaterialScraper):
    """
    Scraper dédié à lecnt.com — Faïence, carrelage, sol et mur, bois, portes.
    """

    BASE_URL = "https://www.lecnt.com"

    # Catégories pertinentes (matériaux de construction / revêtement)
    # IDs observés dans l'URL screenshot : 60062 = Faïence et Sol Assorti
    CATEGORY_URLS = [
        "/60062-faience-et-sol-assorti",              # Faïence & Sol
        "/revetements-sol-et-mur",                    # Revêtements sol et mur
        "/cuisine",                                    # Cuisine
        "/salle-de-bain",                             # Salle de bain
        "/bois-et-derives",                           # Bois & dérivés
        "/terrasse-et-jardin",                        # Terrasse & jardin
        "/porte",                                     # Portes
        "/meuble-d-interieur",                        # Mobilier intérieur
    ]

    def fetch_listing_pages(self) -> List[str]:
        """
        Génère les pages paginées pour chaque catégorie.
        Système de pagination : ?page=N ou /page-N
        """
        pages = []
        for cat in self.CATEGORY_URLS:
            pages.append(f"{self.BASE_URL}{cat}")
            for p in range(2, 6):
                pages.append(f"{self.BASE_URL}{cat}?page={p}")
        return pages

    def extract_listing_links(self, page_url: str) -> List[str]:
        """
        Extrait les liens produit depuis une page de catalogue lecnt.com.
        Cherche les liens vers les fiches produit individuelles.
        """
        links = []
        try:
            resp = requests.get(page_url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                return links

            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')

            seen = set()

            # Sélecteurs possibles pour les cartes produit
            selectors = [
                'article.product-miniature a',
                '.product-container a.product_img_link',
                'h3.product-title a',
                'h2.product-title a',
                '.products .product a',
                '.thumbnail-container a',
                'a.product-thumbnail',
            ]

            for sel in selectors:
                for a in soup.select(sel):
                    href = a.get('href', '')
                    if not href or href in seen:
                        continue
                    # Exclure liens de navigation/catégorie
                    if any(skip in href for skip in ['#', 'javascript:', 'mailto:', 'tel:']):
                        continue
                    full = urljoin(self.BASE_URL, href)
                    if self.BASE_URL in full and full != page_url:
                        seen.add(href)
                        links.append(full)

            time.sleep(0.3)

        except Exception as e:
            logger.error(f"[LeCNT] Erreur liens {page_url}: {e}")

        return list(set(links))

    def extract_listing_data(self, product_url: str) -> Dict[str, Any]:
        """
        Extrait les données d'une fiche produit lecnt.com.
        Priorité au JSON-LD, fallback HTML.
        """
        data: Dict[str, Any] = {'listing_url': product_url}
        try:
            resp = requests.get(product_url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                return self.normalize_data(data)

            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')
            full_text = soup.get_text(separator=' ')

            # ── JSON-LD ───────────────────────────────────────────────────
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    jdata = json.loads(script.string or '{}')
                    if isinstance(jdata, list):
                        jdata = next((x for x in jdata if x.get('@type') == 'Product'), jdata[0] if jdata else {})
                    if jdata.get('@type') == 'Product':
                        data['title'] = jdata.get('name', 'N/A')
                        offers = jdata.get('offers', {})
                        if isinstance(offers, list):
                            offers = offers[0]
                        data['price'] = self._clean_numeric(str(offers.get('price', '0')))
                        data['currency'] = offers.get('priceCurrency', 'TND')
                        data['brand'] = (
                            jdata['brand']['name']
                            if isinstance(jdata.get('brand'), dict)
                            else jdata.get('brand', '')
                        )
                        data['reference'] = jdata.get('sku', '')
                        data['description'] = jdata.get('description', '')
                        imgs = jdata.get('image', [])
                        data['image_urls'] = imgs if isinstance(imgs, list) else [imgs]
                        availability = offers.get('availability', '')
                        data['in_stock'] = 'InStock' in availability
                        break
                except Exception:
                    continue

            # ── Fallback HTML ─────────────────────────────────────────────

            # Titre
            if not data.get('title') or data['title'] == 'N/A':
                h1 = soup.find('h1')
                data['title'] = h1.text.strip() if h1 else 'N/A'

            # Prix
            if not data.get('price'):
                price_tag = (
                    soup.find('span', {'itemprop': 'price'}) or
                    soup.select_one('.price, .product-price, .current-price')
                )
                if price_tag:
                    raw = price_tag.get('content') or price_tag.text
                    data['price'] = self._clean_numeric(str(raw))
                if not data.get('price'):
                    pm = re.search(r'(\d[\d\s.,]*)\s*(?:dt|tnd|dinars|€)', full_text, re.I)
                    data['price'] = self._clean_numeric(pm.group(1)) if pm else 0.0

            data['currency'] = data.get('currency', 'TND')

            # Dimensions (faïence : souvent "30x60 cm", "60x60 cm"…)
            dim_match = re.search(r'(\d+)\s*[xX×]\s*(\d+)\s*(?:cm|mm)?', full_text)
            if dim_match:
                data['dimensions'] = f"{dim_match.group(1)}x{dim_match.group(2)} cm"
                # Calcul m² si dimensions trouvées
                w = float(dim_match.group(1)) / 100
                h = float(dim_match.group(2)) / 100
                data['tile_m2'] = round(w * h, 4)

            # Marque
            if not data.get('brand'):
                brand_tag = soup.select_one('.manufacturer a, .brand, [itemprop="brand"]')
                if brand_tag:
                    data['brand'] = brand_tag.text.strip()

            # Référence
            if not data.get('reference'):
                ref_tag = soup.select_one('.product-reference, [itemprop="sku"]')
                if ref_tag:
                    data['reference'] = ref_tag.text.replace('Réf.', '').replace('REF:', '').strip()

            # Disponibilité
            if 'in_stock' not in data:
                avail = soup.select_one('.availability, .product-availability, .in-stock')
                data['in_stock'] = True
                if avail:
                    txt = avail.text.lower()
                    data['in_stock'] = 'stock' in txt or 'disponible' in txt

            # Description
            if not data.get('description'):
                desc = soup.select_one(
                    '#product-description, .product-description, '
                    '.product-description-short, [itemprop="description"]'
                )
                data['description'] = desc.text.strip() if desc else ''

            # Images
            if not data.get('image_urls'):
                imgs = []
                for img in soup.select(
                    '.product-cover img, .images-container img, '
                    '.product-image img, .gallery img'
                ):
                    src = img.get('data-src') or img.get('src', '')
                    if src and any(e in src.lower() for e in ['.jpg', '.jpeg', '.png', '.webp']):
                        if 'logo' not in src.lower():
                            imgs.append(urljoin(product_url, src))
                data['image_urls'] = imgs[:8]

            # Catégorie depuis breadcrumb
            crumbs = soup.select('.breadcrumb li, .breadcrumb-item, nav[aria-label="breadcrumb"] span')
            if crumbs:
                data['subcategory'] = crumbs[-1].text.strip()

            # Métadonnées fixes
            data['supplier'] = 'Le CNT – La Maison du Bien-Vivre'
            data['city'] = 'Tunis'

        except Exception as e:
            logger.error(f"[LeCNT] Erreur données {product_url}: {e}")

        return self.normalize_data(data)