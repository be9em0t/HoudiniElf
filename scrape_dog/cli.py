"""CLI and GUI entrypoint moved into the `scrape_dog` package.

This file was adapted from the previous top-level `scrape_dog.py` and uses
relative imports so the package is self-contained.
"""
import sys
import asyncio
import json
import re
import logging
from importlib import import_module
from pathlib import Path
import configparser

from .scrape_core import Scraper, VexFunction, NodeEntry
from .models import from_nodeentry_list, DocumentModel

logger = logging.getLogger(__name__)


def print_usage():
    print('Usage: python -m scrape_dog <adapter> [url] [--max N]')


async def run_adapter(adapter_name, url, max_results=0):
    mod = import_module(f'scrape_dog.adapters.{adapter_name}')
    func = getattr(mod, f'run_{adapter_name.replace("-","_")}', None)
    if not func:
        raise SystemExit(f'Adapter {adapter_name} does not expose run_{adapter_name}')
    doc = await func(url, max_results=max_results)
    print(json.dumps(doc.model_dump(), default=str, indent=2))


# GUI code is intentionally omitted here; import it lazily in main() so tests
# remain headless when PyQt6 isn't available.


def main(argv=None):
    argv = argv or sys.argv
    # prefer GUI when no adapter specified (always start GUI by default)
    if len(argv) == 1:
        try:
            from .gui import run_gui
            run_gui()
            return
        except Exception:
            print('GUI dependencies not available. Install PyQt6 or run with adapter args.')
            print_usage()
            return

    if len(argv) < 3:
        print_usage(); return
    adapter = argv[1]
    url = argv[2]
    max_results = 0
    if '--max' in argv:
        i = argv.index('--max')
        try:
            max_results = int(argv[i+1])
        except Exception:
            max_results = 0
    asyncio.run(run_adapter(adapter, url, max_results=max_results))


if __name__ == '__main__':
    main()
