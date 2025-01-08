import os
import re
import matplotlib.pyplot as plt
import numpy as np
import argparse
import pandas as pd

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Process log files and generate a plot.")
parser.add_argument("log_path", type=str, help="Path to the folder containing log files.")
parser.add_argument(
    "-r", "--outlier-tolerance-offset-ratio", type=float, help="Outlier tolerance offset ratio (P%)."
)
parser.add_argument(
    "-w", "--window", type=int, default=0, help="Window size (W) for outlier detection. Default is 0 (no sliding window)."
)
args = parser.parse_args()

# Path to the folder containing log files
log_path = args.log_path
log_dir_path = os.path.dirname(log_path)
output_dir = os.path.join(log_dir_path, "link_setup_figures")
os.makedirs(output_dir, exist_ok=True)

proportion_threshold = args.outlier_tolerance_offset_ratio / 100.0 if args.outlier_tolerance_offset_ratio else None
window_size = args.window

# Regular expressions to extract values from logs
regex_patterns = {
    "total_time": r"total run time:\s+(\d+)",
}

# Data storage
data = {
    "x": [],  # XXX values
    "total_time": [],
}

# Process each log file
link_log_filepath = os.path.join(log_path)
with open(link_log_filepath, "r") as f:
    for i, line in enumerate(f):
        if line.startswith("Link"):
            elements = line.strip().split()
            t_ns_str = elements[2][:-2]
            t_ns = int(t_ns_str)
            data['x'].append(i + 1)
            data['total_time'].append(t_ns)

# Sort data by x (XXX values)
sorted_indices = np.argsort(data["x"])
for key in data.keys():
    data[key] = np.array(data[key])[sorted_indices]
    if key == "x":
        continue
    data[key] = data[key] / (10 ** 6)

# Function to remove outliers using sliding window and proportion threshold
def remove_outliers_with_window(x_values, y_values, proportion_threshold, window_size):
    if proportion_threshold is None:
        return x_values, y_values  # No outlier processing
    clean_x, clean_y = [], []
    n = len(y_values)
    for i in range(n):
        start_idx = max(0, i - window_size)
        end_idx = min(n, i + window_size + 1)
        window_avg = np.mean(y_values[start_idx:end_idx])
        if y_values[i] <= (1 + proportion_threshold) * window_avg:
            clean_x.append(x_values[i])
            clean_y.append(y_values[i])
    return np.array(clean_x), np.array(clean_y)

# Remove outliers if a proportion threshold is provided
if proportion_threshold is not None:
    data["x"], data["total_time"] = remove_outliers_with_window(data["x"], data["total_time"], proportion_threshold, window_size)
else:
    data["x"] = data["x"]

# Create two curves
sample_num = len(data["x"])
acc_setup_time = 0
data["acc_setup_time"] = np.copy(data["total_time"])
for i in range(sample_num):
    acc_setup_time += data["acc_setup_time"][i]
    data["acc_setup_time"][i] = acc_setup_time
data["linear"] = np.copy(data["total_time"])
sample_x = sample_num // 100
K = data["acc_setup_time"][sample_x] / sample_x
for i in range(sample_num):
    data["linear"][i] = K * i

# Output each curve's data to a separate CSV file
for curve_name in ["acc_setup_time"]:
    x_key = f"x"
    y_key = curve_name
    if proportion_threshold is not None:
        output_csv_path = os.path.join(output_dir, f"{curve_name}_outliers_removed_w{window_size}_r{int(args.outlier_tolerance_offset_ratio)}.csv")
    else:
        output_csv_path = os.path.join(output_dir, f"{curve_name}_original.csv")
    df = pd.DataFrame({x_key: data[x_key], y_key: data[y_key]})
    df.to_csv(output_csv_path, index=False)
    print(f"{curve_name} data saved to: {output_csv_path}")

# Plot the data
plt.figure(figsize=(10, 6))
plt.plot(data["x"], data["acc_setup_time"], label="accumulated node setup time")
plt.plot(data["x"], data["linear"], '--', label="linear time")

# Customize the plot
plt.xlabel("node i")
plt.ylabel("Time (ms)")
plt.title(f"Accumulated setup time per node")
plt.legend()
plt.grid(True)

# Save the figure
if proportion_threshold is not None:
    output_filename = f"link_acc_setup_time_outlier_w{window_size}_r{int(args.outlier_tolerance_offset_ratio)}.png"
else:
    output_filename = "link_acc_setup_time_original.png"
output_path = os.path.join(output_dir, output_filename)
plt.savefig(output_path)
plt.close()

print(f"Figure saved to: {output_path}")
