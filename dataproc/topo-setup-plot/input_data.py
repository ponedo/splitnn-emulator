import os
import re
import pandas as pd
from topo_info import *
from copy import deepcopy

# Regular expressions to extract values from logs
regex_patterns = {
    "node_setup_time": r"Node setup time:\s+(\d+)", # s
    "link_setup_time": r"Link setup time:\s+(\d+)", # s
    "setup_time": r"Network operation time:\s+(\d+)", # s
    "clean_time": r"Clean link time:\s+(\d+)", # ms
}

def parse_test_opts(test_dirname, valid_options):
    opts = {}
    splited_dirname = test_dirname.strip().split("--")
    k, v = None, None
    for i, ele in enumerate(splited_dirname):
        if i % 2 == 0:
            k = ele
            if k not in valid_options:
                print(f"Wrong option \"{k}\" in result dir name: {test_dirname}")
        else:
            v = ele
            if k == "b":
                v = int(v)
            opts[k] = v
    return opts


def get_one_test_topo_info(opts):
    topo_name = opts['t']
    splited_topo_value = topo_name.strip().split()
    topo_type = splited_topo_value[0]
    topo_args = splited_topo_value[1:]
    topo_info = {
        "node_num": topo_funcs[topo_type]["get_node_num"](topo_args),
        "link_num": topo_funcs[topo_type]["get_link_num"](topo_args),
        "t": topo_type,
        "topo_name": topo_name,
    }
    return topo_info


def get_setup_time(log_dirpath):
    log_filepath = os.path.join(log_dirpath, "setup_log.txt")
    with open(log_filepath, 'r') as file:
        log_content = file.read()
        node_setup_time = int(re.search(regex_patterns["node_setup_time"], log_content).group(1))
        link_setup_time = int(re.search(regex_patterns["link_setup_time"], log_content).group(1))
        setup_time = int(re.search(regex_patterns["setup_time"], log_content).group(1))
    return node_setup_time, link_setup_time, setup_time


def get_clean_time(log_dirpath):
    log_filepath = os.path.join(log_dirpath, "clean_log.txt")
    with open(log_filepath, 'r') as file:
        log_content = file.read()
        clean_time = int(re.search(regex_patterns["clean_time"], log_content).group(1))
    clean_time /= 1000 # convert millisecond to second
    return clean_time


def get_one_test_results(test_dirpath):
    results = {
        'node_setup_time': 0,
        'link_setup_time': 0,
        'setup_time': 0,
        'clean_time': 0,
    }
    for server_dirname in os.listdir(test_dirpath):
        node_setup_time, link_setup_time, setup_time = get_setup_time(
            os.path.join(test_dirpath, server_dirname)
        )
        clean_time = get_clean_time(
            os.path.join(test_dirpath, server_dirname)
        )
        results["node_setup_time"] = \
            max(results["node_setup_time"], node_setup_time)
        results["link_setup_time"] = \
            max(results["link_setup_time"], link_setup_time)
        results["setup_time"] = \
            max(results["setup_time"], setup_time)
        results["clean_time"] = \
            max(results["clean_time"], clean_time)
    return results


def get_one_test_topo_info_and_results(
        test_dirpath, opts, y_value_types):
    topo_and_results = {}

    # Get topo info
    topo_info = get_one_test_topo_info(opts)
    topo_and_results.update(topo_info)

    # Get results
    test_results = get_one_test_results(test_dirpath)
    topo_and_results.update(test_results, y_value_types)

    return topo_and_results


def get_all_data(test_results_dir, valid_options, x_value_types, y_value_types):
    columns = valid_options + x_value_types + y_value_types
    all_data_df = pd.DataFrame(columns=columns)

    # Scan test_results_dir
    test_dirnames = os.listdir(test_results_dir)
    for test_dirname in test_dirnames:
        opts = parse_test_opts(test_dirname, valid_options)
        row = deepcopy(opts)
        topo_and_results = get_one_test_topo_info_and_results(
            os.path.join(test_results_dir, test_dirname), opts, y_value_types)
        row.update(topo_and_results)
        all_data_df = all_data_df.append(row, ignore_index=True)

    return all_data_df
    