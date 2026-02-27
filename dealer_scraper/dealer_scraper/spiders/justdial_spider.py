import json
import scrapy
from dealer_scraper.items import DealerItem


class JustDialSpider(scrapy.Spider):
    """
    Spider to scrape battery and charger dealer data from JustDial.
    Uses JSON-LD structured data embedded in page source.
    Fast bulk scraper — phone numbers come from the Google Maps spider.
    """
    name = "justdial"
    allowed_domains = ["justdial.com"]

    CATEGORIES = [
        ("Battery-Dealers", "nct-10039172", "battery"),
        ("Car-Battery-Dealers", "nct-10075591", "battery"),
        ("Inverter-Battery-Dealers", "nct-10274587", "battery"),
        ("Electric-Vehicle-Battery-Charger-Dealers", "nct-15123569", "charger"),
        ("EV-Charging-Station", "nct-11384971", "charger"),
    ]

    DEFAULT_CITIES = [
        "Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad",
        "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    ]

    MAX_PAGES = 5

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "HTTPCACHE_ENABLED": True,
        "HTTPCACHE_EXPIRATION_SECS": 86400,
    }

    def __init__(self, cities=None, max_pages=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if cities and isinstance(cities, str):
            self.cities = [c.strip() for c in cities.split(",")]
        elif cities and isinstance(cities, list):
            self.cities = cities
        else:
            self.cities = self.DEFAULT_CITIES
        if max_pages is not None:
            self.MAX_PAGES = int(max_pages)

    def start_requests(self):
        for city in self.cities:
            for slug, nct, dealer_type in self.CATEGORIES:
                url = f"https://www.justdial.com/{city}/{slug}/{nct}"
                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    meta={
                        "city": city,
                        "dealer_type": dealer_type,
                        "category_slug": slug,
                        "nct": nct,
                        "page": 1,
                    },
                )

    def parse(self, response):
        city = response.meta["city"]
        dealer_type = response.meta["dealer_type"]
        category_slug = response.meta["category_slug"]
        nct = response.meta["nct"]
        page = response.meta["page"]

        items_found = 0

        # Extract from JSON-LD structured data
        json_ld_scripts = response.xpath(
            '//script[@type="application/ld+json"]/text()'
        ).getall()

        for script_text in json_ld_scripts:
            try:
                data = json.loads(script_text)
            except json.JSONDecodeError:
                continue

            entries = data if isinstance(data, list) else [data]

            for entry in entries:
                if entry.get("@type") == "LocalBusiness":
                    item = self._parse_business(entry, city, dealer_type, category_slug)
                    if item:
                        items_found += 1
                        yield item

                if entry.get("@type") == "ItemList":
                    for elem in entry.get("itemListElement", []):
                        biz = elem.get("item", elem)
                        if biz.get("@type") == "LocalBusiness":
                            item = self._parse_business(biz, city, dealer_type, category_slug)
                            if item:
                                items_found += 1
                                yield item

        # Fallback to HTML parsing
        if items_found == 0:
            items_found = yield from self._parse_html(response, city, dealer_type, category_slug)

        self.logger.info(
            f"[{city}] {category_slug} page {page}: {items_found} dealers found"
        )

        # Pagination
        if items_found > 0 and page < self.MAX_PAGES:
            next_page = page + 1
            next_url = (
                f"https://www.justdial.com/{city}/{category_slug}/{nct}/page-{next_page}"
            )
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={
                    "city": city,
                    "dealer_type": dealer_type,
                    "category_slug": category_slug,
                    "nct": nct,
                    "page": next_page,
                },
            )

    def _parse_business(self, entry, city, dealer_type, category_slug):
        """Parse a JSON-LD LocalBusiness entry into a DealerItem."""
        name = entry.get("name", "").strip()
        if not name:
            return None

        # Skip category summary entries
        name_lower = name.lower()
        if " in " in name_lower and any(
            kw in name_lower for kw in ["dealers", "station", "charger"]
        ):
            return None

        address_obj = entry.get("address", {})
        street = address_obj.get("streetAddress", "")
        locality = (
            address_obj.get("addressLocality")
            or address_obj.get("addresslocality", "")
        )
        region = address_obj.get("addressRegion", "")
        pincode = address_obj.get("postalCode", "")
        full_address = ", ".join(filter(None, [street, locality, region]))

        agg_rating = entry.get("aggregateRating", {})
        rating = agg_rating.get("ratingValue", "")
        reviews = agg_rating.get("ratingCount") or agg_rating.get("reviewCount", "")
        phone = entry.get("telephone", "")

        return DealerItem(
            name=name,
            address=full_address,
            city=city,
            area=locality,
            pincode=str(pincode),
            phone=str(phone),
            rating=str(rating),
            reviews=str(reviews),
            category=category_slug.replace("-", " "),
            dealer_type=dealer_type,
            source="justdial",
            source_url=entry.get("url", ""),
        )

    def _parse_html(self, response, city, dealer_type, category_slug):
        """Fallback: parse dealer data from HTML elements."""
        count = 0
        listings = response.css(".jdresult_box")

        for listing in listings:
            name = listing.css(".resultbox_title_anchor::text").get("").strip()
            if not name:
                continue

            address = listing.css(".resultbox_address::text").get("").strip()
            rating = listing.css(".resultbox_totalrate::text").get("").strip()

            yield DealerItem(
                name=name,
                address=address,
                city=city,
                area="",
                pincode="",
                phone="",
                rating=rating,
                reviews="",
                category=category_slug.replace("-", " "),
                dealer_type=dealer_type,
                source="justdial",
                source_url=response.url,
            )
            count += 1

        return count
