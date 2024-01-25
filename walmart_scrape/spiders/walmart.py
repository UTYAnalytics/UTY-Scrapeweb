import json
import math
import scrapy
from urllib.parse import urlencode
from datetime import datetime
from walmart_scrape.items import WalmartScraperItem


class WalmartSpider(scrapy.Spider):
    name = "walmart"

    # custom_settings = {
    #     "FEEDS": {
    #         "data/%(name)s_%(time)s.csv": {
    #             "format": "csv",
    #         }
    #     }
    # }

    def start_requests(self):
        keyword_list = [
            "Snacks",
            "Beverages",
            "Canned Goods",
            "Frozen Foods",
            "Dairy",
            "Fresh Produce",
            "Bakery",
            "Pantry Staples",
            "Apples",
            "Milk",
            "Bread",
            "Eggs",
            "Chicken",
            "Pasta",
            "Rice",
            "Cereal",
            "Kellogg",
            "Kraft",
            "General Mills",
            "Coca-Cola",
            "Nestle",
            "Heinz",
            "Campbell",
            "Gluten-Free",
            "Organic",
            "Vegan",
            "Low-Sodium",
            "Sugar-Free",
            "Bulk",
            "Family Size",
            "Individual Serving",
            "Value Pack",
            "Holiday Specials",
            "Party Supplies",
            "BBQ Essentials",
            "Organic",
            "Low-Fat",
            "High-Fiber",
            "Non-GMO",
            "Keto",
            "Paleo",
            "Atkins",
            "grocery",
        ]
        # for keyword in keyword_list:
        payload = {
            # "q": keyword,
            # "sort": "price_low",
            "page": 1,
            "affinityOverride": "default",
        }
        walmart_search_url = "https://www.walmart.com/shop/deals?" + urlencode(
            payload
        )  # "https://www.walmart.com/search?" + urlencode(payload)
        yield scrapy.Request(
            url=walmart_search_url,
            callback=self.parse_search_results,
            meta={
                # "keyword": keyword,
                "page": 1
            },
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
        def find_variant(variant_criteria, variant_id, desired_product_id):
            if variant_criteria is None:
                return None

            return next(
                (
                    variant["name"]
                    for variant in variant_criteria.get("variantList", [])
                    if desired_product_id in variant.get("products", [])
                ),
                None,
            )

        script_tag = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        if script_tag is not None:
            json_blob = json.loads(script_tag)
            raw_product_data = json_blob["props"]["pageProps"]["initialData"]["data"][
                "product"
            ]
            desired_product_id = raw_product_data.get("id")
            # Extract color variants
            color_variants = find_variant(
                next(
                    (
                        variant_criteria
                        for variant_criteria in raw_product_data.get(
                            "variantCriteria", []
                        )
                        if variant_criteria["id"] == "actual_color"
                    ),
                    None,
                ),
                "actual_color",
                desired_product_id,
            )

            # Extract clothing size variants
            clothing_size_variants = find_variant(
                next(
                    (
                        variant_criteria
                        for variant_criteria in raw_product_data.get(
                            "variantCriteria", []
                        )
                        if variant_criteria["id"] == "clothing_size"
                    ),
                    None,
                ),
                "clothing_size",
                desired_product_id,
            )

            yield {
                "web_scraper_start_url": "walmart",
                "product_id": raw_product_data.get("id")
                if raw_product_data.get("id")
                else None,
                "product_type": raw_product_data.get("type")
                if raw_product_data.get("type")
                else None,
                "product_title": raw_product_data.get("name")
                if raw_product_data.get("name")
                else None,
                "product_brand": raw_product_data.get("brand")
                if raw_product_data.get("brand")
                else None,
                "product_rating": raw_product_data.get("averageRating")
                if raw_product_data.get("averageRating")
                else None,
                "product_availabilityStatus": raw_product_data.get("availabilityStatus")
                if raw_product_data.get("availabilityStatus")
                else None,
                "product_price": raw_product_data["priceInfo"]["currentPrice"].get(
                    "price"
                )
                if raw_product_data["priceInfo"]["currentPrice"].get("price")
                else None,
                "product_original_price": raw_product_data["priceInfo"]["wasPrice"].get(
                    "price"
                )
                if raw_product_data["priceInfo"]["wasPrice"]
                else None,
                "product_currencyUnit": raw_product_data["priceInfo"][
                    "currentPrice"
                ].get("currencyUnit")
                if raw_product_data["priceInfo"]["currentPrice"]
                else None,
                "product_url_href": response.meta["product_url"]
                if response.meta["product_url"]
                else None,  # Include product URL in the output
                "product_sellername": raw_product_data.get("sellerName")
                if raw_product_data.get("sellerName")
                else None,
                "product_upc": raw_product_data.get("upc")
                if raw_product_data.get("upc")
                else None,
                "product_sku": raw_product_data.get("itemId")
                if raw_product_data.get("itemId")
                else None,
                "product_review_count": raw_product_data.get("numberOfReviews")
                if raw_product_data.get("numberOfReviews")
                else None,
                "product_image_1_src": raw_product_data["imageInfo"].get("thumbnailUrl")
                if raw_product_data["imageInfo"].get("thumbnailUrl")
                else None,
                "product_image_2_src": raw_product_data["imageInfo"]["allImages"][1][
                    "url"
                ]
                if len(raw_product_data["imageInfo"]["allImages"]) >= 2
                else None,
                "product_image_3_src": raw_product_data["imageInfo"]["allImages"][2][
                    "url"
                ]
                if len(raw_product_data["imageInfo"]["allImages"]) >= 3
                else None,
                "product_image_4_src": raw_product_data["imageInfo"]["allImages"][3][
                    "url"
                ]
                if len(raw_product_data["imageInfo"]["allImages"]) >= 4
                else None,
                "product_image_5_src": raw_product_data["imageInfo"]["allImages"][4][
                    "url"
                ]
                if len(raw_product_data["imageInfo"]["allImages"]) >= 5
                else None,
                "product_category": raw_product_data["category"]["path"][1]["name"]
                if raw_product_data["category"]["path"][1]["name"]
                else None,
                "product_variants": json.dumps(
                    {
                        "color": color_variants,
                        "size": clothing_size_variants,
                    }
                ),
                "sys_run_date": datetime.now().strftime(
                    "%Y-%m-%d"
                ),  # Include current date
            }
