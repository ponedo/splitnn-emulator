import sys
import os
import time
import math
import csv
import concurrent
from .partition.partition_topo_vm import partition_graph_across_vm

################## E_max_n derivation functions ##################

def get_partition_stats(nodes, adjacency_list, node2serverid, n):
    # Count the number of edges in each partition as well dangling edges
    partition_stats = {}
    for _, server_id in node2serverid.items():
        if server_id not in partition_stats:
            partition_stats[server_id] = {
                "node_count": 0,
                "edge_count": 0,
                "dangling_edges": 0
            }
    # Count nodes in each partition
    for node in nodes:
        server_id = node2serverid[node]
        if server_id in partition_stats:
            partition_stats[server_id]["node_count"] += 1
        else:
            partition_stats[server_id] = {
                "node_count": 1,
                "edge_count": 0,
                "dangling_edges": 0
            }

    # Count edges in each partition
    for u in nodes:
        for v in adjacency_list[u]:
            if u >= v:
                continue
            u_server_id = node2serverid[u]
            v_server_id = node2serverid[v]
            if u_server_id == v_server_id:
                partition_stats[u_server_id]["edge_count"] += 1
            else:
                partition_stats[u_server_id]["edge_count"] += 1
                partition_stats[u_server_id]["edge_count"] += 1
                partition_stats[u_server_id]["dangling_edges"] += 1
                partition_stats[v_server_id]["dangling_edges"] += 1
    # print(partition_stats)
    return partition_stats


def get_E_max_data_for_pm_topo(nodes, adjacency_list, pm_core_num):
    E_max_data = {}
    n_range = range(1, pm_core_num + 1)
    for n in n_range:
        # Partition the topology with METIS
        node2serverid = partition_graph_across_vm(nodes, adjacency_list, n, 0, random=False)
        partition_stats = get_partition_stats(nodes, adjacency_list, node2serverid, n)
        max_edge_count = max(partition_stats[server_id]["edge_count"] for server_id in partition_stats)
        E_max_data[n] = max_edge_count
    return E_max_data

################## Optimization functions ##################

def T_mvs(n, V, E_max, X, Y, Z):
    E_max_n = E_max(n)
    T_mvs_n = E_max_n * (V / n * X + Z) + E_max_n ** 2 * Y / 2
    return T_mvs_n

def T_sn(n, V, E_max, X, Y, Z):
    E_max_n = E_max(n)
    T_sn_n_topo = E_max_n * (V / n * X + Z) + E_max_n * math.sqrt(2 * E_max_n * X * Y)
    return T_sn_n_topo

def M_mvs(n, m_conf, Theta):
    theta_m_conf = Theta(m_conf)
    return n * theta_m_conf

def Gain_mvs(n, m_conf, V, E_max, X, Y, Z, Theta, m_req):
    T_mvs_1 = T_mvs(1, V, E_max, X, Y, Z)
    numerator = (T_mvs_1 - T_mvs(n, V, E_max, X, Y, Z)) / T_mvs_1
    dominator = M_mvs(n, m_conf, Theta) / m_req
    gain_mvs = numerator / dominator
    return gain_mvs

def Gain_sn(n, m_conf, V, E_max, X, Y, Z, Theta, m_req):
    T_sn_1 = T_sn(1, V, E_max, X, Y, Z)
    numerator = (T_sn_1 - T_sn(n, V, E_max, X, Y, Z)) / T_sn_1
    dominator = M_mvs(n, m_conf, Theta) / m_req
    gain_sn = numerator / dominator
    return gain_sn

def get_optimal_vm_allocation_for_pm(
    pmid, nodes, adjacency_list,
    pm_config, exp_config,
    FIXED_VM_NUM, FIXED_M_CONF, FIXED_BBNS_NUM):

    # Parse the PM config
    pm_core_num = pm_config["coreNum"]
    m_platform = pm_config["Memory"]
    X = pm_config["Parameters"]["X"]
    Y = pm_config["Parameters"]["Y"]
    Z = pm_config["Parameters"]["Z"]
    theta_m_conf_table = {
        int(m_conf): theta_m for m_conf, theta_m in \
            pm_config["Parameters"]["theta_m_conf_table"].items()
    }
    Theta = lambda m_conf: theta_m_conf_table[m_conf]

    # Constants
    m_req = exp_config["MemoryReq(GB)"]

    # # If VM number is fixed, use the fixed VM number
    # if FIXED_VM_NUM > 0:
    #     # Set m_conf to the key which is nearest to m_req/FIXED_VM_NUM in the theta_m_conf_table
    #     m_conf = min(theta_m_conf_table.keys(), key=lambda x: abs(x - m_req / FIXED_VM_NUM))
    #     return search_results, (FIXED_VM_NUM, m_conf, min(4, int(pm_core_num / FIXED_VM_NUM)))

    # Get the V and E_max(n) for the topology
    V = len(nodes)
    E_max_data = get_E_max_data_for_pm_topo(nodes, adjacency_list, pm_core_num)
    print(f"E_max data for pm #{pmid}: {E_max_data}")
    E_max = lambda n: E_max_data[n]

    # Setup the T and M models and Gain computation functions
    # T_mvs = lambda n, V, E_max: compute_T_mvs(n, V, E_max, X, Y, Z)
    # T_sn = lambda n, V, E_max: compute_T_sn(n, V, E_max, X, Y, Z)
    # M_mvs = lambda n, m_conf: compute_M_mvs(n, m_conf)
    # Gain_mvs = lambda n, m_conf: compute_gain_mvs(n, m_conf, T_mvs, M_mvs, m_req)
    # Gain_sn = lambda n, m_conf: compute_gain_sn(n, m_conf, T_sn, M_mvs, m_req)
    Gain = Gain_sn if FIXED_BBNS_NUM == 0 else Gain_mvs

    # Search for the optimal n and m_conf value that maximizes Gain
    n_opt = 1
    m_conf_opt = 8
    m_extra_opt = n_opt * Theta(m_conf_opt)
    # max_gain = Gain(n_opt, m_conf_opt, V, E_max, X, Y, Z, Theta, m_req)
    max_gain = -1
    search_n_range = range(2, pm_core_num)
    search_m_conf_range = list(theta_m_conf_table.keys())
    search_results = []
    for n in search_n_range:
        for m_conf in search_m_conf_range:
            gain = Gain(n, m_conf, V, E_max, X, Y, Z, Theta, m_req)
            m_extra = n * Theta(m_conf)
            search_results.append((n, m_conf, m_extra, gain))
            # If violating constraints, skip this value pair
            if FIXED_VM_NUM > 0 and n != FIXED_VM_NUM:
                continue
            if FIXED_M_CONF > 0 and m_conf != FIXED_M_CONF:
                continue
            if n * m_conf < m_req or n * m_conf > m_platform:
                continue
            if gain > max_gain:
                max_gain = gain
                n_opt = n
                m_conf_opt = m_conf
                m_extra_opt = m_extra
    vcpu_num_opt = min(8, int(pm_core_num / n_opt))
    optimal_result = (n_opt, m_conf_opt, vcpu_num_opt)
    return search_results, optimal_result

def get_optimal_vm_allocation_for_all_pms(
    pmid2nodes, pmid2adjacencylist,
    pm_config_list, exp_config,
    FIXED_VM_NUM_PER_PM, FIXED_M_CONF, FIXED_BBNS_NUM):

    # Get maximum VM number on each VM
    cur_ts = time.time()
    pmid2search_results = {}
    pmid2vmalloc = {}
    n_opt_legal = {}

    def compute_vm_allocation(pmid):
        search_results, optimal_result = get_optimal_vm_allocation_for_pm(
            pmid, pmid2nodes[pmid], pmid2adjacencylist[pmid],
            pm_config_list[pmid], exp_config,
            FIXED_VM_NUM_PER_PM, FIXED_M_CONF, FIXED_BBNS_NUM
        )
        n_opt, M_conf_opt, vcpu_num_opt = optimal_result
        legal = n_opt <= pm_config_list[pmid]["maxVMNum"]
        return pmid, search_results, optimal_result, legal

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(compute_vm_allocation, pmid2nodes.keys()))
    for pmid, search_results, vmalloc, legal in results:
        pmid2search_results[pmid] = search_results
        pmid2vmalloc[pmid] = vmalloc
        n_opt_legal[pmid] = legal

    # for pmid, pm_config in enumerate(pm_config_list):
    #     pmid = pm_config["id"]
    #     search_results, optimal_result = get_optimal_vm_allocation(
    #         pmid2nodes[pmid], pmid2adjacencylist[pmid],
    #         pm_config_list[pmid], FIXED_VM_NUM_PER_PM, FIXED_BBNS_NUM
    #     )
    #     n_opt, M_conf_opt = optimal_result[0], optimal_result[1]
    #     pmid2vmalloc[pmid] = (n_opt, M_conf_opt)
    #     # Raise an warning and skip current test if the optimal VM number exceed maximum VM number on this PM
    #     max_vm_num = pmid2maxvmnum[pmid]
    #     if n_opt > max_vm_num:
    #         print(f"Warning: Optimal VM number {n_opt} exceeds maximum VM number {max_vm_num} on PM {pmid}. Skipping current test.")
    #         n_opt_legal[pmid] = False

    # Record optimization time
    opt_time = time.time() - cur_ts
    print(f"Time for VM allocation optimization: {opt_time:.2f} seconds")

    return pmid2search_results, pmid2vmalloc, n_opt_legal

def output_vm_alloc_results(search_results, output_filepath):
    # Output the optimal n and m_conf for each topology to a csv file into separate files
    search_results.sort(key=lambda x: x[3], reverse=True)
    with open(output_filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["n", "m_conf", "m_extra", "Gain"])
        for n, m_conf, m_extra, gain in search_results:
            # Only keep two decimal places for m_extra and gain
            m_extra = round(m_extra, 2)
            gain = round(gain, 2)
            writer.writerow([n, m_conf, m_extra, gain])

def output_vm_alloc_result_for_all_pms(
    pmid2search_results, topo_name, full_cur_test_log_dir):
    vm_alloc_result_subdir = os.path.join(full_cur_test_log_dir, "vm_alloc_result")
    os.makedirs(vm_alloc_result_subdir, exist_ok=True)
    for pmid, search_results in pmid2search_results.items():
        output_vm_alloc_results(search_results, os.path.join(vm_alloc_result_subdir, f"pm_{pmid}.csv"))
