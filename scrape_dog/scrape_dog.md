HoudiniElf — scraping toolkit (short project notes)

Purpose
- Universal web scraper focused on extracting API/function/node documentation from docs and translating them into a common export format. 
- Usage as reference document both by AI agents and humans.
- Designed to support multiple "modes" (adapters): vex (Houdini VEX functions), unity_shadergraph (Unity Shader Graph nodes), python (general Python API docs), etc.

Key components
- scrape_core.py: testable Scraper core. Fetches an index page, parses items, and (for function-like items) fetches usage examples concurrently. It exposes a parse wrapper that is awaitable for sync tests.
- models.py: universal Pydantic export models (ElementModel, CategoryModel, DocumentModel) and `from_nodeentry_list` converter. Enhanced with `contents_tree` and `problems` fields for better structure visualization and issue tracking.
- adapters/: per-mode adapters that call the Scraper in a specific mode and return a `DocumentModel` (convention: expose `run_<adapter>` coroutine). Modern adapters implement custom parsing for complex hierarchical documentation.
- scrape_dog.py: master entrypoint. Contains a CLI adapter runner and an embedded Qt GUI (guarded to allow headless test runs). The GUI auto-saves exports into `capture_results/`.
- capture_results/: default folder where the GUI writes JSON exports.

Recent improvements (Unity ShaderGraph adapter)
- Fixed duplication issues by implementing proper Topic → Category → Element hierarchy parsing
- Added targeted table-specific content extraction to avoid navigation pollution  
- Enhanced DocumentModel with hierarchical `contents_tree` for easy visualization
- Implemented comprehensive debug logging for transparent parsing behavior
- Solved infinite loop issues by eliminating unnecessary URL scraping in tree-building phase

Developer notes
- Tests live under `tests/` and are minimal; they exercise parsing and conversion logic without network.
- The project uses Pydantic v2; be mindful of timezone-aware datetimes and ConfigDict vs class-based Config deprecation warnings.
- GUI imports are guarded to keep the code runnable in CI/headless environments without PyQt installed.
- Modern adapters should implement custom parsing logic rather than relying solely on the generic Scraper core when dealing with complex documentation structures.

How to run
- CLI: `python scrape_dog.py <adapter> <url> [--max N]` (adapters under `adapters/`)
- GUI: `python scrape_dog.py --gui` (requires PyQt6)
- Unity ShaderGraph example: `python -m scrape_dog unity_shadergraph "https://docs.unity3d.com/Packages/com.unity.shadergraph@17.1/manual/Node-Library.html"`

Notes for tomorrow
- Consider adding timestamped auto-save filenames for captures.
- Consider expanding the adapter collection and adding basic integration tests for adapters using local fixtures.
- Implement URL scraping for descriptions once the tree structure is proven stable.
