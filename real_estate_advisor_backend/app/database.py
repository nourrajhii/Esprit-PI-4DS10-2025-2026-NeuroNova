"""
MongoDB Atlas database connection for real_estate_advisor_backend.
Replaces the former MySQL/SQLAlchemy layer.
Reads from the dcrawl.listings collection scraped by dhia.
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv(
    "DATABASE_URL",
    "mongodb+srv://dhiaromd1_db_user:uFXwH6QvnGYib1eX@cluster0.dm9cm4p.mongodb.net/dcrawl"
    "?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"
)
MONGO_DB = "dcrawl"

# Sync client for the advisor routes (keeps existing sync code working)
_sync_client: MongoClient | None = None


def get_sync_client() -> MongoClient:
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(MONGO_URL, tlsCAFile=certifi.where())
    return _sync_client


def get_listings_collection():
    client = get_sync_client()
    return client[MONGO_DB]["listings"]


# Dependency injected into route handlers — yields the collection
def get_db():
    col = get_listings_collection()
    try:
        yield col
    finally:
        pass  # MongoClient is long-lived; no per-request teardown needed
