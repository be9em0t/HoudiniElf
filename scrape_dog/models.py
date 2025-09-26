"""
Package-local models mirror of top-level `models.py` moved into `scrape_dog`.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ElementModel(BaseModel):
    """Represents a single scraped element: function, class or node.

    The original tests expect a `kind` attribute that differentiates between
    generic 'node' elements and 'function' elements. We infer `kind` during
    construction: if usage examples are present we treat it as a 'function',
    otherwise default to 'node'. Adapters that know a more specific kind can
    override this explicitly when instantiating.
    """
    name: str
    description: Optional[str] = ''
    url: Optional[str] = ''
    usage: List[str] = Field(default_factory=list)
    kind: str = 'node'
    
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
    """Convert a flat list of node/function entries to a `DocumentModel`.

    Heuristic for `kind`:
    - If an entry exposes a non-empty `usage` list -> 'function'
    - Else -> 'node'
    """
    doc = DocumentModel(software=software, version=version)
    cat_map = {}
    for ne in node_entries:
        cat = getattr(ne, 'category', None) or 'Uncategorized'
        if cat not in cat_map:
            cat_map[cat] = CategoryModel(category=cat)
            doc.categories.append(cat_map[cat])
        usage_list = getattr(ne, 'usage', []) or []
        kind = 'function' if usage_list else 'node'
        elem = ElementModel(
            name=ne.name,
            description=getattr(ne, 'description', '') or '',
            url=getattr(ne, 'url', ''),
            usage=usage_list,
            kind=kind
        )
        cat_map[cat].elements.append(elem)
    return doc
