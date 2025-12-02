#!/usr/bin/env python3
"""
Sample Text Processor Script

This script demonstrates all the different argument types that the GUI launcher
can automatically detect and generate widgets for.

This is a fully functional script that processes text files with various options.
"""

import argparse
import sys
from pathlib import Path


def build_parser():
    """
    Build and return the argument parser.
    
    This function MUST be present in any script you want to use with the launcher.
    The GUI will call this function to discover what arguments the script accepts.
    """
    parser = argparse.ArgumentParser(
        description="A sample text processing utility demonstrating various argument types",
        epilog="Example: python sample_text_processor.py input.txt --output output.txt --uppercase --repeat 3"
    )
    
    # ===== POSITIONAL ARGUMENTS =====
    # These will appear as required text fields
    parser.add_argument(
        "input_file",
        help="Path to the input text file to process"
    )
    
    # ===== OPTIONAL FILE PATH ARGUMENTS =====
    # These will get file picker buttons
    parser.add_argument(
        "--output-file",
        "-o",
        help="Path to save the processed output (default: stdout)",
        default=None
    )
    
    # ===== BOOLEAN FLAGS =====
    # These will become checkboxes
    parser.add_argument(
        "--uppercase",
        "-u",
        action="store_true",
        help="Convert all text to uppercase"
    )
    
    parser.add_argument(
        "--lowercase",
        "-l",
        action="store_true",
        help="Convert all text to lowercase"
    )
    
    parser.add_argument(
        "--strip-whitespace",
        action="store_true",
        help="Remove leading and trailing whitespace from each line"
    )
    
    parser.add_argument(
        "--remove-empty-lines",
        action="store_true",
        help="Remove empty lines from the output"
    )
    
    # ===== CHOICE ARGUMENTS =====
    # These will become dropdown menus
    parser.add_argument(
        "--encoding",
        choices=["utf-8", "ascii", "latin-1", "utf-16"],
        default="utf-8",
        help="Character encoding for reading the file"
    )
    
    parser.add_argument(
        "--line-ending",
        choices=["unix", "windows", "mac"],
        default="unix",
        help="Line ending style for output"
    )
    
    # ===== NUMERIC ARGUMENTS =====
    # These will be text fields with numeric validation
    parser.add_argument(
        "--repeat",
        "-r",
        type=int,
        default=1,
        help="Number of times to repeat each line"
    )
    
    parser.add_argument(
        "--max-lines",
        type=int,
        help="Maximum number of lines to process (optional)"
    )
    
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=1.0,
        help="A sample float parameter (doesn't do anything in this script)"
    )
    
    # ===== TEXT ARGUMENTS =====
    # These will be simple text input fields
    parser.add_argument(
        "--prefix",
        "-p",
        default="",
        help="Text to add at the beginning of each line"
    )
    
    parser.add_argument(
        "--suffix",
        "-s",
        default="",
        help="Text to add at the end of each line"
    )
    
    parser.add_argument(
        "--find",
        help="Text to find (for use with --replace)"
    )
    
    parser.add_argument(
        "--replace",
        help="Text to replace --find with"
    )
    
    return parser


def process_line(line, args):
    """Process a single line according to the arguments"""
    # Strip whitespace if requested
    if args.strip_whitespace:
        line = line.strip()
    
    # Case conversion
    if args.uppercase:
        line = line.upper()
    elif args.lowercase:
        line = line.lower()
    
    # Find and replace
    if args.find and args.replace:
        line = line.replace(args.find, args.replace)
    
    # Add prefix and suffix
    line = args.prefix + line + args.suffix
    
    return line


def main():
    """Main execution function"""
    # Build parser and parse arguments
    parser = build_parser()
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_file}' does not exist", file=sys.stderr)
        return 1
    
    if not input_path.is_file():
        print(f"Error: '{args.input_file}' is not a file", file=sys.stderr)
        return 1
    
    # Read input file
    try:
        print(f"Reading file: {input_path}")
        print(f"Encoding: {args.encoding}")
        
        with open(input_path, 'r', encoding=args.encoding) as f:
            lines = f.readlines()
        
        print(f"Read {len(lines)} lines")
        
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1
    
    # Process lines
    print("Processing...")
    processed_lines = []
    
    for i, line in enumerate(lines):
        # Check max lines limit
        if args.max_lines and i >= args.max_lines:
            print(f"Stopped at {args.max_lines} lines (max-lines limit)")
            break
        
        # Remove newline for processing
        line = line.rstrip('\n\r')
        
        # Skip empty lines if requested
        if args.remove_empty_lines and not line.strip():
            continue
        
        # Process the line
        processed = process_line(line, args)
        
        # Repeat if requested
        for _ in range(args.repeat):
            processed_lines.append(processed)
    
    print(f"Processed {len(processed_lines)} output lines")
    
    # Determine line ending
    line_ending_map = {
        "unix": "\n",
        "windows": "\r\n",
        "mac": "\r"
    }
    line_ending = line_ending_map[args.line_ending]
    
    # Output
    output_text = line_ending.join(processed_lines) + line_ending
    
    if args.output_file:
        try:
            output_path = Path(args.output_file)
            with open(output_path, 'w', encoding=args.encoding) as f:
                f.write(output_text)
            print(f"✓ Output written to: {output_path}")
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            return 1
    else:
        print("\n" + "="*60)
        print("OUTPUT:")
        print("="*60)
        print(output_text)
    
    print("\n✓ Processing complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
