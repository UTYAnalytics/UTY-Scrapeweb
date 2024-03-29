# Scrapy settings for walmart_scraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "walmart_scraper"

SPIDER_MODULES = ["walmart_scraper.spiders"]
NEWSPIDER_MODULE = "walmart_scraper.spiders"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

SCRAPEOPS_API_KEY = "d0ea9ce7-20ed-447e-9b49-6d7fd4c99fa8"

SCRAPEOPS_PROXY_ENABLED = True

# Add In The ScrapeOps Monitoring Extension
EXTENSIONS = {
    "scrapeops_scrapy.extension.ScrapeOpsMonitor": 500,
}


DOWNLOADER_MIDDLEWARES = {
    ## ScrapeOps Monitor
    "scrapeops_scrapy.middleware.retry.RetryMiddleware": 550,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
    ## Proxy Middleware
    "scrapeops_scrapy_proxy_sdk.scrapeops_scrapy_proxy_sdk.ScrapeOpsScrapyProxySdk": 725,
}
ITEM_PIPELINES = {
    #    'walmart_scraper.pipelines.PostgresDemoPipeline': 300,
    "walmart_scraper.pipelinesnew.PostgresNoDuplicatesPipeline": 800,
}
# Max Concurrency On ScrapeOps Proxy Free Plan is 1 thread
CONCURRENT_REQUESTS = 10
