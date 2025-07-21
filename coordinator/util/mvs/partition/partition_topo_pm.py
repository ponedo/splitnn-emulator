import os
import metis
import shutil
import argparse
import subprocess
from .fmt_convert import *


# TBS partitioning need to be downloaded from https://github.com/tbs2022/tbs. Please change this path to the "build" directory compiled out from that project.
TBS_BIN_DIR = "/home/cnic/open-src/tbs/build"
TBS_BIN_PATH = os.path.join(TBS_BIN_DIR, "tbs")


def run_tbs(full_graph_metis_filepath, pm_num, cpu_capacity):
    generate_topology_cmd = [
        TBS_BIN_PATH, full_graph_metis_filepath,
        f"--k={pm_num}",
        f"--cpu_capacity={cpu_capacity}",
        "--preconfiguration=esocial"
    ]
    print(f"Running TBS partitioning with command: {' '.join(generate_topology_cmd)}")
    original_dir = os.getcwd()
    os.chdir(TBS_BIN_DIR)
    try:
        stderr_output = []
        with subprocess.Popen(generate_topology_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
            # for line in proc.stdout:
            #     print(line, end='')
            for line in proc.stderr:
                stderr_output.append(line)
            #     print(line, end='')
            proc.wait()
    finally:
        os.chdir(original_dir)
    # If returncode is 0, but stderr is non-empty and contains 'Traceback', treat as error, and exit the program
    # print(f"proc.returncode: {proc.returncode}")
    # if any("Traceback" in line for line in stderr_output):
    if proc.returncode != 0 or any("Traceback" in line for line in stderr_output):
        print("Error occurred while running TBS partitioning:")
        for line in stderr_output:
            print(line, end='')
        return False
    return True


def trial_cpu_capacity_factors():
    init_factors =  [1.05, 1.04, 1.03, 1.02, 1.01]
    init_factors_len = len(init_factors)
    init_factor_i = 0
    inc_factor = 1.1
    last_yield = "inc"
    while True:
        if init_factor_i < init_factors_len and last_yield == "inc":
            yield init_factors[init_factor_i]
            init_factor_i += 1
            last_yield = "init"
        else:
            yield inc_factor
            inc_factor += 0.05
            last_yield = "inc"


def partition_graph_across_pm(
    nodes, adjacency_list, pm_config_list, input_topo_filepath):
    """Partitions the graph across multiple physical machines with TBS according to config."""

    # Scan IDs of physical machines
    distinct_pm_ids = set()
    for pm_id, _ in enumerate(pm_config_list):
        distinct_pm_ids.add(pm_id)

    # If the number of PMs is 1, return the original topology
    if len(distinct_pm_ids) == 1:
        print("Only one PM is available. No partitioning needed.")
        pmid = list(distinct_pm_ids)[0]
        node2pmid = {}
        for node in nodes:
            node2pmid[node] = pmid
        pmid2nodes = {pmid: nodes}
        pmid2adjacencylist = {pmid: adjacency_list}
        return node2pmid, pmid2nodes, pmid2adjacencylist

    # Convert the topology file into metis graph format
    topo_file_dir = os.path.dirname(input_topo_filepath)
    topo_filename = os.path.basename(input_topo_filepath)
    topo_filename_elements = topo_filename.split('.')
    full_graph_metis_filename = '.'.join(topo_filename_elements[:-1]) + ".graph"
    full_graph_metis_filepath = os.path.join(topo_file_dir, full_graph_metis_filename)
    node_ids, nodeid2name, adj_matrix, edge_num = \
        convert_adjlist_to_metis_graph(nodes, adjacency_list, full_graph_metis_filepath)
    node_num = len(node_ids)

    # Call TBS partitioning program
    pm_num = len(distinct_pm_ids)
    node_num = len(node_ids)
    cpu_capacity_factor_to_try = trial_cpu_capacity_factors()
    for cpu_capacity_factor in cpu_capacity_factor_to_try:
        print(f"Using cpu_capacity_factor {cpu_capacity_factor} for TBS")
        cpu_capacity = int(cpu_capacity_factor * node_num // pm_num)
        run_success = run_tbs(full_graph_metis_filepath, pm_num, cpu_capacity)
        if run_success:
            break

    # Acquire partition result
    partition_output_filepath = os.path.join(TBS_BIN_DIR, f"tmppartition{pm_num}")
    nodeid2pmid = {}
    with open(partition_output_filepath, 'r') as f:
        for i, line in enumerate(f):
            node_id = i + 1
            pm_id = int(line.strip())
            nodeid2pmid[node_id] = pm_id
            if pm_id not in distinct_pm_ids:
                print(f"Node {node_id} is assigned to PM {pm_id}, which is not in the server list.")
                exit(1)
    node2pmid = {}
    for node_id, pm_id in nodeid2pmid.items():
        node_name = nodeid2name[node_id]
        node2pmid[node_name] = pm_id

    # Print # of nodes in each PM
    pmid2nodes = {}
    for node_name, pm_id in node2pmid.items():
        if pmid2nodes.get(pm_id) is None:
            pmid2nodes[pm_id] = []
        pmid2nodes[pm_id].append(node_name)
    for pm_id in sorted(pmid2nodes.keys()):
        print(f"PM {pm_id} has {len(pmid2nodes[pm_id])} nodes.")

    # Construct the sub-graph of each PM for partitioning
    pmid2nodes = {} # Construct node list
    for pm_id, _ in enumerate(pm_config_list):
        pmid2nodes[pm_id] = []
    for node, pm_id in node2pmid.items():
        pmid2nodes[pm_id].append(node)
    pmid2adjacencylist = {} # Construct adjacency list
    for pm_id in pmid2nodes.keys():
        pmid2adjacencylist[pm_id] = {}
        for node in pmid2nodes[pm_id]:
            pmid2adjacencylist[pm_id][node] = []
    for node, pm_id in node2pmid.items():
        # If the node is not dangling, add its neighbors in the same PM into the adjacency list
        for neighbor in adjacency_list[node]:
            if node2pmid[neighbor] == pm_id:
                if neighbor not in pmid2adjacencylist[pm_id]:
                    pmid2adjacencylist[pm_id][neighbor] = []
                if node not in pmid2adjacencylist[pm_id]:
                    pmid2adjacencylist[pm_id][node] = []
                pmid2adjacencylist[pm_id][node].append(neighbor)
                pmid2adjacencylist[pm_id][neighbor].append(node)

    return node2pmid, pmid2nodes, pmid2adjacencylist
