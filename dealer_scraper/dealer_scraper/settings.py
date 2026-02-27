BOT_NAME = "dealer_scraper"

SPIDER_MODULES = ["dealer_scraper.spiders"]
NEWSPIDER_MODULE = "dealer_scraper.spiders"

ADDONS = {}

# -----------  Playwright (headless browser) integration  -----------
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 60000,
}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000

# Browser-like user agent to avoid blocks
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Respect robots.txt
ROBOTSTXT_OBEY = False

# Throttle to be polite
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

# Default headers
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

# Retry settings
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Enable AutoThrottle
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Pipelines
ITEM_PIPELINES = {
    "dealer_scraper.pipelines.CleanDataPipeline": 100,
    "dealer_scraper.pipelines.DuplicateFilterPipeline": 200,
    "dealer_scraper.pipelines.CsvExportPipeline": 300,
}

# Output encoding
FEED_EXPORT_ENCODING = "utf-8"

# Logging
LOG_LEVEL = "INFO"

# Cache — disabled by default since Playwright spiders need live rendering.
# Non-Playwright spiders can re-enable via custom_settings.
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 86400
HTTPCACHE_DIR = "httpcache"
