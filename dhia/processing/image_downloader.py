import os
import aiohttp
import asyncio
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

IMAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads", "images")

# Ensure the directory exists
os.makedirs(IMAGE_DIR, exist_ok=True)

async def download_image(session: aiohttp.ClientSession, url: str, save_path: str):
    try:
        async with session.get(url, timeout=15) as response:
            if response.status == 200:
                content = await response.read()
                with open(save_path, 'wb') as f:
                    f.write(content)
                return True
    except Exception as e:
        logger.debug(f"Failed to download image {url}: {e}")
    return False

async def download_listing_images(listing_id: str, image_urls: list):
    """
    Downloads images for a given listing. 
    listing_id: A unique identifier for the listing (e.g., hash or DB ID)
    image_urls: List of image URLs
    """
    if not image_urls:
        return

    # Create a subfolder for the listing to keep things organized
    listing_dir = os.path.join(IMAGE_DIR, str(listing_id))
    os.makedirs(listing_dir, exist_ok=True)

    # Use aiohttp to download images concurrently for this listing
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, url in enumerate(image_urls[:5]): # Download up to 5 images to save space/time
            ext = os.path.splitext(urlparse(url).path)[-1]
            if not ext or len(ext) > 5:
                ext = '.jpg' # fallback extension
            filename = f"image_{i+1}{ext}"
            save_path = os.path.join(listing_dir, filename)
            
            # Skip if already downloaded
            if not os.path.exists(save_path):
                tasks.append(download_image(session, url, save_path))
        
        if tasks:
            await asyncio.gather(*tasks)
