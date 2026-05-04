import httpx
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import logging
from typing import List, Set, Dict, Any, Optional, Tuple
from database.models import Website, DiscoveredRelation # No more SessionLocal
import datetime
import os
import re
from serpapi import GoogleSearch

logger = logging.getLogger(__name__)

# Constants
DOMAIN_KEYWORDS = ["immo", "immobilier", "property", "estate", "agence", "realestate"]
REAL_ESTATE_KEYWORDS = {
    "immobilier": 10, "appartement": 10, "maison": 10, "villa": 10, "vente": 5, 
    "location": 5, "annonces immobilières": 15, "terrain": 5, "agence immobilière": 15, 
    "loyer": 5, "architecture": 2, "résidence": 5
}
PRICE_PATTERNS = [r"\d[\d\s.,]{2,}\s*(dt|tnd|dinars|millimes)"]
TUNISIA_REGIONS = [
    "tunis", "ariana", "ben arous", "manouba", "nabeul", "zaghouan", "benzart", 
    "beja", "jendouza", "kef", "siliana", "kairouan", "kasserine", "sidi bouzid", 
    "sousse", "monastir", "mahdia", "sfax", "gairouan", "tozeur", "kebili", 
    "gabes", "mednine", "tataouine"
]
BLACKLIST_DOMAINS = [
    "facebook.com", "instagram.com", "youtube.com", "linkedin.com", "avito.ma", 
    "wikipedia.org", "pinterest.com", "twitter.com", "google.com", "bing.com"
]
LISTING_URL_PATTERNS = [r"/annonce/", r"/vente/", r"/location/", r"/bien/", r"/propriete/", r"/detail/"]

class WebsiteExplorer:
    def __init__(self, max_concurrent: int = 10):
        self.serp_api_key = os.getenv("SERPAPI_KEY")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queue = asyncio.PriorityQueue()
        self.visited_domains = set()

    async def discover_serpapi(self, query: str, num_pages: int = 3):
        if not self.serp_api_key: return
        try:
            for page in range(num_pages):
                params = {
                    "engine": "google",
                    "q": query,
                    "api_key": self.serp_api_key,
                    "gl": "tn",
                    "start": page * 10
                }
                search = GoogleSearch(params)
                results = search.get_dict().get("organic_results", [])
                if not results: break
                
                for res in results:
                    await self.add_to_queue(res.get("link"), source=f"SerpAPI:{query}", priority=5.0)
                
                # Small delay to keep API happy
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"SerpAPI Error: {e}")

    async def discover_crt_sh(self, domain_suffix: str = "%.tn"):
        url = f"https://crt.sh/?q={domain_suffix}&output=json"
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=30)
                if res.status_code == 200:
                    data = res.json()
                    for entry in data:
                        name = entry.get("common_name")
                        if name:
                            await self.add_to_queue(f"https://{name}", source="crt.sh", priority=3.0)
        except Exception as e:
            logger.error(f"crt.sh Error: {e}")

    async def add_to_queue(self, url: str, source: str, priority: float = 0.0, depth: int = 0):
        domain = self._normalize_domain(url)
        if not domain or domain in self.visited_domains: return
        if any(bd in domain for bd in BLACKLIST_DOMAINS): return
        
        if priority == 0.0:
            priority = 10.0
            if any(kw in domain.lower() for kw in DOMAIN_KEYWORDS): priority += 20.0
            if domain.lower().endswith(".tn"): priority += 15.0

        await self.queue.put((-priority, domain, source, depth))

    def _normalize_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            domain = domain.replace("www.", "")
            return f"https://{domain}" if domain else ""
        except: return ""

    async def validate_and_expand(self, client: httpx.AsyncClient, domain: str, source: str, depth: int):
        self.visited_domains.add(domain)
        async with self.semaphore:
            try:
                logger.info(f"Validating: {domain} (Depth: {depth})")
                await asyncio.sleep(1.0)
                
                response = await client.get(domain, headers=self.headers, timeout=15.0, follow_redirects=True)
                if response.status_code != 200: return

                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text().lower()
                score = 0
                for kw, weight in REAL_ESTATE_KEYWORDS.items():
                    if kw in text: score += weight
                for reg in TUNISIA_REGIONS:
                    if reg in text: score += 5
                for p in PRICE_PATTERNS:
                    if re.search(p, text): score += 20

                final_score = min(score, 100)
                tech_found = "Next.js" if "__NEXT_DATA__" in response.text else "WordPress" if "wp-content" in response.text else "Vanilla"

                # MongoDB (Beanie) Save
                existing = await Website.find_one(Website.base_url == domain)
                if not existing:
                    new_ws = Website(
                        name=urlparse(domain).netloc, base_url=domain, is_active=False,
                        confidence_score=final_score, discovery_source=source,
                        tech_stack=tech_found, discovery_depth=depth,
                        validation_status="valid" if final_score > 50 else "needs_review"
                    )
                    await new_ws.insert()
                else:
                    existing.confidence_score = max(existing.confidence_score, final_score)
                    existing.discovery_depth = min(existing.discovery_depth, depth)
                    await existing.save()

                if final_score > 40 and depth < 3:
                    links = soup.find_all('a', href=True)
                    for a in links:
                        href = a['href']
                        ext_domain = self._normalize_domain(href)
                        if ext_domain and ext_domain != domain:
                            await DiscoveredRelation(source_domain=domain, target_domain=ext_domain, relation_type="outbound").insert()
                            await self.add_to_queue(ext_domain, source=f"Outbound:{domain}", depth=depth+1)

            except Exception as e:
                logger.error(f"❌ Database error validating {domain}: {e}")

            except Exception as e:
                logger.error(f"❌ System error validating {domain}: {e}")

    async def run_discovery_worker(self, custom_query: Optional[str] = None):
        logger.info("Starting MongoDB-backed Discovery Worker...")
        
        # Initial seeding if not a restricted run
        if not custom_query:
            await self.discover_crt_sh()
            initial_queries = ["immobilier tunisie", "vente appartement tunis", "location maison tunisie"]
        else:
            initial_queries = [custom_query]

        for query in initial_queries:
            await self.discover_serpapi(query)

        async with httpx.AsyncClient() as client:
            while not self.queue.empty():
                priority, domain, source, depth = await self.queue.get()
                await self.validate_and_expand(client, domain, source, depth)
                self.queue.task_done()
                
                # Check if we need more targets
                if self.queue.qsize() < 3:
                   import random
                   region = random.choice(TUNISIA_REGIONS)
                   await self.discover_serpapi(f"agence immobilière {region}")

if __name__ == "__main__":
    from database.models import init_db
    async def main():
        await init_db()
        explorer = WebsiteExplorer()
        await explorer.run_discovery_worker()
    asyncio.run(main())
