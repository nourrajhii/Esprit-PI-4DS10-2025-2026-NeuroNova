import requests
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from urllib.parse import urljoin, urlparse, quote, unquote
from typing import List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)

class GenericStaticScraper(BaseScraper):
    """
    A powerful generic scraper for static websites using BS4.
    """
    def fetch_listing_pages(self) -> List[str]:
        """
        Attempts to find listing pages by:
        1. Checking for Sitemaps (High quality).
        2. Scanning the homepage for keywords like 'Vente', 'Location', 'Achat'.
        3. Using guessed patterns.
        """
        found_pages = set()
        
        # 1. Check for Sitemaps (High quality)
        sitemap_pages = self.fetch_sitemaps()
        found_pages.update(sitemap_pages)

        # 2. Homepage scanning (Fallback)
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=15, allow_redirects=True)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                
                # Keywords that usually lead to listing pages
                cat_keywords = ["vente", "location", "achat", "recherche", "immobilier", "bien", "propriete"]
                
                for a in links:
                    text = a.text.lower()
                    href = a['href']
                    if any(kw in text for kw in cat_keywords) or any(kw in href.lower() for kw in cat_keywords):
                        full_url = urljoin(self.base_url, href)
                        # Avoid social media or external links
                        base_domain = urlparse(self.base_url).netloc.replace('www.', '')
                        link_domain = urlparse(full_url).netloc.replace('www.', '')
                        if link_domain == base_domain:
                            found_pages.add(full_url)
        except Exception as e:
            logger.error(f"Error scanning homepage of {self.base_url}: {e}")

        # 3. Add some guessed patterns as fallback if nothing found
        if not found_pages:
            for guess in ["/recherche", "/annonces", "/proprietes", "/achat", "/location"]:
                found_pages.add(urljoin(self.base_url, guess))

        return list(found_pages)[:15] # Increase slightly for more coverage

    def fetch_sitemaps(self) -> List[str]:
        """Checks for sitemap.xml and extracts potential listing category URLs."""
        sitemap_locations = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-listings.xml"]
        discovered = set()
        
        for loc in sitemap_locations:
            try:
                sitemap_url = urljoin(self.base_url, loc)
                res = requests.get(sitemap_url, headers=self.headers, timeout=10)
                if res.status_code == 200:
                    # Very basic XML parsing via regex for speed/reliability
                    urls = re.findall(r'<loc>(.*?)</loc>', res.text)
                    for u in urls:
                        # Only keep URLs that look like listing categories
                        if any(kw in u.lower() for kw in ["vente", "location", "achat", "listing", "immobilier", "bien"]):
                            discovered.add(u)
                        # If sitemap index, we could recurse, but keep simple for now
            except:
                continue
        return list(discovered)

    def extract_listing_links(self, page_url: str) -> List[str]:
        links = []
        try:
            response = requests.get(page_url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                # Use apparent encoding to avoid UTF-8 errors on non-standard sites
                response.encoding = response.apparent_encoding
                soup = BeautifulSoup(response.text, 'html.parser')
                # Grab all links and filter by detected patterns
                all_links = [a.get('href', '') for a in soup.find_all('a', href=True)]
                patterns = self.config.get('listing_patterns', []) or ["/annonce", "/vente", "/achat", "/bien", "/propriete", "/detail", "/property", "/produit", "/a/"]
                
                base_domain = urlparse(self.base_url).netloc.replace('www.', '')
                for link in all_links:
                    try:
                        # Safety: Encode URL if it contains special chars (Tayara bug)
                        safe_link = quote(link, safe='/:?=&') if not link.startswith('http') else link
                        full_link = urljoin(self.base_url, safe_link)
                        
                        if any(p in full_link.lower() for p in patterns):
                            link_domain = urlparse(full_link).netloc.replace('www.', '')
                            if link_domain == base_domain:
                                if full_link not in links:
                                    links.append(full_link)
                    except:
                        continue
        except Exception as e:
            logger.error(f"Error links {page_url}: {e}")
        return links

    def extract_listing_data(self, property_url: str) -> Dict[str, Any]:
        data = {'listing_url': property_url}
        try:
            response = requests.get(property_url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Heuristic Extraction
                data['title'] = soup.find('h1').text.strip() if soup.find('h1') else "N/A"
                
                # Improved Price search: Look for price-like numbers
                # Stricter: avoid very long numbers (phone numbers) and very small (1.0)
                price_match = re.search(r"(?:prix|price|montant|somme)?[:\s]*(\d[\d\s.,]{2,12})\s*(?:dt|tnd|dinars|€|\$)", soup.get_text(), re.I)
                raw_price = price_match.group(1) if price_match else "0"
                cleaned_price = self._clean_numeric(raw_price)
                
                # Filter out suspicious prices (e.g., phone numbers or placeholders)
                if cleaned_price > 10000000 or cleaned_price <= 1.0:
                    data['price'] = 0
                else:
                    data['price'] = cleaned_price
                data['currency'] = "TND"
                
                # Location (Cities/Regions)
                from discovery.explorer import TUNISIA_REGIONS
                text = soup.get_text()
                for region in TUNISIA_REGIONS:
                    if region.lower() in text.lower():
                        data['city'] = region.capitalize()
                        break
                
                # Characteristics (Surface, Rooms)
                all_text = soup.get_text()
                surf_match = re.search(r"(\d+)\s*m²", all_text, re.I)
                data['surface_m2'] = surf_match.group(1) if surf_match else 0
                
                room_match = re.search(r"(\d+)\s*(chambres|pièces|rooms)", all_text, re.I)
                data['rooms'] = room_match.group(1) if room_match else 0
                
                # Images - More aggressive
                img_tags = soup.find_all('img', src=True)
                data['image_urls'] = []
                for img in img_tags:
                    src = img['src']
                    if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and "logo" not in src.lower() and "icon" not in src.lower():
                        data['image_urls'].append(urljoin(property_url, src))
                data['image_urls'] = data['image_urls'][:10]
                
                # Description - Fallback classes
                desc_selectors = ['.description', '.block-content', '.content', '.listing-details', '#description', '.entry-content']
                for selector in desc_selectors:
                    item = soup.select_one(selector)
                    if item:
                        data['description'] = item.text.strip()
                        break
                if not data.get('description'):
                    data['description'] = ""

        except Exception as e:
            logger.error(f"Error data {property_url}: {e}")
        
        return self.normalize_data(data)
