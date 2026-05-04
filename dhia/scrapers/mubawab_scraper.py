import requests
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from typing import List, Dict, Any
import time
import logging

logger = logging.getLogger(__name__)

class MubawabScraper(BaseScraper):
    def __init__(self, website_config: Dict[str, Any]):
        super().__init__(website_config)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_listing_pages(self) -> List[str]:
        """
        Mubawab specific entry points.
        """
        # Common listing categories on Mubawab.tn
        return [
            f"{self.base_url}/vente-immobilier-sc-1",
            f"{self.base_url}/location-immobilier-sc-2",
            f"{self.base_url}/locations-vacances-sc-3"
        ]

    def extract_listing_links(self, page_url: str) -> List[str]:
        links = []
        try:
            # Add pagination to the category links
            for p in range(1, 4): # First 3 pages
                paged_url = f"{page_url}?p={p}"
                response = requests.get(paged_url, headers=self.headers, timeout=15)
                if response.status_code == 200:
                    response.encoding = response.apparent_encoding
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Mubawab patterns: /a/ for detail, /pa/ for search results (sometimes)
                    patterns = ["/a/", "/pa/", "/immobilier-tunisie-sc-1", "/location-immobilier-sc-2", "/fr/a/", "/fr/pa/"]
                    
                    cards = soup.select('.listingCard, li.listing-card, div.listing-item, .listingCard-item')
                    for card in cards:
                        a_tag = card.find('a', href=True)
                        if a_tag:
                            link = a_tag['href']
                            if any(p in link.lower() for p in patterns):
                                full_url = urljoin(self.base_url, link)
                                links.append(full_url)
                    
                    # Also check all links on the page just in case
                    if not links:
                        for a in soup.find_all('a', href=True):
                            href = a['href']
                            if "/a/" in href.lower() or "/pa/" in href.lower() or "/annonce/" in href.lower():
                                full_url = urljoin(self.base_url, href)
                                links.append(full_url)
        except Exception as e:
            logger.error(f"Error extracting links from {page_url}: {e}")
        return list(set(links))

    def extract_listing_data(self, property_url: str) -> Dict[str, Any]:
        data = {}
        try:
            response = requests.get(property_url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding
                soup = BeautifulSoup(response.text, 'html.parser')
                
                header = soup.select_one('h1')
                data['title'] = header.text.strip() if header else 'N/A'
                
                price_tag = soup.select_one('.orangePrice, .price, .item-price')
                data['price'] = price_tag.text.strip() if price_tag else '0'
                
                description = soup.select_one('.block-content p, .description, .adMainDescription')
                data['description'] = description.text.strip() if description else ''
                
                # Characteristics
                chars = soup.select('.adMainChar li, .property-amenities li')
                for char in chars:
                    text = char.text.lower()
                    if 'm²' in text:
                        data['surface_m2'] = text
                    if 'chambre' in text or 'pièce' in text:
                        data['rooms'] = text
                    if 'salle' in text:
                        data['bathrooms'] = text
                
                data['listing_url'] = property_url
                
                # Images
                img_tags = soup.select('.slider-item img, .gallery img, #property-gallery img')
                data['image_urls'] = [urljoin(property_url, img.get('src') or img.get('data-src')) for img in img_tags if img.get('src') or img.get('data-src')]
                
        except Exception as e:
            logger.error(f"Error extracting data from {property_url}: {e}")
        
        return self.normalize_data(data)
