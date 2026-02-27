# dealer_scraper
A Scrapy web scraping application that collects battery dealer and EV charger dealer data (name, address, phone, rating) from Google Maps, JustDial, and IndiaMART across major Indian cities — without using any paid APIs. Uses Playwright for JavaScript rendering to extract phone numbers from Google Maps.
# Battery & Charger Dealer Data Scraper

A Scrapy-based web scraping application that collects battery dealer and EV charger dealer data from multiple Indian business directories — **without using any paid APIs**.

## Data Sources

| Source | Method | Phone Numbers |
|--------|--------|---------------|
| **Google Maps** | Playwright (headless browser) | Yes (96%+ success) |
| **JustDial** | JSON-LD structured data | No (protected by JS) |
| **IndiaMART** | `__NEXT_DATA__` JSON parsing | No (behind login wall) |

## Data Fields

| Field | Description |
|-------|-------------|
| `name` | Business / dealer name |
| `address` | Full street address |
| `area` | Locality / area |
| `city` | City name |
| `pincode` | PIN code |
| `phone` | Phone number (from Google Maps) |
| `rating` | Star rating |
| `reviews` | Review count |
| `category` | Dealer category |
| `dealer_type` | `battery` or `charger` |
| `source` | Source website |
| `source_url` | Original listing URL |

## Setup

### Prerequisites

- Python 3.10+

### Installation

```bash
# Clone the repo
git clone https://github.com/<your-username>/dealer-data-scraper.git
cd dealer-data-scraper

# Install dependencies
pip install scrapy scrapy-playwright itemadapter

# Install Playwright browser (required for Google Maps)
playwright install chromium
```

## Usage

```bash
cd dealer_scraper

# Run all spiders (JustDial + IndiaMART + Google Maps)
python run.py

# Run a specific spider
python run.py --spider googlemaps
python run.py --spider justdial
python run.py --spider indiamart

# Scrape specific cities only
python run.py --cities Delhi Mumbai Bangalore

# Limit pages / scroll depth
python run.py --max-pages 3

# Combine options
python run.py --spider googlemaps --cities Delhi Chennai --max-pages 5
```

### Run Individual Spiders via Scrapy CLI

```bash
cd dealer_scraper

# Google Maps - Delhi only, 5 scroll iterations
python -m scrapy crawl googlemaps -a cities=Delhi -a max_scrolls=5

# JustDial - Mumbai only, 2 pages per category
python -m scrapy crawl justdial -a cities=Mumbai -a max_pages=2

# IndiaMART - 3 pages per keyword
python -m scrapy crawl indiamart -a max_pages=3
```

## Output

Results are saved to the `output/` directory:

```
output/
  battery_dealers.csv   # Battery dealer records only
  charger_dealers.csv   # EV charger dealer records only
  all_dealers.csv       # Combined dataset
```

## Project Structure

```
dealer_scraper/
├── dealer_scraper/
│   ├── items.py              # DealerItem schema (12 fields)
│   ├── pipelines.py          # Data cleaning, phone-based dedup, CSV export
│   ├── settings.py           # Scrapy + Playwright configuration
│   └── spiders/
│       ├── googlemaps_spider.py   # Google Maps (Playwright, phone numbers)
│       ├── justdial_spider.py     # JustDial (JSON-LD, bulk listings)
│       └── indiamart_spider.py    # IndiaMART (__NEXT_DATA__, B2B data)
├── run.py                    # CLI runner (--spider, --cities, --max-pages)
└── scrapy.cfg
```

## How It Works

### Google Maps Spider
1. Searches Google Maps for dealer categories across Indian cities
2. Uses Playwright headless browser to render the JavaScript SPA
3. Scrolls the results feed to load all listings
4. Visits each dealer's detail page to extract phone, address, and rating via `aria-label` selectors

### JustDial Spider
1. Fetches category listing pages for battery/charger dealers
2. Parses `application/ld+json` (JSON-LD) structured data for business info
3. Paginates through `/page-N` URLs
4. Covers 5 categories across 10 cities

### IndiaMART Spider
1. Searches IndiaMART directory with `biz=40` (Retailers & Dealers) filter
2. Extracts supplier data from `__NEXT_DATA__` JSON embedded in the page
3. Covers 11 search keywords (battery + charger categories)

### Data Pipeline
1. **CleanDataPipeline** - Normalizes whitespace, phone formats, and ratings
2. **DuplicateFilterPipeline** - Removes duplicates by name+city AND by phone number
3. **CsvExportPipeline** - Writes to separate CSV files by dealer type

## Cities Covered (Default)

Delhi, Mumbai, Bangalore, Chennai, Hyderabad, Kolkata, Pune, Ahmedabad, Jaipur, Lucknow

## Dealer Categories

**Battery Dealers:** Car Battery, Inverter Battery, Lithium Battery, Solar Battery, Two Wheeler Battery, UPS Battery

**Charger Dealers:** EV Charging Station, Electric Car Charger, Electric Bike Charger, Battery Charger, Industrial Battery Charger

## Notes

- Google Maps spider uses Playwright (headless Chromium) and is slower but provides phone numbers
- JustDial and IndiaMART spiders use plain HTTP requests and are faster for bulk data
- Built-in rate limiting and auto-throttle to be respectful to source websites
- HTTP caching enabled for JustDial/IndiaMART to speed up development reruns

## License

MIT
