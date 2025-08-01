import argparse
import os
import csv
import re

parser = argparse.ArgumentParser(description='Alter VM time in log.')
parser.add_argument(
    '-i', '--input-filepath', type=str, required=True, help='Path of the input file')
parser.add_argument(
    '-o', '--output-dir', type=str, required=True, help='Directory of the output .csv file')
args = parser.parse_args()

if __name__ == "__main__":
    with open(args.input_filepath, 'r') as f:
        file_content = f.read()
        
        # Regular expression to match lines with sample data
        pattern = re.compile(
            r'\[Sample\s+(\d+)\s+BBNSes\]\s+Time:\s*([\d.]+)s,\s*Memory Increased:\s*([\d.]+)MB'
        )

        samples = []
        for line in file_content.splitlines():
            match = pattern.search(line)
            if match:
                num_bbns = int(match.group(1))
                time_cost = float(match.group(2))
                memory = float(match.group(3))
                samples.append([num_bbns, time_cost, memory])

        output_filename = "bbns_measure.csv"
        output_path = os.path.join(args.output_dir, output_filename)

        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['BBNSes', 'Time-cost', 'Memory'])
            writer.writerows(samples)