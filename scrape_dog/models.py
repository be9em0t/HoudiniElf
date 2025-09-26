"""
Package-local models mirror of top-level `models.py` moved into `scrape_dog`.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ElementModel(BaseModel):
    """Represents a single scraped element: function, class or node."""
    name: str
    description: Optional[str] = ''
    url: Optional[str] = ''
    usage: List[str] = Field(default_factory=list)
    
    def model_dump(self, **kwargs):
        """Override model_dump to exclude empty usage field."""
        data = super().model_dump(**kwargs)
        # Remove usage if it's empty
        if not data.get('usage'):
            data.pop('usage', None)
        return data


class CategoryModel(BaseModel):
    category: str
    elements: List[ElementModel] = Field(default_factory=list)


class DocumentModel(BaseModel):
    software: Optional[str] = ''
    version: Optional[str] = ''
    capture_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    root_url: Optional[str] = ''
    contents_tree: Optional[Dict[str, Any]] = None
    categories: List[CategoryModel] = Field(default_factory=list)
    problems: Optional[List[str]] = None


def from_nodeentry_list(node_entries, software: str = '', version: str = '') -> DocumentModel:
    doc = DocumentModel(software=software, version=version)
    cat_map = {}
    for ne in node_entries:
        cat = ne.category or 'Uncategorized'
        if cat not in cat_map:
            cat_map[cat] = CategoryModel(category=cat)
            doc.categories.append(cat_map[cat])
        elem = ElementModel(name=ne.name, description=getattr(ne, 'description', '') or '', url=getattr(ne, 'url', ''), usage=getattr(ne, 'usage', []) or [])
        cat_map[cat].elements.append(elem)
    return doc
