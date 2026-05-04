from typing import Optional, List, Dict, Any
from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
import certifi
from pydantic import Field
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class Website(Document):
    name: str
    base_url: str
    pagination_type: Optional[str] = "page"
    listing_page_pattern: Optional[str] = None
    property_page_selector: Optional[Dict[str, Any]] = None
    anti_bot_level: int = 0
    is_active: bool = False
    
    # Discovery metadata
    confidence_score: float = 0.0
    discovery_source: Optional[str] = None
    validation_status: str = "pending"  # pending, valid, rejected, needs_review
    rejection_reason: Optional[str] = None
    listing_patterns: List[str] = []
    tech_stack: str = "Unknown"
    last_validated_at: Optional[datetime.datetime] = None
    crawl_budget: int = 100
    priority: float = 0.0
    discovery_depth: int = 0
    
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    class Settings:
        name = "websites"

class Listing(Document):
    website_id: str # Store the string ID of the Website document
    title: str
    price: Optional[float] = 0.0
    currency: str = "TND"
    city: Optional[str] = None
    zone: Optional[str] = None
    property_type: Optional[str] = None
    transaction_type: Optional[str] = None  # rent/sale
    surface_m2: Optional[float] = 0.0
    rooms: Optional[int] = 0
    bathrooms: Optional[int] = 0
    description: Optional[str] = None
    agency_owner: Optional[str] = None
    phone: Optional[str] = None
    listing_url: str
    data_hash: str
    image_urls: List[str] = []
    published_date: Optional[datetime.datetime] = None
    scraped_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    class Settings:
        name = "listings"

class DiscoveredRelation(Document):
    source_domain: str
    target_domain: str
    relation_type: str  # backlink, outbound, search_result
    discovered_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    class Settings:
        name = "discovered_relations"

async def init_db():
    # Use MongoDB URL from .env
    db_url = os.getenv("DATABASE_URL")
    
    # Correctly parse database name from URL (handle query params)
    # Example: mongodb+srv://user:pass@host/dbname?params
    if "mongodb+srv" in db_url or "mongodb://" in db_url:
        # Split out the part after the last single slash (ignoring //)
        parts = db_url.replace("://", "##").split("/")
        path = parts[-1] if len(parts) > 1 else ""
        db_name = path.split("?")[0] if "?" in path else path
        
        # Default if db_name is empty (e.g., ...mongodb.net/?)
        if not db_name or db_name.strip() == "":
            db_name = "dcrawl"
    else:
        db_name = "dcrawl"
        
    client = AsyncIOMotorClient(db_url, tlsCAFile=certifi.where())
    await init_beanie(database=client[db_name], document_models=[Website, Listing, DiscoveredRelation])
