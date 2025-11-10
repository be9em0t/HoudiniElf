#!/bin/bash

# Check if at least one file is provided
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 file1.csv [file2.csv ...]"
  exit 1
fi

# Loop through each provided file
for input_file in "$@"; do
  # Get the base name without extension
  base_name="${input_file%.*}"

  # Extract header
  header=$(head -n 1 "$input_file")

  # Create a temp directory to hold split parts
  tmp_dir=$(mktemp -d)

  # Split file excluding header, use numeric suffixes with 2 digits
  tail -n +2 "$input_file" | split -l 2999 --numeric-suffixes=1 --suffix-length=2 --additional-suffix=.csv - "$tmp_dir/${base_name}_part_"

  # Add header to each split file
  for f in "$tmp_dir/${base_name}_part_"*.csv; do
    out_file="${f##*/}"  # Strip path
    echo "$header" > "$out_file"
    cat "$f" >> "$out_file"
  done

  # Clean up
  rm -r "$tmp_dir"
done