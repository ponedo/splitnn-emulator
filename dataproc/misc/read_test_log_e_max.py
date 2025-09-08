import os
import re
import sys
import csv
import argparse
import pandas as pd

parser = argparse.ArgumentParser(description='Alter VM time in log.')
parser.add_argument(
    '-i', '--log-path', type=str, required=True, help='Filepath of the log')
parser.add_argument(
    '-o', '--output-dir', type=str, required=True, help='Directory of the output .csv file')
args = parser.parse_args()

if not os.path.exists(args.log_path):
    print(f"Input dir doesn't exist!")
    exit(1)
if not os.path.exists(args.output_dir):
    print(f"New dir doesn't exist!")
    exit(1)

def argstr2dict(argstr):
    rtr = {}
    argstr = argstr.strip()
    splited_str = argstr.split('--')
    for str_part in splited_str:
        try:
            k, v = str_part.split('-')
            rtr[k] = int(v)
        except ValueError:
            break
    return rtr

def topodir2dict(topo_dirname):
    rtr = {}
    topo_dirname = topo_dirname.strip()
    splited_str = topo_dirname.split('--')
    k, v = None, None
    for i, str_part in enumerate(splited_str):
        if i % 2 == 0:
            k = str_part
        else:
            v = str_part
            rtr[k] = v
    return rtr

def get_index(input_dir):
    argstr2dirpath = {}
    argstr2logpath = {}
    test_dirnames = os.listdir(input_dir)
    test_dirnames.sort(key=lambda x: (argstr2dict(x)['n'], argstr2dict(x)['m']))
    for test_dirname in test_dirnames:
        print(test_dirname)
        match = re.search(r"pm-\d+--n-\d+--m-\d+--k-\d+", test_dirname)
        test_args_str = match.group(0)
        test_dirpath = os.path.join(input_dir, test_dirname)
        argstr2dirpath[test_args_str] = test_dirpath
        test_log_filepath = os.path.join(test_dirpath, "test_log.txt")
        argstr2logpath[test_args_str] = test_log_filepath
    return argstr2dirpath, argstr2logpath

def get_log_topo_and_emaxs(log_path):
    with open(log_path, 'r') as f:
        file_content = f.read()

    topo_found = re.findall(r"New test! Options: \{'t': (\[.+\])", file_content)
    emax_found = re.findall(r"E_max data for pm #\d+: (.+)", file_content)

    topos = ['_'.join(eval(topo_args)) for topo_args in topo_found]
    emax_dicts = [eval(emax_dict_str) for emax_dict_str in emax_found]

    log_info = []
    for topo, emax_dict in zip(topos, emax_dicts):
        for n, emax_n in emax_dict.items():
            log_info.append({
                "topo": topo,
                "n": n,
                "E_max(n)": emax_n,
            })

    return log_info

def output_results(argstr2times, output_dir):
    output_filepath = os.path.join(output_dir, "time_results.csv")
    argstr2results_list = list(argstr2times.items())
    argstr2results_list.sort(
        key=lambda x: (
            x[1][0], # topo
            argstr2dict(x[0])['n'], # VM num
            argstr2dict(x[0])['m'], # m
        ))
    with open(output_filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        header = list(argstr2dict(argstr2results_list[0][0]).keys())
        header.extend([
            "topo", "vm_start_time", "vm_destroy_time", "setup_time"
        ])
        writer.writerow(header)
        for argstr, results in argstr2results_list:
            args = list(argstr2dict(argstr).values())
            args = [int(e) for e in args]
            times = [round(e, 2) for e in results]
            row = args + times
            writer.writerow(row)

if __name__ == "__main__":
    log_info = get_log_topo_and_emaxs(args.log_path)

    df = pd.DataFrame(log_info)

    # Sort or rearrange columns
    df = df.sort_values(by=["topo", "n"])
    df = df[["topo", "n", "E_max(n)"]]

    # Save to CSV
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "emax_results.csv")
    df.to_csv(output_path, index=False)

    print(f"Data written to: {output_path}")