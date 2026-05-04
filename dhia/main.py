import logging
import asyncio
import os
from database.models import init_db, Website, Listing
from discovery.registry import register_seed_websites
from discovery.explorer import WebsiteExplorer
from scrapers.generic_scraper import GenericStaticScraper
from scrapers.mubawab_scraper import MubawabScraper
from scrapers.menzili_scraper import MenZiliScraper
from processing.reporting import generate_sites_report, export_listings_to_excel
from processing.image_downloader import download_listing_images
from processing.cleaner import run_cleaning_pipeline
from processing.feature_engineering import run_feature_engineering
from processing.model_trainer import run_model_training
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_scraper():
    logger.info("Starting production crawler job...")
    try:
        # Lowering threshold to 50 as requested to capture all 'Valid' sites
        websites = await Website.find(Website.confidence_score >= 50).to_list()
        active_seeds = await Website.find(Website.is_active == True).to_list()
        
        target_sites = list({ws.base_url: ws for ws in websites + active_seeds}.values())
        logger.info(f"Targeting {len(target_sites)} websites for scraping.")

        for ws in target_sites:
            logger.info(f"Scraping Engine: {ws.name if ws.name else ws.base_url}")
            
            # Routing: Choose specialized scraper if available
            domain = ws.base_url.lower()
            if "mubawab.tn" in domain:
                scraper = MubawabScraper(ws.model_dump())
            elif "menzili.tn" in domain:
                scraper = MenZiliScraper(ws.model_dump())
            else:
                scraper = GenericStaticScraper(ws.model_dump())
            
            entry_pages = scraper.fetch_listing_pages()
            to_scrape = set()
            
            for url in entry_pages:
                if any(p in url.lower() for p in (scraper.config.get('listing_patterns', []) or ["/annonce", "/vente", "/achat", "/bien", "/propriete", "/detail", "/property", "/produit", "/a/"])):
                    to_scrape.add(url)
                else:
                    logger.info(f"Crawling listings from: {url}")
                    links = scraper.extract_listing_links(url)
                    to_scrape.update(links)
            
            logger.info(f"Found {len(to_scrape)} potential properties to scrape for {ws.base_url}")
            
            # Increase default budget for 'find all' request
            budget = ws.crawl_budget if ws.crawl_budget > 100 else 2000
            
            for link in list(to_scrape)[:budget]: # Use increased budget
                try:
                    existing = await Listing.find_one(Listing.listing_url == link)
                    if existing: continue
                    
                    data = scraper.extract_listing_data(link)
                    
                    if data and data.get('title') and data.get('title') != "N/A" and data.get('listing_url'):
                        existing_hash = await Listing.find_one(Listing.data_hash == data['data_hash'])
                        if existing_hash: continue

                        new_listing = Listing(
                            website_id=str(ws.id),
                            **data
                        )
                        await new_listing.insert()
                        logger.info(f"✅ Saved: {data['title'][:40]}... ({data['price']} {data['currency']})")
                        
                        # Trigger image download in the background without blocking the main scraper
                        if data.get('image_urls'):
                            asyncio.create_task(download_listing_images(str(new_listing.id), data['image_urls']))
                    else:
                        logger.warning(f"⚠️ Skipping incomplete data for {link}")
                except Exception as e:
                    logger.error(f"Error scraping {link}: {e}")
                
                await asyncio.sleep(0.5)

        # Final Export
        await export_listings_to_excel("final_listings_report.xlsx")

        # ── AI Pipeline ───────────────────────────────────────────────────
        # Stage 1: Clean + Tunisia filter → pipeline/cleaned_listings.csv
        os.makedirs("pipeline", exist_ok=True)
        cleaned_count = await run_cleaning_pipeline()

        # Stage 2: Feature engineering → pipeline/X_train.csv etc.
        if cleaned_count >= 50:
            fe_result = run_feature_engineering()
            # Stage 3: Train / Retrain the price-prediction model
            model_meta = run_model_training()
            logger.info(
                f"Model updated: R²={model_meta['r2']} | "
                f"MAPE={model_meta['mape_pct']}% | "
                f"Trained on {model_meta['n_train']} samples"
            )
        else:
            logger.warning(f"Only {cleaned_count} clean rows — skipping feature engineering.")

        final_count = await Listing.count()
        logger.info(f"Cycle complete │ DB total: {final_count} │ AI-ready: {cleaned_count}")

    except Exception as e:
        logger.error(f"Error in crawler job: {e}")
    logger.info("Crawler job finished.")

async def start_app():
    await init_db()
    
    cycle = 1
    while True:
        import datetime
        now = datetime.datetime.now()
        next_run = now + datetime.timedelta(hours=24)
        
        logger.info(f"=== Starting Daily Sync Cycle {cycle} at {now.strftime('%Y-%m-%d %H:%M:%S')} ===")
        await register_seed_websites()
        
        # 1. Run Discovery to find target sites
        logger.info(f"Step 1: Running Deep Discovery cycle {cycle}...")
        explorer = WebsiteExplorer()
        
        # Diversify search by picking random regions
        import random
        from discovery.explorer import TUNISIA_REGIONS
        region = random.choice(TUNISIA_REGIONS)
        # Deep discovery: Paginate through SerpAPI
        await explorer.run_discovery_worker(custom_query=f"agence immobilière {region} tunisie")
        
        # 2. Generate Discovery Excel Report
        logger.info("Step 2: Generating Discovery Excel Report...")
        await generate_sites_report("tunisian_real_estate_ecosystem.xlsx")
        
        # 3. Run Production Scraper on all valid sites
        logger.info("Step 3: Starting Production Scraper (High Budget)...")
        await run_scraper()
        
        logger.info(f"=== Cycle {cycle} Complete. Next run scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')} ===")
        # Sleep for 24 hours
        await asyncio.sleep(86400) 
        cycle += 1

if __name__ == "__main__":
    asyncio.run(start_app())
