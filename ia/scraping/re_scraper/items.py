# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ReScraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass
# re_scraper/schemas/items.py
import scrapy

class ListingItem(scrapy.Item):
    source = scrapy.Field()
    source_listing_id = scrapy.Field()
    url = scrapy.Field()

    title = scrapy.Field()
    listing_type = scrapy.Field()
    property_type = scrapy.Field()

    price_value = scrapy.Field()
    price_currency = scrapy.Field()

    area_m2 = scrapy.Field()
    rooms = scrapy.Field()
    bedrooms = scrapy.Field()
    bathrooms = scrapy.Field()

    city = scrapy.Field()
    delegation = scrapy.Field()
    location_raw = scrapy.Field()

    description = scrapy.Field()
    image_urls = scrapy.Field()   # requis par ImagesPipeline
    images = scrapy.Field()       # résultat pipeline
    first_seen = scrapy.Field()
    last_seen = scrapy.Field()

    raw = scrapy.Field()
