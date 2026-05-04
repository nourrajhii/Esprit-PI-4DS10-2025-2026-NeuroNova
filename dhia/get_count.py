import asyncio
from database.models import init_db, Listing

async def get_count():
    await init_db()
    count = await Listing.count()
    print(f"TOTAL_LISTINGS: {count}")

if __name__ == "__main__":
    asyncio.run(get_count())
