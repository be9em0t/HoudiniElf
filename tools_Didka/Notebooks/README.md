# Geographic Name Localization Pipeline

A compact pipeline for intelligent processing of geographic names (cities, streets, POIs). Designed for CSV/TSV UTF-8 input and modular processing using a Jupyter notebook.

Features
- Preprocessing: NBSP removal, whitespace normalization, numeral/shorthand fixes (configurable). 🔧
- AI Agent: placeholder for LLM-driven transliteration, localization, translation and normalization. 🧠
- Postprocessing: verification, tagging, and export. ✅
- Robust CSV import: malformed-line detection and fallout file generation. ⚠️
- Config-driven via `tools_Didka/Notebooks/lang_pipeline.ini` (source file, preview, chunk size, and column lists).

Quick start
1. Open `tools_Didka/Notebooks/DidkaLangPipeline.ipynb` and run top-to-bottom.
2. Edit `tools_Didka/Notebooks/lang_pipeline.ini` to set `source`, `source_browser`, `preview`, and column lists.
3. Check `tools_Didka/test_files/` for sample inputs and outputs.

Notes
- The LLM adapter is currently a placeholder; adapt it to your chosen provider (OpenAI/Anthropic/local) when ready.
- Malformed lines are written to `<source>_fallout<ext>` and include the header for context. This is caused by a wrong number of fields, caused by newline inside a field, unmatched quites or missing fields.

Contributors
- Managed in this repo by the project maintainer.

