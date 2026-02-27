import re
import scrapy
from scrapy_playwright.page import PageMethod
from dealer_scraper.items import DealerItem


class GoogleMapsSpider(scrapy.Spider):
    """
    Spider to scrape battery and charger dealer data from Google Maps.
    Uses scrapy-playwright to render the JavaScript SPA.

    Two-phase approach:
      1. Load search results, scroll feed, collect detail URLs.
      2. Visit each detail URL to extract phone, address, etc.
    """
    name = "googlemaps"

    SEARCH_QUERIES = [
        ("battery dealers", "battery"),
        ("car battery dealers", "battery"),
        ("inverter battery dealers", "battery"),
        ("EV charging station", "charger"),
        ("electric vehicle charger dealers", "charger"),
    ]

    DEFAULT_CITIES = [
        "Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad",
        "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    ]

    MAX_SCROLLS = 10

    custom_settings = {
        "DOWNLOAD_DELAY": 5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "CONCURRENT_REQUESTS": 1,
        "HTTPCACHE_ENABLED": False,
    }

    def __init__(self, cities=None, max_scrolls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if cities and isinstance(cities, str):
            self.cities = [c.strip() for c in cities.split(",")]
        elif cities and isinstance(cities, list):
            self.cities = cities
        else:
            self.cities = self.DEFAULT_CITIES
        if max_scrolls is not None:
            self.MAX_SCROLLS = int(max_scrolls)

    def start_requests(self):
        for city in self.cities:
            for query, dealer_type in self.SEARCH_QUERIES:
                search_term = f"{query} in {city}"
                url = (
                    f"https://www.google.com/maps/search/"
                    f"{search_term.replace(' ', '+')}"
                )
                yield scrapy.Request(
                    url,
                    callback=self.parse_search,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_page_methods": [
                            PageMethod(
                                "wait_for_selector",
                                'div[role="feed"]',
                                timeout=30000,
                            ),
                        ],
                        "city": city,
                        "dealer_type": dealer_type,
                        "query": query,
                    },
                    errback=self.errback_close_page,
                    dont_filter=True,
                )

    async def parse_search(self, response):
        """Phase 1: Scroll the results feed, then extract all detail URLs."""
        page = response.meta["playwright_page"]
        city = response.meta["city"]
        dealer_type = response.meta["dealer_type"]
        query = response.meta["query"]

        try:
            feed_selector = 'div[role="feed"]'

            for scroll_i in range(self.MAX_SCROLLS):
                await page.evaluate(
                    """(selector) => {
                        const feed = document.querySelector(selector);
                        if (feed) feed.scrollTop = feed.scrollHeight;
                    }""",
                    feed_selector,
                )
                await page.wait_for_timeout(2000)

                # Check if we reached the end of results
                end_of_list = await page.query_selector('span.HlvSq')
                if end_of_list:
                    self.logger.info(
                        f"[{city}] {query}: End of results at scroll {scroll_i + 1}"
                    )
                    break

            content = await page.content()
        finally:
            await page.close()

        sel = scrapy.Selector(text=content)

        # Extract detail page URLs from result cards
        detail_links = sel.css('a.hfpxzc::attr(href)').getall()

        self.logger.info(
            f"[{city}] {query}: Found {len(detail_links)} results"
        )

        for link in detail_links:
            if not link.startswith("http"):
                link = response.urljoin(link)

            yield scrapy.Request(
                link,
                callback=self.parse_detail,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod(
                            "wait_for_selector",
                            "h1",
                            timeout=20000,
                        ),
                    ],
                    "city": city,
                    "dealer_type": dealer_type,
                    "query": query,
                },
                errback=self.errback_close_page,
                dont_filter=True,
            )

    async def parse_detail(self, response):
        """Phase 2: Extract business details from a place detail page."""
        page = response.meta["playwright_page"]
        city = response.meta["city"]
        dealer_type = response.meta["dealer_type"]
        query = response.meta["query"]

        try:
            await page.wait_for_timeout(2000)
            content = await page.content()
        finally:
            await page.close()

        sel = scrapy.Selector(text=content)

        # --- Business name ---
        name = sel.css("h1::text").get("").strip()
        if not name:
            return

        # --- Phone via aria-label ---
        phone = ""
        phone_label = sel.css(
            '*[aria-label*="Phone:"]::attr(aria-label)'
        ).get("")
        if phone_label:
            phone = re.sub(r'^Phone:\s*', '', phone_label).strip()

        if not phone:
            # Fallback: data-tooltip or button with phone info
            phone_label = sel.css(
                'button[data-tooltip*="phone"]::attr(aria-label)'
            ).get("")
            if phone_label:
                phone = re.sub(r'^Phone:\s*', '', phone_label).strip()

        if not phone:
            # Fallback: tel: links
            tel_href = sel.css('a[href^="tel:"]::attr(href)').get("")
            if tel_href:
                phone = tel_href.replace("tel:", "").strip()

        # --- Address via aria-label ---
        address = ""
        address_label = sel.css(
            '*[aria-label*="Address:"]::attr(aria-label)'
        ).get("")
        if address_label:
            address = re.sub(r'^Address:\s*', '', address_label).strip()

        if not address:
            address_label = sel.css(
                'button[data-item-id="address"]::attr(aria-label)'
            ).get("")
            if address_label:
                address = re.sub(r'^Address:\s*', '', address_label).strip()

        # --- Rating ---
        rating = ""
        rating_label = sel.css(
            '*[aria-label*=" stars"]::attr(aria-label)'
        ).get("")
        if rating_label:
            match = re.search(r'([\d.]+)\s*stars?', rating_label)
            if match:
                rating = match.group(1)

        # --- Review count ---
        reviews = ""
        reviews_label = sel.css(
            '*[aria-label*=" reviews"]::attr(aria-label)'
        ).get("")
        if reviews_label:
            match = re.search(r'([\d,]+)\s*reviews?', reviews_label)
            if match:
                reviews = match.group(1).replace(",", "")

        # --- Pincode from address ---
        pincode = ""
        if address:
            pin_match = re.search(r'\b(\d{6})\b', address)
            if pin_match:
                pincode = pin_match.group(1)

        # --- Area from address ---
        area = ""
        if address:
            parts = [p.strip() for p in address.split(",")]
            if len(parts) > 2:
                area = parts[-2]
            elif len(parts) == 2:
                area = parts[0]

        self.logger.info(
            f"Scraped: {name} | Phone: {phone or 'N/A'} | {city}"
        )

        yield DealerItem(
            name=name,
            address=address,
            city=city,
            area=area,
            pincode=pincode,
            phone=phone,
            rating=rating,
            reviews=reviews,
            category=query,
            dealer_type=dealer_type,
            source="googlemaps",
            source_url=response.url,
        )

    async def errback_close_page(self, failure):
        """Close the Playwright page on request failure."""
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Request failed: {failure.request.url}")
