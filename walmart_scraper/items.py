# # Define here the models for your scraped items
# #
# # See documentation in:
# # https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.item import Item, Field


class WalmartScraperItem(Item):
    # define the fields for your item here like:
    web_scraper_start_url = Field()
    product_id = Field()
    product_type = Field()
    product_title = Field()
    product_brand = Field()
    product_rating = Field()
    product_availabilityStatus = Field()
    product_price = Field()
    product_original_price = Field()
    product_currencyUnit = Field()
    product_url_href = Field()
    product_sellername = Field()
    product_upc = Field()
    product_sku = Field()
    product_review_count = Field()
    product_image_1_src = Field()
    product_image_2_src = Field()
    product_image_3_src = Field()
    product_image_4_src = Field()
    product_image_5_src = Field()
    product_category = Field()
    product_variants = Field()
    sys_run_date = Field()


# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

# import scrapy


# class WalmartScraperItem(scrapy.Item):
#     # define the fields for your item here like:
#     # name = scrapy.Field()
#     pass
