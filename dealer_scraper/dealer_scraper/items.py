import scrapy


class DealerItem(scrapy.Item):
    """Common item for both battery and charger dealers."""
    name = scrapy.Field()
    address = scrapy.Field()
    city = scrapy.Field()
    phone = scrapy.Field()
    rating = scrapy.Field()
    reviews = scrapy.Field()
    category = scrapy.Field()
    dealer_type = scrapy.Field()  # 'battery' or 'charger'
    source = scrapy.Field()       # website name
    source_url = scrapy.Field()
    pincode = scrapy.Field()
    area = scrapy.Field()
