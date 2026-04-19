# re_scraper/spiders/sites/mubawab_spider.py
import scrapy
from datetime import datetime, timezone
from re_scraper.items import ListingItem
from re_scraper.core.normalization import clean_text, parse_price_tnd, parse_area_m2, infer_listing_type

class MubawabSpider(scrapy.Spider):
    name = "mubawab"
    allowed_domains = ["mubawab.tn"]
    start_urls = [
        # Exemple: pages catégories; tu peux en mettre plusieurs
        "https://www.mubawab.tn/fr/sc/appartements-a-vendre",
        "https://www.mubawab.tn/fr/sc/appartements-a-louer",
    ]

    def parse(self, response):
        """
        Objectif:
        - trouver toutes les URLs des annonces sur une page liste
        - paginer
        """
        # 1) liens vers pages détail (selector à adapter au HTML réel)
        for href in response.css("a::attr(href)").getall():
            if "/fr/a/" in href or "/fr/" in href:
                url = response.urljoin(href)
                yield response.follow(url, callback=self.parse_detail)

        # 2) pagination (selector à adapter)
        next_page = response.css("a[rel='next']::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_detail(self, response):
        """
        Objectif:
        - extraire les champs (même si certains manquent)
        - normaliser
        """
        now = datetime.now(timezone.utc)

        title = clean_text(response.css("h1::text").get())
        price_raw = clean_text(response.css("[class*='price']::text").get())
        area_raw = clean_text(response.css("li:contains('m²')::text").get())

        item = ListingItem()
        item["source"] = "mubawab"
        item["url"] = response.url

        # Clé unique : idéalement un id site; sinon fallback: URL
        item["source_listing_id"] = response.url.split("?")[0]

        item["title"] = title
        item["listing_type"] = infer_listing_type(title + " " + response.text[:2000])
        item["price_value"] = parse_price_tnd(price_raw)
        item["price_currency"] = "TND"

        item["area_m2"] = parse_area_m2(area_raw)

        item["description"] = clean_text(" ".join(response.css("[class*='description'] *::text").getall()))

        # Images
        item["image_urls"] = [response.urljoin(u) for u in response.css("img::attr(src)").getall()]

        item["last_seen"] = now
        item["raw"] = {"price_raw": price_raw, "area_raw": area_raw}

        yield item
        yield scrapy.Request(
         response.url,
         callback=self.parse_detail,
         meta={"playwright": True}
)
