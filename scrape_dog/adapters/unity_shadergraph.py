"""Adapter: unity_shadergraph

Adapter that runs the core Scraper in 'shadergraph' mode and converts results
into the universal `DocumentModel` used for export.
"""

from typing import Optional
from scrape_dog import Scraper
from scrape_dog.models import from_nodeentry_list, DocumentModel


async def run_shadergraph(target_url: str, max_results: int = 0, concurrency: int = 6) -> DocumentModel:
    """Run the existing Scraper in shadergraph mode and return a DocumentModel."""
    s = Scraper(target_url=target_url, max_results=max_results, concurrency=concurrency, mode='shadergraph')
    items = await s.scrape()
    # items is a list of NodeEntry objects
    doc = from_nodeentry_list(items, software='Unity ShaderGraph')
    doc.root_url = target_url
    return doc
