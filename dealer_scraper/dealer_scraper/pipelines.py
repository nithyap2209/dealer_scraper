import csv
import os
import re

from itemadapter import ItemAdapter


class CleanDataPipeline:
    """Clean and normalize scraped data."""

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Strip whitespace from all string fields
        for field_name in adapter.field_names():
            value = adapter.get(field_name)
            if isinstance(value, str):
                # Collapse whitespace and strip
                value = re.sub(r'\s+', ' ', value).strip()
                adapter[field_name] = value

        # Clean phone numbers - keep only digits, +, -, spaces
        phone = adapter.get("phone", "")
        if phone:
            adapter["phone"] = re.sub(r'[^\d+\-\s,]', '', phone).strip()

        # Normalize rating to float
        rating = adapter.get("rating")
        if rating:
            try:
                adapter["rating"] = str(round(float(re.sub(r'[^\d.]', '', str(rating))), 1))
            except (ValueError, TypeError):
                adapter["rating"] = ""

        return item


class DuplicateFilterPipeline:
    """Filter out duplicate dealers based on name+city OR phone number."""

    def __init__(self):
        self.seen_name_city = set()
        self.seen_phones = set()

    def process_item(self, item, spider):
        from scrapy.exceptions import DropItem

        adapter = ItemAdapter(item)
        name = (adapter.get("name") or "").lower().strip()
        city = (adapter.get("city") or "").lower().strip()
        phone = (adapter.get("phone") or "").strip()

        if not name:
            raise DropItem("Missing dealer name")

        # Check 1: Duplicate by name + city
        name_city_key = f"{name}|{city}"
        if name_city_key in self.seen_name_city:
            raise DropItem(f"Duplicate (name+city): {name} in {city}")

        # Check 2: Duplicate by phone number
        if phone:
            normalized = re.sub(r'[^\d]', '', phone)
            # Remove leading 91 (India country code)
            if normalized.startswith('91') and len(normalized) == 12:
                normalized = normalized[2:]
            # Only dedup on valid 10-digit Indian numbers
            if len(normalized) == 10:
                if normalized in self.seen_phones:
                    raise DropItem(f"Duplicate (phone): {name} - {phone}")
                self.seen_phones.add(normalized)

        self.seen_name_city.add(name_city_key)
        return item


class CsvExportPipeline:
    """Export items to separate CSV files by dealer_type.

    Uses append mode so that multiple spiders running sequentially
    all contribute to the same output files.
    """

    FIELDS = [
        "name", "address", "area", "city", "pincode",
        "phone", "rating", "reviews", "category",
        "dealer_type", "source", "source_url",
    ]

    def open_spider(self, spider):
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), "output")
        os.makedirs(self.output_dir, exist_ok=True)

        self.files = {}
        self.writers = {}

        for key in ("battery", "charger", "all"):
            fname = "all_dealers.csv" if key == "all" else f"{key}_dealers.csv"
            filepath = os.path.join(self.output_dir, fname)

            # Append if file already exists and has content, else write fresh
            file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 0
            mode = "a" if file_exists else "w"

            f = open(filepath, mode, newline="", encoding="utf-8")
            writer = csv.DictWriter(f, fieldnames=self.FIELDS, extrasaction="ignore")

            # Only write header if this is a new file
            if not file_exists:
                writer.writeheader()

            self.files[key] = f
            self.writers[key] = writer

        spider.logger.info(f"CSV output directory: {self.output_dir}")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        row = dict(adapter)
        dealer_type = row.get("dealer_type", "battery")

        # Write to type-specific file
        if dealer_type in self.writers:
            self.writers[dealer_type].writerow(row)
            self.files[dealer_type].flush()

        # Write to combined file
        self.writers["all"].writerow(row)
        self.files["all"].flush()

        return item

    def close_spider(self, spider):
        for f in self.files.values():
            f.close()

        for key in self.files:
            fname = "all_dealers.csv" if key == "all" else f"{key}_dealers.csv"
            filepath = os.path.join(self.output_dir, fname)
            spider.logger.info(f"Saved: {filepath}")
