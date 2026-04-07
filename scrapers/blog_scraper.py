"""
blog_scraper.py — Scraper pour sites de type BLOG avec tableaux de prix matériaux.

Sites ciblés :
  1. limmobilier.tn — Article blog avec tableaux HTML de prix (ciment, fer, sable, etc.)

  2. sm-devis.tn — Site complet avec :
       • Estimations prix construction/rénovation m²
       • Guide des prix rénovation Tunisie (multi-articles)
       • Devis climatisation Tunisie
       • Tout article contenant un prix

Stratégie : crawler automatique du sitemap/menu + parser <table>, listes et
            texte libre. Ces sites ne sont PAS des e-commerces.
"""
import requests
from bs4 import BeautifulSoup
from core.base_scraper import BaseMaterialScraper, MATERIAL_CATEGORIES
from typing import List, Dict, Any, Set
from urllib.parse import urljoin, urlparse
import logging
import re
import datetime
import time

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Scraper limmobilier.tn — Article blog tableaux de prix
# ─────────────────────────────────────────────────────────────────────────────
class LimmobilierBlogScraper(BaseMaterialScraper):
    """
    Scrape l'article de blog limmobilier.tn qui liste les prix
    des matériaux de construction en Tunisie 2025.
    """

    ARTICLE_URLS = [
        "https://limmobilier.tn/article/25/prix-des-materiaux-de-construction-en-tunisie-2025-guide-complet.html",
    ]

    def fetch_listing_pages(self) -> List[str]:
        return self.ARTICLE_URLS

    def extract_listing_links(self, page_url: str) -> List[str]:
        return [page_url]

    def extract_listing_data(self, article_url: str) -> Dict[str, Any]:
        return {}

    def extract_all_from_article(self, article_url: str) -> List[Dict[str, Any]]:
        records = []
        try:
            resp = requests.get(article_url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                logger.error(f"[LimmobilierBlog] HTTP {resp.status_code} pour {article_url}")
                return records

            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')

            tables = soup.find_all('table')
            for table in tables:
                headers_row = table.find('tr')
                if not headers_row:
                    continue
                headers = [th.text.strip().lower() for th in headers_row.find_all(['th', 'td'])]
                col_map = self._map_columns(headers)
                for row in table.find_all('tr')[1:]:
                    cells = [td.text.strip() for td in row.find_all(['td', 'th'])]
                    if not cells or all(c == '' for c in cells):
                        continue
                    record = self._build_record_from_row(cells, col_map, article_url)
                    if record and record.get('title') and record.get('title') != 'N/A':
                        records.append(self.normalize_data(record))

            if not records:
                records = self._extract_from_text(soup, article_url)

            logger.info(f"[LimmobilierBlog] {len(records)} enregistrements extraits de {article_url}")
        except Exception as e:
            logger.error(f"[LimmobilierBlog] Erreur {article_url}: {e}")

        return records

    def _map_columns(self, headers: List[str]) -> Dict[str, int]:
        col_map = {}
        for i, h in enumerate(headers):
            if any(w in h for w in ['matériau', 'produit', 'article', 'désignation', 'nom']):
                col_map['title'] = i
            elif any(w in h for w in ['prix', 'price', 'tarif', 'coût']):
                col_map['price'] = i
            elif any(w in h for w in ['unité', 'unit', 'conditionnement']):
                col_map['unit'] = i
            elif any(w in h for w in ['marque', 'brand', 'fabricant']):
                col_map['brand'] = i
            elif any(w in h for w in ['catégorie', 'type', 'famille']):
                col_map['category'] = i
            elif any(w in h for w in ['note', 'remarque', 'description']):
                col_map['description'] = i
        return col_map

    def _build_record_from_row(self, cells: List[str], col_map: Dict[str, int], source_url: str) -> Dict[str, Any]:
        record: Dict[str, Any] = {
            'listing_url': source_url,
            'currency': 'TND',
            'city': 'Tunisie',
            'supplier': 'limmobilier.tn (source blog)',
            'in_stock': True,
        }
        try:
            title_idx = col_map.get('title', 0)
            if title_idx < len(cells):
                record['title'] = cells[title_idx]
            price_idx = col_map.get('price')
            if price_idx is not None and price_idx < len(cells):
                record['price'] = self._clean_numeric(cells[price_idx])
            else:
                for cell in cells:
                    pm = re.search(r'(\d[\d\s.,]*)\s*(?:dt|tnd|dinars)?', cell, re.I)
                    if pm:
                        val = self._clean_numeric(pm.group(1))
                        if 0.1 < val < 500_000:
                            record['price'] = val
                            break
            unit_idx = col_map.get('unit')
            if unit_idx is not None and unit_idx < len(cells):
                record['unit'] = cells[unit_idx]
            else:
                all_text = ' '.join(cells)
                for unit in ['kg', 'tonne', 'sac', 'm²', 'm³', 'ml', 'pièce', 'palette', 'botte', 'rouleau', 'l']:
                    if re.search(rf'\b{re.escape(unit)}\b', all_text, re.I):
                        record['unit'] = unit
                        break
            brand_idx = col_map.get('brand')
            if brand_idx is not None and brand_idx < len(cells):
                record['brand'] = cells[brand_idx]
            used = set(col_map.values())
            extras = [cells[i] for i in range(len(cells)) if i not in used and cells[i]]
            record['description'] = ' | '.join(extras)
        except Exception as e:
            logger.debug(f"Erreur ligne: {e}")
        return record

    def _extract_from_text(self, soup: BeautifulSoup, source_url: str) -> List[Dict[str, Any]]:
        records = []
        text = soup.get_text(separator='\n')
        pattern = re.compile(
            r'^[\-•*]?\s*'
            r'(?P<title>[A-Za-zÀ-ÿ\s\-/\'()+&]{3,60})'
            r'\s*[:]\s*'
            r'(?P<price>\d[\d\s.,]{0,10})'
            r'\s*(?:dt|tnd|dinars)?\s*'
            r'(?:/\s*(?P<unit>[a-zA-Zé²³µ]+))?',
            re.I | re.MULTILINE
        )
        for m in pattern.finditer(text):
            title = m.group('title').strip()
            price = self._clean_numeric(m.group('price'))
            unit = (m.group('unit') or '').strip()
            if not title or price <= 0 or price > 500_000:
                continue
            record = {
                'listing_url': source_url,
                'title': title,
                'price': price,
                'unit': unit or 'unité',
                'currency': 'TND',
                'city': 'Tunisie',
                'supplier': 'limmobilier.tn (source blog)',
                'in_stock': True,
                'description': '',
            }
            records.append(self.normalize_data(record))
        return records


# ─────────────────────────────────────────────────────────────────────────────
# Scraper sm-devis.tn — Scraper complet multi-sections
# ─────────────────────────────────────────────────────────────────────────────
class SmDevisScraper(BaseMaterialScraper):
    """
    Scraper complet pour sm-devis.tn.

    Sections couvertes :
      1. Prix estimatifs construction m² (maison, villa, appartement…)
      2. Guide des prix rénovation Tunisie (multi-articles : peinture, carrelage,
         plomberie, électricité, isolation, toiture…)
      3. Devis climatisation (split, gainable, multisplit…)
      4. Tout autre article contenant un prix TND

    Stratégie :
      - fetch_listing_pages() crawle le menu du site + sitemap pour collecter
        toutes les URLs pertinentes.
      - extract_all_from_article() parse <table>, listes <ul>/<ol>, paragraphes
        et fourchettes de prix pour chaque article trouvé.
    """

    BASE_URL = "https://www.sm-devis.tn"

    # ── URLs de départ garanties ───────────────────────────────────────────────
    SEED_URLS = [
        # Construction
        "/prix-estimatif-dun-construction-m2-en-tunis/",
        "/prix-construction-maison-tunisie/",
        "/cout-construction-villa-tunisie/",
        # Rénovation
        "/guide-des-prix-renovation-tunisie/",
        "/prix-renovation-appartement-tunisie/",
        "/prix-peinture-interieure-tunisie/",
        "/prix-carrelage-pose-tunisie/",
        "/prix-plomberie-tunisie/",
        "/prix-electricite-maison-tunisie/",
        "/prix-isolation-thermique-tunisie/",
        "/prix-toiture-tunisie/",
        "/prix-faux-plafond-tunisie/",
        # Climatisation
        "/prix-climatiseur-tunisie/",
        "/prix-climatisation-tunisie/",
        "/devis-climatisation-tunisie/",
        # Sections menu observées
        "/nos-prix-estimative-des-travaux-tunisie/",
        "/travaux-et-batiment-tunisie/",
        "/guide-des-prix-pour-travaux-renovation-tunis-2024/",
    ]

    # Mots-clés signalant qu'un article contient des prix
    PRICE_KEYWORDS = [
        'prix', 'tarif', 'coût', 'cout', 'estimation', 'devis',
        'dt/m', 'tnd', 'dinars', 'forfait', 'budget',
    ]

    # Catégories par sous-section SM Devis
    SECTION_CATEGORIES = {
        'construction':   ['construction', 'maison', 'villa', 'batiment', 'bâtiment', 'gros-oeuvre'],
        'renovation':     ['renovation', 'rénovation', 'refection', 'réfection', 'travaux', 'guide-des-prix'],
        'climatisation':  ['climatisation', 'climatiseur', 'clim', 'split'],
        'peinture':       ['peinture', 'enduit', 'ravalement'],
        'carrelage':      ['carrelage', 'faience', 'faïence', 'sol', 'revetement'],
        'plomberie':      ['plomberie', 'sanitaire', 'robinet', 'tuyau'],
        'electricite':    ['electricite', 'électricité', 'tableau', 'cable'],
        'isolation':      ['isolation', 'isolant', 'thermique'],
        'toiture':        ['toiture', 'charpente', 'etancheite'],
        'faux_plafond':   ['faux-plafond', 'plafond'],
    }

    def fetch_listing_pages(self) -> List[str]:
        """
        Collecte toutes les URLs d'articles SM Devis contenant des prix.
        Stratégie en 3 passes :
          1. URLs graines (SEED_URLS)
          2. Crawl du menu de navigation du site
          3. Crawl de la section "Guide des prix"
        """
        urls: Set[str] = set()

        # Passe 1 : URLs graines
        for path in self.SEED_URLS:
            urls.add(f"{self.BASE_URL}{path}")

        # Passe 2 : crawler le menu principal
        try:
            resp = requests.get(self.BASE_URL, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                nav_urls = self._extract_internal_links(soup, min_path_depth=1)
                urls.update(nav_urls)
                logger.info(f"[SmDevis] Menu → {len(nav_urls)} URLs trouvées")
        except Exception as e:
            logger.warning(f"[SmDevis] Impossible de crawler le menu : {e}")

        # Passe 3 : crawler les pages de section (guide rénovation, climatisation…)
        section_pages = [
            f"{self.BASE_URL}/guide-des-prix-pour-travaux-renovation-tunis-2024/",
            f"{self.BASE_URL}/nos-prix-estimative-des-travaux-tunisie/",
            f"{self.BASE_URL}/devis-climatisation-tunisie/",
        ]
        for section_url in section_pages:
            try:
                resp = requests.get(section_url, headers=self.headers, timeout=15)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    sub_urls = self._extract_internal_links(soup, min_path_depth=1)
                    urls.update(sub_urls)
                    logger.info(f"[SmDevis] Section {section_url} → {len(sub_urls)} URLs")
                time.sleep(0.4)
            except Exception as e:
                logger.warning(f"[SmDevis] Section {section_url} inaccessible : {e}")

        # Filtrer : garder uniquement les URLs qui semblent être des articles
        article_urls = self._filter_article_urls(urls)
        logger.info(f"[SmDevis] Total articles à scraper : {len(article_urls)}")
        return sorted(article_urls)

    def extract_listing_links(self, page_url: str) -> List[str]:
        """Non utilisé pour les blogs — fetch_listing_pages() fait déjà le crawl."""
        return [page_url]

    def extract_listing_data(self, article_url: str) -> Dict[str, Any]:
        """Non utilisé directement — voir extract_all_from_article()."""
        return {}

    def extract_all_from_article(self, article_url: str) -> List[Dict[str, Any]]:
        """
        Point d'entrée principal : extrait TOUS les prix d'un article SM Devis.
        Combine 4 stratégies d'extraction :
          1. Tableaux HTML (<table>)
          2. Listes structurées (<ul>/<ol> avec prix)
          3. Paragraphes avec pattern "Prestation : XX DT/unité"
          4. Fourchettes de prix "entre X DT et Y DT"
        """
        records = []
        category = self._category_from_url(article_url)

        try:
            resp = requests.get(article_url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"[SmDevis] HTTP {resp.status_code} → {article_url}")
                return records

            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Titre de l'article (contexte pour les enregistrements sans titre propre)
            article_title = ''
            h1 = soup.find('h1')
            if h1:
                article_title = h1.text.strip()

            full_text = soup.get_text(separator='\n')

            # ── 1. Tableaux HTML ──────────────────────────────────────────
            table_records = self._parse_tables(soup, article_url, article_title, category)
            records.extend(table_records)

            # ── 2. Listes <ul>/<ol> avec prix ────────────────────────────
            list_records = self._parse_lists(soup, article_url, article_title, category)
            records.extend(list_records)

            # ── 3. Paragraphes "Prestation : XX DT / unité" ───────────────
            para_records = self._parse_price_paragraphs(full_text, article_url, article_title, category)
            records.extend(para_records)

            # ── 4. Fourchettes de prix ────────────────────────────────────
            range_records = self._parse_price_ranges(full_text, article_url, article_title, category)
            records.extend(range_records)

            # Dédupliquer par hash
            seen_hashes: Set[str] = set()
            unique = []
            for r in records:
                h = r.get('data_hash', '')
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    unique.append(r)
            records = unique

            logger.info(f"[SmDevis] {len(records)} enregistrements ← {article_url}")

        except Exception as e:
            logger.error(f"[SmDevis] Erreur {article_url}: {e}")

        return records

    # ── Extraction : tableaux ─────────────────────────────────────────────────

    def _parse_tables(
        self, soup: BeautifulSoup, url: str, article_title: str, category: str
    ) -> List[Dict[str, Any]]:
        records = []
        for table in soup.find_all('table'):
            # Récupérer les en-têtes
            header_row = table.find('tr')
            if not header_row:
                continue
            raw_headers = [th.text.strip() for th in header_row.find_all(['th', 'td'])]
            col_map = self._map_table_columns(raw_headers)

            for row in table.find_all('tr')[1:]:
                cells = [td.text.strip() for td in row.find_all(['td', 'th'])]
                if not cells or all(c == '' for c in cells):
                    continue
                record = self._row_to_record(cells, col_map, url, article_title, category)
                if record:
                    records.append(self.normalize_data(record))
        return records

    def _map_table_columns(self, raw_headers: List[str]) -> Dict[str, int]:
        """Mappe les en-têtes de tableau vers les champs du modèle."""
        col_map: Dict[str, int] = {}
        for i, h in enumerate(raw_headers):
            hl = h.lower()
            if any(w in hl for w in ['prestation', 'travaux', 'désignation', 'désig', 'poste',
                                      'type', 'nature', 'matériau', 'produit', 'article', 'nom']):
                col_map.setdefault('title', i)
            elif any(w in hl for w in ['prix min', 'minimum', 'min']):
                col_map.setdefault('price_min', i)
            elif any(w in hl for w in ['prix max', 'maximum', 'max']):
                col_map.setdefault('price_max', i)
            elif any(w in hl for w in ['prix moyen', 'moyen', 'moyenne']):
                col_map.setdefault('price_avg', i)
            elif any(w in hl for w in ['prix', 'price', 'tarif', 'coût', 'cout', 'montant']):
                col_map.setdefault('price', i)
            elif any(w in hl for w in ['unité', 'unit', 'conditionnement']):
                col_map.setdefault('unit', i)
            elif any(w in hl for w in ['note', 'remarque', 'détail', 'description']):
                col_map.setdefault('description', i)
        return col_map

    def _row_to_record(
        self, cells: List[str], col_map: Dict[str, int],
        url: str, article_title: str, category: str
    ) -> Dict[str, Any]:
        """Construit un enregistrement depuis une ligne de tableau."""
        record: Dict[str, Any] = {
            'listing_url': url,
            'currency': 'TND',
            'city': 'Tunis',
            'supplier': 'SM Devis (source blog)',
            'in_stock': True,
            'category': category,
        }

        # Titre
        title_idx = col_map.get('title', 0)
        record['title'] = cells[title_idx] if title_idx < len(cells) else article_title
        if not record['title']:
            record['title'] = article_title or 'N/A'

        # Prix min / max / moyen / unique
        for field in ('price_min', 'price_max', 'price_avg', 'price'):
            idx = col_map.get(field)
            if idx is not None and idx < len(cells):
                val = self._clean_numeric(cells[idx])
                if val > 0:
                    if field == 'price_avg':
                        record['price'] = val
                    else:
                        record[field] = val

        # Si on a min+max mais pas price, calculer la moyenne
        if not record.get('price') and record.get('price_min') and record.get('price_max'):
            record['price'] = round(
                (record['price_min'] + record['price_max']) / 2, 2
            )

        # Fallback : chercher un prix dans n'importe quelle cellule
        if not record.get('price'):
            for cell in cells:
                pm = re.search(r'(\d[\d\s.,]+)', cell)
                if pm:
                    val = self._clean_numeric(pm.group(1))
                    if 10 < val < 500_000:
                        record['price'] = val
                        break

        if not record.get('price'):
            return {}  # Pas de prix → on ignore

        # Unité
        unit_idx = col_map.get('unit')
        if unit_idx is not None and unit_idx < len(cells):
            record['unit'] = cells[unit_idx]
        else:
            record['unit'] = self._detect_unit_from_cells(cells)

        # Description
        desc_idx = col_map.get('description')
        if desc_idx is not None and desc_idx < len(cells):
            record['description'] = cells[desc_idx]
        else:
            used = set(col_map.values())
            extras = [cells[i] for i in range(len(cells)) if i not in used and cells[i]]
            record['description'] = ' | '.join(extras[:4])

        return record

    # ── Extraction : listes <ul>/<ol> ─────────────────────────────────────────

    def _parse_lists(
        self, soup: BeautifulSoup, url: str, article_title: str, category: str
    ) -> List[Dict[str, Any]]:
        """
        Parse les listes HTML.
        Exemple : <li>Peinture intérieure : 15 DT/m²</li>
        """
        records = []
        # Pattern : "Texte descriptif : XX DT / unité"
        item_pattern = re.compile(
            r'^(?P<title>[A-Za-zÀ-ÿ][^:]{2,80})'
            r'\s*:\s*'
            r'(?:(?:entre|de)\s+)?'
            r'(?P<price1>\d[\d\s.,]*)\s*(?:dt|tnd)?\s*'
            r'(?:(?:à|et|-)\s*(?P<price2>\d[\d\s.,]*)\s*(?:dt|tnd)?)?\s*'
            r'(?:[/]\s*(?P<unit>[A-Za-zé²³µ²]+))?',
            re.I
        )
        for li in soup.find_all('li'):
            text = li.get_text(' ', strip=True)
            # Vérifier qu'il y a un prix
            if not re.search(r'\d', text):
                continue
            m = item_pattern.match(text)
            if not m:
                continue
            title = m.group('title').strip()
            p1 = self._clean_numeric(m.group('price1') or '0')
            p2 = self._clean_numeric(m.group('price2') or '0') if m.group('price2') else 0.0
            unit = (m.group('unit') or '').strip()

            if p1 <= 0 or p1 > 500_000:
                continue

            record: Dict[str, Any] = {
                'listing_url': url,
                'title': title,
                'currency': 'TND',
                'city': 'Tunis',
                'supplier': 'SM Devis (source blog)',
                'in_stock': True,
                'category': category,
                'unit': unit or self._detect_unit_from_cells([text]),
                'description': text,
            }
            if p2 > p1:
                record['price_min'] = p1
                record['price_max'] = p2
                record['price'] = round((p1 + p2) / 2, 2)
                record['description'] = f"Fourchette : {p1} – {p2} DT/{unit or 'unité'}"
            else:
                record['price'] = p1

            records.append(self.normalize_data(record))
        return records

    # ── Extraction : paragraphes ──────────────────────────────────────────────

    def _parse_price_paragraphs(
        self, full_text: str, url: str, article_title: str, category: str
    ) -> List[Dict[str, Any]]:
        """
        Extrait les lignes du type :
          "Pose carrelage : 25 DT/m²"
          "- Installation split 9000 BTU : 120 DT"
          "• Main d'œuvre peinture : 12 à 18 DT/m²"
        """
        records = []
        pattern = re.compile(
            r'^[\-•*►▶→]?\s*'
            r'(?P<title>[A-Za-zÀ-ÿ][^:\n]{2,80})'
            r'\s*[:|–]\s*'
            r'(?:(?:environ|de|entre|à partir de)\s+)?'
            r'(?P<price1>\d[\d\s.,]{0,12})'
            r'\s*(?:dt|tnd|dinars)?\s*'
            r'(?:(?:à|et|-)\s*(?P<price2>\d[\d\s.,]{0,12})\s*(?:dt|tnd|dinars)?)?\s*'
            r'(?:[/]\s*(?P<unit>[A-Za-zé²³µ²]{1,10}))?',
            re.I | re.MULTILINE
        )
        for m in pattern.finditer(full_text):
            title = m.group('title').strip()
            # Ignorer les titres trop génériques
            if len(title) < 4 or title.lower() in ('note', 'source', 'exemple'):
                continue

            p1 = self._clean_numeric(m.group('price1') or '0')
            p2_raw = m.group('price2')
            p2 = self._clean_numeric(p2_raw) if p2_raw else 0.0
            unit = (m.group('unit') or '').strip()

            if p1 <= 0 or p1 > 500_000:
                continue

            record: Dict[str, Any] = {
                'listing_url': url,
                'title': title,
                'currency': 'TND',
                'city': 'Tunis',
                'supplier': 'SM Devis (source blog)',
                'in_stock': True,
                'category': category,
                'unit': unit or 'unité',
                'description': m.group(0).strip(),
            }
            if p2 > p1:
                record['price_min'] = p1
                record['price_max'] = p2
                record['price'] = round((p1 + p2) / 2, 2)
            else:
                record['price'] = p1

            records.append(self.normalize_data(record))
        return records

    # ── Extraction : fourchettes ──────────────────────────────────────────────

    def _parse_price_ranges(
        self, full_text: str, url: str, article_title: str, category: str
    ) -> List[Dict[str, Any]]:
        """
        Extrait les fourchettes de prix du type :
          "entre 1 200 DT/m² et 4 500 DT/m²"
          "de 800 à 2000 DT/m²"
          "8 000 DT à 25 000 DT"
          "5 000 dt/BTU"
        """
        records = []
        range_pattern = re.compile(
            r'(?:entre\s+|de\s+)?'
            r'(?P<p1>\d[\d\s.,]{0,10})\s*(?:dt|tnd)?\s*(?:[/]\s*(?P<u1>[A-Za-zé²³µ²]{1,6}))?\s*'
            r'(?:à|et|-)\s*'
            r'(?P<p2>\d[\d\s.,]{0,10})\s*(?:dt|tnd)?\s*(?:[/]\s*(?P<u2>[A-Za-zé²³µ²]{1,6}))?',
            re.I
        )
        for m in range_pattern.finditer(full_text):
            p1 = self._clean_numeric(m.group('p1'))
            p2 = self._clean_numeric(m.group('p2'))
            unit = (m.group('u1') or m.group('u2') or '').strip()

            if p1 <= 0 or p2 <= 0 or p1 >= p2:
                continue
            if p2 > 2_000_000:   # Ignorer les valeurs aberrantes
                continue

            # Titre = contexte avant la fourchette
            start = max(0, m.start() - 120)
            context_lines = full_text[start:m.start()].strip().split('\n')
            title = context_lines[-1].strip()
            # Nettoyer le titre (enlever ponctuation finale)
            title = re.sub(r'[.,:;!?]+$', '', title).strip()
            if not title or len(title) < 4:
                title = article_title or 'Estimation SM Devis'

            record: Dict[str, Any] = {
                'listing_url': url,
                'title': title[:120],
                'price': round((p1 + p2) / 2, 2),
                'price_min': p1,
                'price_max': p2,
                'unit': unit or 'unité',
                'currency': 'TND',
                'city': 'Tunis',
                'category': category,
                'supplier': 'SM Devis (source blog)',
                'in_stock': True,
                'description': f"Fourchette estimée : {p1} – {p2} DT/{unit or 'unité'}",
            }
            records.append(self.normalize_data(record))
        return records

    # ── Helpers crawl ─────────────────────────────────────────────────────────

    def _extract_internal_links(
        self, soup: BeautifulSoup, min_path_depth: int = 1
    ) -> Set[str]:
        """Extrait tous les liens internes sm-devis.tn depuis une page."""
        urls: Set[str] = set()
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if not href or href.startswith('#') or 'javascript:' in href:
                continue
            full = urljoin(self.BASE_URL, href)
            parsed = urlparse(full)
            # Garder uniquement les URLs du domaine sm-devis.tn
            if 'sm-devis.tn' not in parsed.netloc:
                continue
            # Profondeur minimale (évite d'indexer la homepage seule)
            path_parts = [p for p in parsed.path.split('/') if p]
            if len(path_parts) < min_path_depth:
                continue
            # Exclure les ressources statiques
            if re.search(r'\.(jpg|jpeg|png|gif|pdf|zip|css|js|xml)$', parsed.path, re.I):
                continue
            urls.add(full.rstrip('/') + '/')
        return urls

    def _filter_article_urls(self, urls: Set[str]) -> List[str]:
        """
        Filtre pour ne garder que les URLs qui ressemblent à des articles
        contenant des prix (based sur mots-clés dans le path).
        """
        kept = []
        price_path_kw = [
            'prix', 'tarif', 'cout', 'coût', 'devis', 'estimation',
            'guide', 'travaux', 'renovation', 'construction', 'batiment',
            'climatisation', 'climatiseur', 'peinture', 'carrelage',
            'plomberie', 'electricite', 'isolation', 'toiture', 'plafond',
            'menuiserie', 'maconnerie', 'enduit', 'chape', 'dalle',
        ]
        for url in urls:
            path = urlparse(url).path.lower()
            if any(kw in path for kw in price_path_kw):
                kept.append(url)
        # Toujours inclure les seeds même si path ne matche pas
        for path in self.SEED_URLS:
            full = f"{self.BASE_URL}{path}"
            if full not in kept:
                kept.append(full)
        return list(set(kept))

    def _category_from_url(self, url: str) -> str:
        """Détecte la catégorie métier depuis l'URL de l'article."""
        url_lower = url.lower()
        for cat, keywords in self.SECTION_CATEGORIES.items():
            if any(kw in url_lower for kw in keywords):
                return cat
        return 'estimation_construction'

    def _detect_unit_from_cells(self, cells: List[str]) -> str:
        """Détecte l'unité de mesure dans une liste de cellules texte."""
        all_text = ' '.join(cells).lower()
        unit_map = [
            (r'\bm²\b|m2\b|/m2|/m²',          'm²'),
            (r'\bm³\b|m3\b|/m3|/m³',          'm³'),
            (r'\bml\b|mètre\s+linéaire',       'ml'),
            (r'\bkg\b',                         'kg'),
            (r'\btonne\b',                      'tonne'),
            (r'\bsac\b',                        'sac'),
            (r'\bpièce\b|\bpiece\b|\bunit',    'pièce'),
            (r'\bpalette\b',                    'palette'),
            (r'\bbtu\b',                        'BTU'),
            (r'\bforfait\b',                    'forfait'),
            (r'\bjour\b|\bj\b',               'jour'),
            (r'\bheure\b|\bh\b',              'heure'),
        ]
        for pattern, unit in unit_map:
            if re.search(pattern, all_text, re.I):
                return unit
        return 'unité'