import sys
from pathlib import Path
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
  sys.path.insert(0, ROOT)

import asyncio
from scrape_dog.scrape_core import Scraper, VexFunction


def sample_index_html():
    return '''
    <html><body>
      <h2>Category One</h2>
      <ul>
        <li class="item"><p class="label"><a href="/a/foo.html">foo</a></p><p class="summary">First function</p></li>
        <li class="item"><p class="label"><a href="/a/bar.html">bar</a></p><p class="summary">Second function</p></li>
      </ul>
      <h2>Category Two</h2>
      <ul>
        <li class="item"><p class="label"><a href="/a/baz.html">baz</a></p><p class="summary">Third</p></li>
      </ul>
    </body></html>
    '''


class FakeResult:
    def __init__(self, html, success=True):
        self.html = html
        self.success = success


class FakeCrawler:
    def __init__(self, pages):
        # pages is a dict url->html
        self.pages = pages

    async def arun(self, url, session_id=None):
        html = self.pages.get(url, '')
        return FakeResult(html, success=bool(html))


def test_parse_functions_awaitable():
    s = Scraper('http://example.com/a/index.html', max_results=0, concurrency=2, mode='vex')
    html = sample_index_html()
    # parse_functions returns an awaitable list
    res = s.parse_functions(html)
    # parse_functions may return an already-materialized list or an awaitable; handle both
    if isinstance(res, list):
        funcs = res
    else:
        funcs = asyncio.run(res)
    assert isinstance(funcs, list)
    assert len(funcs) == 3
    assert all(hasattr(f, 'name') for f in funcs)


def test_fetch_function_usage_finds_code_snippets():
    # prepare a fake crawler with a page containing code
    func = VexFunction(name='foo', description='', category='Category One', url='http://example.com/a/foo.html', usage=[])
    index_html = ''
    code_page = '<html><body><code>foo(1,2)</code><code>notmatching()</code></body></html>'
    crawler = FakeCrawler({'http://example.com/a/foo.html': code_page})

    s = Scraper('http://example.com/a/index.html', mode='vex')
    usages = asyncio.run(s.fetch_function_usage(crawler, func))
    assert isinstance(usages, list)
    assert any('foo(' in u for u in usages)
