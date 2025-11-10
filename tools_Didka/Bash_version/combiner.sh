
#!/bin/bash
set -euo pipefail

# combine CSV files in a directory into a single CSV with one header
# Usage:
#   combiner.sh [directory] [output.csv]
# Defaults: directory=".", output.csv="combined.csv"

usage() {
  cat <<EOF
Usage: $0 [directory] [output.csv]

Combine all .csv files in [directory] (default: current dir) into [output.csv]
Only the header from the first file is kept. Files are processed in alphabetical order.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

dir="${1:-.}"
out="${2:-combined.csv}"

# Work in the target directory
if [ ! -d "$dir" ]; then
  echo "Directory not found: $dir" >&2
  exit 1
fi

cd "$dir"

# Avoid including the output file if it's in the same directory
out_basename=$(basename "$out")

# Use bash nullglob so that the loop skips when no matches
shopt -s nullglob

first_header=""
first_file=""

# Truncate/create output file (in cwd or as a path relative to cwd)
: > "$out" || { echo "Cannot write to output: $out" >&2; exit 1; }

for f in *.csv; do
  # skip the output file if it lives here
  if [ "$f" = "$out_basename" ]; then
    continue
  fi

  # skip non-regular or empty files
  if [ ! -f "$f" ] || [ ! -s "$f" ]; then
    continue
  fi

  header=$(head -n 1 "$f")

  if [ -z "$first_header" ]; then
    first_header="$header"
    first_file="$f"
    printf '%s
' "$first_header" > "$out"
  else
    if [ "$header" != "$first_header" ]; then
      printf 'Warning: header mismatch in %s\n' "$f" >&2
    fi
  fi

  # Append data (exclude header)
  tail -n +2 "$f" >> "$out"
done

if [ ! -s "$out" ]; then
  echo "No CSV data was combined; output is empty: $out" >&2
  exit 1
fi

echo "Combined CSV written to: $out (header from: ${first_file:-none})"
