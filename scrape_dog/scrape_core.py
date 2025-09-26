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
        
        if self.mode == 'shadergraph':
            # Unity ShaderGraph has a different structure - we need to parse category links
            return await self._parse_shadergraph_nodes(soup, crawler)
        else:
            # Original VEX parsing logic
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

    async def _parse_shadergraph_nodes(self, soup: BeautifulSoup, crawler) -> List[NodeEntry]:
        """Parse Unity ShaderGraph nodes from the Node Library structure."""
        results: List[NodeEntry] = []
        
        # Find category links from tables on the main Node Library page
        category_links = []
        
        # Look for category links in table cells
        tables = soup.find_all('table')
        for table in tables:
            cells = table.find_all(['td', 'th'])
            for cell in cells:
                links = cell.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    category_name = link.get_text().strip()
                    
                    # Look for category pages ending in -Nodes.html
                    if href.endswith('-Nodes.html') and category_name:
                        full_url = urljoin(self.target_url, href)
                        category_links.append((category_name, full_url))
        
        # Remove duplicates
        seen = set()
        unique_category_links = []
        for name, url in category_links:
            if url not in seen:
                unique_category_links.append((name, url))
                seen.add(url)
        
        self._report(f"Found {len(unique_category_links)} categories to scrape")
        
        # Scrape each category page
        for category_name, category_url in unique_category_links:
            if self.cancel_check() or self._is_cancelled:
                break
            if self.max_results > 0 and len(results) >= self.max_results:
                break
                
            try:
                self._report(f"Scraping category: {category_name}")
                result = await crawler.arun(url=category_url, session_id="shadergraph_category")
                if not result.success:
                    logger.warning(f"Failed to fetch category page: {category_url}")
                    continue
                    
                category_soup = BeautifulSoup(result.html, 'html.parser')
                category_nodes = await self._parse_category_nodes(category_soup, category_name, category_url)
                
                # Add nodes respecting the max_results limit
                for node in category_nodes:
                    if self.max_results > 0 and len(results) >= self.max_results:
                        break
                    results.append(node)
                
                # Check if we've reached the limit
                if self.max_results > 0 and len(results) >= self.max_results:
                    break
                
            except Exception as e:
                logger.warning(f"Error parsing category {category_name}: {e}")
                continue
        
        # Now fetch individual node descriptions
        self._report(f"Fetching descriptions for {len(results)} nodes")
        await self._fetch_node_descriptions(crawler, results)
        
        return results

    async def _parse_category_nodes(self, soup: BeautifulSoup, category_name: str, base_url: str) -> List[NodeEntry]:
        """Parse nodes from a Unity ShaderGraph category page like Artistic-Nodes.html."""
        nodes = []
        
        # Look for node links in the navigation sidebar
        nav_links = soup.find_all('a')
        for link in nav_links:
            href = link.get('href', '')
            link_text = link.get_text().strip()
            
            # Skip non-node links
            if not href or not link_text:
                continue
            if 'Node.html' not in href:
                continue
            if link_text in ['Node Library', 'Manual', category_name]:
                continue
                
            # Extract node information
            node_url = urljoin(base_url, href)
            
            # Create the node entry - we'll fetch the description later
            node = NodeEntry(
                name=link_text,
                description="",  # Will be populated by fetching individual page
                category=category_name,
                url=node_url
            )
            nodes.append(node)
        
        return nodes

    async def _fetch_node_descriptions(self, crawler, nodes: List[NodeEntry]):
        """Fetch detailed descriptions from individual node pages."""
        sem = asyncio.Semaphore(self.concurrency)
        
        async def fetch_node_description(node: NodeEntry):
            if self.cancel_check() or self._is_cancelled:
                return
            async with sem:
                try:
                    result = await crawler.arun(url=node.url, session_id="shadergraph_node")
                    if not result.success:
                        logger.debug(f"Failed to fetch node page: {node.url}")
                        return
                        
                    soup = BeautifulSoup(result.html, 'html.parser')
                    
                    # Validate that the node name matches the page
                    page_title = soup.find('h1')
                    if page_title:
                        title_text = page_title.get_text().strip()
                        # Check if the node name is in the page title
                        if node.name.lower() not in title_text.lower():
                            logger.debug(f"Node name mismatch: expected '{node.name}', found '{title_text}'")
                    
                    # Look for the Description section
                    description = ""
                    
                    # Find the Description heading and get the following paragraph
                    headings = soup.find_all(['h2', 'h3'])
                    for heading in headings:
                        heading_text = heading.get_text().strip()
                        if 'description' in heading_text.lower():
                            # Look for the next paragraph or div
                            next_elem = heading.find_next_sibling(['p', 'div'])
                            if next_elem:
                                desc_text = next_elem.get_text().strip()
                                # Clean up the description
                                if (desc_text and 
                                    len(desc_text) > 10 and
                                    'toggle navigation' not in desc_text.lower() and
                                    'docs.unity3d.com' not in desc_text.lower()):
                                    description = desc_text
                                    break
                    
                    # If no description found, try to get text from paragraphs under main content
                    if not description:
                        paragraphs = soup.find_all('p')
                        for p in paragraphs[:3]:  # Check first few paragraphs
                            p_text = p.get_text().strip()
                            if (p_text and 
                                len(p_text) > 20 and
                                'toggle navigation' not in p_text.lower() and
                                'docs.unity3d.com' not in p_text.lower() and
                                not p_text.startswith('http')):
                                description = p_text
                                break
                    
                    # Update the node with the fetched description
                    if description:
                        node.description = description
                    
                except Exception as e:
                    logger.debug(f"Error fetching description for {node.name}: {e}")
        
        # Process nodes in batches
        tasks = [asyncio.create_task(fetch_node_description(node)) for node in nodes]
        processed = 0
        total = len(tasks)
        
        try:
            for coro in asyncio.as_completed(tasks):
                if self.cancel_check() or self._is_cancelled:
                    break
                await coro
                processed += 1
                if processed % 10 == 0 or processed == total:  # Report every 10 nodes
                    pct = int((processed / total) * 100)
                    self._report(f"Fetched descriptions: {processed}/{total}", pct)
        except Exception:
            pass
        
        # Cancel any remaining tasks
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

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
