"""
Package-local models mirror of top-level `models.py` moved into `scrape_dog`.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ElementModel(BaseModel):
    """Represents a single scraped element: function, class or node."""
    kind: str = Field(..., description="function | class | node")
    name: str
    description: Optional[str] = ''
    url: Optional[str] = ''
    usage: List[str] = Field(default_factory=list)


class CategoryModel(BaseModel):
    category: str
    elements: List[ElementModel] = Field(default_factory=list)


class DocumentModel(BaseModel):
    software: Optional[str] = ''
    version: Optional[str] = ''
    capture_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    root_url: Optional[str] = ''
    categories: List[CategoryModel] = Field(default_factory=list)


def from_nodeentry_list(node_entries, software: str = '', version: str = '') -> DocumentModel:
    doc = DocumentModel(software=software, version=version)
    cat_map = {}
    for ne in node_entries:
        cat = ne.category or 'Uncategorized'
        if cat not in cat_map:
            cat_map[cat] = CategoryModel(category=cat)
            doc.categories.append(cat_map[cat])
        kind = 'node'
        if hasattr(ne, 'usage'):
            kind = 'function'
        elem = ElementModel(kind=kind, name=ne.name, description=getattr(ne, 'description', '') or '', url=getattr(ne, 'url', ''), usage=getattr(ne, 'usage', []) or [])
        cat_map[cat].elements.append(elem)
    return doc
