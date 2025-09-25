"""Adapters package for `scrape_dog`.

Drop your adapter modules here. Each adapter must expose an async function
`run_<adapter>` which accepts (target_url, max_results, concurrency) and
returns a `DocumentModel`.
"""

__all__ = []
