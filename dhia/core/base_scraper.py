from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import hashlib
import datetime
import logging
import re

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    def __init__(self, website_config: Dict[str, Any]):
        self.config = website_config
        self.base_url = website_config.get('base_url')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    @abstractmethod
    def fetch_listing_pages(self) -> List[str]:
        pass

    @abstractmethod
    def extract_listing_links(self, page_url: str) -> List[str]:
        pass

    @abstractmethod
    def extract_listing_data(self, property_url: str) -> Dict[str, Any]:
        pass

    def normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Price
        if 'price' in data and data['price']:
            data['price'] = self._clean_numeric(str(data['price']))
        
        # Surface
        if 'surface_m2' in data and data['surface_m2']:
            data['surface_m2'] = self._clean_numeric(str(data['surface_m2']))

        # Rooms/Baths
        for key in ['rooms', 'bathrooms']:
            if key in data and data[key]:
                data[key] = int(self._clean_numeric(str(data[key])))

        data['scraped_at'] = datetime.datetime.utcnow()
        data['data_hash'] = self.generate_hash(data)
        return data

    def _clean_numeric(self, val: str) -> float:
        try:
            cleaned = re.sub(r'[^\d.]', '', val.replace(',', '.'))
            return float(cleaned) if cleaned else 0.0
        except: return 0.0

    def generate_hash(self, data: Dict[str, Any]) -> str:
        hash_str = f"{data.get('title', '')}|{data.get('price', 0)}|{data.get('surface_m2', 0)}|{data.get('listing_url', '')}"
        return hashlib.md5(hash_str.encode()).hexdigest()
