#!/usr/bin/env python3
"""
fix_nonprintable_spaces_column.py

Usage:
  python fix_nonprintable_spaces_column.py input.csv [--column COLNAME]

This script normalizes spaces and non-printable characters in a single column of a tab-delimited CSV file.
- Targets tab-delimited CSV files (TSV) with UTF-8 encoding (supports Arabic/RTL text)
- By default processes the 'translation' column
- If an NBSP (U+00A0) is found in a field, everything from the first NBSP to the end of the field (including the NBSP) is deleted
- After truncation, multiple ASCII spaces are collapsed into a single ASCII space and leading/trailing spaces are trimmed
- Preserves all other columns unchanged
- Use `--nbsp_lines_only` to output only rows where the selected column contained an NBSP (test mode)

Writes output to the same directory with `_NPC_fixed` appended before the extension.
"""

import sys
from pathlib import Path
import re
import argparse
import csv

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

# Compile patterns for NPC_AS_SPACE (these never change)
NPC_AS_SPACE_CLASS = build_char_class(NPC_AS_SPACE)
SEQ_SPACES_NPC = re.compile(r'(?:[ ]|' + NPC_AS_SPACE_CLASS + r')+')
MULTI_SPACES = re.compile(r'[ ]{2,}')
NPC_RUN = re.compile(r'(?:' + NPC_AS_SPACE_CLASS + r'){1,}')


def normalize_text(s: str, remove_directional: bool = False) -> str:
    """Normalize text by truncating at the first NBSP and collapsing spaces.

    Behaviour:
    1) If an NBSP (U+00A0) is present, remove the NBSP and everything after it.
    2) Collapse runs of ASCII spaces into a single space and trim leading/trailing spaces.

    Args:
        s: Text to normalize
        remove_directional: If True, also remove directional marks (U+200E/U+200F) before processing
    """
    # Step 0: Remove directional marks if requested
    if remove_directional:
        s = s.replace('\u200E', '').replace('\u200F', '')

    # Step 1: If an NBSP exists, truncate the field at the first NBSP (remove NBSP and everything after)
    idx = s.find('\u00A0')
    if idx != -1:
        s = s[:idx]

    # Step 2: Collapse multiple ASCII spaces to one and trim ends
    s = MULTI_SPACES.sub(' ', s)
    s = s.strip()

    return s


def read_csv_header(path: str):
    """Read CSV header for GUI column picker - compatible with GUI launcher."""
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        sample = fh.read(4096)
        sniffer = csv.Sniffer()
        try:
            delimiter = sniffer.sniff(sample, delimiters=',;\t').delimiter
        except Exception:
            delimiter = '\t'
        
        # Read first line for header
        fh.seek(0)
        first_line = fh.readline().rstrip('\n\r')
        header = [h.strip().strip('"') for h in first_line.split(delimiter)]
        
        return delimiter, header


def find_columns_with_nbsp(path: str):
    """Find all columns that contain NBSP characters.
    
    Returns:
        tuple: (delimiter, list of column names that contain NBSP)
    """
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            sample = fh.read(4096)
            sniffer = csv.Sniffer()
            try:
                delimiter = sniffer.sniff(sample, delimiters=',;\t').delimiter
            except Exception:
                delimiter = '\t'
        
        # Read file line by line
        with open(path, 'r', encoding='utf-8', errors='replace', newline='') as fh:
            lines = fh.readlines()
        
        if not lines:
            return delimiter, []
        
        # Parse header
        header_line = lines[0].rstrip('\n\r')
        header = [h.strip().strip('"') for h in header_line.split(delimiter)]
        
        # Track which columns have NBSP
        has_nbsp = [False] * len(header)
        
        # Check all data rows
        for line in lines[1:]:
            line = line.rstrip('\n\r')
            if not line.strip():
                continue
            
            fields = line.split(delimiter)
            for i, field in enumerate(fields):
                if i < len(has_nbsp) and '\u00A0' in field:
                    has_nbsp[i] = True
        
        # Get column names that have NBSP
        columns_with_nbsp = [header[i] for i in range(len(header)) if i < len(has_nbsp) and has_nbsp[i]]
        
        return delimiter, columns_with_nbsp
        
    except Exception as e:
        print(f'Error finding columns with NBSP: {e}', file=sys.stderr)
        return '\t', []


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the argument parser.
    
    This is required by the launcher GUI.
    """
    parser = argparse.ArgumentParser(
        description='Normalize spaces and non-printable characters in a single CSV column'
    )
    
    parser.add_argument('-f', '--file', help='Input tab-delimited CSV file (UTF-8 encoding)')
    parser.add_argument('-c', '--column', metavar='COLUMN', help='Column name to normalize (default: translation)')
    parser.add_argument('-o', '--output', help='Output file path (default: auto-generated with _NPC_fixed suffix)')
    parser.add_argument('-rd', '--remove-directional', action='store_true',
                        help='Also remove directional marks (U+200E/U+200F). Off by default to preserve RTL text')
    parser.add_argument('--nbsp_lines_only', action='store_true',
                        help='Output only rows where the target column contained an NBSP (test mode)')
    
    # Mark column as dynamic for GUI
    for action in parser._actions:
        if action.dest == 'column':
            action.is_dynamic_choices = True
            break
    
    return parser


def out_path_for(in_path: Path) -> Path:
    name = in_path.stem + '_NPC_fixed'
    if in_path.suffix:
        name += in_path.suffix
    return in_path.with_name(name)


def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    
    # Check if file argument is provided
    if not args.file:
        parser.print_help()
        print("\nError: --file is required", file=sys.stderr)
        return 1

    p = Path(args.file)
    if not p.exists():
        print('Input file not found:', p)
        return 3
    
    # If requested, extend NPC_REMOVE to include directional marks
    remove_dir = args.remove_directional
    nbsp_only = args.nbsp_lines_only

    # Determine output path
    if args.output:
        out = Path(args.output)
    else:
        out = out_path_for(p)
    
    # Determine column to process
    column_name = args.column if args.column else 'translation'
    
    # Detect delimiter
    delimiter = '\t'  # Default to tab
    try:
        with p.open('r', encoding='utf-8', errors='replace') as fh:
            sample = fh.read(4096)
            sniffer = csv.Sniffer()
            try:
                delimiter = sniffer.sniff(sample, delimiters=',;\t').delimiter
            except Exception:
                pass  # Keep default tab delimiter
    except Exception as e:
        print(f'Warning: Could not detect delimiter, using tab: {e}', file=sys.stderr)
    
    # Read line-by-line to handle malformed rows robustly
    # This avoids quote-matching issues with embedded quotes in RTL text
    try:
        with p.open('r', encoding='utf-8', errors='replace', newline='') as fh:
            lines = fh.readlines()
    except Exception as e:
        print(f'Error reading file: {e}', file=sys.stderr)
        return 4

    if not lines:
        print('Warning: empty input file', file=sys.stderr)
        return 5

    # Parse header
    header_line = lines[0].rstrip('\n\r')
    header = [h.strip().strip('"') for h in header_line.split(delimiter)]
    
    # Find the target column (case-sensitive exact match)
    try:
        col_idx = header.index(column_name)
    except ValueError:
        print(f"Error: column '{column_name}' not found in header. Available columns: {', '.join(header)}", file=sys.stderr)
        return 6

    # Process data rows line-by-line
    output_lines = [header_line + '\n']
    changed_count = 0
    nbsp_found_count = 0
    lines_written = 0
    
    for line_num, line in enumerate(lines[1:], start=2):
        line = line.rstrip('\n\r')
        if not line.strip():
            # Skip empty lines
            continue
        
        # Split by delimiter
        fields = line.split(delimiter)
        
        # Ensure row has enough columns (pad with empty strings if needed)
        while len(fields) < len(header):
            fields.append('')
        
        # Normalize the target column
        if col_idx < len(fields):
            original = fields[col_idx]
            had_nbsp = '\u00A0' in original

            # If test mode and row did not contain NBSP, skip writing this line
            if nbsp_only and not had_nbsp:
                continue

            fields[col_idx] = normalize_text(fields[col_idx], remove_directional=remove_dir)
            if fields[col_idx] != original:
                changed_count += 1
            if had_nbsp:
                nbsp_found_count += 1
        
        # Reconstruct line
        output_line = delimiter.join(fields) + '\n'
        output_lines.append(output_line)
        lines_written += 1

    # Write output
    with out.open('w', encoding='utf-8', newline='') as fh:
        fh.writelines(output_lines)
    
    if nbsp_only:
        print(f"Wrote {lines_written} rows (only rows that contained NBSP) to: {out}")
        print(f"Found NBSP in {nbsp_found_count} rows in column '{column_name}' (normalized {changed_count} rows)")
    else:
        print(f"Wrote: {out}")
        print(f"Normalized {changed_count} rows in column '{column_name}'")
    
    # Check if any columns still have NBSP after processing
    _, remaining_cols = find_columns_with_nbsp(str(out))
    if remaining_cols:
        print(f"\nWarning: Columns still containing NBSP: {', '.join(remaining_cols)}")
        print("(These were not processed - only the specified column was normalized)")
    else:
        print("\n✓ No NBSP characters remaining in output file")
    
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
