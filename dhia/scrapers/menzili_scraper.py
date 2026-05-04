import requests
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from typing import List, Dict, Any
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class MenZiliScraper(BaseScraper):
    def fetch_listing_pages(self) -> List[str]:
        return [
            f"{self.base_url}/vente-immobilier",
            f"{self.base_url}/location-immobilier",
            f"{self.base_url}/location-vacance"
        ]

    def extract_listing_links(self, page_url: str) -> List[str]:
        links = []
        try:
            for p in range(1, 3):
                paged_url = f"{page_url}/page-{p}"
                response = requests.get(paged_url, headers=self.headers, timeout=15)
                if response.status_code == 200:
                    response.encoding = response.apparent_encoding
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # MenZili uses listing-item or similar
                    items = soup.select('.property-item, .listing-item, a[href*="/immobilier/"]')
                    for item in items:
                        href = item.get('href') or (item.find('a')['href'] if item.find('a') else None)
                        if href and "/immobilier/" in href:
                            full_url = urljoin(self.base_url, href)
                            links.append(full_url)
        except Exception as e:
            logger.error(f"Error extracting links from {page_url}: {e}")
        return list(set(links))

    def extract_listing_data(self, property_url: str) -> Dict[str, Any]:
        data = {'listing_url': property_url}
        try:
            response = requests.get(property_url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding
                soup = BeautifulSoup(response.text, 'html.parser')
                data['title'] = soup.find('h1').text.strip() if soup.find('h1') else "N/A"
                
                # Price
                price_tag = soup.select_one('.price, .property-price, .item-price')
                data['price'] = price_tag.text.strip() if price_tag else "0"
                
                # Description
                data['description'] = soup.select_one('.property-description, .description, .entry-content').text.strip() if soup.select_one('.property-description, .description, .entry-content') else ""
                
                # Images
                img_tags = soup.select('.property-gallery img, .slider img, .owl-carousel img')
                data['image_urls'] = [urljoin(property_url, img['src']) for img in img_tags if img.get('src')]
                
        except Exception as e:
            logger.error(f"Error extracting data from {property_url}: {e}")
        
        return self.normalize_data(data)
