# pipelines.py

import psycopg2


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
        ## Check to see if the product's price is less than or equal to 55
        try:
            # Ensure that product_price is converted to a float for comparison
            product_price = float(
                item.get("product_price", 0)
            )  # Default to 0 if not present
        except ValueError:
            # Log and skip items with invalid price data
            spider.logger.warn("Invalid price for item: %s" % item["product_id"])
            return item  # Skip items with invalid price data

        if product_price <= 55:
            ## Check to see if text is already in database
            self.cur.execute(
                """SELECT * FROM seller_product_data WHERE product_id = %s AND sys_run_date = %s""",
                (item["product_id"], item["sys_run_date"]),
            )
            result = self.cur.fetchone()

            ## If it is in DB, create log message
            if result:
                spider.logger.warn("Item already in database: %s" % item["product_id"])

            ## If text isn't in the DB, insert data
            else:
                ## Define insert statement
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

                ## Execute insert of data into database
                self.connection.commit()
        else:
            ## If product price is greater than 55, log message and skip insertion
            spider.logger.info(
                "Item price exceeds limit (>$55) and will not be inserted: %s"
                % item["product_id"]
            )

        return item

    def close_spider(self, spider):
        ## Close cursor & connection to database
        self.cur.close()
        self.connection.close()
