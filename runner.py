"""
runner.py — Orchestrateur scraper materiaux de construction (Tunisie)
Base de donnees : SQLite (fichier local materiaux.db)

Usage :
  python runner.py                        # scrape tous les sites -> CSV
  python runner.py --site comaf
  python runner.py --site lecnt
  python runner.py --site limmobilier
  python runner.py --site smdevis
  python runner.py --export json
"""
import asyncio
import argparse
import csv
import json
import logging
import datetime
import os
import uuid
from typing import List, Dict, Any

from core.models import init_db, MaterialListing, Website, get_session
from scrapers.comaf_scraper import ComafScraper
from scrapers.lecnt_scraper import LeCNTScraper
from scrapers.blog_scraper import LimmobilierBlogScraper, SmDevisScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ── Configuration sites ───────────────────────────────────────────────────────
ECOMMERCE_SITES = [
    {
        "id": "comaf",
        "name": "COMAF - Comptoir Africain Tunisie",
        "base_url": "https://www.comaf.tn",
        "source_type": "ecommerce",
        "scraper_class": ComafScraper,
    },
    {
        "id": "lecnt",
        "name": "Le CNT - La Maison du Bien-Vivre",
        "base_url": "https://www.lecnt.com",
        "source_type": "ecommerce",
        "scraper_class": LeCNTScraper,
    },
]

BLOG_SITES = [
    {
        "id": "limmobilier",
        "name": "limmobilier.tn - Prix materiaux 2025",
        "base_url": "https://limmobilier.tn",
        "source_type": "blog_article",
        "scraper_class": LimmobilierBlogScraper,
    },
    {
        "id": "smdevis",
        "name": "SM Devis - Prix construction, rénovation & climatisation Tunisie",
        "base_url": "https://www.sm-devis.tn",
        "source_type": "blog_article",
        "scraper_class": SmDevisScraper,
    },
]

ALL_SITES = ECOMMERCE_SITES + BLOG_SITES


# ── Helpers SQLite ────────────────────────────────────────────────────────────
def get_or_create_website(site_cfg: Dict) -> Website:
    with get_session() as session:
        website = session.query(Website).filter_by(base_url=site_cfg["base_url"]).first()
        if not website:
            website = Website(
                id=str(uuid.uuid4()),
                name=site_cfg["name"],
                base_url=site_cfg["base_url"],
                is_active=True,
            )
            session.add(website)
            session.commit()
            session.refresh(website)
        return website


def save_listing(data: Dict, website: Website, source_type: str):
    with get_session() as session:
        # Eviter les doublons via data_hash
        existing = session.query(MaterialListing).filter_by(
            data_hash=data.get('data_hash', '')
        ).first()
        if existing:
            return

        listing = MaterialListing(
            id=str(uuid.uuid4()),
            website_id=website.id,
            source_type=source_type,
            title=data.get('title', 'N/A'),
            category=data.get('category', 'autre'),
            subcategory=data.get('subcategory'),
            brand=data.get('brand'),
            reference=data.get('reference'),
            price=data.get('price', 0.0),
            price_min=data.get('price_min'),
            price_max=data.get('price_max'),
            price_per_unit=data.get('price_per_unit', 0.0),
            currency=data.get('currency', 'TND'),
            unit=data.get('unit', 'unite'),
            quantity=data.get('quantity', 1.0),
            dimensions=data.get('dimensions'),
            tile_m2=data.get('tile_m2'),
            city=data.get('city'),
            supplier=data.get('supplier'),
            in_stock=data.get('in_stock', True),
            description=data.get('description', ''),
            image_urls=json.dumps(data.get('image_urls', [])),
            listing_url=data.get('listing_url', ''),
            data_hash=data.get('data_hash', str(uuid.uuid4())),
        )
        session.add(listing)
        session.commit()


# ── Scraping e-commerce ───────────────────────────────────────────────────────
async def scrape_ecommerce(site_cfg: Dict) -> List[Dict]:
    scraper = site_cfg["scraper_class"](website_config=site_cfg)
    results = []
    website = get_or_create_website(site_cfg)

    logger.info(f"[E-commerce] Demarrage : {site_cfg['name']}")

    listing_pages = scraper.fetch_listing_pages()
    logger.info(f"  {len(listing_pages)} pages catalogue")

    product_links = set()
    for page in listing_pages:
        product_links.update(scraper.extract_listing_links(page))
    logger.info(f"  {len(product_links)} produits a scraper")

    for url in product_links:
        try:
            data = scraper.extract_listing_data(url)
            if not data.get('title') or data['title'] == 'N/A':
                continue
            data['source_type'] = site_cfg["source_type"]
            save_listing(data, website, site_cfg["source_type"])
            results.append(data)
            logger.debug(f"  OK {data['title'][:55]} | {data.get('price', 0)} TND")
        except Exception as e:
            logger.error(f"  ERR {url}: {e}")

    logger.info(f"[E-commerce] {site_cfg['name']} : {len(results)} produits sauvegardes")
    return results


# ── Scraping blog ─────────────────────────────────────────────────────────────
async def scrape_blog(site_cfg: Dict) -> List[Dict]:
    scraper = site_cfg["scraper_class"](website_config=site_cfg)
    results = []
    website = get_or_create_website(site_cfg)

    logger.info(f"[Blog] Demarrage : {site_cfg['name']}")

    for article_url in scraper.fetch_listing_pages():
        try:
            records = scraper.extract_all_from_article(article_url)
            for data in records:
                if not data.get('title') or data['title'] == 'N/A':
                    continue
                data['source_type'] = site_cfg["source_type"]
                save_listing(data, website, site_cfg["source_type"])
                results.append(data)
            logger.info(f"  {len(records)} enregistrements depuis {article_url}")
        except Exception as e:
            logger.error(f"  ERR {article_url}: {e}")

    logger.info(f"[Blog] {site_cfg['name']} : {len(results)} enregistrements")
    return results


# ── Exports ───────────────────────────────────────────────────────────────────
EXPORT_FIELDS = [
    "source_type", "title", "category", "subcategory", "brand", "reference",
    "price", "price_min", "price_max", "price_per_unit",
    "currency", "unit", "quantity", "dimensions", "tile_m2",
    "city", "supplier", "in_stock", "description", "listing_url", "scraped_at"
]


def export_csv(results: List[Dict], filepath: str):
    if not results:
        logger.warning("Aucune donnee a exporter.")
        return
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    logger.info(f"CSV exporte : {filepath}")


def export_json(results: List[Dict], filepath: str):
    def serial(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        raise TypeError

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=serial)
    logger.info(f"JSON exporte : {filepath}")


# ── Main ──────────────────────────────────────────────────────────────────────
async def main(site_filter: str = None, export_format: str = "csv"):
    await init_db()
    logger.info("SQLite initialise")

    all_results: List[Dict] = []
    sites = [s for s in ALL_SITES if site_filter is None or s["id"] == site_filter]

    if not sites:
        logger.error(f"Site '{site_filter}' introuvable. Disponibles : {[s['id'] for s in ALL_SITES]}")
        return

    for site_cfg in sites:
        if site_cfg["source_type"] == "ecommerce":
            results = await scrape_ecommerce(site_cfg)
        else:
            results = await scrape_blog(site_cfg)
        all_results.extend(results)

    logger.info(f"TOTAL : {len(all_results)} enregistrements")
    os.makedirs("exports", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    if export_format == "json":
        export_json(all_results, f"exports/materiaux_{ts}.json")
    else:
        export_csv(all_results, f"exports/materiaux_{ts}.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper prix materiaux construction Tunisie")
    parser.add_argument('--site', choices=['comaf', 'lecnt', 'limmobilier', 'smdevis'],
                        help='Site a scraper (defaut: tous)')
    parser.add_argument('--export', choices=['csv', 'json'], default='csv')
    args = parser.parse_args()
    asyncio.run(main(site_filter=args.site, export_format=args.export))