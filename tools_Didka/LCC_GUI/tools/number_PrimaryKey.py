#!/usr/bin/env python3
import argparse
import csv
import sys
import os

def main():
    parser = argparse.ArgumentParser(description='Add sequential primary key numbers to a specified column in a CSV file.')
    parser.add_argument('-f', '--file', required=True, help='Path to the input CSV file')
    parser.add_argument('-c', '--column', required=True, help='Name of the column to add primary key numbers to')
    
    args = parser.parse_args()
    
    input_file = args.file
    column_name = args.column
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' does not exist.")
        sys.exit(1)
    
    # Determine output file name
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_numbered{ext}"
    
    try:
        with open(input_file, 'r', encoding='utf-8', newline='') as infile:
            sample = infile.read(1024)
            infile.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample, delimiters=',;\t').delimiter
            
            reader = csv.DictReader(infile, delimiter=delimiter)
            fieldnames = reader.fieldnames
            
            if column_name not in fieldnames:
                print(f"Error: Column '{column_name}' does not exist in the CSV file.")
                sys.exit(1)
            
            # Prepare data with new column
            rows = []
            pk_counter = 1
            for row in reader:
                row[column_name] = str(pk_counter)
                rows.append(row)
                pk_counter += 1
            
            # Write to output file
            with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(rows)
        
        print(f"Successfully added primary keys to '{output_file}'")
    
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
