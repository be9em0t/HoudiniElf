import asyncio
import importlib.util
import pathlib
import requests

# Load module by path to avoid import issues
p = pathlib.Path(__file__).parent / 'scrape_dog_qt6.py'
spec = importlib.util.spec_from_file_location('scrape_dog_qt6', str(p))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
Scraper = mod.Scraper

url = 'https://qgis.org/pyqgis/3.40/core/index.html'
print('Fetching:', url)
r = requests.get(url, timeout=20)
print('HTTP status:', r.status_code)
html = r.text
s = Scraper(target_url=url, max_results=20, mode='python')
items = asyncio.run(s.parse_functions(html))
print('Found items:', len(items))
for i, it in enumerate(items[:20], 1):
    print(i, repr(it.name), '|', repr(it.category), '|', it.url)
