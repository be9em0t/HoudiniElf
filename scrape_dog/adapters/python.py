"""Adapter: python

Wraps the core Scraper in 'python' mode and returns a `DocumentModel`.
"""

from typing import Optional
from scrape_dog import Scraper
from scrape_dog.models import from_nodeentry_list, DocumentModel


async def run_python(target_url: str, max_results: int = 0, concurrency: int = 6) -> DocumentModel:
    s = Scraper(target_url=target_url, max_results=max_results, concurrency=concurrency, mode='python')
    items = await s.scrape()
    doc = from_nodeentry_list(items, software='Python API', version='')
    doc.root_url = target_url
    return doc
