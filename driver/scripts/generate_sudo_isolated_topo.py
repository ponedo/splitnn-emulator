import sys
import argparse

def generate_sudo_isolated(n, l, filepath):
    nodes = []
    edges = []

    # Generate nodes in the grid
    for i in range(n):
        nodes.append(i+1)

    # Generate edges within the grid, considering marginal cases where x or y might be 1
    for i in range(l):
        edges.append((1, 2))

    # Write nodes and edges to the output file
    with open(filepath, 'w') as f:
        # Write nodes
        f.write(' '.join(map(str, nodes)) + '\n')
        # Write edges
        for edge in edges:
            f.write(f"{edge[0]} {edge[1]}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A script to generate positions and events')
    parser.add_argument('n', type=int, help='# of nodes')
    parser.add_argument('l', type=int, help='# of links between first two nodes')
    parser.add_argument('filepath', type=str, help='Output file name')
    args = parser.parse_args()

    if len(sys.argv) != 4:
        print("Usage: python generate_sudo_isolated.py <n> <l> <output_filepath>")
        sys.exit(1)

    n = args.n
    l = args.l
    filepath = args.filepath

    if n < 2:
        print("n >= 2 should be satisfied")
        sys.exit(1)

    generate_sudo_isolated(n, l, filepath)
    print(f"Pseudo isolated topology with {n} nodes and {l} links generated in {filepath}.")
