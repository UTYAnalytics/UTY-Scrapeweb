import json
import math
import scrapy
from urllib.parse import urlencode
from datetime import datetime
from walmart_scraper.items import WalmartScraperItem
import time
import re


class WalmartSpider(scrapy.Spider):
    name = "walmart"

    custom_settings = {
        "RETRY_HTTP_CODES": [429, 500, 502, 503, 504],
        "RETRY_TIMES": 10,  # Adjust based on how aggressively you wish to retry
        "DOWNLOAD_DELAY": 1,  # Adjust delay between requests to respect the site's rate limit
        # Uncomment and adjust if you want to specify output format and path dynamically
        # "FEEDS": {
        #     "data/%(name)s_%(time)s.csv": {
        #         "format": "csv",
        #     }
        # },
    }

    def start_requests(self):
        # List of Walmart search URLs
        search_urls = [
            "https://www.walmart.com/shop/deals?",
            "https://www.walmart.com/shop/deals/household-essentials?povid=HHE_HHECP_hubspoke_shopbyprice_hhedeals&",
            "https://www.walmart.com/browse/976759?athcpid=7cbe8a0a-c5fe-4839-a851-edb3ec71638c&athpgid=AthenaContentPage&athznid=athenaModuleZone&athmtid=AthenaItemCarousel&athtvid=4&athena=true&",  # Food
            "https://www.walmart.com/browse/personal-care/1005862_1071969?povid=EDN_EDNCP_Feb_itemcarousel_carousel_PC&",  # All Bath & Body
            # Add more URLs as needed
        ]

        for walmart_search_url in search_urls:
            payload = {
                "page": 1,
                "affinityOverride": "default",
            }

            yield scrapy.Request(
                url=walmart_search_url + urlencode(payload),
                callback=self.parse_search_results,
                meta={"page": 1},
            )

    def parse_search_results(self, response):
        page = response.meta["page"]
        # keyword = response.meta["keyword"]
        script_tag = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if script_tag is not None:
            json_blob = json.loads(script_tag)

            ## Request Product Page
            product_list = json_blob["props"]["pageProps"]["initialData"][
                "searchResult"
            ]["itemStacks"][0]["items"]
            for idx, product in enumerate(product_list):
                walmart_product_url = (
                    "https://www.walmart.com"
                    + product.get("canonicalUrl", "").split("?")[0]
                )
                yield scrapy.Request(
                    url=walmart_product_url,
                    callback=self.parse_product_data,
                    meta={
                        # "keyword": keyword,
                        "page": page,
                        "position": idx + 1,
                        "product_url": walmart_product_url,  # Include product URL in the meta
                    },
                )

            ## Request Next Page
            if page == 1:
                total_product_count = json_blob["props"]["pageProps"]["initialData"][
                    "searchResult"
                ]["itemStacks"][0]["count"]
                max_pages = math.ceil(total_product_count / 40)
                if max_pages > 25:
                    max_pages = 25
                for p in range(2, max_pages):
                    payload = {
                        # "q": keyword,
                        # "sort": "price_low",
                        "page": p,
                        "affinityOverride": "default",
                    }
                    walmart_search_url = (
                        "https://www.walmart.com/shop/deals?" + urlencode(payload)
                    )
                    yield scrapy.Request(
                        url=walmart_search_url,
                        callback=self.parse_search_results,
                        meta={
                            # "keyword": keyword,
                            "page": p
                        },
                    )

    def parse_product_data(self, response):
        script_tag = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if script_tag is not None:
            json_blob = json.loads(script_tag)
            # Extract product URLs from the "variantsMap" section
            variants_map = json_blob["props"]["pageProps"]["initialData"]["data"][
                "product"
            ]["variantsMap"]
            if variants_map:
                # Request Product Page
                product_list = [
                    variant["productUrl"] for variant in variants_map.values()
                ]
                for product in product_list:
                    walmart_product_url = (
                        "https://www.walmart.com" + product.split("?")[0]
                    )
                    yield scrapy.Request(
                        url=walmart_product_url,
                        callback=self.parse_product_detail,
                        meta={
                            # "keyword": keyword,
                            "product_url": walmart_product_url,  # Include product URL in the meta
                        },
                    )
            self.parse_product_detail

    def parse_product_detail(self, response):
        # Function to check if product_id is in the list of products for a variant
        def find_variant_by_pattern(all_variant_criteria, pattern, desired_product_id):
            if all_variant_criteria is None:
                return None

            # Compile the regex pattern for case-insensitive search
            pattern_regex = re.compile(pattern, re.IGNORECASE)

            # Search for criteria that matches the pattern
            for variant_criteria in all_variant_criteria:
                if pattern_regex.search(variant_criteria["id"]):
                    # Once the matching criteria is found, search its variantList
                    return next(
                        (
                            variant["name"]
                            for variant in variant_criteria.get("variantList", [])
                            if desired_product_id in variant.get("products", [])
                        ),
                        None,
                    )
            return None

        script_tag = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if script_tag is not None:
            json_blob = json.loads(script_tag)
            raw_product_data = json_blob["props"]["pageProps"]["initialData"]["data"][
                "product"
            ]
            desired_product_id = raw_product_data.get("id")

            # Extract color and size variants using the updated function
            color_variants = find_variant_by_pattern(
                raw_product_data.get("variantCriteria", []),
                ".*color.*",
                desired_product_id,
            )
            size_variants = find_variant_by_pattern(
                raw_product_data.get("variantCriteria", []),
                ".*size.*|.*number_of.*|.*multipack.*",
                desired_product_id,
            )

            yield {
                "web_scraper_start_url": "walmart",
                "product_id": (
                    raw_product_data.get("id") if raw_product_data.get("id") else None
                ),
                "product_type": (
                    raw_product_data.get("type")
                    if raw_product_data.get("type")
                    else None
                ),
                "product_title": (
                    raw_product_data.get("name")
                    if raw_product_data.get("name")
                    else None
                ),
                "product_brand": (
                    raw_product_data.get("brand")
                    if raw_product_data.get("brand")
                    else None
                ),
                "product_rating": (
                    raw_product_data.get("averageRating")
                    if raw_product_data.get("averageRating")
                    else None
                ),
                "product_availabilityStatus": (
                    raw_product_data.get("availabilityStatus")
                    if raw_product_data.get("availabilityStatus")
                    else None
                ),
                "product_price": (
                    raw_product_data["priceInfo"]["currentPrice"].get("price")
                    if raw_product_data["priceInfo"]["currentPrice"].get("price")
                    else None
                ),
                "product_original_price": (
                    raw_product_data["priceInfo"]["wasPrice"].get("price")
                    if raw_product_data["priceInfo"]["wasPrice"]
                    else None
                ),
                "product_currencyUnit": (
                    raw_product_data["priceInfo"]["currentPrice"].get("currencyUnit")
                    if raw_product_data["priceInfo"]["currentPrice"]
                    else None
                ),
                "product_url_href": (
                    response.meta["product_url"]
                    if response.meta["product_url"]
                    else None
                ),  # Include product URL in the output
                "product_sellername": (
                    raw_product_data.get("sellerName")
                    if raw_product_data.get("sellerName")
                    else None
                ),
                "product_upc": (
                    raw_product_data.get("upc") if raw_product_data.get("upc") else None
                ),
                "product_sku": (
                    raw_product_data.get("itemId")
                    if raw_product_data.get("itemId")
                    else None
                ),
                "product_review_count": (
                    raw_product_data.get("numberOfReviews")
                    if raw_product_data.get("numberOfReviews")
                    else None
                ),
                "product_image_1_src": (
                    raw_product_data["imageInfo"].get("thumbnailUrl")
                    if raw_product_data["imageInfo"].get("thumbnailUrl")
                    else None
                ),
                "product_image_2_src": (
                    raw_product_data["imageInfo"]["allImages"][1]["url"]
                    if len(raw_product_data["imageInfo"]["allImages"]) >= 2
                    else None
                ),
                "product_image_3_src": (
                    raw_product_data["imageInfo"]["allImages"][2]["url"]
                    if len(raw_product_data["imageInfo"]["allImages"]) >= 3
                    else None
                ),
                "product_image_4_src": (
                    raw_product_data["imageInfo"]["allImages"][3]["url"]
                    if len(raw_product_data["imageInfo"]["allImages"]) >= 4
                    else None
                ),
                "product_image_5_src": (
                    raw_product_data["imageInfo"]["allImages"][4]["url"]
                    if len(raw_product_data["imageInfo"]["allImages"]) >= 5
                    else None
                ),
                "product_category": (
                    raw_product_data["category"]["path"][1]["name"]
                    if raw_product_data["category"]["path"][1]["name"]
                    else None
                ),
                "product_variants": json.dumps(
                    {
                        "color": color_variants,
                        "size": size_variants,
                    }
                ),
                "sys_run_date": datetime.now().strftime(
                    "%Y-%m-%d"
                ),  # Include current date
            }

    def retry_request(self, response):
        """Retry request with exponential backoff."""
        retry_times = response.meta.get("retry_times", 0) + 1
        if retry_times <= self.custom_settings.get("RETRY_TIMES", 10):
            wait_time = math.pow(2, retry_times)  # Exponential backoff
            self.logger.info(f"Waiting {wait_time} seconds to retry...")
            time.sleep(wait_time)
            return response.request.replace(
                meta={"retry_times": retry_times}, dont_filter=True
            )
