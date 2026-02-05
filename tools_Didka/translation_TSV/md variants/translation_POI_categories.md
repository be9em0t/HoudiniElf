---
description: 'Translation Task for POI Categories (TSV)'
name: 'translation_POI_categories'
agent: 'agent'
---

Task (replace placeholders):

You are an expert in geographic, navigation, and map translations; consult online references if needed.
Edit the file ${file} (TSV) and fill the translation columns for the target languages `{languages}` with concise, idiomatic translations for each `name_en` POI category label.

File format requirements:
- Use TSV (tab-separated), UTF-8, no BOM.
- Header row MUST include `name_en` and one `translation_{langcode}` column for each target language (e.g. `translation_th`, `translation_pt`, `translation_it`, `translation_ja`).
- If a translation is ambiguous, add a short note in `translation_{langcode}_note`. Otherwise leave the note blank.
- Preserve placeholders and markup exactly (e.g., `{0}`, `%s`, HTML tags). Do not translate them.
- Do not change existing non-empty translations unless clearly incorrect; only fill blank cells.

Recommended conventions and guidelines:
- Keep translations concise and natural (1–4 words when possible).
- Prefer neutral, widely-understood terms rather than regional slang.
- Keep proper nouns untranslated unless a common local equivalent exists.
- Prefer generic POI labels (e.g., `Park` instead of a brand-specific name) unless the source is obviously a brand or proper name.

Example rows:
- The first rows include examples

Processing & QA notes for the assistant:
- Validate TSV parsing (no stray tabs inside fields unless quoted), ensure UTF-8.
- Flag rows where translation length ratio vs source > 3x 
- Flag rows where banned tokens appear.
- Provide a short changelog after completion: total rows processed, rows changed, and count of ambiguous items flagged.

Optional stricter rules (recommended for production):
- Use translation memory (TM) to reuse previous translations when available.
- Apply automated QA checks: placeholder preservation, character set checks, length thresholds, and glossary enforcement.

Short variant (one-liner to paste into Copilot):
Fill translation_{langcode} columns in `{file_path}` (TSV) using `name_en` as source, preserve placeholders, flag ambiguous items in `translation_{langcode}_note`, keep translations concise, and return a changelog.

How to use (replace placeholders):
- `{file_path}` → tools_Didka/Translation CSV/poi_translations.tsv
- `{languages}` → `translation_alb,translation_th,translation_pt` (comma-separated list)

---

Changelog expectations (assistant must return):
- `total_rows`: N
- `rows_filled`: M
- `ambiguous_flagged`: K


