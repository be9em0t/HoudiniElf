import sys
from pathlib import Path
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from datetime import datetime
from scrape_dog.models import from_nodeentry_list, DocumentModel


class Dummy:
    def __init__(self, name, description, category, url, usage=None):
        self.name = name
        self.description = description
        self.category = category
        self.url = url
        if usage is not None:
            self.usage = usage


def test_from_nodeentry_list_groups_categories():
    items = [
        Dummy('foo', 'desc foo', 'CatA', 'http://a/foo'),
        Dummy('bar', 'desc bar', 'CatB', 'http://a/bar'),
        Dummy('baz', 'desc baz', 'CatA', 'http://a/baz', usage=['baz()'])
    ]
    doc = from_nodeentry_list(items, software='TestSoft', version='1.2')
    assert isinstance(doc, DocumentModel)
    assert doc.software == 'TestSoft'
    assert doc.version == '1.2'
    cats = {c.category: c for c in doc.categories}
    assert 'CatA' in cats and 'CatB' in cats
    assert len(cats['CatA'].elements) == 2
    # ensure function with usage got mapped to kind=function
    kinds = [e.kind for e in cats['CatA'].elements]
    assert 'function' in kinds and 'node' in kinds
