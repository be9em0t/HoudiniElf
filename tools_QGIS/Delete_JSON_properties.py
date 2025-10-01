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
from typing import Any


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
		"--overwrite",
		action="store_true",
		help="Overwrite the input file with the cleaned output",
	)
	return p.parse_args(argv)


def main(argv=None) -> int:
	args = parse_args(argv)

	input_path = args.input
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

	cleaned = remove_rel_source(data)

	try:
		with open(output_path, "w", encoding="utf-8") as fh:
			json.dump(cleaned, fh, indent=2, ensure_ascii=False)
	except Exception as e:
		print(f"Error writing JSON to {output_path}: {e}", file=sys.stderr)
		return 4

	print(f"Wrote cleaned JSON to: {output_path}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
