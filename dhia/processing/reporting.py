import pandas as pd
from database.models import Website, Listing
import os
import logging

logger = logging.getLogger(__name__)

async def generate_sites_report(output_path: str = "discovered_sites_report.xlsx"):
    """
    Generates an Excel report of all discovered and valid websites.
    """
    logger.info("Generating discovery report...")
    websites = await Website.find_all().to_list()
    
    data = []
    for ws in websites:
        data.append({
            "Name": ws.name,
            "Base URL": ws.base_url,
            "Status": ws.validation_status,
            "Score": ws.confidence_score,
            "Tech Stack": ws.tech_stack,
            "Source": ws.discovery_source,
            "Detected Patterns": ", ".join(ws.listing_patterns),
            "Last Validated": ws.last_validated_at,
            "Rejection Reason": ws.rejection_reason
        })
    
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False)
    logger.info(f"Report saved to {output_path}")
    return output_path

async def export_listings_to_excel(output_path: str = "scraped_listings.xlsx"):
    """
    Exports all scraped listings to an Excel file.
    """
    logger.info("Exporting listings to Excel...")
    listings = await Listing.find_all().to_list()
    
    data = [l.dict() for l in listings]
    df = pd.DataFrame(data)
    
    # Drop Mongo/ID fields for clean Excel
    if not df.empty:
        df = df.drop(columns=['_id', 'id', 'revision'], errors='ignore')
    
    df.to_excel(output_path, index=False)
    logger.info(f"Listings exported to {output_path}")
    return output_path
