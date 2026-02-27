"""
Dealer Data Scraper - Main Runner
=================================
Scrapes battery & charger dealer data from JustDial, IndiaMART, and Google Maps.

Usage:
    python run.py                          # Run all spiders
    python run.py --spider justdial        # Run only JustDial spider
    python run.py --spider indiamart       # Run only IndiaMART spider
    python run.py --spider googlemaps      # Run only Google Maps spider
    python run.py --cities Delhi Mumbai    # Specific cities
    python run.py --max-pages 3            # Limit pages per category

Output:
    output/battery_dealers.csv
    output/charger_dealers.csv
    output/all_dealers.csv
"""

import argparse
import os

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def main():
    parser = argparse.ArgumentParser(description="Scrape battery & charger dealer data")
    parser.add_argument(
        "--spider",
        choices=["justdial", "indiamart", "googlemaps", "all"],
        default="all",
        help="Which spider to run (default: all)",
    )
    parser.add_argument(
        "--cities",
        nargs="+",
        default=None,
        help="Cities to scrape (JustDial/GoogleMaps). Default: top 10 Indian cities",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Max pages per category (or max scrolls for Google Maps)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable HTTP cache",
    )
    args = parser.parse_args()

    # Ensure we are in the right directory for scrapy.cfg
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    settings = get_project_settings()

    if args.no_cache:
        settings.set("HTTPCACHE_ENABLED", False)

    # Create output directory (same as pipeline: parent of project dir)
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output"
    )
    os.makedirs(output_dir, exist_ok=True)

    process = CrawlerProcess(settings)

    spiders_to_run = []
    if args.spider in ("justdial", "all"):
        spiders_to_run.append("justdial")
    if args.spider in ("indiamart", "all"):
        spiders_to_run.append("indiamart")
    if args.spider in ("googlemaps", "all"):
        spiders_to_run.append("googlemaps")

    for spider_name in spiders_to_run:
        kwargs = {}
        if spider_name == "justdial":
            if args.cities:
                kwargs["cities"] = ",".join(args.cities)
            if args.max_pages:
                kwargs["max_pages"] = args.max_pages
        elif spider_name == "indiamart":
            if args.max_pages:
                kwargs["max_pages"] = args.max_pages
        elif spider_name == "googlemaps":
            if args.cities:
                kwargs["cities"] = ",".join(args.cities)
            if args.max_pages:
                kwargs["max_scrolls"] = args.max_pages

        process.crawl(spider_name, **kwargs)

    print("\n" + "=" * 60)
    print("  DEALER DATA SCRAPER")
    print("=" * 60)
    print(f"  Spiders  : {', '.join(spiders_to_run)}")
    print(f"  Output   : {output_dir}")
    print("=" * 60 + "\n")

    process.start()

    # Summary
    print("\n" + "=" * 60)
    print("  SCRAPING COMPLETE!")
    print("=" * 60)
    for fname in ["battery_dealers.csv", "charger_dealers.csv", "all_dealers.csv"]:
        fpath = os.path.join(output_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                lines = sum(1 for _ in f) - 1  # subtract header
            print(f"  {fname}: {lines} records")
    print("=" * 60)


if __name__ == "__main__":
    main()
