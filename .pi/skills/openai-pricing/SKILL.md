---
name: openai-pricing
description: Extracts available OpenAI model IDs and resolves current public pricing for those models, including token prices, cached-input prices, and special pricing modes. Use when you need an up-to-date model list, token-cost table, or pricing comparison for OpenAI models.
---

# OpenAI Pricing Skill

## What this skill does

This skill answers two related questions efficiently:

1. **Which models are available to the current API key?**
   - Fetches `GET /v1/models`
   - Requires a valid OpenAI API key

2. **What do those models cost?**
   - Fetches the public pricing page through a text mirror that is reachable from the agent environment
   - Extracts model prices from the pricing tables
   - Normalizes dated aliases like `gpt-4o-mini-2024-07-18` to their base model when needed

## What worked in the investigation

- `GET https://api.openai.com/v1/models` worked once the API key was loaded from macOS Keychain.
- The API response gave the **available model IDs**, but **not prices**.
- Direct access to `https://openai.com/api/pricing/` was blocked by Cloudflare in this environment.
- The mirror `https://r.jina.ai/http://developers.openai.com/api/docs/pricing` returned the pricing page as Markdown and was parseable.

## What did not work

- Model IDs alone cannot be used to infer exact pricing.
- Some models are aliases or dated variants, so a direct string match may fail.
- Some prices are not token prices at all (audio/video/image/transcription/tools), so they must be labeled separately.
- Some models exist in the model list but are not separately priced on the public page.

## Recommended workflow

For the task "list available 3.x, 4.x, and 5.x models with pricing, sorted from most to least expensive", use:

```bash
python .pi/skills/openai-pricing/scripts/openai_pricing.py available --family 345 --sort price-desc --hide-unpriced
```

That command:
- pulls the live `/v1/models` list
- pulls the current public pricing page from the mirror
- prefers canonical standard-token pricing rows
- falls back to DuckDuckGo pricing snippets for models missing from the official page
- keeps only priced 3.x/4.x/5.x models in the output
- sorts by price descending

## Usage

### Show all available 3.x, 4.x and 5.x models with pricing if found

```bash
python .pi/skills/openai-pricing/scripts/openai_pricing.py available --family 345 --sort price-desc --hide-unpriced
```

### Show all available models

```bash
python .pi/skills/openai-pricing/scripts/openai_pricing.py available
```

### Look up specific models

```bash
python .pi/skills/openai-pricing/scripts/openai_pricing.py gpt-5.4-mini gpt-4o-mini gpt-4.1-mini
```

### Print raw parsed pricing data

```bash
python .pi/skills/openai-pricing/scripts/openai_pricing.py --json all
```

## Key requirements

- The script reads the API key from `OPENAI_API_KEY` if set.
- If not set, it tries macOS Keychain with the service name `OPENAI_API_KEY`.
- No `.env` file is required.
- The pricing page is fetched from the mirror `r.jina.ai` endpoint rather than the Cloudflare-protected page.
- If the official pricing page does not list a model, the script can fall back to DuckDuckGo snippets for a model-specific pricing lookup.

## Notes

- Standard token pricing is the default reference for comparison.
- Batch, Flex, Priority, and special modality pricing are preserved when found.
- Regional processing may add a surcharge for some models; the script reports it when present in the pricing page.
