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
        "DOWNLOAD_DELAY": 10,  # Adjust delay between requests to respect the site's rate limit
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
            "https://www.walmart.com/shop/deals?facet=exclude_oos%3AShow+available+items+only%7C%7Cretailer_type%3AWalmart&max_price=65&",
            "https://www.walmart.com/shop/household-essentials-stock-up?povid=EDN_EDNCP_Feb_itemcarousel_carousel_HHE&facet=retailer_type%3AWalmart%7C%7Cexclude_oos%3AShow+available+items+only&",
            "https://www.walmart.com/browse/health/first-aid/976760_2571007?sort=best_seller&povid=FirstAidCP_Itemcarousel_Firstaidessentials_Rweb_7523&facet=exclude_oos%3AShow+available+items+only%7C%7Cretailer_type%3AWalmart&",
            "https://www.walmart.com/browse/family-favorites/0?_refineresult=true&_be_shelf_id=2086032&search_sort=100&facet=shelf_id%3A2086032%7C%7Cretailer_type%3AWalmart%7C%7Cexclude_oos%3AShow+available+items+only&povid=976759_itemcarousel_976794_Familyfavorites_Viewall_Rweb_Jun_27&",
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
                meta={"page": 1, "url": walmart_search_url},
            )

    def parse_search_results(self, response):
        page = response.meta["page"]
        walmart_url = response.meta["url"]
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
                    walmart_search_url = walmart_url + urlencode(payload)
                    yield scrapy.Request(
                        url=walmart_search_url,
                        callback=self.parse_search_results,
                        meta={"page": p, "url": walmart_search_url},
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

        def extract_pack_quantity(text):
            if not text:
                return None
            # Updated regex to handle titles that are just numbers or contain "pack" variations
            pack_pattern = re.compile(
                r"^(\d+)$|(\d+)\s*pack|pack\s*of\s*(\d+)", re.IGNORECASE
            )
            match = pack_pattern.search(text)
            if match:
                # Check each group for a match and extract the first non-None group
                for group in match.groups():
                    if group is not None:
                        return int(group)
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
                ".*size.*",
                desired_product_id,
            )
            attr_variants = find_variant_by_pattern(
                raw_product_data.get("variantCriteria", []),
                ".*scent.*",
                desired_product_id,
            )
            ## Assuming you have already defined 'product_title' and 'desired_product_id'
            product_title = raw_product_data.get("name", "")

            # First, try to extract pack quantity directly from the product title
            pack_quantity = extract_pack_quantity(product_title)

            # If 'pack_quantity' is None, then attempt to find and extract pack info from variant criteria
            if pack_quantity is None:
                pack_variant_title = find_variant_by_pattern(
                    raw_product_data.get("variantCriteria", []),
                    ".*number_of.*|.*multipack.*|.*pack.*",
                    desired_product_id,
                )
                if pack_variant_title:
                    # Assuming 'pack_variant_title' returns a string that can be passed to 'extract_pack_quantity'
                    pack_quantity = extract_pack_quantity(pack_variant_title)
            # After extracting product details, calculate price per pack and check availability
            product_price = raw_product_data["priceInfo"]["currentPrice"].get(
                "price", 0
            )
            product_availabilityStatus = raw_product_data.get("availabilityStatus", "")
            pack_quantity = (
                pack_quantity if pack_quantity is not None else 1
            )  # Ensure pack_quantity is at least 1 to avoid division by zero

            price_per_pack = (
                product_price / pack_quantity if pack_quantity else float("inf")
            )  # Calculate price per pack, handle division by zero

            product_sellername = raw_product_data.get("sellerName", "")
            # Check if price per pack is less than or equal to 55 and product is not out of stock
            # if (
            #     price_per_pack <= 55
            #     and product_availabilityStatus.lower() != "out_of_stock"
            #     and product_sellername.lower() == "walmart.com"
            # ):
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
                        "attr": attr_variants,
                        "color": color_variants,
                        "size": size_variants,
                        "pack": pack_quantity,
                    }
                ),
                "sys_run_date": datetime.now().strftime(
                    "%Y-%m-%d"
                ),  # Include current date
            }
        else:
            self.logger.info(
                f"Skipping product {raw_product_data.get('id')} due to price,seller or availability constraints."
            )

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
