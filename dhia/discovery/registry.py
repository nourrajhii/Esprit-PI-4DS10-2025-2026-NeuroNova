from database.models import Website, Listing # No more SessionLocal

SEED_WEBSITES = [
    {
        "name": "Mubawab",
        "base_url": "https://www.mubawab.tn",
        "pagination_type": "page",
        "listing_page_pattern": "p={page}",
        "property_page_selector": {
            "title": "h1",
            "price": ".orangePrice",
            "surface": ".adMainChar li:contains('m²')"
        },
        "anti_bot_level": 1,
        "is_active": True
    },
    {
        "name": "Tayara",
        "base_url": "https://www.tayara.tn",
        "pagination_type": "scroll",
        "listing_page_pattern": None,
        "property_page_selector": {
            "title": "h1",
            "price": "span[data-testid='price']"
        },
        "anti_bot_level": 3,
        "is_active": True
    },
    {
        "name": "Tecnocasa",
        "base_url": "https://www.tecnocasa.tn",
        "pagination_type": "page",
        "listing_page_pattern": None,
        "property_page_selector": None,
        "anti_bot_level": 1,
        "is_active": True
    }
]

async def register_seed_websites():
    try:
        for ws_data in SEED_WEBSITES:
            # Deduplicate by base_url for better accuracy
            existing = await Website.find_one(Website.base_url == ws_data['base_url'])
            if not existing:
                new_ws = Website(**ws_data)
                await new_ws.insert()
                print(f"Registered {ws_data['name']}")
            elif not existing.is_active:
                # Update existing site to be active if it's a seed
                existing.is_active = True
                existing.confidence_score = 100.0
                await existing.save()
                print(f"Prioritized existing {ws_data['name']}")
    except Exception as e:
        print(f"Error seeding websites: {e}")
