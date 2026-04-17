#!/usr/bin/env python3
"""Extract OpenAI model availability and public pricing.

This script is intentionally dependency-free.

Features:
- Reads API key from OPENAI_API_KEY or macOS Keychain
- Fetches /v1/models for the current account
- Fetches the public pricing page via r.jina.ai mirror
- Parses Markdown tables into structured records
- Resolves exact and normalized model names

Usage:
  python openai_pricing.py available
  python openai_pricing.py gpt-5.4-mini gpt-4o-mini
  python openai_pricing.py --json all
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

MODELS_URL = "https://api.openai.com/v1/models"
PRICING_URL = "https://r.jina.ai/http://developers.openai.com/api/docs/pricing"
CACHE_PATH = Path(__file__).resolve().parent / ".ddg_pricing_cache.json"

MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$", re.I)
DATE_SUFFIX_RE = re.compile(r"^(.*?)-\d{4}-\d{2}-\d{2}$")

MODALITIES = {"text", "audio", "image"}
TABLE_HEADER_RE = re.compile(r"^\|.*\|$")
DELIM_RE = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+\s*$")


@dataclass
class PricingRecord:
    model: str
    source_model: str
    section: str
    context: str
    modality: str
    input: Optional[str] = None
    cached_input: Optional[str] = None
    output: Optional[str] = None
    estimated_cost: Optional[str] = None
    raw_row: Optional[str] = None
    source: Optional[str] = None


def get_api_key() -> Optional[str]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        out = subprocess.check_output(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", "OPENAI_API_KEY", "-w"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or None
    except Exception:
        return None


def fetch_models(api_key: str) -> List[str]:
    req = urllib.request.Request(MODELS_URL, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return [item["id"] for item in data.get("data", []) if isinstance(item, dict) and "id" in item]


def fetch_pricing_markdown() -> str:
    req = urllib.request.Request(PRICING_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "ignore")


def load_cache() -> Dict[str, str]:
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return {}


def save_cache(cache: Dict[str, str]) -> None:
    try:
        CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))
    except Exception:
        pass


def fetch_duckduckgo_markdown(query: str, cache: Optional[Dict[str, str]] = None) -> str:
    if cache is not None and query in cache:
        return cache[query]
    q = urllib.parse.quote(query)
    url = f"https://r.jina.ai/http://duckduckgo.com/html/?q={q}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        text = resp.read().decode("utf-8", "ignore")
    if cache is not None:
        cache[query] = text
    return text


def fetch_sources(api_key: str) -> Tuple[List[str], str]:
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_models = pool.submit(fetch_models, api_key)
        future_pricing = pool.submit(fetch_pricing_markdown)
        return future_models.result(), future_pricing.result()


def parse_money(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    if not isinstance(value, str):
        return None
    if not value.strip().startswith("$"):
        return None
    try:
        return float(value.replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def format_money(v: Optional[float]) -> Optional[str]:
    if v is None:
        return None
    return f"${v:.2f}".rstrip("0").rstrip(".") if v % 1 else f"${int(v)}.00"


def parse_snippet_prices(text: str) -> Optional[Tuple[str, str]]:
    patterns = [
        r"Priced at \$?([0-9.]+) per million input tokens and \$?([0-9.]+) per million output tokens",
        r"Priced at \$?([0-9.]+) per million input tokens, \$?([0-9.]+) per million output tokens",
        r"Pricing starts at \$?([0-9.]+) per million input tokens and \$?([0-9.]+) per million output tokens",
        r"\$?([0-9.]+) per million input tokens and \$?([0-9.]+) per million output tokens",
        r"input pricing of \$?([0-9.]+) and output pricing of \$?([0-9.]+) per 1 million tokens",
        r"input pricing of \$?([0-9.]+) and output pricing of \$?([0-9.]+) per million tokens",
        r"input \$\s*([0-9.]+)\s*[·,]\s*output \$\s*([0-9.]+)",
        r"\$([0-9.]+)/\$([0-9.]+) per 1M Tokens",
        r"\$([0-9.]+) / 1M input tokens .*?\$([0-9.]+) / 1M output tokens",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I | re.S)
        if m:
            return f"${float(m.group(1)):.2f}", f"${float(m.group(2)):.2f}"
    return None


def family_matches(model: str, family: str) -> bool:
    if family in {"345", "3x4x5x", "gpt345"}:
        return model.startswith("gpt-3") or model.startswith("gpt-4") or model.startswith("gpt-5")
    if family == "4x5x":
        return model.startswith("gpt-4") or model.startswith("gpt-5")
    if family == "gpt":
        return model.startswith("gpt-")
    if family == "all":
        return True
    return model.startswith(family)


def model_sort_key(record: Optional[PricingRecord], model: str) -> Tuple[int, float, str]:
    if record is None:
        return (1, float("inf"), model)
    price = parse_money(record.input)
    return (0 if price is not None else 1, -(price or float("inf")), model)


def choose_canonical_record(records: List[PricingRecord]) -> Optional[PricingRecord]:
    if not records:
        return None

    def rank(r: PricingRecord) -> Tuple[int, int, int, float, int]:
        source_rank = 0 if r.source == "official" else 1
        context_rank = {"standard": 0, "batch": 1, "flex": 2, "priority": 3}.get(r.context, 4)
        modality_rank = {"text": 0, "transcription": 1, "audio": 2, "image": 3}.get(r.modality, 4)
        price = parse_money(r.input)
        return (source_rank, context_rank, modality_rank, 0 if price is not None else 1, -(price or float("inf")))

    return sorted(records, key=rank)[0]


def search_pricing_fallback(model: str, cache: Optional[Dict[str, str]] = None) -> Optional[PricingRecord]:
    aliases = [model, normalize_model_id(model)]
    for cand in list(aliases):
        if cand.endswith("-chat-latest"):
            stem = cand[: -len("-chat-latest")]
            if stem.endswith("-"):
                stem = stem[:-1]
            aliases.append(stem)
        if cand.endswith("-latest"):
            stem = cand[: -len("-latest")]
            if stem.endswith("-"):
                stem = stem[:-1]
            aliases.append(stem)
        if cand.endswith("-preview"):
            aliases.append(cand[: -len("-preview")])
    # de-dup while preserving order
    seen_aliases = set()
    aliases = [a for a in aliases if not (a in seen_aliases or seen_aliases.add(a))]
    queries = []
    for alias in aliases:
        queries.extend([f"{alias} pricing openai", f"{alias} pricing"])
    for query in queries:
        try:
            md = fetch_duckduckgo_markdown(query, cache=cache)
        except Exception:
            continue
        lines = md.splitlines()
        candidates: List[Tuple[int, Tuple[str, str], str]] = []
        for i, line in enumerate(lines):
            if model.lower().replace("-", "") not in line.lower().replace("-", "") and model.lower() not in line.lower():
                continue
            blob = "\n".join(lines[max(0, i - 3): min(len(lines), i + 10)])
            prices = parse_snippet_prices(blob)
            if prices:
                candidates.append((0 if "openai" in blob.lower() else 1, prices, blob))
        if candidates:
            candidates.sort(key=lambda x: x[0])
            inp, out = candidates[0][1]
            return PricingRecord(
                model=normalize_model_id(model),
                source_model=model,
                section="DuckDuckGo snippet fallback",
                context="standard",
                modality="text",
                input=inp,
                output=out,
                raw_row=candidates[0][2],
                source="search snippet",
            )
    return None


def normalize_model_id(model_id: str) -> str:
    m = DATE_SUFFIX_RE.match(model_id)
    return m.group(1) if m else model_id


def clean_cell(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.strip())


def split_row(line: str) -> List[str]:
    parts = [clean_cell(p) for p in line.strip().strip("|").split("|")]
    return parts


def is_table_line(line: str) -> bool:
    return bool(TABLE_HEADER_RE.match(line.strip()))


def is_delim_line(line: str) -> bool:
    return bool(DELIM_RE.match(line.strip()))


def heading_name(line: str) -> Optional[Tuple[int, str]]:
    m = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
    if not m:
        return None
    return len(m.group(1)), clean_cell(m.group(2))


def extract_sections(markdown: str) -> List[Tuple[str, List[List[str]]]]:
    lines = markdown.splitlines()
    heading_stack: List[Tuple[int, str]] = []
    current_lines: List[str] = []
    current_section = ""
    tables: List[Tuple[str, List[List[str]]]] = []

    def flush_table(block: List[str]) -> None:
        if not block:
            return
        rows = [split_row(line) for line in block if is_table_line(line)]
        if rows:
            tables.append((current_section, rows))

    i = 0
    while i < len(lines):
        h = heading_name(lines[i])
        if h:
            flush_table(current_lines)
            current_lines = []
            level, name = h
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, name))
            current_section = " > ".join(name for _, name in heading_stack)
            i += 1
            continue

        if is_table_line(lines[i]):
            block = [lines[i]]
            i += 1
            while i < len(lines) and is_table_line(lines[i]):
                block.append(lines[i])
                i += 1
            flush_table(block)
            continue

        i += 1

    return tables


def looks_like_model(cell: str) -> bool:
    # Real OpenAI model ids are lowercase-ish identifiers that usually contain
    # a hyphen, digit, or dot. This intentionally excludes labels like
    # "Text", "Image", "Audio", or "ChatGPT".
    return bool(MODEL_ID_RE.match(cell)) and cell[:1].islower() and any(ch in cell for ch in "-0123456789.")


def parse_pricing(markdown: str) -> List[PricingRecord]:
    tables = extract_sections(markdown)
    records: List[PricingRecord] = []

    for section, rows in tables:
        if len(rows) < 2:
            continue

        header_idx = next((i for i, row in enumerate(rows[:3]) if any("model" in c.lower() for c in row)), None)
        if header_idx is None:
            continue

        # Skip delimiter row if present immediately after the header row.
        data_start = header_idx + 1
        if len(rows) > data_start and all(set(c) <= {"-", ":", " "} for c in rows[data_start]):
            data_start += 1
        data_rows = rows[data_start:]
        current_model: Optional[str] = None
        for row in data_rows:
            if not row:
                continue
            first = row[0]
            if not first:
                continue

            if looks_like_model(first):
                current_model = first
                modality = row[1].lower() if len(row) > 1 and row[1].lower() in (MODALITIES | {"transcription"}) else "text"
                record = row_to_record(section, current_model, row, modality)
                if record:
                    records.append(record)
                continue

            # Category-first rows like: ChatGPT | gpt-5.3-chat-latest | $1.75 | ...
            if len(row) > 1 and looks_like_model(row[1]):
                current_model = row[1]
                modality = row[0].lower() if row[0].lower() in (MODALITIES | {"transcription"}) else row[0]
                record = row_to_record(section, current_model, row, modality)
                if record:
                    records.append(record)
                continue

            # Continuation row for multimodal tables (Text / Audio / Image)
            if current_model and first.lower() in MODALITIES:
                modality = first.lower()
                record = row_to_record(section, current_model, row, modality, continuation=True)
                if record:
                    records.append(record)
                continue

    return records


def row_to_record(section: str, model: str, row: List[str], modality: str, continuation: bool = False) -> Optional[PricingRecord]:
    raw = " | ".join(row)
    normalized = normalize_model_id(model)
    context = detect_context(section)

    # Continuation rows under gpt-realtime / gpt-image tables.
    if continuation and len(row) >= 4:
        return PricingRecord(
            model=normalized,
            source_model=model,
            section=section,
            context=context,
            modality=modality,
            input=row[1] if len(row) > 1 else None,
            cached_input=row[2] if len(row) > 2 else None,
            output=row[3] if len(row) > 3 else None,
            raw_row=raw,
        )

    # Row layouts:
    # 1) Model | Input | Cached input | Output
    # 2) Model | Input | Cached input | Output | Input | Cached input | Output
    # 3) Model | Modality | Input | Cached input | Output / cost
    # 4) Category | Model | Input | Cached input | Output | ...

    if len(row) >= 7 and row[0] == model:
        # Short/long context model rows.
        return PricingRecord(
            model=normalized,
            source_model=model,
            section=section,
            context=context,
            modality=modality,
            input=row[1],
            cached_input=row[2],
            output=row[3],
            estimated_cost=" / ".join(x for x in row[4:7] if x and x != "-"),
            raw_row=raw,
        )

    if len(row) >= 4 and row[0] == model and row[1].lower() in MODALITIES | {"transcription"}:
        # Multi-modal model rows.
        if row[1].lower() == "transcription" and len(row) >= 5:
            return PricingRecord(
                model=normalized,
                source_model=model,
                section=section,
                context=context,
                modality="transcription",
                input=row[2],
                output=row[3],
                estimated_cost=row[4],
                raw_row=raw,
            )
        return PricingRecord(
            model=normalized,
            source_model=model,
            section=section,
            context=context,
            modality=row[1].lower(),
            input=row[2] if len(row) > 2 else None,
            cached_input=row[3] if len(row) > 3 else None,
            output=row[4] if len(row) > 4 else None,
            estimated_cost=row[5] if len(row) > 5 else None,
            raw_row=raw,
        )

    if len(row) >= 5 and row[1] == model:
        # Category-first rows.
        return PricingRecord(
            model=normalized,
            source_model=model,
            section=section,
            context=context,
            modality=modality,
            input=row[2],
            cached_input=row[3] if len(row) > 3 else None,
            output=row[4] if len(row) > 4 else None,
            estimated_cost=row[5] if len(row) > 5 else None,
            raw_row=raw,
        )

    if len(row) >= 4 and row[0] == model:
        # Standard rows.
        return PricingRecord(
            model=normalized,
            source_model=model,
            section=section,
            context=context,
            modality=modality,
            input=row[1],
            cached_input=row[2] if len(row) > 2 else None,
            output=row[3] if len(row) > 3 else None,
            raw_row=raw,
        )

    return None


def detect_context(section: str) -> str:
    s = section.lower()
    if "batch" in s:
        return "batch"
    if "priority" in s:
        return "priority"
    if "flex" in s:
        return "flex"
    return "standard"


def build_index(records: List[PricingRecord]) -> Dict[str, List[PricingRecord]]:
    index: Dict[str, List[PricingRecord]] = {}
    for rec in records:
        index.setdefault(rec.model, []).append(rec)
    return index


def resolve_model(model: str, index: Dict[str, List[PricingRecord]]) -> List[PricingRecord]:
    candidates = [model, normalize_model_id(model)]
    # Try stripping common suffixes repeatedly.
    base = normalize_model_id(model)
    if base != model:
        candidates.append(base)
    # Try family aliases like gpt-5.4-mini-2026-03-17 -> gpt-5.4-mini
    for cand in list(candidates):
        if cand.endswith("-preview"):
            stem = cand[: -len("-preview")]
            if stem not in candidates:
                candidates.append(stem)
        if cand.endswith("-chat-latest"):
            stem = cand[: -len("-chat-latest")]
            if stem.endswith("-"):
                stem = stem[:-1]
            if stem not in candidates:
                candidates.append(stem)
        if cand.endswith("-latest"):
            stem = cand[: -len("-latest")]
            if stem.endswith("-"):
                stem = stem[:-1]
            if stem not in candidates:
                candidates.append(stem)
    seen = set()
    out: List[PricingRecord] = []
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        if cand in index:
            out.extend(index[cand])
    return out


def unique_sorted(records: Iterable[PricingRecord]) -> List[PricingRecord]:
    seen = set()
    out: List[PricingRecord] = []
    for r in records:
        key = (r.model, r.source_model, r.section, r.context, r.modality, r.input, r.cached_input, r.output, r.estimated_cost)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def print_table(rows: List[List[str]]) -> None:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    for idx, row in enumerate(rows):
        print(" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
        if idx == 0:
            print("-|-".join("-" * w for w in widths))


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract OpenAI model pricing from the public pricing page.")
    parser.add_argument("models", nargs="*", help="Model ids to look up, or 'available'/'all'.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--family", default="all", help="Filter family for 'available' mode: all, 4x5x, gpt, gpt-5, gpt-4, etc.")
    parser.add_argument("--sort", default="price-desc", choices=["price-desc", "price-asc", "name"], help="Sort order for 'available' mode.")
    parser.add_argument("--hide-unpriced", action="store_true", help="Omit models without public pricing.")
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        print("error: missing OPENAI_API_KEY and Keychain item OPENAI_API_KEY", file=sys.stderr)
        return 2

    try:
        available_models, pricing_md = fetch_sources(api_key)
    except Exception as e:
        print(f"error: failed to fetch sources: {e}", file=sys.stderr)
        return 1

    records = unique_sorted(parse_pricing(pricing_md))
    index = build_index(records)

    if not args.models or args.models == ["available"]:
        filtered_models = [m for m in available_models if family_matches(m, args.family)]
        chosen_map: Dict[str, Optional[PricingRecord]] = {}
        unresolved: List[str] = []
        for model in filtered_models:
            matches = resolve_model(model, index)
            chosen = choose_canonical_record(matches)
            if chosen is None:
                unresolved.append(model)
            else:
                chosen_map[model] = chosen

        if unresolved:
            ddg_cache = load_cache()
            with ThreadPoolExecutor(max_workers=min(2, len(unresolved))) as pool:
                fallback_results = list(pool.map(lambda m: search_pricing_fallback(m, cache=ddg_cache), unresolved))
            for model, chosen in zip(unresolved, fallback_results):
                if chosen is None and model.endswith("-chat-latest"):
                    base = model[: -len("-chat-latest")]
                    if base.endswith("-"):
                        base = base[:-1]
                    chosen = search_pricing_fallback(base, cache=ddg_cache)
                chosen_map[model] = chosen
            save_cache(ddg_cache)

        rows: List[Tuple[Optional[float], List[str]]] = []
        for model in filtered_models:
            chosen = chosen_map.get(model)
            if chosen is None and args.hide_unpriced:
                continue
            price = parse_money(chosen.input) if chosen else None
            rows.append((price, [model, "yes" if chosen else "no", chosen.input if chosen and chosen.input else "-", chosen.cached_input if chosen and chosen.cached_input else "-", chosen.output if chosen and chosen.output else "-", chosen.context if chosen else "-", chosen.section.split(" > ")[-1] if chosen else "-", chosen.source or "official" if chosen else "-"]))

        if args.sort == "name":
            rows.sort(key=lambda x: x[1][0])
        elif args.sort == "price-asc":
            rows.sort(key=lambda x: (x[0] is None, x[0] if x[0] is not None else float("inf"), x[1][0]))
        else:
            rows.sort(key=lambda x: (x[0] is None, -(x[0] if x[0] is not None else -1), x[1][0]))

        table = [["model", "priced?", "input", "cached", "output", "context", "section", "source"]] + [row for _, row in rows]
        if args.json:
            print(json.dumps({"models": table[1:], "pricing_records": [asdict(r) for r in records]}, indent=2))
        else:
            print_table(table)
        return 0

    if args.models == ["all"]:
        if args.json:
            print(json.dumps([asdict(r) for r in records], indent=2))
            return 0
        rows = [["model", "modality", "input", "cached", "output", "estimate", "context", "section", "source"]]
        for r in records:
            rows.append([r.model, r.modality, r.input or "-", r.cached_input or "-", r.output or "-", r.estimated_cost or "-", r.context, r.section.split(" > ")[-1], r.source or "official"])
        print_table(rows)
        return 0

    lookup_rows = [["requested", "resolved model", "input", "cached", "output", "estimate", "context", "section", "source"]]
    results: List[Dict[str, Any]] = []
    ddg_cache = load_cache()
    for q in args.models:
        matches = resolve_model(q, index)
        chosen = choose_canonical_record(matches)
        if chosen is None:
            chosen = search_pricing_fallback(q, cache=ddg_cache)
            if chosen is None and q.endswith("-chat-latest"):
                base = q[: -len("-chat-latest")]
                if base.endswith("-"):
                    base = base[:-1]
                chosen = search_pricing_fallback(base, cache=ddg_cache)
        if chosen:
            lookup_rows.append([q, chosen.model, chosen.input or "-", chosen.cached_input or "-", chosen.output or "-", chosen.estimated_cost or "-", chosen.context, chosen.section.split(" > ")[-1], chosen.source or "official"])
            results.append({"requested": q, **asdict(chosen)})
        else:
            lookup_rows.append([q, "unresolved", "-", "-", "-", "-", "-", "-", "-"])
            results.append({"requested": q, "resolved": None})

    save_cache(ddg_cache)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_table(lookup_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
