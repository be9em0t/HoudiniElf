#!/usr/bin/env python3
"""
⚡ Synonyms2Access.py — convert 5-column translations TSV to 3-column TSV (adds IsSynonym)

How to use:
Show help (now default): python Synonyms2Access.py
Process a single (or specific) file: python Synonyms2Access.py 'Translations_Synon_04 Claude.tsv'
Process all matching files in the folder: python Synonyms2Access.py --all
Combine with normalization and dry-run: python Synonyms2Access.py --all --normalize --dry-run
"""

import argparse
import csv
from pathlib import Path
import sys
import unicodedata


def process_file(p: Path, suffix: str = "_access", normalize: bool = False) -> int:
	"""Process a single TSV file and write a 3-column TSV (name_en, translation_XX, IsSynonym).

	Returns the number of output rows written.
	"""
	p = Path(p)
	out = p.with_name(p.stem + suffix + p.suffix)
	# prepare normalizer (NFC) if requested
	if normalize:
		def norm(s: str) -> str:
			return unicodedata.normalize("NFC", s)
	else:
		def norm(s: str) -> str:
			return s
	with p.open("r", encoding="utf-8-sig", newline="") as fh:
		reader = csv.reader(fh, delimiter="\t")
		try:
			headers = next(reader)
		except StopIteration:
			print(f"Empty file: {p}", file=sys.stderr)
			return 0
		if len(headers) < 2:
			print(f"File {p} doesn't have at least 2 columns", file=sys.stderr)
			return 0
		keyfield = norm(headers[0].strip())
		translation_field = norm(headers[1].strip())
		# any remaining columns are treated as synonyms
		# we tolerate more or fewer columns than exactly 5
		out_rows = []
		for row in reader:
			# pad short rows
			if len(row) < len(headers):
				row += [""] * (len(headers) - len(row))
			key = norm(row[0].strip())
			if not key:
				continue
			primary = norm(row[1].strip())
			if primary:
				# primary translation: not a synonym
				out_rows.append((key, primary, ""))
			for i in range(2, len(headers)):
				val = norm(row[i].strip())
				if val:
					# synonyms are flagged
					out_rows.append((key, val, "SYNONYM"))

	with out.open("w", encoding="utf-8", newline="") as ofh:
		writer = csv.writer(ofh, delimiter="\t", lineterminator="\n")
		writer.writerow([keyfield, translation_field, "IsSynonym"])
		for k, v, s in out_rows:
			writer.writerow([k, v, s])

	print(f"Wrote {len(out_rows)} rows to {out}")
	return len(out_rows)


def _self_test() -> None:
	"""Quick self-test using a temporary file."""
	import tempfile
	from pathlib import Path

	tmp = Path(tempfile.mkdtemp())
	inp = tmp / "test.tsv"
	inp.write_text(
		"name_en\ttranslation_bg\tsyn1\tsyn2\nA\tА\tА1\t\nB\tБ\t\tБ2\n",
		encoding="utf-8",
	)
	process_file(inp, suffix="_out")
	out = tmp / "test_out.tsv"
	txt = out.read_text(encoding="utf-8")
	expected = (
			"name_en\ttranslation_bg\tIsSynonym\n"
			"A\tА\t\n"
			"A\tА1\tSYNONYM\n"
			"B\tБ\t\n"
			"B\tБ2\tSYNONYM\n"
		)
	assert txt == expected, f"Self-test failed.\nGot:\n{txt!r}\nExpected:\n{expected!r}"

	# Test Unicode normalization (decomposed -> composed)
	ninp = tmp / "test_norm.tsv"
	# 'e' + combining acute accent vs precomposed 'é'
	ninp.write_text("name_en\ttranslation_bg\nX\te\u0301\n", encoding="utf-8")
	process_file(ninp, suffix="_norm", normalize=True)
	nout = tmp / "test_norm_norm.tsv"
	ntxt = nout.read_text(encoding="utf-8")
	nexpected = "name_en\ttranslation_bg\tIsSynonym\nX\t\u00e9\t\n"
	assert ntxt == nexpected, f"Normalization test failed.\nGot:\n{ntxt!r}\nExpected:\n{nexpected!r}"

	# Verify that calling main([]) prints help and exits cleanly (simulated no-args)
	# We call parser via main([]) and expect return 0
	ret = main([])
	assert ret == 0, "Expected main([]) to return 0 (help printed)"


def main(argv=None):
	parser = argparse.ArgumentParser(
		description="Convert Translations_Synon_*.tsv to 3-column TSV (name_en, translation_XX, IsSynonym).",
	)
	parser.add_argument("files", nargs="*", help="TSV files to process (default: Translations_Synon_*.tsv)")
	parser.add_argument("--suffix", "-s", default="_access", help="Suffix appended to the output basename")
	parser.add_argument("--dry-run", action="store_true", help="List candidate files without writing outputs")
	parser.add_argument("--all", action="store_true", help="Process all matching Translations_Synon_*.tsv files in script folder")
	parser.add_argument("--normalize", action="store_true", help="Normalize all text to NFC (optional)")
	parser.add_argument("--test", action="store_true", help="Run a quick self-test and exit")
	args = parser.parse_args(argv)
	if args.test:
		_self_test()
		return 0

	# Sanity check: ensure main behaviour unchanged for explicit empty-invocation tests
	# (used by self-test). If someone calls main([]) we want it to print help and return 0 (same as running without args).

	# Decide candidate files:
	if args.files:
		files = [Path(f) for f in args.files]
	elif args.all:
		files = list(Path(__file__).parent.glob("Translations_Synon_*.tsv"))
	else:
		# No explicit files and --all not provided -> show help
		parser.print_help()
		return 0

	if not files:
		print("No files to process.", file=sys.stderr)
		return 2

	for f in files:
		if not f.exists():
			print(f"Skipping missing file: {f}", file=sys.stderr)
			continue
		if args.dry_run:
			print(f"Would process: {f}")
			continue
		process_file(f, suffix=args.suffix, normalize=args.normalize)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
