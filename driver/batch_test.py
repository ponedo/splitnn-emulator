import os
import time
import json
import argparse
import subprocess
from scripts.partition_topo import partition_graph
from util.remote import RemoteMachine, \
    execute_command_on_multiple_machines, send_file_to_multiple_machines

RUNTIME=1

topos = [
    ["grid", "10", "10"],
    ["grid", "20", "20"],
    ["grid", "30", "30"],
    ["grid", "40", "40"],
    ["grid", "50", "50"],
    ["grid", "60", "60"],
    ["grid", "70", "70"],
    ["grid", "75", "75"],
    ["grid", "80", "80"],
    ["grid", "85", "85"],
    ["grid", "90", "90"],
    ["clos", "8"],
    ["clos", "12"],
    ["clos", "16"],
    ["clos", "20"],
    ["clos", "24"],
    ["clos", "28"],
    # ["grid", "95", "95"],
    # ["clos", "32"],
    # ["grid", "100", "100"],
]

nms = [
    "ntlbrid",
    "ntlbrbk",
    # "iprpt",
    # "ntlpt",
    # "ntlptnc",
    # "ntlbr",
    # "iprbr",
    # "ntlbrnc",
]

algos = [
    "naive",
    "dynamic",
]

# nsnums = []


def get_vn_manage_cmd(exe_path, operation, subtopo_filename, nm, algo, phy_intf, server_config_json):
    return f"{exe_path} -p {phy_intf} -s {server_config_json} -t {subtopo_filename} -m {nm} -a {algo} -o {operation}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Execute a batch of experiments')
    args = parser.parse_args()

    # Get the absolute path of the currently executing script
    current_file_path = os.path.abspath(__file__)
    driver_workdir = os.path.dirname(current_file_path)
    os.chdir(driver_workdir) # Change the working directory
    env = os.environ.copy()
    env["METIS_DLL"]="~/.local/lib/libmetis.so"

    # Read configuration of servers
    with open('server_config.json', 'r') as f:
        server_config = json.load(f)
        servers = server_config["servers"]

    # Connect to remote machine
    remote_machines = []
    for server in servers:
        remote_machine = RemoteMachine(
            server["ipAddr"], server["user"],
            server["password"], working_dir=server["infraWorkDir"])
        machine = remote_machine.connect()
        remote_machines.append(machine)

    # Config servers on remote machines
    server_config_src_path = os.path.join(driver_workdir, "server_config.json")
    server_config_src_dst_paths = {
        server["ipAddr"]: (
            server_config_src_path,
            os.path.join(server["infraWorkDir"], "server_config.json"), \
        ) for server in servers
    }
    send_file_to_multiple_machines(
        remote_machines, server_config_src_dst_paths)
    
    # Recompile virtual network manager on all machines
    execute_command_on_multiple_machines(
        remote_machines, {
            server["ipAddr"]: (
                "make", server["infraWorkDir"], None, False
            ) for server in servers
        }
    )
    
    # Run experiments for different topology
    for topo in topos:
        topo_name = topo[0]
        topo_filepath = os.path.join(driver_workdir, "topo", f"{'_'.join(topo)}.txt")

        # Generate topology
        script_path = os.path.join(driver_workdir, "scripts", f"generate_{topo_name}_topo.py")
        try:
            generate_topology_cmd = ["python3", script_path] + topo[1:] + [topo_filepath]
        except IndexError:
            generate_topology_cmd = ["python3", script_path, topo_filepath]
        result = subprocess.run(generate_topology_cmd, capture_output=True, text=True)

        # Partition topology
        partition_graph(topo_filepath, len(servers))
        # script_path = os.path.join(driver_workdir, "scripts", f"partition_topo.py")
        # partition_topology_cmd = ["python3", script_path, "-f", topo_filepath, "-n", f"{len(servers)}"]
        # result = subprocess.run(partition_topology_cmd, capture_output=True, text=True, env=env)

        # Send sub-topo to servers
        subtopo_src_dst_filepaths = {}
        for i, server in enumerate(servers):
            topo_filename = os.path.basename(topo_filepath)
            topo_filename_arr = topo_filename.split('.')
            if len(topo_filename_arr) == 1:
                subtopo_filename_arr = topo_filename_arr + [f"sub{i}"]
            else:
                subtopo_filename_arr = topo_filename_arr[:-1] + [f"sub{i}"] + topo_filename_arr[-1:]
            subtopo_filename = '.'.join(subtopo_filename_arr)
            subtopo_src_filepath = os.path.join(os.path.dirname(topo_filepath), subtopo_filename)
            subtopo_dst_filepath = os.path.join(server["infraWorkDir"], "tmp", subtopo_filename)
            subtopo_src_dst_filepaths[server["ipAddr"]] = (subtopo_src_filepath, subtopo_dst_filepath)
        send_file_to_multiple_machines(
            remote_machines, subtopo_src_dst_filepaths)
        
        # Run experiments for different network managers and algorithms
        for nm in nms:
            for algo in algos:
                for run_i in range(RUNTIME):
                    # Prepare setup and destroy commands
                    setup_commands, destroy_commands = {}, {}
                    for i, server in enumerate(servers):
                        exe_path = os.path.join(server["infraWorkDir"], "bin", "itl_test")
                        subtopo_dst_filename = subtopo_src_dst_filepaths[server["ipAddr"]][1]
                        server_config_dst_filepath = server_config_src_dst_paths[server["ipAddr"]][1]
                        subtopo_filename = os.path.basename(subtopo_dst_filename)
                        setup_command = get_vn_manage_cmd(
                            os.path.join(server["infraWorkDir"], "bin", "itl_test"),
                            "setup", subtopo_dst_filename, nm, algo,
                            server["phyIntf"], server_config_dst_filepath
                        )
                        destroy_command = get_vn_manage_cmd(
                            os.path.join(server["infraWorkDir"], "bin", "itl_test"),
                            "destroy", subtopo_dst_filename, nm, algo,
                            server["phyIntf"], server_config_dst_filepath
                        )
                        setup_log_path = os.path.join(
                            server["infraWorkDir"], "log", f"{nm}.{algo}.setup.run_{run_i}.{subtopo_filename}")
                        destroy_log_path = os.path.join(
                            server["infraWorkDir"], "log", f"{nm}.{algo}.destroy.run_{run_i}.{subtopo_filename}")
                        setup_commands[server["ipAddr"]] = (setup_command, server["infraWorkDir"], setup_log_path, True)
                        destroy_commands[server["ipAddr"]] = (destroy_command, server["infraWorkDir"], destroy_log_path, True)

                    # Run virtual networks
                    execute_command_on_multiple_machines(remote_machines, setup_commands) # Setup virtual network
                    time.sleep(5) # Wait for a while
                    execute_command_on_multiple_machines(remote_machines, destroy_commands) # Destroy virtual network

    # Close connection
    for remote_machine in remote_machines:
        remote_machine.close_connection()
