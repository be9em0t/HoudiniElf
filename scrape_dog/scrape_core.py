"""
scrape_core (package)

Core Scraper implementation moved into the `scrape_dog` package so adapters
and the CLI can import it as `scrape_dog.scrape_core` or via `scrape_dog`.
"""

import asyncio
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin

from pydantic import BaseModel
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

logger = logging.getLogger(__name__)


class VexFunction(BaseModel):
    name: str
    description: str
    category: str
    url: str
    usage: List[str] = []


class NodeEntry(BaseModel):
    name: str
    description: str
    category: str
    url: str


class Scraper:
    def __init__(self, target_url: str, max_results: int = 0, concurrency: int = 10, progress_callback=None, cancel_check=None, mode: str = 'vex'):
        self.target_url = target_url
        self.max_results = max_results
        self.concurrency = max(1, int(concurrency))
        self.progress_callback = progress_callback or (lambda msg, val=None: None)
        self.cancel_check = cancel_check or (lambda: False)
        self._is_cancelled = False
        self.mode = mode or 'vex'

    def cancel(self):
        self._is_cancelled = True

    def _report(self, message: str, value: Optional[int] = None):
        try:
            self.progress_callback(message, value)
        except Exception:
            logger.debug("Progress callback failed", exc_info=True)

    async def scrape(self) -> List[BaseModel]:
        if self.cancel_check() or self._is_cancelled:
            return []
        async with AsyncWebCrawler(verbose=False) as crawler:
            self._report(f"Fetching: {self.target_url}")
            result = await crawler.arun(url=self.target_url, session_id="universal_scrape")
            if self.cancel_check() or self._is_cancelled:
                return []
            if not result.success:
                raise RuntimeError(getattr(result, 'error_message', 'Failed to fetch index page'))
            items = await self.parse_functions(result.html, crawler)
            if not items:
                self._report("No items found to scrape", 100)
                return []
            if self.max_results > 0:
                items = items[: self.max_results]
            self._report(f"Will process {len(items)} items")
            if self.mode == 'vex':
                sem = asyncio.Semaphore(self.concurrency)

                async def fetch_one(func: VexFunction):
                    if self.cancel_check() or self._is_cancelled:
                        return func
                    async with sem:
                        try:
                            usages = await self.fetch_function_usage(crawler, func)
                            func.usage = usages
                        except Exception:
                            func.usage = []
                    return func

                tasks = [asyncio.create_task(fetch_one(f)) for f in items]
                processed: List[VexFunction] = []
                total = len(tasks)
                try:
                    for coro in asyncio.as_completed(tasks):
                        if self.cancel_check() or self._is_cancelled:
                            break
                        func = await coro
                        processed.append(func)
                        pct = int((len(processed) / total) * 100)
                        self._report(f"Processed {len(processed)}/{total}", pct)
                except Exception:
                    pass
                for t in tasks:
                    if not t.done():
                        t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                return processed
            else:
                return items

    async def _parse_functions_async(self, html: str, crawler=None) -> List[BaseModel]:
        soup = BeautifulSoup(html, 'html.parser')
        results: List[BaseModel] = []
        # Simplified parsing matching test expectations: look for li.item entries
        categories = soup.find_all('h2')
        for h2 in categories:
            category = h2.get_text().strip().split('\n')[0].strip()
            ul = h2.find_next('ul')
            if not ul:
                continue
            lis = ul.find_all('li', class_='item')
            for li in lis:
                if self.max_results > 0 and len(results) >= self.max_results:
                    return results
                label_p = li.find('p', class_='label')
                summary_p = li.find('p', class_='summary')
                if not label_p:
                    continue
                a_tag = label_p.find('a')
                if not a_tag or 'href' not in a_tag.attrs:
                    continue
                name = a_tag.get_text().strip()
                href = a_tag['href']
                url = urljoin(self.target_url, href)
                description = ''
                if summary_p:
                    description = summary_p.get_text().strip()
                if self.mode == 'vex':
                    results.append(VexFunction(name=name, description=description, category=category, url=url, usage=[]))
                else:
                    results.append(NodeEntry(name=name, description=description, category=category, url=url))
        return results

    def parse_functions(self, html: str, crawler=None):
        class AwaitableList(list):
            def __init__(self, coro):
                self._coro = coro
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                if not loop or not loop.is_running():
                    res = asyncio.run(coro)
                    super().__init__(res)
                else:
                    super().__init__()

            def __await__(self):
                res = yield from self._coro.__await__()
                if not self:
                    self.extend(res)
                return self

        return AwaitableList(self._parse_functions_async(html, crawler))

    async def fetch_function_usage(self, crawler, func: VexFunction) -> List[str]:
        if self.cancel_check() or self._is_cancelled:
            return []
        try:
            result = await crawler.arun(url=func.url)
            if not result.success:
                return []
            soup = BeautifulSoup(result.html, 'html.parser')
            codes = soup.find_all('code')
            usages: List[str] = []
            pattern = re.compile(rf"\b{re.escape(func.name)}\s*\(")
            for code in codes:
                text = code.get_text().strip()
                if pattern.search(text):
                    cleaned = text.replace('\u00a0', ' ')
                    usages.append(cleaned)
            return usages
        except Exception as e:
            logger.debug(f"Failed fetching usage for {func.url}: {e}", exc_info=True)
            return []
