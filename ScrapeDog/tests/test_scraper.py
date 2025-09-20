# tests for the Scraper class
import asyncio
import pytest
from bs4 import BeautifulSoup
from ScrapeDog.scrape_dog_qt6 import Scraper, VexFunction

HTML_INDEX = """
<h2>Math</h2>
<ul>
  <li class="item">
    <p class="label"><a href="func1.html">func1</a></p>
    <p class="summary">Does X</p>
  </li>
</ul>
"""

class FakeResult:
    def __init__(self, html, success=True):
        self.html = html
        self.success = success
        self.error_message = ""

class FakeCrawler:
    def __init__(self, pages):
        # pages: dict[url] -> html
        self.pages = pages
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def arun(self, url, session_id=None):
        html = self.pages.get(url, "")
        return FakeResult(html, success=bool(html))

def test_parse_functions_simple():
    s = Scraper("https://example.com/index.html", max_results=0)
    funcs = s.parse_functions(HTML_INDEX)
    assert isinstance(funcs, list)
    assert funcs[0].name == "func1"
    assert funcs[0].url.endswith("func1.html")

@pytest.mark.asyncio
async def test_fetch_function_usage():
    # page for func1 containing code examples
    func_page = '<code>func1(a, b)</code><code>other()</code>'
    pages = {
        "https://example.com/index.html": HTML_INDEX,
        "https://example.com/func1.html": func_page
    }
    crawler = FakeCrawler(pages)
    s = Scraper("https://example.com/index.html", max_results=1)
    # build VexFunction manually
    vf = VexFunction(name="func1", description="Does X", category="Math", url="https://example.com/func1.html", usage=[])
    usages = await s.fetch_function_usage(crawler, vf)
    assert any("func1(" in u for u in usages)