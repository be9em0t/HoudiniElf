"""
Houdini VEX Function Web Scraper

This script scrapes the Houdini VEX function documentation from the official SideFX website,
extracting detailed information about VEX functions including their names, descriptions, 
categories, and usage examples.

Features:
- Asynchronous web crawling of Houdini VEX function index
- Extracts function details using BeautifulSoup
- Saves extracted function information to a JSON file

Usage:
1. Ensure required dependencies are installed:
   pip install crawl4ai pydantic beautifulsoup4

2. Run the script:
   python scrape_dog.py

Output:
- Prints progress of function extraction
- Generates 'vex_functions.json' with comprehensive VEX function details

Dependencies:
- crawl4ai: Asynchronous web crawling
- pydantic: Data validation
- beautifulsoup4: HTML parsing
"""

import asyncio
import re
from crawl4ai import AsyncWebCrawler
from pydantic import BaseModel
from typing import List
from bs4 import BeautifulSoup

class VexFunction(BaseModel):
    name: str
    description: str
    category: str
    url: str
    usage: List[str]

async def scrape_vex_functions():
    async with AsyncWebCrawler(verbose=False) as crawler:  # reduce verbosity
        result = await crawler.arun(
            url="https://www.sidefx.com/docs/houdini20.5/vex/functions/index.html",
            session_id="vex_scrape"
        )

        if result.success:
            functions = parse_vex_functions(result.html)
            print(f"Extracted {len(functions)} functions from index")

            # Fetch usages in batches
            batch_size = 10
            for i in range(0, len(functions), batch_size):
                batch = functions[i:i+batch_size]
                tasks = [fetch_function_usage(crawler, func) for func in batch]
                usages_batch = await asyncio.gather(*tasks)
                for func, usages in zip(batch, usages_batch):
                    func.usage = usages
                print(f"Processed batch {i//batch_size + 1}/{(len(functions)-1)//batch_size + 1}")

            print(f"Extracted {len(functions)} functions")
            for func in functions[:3]:  # print first 3
                print(func)
            # Save to JSON
            import json
            with open("vex_functions.json", "w") as f:
                json.dump([func.model_dump() for func in functions], f, indent=2)
        else:
            print(f"Failed: {result.error_message}")

def parse_vex_functions(html: str) -> List[VexFunction]:
    soup = BeautifulSoup(html, 'html.parser')
    functions = []
    # Find all h2 tags for categories
    categories = soup.find_all('h2')
    for h2 in categories:
        category = h2.get_text().strip().split('\n')[0].strip()  # get first line
        if category in ['Functions', 'Language', 'Next steps', 'Reference']:
            continue  # skip non-category headers
        print(f"Processing category: {category}")
        # Find the ul after this h2
        ul = h2.find_next('ul')
        if ul:
            lis = ul.find_all('li', class_='item')
            for li in lis:
                label_p = li.find('p', class_='label')
                summary_p = li.find('p', class_='summary')
                if label_p and summary_p:
                    a_tag = label_p.find('a')
                    if a_tag:
                        name = a_tag.get_text().strip()
                        description = summary_p.get_text().strip()
                        url = 'https://www.sidefx.com/docs/houdini20.5/vex/functions/' + a_tag['href']
                        functions.append(VexFunction(name=name, description=description, category=category, url=url, usage=[]))
    return functions

async def fetch_function_usage(crawler, func: VexFunction) -> List[str]:
    try:
        result = await crawler.arun(url=func.url)
        if result.success:
            soup = BeautifulSoup(result.html, 'html.parser')
            # Find all code tags that contain the function name and have parentheses
            codes = soup.find_all('code')
            usages = []
            for code in codes:
                text = code.get_text().strip()
                if func.name in text and '(' in text and ')' in text:
                    # Clean the text by replacing non-breaking spaces with regular spaces
                    cleaned_text = text.replace('\u00a0', ' ')
                    usages.append(cleaned_text)
            return usages
        else:
            return []
    except:
        return []

def extract_usage_from_description(description: str) -> List[str]:
    # Placeholder for usage extraction logic
    # For now, just return an empty list
    return []

if __name__ == "__main__":
    asyncio.run(scrape_vex_functions())