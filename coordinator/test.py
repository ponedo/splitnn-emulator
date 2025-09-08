import os
import time
import json
import math
import argparse
import subprocess
import shutil
import sys
from copy import deepcopy
from itertools import product
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout, redirect_stderr

from util.topo_util import generate_topo
from util.mvs.partition.partition_topo_pm import *
from util.mvs.partition.partition_topo_vm import *
from util.mvs.optimize import *
from util.mvs.vm_manage import *
from util.mns import *
from util.common import *
from util.remote import *
from util.topo_util import *
from util.factor import *

############################ Constants ###############################

COORDINATOR_WORKDIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(COORDINATOR_WORKDIR) # Change cuurent working directory

TEST_LOG_FILENAME = "test_log.txt"
COORDINATOR_CONFIG_DIR = "config"
PM_CONFIG_PATH = os.path.join(COORDINATOR_CONFIG_DIR, "pm_config.json")
EXP_CONFIG_PATH = os.path.join(COORDINATOR_CONFIG_DIR, "exp_config.json")
SERVER_CONFIG_FILENAME = "server_config.json"
AGENT_BIN_PATH = "bin/splitnn_agent"
AGENT_TOPO_DIR = "tmp/topo"
LOCAL_RESULT_DIR = "raw_results"
SERVER_RESULTS_DIR = "server_results"
LOCAL_TOPO_DIR = os.path.join(COORDINATOR_WORKDIR, "topo")
REMOTE_RESULT_PATHS = [
    ("file", "tmp/setup_log.txt"),
    ("dir", "tmp/setup_cpu_mem_usage.txt"),
    # ("file", "tmp/clean_log.txt"),
    # ("dir", "tmp/clean_cpu_mem_usage.txt"),
    ("dir", "tmp/kern_func"),
    ("file", "tmp/link_log.txt"),
    # ("dir", "tmp/cctr_log"),
    # ("dir", "tmp/cctr_time.txt"),
]

######################## Test options ###########################
parser = argparse.ArgumentParser(description='A script to calculate optimal VM number n_opt for multi-VM splitting')
parser.add_argument(
    '-n', '--fixed-vm-num', type=int, default=0,
    help='Fixed VM number per PM. If set to 0, use the optimal VM number; if set > 0, use the fixed VM number')
parser.add_argument(
    '-m', '--fixed-m-conf', type=int, default=0,
    help='Fixed memory configuration per PM. If set to 0, use the optimal config; if set > 0, use the fixed number')
parser.add_argument(
    '-k', '--fixed-bbns-num', type=int, default=0,
    help='The BBNS number used per VM. If set to 0, use the optimal BBNS number; if set > 0, use the fixed BBNS number')
args = parser.parse_args()

FIXED_VM_NUM_PER_PM = args.fixed_vm_num # If set to 0, use the optimal VM number; if set > 0, use the fixed VM number
FIXED_M = args.fixed_m # If set to 0, use the optimal memory configuration for each VM; if set > 0, use the fixed number
FIXED_BBNS_NUM = args.fixed_bbns_num # If set to 0, use the optimal BBNS number; if set > 0, use the fixed BBNS number

assert FIXED_VM_NUM_PER_PM >= 0
assert FIXED_M >= 0
assert not (FIXED_VM_NUM_PER_PM == 0 and FIXED_M > 0)
assert FIXED_BBNS_NUM >= 0

######################### Agent options ############################

const_options = {
}

var_options = {
    #################### Options for the agent ####################
    # Topologies
    "t": [
        # ["isolated", "100"],
        # ["grid", "100", "100"],
        # ["isolated", "10000"],
        # ["grid", "50", "50"],
        # ["isolated", "3600"],
        # ["grid", "18", "30"],
        # ["grid", "40", "50"],
        # ["grid", "60", "60"],

        # ["grid", "10", "10"],
        # ["grid", "20", "20"],
        # ["grid", "30", "30"],
        # ["grid", "40", "40"],
        # ["grid", "50", "50"],
        # ["grid", "60", "60"],
        # ["grid", "70", "70"],
        # ["grid", "75", "75"],
        # ["grid", "80", "80"],
        # ["grid", "85", "85"],
        # ["grid", "90", "90"],
        # ["grid", "95", "95"],
        # ["grid", "100", "100"],
        # ["grid", "200", "200"],

        # ["clos", "8"],
        # ["clos", "12"],
        # ["clos", "16"],
        # ["clos", "20"],
        # ["clos", "24"],
        # ["clos", "28"],
        # ["clos", "32"],

        # ["chain", "1251"],
        # ["chain", "2501"],
        # ["chain", "3751"],
        # ["chain", "5001"],
        # ["chain", "6251"],
        # ["chain", "7501"],
        # ["chain", "8751"],
        # ["chain", "10001"],

        # ["trie", "1251", "10"],
        # ["trie", "2501", "10"],
        # ["trie", "3751", "10"],
        # ["trie", "5001", "10"],
        # ["trie", "6251", "10"],
        # ["trie", "7501", "10"],
        # ["trie", "8751", "10"],
        # ["trie", "10001", "10"],

        # ["as", "small"],
        # ["as", "medium"],
        # ["as", "large"],
        # ["as", "eu"],
        # ["as", "us"],
    ],

    "s": [
        SERVER_CONFIG_FILENAME
    ],

    # "a": [
    #     "dynamic",
    #     "naive",
    # ],

    # "d": [
    #     0,
    #     1
    # ],

    # "N": [
        # "cctr",
        # "goctr"
    # ],

    # "l": [
    #     "ntlbr",
    # ],

    # "p": [
    #     0,
    #     2,
    #     4,
    #     8
    # ],
}

#################### Options for testing ####################
# "CrossPMPartitioning" : [
#     "naive",
#     "METIS",
#     "TBS",
# ]

######################### SSH Helper functions ############################

def connect_remote_machines(machine_config_list):
    remote_machines = []
    for mach in machine_config_list:
        remote_machine = RemoteMachine(
            mach["ipAddr"], mach["user"], mach["password"])
        machine = remote_machine.connect()
        remote_machines.append(machine)
    return remote_machines


def prepare_env_on_remote_servers(
    remote_machines, server_config_filepath, server_config_list):

    # Synchronize code
    print("Synchronizing code...")
    execute_command_on_multiple_machines(
        remote_machines, {
            server["ipAddr"]: (
                "./sync_code.sh master", os.path.join(server["agentWorkDir"], ".."), None, False
            ) for server in server_config_list
        }
    )

    # Distribute vm_config.json onto each VM as server_config.json 
    print("Distributing vm_config.json (server_config.json)...")
    server_config_src_dst_paths = {
        server["ipAddr"]: (
            server_config_filepath,
            os.path.join(server["agentWorkDir"], SERVER_CONFIG_FILENAME),
            False
        ) for server in server_config_list
    }
    send_file_to_multiple_machines(
        remote_machines, server_config_src_dst_paths)

    # Recompile agent on all machines
    print("Building agent on VMs...")
    execute_command_on_multiple_machines(
        remote_machines, {
            server["ipAddr"]: (
                "export GOPROXY=https://goproxy.cn,direct && make", server["agentWorkDir"], None, False
            ) for server in server_config_list
        }
    )

    # # Prepare docker images on VMs
    # print("Preparing docker images on VMs...")
    # execute_command_on_multiple_machines(
    #     remote_machines, {
    #         server["ipAddr"]: (
    #             f"./scripts/prepare_rootfs.sh {server['dockerImageName']}", server["agentWorkDir"], None, True
    #         ) for server in server_config_list
    #     }
    # )

######################### VM manage helper functions ############################

def get_mem_usage_of_all_pms(remote_pms, pm_config_list):
    ipAddr2pmid = {}
    for pmid, server in enumerate(pm_config_list):
        ipAddr2pmid[server["ipAddr"]] = pmid
    results = execute_command_on_multiple_machines(
        remote_pms, {
            server["ipAddr"]: (
                "free | awk '/Mem/ {print $3}'", server["vmManagerWorkDir"], None, False
            ) for server in pm_config_list
        }
    )
    mem_results = {ipAddr2pmid[ipAddr]: int(result) for ipAddr, result in results.items()}
    return mem_results

######################### Topology Helper functions ############################

def distribute_sub_topo_to_vms(topo, full_topo_filepath, remote_vms, vm_config_list):
    # Send sub-topo to servers
    sub_topo_src_dst_filepaths = {}
    for i, server in enumerate(vm_config_list):
        sub_topo_filename = get_sub_topo_filename(topo, i)
        sub_topo_src_filepath = os.path.join(os.path.dirname(full_topo_filepath), sub_topo_filename)
        sub_topo_dst_filepath = os.path.join(server["agentWorkDir"], AGENT_TOPO_DIR, sub_topo_filename)
        sub_topo_src_dst_filepaths[server["ipAddr"]] = \
            (sub_topo_src_filepath, sub_topo_dst_filepath, False)
    send_file_to_multiple_machines(
        remote_vms, sub_topo_src_dst_filepaths)

###################### Test Command Helper functions #########################

def get_one_vn_manage_cmd(bin_path, operation, options):
    vn_manage_cmd = f"{bin_path} -o {operation}"
    for k, v in options.items():
        v = f"{v}"
        if " " in v:
            print(f"Warning: an option value of virtual network management command contains space: (\"{k}\" \"{v}\")")
        vn_manage_cmd += f" -{k} {v}"
    return vn_manage_cmd

def generate_agent_commands(
    var_opts, topo_args, vm_config_list, serverid2bbnsnum):

    setup_commands, clean_commands = {}, {}

    # Merge -i -b -t options to setup/clean commands
    for server_id, server in enumerate(vm_config_list):
        server_i_opts = deepcopy(var_opts)

        # Add -i option
        server_i_opts['i'] = server_id

        # Add -t option
        remote_sub_topo_filepath = os.path.join(
            AGENT_TOPO_DIR, get_sub_topo_filename(topo_args, server_id))
        server_i_opts['t'] = remote_sub_topo_filepath

        # Add -b option
        server_i_opts['b'] = serverid2bbnsnum[server_id]

        # Generate commands
        setup_command = get_one_vn_manage_cmd(AGENT_BIN_PATH, "setup", server_i_opts)
        setup_commands[server["ipAddr"]] = \
            (setup_command, server["agentWorkDir"], None, True)
        clean_command = get_one_vn_manage_cmd(AGENT_BIN_PATH, "clean", server_i_opts)
        clean_commands[server["ipAddr"]] = \
            (clean_command, server["agentWorkDir"], None, True)

    return setup_commands, clean_commands

###################### Result Collection Helper functions #########################

def get_one_test_log_name(var_opts):
    old_var_opts_t = var_opts['t']
    var_opts['t'] = '_'.join(var_opts['t'])
    dir_name_elements = [f"{k}--{v}" for k, v in var_opts.items()]
    dir_name = '--'.join(dir_name_elements)
    var_opts['t'] = old_var_opts_t
    return dir_name

def reap_one_test_results(remote_machines, server_config_list, cur_test_log_dir):
    server_log_dirs = []
    for i, server in enumerate(server_config_list):
        server_i_log_dir = os.path.join(cur_test_log_dir, SERVER_RESULTS_DIR, f"server{i}")
        os.makedirs(server_i_log_dir, exist_ok=True)
        server_log_dirs.append(server_i_log_dir)

    for remote_result_path in REMOTE_RESULT_PATHS:
        # Define different remote and local directories for each machine
        directories = {
            server["ipAddr"]: (
                os.path.join(server["agentWorkDir"], remote_result_path[1]),
                server_log_dirs[i],
                remote_result_path[0] == "dir"
            )
            for i, server in enumerate(server_config_list)
        }
        receive_file_from_multiple_machines(remote_machines, directories)

def print_commands(commands):
    for ip, (cmd, work_dir, _, _) in commands.items():
        print(f"{ip} in {work_dir}: {cmd}")


def output_tdf_to_file(tdf, tdf_filepath):
    with open(tdf_filepath, 'w') as f:
        f.write(f"TDF: {tdf}\n")

def output_mem_usage_to_file(
    vm_mem_results, exp_mem_results, empty_mem_results, mem_usage_filepath):
    assert set(vm_mem_results.keys()) == set(exp_mem_results.keys())
    assert set(vm_mem_results.keys()) == set(empty_mem_results.keys())
    vm_mem_usage_results = {}
    for pmid in vm_mem_results.keys():
        vm_mem_usage_results[pmid] = vm_mem_results[pmid] - empty_mem_results[pmid]
    total_vm_mem_usage = sum(vm_mem_usage_results.values())
    exp_mem_usage_results = {}
    for pmid in vm_mem_results.keys():
        exp_mem_usage_results[pmid] = exp_mem_results[pmid] - empty_mem_results[pmid]
    total_exp_mem_usage = sum(exp_mem_usage_results.values())

    with open(mem_usage_filepath, 'w') as f:
        for pmid in vm_mem_usage_results:
            f.write(f"PM {pmid} VM Memory: {vm_mem_usage_results[pmid]}\n")
        f.write(f"Total VM Memory (KB): {total_vm_mem_usage}\n")
        for pmid in exp_mem_usage_results:
            f.write(f"PM {pmid} Exp Memory: {exp_mem_usage_results[pmid]}\n")
        f.write(f"Total Exp Memory (KB): {total_exp_mem_usage}\n")

###################### One run of the experiment #########################

def one_test(var_opts, remote_pms, local_result_repo_dir, pm_config_list, exp_config):
    # Check log directory of current test
    print(f"\n\n============== New test! Options: {var_opts} ==============\n")
    test_start_ts = time.time()
    final_cur_test_log_dir = get_one_test_log_name(var_opts)
    full_cur_test_log_dir = os.path.join(local_result_repo_dir, final_cur_test_log_dir)
    if os.path.exists(full_cur_test_log_dir) and os.listdir(full_cur_test_log_dir):
        print(f"Test {var_opts} skipped")
        return # Current test has been completed before, skip current iteration
    os.makedirs(full_cur_test_log_dir, exist_ok=True)

    # Generate current topology
    topo = var_opts['t']
    full_topo_filepath = generate_topo(topo, LOCAL_TOPO_DIR)

    # Partition topo to PMs
    print(f"Partitioning across all PMs...")
    cur_ts = time.time()
    nodes, adjacency_list = read_graph_from_topo_file(full_topo_filepath)
    cross_pm_partition_method = exp_config["CrossPMPartitioning"]
    node2pmid, pmid2nodes, pmid2adjacencylist = partition_graph_across_pm(
        cross_pm_partition_method,
        nodes, adjacency_list,
        pm_config_list, full_topo_filepath)
    cross_pm_partition_time = time.time() - cur_ts
    print(f"Cross-PM partitioning elapsed for {cross_pm_partition_time}s")

    # Get the optimal VM allocation for each PM in parallel
    print(f"Planning optimal VM configuration...")
    cur_ts = time.time()
    pmid2search_results, pmid2vmalloc, n_opt_legal = \
        get_optimal_vm_allocation_for_all_pms(
            pmid2nodes, pmid2adjacencylist,
            pm_config_list, exp_config,
            FIXED_VM_NUM_PER_PM, FIXED_M, FIXED_BBNS_NUM
        )
    if not all(n_opt_legal.values()):
        print(f"Warning: Optimal VM number exceeds maximum VM number on some PMs. Skipping current test.")
        print(f"n_opt_legal: {n_opt_legal}")
        return
    opt_time = time.time() - cur_ts
    print(f"Time for VM allocation optimization: {opt_time:.2f} seconds")

    # Store the vm allocation result
    topo_name = '_'.join(var_opts['t'])
    output_vm_alloc_result_for_all_pms(
        pmid2search_results, topo_name, full_cur_test_log_dir)

    # Alter VM memory and get configration of VMs across all PMs
    print(f"Partitioning across all VMs...")
    cur_ts = time.time()
    vm_config_list = alter_vm_for_all_pms(
        pmid2vmalloc, remote_pms,
        pm_config_list, exp_config,
        full_cur_test_log_dir)
    pmid2vms = get_pmid2vms(pm_config_list, vm_config_list)
    vm_config_filepath = write_vm_config_list_to_file(
        vm_config_list, full_cur_test_log_dir)
    cross_vm_partition_time = time.time() - cur_ts
    print(f"Cross-VM partitioning elapsed for {cross_vm_partition_time}s")

    # Start VMs on all PMs
    print(f"Starting VMs...")
    cur_ts = time.time()
    start_vms_for_all_pms(remote_pms, pm_config_list, pmid2vms)
    wait_for_all_vms_to_start(vm_config_list, timeout=300)
    vm_start_elapsed_time = time.time() - cur_ts
    time.sleep(10)
    print(f"VM starting consumes {vm_start_elapsed_time}s")

    # Record host PM usage
    vm_mem_results = get_mem_usage_of_all_pms(remote_pms, pm_config_list)

    # Connect to all remote VMs
    remote_vms = [None for vm_config in vm_config_list]
    while True:
        print("Trying SSH connection...")
        remote_vms = connect_remote_machines(vm_config_list)
        if all(remote_vms):
            break
        wait_for_all_vms_to_start(vm_config_list, timeout=300)

    # Config environments on remote VMs
    prepare_env_on_remote_servers(remote_vms, vm_config_filepath, vm_config_list)

    # Partition the topology to VMs
    tdf = partition_topo_across_vms_for_all_pms(
        nodes, adjacency_list,
        pmid2nodes, pmid2adjacencylist,
        vm_config_list, full_topo_filepath)
    tdf_filepath = os.path.join(full_cur_test_log_dir, "tdf.txt")
    output_tdf_to_file(tdf, tdf_filepath)

    # Distribute sub-topologies to remote VMs
    distribute_sub_topo_to_vms(
        topo, full_topo_filepath, remote_vms, vm_config_list)

    # Calcuate best BBNS number k_opt for each sub-topology
    serverid2bbnsnum = get_bbns_num_for_all_vms(
        topo, pm_config_list, vm_config_list, FIXED_BBNS_NUM
    )

    # Generate setup/clean commands
    setup_commands, clean_commands = generate_agent_commands(
        var_opts, topo, vm_config_list, serverid2bbnsnum)

    # Setup virtual network with agents on remote VMs
    time.sleep(5)
    print(f"Setup virtual networks...")
    print_commands(setup_commands)
    cur_ts = time.time()
    execute_command_on_multiple_machines(remote_vms, setup_commands) # Setup virtual network
    setup_elapsed_time = time.time() - cur_ts
    print(f"Setup done, time: {setup_elapsed_time}s")
    time.sleep(15) # Wait for a while

    # Record host PM usage
    exp_mem_results = get_mem_usage_of_all_pms(remote_pms, pm_config_list)

    # # Clean virtual network with agents on remote VMs
    # print_commands(clean_commands)
    # execute_command_on_multiple_machines(remote_vms, clean_commands) # Clean virtual network
    # time.sleep(20) # Wait for a while

    # Reap results of current test
    reap_one_test_results(remote_vms, vm_config_list, full_cur_test_log_dir)
    time.sleep(5) # Wait for a while

    # Close connection to VMs
    for remote_vm in remote_vms:
        remote_vm.close_connection()
    time.sleep(5) # Wait for a while

    # Destroy VMs and record destroy time
    print(f"Destroying VMs...")
    cur_ts = time.time()
    destroy_vms_for_all_pms(remote_pms, pm_config_list, pmid2vms)
    vm_destroy_elapsed_time = time.time() - cur_ts
    time.sleep(10)
    print(f"VM destroying consumes {vm_destroy_elapsed_time}s")

    # Record PM memory usage
    empty_mem_results = get_mem_usage_of_all_pms(remote_pms, pm_config_list)
    mem_usage_filepath = os.path.join(full_cur_test_log_dir, "pm_mem_usage.txt")
    output_mem_usage_to_file(vm_mem_results, exp_mem_results, empty_mem_results, mem_usage_filepath)

    test_elapsed_time = time.time() - test_start_ts
    print(f"The test consumes {test_elapsed_time}s")
    

def run_all_tests(local_result_repo_dir, pm_config_list, exp_config):
    # Connect to remote PMs
    remote_pms = connect_remote_machines(pm_config_list)

    # Iterate over all possible combiation of options
    var_opt_keys = var_options.keys()

    # Each combination of options is a test
    for var_opt_comb in product(*var_options.values()):
        # Get a combination of options
        opts = dict(zip(var_opt_keys, var_opt_comb))
        var_opts = deepcopy(opts)
        one_test(var_opts, remote_pms, local_result_repo_dir, pm_config_list, exp_config)

    # Close connection to PMs
    for remote_machine in remote_pms:
        remote_machine.close_connection()


################################# Main ##################################

if __name__ == "__main__":
    # Read configurations
    with open(PM_CONFIG_PATH, 'r') as f:
        pm_config = json.load(f)
        pm_config_list = pm_config["physicalMachines"]
    with open(EXP_CONFIG_PATH, 'r') as f:
        exp_config = json.load(f)

    # Prepare local repository directory for storing test results
    current_time = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    cross_pm_partition_method = exp_config["CrossPMPartitioning"] # naive, METIS, or TBS
    local_result_repo_dir = os.path.join(
        LOCAL_RESULT_DIR,
        f"cppm-{cross_pm_partition_method}--pm-{len(pm_config_list)}--n-{FIXED_VM_NUM_PER_PM}--m-{FIXED_M}--k-{FIXED_BBNS_NUM}--{current_time}")
    os.makedirs(local_result_repo_dir, exist_ok=True)

    # Redirect stdout and stderr to the log file
    with open(os.path.join(local_result_repo_dir, TEST_LOG_FILENAME), "w", buffering=1) as f:
        with redirect_stdout(f), redirect_stderr(f):
            print(f"CrossPMPartitioning: {cross_pm_partition_method}")
            print(f"FIXED_VM_NUM_PER_PM: {FIXED_VM_NUM_PER_PM}")
            print(f"FIXED_M: {FIXED_M}")
            print(f"FIXED_BBNS_NUM: {FIXED_BBNS_NUM}")
            run_all_tests(local_result_repo_dir, pm_config_list, exp_config)
