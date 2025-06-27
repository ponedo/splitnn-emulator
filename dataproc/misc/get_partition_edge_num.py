import os
import sys

if __name__ == "__main__":
    INPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else None
    # Record edge number for each subdirectory in the input directory
    edge_nums = []
    for subdir in os.listdir(INPUT_DIR):
        subdir_path = os.path.join(INPUT_DIR, subdir)
        if os.path.isdir(subdir_path):
            log_file = os.path.join(subdir_path, 'setup_log.txt')
            # Find the line with "edgeSum: "
            with open(log_file, 'r') as f:
                for line in f:
                    if "edgeSum: " in line:
                        # Extract the string after "edgeSum: "
                        # The string is a space-separated list of node names, wrapped with a pair of square brackets
                        edge_sum_str = line.split("edgeSum: ")[1].strip()
                        edge_sum = int(edge_sum_str)
                        # Print the number of nodes
                        # print(f"{subdir}: {edge_sum} edges")
                        edge_nums.append((subdir, edge_sum))
                        break
                else:
                    print(f"{subdir}: setup.log does not contain 'edgeSum: ' line")
        else:
            print(f"{subdir}: is not a directory")
    # Calclate the range and variance of edge numbers
    if edge_nums:
        edge_nums.sort(key=lambda x: x[1])
        min_edges = edge_nums[0][1]
        max_edges = edge_nums[-1][1]
        avg_edges = sum(edge_num for _, edge_num in edge_nums) / len(edge_nums)
        variance = sum((edge_num - avg_edges) ** 2 for _, edge_num in edge_nums) / len(edge_nums)
        # print(f"Average: {avg_edges:.2f}")
        print(f"Range: {min_edges} - {max_edges}")
        print(f"Variance: {variance:.2f}")
    else:
        print("No edge numbers found.")
        print("Average: N/A")
        print("Range: N/A")
        print(f"Variance: N/A")
