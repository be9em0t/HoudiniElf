#!/usr/bin/env python3
"""
fix_nonprintable_spaces.py

Usage:
  python fix_nonprintable_spaces.py input.txt

This script normalizes spaces and non-printable characters in a UTF-8 text file.
- Configure `NPC_CHARS` near the top to control which non-printable characters are considered.
- Replaces any sequence of spaces and configured non-printable characters with a single ASCII space.
- Replaces 2+ ASCII spaces with a single ASCII space.
- Replaces any run of configured non-printable characters (with no space between) with a single ASCII space.

Writes output to the same directory with `_NPC_fixed` appended before the extension.
"""

import sys
from pathlib import Path
import re
import argparse

# === Configuration ===
# Two configurable lists control how characters are handled:
# - NPC_AS_SPACE: characters treated like spaces (they will be collapsed with spaces into a single ASCII space)
# - NPC_REMOVE: characters removed entirely (useful for directional marks like LRM/RLM which break RTL text)
#
# By default only normalize NO-BREAK SPACE (U+00A0) into a regular ASCII space.
# We intentionally preserve tabs and directional marks so RTL Arabic text
# and existing tab structure remain intact. If you explicitly want to remove
# directionality marks, use `--remove-directional` on the command line.
NPC_AS_SPACE = ["\u00A0"]
NPC_REMOVE = []
# You can edit the two lists above to add or remove codepoints as needed.

# Build a character class for regex that matches any of these characters
def build_char_class(chars):
    # Escape each char for regex character class
    parts = []
    for ch in chars:
        cp = ord(ch)
        # if printable ASCII, escape if needed
        if ch == '-' or ch == '^' or ch == ']' or ch == '\\':
            parts.append('\\' + ch)
        elif 32 <= cp <= 126:
            parts.append(re.escape(ch))
        else:
            parts.append('\\u%04X' % cp)
    if not parts:
        return '(?!)'  # a class that matches nothing
    return '[' + ''.join(parts) + ']'

NPC_AS_SPACE_CLASS = build_char_class(NPC_AS_SPACE)
NPC_REMOVE_CLASS = build_char_class(NPC_REMOVE)

# Matches any sequence that is made of ASCII spaces and/or NPC_AS_SPACE characters
SEQ_SPACES_NPC = re.compile(r'(?:[ ]|' + NPC_AS_SPACE_CLASS + r')+')
# Matches sequences of 2+ ASCII spaces
MULTI_SPACES = re.compile(r'[ ]{2,}')
# Matches sequence of NPC_AS_SPACE chars with no ASCII space
NPC_RUN = re.compile(r'(?:' + NPC_AS_SPACE_CLASS + r'){1,}')
# Matches any NPC_REMOVE characters (to delete)
NPC_REMOVE_RE = re.compile(r'(?:' + NPC_REMOVE_CLASS + r')+')


def normalize_text(s: str) -> str:
    # Step 0: Remove configured characters that should be deleted entirely
    # (directionality marks, zero-width marks, etc.). Removing these
    # preserves the logical order of RTL text.
    if NPC_REMOVE_CLASS != '(?!)':
        s = NPC_REMOVE_RE.sub('', s)

    # Step 1: Replace any sequence of ASCII spaces and NPC-as-space characters with a single ASCII space
    s = SEQ_SPACES_NPC.sub(' ', s)

    # Step 2: Defensive: replace any remaining runs of NPC-as-space characters with a single ASCII space
    s = NPC_RUN.sub(' ', s)

    # Step 3: Collapse 2+ ASCII spaces to one
    s = MULTI_SPACES.sub(' ', s)
    return s


def out_path_for(in_path: Path) -> Path:
    name = in_path.stem + '_NPC_fixed'
    if in_path.suffix:
        name += in_path.suffix
    return in_path.with_name(name)


def main(argv):
    class HintingArgumentParser(argparse.ArgumentParser):
        def error(self, message):
            # Provide the original error message, then hint that -h/--help is available
            self.print_usage(sys.stderr)
            err = f"error: {message}. Use -h/--help for usage.\n"
            self.exit(2, err)

    parser = HintingArgumentParser(description='Normalize spaces and configured non-printable characters')
    parser.add_argument('input', help='Input UTF-8 text file (plain text or CSV/TSV)')
    parser.add_argument('-rd', '--remove-directional', action='store_true',
                        help='Also remove directional marks (U+200E/U+200F). Off by default to preserve RTL text')
    parser.add_argument('-d', '--delimiter', help='Force delimiter: "," for CSV or "\t" for TSV. If not provided the script will try to detect it.')
    args = parser.parse_args(argv[1:])

    p = Path(args.input)
    if not p.exists():
        print('Input file not found:', p)
        return 3
    # Read file with robust encoding fallback: prefer UTF-8 strict, then UTF-8 with replacement, then latin-1
    try:
        data = p.read_text(encoding='utf-8')
    except UnicodeDecodeError as e:
        print('Warning: file not valid UTF-8 (strict). Retrying with replacement for invalid bytes.', file=sys.stderr)
        try:
            data = p.read_text(encoding='utf-8', errors='replace')
        except Exception:
            print('Warning: retry with UTF-8 replace failed; falling back to latin-1.', file=sys.stderr)
            data = p.read_text(encoding='latin-1')
    # If requested, extend NPC_REMOVE to include directional marks
    if args.remove_directional:
        global NPC_REMOVE_CLASS, NPC_REMOVE_RE
        # add directional marks to the remove list (if not already present)
        for ch in ('\u200E', '\u200F'):
            if ch not in NPC_REMOVE:
                NPC_REMOVE.append(ch)
        NPC_REMOVE_CLASS = build_char_class(NPC_REMOVE)
        NPC_REMOVE_RE = re.compile(r'(?:' + NPC_REMOVE_CLASS + r')+')

    fixed = normalize_text(data)
    out = out_path_for(p)
    # If file appears to be CSV/TSV, only normalize the 'translation' column
    import csv

    def is_probably_tab_separated(text: str) -> bool:
        # Heuristic: if tabs occur more often than commas on first few lines, assume TSV
        sample = '\n'.join(text.splitlines()[:10])
        return sample.count('\t') > sample.count(',')

    delim = None
    if args.delimiter:
        if args.delimiter == '\\t':
            delim = '\t'
        else:
            delim = args.delimiter
    else:
        delim = '\t' if is_probably_tab_separated(data) else ','

    # Try to parse CSV with detected delimiter. If header contains 'translation', operate per-column.
    try:
        rows = list(csv.reader(data.splitlines(), delimiter=delim))
    except Exception:
        # Fallback: write the normalized whole file
        out.write_text(fixed, encoding='utf-8')
        print('Wrote (normalized whole file):', out)
        return 0

    if not rows:
        out.write_text(fixed, encoding='utf-8')
        print('Wrote (empty input):', out)
        return 0

    header = rows[0]
    # Find the translation column (case-sensitive exact match)
    try:
        col_idx = header.index('translation')
    except ValueError:
        # No translation column: write normalized whole file
        out.write_text(fixed, encoding='utf-8')
        print("No 'translation' column found; wrote normalized whole file:", out)
        return 0

    # Normalize only the translation column for all subsequent rows
    new_rows = [header]
    for r in rows[1:]:
        # Ensure row has enough columns
        if col_idx < len(r):
            r[col_idx] = normalize_text(r[col_idx])
        new_rows.append(r)

    # Write back using same delimiter and quoting minimal
    with out.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.writer(fh, delimiter=delim, quoting=csv.QUOTE_MINIMAL)
        for r in new_rows:
            writer.writerow(r)
    print('Wrote (column-normalized):', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
