#!/usr/bin/env python3
"""find_keys.py — scan a CSV's tags column for keys starting with a prefix and list them.

Usage: python find_keys.py input.csv

Put the column name and key prefix near the top as variables for easy adjustment.
"""

# ⚙️ Configuration variables (edit if needed)
TAGS_COLUMN = 'tags'
KEY_PREFIX = 'building'

import argparse
import csv
import sys
import collections
import re


def parse_tags(tags_str):
	"""Parse a tags string into a dict of key->value.

	Supports common separators (';', ',', '|') and separators '=', '->', or ':' when appropriate.
	This version handles '->' (e.g., 'building:levels -> 1') by splitting on '->'
	so keys like 'building:levels' are preserved. It also preserves trailing colon keys
	(e.g. 'building:') and returns an empty dict for empty/None input.
	"""
	if not tags_str:
		return {}
	# strip surrounding quotes and whitespace
	tags_str = tags_str.strip().strip('"').strip("'")
	parts = re.split(r'[;,\|]\s*', tags_str)
	result = {}
	for part in parts:
		part = part.strip()
		if not part:
			continue
		# Prefer '=' as key/value separator first
		if '=' in part:
			k, v = part.split('=', 1)
		else:
			# handle '->' as a separator (with optional spaces)
			m = re.split(r'\s*->\s*', part, maxsplit=1)
			if len(m) == 2:
				k, v = m[0], m[1]
			# only treat single ':' as separator when it doesn't end with ':' (preserve 'building:')
			elif ':' in part and not part.endswith(':') and part.count(':') == 1:
				k, v = part.split(':', 1)
			else:
				k, v = part, ''
		result[k.strip()] = v.strip()
	return result


def find_keys_in_csv(csv_path, tags_column=TAGS_COLUMN, key_prefix=KEY_PREFIX, delimiter=','):
	"""Return (counts, values) for keys starting with key_prefix found in tags_column.

	counts is collections.Counter of key -> occurrence count.
	values is dict of key -> set(values seen).
	"""
	counts = collections.Counter()
	values = {}
	with open(csv_path, newline='') as fh:
		reader = csv.DictReader(fh, delimiter=delimiter)
		if tags_column not in (reader.fieldnames or []):
			raise KeyError(f"Column {tags_column!r} not found in {csv_path} (found: {reader.fieldnames})")
		for row in reader:
			tags = parse_tags(row.get(tags_column, ''))
			for k, v in tags.items():
				if k.startswith(key_prefix):
					counts[k] += 1
					values.setdefault(k, set()).add(v)
	return counts, values


def main():
	parser = argparse.ArgumentParser(description="Scan a CSV 'tags' column for keys starting with a prefix.")
	parser.add_argument('csv', help='Input CSV file')
	parser.add_argument('--column', default=TAGS_COLUMN, help=f"Tags column (default: {TAGS_COLUMN})")
	parser.add_argument('--prefix', default=KEY_PREFIX, help=f"Key prefix to search for (default: {KEY_PREFIX})")
	parser.add_argument('--delimiter', default=',', help='CSV delimiter (default: ,)')
	args = parser.parse_args()
	try:
		counts, values = find_keys_in_csv(args.csv, tags_column=args.column, key_prefix=args.prefix, delimiter=args.delimiter)
	except Exception as e:
		print("Error:", e, file=sys.stderr)
		sys.exit(2)
	if not counts:
		print(f"No keys found with prefix {args.prefix!r}")
		return
	print(f"Found {sum(counts.values())} tag occurrences matching prefix {args.prefix!r}")
	# compute column widths for neat aligned output
	key_w = max(len("Key"), max((len(k) for k in counts), default=0))
	count_w = max(len("Count"), max((len(str(c)) for c in counts.values()), default=0))
	print(f"{'Key':<{key_w}}  {'Count':>{count_w}}  Unique values (sample)")
	for k, c in counts.most_common():
		raw_vals = sorted(values.get(k, {''}))
		# Show any empty values as '<empty>' so bare keys like 'building:' are visible
		display_vals = [v if v != '' else '<empty>' for v in raw_vals]
		sample = ", ".join(display_vals[:5])
		print(f"{k:<{key_w}}  {c:>{count_w}}  {sample}")


if __name__ == '__main__':
	main()
# look in column 'tags' 
# and list all keys that start with 'building'
# put column name and key search term near the top as variables