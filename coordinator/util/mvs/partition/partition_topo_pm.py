import os
import metis
import shutil
import argparse
import subprocess
from .algorithm import *

def partition_graph_across_pm(
    cross_pm_partition_method,
    nodes, adjacency_list,
    pm_config_list, input_topo_filepath):
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

    if cross_pm_partition_method.lower() == "naive":
        node2pmid = partition_naive(
            nodes, len(pm_config_list))
    elif cross_pm_partition_method.lower() == "metis":
        node2pmid = partition_metis(
            nodes, adjacency_list, len(pm_config_list), random=False)
    elif cross_pm_partition_method.lower() == "tbs":
        node2pmid = partition_tbs(
            nodes, adjacency_list,
            pm_config_list, input_topo_filepath)
    else:
        print(f"Cross-PM partitioning method {cross_pm_partition_method} is not identified, exiting...")
        exit(1)

    # Construct the sub-graph of each PM for partitioning
    pmid2nodes = {} # Construct node list
    for pm_id, _ in enumerate(pm_config_list):
        pmid2nodes[pm_id] = []
    for node, pm_id in node2pmid.items():
        pmid2nodes[pm_id].append(node)
    for pm_id in sorted(pmid2nodes.keys()):
        print(f"PM {pm_id} has {len(pmid2nodes[pm_id])} nodes.")
    pmid2adjacencylist = {} # Construct adjacency list
    pmid2edgenum = {} # Construct adjacency list
    for pm_id in pmid2nodes.keys():
        pmid2adjacencylist[pm_id] = {}
        pmid2edgenum[pm_id] = 0
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
                pmid2edgenum[pm_id] += 1
    for pm_id in sorted(pmid2adjacencylist.keys()):
        print(f"PM {pm_id} has {pmid2edgenum[pm_id]} edges.")

    return node2pmid, pmid2nodes, pmid2adjacencylist
