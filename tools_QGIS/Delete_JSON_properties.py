#!/usr/bin/env python3
"""
Delete JSON properties starting with 'rel_source'.

Usage:
  Delete_JSON_properties.py input.json [--output output.json] [--overwrite]

If --output is not provided, the script writes to a new file with
"_output" appended before the extension (e.g. input_output.json).
--overwrite will overwrite the input file.

The script will remove any dict keys that start with the string
"rel_source" anywhere in the JSON structure (recursively).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Iterable, List, Tuple
import fnmatch

# --- User-configurable named modes (glob patterns) ---
# Define named glob patterns here. Keep them simple: '*' and '?' are supported.
# Example:
# HD_lanes = ["rel_source*"]
# HD_tracks = ["rel_track*", "rel_source_track*"]
# Then add them to NAMED_MODES below.

HD_lanes = ["id", "rel_source*", "way_node*", "revision", "modified*", "uow_ids", "origin", "kind_featurestore"]
HD_lanes_min = ["rel_source*"]
HD_tracks = ["rel_track*"]

NAMED_MODES = {
	"HD_lanes": HD_lanes,
	"HD_lanes_min": HD_lanes_min,
	"HD_tracks": HD_tracks,
}



def remove_rel_source(obj: Any) -> Any:
	"""Recursively remove keys starting with 'rel_source' from JSON-like object.

	Args:
		obj: A JSON-decoded object (dict, list, or primitive).

	Returns:
		The cleaned object with keys removed.
	"""
	if isinstance(obj, dict):
		new = {}
		for k, v in obj.items():
			if isinstance(k, str) and k.startswith("rel_source"):
				# skip this key
				continue
			new[k] = remove_rel_source(v)
		return new
	elif isinstance(obj, list):
		return [remove_rel_source(v) for v in obj]
	else:
		return obj


def make_glob_predicate(patterns: Iterable[str]) -> Callable[[str], bool]:
	"""Return a predicate that matches a key against any of the glob patterns."""
	pats = list(patterns)

	def pred(key: str) -> bool:
		for p in pats:
			if fnmatch.fnmatch(key, p):
				return True
		return False

	return pred


def remove_by_predicate(obj: Any, predicate: Callable[[str], bool], stats: dict | None = None) -> Any:
	"""Recursively remove dict keys for which predicate(key) is True.

	Optionally collects stats in the provided dict: {'removed': int}
	"""
	if stats is None:
		stats = {"removed": 0}

	if isinstance(obj, dict):
		new = {}
		for k, v in obj.items():
			if isinstance(k, str) and predicate(k):
				stats["removed"] += 1
				continue
			new[k] = remove_by_predicate(v, predicate, stats)
		return new
	elif isinstance(obj, list):
		return [remove_by_predicate(v, predicate, stats) for v in obj]
	else:
		return obj


def make_output_path(input_path: str) -> str:
	base, ext = os.path.splitext(input_path)
	if not ext:
		ext = ".json"
	return f"{base}_output{ext}"


def parse_args(argv=None) -> argparse.Namespace:
	p = argparse.ArgumentParser(
		description="Remove JSON properties whose keys start with 'rel_source'."
	)
	p.add_argument("input", help="Path to input JSON file")
	p.add_argument("-o", "--output", help="Path to output JSON file")
	p.add_argument(
		"--pattern",
		action="append",
		help="Glob pattern to delete (supports * and ?). Repeatable.",
	)
	p.add_argument(
		"--mode",
		action="append",
		help="Named mode to use (predefined in the script). Repeatable.",
	)
	p.add_argument(
		"--dry-run",
		action="store_true",
		help="Don't write output; print summary of what would be removed.",
	)
	p.add_argument(
		"--overwrite",
		action="store_true",
		help="Overwrite the input file with the cleaned output",
	)
	return p.parse_args(argv)




def main(argv=None) -> int:
	args = parse_args(argv)

	input_path = args.input

	# Build patterns: CLI patterns override/extend named modes
	patterns: List[str] = []
	if args.mode:
		for name in args.mode:
			if name not in NAMED_MODES:
				print(f"Unknown mode: {name}", file=sys.stderr)
				return 5
			patterns.extend(NAMED_MODES[name])

	if args.pattern:
		patterns.extend(args.pattern)

	# Default: if no patterns specified, use HD_lanes (original behavior)
	if not patterns:
		patterns = HD_lanes.copy()

	predicate = make_glob_predicate(patterns)
	if not os.path.isfile(input_path):
		print(f"Error: input file does not exist: {input_path}", file=sys.stderr)
		return 2

	output_path = args.output or make_output_path(input_path)
	if args.overwrite:
		output_path = input_path

	try:
		with open(input_path, "r", encoding="utf-8") as fh:
			data = json.load(fh)
	except Exception as e:
		print(f"Error reading JSON from {input_path}: {e}", file=sys.stderr)
		return 3

	stats = {"removed": 0}
	cleaned = remove_by_predicate(data, predicate, stats)

	if args.dry_run:
		print(f"Dry run: would remove {stats['removed']} keys matching patterns: {patterns}")
		return 0

	try:
		with open(output_path, "w", encoding="utf-8") as fh:
			json.dump(cleaned, fh, indent=2, ensure_ascii=False)
	except Exception as e:
		print(f"Error writing JSON to {output_path}: {e}", file=sys.stderr)
		return 4

	print(f"Wrote cleaned JSON to: {output_path} (removed {stats['removed']} keys)")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
