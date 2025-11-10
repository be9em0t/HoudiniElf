#!/usr/bin/env python3
"""
CSV Splitter/Combiner Script
Splits large CSV files into smaller chunks or combines multiple CSV files into one.
"""

import argparse
import os
from pathlib import Path


def split_csv(file_path, lines_per_file=3000):
    """Split a CSV file into multiple files with specified number of lines."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"Error: File '{file_path}' not found.")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        header = f.readline()
        
        if not header:
            print("Error: File is empty.")
            return
        
        file_count = 1
        line_count = 0
        output_file = None
        
        for line in f:
            if line_count == 0:
                # Create new output file
                base_name = file_path.stem
                extension = file_path.suffix
                output_path = file_path.parent / f"{base_name}_part_{file_count:04d}{extension}"
                output_file = open(output_path, 'w', encoding='utf-8')
                output_file.write(header)
                print(f"Creating: {output_path.name}")
            
            output_file.write(line)
            line_count += 1
            
            if line_count >= lines_per_file:
                output_file.close()
                line_count = 0
                file_count += 1
        
        if output_file and not output_file.closed:
            output_file.close()
        
        print(f"Split complete: Created {file_count} file(s)")


def combine_csv(directory):
    """Combine all CSV files in a directory into one file."""
    dir_path = Path(directory)
    
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"Error: Directory '{directory}' not found.")
        return
    
    csv_files = sorted(dir_path.glob('*.csv'))
    
    if not csv_files:
        print(f"No CSV files found in '{directory}'")
        return
    
    output_path = dir_path / "combined_output.csv"
    header_written = False
    total_lines = 0
    
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for csv_file in csv_files:
            print(f"Processing: {csv_file.name}")
            with open(csv_file, 'r', encoding='utf-8') as infile:
                header = infile.readline()
                
                if not header_written:
                    outfile.write(header)
                    header_written = True
                
                for line in infile:
                    outfile.write(line)
                    total_lines += 1
    
    print(f"Combine complete: {len(csv_files)} file(s) merged into '{output_path.name}'")
    print(f"Total lines written (excluding header): {total_lines}")


def main():
    parser = argparse.ArgumentParser(
        description="Split or combine CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Split a CSV file into chunks of 3000 lines each:
    %(prog)s split --file input.csv --lines 3000
  
  Split using default line count:
    %(prog)s split --file input.csv
  
  Combine all CSV files in a directory:
    %(prog)s combine --dir /path/to/csv/files
        """
    )
    
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode', required=True)
    
    # Split mode
    split_parser = subparsers.add_parser(
        'split', 
        help='Split a CSV file into multiple files',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    split_parser.add_argument('--file', required=True, help='CSV file to split')
    split_parser.add_argument('--lines', type=int, default=3000, help='Lines per file (default: 3000)')
    
    # Combine mode
    combine_parser = subparsers.add_parser(
        'combine', 
        help='Combine CSV files from a directory',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    combine_parser.add_argument('--dir', required=True, help='Directory containing CSV files to combine')
    
    args = parser.parse_args()
    
    if args.mode == 'split':
        split_csv(args.file, args.lines)
    elif args.mode == 'combine':
        combine_csv(args.dir)


if __name__ == '__main__':
    main()