# crawl_and_ingest.py

```python
import asyncio
import os
from datetime import datetime
import hashlib
import json
import logging
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
# Supabase client library (example)
from supabase import create_client, Client

# Supabase setup — fill your URL & key
SUPABASE_URL = os.getenv("SUPABASE_URL", "<your-url>")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "<your-anon-or-service-key>")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def crawl_page(url: str, browser_conf: BrowserConfig = None, run_conf: CrawlerRunConfig = None) -> dict:
    browser_conf = browser_conf or BrowserConfig(headless=True, verbose=False)
    run_conf = run_conf or CrawlerRunConfig()
    async with AsyncWebCrawler(config=browser_conf) as crawler:
        result = await crawler.arun(url=url, config=run_conf)
        if not result.success:
            logger.warning(f"Crawl failed for {url}")
        # raw_html, cleaned_html, markdown etc available
        return {
            "url": url,
            "fetched_at": datetime.utcnow().isoformat(),
            "raw_markdown": result.markdown.raw_markdown,
            "clean_markdown": getattr(result.markdown, "fit_markdown", None),
            "raw_html": getattr(result, "cleaned_html", None),
        }

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def upsert_supabase(table: str, record: dict, key_field: str):
    """
    Upsert record into Supabase table.
    :param table: Supabase table name
    :param record: dict of field-values
    :param key_field: field name to use for ON CONFLICT / matching
    """
    # Example assumes primary key exists or unique index on key_field
    resp = supabase.table(table).upsert(record, on_conflict=key_field).execute()
    if resp.error:
        logger.error(f"Supabase upsert error: {resp.error}")
    else:
        logger.info(f"Upserted record into {table}, {key_field}={record.get(key_field)}")

async def process_ruling(url: str):
    # Example for CBP rulings page: 
    crawl_result = await crawl_page(url)
    # Extract fields — adapt selectors/schema
    # For demonstration we'll treat markdown as the body
    record = {
        "ruling_number": "<extract-value>",
        "url": url,
        "text": crawl_result["raw_markdown"],
        "ingested_at": datetime.utcnow().isoformat(),
        "content_hash": compute_hash(crawl_result["raw_markdown"] or ""),
    }
    upsert_supabase("cbp_rulings", record, "ruling_number")

async def main_crawl_rulings():
    # Entry function for your ruling crawl
    # Discover list of new ruling URLs via your own logic,
    # then for each URL call process_ruling(url)
    urls_to_process = [
        "https://rulings.cbp.gov/ruling/H289712",
        # etc.
    ]
    tasks = [process_ruling(u) for u in urls_to_process]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main_crawl_rulings())
    ``` 
