"""Origin-Destination column rename and reorder

This script normalizes messy CSV column headers like:
  "Date range: 2025-03-01 - 2025-06-30 Time range: 00:00 - 04:00 Trips"
or
  "Date range: 2025-03-01 - 2025-06-30 Time range: 00:00 - 04:00 Percent11"

Behavior implemented:
1) If the last word has trailing digits (e.g. Trips11) the digits are replaced with a single '2' (Trips2).
2) Columns are renamed to <Label>_HHMM-HHMM where Label is Trips/Percent/Trips2/Percent2 and HHMM-HHMM is taken from the "Time range: 00:00 - 04:00" portion.
   Example: "Date range: ... Time range: 00:00 - 04:00 Trips11" -> "Trips2_0000_0400"
3) Columns are reordered in this group order: Trips_*, Percent_*, Trips2_*, Percent2_* (others are at the beginning).

Usage:
  python OD_Filter_and_Sort.py input.csv [output.csv]

If output.csv is omitted, a file named input_fixed.csv will be written next to the input.
Dont forget
pip install pandas
"""

from __future__ import annotations

import re
import sys
from typing import Dict, List, Tuple

import pandas as pd


def normalize_col(col: str) -> str:
	"""Return normalized column name.

	- Extract time from "Time range: HH:MM - HH:MM" if present and format as HHMM-HHMM.
	- Take last word (alpha part) as label (Trips or Percent).
	- If last word had trailing digits, replace them with '2' (e.g. Trips11 -> Trips2).
	- Return "<Label>_HHMM-HHMM" or just "<Label>" when time is missing.
	"""
	if not isinstance(col, str):
		return col

	# find time range
	tm = re.search(r"Time range:\s*([0-9]{2}:[0-9]{2})\s*-\s*([0-9]{2}:[0-9]{2})", col)
	if tm:
		start, end = tm.groups()
		start_n = start.replace(":", "")
		end_n = end.replace(":", "")
		# use underscore between start and end to satisfy downstream reader
		time_part = f"{start_n}_{end_n}"
	else:
		time_part = None

	# get last token (last word) from the header
	last = col.strip().split()[-1] if col.strip() else col

	m = re.match(r"([A-Za-z]+)(\d*)$", last)
	if not m:
		# fallback: if we cannot parse, return original (or include time)
		return f"{last}_{time_part}" if time_part else last

	base = m.group(1)
	digits = m.group(2)
	label = base + ("2" if digits else "")

	return f"{label}_{time_part}" if time_part else label


def rename_columns(cols: List[str]) -> Tuple[Dict[str, str], List[str]]:
	mapping: Dict[str, str] = {}
	new_cols: List[str] = []
	for c in cols:
		nc = normalize_col(c)
		mapping[c] = nc
		new_cols.append(nc)
	return mapping, new_cols


def reorder_columns_order(colnames: List[str]) -> List[str]:
	"""Return column names sorted by the requested group order.

	Group priorities:
	  0 -> Trips (no trailing '2')
	  1 -> Percent (no trailing '2')
	  2 -> Trips2
	  3 -> Percent2
	  4 -> others
	"""
	# New ordering: put all non-Trips/Percent columns first, then
	# Trips, Percent, Trips2, Percent2 (each group sorted by time suffix when present).

	def secondary(name: str) -> str:
		# sort by the time part if present, otherwise by full name
		# join all parts after the first so time like 0000_0400 is returned as a single key
		parts = name.split("_")
		return "_".join(parts[1:]) if len(parts) > 1 else name

	others: List[str] = []
	trips: List[str] = []
	percent: List[str] = []
	trips2: List[str] = []
	percent2: List[str] = []

	for name in colnames:
		if name.startswith("Trips2"):
			trips2.append(name)
		elif name.startswith("Trips"):
			trips.append(name)
		elif name.startswith("Percent2"):
			percent2.append(name)
		elif name.startswith("Percent"):
			percent.append(name)
		else:
			others.append(name)

	# sort each group by the secondary key (time part)
	others = sorted(others, key=secondary)
	trips = sorted(trips, key=secondary)
	percent = sorted(percent, key=secondary)
	trips2 = sorted(trips2, key=secondary)
	percent2 = sorted(percent2, key=secondary)

	# final order: others first, then trips, percent, trips2, percent2
	return others + trips + percent + trips2 + percent2


def process_csv(inpath: str, outpath: str | None = None) -> str:
	"""Read CSV, rename headers, reorder columns and write output CSV.

	Returns the path to the written file.
	"""
	df = pd.read_csv(inpath)
	old_cols = list(df.columns)
	mapping, _ = rename_columns(old_cols)
	df = df.rename(columns=mapping)

	ordered = reorder_columns_order(list(df.columns))
	# keep stable: include any columns not matched by ordering at the end
	ordered = [c for c in ordered if c in df.columns] + [c for c in df.columns if c not in ordered]
	df = df[ordered]

	if outpath is None:
		outpath = inpath.replace(".csv", "_fixed.csv")

	df.to_csv(outpath, index=False)
	return outpath


def main(argv: List[str]) -> int:
	if len(argv) < 2:
		print("Usage: python OD_Filter_and_Sort.py input.csv [output.csv]")
		return 1

	inp = argv[1]
	out = argv[2] if len(argv) >= 3 else None
	outpath = process_csv(inp, out)
	print(f"Wrote fixed CSV to: {outpath}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main(sys.argv))