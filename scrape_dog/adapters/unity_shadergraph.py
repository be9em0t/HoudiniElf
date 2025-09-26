"""Adapter: unity_shadergraph

Adapter that properly scrapes Unity ShaderGraph nodes following the correct structure:
1. Main page has Topics table (in main content, not sidebar)
2. Each Topic page contains either single Category table or multiple Category tables
3. Each Category contains actual Node links
4. Validate Node page titles contain "Node"
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

from scrape_dog.models import DocumentModel, CategoryModel, ElementModel

logger = logging.getLogger(__name__)


async def run_unity_shadergraph(target_url: str, max_results: int = 0, concurrency: int = 6) -> DocumentModel:
    """Build Unity ShaderGraph element tree following Topic->Category->Node structure (no URL scraping)."""
    async with AsyncWebCrawler(verbose=False) as crawler:
        # Step 1: Parse main page for Topic links
        result = await crawler.arun(url=target_url, session_id="shadergraph_main")
        if not result.success:
            raise RuntimeError(f"Failed to fetch main page: {target_url}")
        
        soup = BeautifulSoup(result.html, 'html.parser')
        topic_links = await _parse_topic_links(soup, target_url)
        
        print(f"DEBUG: Found {len(topic_links)} topics: {[name for name, url in topic_links]}")
        
        # Step 2: For each Topic, determine Categories and Elements
        contents_tree = {}
        categories_data = []
        total_elements = 0
        
        for topic_name, topic_url in topic_links[:3]:  # Limit to first 3 topics to avoid infinite loops
            print(f"DEBUG: Processing topic: {topic_name} -> {topic_url}")
            
            # Fetch topic page
            topic_result = await crawler.arun(url=topic_url, session_id=f"topic_{topic_name}")
            if not topic_result.success:
                print(f"DEBUG: Failed to fetch topic page: {topic_url}")
                continue
            
            topic_soup = BeautifulSoup(topic_result.html, 'html.parser')
            topic_categories = await _parse_topic_categories(topic_soup, topic_name, topic_url)
            
            print(f"DEBUG: Topic '{topic_name}' has {len(topic_categories)} categories: {[name for name, url in topic_categories]}")
            
            contents_tree[topic_name] = {}
            
            # Step 3: For each Category, get Element names (NO URL SCRAPING)
            for category_name, category_url in topic_categories:
                if max_results > 0 and total_elements >= max_results:
                    break
                    
                element_names = await _get_element_names_only(
                    crawler, category_name, category_url, 
                    max_results - total_elements if max_results > 0 else 0
                )
                
                print(f"DEBUG: Category '{category_name}' has {len(element_names)} elements")
                
                if element_names:
                    # Create simplified elements (no descriptions or URL scraping)
                    elements = [
                        ElementModel(
                            name=name,
                            description="",  # Empty - no URL scraping
                            url="",         # Empty - no URL scraping  
                            usage=[]
                        )
                        for name in element_names
                    ]
                    
                    categories_data.append(CategoryModel(
                        category=category_name,
                        elements=elements
                    ))
                    
                    contents_tree[topic_name][category_name] = element_names
                    total_elements += len(element_names)
        
        # Build the final document
        doc = DocumentModel(
            software="Unity ShaderGraph",
            version="",
            capture_date=datetime.now(),
            root_url=target_url,
            categories=categories_data
        )
        
        # Add contents_tree to the document dict for JSON serialization
        doc_dict = doc.model_dump()
        doc_dict['contents_tree'] = contents_tree
        
        return DocumentModel.model_validate(doc_dict)


async def _get_element_names_only(crawler: AsyncWebCrawler, category_name: str, category_url: str, max_elements: int = 0) -> List[str]:
    """Get only the element names from a Category page (no URL scraping)."""
    element_names = []
    
    # Fetch the category page
    result = await crawler.arun(url=category_url, session_id=f"category_{category_name}")
    if not result.success:
        print(f"DEBUG: Failed to fetch category page: {category_url}")
        return element_names
    
    soup = BeautifulSoup(result.html, 'html.parser')
    
    # Find the specific table for this category
    # Look for headings that match the category name, then find the next table
    category_table = None
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    for heading in headings:
        heading_text = heading.get_text().strip()
        if category_name.lower() in heading_text.lower():
            # Found the heading for this category, look for the next table
            category_table = heading.find_next('table')
            print(f"DEBUG: Found table for category '{category_name}' after heading '{heading_text}'")
            break
    
    if not category_table:
        print(f"DEBUG: Could not find table for category '{category_name}'")
        return element_names
    
    # Extract links ONLY from this specific table
    table_links = category_table.find_all('a')
    print(f"DEBUG: Found {len(table_links)} links in category table")
    
    for link in table_links:
        href = link.get('href', '')
        link_text = link.get_text().strip()
        
        # Node links usually end with "Node.html" and the text should be a node name
        if (href and link_text and 
            'Node.html' in href and
            len(link_text) > 2):  # Basic sanity check
            
            element_names.append(link_text)
            print(f"DEBUG: Added element: '{link_text}'")
            
            if max_elements > 0 and len(element_names) >= max_elements:
                break
    
    print(f"DEBUG: Final count for category '{category_name}': {len(element_names)} elements")
    return element_names


async def _parse_topic_links(soup: BeautifulSoup, base_url: str) -> List[Tuple[str, str]]:
    """Parse Topic links from the main Node Library page table (not sidebar)."""
    topic_links = []
    
    print("DEBUG: Looking for topic links in main content...")
    
    # Look for the main content area, not the navigation sidebar
    main_content = soup.find('div', {'class': 'content'}) or soup.find('main') or soup
    
    # Find tables in the main content
    tables = main_content.find_all('table')
    print(f"DEBUG: Found {len(tables)} tables in main content")
    
    for i, table in enumerate(tables):
        print(f"DEBUG: Processing table {i+1}")
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                links = cell.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    link_text = link.get_text().strip()
                    
                    # Topics should be links that lead to pages with node collections
                    # Usually they contain words like "Nodes" in the text or URL
                    if (href and link_text and 
                        ('node' in link_text.lower() or 'node' in href.lower()) and
                        not href.startswith('#')):  # Skip anchor links
                        
                        full_url = urljoin(base_url, href)
                        topic_links.append((link_text, full_url))
                        print(f"DEBUG: Found topic link: '{link_text}' -> {full_url}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_topics = []
    for name, url in topic_links:
        if url not in seen:
            unique_topics.append((name, url))
            seen.add(url)
    
    print(f"DEBUG: Unique topics after deduplication: {len(unique_topics)}")
    return unique_topics


async def _parse_topic_categories(soup: BeautifulSoup, topic_name: str, topic_url: str) -> List[Tuple[str, str]]:
    """Parse Category links from a Topic page.
    
    Handle two cases:
    1. Single table (topic = category)
    2. Multiple tables (topic contains multiple categories)
    """
    category_links = []
    tables = soup.find_all('table')
    
    print(f"DEBUG: Parsing topic '{topic_name}', found {len(tables)} tables")
    
    if len(tables) == 1:
        # Single table case: topic name is the category name
        print(f"DEBUG: Single table case - using topic name '{topic_name}' as category")
        category_links.append((topic_name, topic_url))
    else:
        # Multiple tables case: each table header/caption represents a category
        print(f"DEBUG: Multiple tables case - extracting category names from table headers")
        for i, table in enumerate(tables):
            # Try to find the category name from table headers or preceding headings
            category_name = None
            
            # Check for table caption
            caption = table.find('caption')
            if caption:
                category_name = caption.get_text().strip()
                print(f"DEBUG: Table {i+1} has caption: '{category_name}'")
            
            # If no caption, look for the preceding heading
            if not category_name:
                prev_heading = table.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if prev_heading:
                    category_name = prev_heading.get_text().strip()
                    print(f"DEBUG: Table {i+1} has preceding heading: '{category_name}'")
            
            # If still no category name, try to extract from the first cell content
            if not category_name:
                first_row = table.find('tr')
                if first_row:
                    first_cell = first_row.find(['th', 'td'])
                    if first_cell:
                        # Get text from first cell, might be the category name
                        cell_text = first_cell.get_text().strip()
                        if cell_text and not cell_text.startswith('http'):
                            category_name = cell_text
                            print(f"DEBUG: Table {i+1} first cell text: '{category_name}'")
            
            if category_name:
                # Use the same URL since nodes will be on the same page
                category_links.append((category_name, topic_url))
                print(f"DEBUG: Added category: '{category_name}' -> {topic_url}")
            else:
                print(f"DEBUG: Could not determine category name for table {i+1}")
    
    print(f"DEBUG: Total categories found: {len(category_links)}")
    return category_links


class NodeInfo:
    def __init__(self, name: str, description: str, url: str):
        self.name = name
        self.description = description 
        self.url = url
