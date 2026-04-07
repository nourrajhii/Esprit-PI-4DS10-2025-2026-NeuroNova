"""
comaf_scraper.py — Scraper pour www.comaf.tn
Classes CSS confirmees par debug :
  - .result-price-list        → "273,510 DT   TTC / KIT"
  - .product-price-and-shipping.product_price → meme contenu
  - .old-price_res.product-price → ancien prix (a ignorer)
"""
import requests
from bs4 import BeautifulSoup
from core.base_scraper import BaseMaterialScraper
from typing import List, Dict, Any
from urllib.parse import urljoin
import logging
import re
import time
import json

logger = logging.getLogger(__name__)


class ComafScraper(BaseMaterialScraper):

    BASE_URL = "https://www.comaf.tn"

    CATEGORY_URLS = [
        "/73-ciment-et-produits-en-beton.html",
        "/materiaux-de-construction.html",
        "/carrelage-et-faience.html",
        "/peinture-et-revetement.html",
        "/fer-et-acier.html",
        "/bois-et-derives.html",
        "/plomberie.html",
        "/electricite.html",
        "/isolation.html",
        "/toiture.html",
    ]

    def fetch_listing_pages(self) -> List[str]:
        pages = []
        for cat in self.CATEGORY_URLS:
            pages.append(f"{self.BASE_URL}{cat}")
            for p in range(2, 6):
                pages.append(f"{self.BASE_URL}{cat}?p={p}")
        return pages

    def extract_listing_links(self, page_url: str) -> List[str]:
        links = []
        try:
            resp = requests.get(page_url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                return links

            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')

            seen = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if (href and
                    'comaf.tn' in href and
                    '.html' in href and
                    href not in seen and
                    # Exclure pages categorie (URL courte type /70- /73-)
                    not re.search(r'comaf\.tn/\d+-[^/]+\.html$', href) or
                    # Garder les produits avec sous-dossier ex: /etaiement/3110-...html
                    re.search(r'comaf\.tn/[^/]+/\d+-', href)):
                    seen.add(href)
                    links.append(href)

            time.sleep(0.3)

        except Exception as e:
            logger.error(f"[Comaf] Erreur liens {page_url}: {e}")

        return list(set(links))

    def _parse_price_from_text(self, text: str) -> tuple:
        """
        Parse un texte comme "273,510 DT   TTC / KIT"
        Retourne (prix, unite)
        ex: (273.51, "KIT")
        """
        if not text:
            return 0.0, "unite"

        # Extraire l'unite (apres le /)
        unit = "unite"
        unit_match = re.search(r'/\s*([A-Z0-9\-²³µ]+)', text, re.I)
        if unit_match:
            unit = unit_match.group(1).strip()

        # Extraire le prix (premier nombre avant DT)
        # Format comaf: "273,510 DT" ou "1 666,000 DT"
        price_match = re.search(r'([\d\s]+,\d+|[\d]+\.[\d]+|\d+)\s*DT', text, re.I)
        if price_match:
            raw = price_match.group(1).replace(' ', '')  # supprimer espaces "1 666" -> "1666"
            price = self._clean_numeric(raw)
            return price, unit

        return 0.0, unit

    def extract_listing_data(self, product_url: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {'listing_url': product_url}
        try:
            resp = requests.get(product_url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                return self.normalize_data(data)

            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')

            # ── Titre ─────────────────────────────────────────────────────
            h1 = soup.find('h1', {'itemprop': 'name'}) or soup.find('h1')
            data['title'] = h1.text.strip() if h1 else 'N/A'

            # ── Prix : sélecteur confirme par debug ───────────────────────
            # Chercher .result-price-list en EXCLUANT .old-price_res
            # Structure : <div class="result-price-list">273,510 DT TTC / KIT</div>
            price = 0.0
            unit = "unite"

            # Priorite 1 : .result-price-list (prix actuel sans ancien prix)
            result_price_divs = soup.select('.result-price-list')
            for div in result_price_divs:
                # S'assurer que ce n'est pas un ancien prix
                if 'old-price' not in ' '.join(div.get('class', [])):
                    text = div.text.strip()
                    if text and 'DT' in text.upper():
                        price, unit = self._parse_price_from_text(text)
                        if price > 0:
                            break

            # Priorite 2 : .product-price-and-shipping.product_price
            if price == 0.0:
                price_divs = soup.select('.product-price-and-shipping.product_price')
                for div in price_divs:
                    text = div.text.strip()
                    if text and 'DT' in text.upper():
                        price, unit = self._parse_price_from_text(text)
                        if price > 0:
                            break

            # Priorite 3 : regex sur tout le texte
            if price == 0.0:
                full_text = soup.get_text(separator=' ')
                match = re.search(r'([\d][\d\s]*,\d+|[\d]+\.[\d]+)\s*DT', full_text, re.I)
                if match:
                    raw = match.group(1).replace(' ', '')
                    price = self._clean_numeric(raw)

            data['price'] = price
            data['unit'] = unit
            data['currency'] = 'TND'

            # ── Marque ────────────────────────────────────────────────────
            brand_tag = (
                soup.find(itemprop='brand') or
                soup.select_one('.manufacturer-name, .brand a, .product-manufacturer')
            )
            if brand_tag:
                data['brand'] = brand_tag.text.strip()

            # ── Reference ─────────────────────────────────────────────────
            ref_tag = soup.select_one('.product-reference span, [itemprop="sku"]')
            if ref_tag:
                data['reference'] = ref_tag.text.strip()

            # ── Disponibilite ─────────────────────────────────────────────
            stock_tag = soup.select_one('.availability span, .product-availability')
            data['in_stock'] = True
            if stock_tag:
                data['in_stock'] = 'stock' in stock_tag.text.lower() or 'disponible' in stock_tag.text.lower()

            # ── Description ───────────────────────────────────────────────
            desc = soup.select_one(
                '#product-description-short, .product-description, '
                '[itemprop="description"], .rte'
            )
            data['description'] = desc.text.strip() if desc else ''

            # ── Images ────────────────────────────────────────────────────
            imgs = []
            for img in soup.select('.product-cover img, #product-images-large img, .slick-slide img'):
                src = img.get('data-src') or img.get('src', '')
                if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    imgs.append(urljoin(product_url, src))
            data['image_urls'] = imgs[:8]

            # ── Sous-categorie depuis breadcrumb ──────────────────────────
            breadcrumb = soup.select('.breadcrumb li')
            if len(breadcrumb) >= 2:
                data['subcategory'] = breadcrumb[-1].text.strip()

            data['city'] = 'Tunisie'
            data['supplier'] = 'COMAF - Comptoir Africain'

            logger.info(f"[Comaf] {data['title'][:45]} → {data['price']} TND / {data['unit']}")

        except Exception as e:
            logger.error(f"[Comaf] Erreur {product_url}: {e}")

        return self.normalize_data(data)