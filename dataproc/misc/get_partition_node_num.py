import os
import sys

if __name__ == "__main__":
    INPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else None
    for subdir in os.listdir(INPUT_DIR):
        subdir_path = os.path.join(INPUT_DIR, subdir)
        if os.path.isdir(subdir_path):
            log_file = os.path.join(subdir_path, 'setup_log.txt')
            # Find the line with "Node Order: "
            with open(log_file, 'r') as f:
                for line in f:
                    if "Node Order: " in line:
                        # Extract the string after "Node Order: "
                        # The string is a space-separated list of node names, wrapped with a pair of square brackets
                        node_order_str = line.split("Node Order: ")[1].strip()
                        # Remove the square brackets
                        node_order_str = node_order_str[1:-1]
                        # Split the string into a list of node names
                        node_order = node_order_str.split()
                        # Print the number of nodes
                        print(f"{subdir}: {len(node_order)} nodes")
                        break
                else:
                    print(f"{subdir}: setup.log does not contain 'Node Order: ' line")
        else:
            print(f"{subdir}: is not a directory")
                        