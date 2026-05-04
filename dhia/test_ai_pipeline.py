import asyncio
import logging
from processing.cleaner import run_cleaning_pipeline
from database.models import init_db

logging.basicConfig(level=logging.INFO)

async def test_pipeline():
    await init_db()
    count = await run_cleaning_pipeline()
    print(f"\n--- TEST RESULT ---")
    print(f"Listings ready for AI: {count}")
    print(f"Results saved to: ai_ready_listings.csv")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
