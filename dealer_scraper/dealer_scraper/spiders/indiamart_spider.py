import json
import scrapy
from dealer_scraper.items import DealerItem


class IndiaMartSpider(scrapy.Spider):
    """
    Spider to scrape battery and charger dealer data from IndiaMART.
    Uses __NEXT_DATA__ JSON embedded in the page source.
    Fast bulk scraper — phone numbers come from the Google Maps spider.
    """
    name = "indiamart"
    allowed_domains = ["indiamart.com", "dir.indiamart.com"]

    SEARCH_QUERIES = [
        ("car battery", "battery"),
        ("inverter battery", "battery"),
        ("lithium battery", "battery"),
        ("two wheeler battery", "battery"),
        ("solar battery", "battery"),
        ("ups battery", "battery"),
        ("battery charger", "charger"),
        ("ev charging station", "charger"),
        ("electric car charger", "charger"),
        ("electric bike charger", "charger"),
        ("industrial battery charger", "charger"),
    ]

    BIZ_FILTER = "40"
    MAX_PAGES = 10

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "HTTPCACHE_ENABLED": True,
        "HTTPCACHE_EXPIRATION_SECS": 86400,
    }

    def __init__(self, max_pages=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if max_pages is not None:
            self.MAX_PAGES = int(max_pages)

    def start_requests(self):
        for keyword, dealer_type in self.SEARCH_QUERIES:
            url = (
                f"https://dir.indiamart.com/search.mp"
                f"?ss={keyword.replace(' ', '+')}&biz={self.BIZ_FILTER}"
            )
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={
                    "keyword": keyword,
                    "dealer_type": dealer_type,
                    "page": 1,
                },
            )

    def parse(self, response):
        keyword = response.meta["keyword"]
        dealer_type = response.meta["dealer_type"]
        page = response.meta["page"]

        items_found = 0

        next_data_text = response.xpath(
            '//script[@id="__NEXT_DATA__"]/text()'
        ).get()

        if next_data_text:
            items_found = yield from self._parse_next_data(
                next_data_text, keyword, dealer_type, response.url
            )
        else:
            items_found = yield from self._parse_script_json(
                response, keyword, dealer_type
            )

        if items_found == 0:
            items_found = yield from self._parse_html(
                response, keyword, dealer_type
            )

        self.logger.info(f"[{keyword}] page {page}: {items_found} dealers found")

        # Pagination
        has_next = False
        if next_data_text:
            try:
                data = json.loads(next_data_text)
                search_resp = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("searchResponse", {})
                )
                has_next = search_resp.get("nextPage", False)
            except (json.JSONDecodeError, AttributeError):
                pass

        if has_next and page < self.MAX_PAGES and items_found > 0:
            next_page = page + 1
            base_url = response.url.split("&page=")[0]
            next_url = f"{base_url}&page={next_page}"
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={
                    "keyword": keyword,
                    "dealer_type": dealer_type,
                    "page": next_page,
                },
            )

    def _parse_next_data(self, json_text, keyword, dealer_type, page_url):
        """Parse the __NEXT_DATA__ JSON payload."""
        count = 0
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse __NEXT_DATA__ JSON")
            return

        search_resp = (
            data.get("props", {})
            .get("pageProps", {})
            .get("searchResponse", {})
        )
        results = search_resp.get("results", [])

        for result in results:
            fields = result.get("fields", {})
            item = self._fields_to_item(fields, keyword, dealer_type, page_url)
            if item:
                count += 1
                yield item

            for sub in fields.get("more_results", []):
                sub_fields = sub.get("fields", sub)
                item = self._fields_to_item(sub_fields, keyword, dealer_type, page_url)
                if item:
                    count += 1
                    yield item

        return count

    def _fields_to_item(self, fields, keyword, dealer_type, page_url):
        """Convert IndiaMART fields to a DealerItem."""
        name = fields.get("companyname", "").strip()
        if not name:
            return None

        phone = fields.get("phone", "")
        if isinstance(phone, list):
            phone = ", ".join(str(p) for p in phone if p)
        mobile = fields.get("mobile", "")
        if isinstance(mobile, list):
            mobile = ", ".join(str(m) for m in mobile if m)

        contact = ", ".join(filter(None, [str(phone), str(mobile)]))

        source_url = fields.get("desktop_title_url", page_url)
        if "?" in source_url:
            source_url = source_url.split("?")[0]

        return DealerItem(
            name=name,
            address=fields.get("address", ""),
            city=fields.get("city", ""),
            area=fields.get("locality", ""),
            pincode=fields.get("zipcode", ""),
            phone=contact,
            rating=str(fields.get("supplier_rating", "")),
            reviews=str(fields.get("rating_count", "")),
            category=fields.get("title", keyword),
            dealer_type=dealer_type,
            source="indiamart",
            source_url=source_url,
        )

    def _parse_script_json(self, response, keyword, dealer_type):
        """Try to find product data in other script tags."""
        count = 0
        scripts = response.xpath("//script/text()").getall()

        for script in scripts:
            if "companyname" not in script:
                continue
            try:
                for prefix in ["window.__INITIAL_STATE__=", "window.__DATA__="]:
                    if prefix in script:
                        json_str = script.split(prefix, 1)[1].rstrip(";")
                        data = json.loads(json_str)
                        if isinstance(data, dict):
                            for key, val in data.items():
                                if isinstance(val, list):
                                    for entry in val:
                                        if isinstance(entry, dict) and "companyname" in entry:
                                            item = self._fields_to_item(
                                                entry, keyword, dealer_type, response.url
                                            )
                                            if item:
                                                count += 1
                                                yield item
            except (json.JSONDecodeError, IndexError):
                continue

        return count

    def _parse_html(self, response, keyword, dealer_type):
        """Fallback HTML-based parsing."""
        count = 0

        for card in response.css(".lcnt, .prd-card, .card"):
            name = card.css(
                ".lcname::text, .company-name::text, .prd-card-name::text"
            ).get("").strip()
            if not name:
                continue

            city = card.css(".cloc::text, .city-name::text").get("").strip()
            address = card.css(".adr::text, .address::text").get("").strip()

            yield DealerItem(
                name=name,
                address=address,
                city=city,
                area="",
                pincode="",
                phone="",
                rating="",
                reviews="",
                category=keyword,
                dealer_type=dealer_type,
                source="indiamart",
                source_url=response.url,
            )
            count += 1

        return count
