import time
import json
import subprocess
from ..remote import *

##################### VM management functions #####################

def start_vms_for_pm(vm_configs):
    vm_num = len(vm_configs)
    return f"./vm_operator/operate_vm.sh start {vm_num}"

def start_vms_for_all_pms(remote_pms, pm_config_list, pmid2vms):
    start_vm_cmds = {}
    for pmid, vm_configs in pmid2vms.items():
        pm = pm_config_list[pmid]
        start_vm_cmds[pm["ipAddr"]] = (
            start_vms_for_pm(vm_configs),
            pm_config_list[pmid]["vmManagerWorkDir"],
            None, False
        )
    execute_command_on_multiple_machines(
        remote_pms, start_vm_cmds
    )

def destroy_vms_for_pm(vm_configs):
    vm_num = len(vm_configs)
    return f"./vm_operator/operate_vm.sh destroy {vm_num}"

def destroy_vms_for_all_pms(remote_pms, pm_config_list, pmid2vms):
    destroy_vm_cmds = {}
    for pmid, vm_configs in pmid2vms.items():
        pm = pm_config_list[pmid]
        destroy_vm_cmds[pm["ipAddr"]] = (
            destroy_vms_for_pm(vm_configs),
            pm_config_list[pmid]["vmManagerWorkDir"],
            None, False
        )
    execute_command_on_multiple_machines(
        remote_pms, destroy_vm_cmds
    )

def alter_vm_cmd_for_pm(vm_alloc):
    vm_num, m, vcpu_num = vm_alloc
    m = 1000000 * m # convert GB to KB
    return f"./vm_operator/alter_vm.sh {vm_num} {m} {vcpu_num}"

def alter_vm_for_all_pms(
    pmid2vmalloc, remote_pms,
    pm_config_list, exp_config,
    full_cur_test_log_dir):

    # Alter VM memory
    alter_vm_cmds = {}
    for pmid, vm_alloc in pmid2vmalloc.items():
        pm = pm_config_list[pmid]
        alter_vm_cmds[pm["ipAddr"]] = (
            alter_vm_cmd_for_pm(vm_alloc),
            pm_config_list[pmid]["vmManagerWorkDir"],
            None, False
        )
    execute_command_on_multiple_machines(
        remote_pms, alter_vm_cmds
    )

    # Reap vm_ips.txt from remote PMs
    vm_ips_dir = os.path.join(full_cur_test_log_dir, "vm_ips")
    os.makedirs(vm_ips_dir, exist_ok=True)
    directories = {
        pm_config["ipAddr"]: (
            os.path.join(pm_config["vmManagerWorkDir"], "vm_ips.txt"),
            os.path.join(vm_ips_dir, f"pm_{pmid}_vm_ips.txt"),
            False
        )
        for pmid, pm_config in enumerate(pm_config_list)
    }
    receive_file_from_multiple_machines(remote_pms, directories)

    # Read vm_ips.txt and generate vm_config_list
    vm_config_list = []
    for pmid, pm_config in enumerate(pm_config_list):
        vm_ips_filepath = os.path.join(
            vm_ips_dir, f"pm_{pmid}_vm_ips.txt")
        with open(vm_ips_filepath, 'r') as f:
            vm_ips = f.read().strip().splitlines()
        for vm_ip in vm_ips:
            vm_config = {
                "ipAddr": vm_ip,
                "user": exp_config["VMuser"],
                "password": exp_config["VMpassword"],
                "phyIntf": exp_config["VMphyIntf"],
                "agentWorkDir": exp_config["VMagentWorkDir"],
                "dockerImageName": exp_config["dockerImageName"],
                "kernFuncsToMonitor": exp_config["kernFuncsToMonitor"],
                "physicalMachineId": pmid
            }
            vm_config_list.append(vm_config)
    print("VM configuration:")
    for vm_config in vm_config_list:
        print(vm_config)

    return vm_config_list

def get_pmid2vms(pm_config_list, vm_config_list):
    pmid2vms = {}
    for vm_config in vm_config_list:
        pmid = vm_config["physicalMachineId"]
        if pmid not in pmid2vms:
            pmid2vms[pmid] = []
        pmid2vms[pmid].append(vm_config)
    return pmid2vms

def test_connectivity_of_all_vms(vm_config_list):
    # Use ping to test connectivity of all VMs
    # Return True if all VMs are reachable, False otherwise
    for vm_config in vm_config_list:
        vm_ip = vm_config["ipAddr"]
        response = subprocess.run(
            ["ping", "-c", "1", vm_ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if response.returncode != 0:
            print(f"VM {vm_ip} is not reachable.")
            return False
    return True

def wait_for_all_vms_to_start(vm_config_list, timeout=300):
    # Wait for all VMs to start by checking if they are reachable
    start_time = time.time()
    while True:
        if test_connectivity_of_all_vms(vm_config_list):
            print("All VMs are started.")
            return True
        if time.time() - start_time > timeout:
            print("Timeout while waiting for VMs to start.")
            return False
        time.sleep(5)  # Wait for 5 seconds before retrying

def write_vm_config_list_to_file(vm_config_list, full_cur_test_log_dir):
    # Write vm_config_list to a file
    json_content = {
        "servers": vm_config_list
    }
    vm_config_filepath = os.path.join(full_cur_test_log_dir, "vm_config.json")
    with open(vm_config_filepath, 'w') as f:
        json.dump(json_content, f, indent=4)
    print(f"VM configuration written to {vm_config_filepath}")
    return vm_config_filepath