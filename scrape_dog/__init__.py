"""scrape_dog package

Public exports expose the core Scraper and model conversion helpers so adapters
and tests can import from `scrape_dog` (e.g. `from scrape_dog import Scraper`).
"""

from .scrape_core import Scraper, VexFunction, NodeEntry
from .models import from_nodeentry_list, DocumentModel

__all__ = [
    'Scraper', 'VexFunction', 'NodeEntry',
    'from_nodeentry_list', 'DocumentModel'
]
