import os
import metis
import shutil
import argparse
import subprocess
import metis
import numpy as np
import random
import time
from .fmt_convert import *

########################## Naive Partitioning ##########################

def partition_naive(
    nodes, num_partitions):

    "Random Partitioning"

    node2pmid = {}
    for node in nodes:
        node2pmid[node] = random.randint(0, num_partitions - 1)

    return node2pmid

########################## METIS Partitioning ##########################

def create_metis_adjacency_list(nodes, adjacency_list):
    """Converts the adjacency list to METIS format where indices must be contiguous."""
    node_to_index = {node: idx for idx, node in enumerate(nodes)}
    index_to_node = {idx: node for node, idx in node_to_index.items()}
    metis_adjacency_list = []

    start_time = time.time()
    neighbor_count = 0
    for node in nodes:
        # Convert the node's neighbors from IDs to indices
        # neighbors_with_weight = [(node_to_index[neighbor], 1) for neighbor in adjacency_list[node]]  # Add default weight 1
        # metis_adjacency_list.append(neighbors_with_weight)
        neighbors = [node_to_index[neighbor] for neighbor in adjacency_list[node]]  # Add default weight 1
        metis_adjacency_list.append(neighbors)
        neighbor_count += 1
        # if neighbor_count % 1000 == 0:
        #     print(f"Neighbor count: {neighbor_count}")
    # print("Adjacency list conversion completed. Time-cost: ", time.time() - start_time)

    return metis_adjacency_list, node_to_index, index_to_node


def partition_metis(
    nodes, adjacency_list, num_partitions, random=False):
    
    """Partitions the graph into num_partitions using METIS and writes each subgraph."""
    node2serverid = {}
    if num_partitions == 1:
        server_id = 0
        for node in nodes:
            node2serverid[node] = 0
        return node2serverid

    # Convert adjacency list to METIS format with correct indices
    start_time = time.time()
    metis_adjacency_list, node_to_index, index_to_node = create_metis_adjacency_list(nodes, adjacency_list)

    # Partition the graph into num_partitions parts using METIS
    # print("Calling metis.part_graph...")
    # start_time = time.time()
    while True:
        try:
            if random:
                # Generate an random integer as seed
                seed = int(np.random.randint(0, 100))
                _, parts = metis.part_graph(metis_adjacency_list, nparts=num_partitions, niter=20, recursive=True, seed=seed)
            else:
                _, parts = metis.part_graph(metis_adjacency_list, nparts=num_partitions)
            break
        except metis.METIS_InputError as e:
            print(f"METIS Input Error: {e}")
            print("Retrying with a different seed...")
            continue
    # print("Partitioning completed. Time-cost: ", time.time() - start_time)

    for idx, part in enumerate(parts):
        node = index_to_node[idx]  # Convert index back to original node ID
        server_id = part
        node2serverid[node] = server_id

    return node2serverid

########################### TBS Partitioning ###########################
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


def partition_tbs(
    nodes, adjacency_list,
    pm_config_list, input_topo_filepath):

    distinct_pm_ids = set()
    for pm_id, _ in enumerate(pm_config_list):
        distinct_pm_ids.add(pm_id)
    
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

    return node2pmid
