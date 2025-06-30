import csv
import re
import sys

# Read E_max.txt and generate a CSV file
if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <input_file> <output_file>")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

with open(input_file, "r") as f:
    lines = f.readlines()

header = ["n", "grid E_max(n)", "clos E_max(n)", "as E_max(n)", "average E_max(n)"]
n_values = []
grid = []
clos = []
as_ = []
avg = []

results_section = False

def convert_line_to_list(line, prefix):
    """Convert a line of space-separated values to a list of floats."""
    # Strip the prefix
    line = line.replace(prefix, "").strip()
    # Evaluate the line to convert it to a list of floats
    rtr_list = eval(line)
    # Keep only 2 decimal places, but keep the integers as are
    if isinstance(rtr_list, list):
        # Convert each element to float and round to 2 decimal places
        rtr_list = [round(float(x), 2) if isinstance(x, float) else x for x in rtr_list]
    # Ensure the list is of type float
    return rtr_list

for idx, line in enumerate(lines):
    if line.startswith("Node range:"):
        n_values = convert_line_to_list(line, "Node range:")
        continue
    if "Results averaged across runs:" in line:
        results_section = True
        data_lines = []
        # Collect the next 3 lines (grid, clos, as)
        for i in range(3):
            if idx + 1 + i < len(lines):
                data_lines.append(lines[idx + 1 + i].strip())
        if len(data_lines) == 3:
            grid = convert_line_to_list(data_lines[0], "grid: ")
            clos = convert_line_to_list(data_lines[1], "clos: ")
            as_ = convert_line_to_list(data_lines[2], "as: ")
    elif "Results averaged across runs and topos: " in line:
        avg = convert_line_to_list(line, "Results averaged across runs and topos: ")

# Transpose columns to rows for CSV
data = []
for i in range(len(n_values)):
    row = [
        n_values[i],
        grid[i] if i < len(grid) else "",
        clos[i] if i < len(clos) else "",
        as_[i] if i < len(as_) else "",
        avg[i] if i < len(avg) else "",
    ]
    data.append(row)

with open(output_file, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(header)
    writer.writerows(data)