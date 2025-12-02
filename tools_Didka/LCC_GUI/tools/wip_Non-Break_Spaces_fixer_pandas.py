#!/usr/bin/env python3
"""
fix_nonprintable_spaces_column.py

Usage:
  python fix_nonprintable_spaces_column.py input.csv [--column COLNAME]

This script normalizes spaces and non-printable characters in a single column of a tab-delimited CSV file.
- Targets tab-delimited CSV files (TSV) with UTF-8 encoding (supports Arabic/RTL text)
- By default processes the 'translation' column
- Replaces any sequence of spaces and NBSP (U+00A0) with a single ASCII space
- Replaces 2+ ASCII spaces with a single ASCII space
- Replaces multiple NBSP characters with a single ASCII space
- Preserves all other columns unchanged

Writes output to the same directory with `_NPC_fixed` appended before the extension.
"""

import sys
from pathlib import Path
import re
import argparse

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required. Install with: pip install pandas", file=sys.stderr)
    sys.exit(1)

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

    parser = HintingArgumentParser(description='Normalize spaces and configured non-printable characters in a single CSV column')
    parser.add_argument('input', help='Input tab-delimited CSV file (UTF-8 encoding)')
    parser.add_argument('-c', '--column', default='translation',
                        help='Column name to normalize (default: translation)')
    parser.add_argument('-rd', '--remove-directional', action='store_true',
                        help='Also remove directional marks (U+200E/U+200F). Off by default to preserve RTL text')
    args = parser.parse_args(argv[1:])

    p = Path(args.input)
    if not p.exists():
        print('Input file not found:', p)
        return 3
    
    # If requested, extend NPC_REMOVE to include directional marks
    if args.remove_directional:
        global NPC_REMOVE_CLASS, NPC_REMOVE_RE
        # add directional marks to the remove list (if not already present)
        for ch in ('\u200E', '\u200F'):
            if ch not in NPC_REMOVE:
                NPC_REMOVE.append(ch)
        NPC_REMOVE_CLASS = build_char_class(NPC_REMOVE)
        NPC_REMOVE_RE = re.compile(r'(?:' + NPC_REMOVE_CLASS + r')+')

    out = out_path_for(p)
    
    # Read tab-delimited CSV as DataFrame
    # Use on_bad_lines='warn' to handle rows with inconsistent column counts
    try:
        df = pd.read_csv(p, sep='\t', encoding='utf-8', encoding_errors='replace', 
                        dtype=str, keep_default_na=False, on_bad_lines='warn')
    except Exception as e:
        print(f'Error reading CSV: {e}', file=sys.stderr)
        return 4

    if df.empty:
        print('Warning: empty input file', file=sys.stderr)
        return 5

    # Check if target column exists
    if args.column not in df.columns:
        print(f"Error: column '{args.column}' not found. Available columns: {', '.join(df.columns)}", file=sys.stderr)
        return 6

    # Normalize only the target column
    original_values = df[args.column].copy()
    df[args.column] = df[args.column].apply(normalize_text)
    
    # Count how many rows actually changed
    changed_count = (df[args.column] != original_values).sum()

    # Write back as tab-delimited CSV
    df.to_csv(out, sep='\t', index=False, encoding='utf-8', lineterminator='\n')
    
    print(f"Wrote: {out}")
    print(f"Normalized {changed_count} rows in column '{args.column}'")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
