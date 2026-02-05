---
agent: 'agent'
description: 'Translation Task for POI Categories (TSV)'
name: 'translate_POI_categories'
---
You are an expert in geographic, navigation, and map translations; consult online references if needed.
Edit the file ${file} (TSV) and fill the translation columns for the target languages `{languages}` with concise, idiomatic translations for each `name_en` POI category label. Do not create scripts to complete the task, do it yourself. Fetch online sources if necessary.

* Init
Start by asking the user to confirm the tsv file to process, and to supply the target translation `{languages}`. Add `translation_{langcode}` columns if missing.

* Verification
After init verify requirements:
- Header row MUST include `name_en` and one or more `translation_{langcode}` columns for each target language (e.g. `translation_th`, `translation_pt`, `translation_it`, `translation_ja`).
- The first column is `name_en`
- The target languages match the `translation_{langcode}` columns.
- The file is valid TSV (tab-separated), UTF-8, no BOM.
- If a language or ganguage column is ambiguous ask the user for clarification.

* Recommended conventions and guidelines:
- Keep translations concise and natural (1–4 words when possible).
- Prefer neutral, widely-understood terms rather than regional slang.
- Keep proper nouns untranslated unless a common local equivalent exists.
- Prefer generic POI labels (e.g., `Park` instead of a brand-specific name) unless the source is obviously a brand or proper name.

* Example rows:
- The first rows may include examples. Do not overwite them.

* Processing & QA:
- Fill concise, idiomatic translations for all name_en rows.
- Validate TSV parsing (no stray tabs inside fields unless quoted), ensure UTF-8.
- Flag rows where translation length ratio vs source > 3x 
- Flag rows where banned tokens appear.
- Normalize and removed slashes/parentheticals
- Provide a short changelog after completion: total rows processed, rows changed, and count of ambiguous items flagged.
- Use translation memory (TM) to reuse previous translations when available.
- Apply automated QA checks: placeholder preservation, character set checks, length thresholds, and glossary enforcement.

* Changelog expectations (assistant must return):
- `total_rows`: N
- `rows_filled`: M
- `ambiguous_flagged`: K
