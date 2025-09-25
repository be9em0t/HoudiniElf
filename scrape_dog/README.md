# scrape_dog package

This package provides a small, test-friendly scraping framework with mode
adapters (for example: `vex`, `python`, `unity_shadergraph`). The package
contains a guarded GUI and a CLI entrypoint so it can be used both programmatically
and from the command line.

## Package API

- `scrape_dog.cli.main(argv=None)`
  - The CLI/GUI entrypoint. When run with no adapter or with `--gui` it will
    attempt to launch the optional GUI. Otherwise it expects arguments like:
    `python -m scrape_dog <adapter> <url> [--max N]`.

- `scrape_dog.scrape_core.Scraper`
  - The async scraping core. Create and use it programmatically if you want
    custom scraping flows. See the docstrings in the module for construction
    details.

- `scrape_dog.models.DocumentModel` and helpers
  - Pydantic models that represent the universal export. Use
    `scrape_dog.models.from_nodeentry_list` to convert scraped node/function
    entries into a `DocumentModel` suitable for JSON export and saving.

## Adapter convention

Adapters live under `scrape_dog.adapters` as small modules. Each adapter should
expose an async runner function named `run_<adapter_name>` (hyphens replaced
with underscores). The function signature should be roughly:

```py
async def run_myadapter(url: str, max_results: int = 0) -> DocumentModel:
    ...
```

The adapter should instantiate the `Scraper` (or perform its own parsing) and
return a `DocumentModel` instance. The CLI uses dynamic importing to load the
adapter module and calls the `run_<adapter>` function.

Example adapter path and symbol for `unity-shadergraph`:

- Module: `scrape_dog.adapters.unity_shadergraph`
- Function: `run_unity_shadergraph`

## Running

- CLI: `python -m scrape_dog unity_shadergraph <url> --max 10`
- Script shim: `python scrape_dog.py unity_shadergraph <url>` (delegates to package)

## Notes

- The GUI is lazily imported to keep tests and headless environments free from
  PyQt6 imports. If you need the GUI, install `PyQt6` in your environment.
- Adapters should not perform network calls in unit tests; tests in this repo
  use small fixtures and fake crawlers to remain deterministic.
