"""Top-level launcher for the scrape_dog package.

This small shim keeps the familiar "python scrape_dog.py" invocation working by
delegating to the package entrypoint. It avoids importing package internals at
top-level so test discovery and imports remain unambiguous.

Usage:
  python scrape_dog.py <adapter> <url> [--max N]
  python scrape_dog.py --gui

This file intentionally delegates to the package so maintainers can keep the
real implementation inside `scrape_dog/` where it's importable as a package.
"""
import runpy
import sys


def main(argv=None):
    # Run the package as a module to ensure package-relative imports work.
    # We pass control to the package's __main__ so the actual CLI/GUI lives
    # under `scrape_dog/cli.py` and `scrape_dog/gui.py`.
    argv = argv or sys.argv
    # If invoked as a script with arguments, forward them to the package main
    # by executing it as a module. runpy.run_module will execute the package
    # in a new globals dict and not alter sys.path unnecessarily.
    runpy.run_module('scrape_dog', run_name='__main__')


if __name__ == '__main__':
    main()
