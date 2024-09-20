import os
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A script to process results')
    parser.add_argument('-d', '--input-dir', type=str, required=False, default="results", help='Input directory name')
    args = parser.parse_args()

    results_dir = args.input_dir

    for filename in os.listdir(results_dir):
        pass
