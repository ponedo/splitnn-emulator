import os
import re
import sys
import csv
import argparse
import pandas as pd

parser = argparse.ArgumentParser(description='Alter VM time in log.')
parser.add_argument(
    '-i', '--input-dir', type=str, required=True, help='Directory of logs')
parser.add_argument(
    '-o', '--output-dir', type=str, required=True, help='Directory of the output .csv file')
args = parser.parse_args()

if not os.path.exists(args.input_dir):
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

def get_log_topo_and_times(log_path):
    with open(log_path, 'r') as f:
        file_content = f.read()
    topo_found = re.findall(r"New test! Options: \{'t': (\[.+\])", file_content)
    vm_start_found = re.findall(r"VM starting consumes (\d+\.\d+)s", file_content)
    vm_destroy_found = re.findall(r"VM destroying consumes (\d+\.\d+)s", file_content)
    setup_found = re.findall(r"Setup done, time: (\d+\.\d+)s", file_content)
    topos = ['_'.join(eval(topo_args)) for topo_args in topo_found]
    vm_start_times = [round(float(vm_start_time), 2) for vm_start_time in vm_start_found]
    vm_destroy_times = [round(float(vm_destroy_time), 2) for vm_destroy_time in vm_destroy_found]
    setup_times = [round(float(setup_time), 2) for setup_time in setup_found]
    return topos, vm_start_times, vm_destroy_times, setup_times

def read_all_logs(argstr2logpath):
    arg_str_keys = argstr2logpath.keys()
    log_info = []
    for arg_str in arg_str_keys:
        print(arg_str)
        args = argstr2dict(arg_str)
        log_filepath = argstr2logpath[arg_str]
        for topo, vm_start_time, vm_destroy_time, setup_time in zip(*get_log_topo_and_times(log_filepath)):
            log_info.append({
                "pm": args['pm'],
                "n": args['n'],
                "m": args['m'],
                "k": args['k'],
                "topo": topo,
                "vm_start_time": vm_start_time,
                "vm_destroy_time": vm_destroy_time,
                "setup_time": setup_time,
            })
    return log_info

def read_gain(vm_alloc_filepath, arg_str):
    args = argstr2dict(arg_str)
    n = args['n']
    m = args['m']
    assert not (n == 0 and m > 0)
    df = pd.read_csv(vm_alloc_filepath)
    if n == 0 and m == 0:
        gain = df.loc[0, "Gain"]
    elif n > 0 and m == 0:
        gain = df[df['n'] == n]['Gain'].iloc[0]
    elif n > 0 and m > 0:
        gain = df[(df['n'] == n) & (df['m'] == m)]['Gain'].iloc[0]
    return gain

def read_vminfo_topo(topo_dirpath, arg_str):
    # Read memory usage
    mem_filepath = os.path.join(
        topo_dirpath, "pm_mem_usage.txt"
    )
    with open(mem_filepath, 'r') as f:
        file_content = f.read()
    mem_found = re.findall(r"Total Exp Memory \(KB\): (\d+)", file_content)
    mem_usage = round(int(mem_found[0]) / 1000000, 2)

    # Read the modeled gain
    gain_filepath = os.path.join(
        topo_dirpath, "vm_alloc_result", "pm_0.csv")
    gain = read_gain(gain_filepath, arg_str)

    return gain, mem_usage

def read_vminfo(argstr2dirpath):
    arg_str_keys = argstr2dirpath.keys()
    vm_info = []
    for arg_str in arg_str_keys:
        args = argstr2dict(arg_str)
        test_dirpath = argstr2dirpath[arg_str]
        for topo_dirname in os.listdir(test_dirpath):
            if not os.path.isdir(os.path.join(test_dirpath, topo_dirname)):
                continue
            topo_dir_args = topodir2dict(topo_dirname)
            topo = topo_dir_args['t']
            topo_dirpath = os.path.join(test_dirpath, topo_dirname)
            gain, mem_usage = read_vminfo_topo(topo_dirpath, arg_str)
            vm_info.append({
                "pm": args['pm'],
                "n": args['n'],
                "m": args['m'],
                "k": args['k'],
                "topo": topo,
                "gain": gain,
                "mem_usage": mem_usage,
            })
    return vm_info

def output_results(argstr2times, output_dir):
    output_filepath = os.path.join(output_dir, "time_results.csv")
    argstr2results_list = list(argstr2times.items())
    argstr2results_list.sort(
        key=lambda x: (
            x[1][0], # topo
            argstr2dict(x[0])['pm'], # PM num
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
    argstr2dirpath, argstr2logpath = get_index(args.input_dir)
    vm_info = read_vminfo(argstr2dirpath)
    log_info = read_all_logs(argstr2logpath)

    df_vm = pd.DataFrame(vm_info)
    df_log = pd.DataFrame(log_info)

    # Merge the two DataFrames on common keys: "pm", "n", "m", "k", "topo"
    df_merged = pd.merge(df_vm, df_log, on=["pm", "n", "m", "k", "topo"], how="inner")

    # Sort or rearrange columns
    df_merged = df_merged.sort_values(by=["topo", "k", "pm", "n", "m"])
    df_merged = df_merged[["pm", "n", "m", "k", "topo", "gain", "mem_usage", "vm_start_time", "vm_destroy_time", "setup_time"]]

    # Save to CSV
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "mvm_results.csv")
    df_merged.to_csv(output_path, index=False)

    print(f"Data written to: {output_path}")