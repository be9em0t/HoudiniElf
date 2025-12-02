#!/usr/bin/env python3
import argparse
import csv
import sys
import os
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the argument parser.

    This is required by the launcher GUI.
    """
    parser = argparse.ArgumentParser(
        description="Add sequential primary key numbers to a specified column in a CSV file"
    )

    parser.add_argument("-f", "--file", help="Path to the input CSV file")
    # Use a custom action to mark this as needing dynamic choices without enforcing them
    parser.add_argument("-c", "--column", metavar="COLUMN", help="Name of the column to add primary key numbers to")
    parser.add_argument("-o", "--output", help="Output CSV file path")
    parser.add_argument("--start", type=int, default=1, help="Starting number for primary keys")

    # Store a hint for the GUI that column should be a dropdown
    if hasattr(parser, '_column_is_dynamic'):
        parser._column_is_dynamic = True
    else:
        # Add as a custom attribute
        for action in parser._actions:
            if action.dest == 'column':
                action.is_dynamic_choices = True
                break

    return parser


def read_csv_header(path: str):
    """Read only the first chunk of the CSV to detect delimiter and header fields."""
    with open(path, 'r', encoding='utf-8', newline='') as infile:
        sample = infile.read(4096)
        infile.seek(0)
        sniffer = csv.Sniffer()
        try:
            delimiter = sniffer.sniff(sample, delimiters=',;\t').delimiter
        except Exception:
            delimiter = '\t'  # Default to tab for TSV files
        
        # Read first line for header
        reader = csv.reader(infile, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
        try:
            header = next(reader)
            header = [h.strip() for h in header]
        except Exception:
            # Fallback: split first line manually
            infile.seek(0)
            first_line = infile.readline()
            header = [h.strip() for h in first_line.split(delimiter)]
        
        return delimiter, header


def add_primary_key(input_file: str, column_name: str, output_file: str, start: int = 1) -> int:
    """Add sequential primary key numbers into the specified column and write to output."""
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File '{input_file}' does not exist.")
        return 1

    # Detect delimiter
    with open(input_file, 'r', encoding='utf-8', newline='') as infile:
        sample = infile.read(4096)
        sniffer = csv.Sniffer()
        try:
            delimiter = sniffer.sniff(sample, delimiters=',;\t').delimiter
        except Exception:
            delimiter = '\t'  # Default to tab for TSV files

    # Read line by line to handle malformed rows
    with open(input_file, 'r', encoding='utf-8', newline='') as infile:
        lines = infile.readlines()
    
    if not lines:
        print("Error: File is empty.")
        return 1
    
    # Parse header
    header_line = lines[0].rstrip('\n\r')
    fieldnames = [h.strip().strip('"') for h in header_line.split(delimiter)]
    
    if column_name not in fieldnames:
        print(f"Error: Column '{column_name}' does not exist in the CSV file.")
        print(f"Available columns: {', '.join(fieldnames)}")
        return 1
    
    column_index = fieldnames.index(column_name)
    
    # Process data rows
    output_lines = [header_line + '\n']
    pk_counter = start
    skipped = 0
    
    for line_num, line in enumerate(lines[1:], start=2):
        line = line.rstrip('\n\r')
        if not line.strip():
            continue  # Skip empty lines
        
        # Split by delimiter
        fields = line.split(delimiter)
        
        # Ensure we have enough fields
        while len(fields) < len(fieldnames):
            fields.append('')
        
        # Set the primary key
        fields[column_index] = str(pk_counter)
        
        # Reconstruct line
        output_line = delimiter.join(fields) + '\n'
        output_lines.append(output_line)
        pk_counter += 1

    # Ensure output folder exists
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        outfile.writelines(output_lines)

    rows_processed = pk_counter - start
    print(f"Successfully added primary keys to '{output_file}'")
    print(f"Processed {rows_processed} rows (numbered from {start} to {pk_counter - 1})")
    if skipped > 0:
        print(f"Skipped {skipped} empty lines")
    return 0


def run_cli(args: argparse.Namespace) -> int:
    """Run using command-line args."""
    input_file = args.file
    column = args.column
    output = args.output
    start = args.start

    if not input_file:
        print("Error: --file is required when running from CLI.")
        return 1

    if not output:
        base, ext = os.path.splitext(input_file)
        output = f"{base}_numbered{ext}"

    if not column:
        # Try to auto-detect and prompt
        _, headers = read_csv_header(input_file)
        print("Columns:")
        for i, h in enumerate(headers):
            print(f"{i}: {h}")
        sel = input("Select column by name or index: ")
        if sel.isdigit():
            column = headers[int(sel)]
        else:
            column = sel

    return add_primary_key(input_file, column, output, start)


def main():
    parser = build_parser()
    args = parser.parse_args()

    # If file argument provided, assume CLI mode
    if args.file:
        return_code = run_cli(args)
        sys.exit(return_code)

    # Otherwise, the launcher GUI will call build_parser and populate fields


def run_gui():
    """Run a small PyQt6 GUI to pick file, select column, and choose output."""
    try:
        from PyQt6.QtWidgets import (
            QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
            QLineEdit, QPushButton, QFileDialog, QComboBox, QSpinBox, QTextEdit
        )
        from PyQt6.QtCore import Qt
    except Exception as e:
        print("PyQt6 not available — please install PyQt6 or run from the launcher.")
        return 1

    app = QApplication(sys.argv)

    w = QWidget()
    w.setWindowTitle("Add Primary Key — GUI")
    layout = QVBoxLayout(w)

    info = QLabel("Select a CSV file, choose a column to fill with sequential primary keys.")
    info.setWordWrap(True)
    layout.addWidget(info)

    # Input file picker
    in_layout = QHBoxLayout()
    in_edit = QLineEdit()
    in_btn = QPushButton("Browse...")
    in_layout.addWidget(QLabel("Input CSV:"))
    in_layout.addWidget(in_edit)
    in_layout.addWidget(in_btn)
    layout.addLayout(in_layout)

    # Column selector
    col_layout = QHBoxLayout()
    col_combo = QComboBox()
    col_layout.addWidget(QLabel("Column:"))
    col_layout.addWidget(col_combo)
    layout.addLayout(col_layout)

    # Output file
    out_layout = QHBoxLayout()
    out_edit = QLineEdit()
    out_btn = QPushButton("Browse...")
    out_layout.addWidget(QLabel("Output CSV:"))
    out_layout.addWidget(out_edit)
    out_layout.addWidget(out_btn)
    layout.addLayout(out_layout)

    # Start number
    start_layout = QHBoxLayout()
    start_spin = QSpinBox()
    start_spin.setMinimum(0)
    start_spin.setValue(1)
    start_layout.addWidget(QLabel("Start number:"))
    start_layout.addWidget(start_spin)
    layout.addLayout(start_layout)

    # Run and log
    run_btn = QPushButton("Run")
    run_btn.setEnabled(False)
    log = QTextEdit()
    log.setReadOnly(True)
    layout.addWidget(run_btn)
    layout.addWidget(log)

    def set_log(msg: str):
        log.append(msg)

    def on_pick_input():
        path, _ = QFileDialog.getOpenFileName(w, "Select CSV file", filter="CSV Files (*.csv);;All Files (*)")
        if path:
            in_edit.setText(path)
            try:
                delim, headers = read_csv_header(path)
                col_combo.clear()
                col_combo.addItems(headers)
                # Autofill output
                base, ext = os.path.splitext(path)
                out_edit.setText(f"{base}_numbered{ext}")
                set_log(f"Detected delimiter: '{delim}' — {len(headers)} columns\n")
                run_btn.setEnabled(True if headers else False)
            except Exception as e:
                set_log(f"Failed to read header: {e}")
                run_btn.setEnabled(False)

    def on_pick_output():
        path, _ = QFileDialog.getSaveFileName(w, "Select output CSV", filter="CSV Files (*.csv);;All Files (*)")
        if path:
            out_edit.setText(path)

    def on_run():
        input_path = in_edit.text().strip()
        column = col_combo.currentText().strip()
        output_path = out_edit.text().strip()
        start = start_spin.value()
        if not input_path or not column or not output_path:
            set_log("Please fill input file, column and output file.")
            return
        set_log(f"Running: input={input_path}, column={column}, output={output_path}, start={start}")
        try:
            rc = add_primary_key(input_path, column, output_path, start)
            if rc == 0:
                set_log("Completed successfully.")
            else:
                set_log(f"Finished with errors (rc={rc}).")
        except Exception as e:
            set_log(f"Error: {e}")

    in_btn.clicked.connect(on_pick_input)
    out_btn.clicked.connect(on_pick_output)
    run_btn.clicked.connect(on_run)

    w.resize(700, 400)
    w.show()
    app.exec()
    return 0


if __name__ == '__main__':
    main()
