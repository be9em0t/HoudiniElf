# scrape_dog package

This package provides a small, test-friendly scraping framework with mode
adapters (for example: `vex`, `python`, `unity_shadergraph`). The package
contains a guarded GUI and a CLI entrypoint so it can be used both programmatically
and from the command line.

## Package API

- `scrape_dog.cli.main(argv=None)`
  - The CLI/GUI entrypoint. When run with no adapter it will attempt to launch
    the GUI. Otherwise it expects arguments like: `python -m scrape_dog <adapter> <url> [--max N]`.

- `scrape_dog.scrape_core.Scraper`
  - The async scraping core. Create and use it programmatically if you want
    custom scraping flows. See the docstrings in the module for construction
    details.

- `scrape_dog.models.DocumentModel` and helpers
  - Pydantic models that represent the universal export. Use
    `scrape_dog.models.from_nodeentry_list` to convert scraped node/function
    entries into a `DocumentModel` suitable for JSON export and saving.
  - Extended with `contents_tree` and `problems` fields for hierarchical visualization.

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

### Adapter Implementation Guidelines

Modern adapters (like `unity_shadergraph`) implement custom parsing logic to:
- Handle complex hierarchical documentation structures (Topic → Category → Element)
- Avoid duplication by parsing specific content sections rather than entire pages
- Generate structured `contents_tree` for easy visualization and verification
- Provide debug output for transparent parsing processes

Example adapter path and symbol for `unity-shadergraph`:

- Module: `scrape_dog.adapters.unity_shadergraph`  
- Function: `run_unity_shadergraph`
- Structure: Parses Unity ShaderGraph Node Library into Topics (e.g., "Artistic", "Math") containing Categories (e.g., "Adjustment", "Blend") with precise Element extraction

## Running

- Launch GUI (default when no adapter args provided): `python -m scrape_dog`
- CLI adapter run: `python -m scrape_dog unity_shadergraph <url> --max 10`
  

## Notes

- The GUI is lazily imported to keep tests and headless environments free from
  PyQt6 imports. If you need the GUI, install `PyQt6` in your environment.
- Adapters should not perform network calls in unit tests; tests in this repo
  use small fixtures and fake crawlers to remain deterministic.
- Modern adapters include comprehensive debug logging to make parsing behavior transparent and debuggable.
