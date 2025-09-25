"""Entry point for `python -m scrape_dog`.

This module imports the top-level CLI/GUI runner from the previous top-level
`scrape_dog.py` and exposes it for package-based execution.
"""
from . import cli

if __name__ == '__main__':
    cli.main()
