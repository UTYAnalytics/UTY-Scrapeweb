# pipelines.py

import psycopg2
import json


class PostgresNoDuplicatesPipeline:
    def __init__(self):
        ## Connection Details
        hostname = "db.sxoqzllwkjfluhskqlfl.supabase.co"
        database = "postgres"
        username = "postgres"
        password = "5giE*5Y5Uexi3P2"

        ## Create/Connect to database
        self.connection = psycopg2.connect(
            host=hostname, user=username, password=password, dbname=database
        )

        ## Create cursor, used to execute commands
        self.cur = self.connection.cursor()

        ## Create quotes table if none exists
        # self.cur.execute("""
        # CREATE TABLE IF NOT EXISTS quotes(
        #     id serial PRIMARY KEY,
        #     content text,
        #     tags text,
        #     author VARCHAR(255)
        # )
        # """)

    def process_item(self, item, spider):
        try:
            product_price = float(item.get("product_price", 0))
            product_availabilityStatus = item.get("product_availabilityStatus", "")
            product_variants = json.loads(item.get("product_variants", "{}"))

            # Attempt to retrieve 'pack' value; use 1 if not found or if None
            pack_quantity = product_variants.get("pack")
            if pack_quantity is None:
                pack_quantity = 1
            else:
                try:
                    pack_quantity = int(pack_quantity)
                except ValueError:
                    # Log the error and use a default value if conversion fails
                    spider.logger.warn(
                        f"Invalid pack quantity for item {item['product_id']}: {pack_quantity}. Defaulting to 1."
                    )
                    pack_quantity = 1

            # Calculate price per pack
            price_per_pack = product_price / pack_quantity

        except ValueError as e:
            spider.logger.warn(f"Error processing item {item['product_id']}: {e}")
            return item

        # Check if the price per pack is less than or equal to 55 and product is in stock
        if price_per_pack <= 55 and product_availabilityStatus != "OUT_OF_STOCK":
            # Check if product_id and sys_run_date already exist in the database
            self.cur.execute(
                """SELECT * FROM seller_product_data WHERE product_id = %s AND sys_run_date = %s""",
                (item["product_id"], item["sys_run_date"]),
            )
            result = self.cur.fetchone()

            if result:
                spider.logger.warn("Item already in database: %s" % item["product_id"])
            else:
                # Insert data into the database as the conditions are met
                self._insert_item(item, spider)
        else:
            spider.logger.info(
                f"Item does not meet criteria for insertion: {item['product_id']}"
            )

        return item

    def _insert_item(self, item, spider):
        # Define insert statement and execute
        self.cur.execute(
            """
            INSERT INTO seller_product_data 
            (web_scraper_start_url, product_id, product_type, product_title, product_brand, product_rating,
            product_availabilityStatus, product_price, product_original_price, product_currencyUnit, 
            product_url_href, product_sellername, product_upc, product_sku, product_review_count,
            product_image_1_src, product_image_2_src, product_image_3_src, product_image_4_src, 
            product_image_5_src, product_category, product_variants, sys_run_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                item["web_scraper_start_url"],
                item["product_id"],
                item["product_type"],
                item["product_title"],
                item["product_brand"],
                item["product_rating"],
                item["product_availabilityStatus"],
                item["product_price"],
                item["product_original_price"],
                item["product_currencyUnit"],
                item["product_url_href"],
                item["product_sellername"],
                item["product_upc"],
                item["product_sku"],
                item["product_review_count"],
                item["product_image_1_src"],
                item["product_image_2_src"],
                item["product_image_3_src"],
                item["product_image_4_src"],
                item["product_image_5_src"],
                item["product_category"],
                item["product_variants"],
                item["sys_run_date"],
            ),
        )

        # Commit the transaction
        self.connection.commit()
        spider.logger.info(f"Item inserted: {item['product_id']}")
        # else:
        #     ## If product price is greater than 55, log message and skip insertion
        #     spider.logger.info(
        #         "Item price exceeds limit (>$55) and will not be inserted: %s"
        #         % item["product_id"]
        #     )

    def close_spider(self, spider):
        ## Close cursor & connection to database
        self.cur.close()
        self.connection.close()
