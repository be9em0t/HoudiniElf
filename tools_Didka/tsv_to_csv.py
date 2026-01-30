import csv

# Input TSV file
tsv_file = 'ENG_to_CHI clean source.tsv'
# Output CSV file
csv_file = 'ENG_to_CHI clean source.csv'

# Open TSV file for reading and CSV file for writing
with open(tsv_file, 'r') as tsv, open(csv_file, 'w', newline='') as csv_out:
    tsv_reader = csv.reader(tsv, delimiter='\t')
    csv_writer = csv.writer(csv_out)
    
    # Write rows from TSV to CSV
    for row in tsv_reader:
        csv_writer.writerow(row)

print(f"Converted {tsv_file} to {csv_file}")
