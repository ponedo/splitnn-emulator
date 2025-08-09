import shutil
import argparse
import time
from .fmt_util import *
from .compute_tdf import *
from .algorithm import *


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


def partition_graph_across_vm(nodes, adjacency_list, num_partitions, acc_server_num, random=False):
    """Partitions the graph into num_partitions using METIS and writes each subgraph."""
    if num_partitions == 1:
        node2serverid = {}
        server_id = acc_server_num
        for node in nodes:
            node2serverid[node] = server_id
        return node2serverid

    node2serverid = partition_metis(
        nodes, adjacency_list, num_partitions, random=False)

    for node in node2serverid:
        node2serverid[node] += acc_server_num

    return node2serverid


def partition_topo_across_vms_for_all_pms(
    nodes, adjacency_list,
    pmid2nodes, pmid2adjacencylist,
    vm_config_list, input_topo_filepath):

    pm2servernum = {}
    serverid2pmid = {}
    for i, server in enumerate(vm_config_list):
        pm_id = server["physicalMachineId"]
        if pm2servernum.get(pm_id) is None:
            pm2servernum[pm_id] = 0
        pm2servernum[pm_id] += 1
        serverid2pmid[i] = pm_id
    print(f"Partitioning...")
    print(f"# of physical machines: {len(pm2servernum)}")
    print(f"# of servers: {len(vm_config_list)}")

    # Partition the sub-graph of each PM into VMs
    import concurrent.futures
    def partition_vm_task(pm_id, pmid2nodes, pmid2adjacencylist, pm_server_num, acc_server_num):
        # print(f"Partitioning with PM #{pm_id}...")
        return partition_graph_across_vm(
            pmid2nodes[pm_id], pmid2adjacencylist[pm_id], pm_server_num, acc_server_num
        )
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        acc_server_num = 0
        for pm_id, pm_server_num in pm2servernum.items():
            futures.append(executor.submit(partition_vm_task, pm_id, pmid2nodes, pmid2adjacencylist, pm_server_num, acc_server_num))
            acc_server_num += pm_server_num
        node2serverid = {}
        for future in concurrent.futures.as_completed(futures):
            node2serverid.update(future.result())

    # Print # of nodes in each server
    serverid2nodes = {}
    for node_name, server_id in node2serverid.items():
        if serverid2nodes.get(server_id) is None:
            serverid2nodes[server_id] = []
        serverid2nodes[server_id].append(node_name)
    for server_id in sorted(serverid2nodes.keys()):
        print(f"Server {server_id}: {len(serverid2nodes[server_id])} nodes")

    # Scan the adjacency_list, and allocate VXLAN IDs for cross-pm edges and cross-vm-intra-pm edges
    write_subtopos_to_file(nodes, adjacency_list, node2serverid, acc_server_num, input_topo_filepath)

    # Calculate and print TDF
    tdf = compute_tdf(nodes, adjacency_list, node2serverid, serverid2pmid)
    print(f"TDF: {tdf}")

    return tdf
