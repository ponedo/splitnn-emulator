import os
import time
import json
import argparse
import subprocess
from util.remote import RemoteMachine, \
    execute_command_on_multiple_machines, send_file_to_multiple_machines

parser = argparse.ArgumentParser(description='Execute a batch of experiments')
args = parser.parse_args()

topos = [
    ["grid", "10", "10"],
    ["grid", "30", "30"],
    ["grid", "20", "20"],
    ["grid", "40", "40"],
    ["grid", "50", "50"],
    ["grid", "60", "60"],
    ["grid", "70", "70"],
    ["grid", "75", "75"],
    ["grid", "80", "80"],
    ["grid", "85", "85"],
    ["grid", "90", "90"],
    ["grid", "95", "95"],
    ["grid", "100", "100"],
    ["clos", "8"],
    ["clos", "12"],
    ["clos", "16"],
    ["clos", "20"],
    ["clos", "24"],
    ["clos", "28"],
    ["clos", "32"],
]

nms = [
    "iprpt",
    "iprbr",
    "ntlpt",
    "ntlbr",
    "ntlptlu",
    "ntlbrlu",
]

algos = [
    "naive",
    "dynamic",
]

# nsnums = []


def get_vn_manage_cmd(exe_path, operation, subtopo_filename, nm, algo, phy_intf, server_config_json):
    return f"{exe_path} -p {phy_intf} -s {server_config_json} -t {subtopo_filename} -m {nm} -a {algo} -o {operation}"


if __name__ == "__main__":
    # Get the absolute path of the currently executing script
    current_file_path = os.path.abspath(__file__)
    driver_workdir = os.path.dirname(current_file_path)
    os.chdir(driver_workdir) # Change the working directory

    # Read configuration of servers
    with open('data.json', 'r') as f:
        servers = json.load(f)

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
    server_config_dst_paths = {
        server["ipAddr"]: (
            server_config_src_path,
            os.path.join(server["infraWorkDir"], "server_config.json"), \
        ) for server in servers
    }
    send_file_to_multiple_machines(
        remote_machines, server_config_dst_paths)
    
    # Recompile virtual network manager on all machines
    execute_command_on_multiple_machines(
        remote_machines, {
            server["ipAddr"]: (
                "make", server["infraWorkDir"]
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
            generate_topology_cmd = [script_path] + topo[1:] + ["-f", topo_filepath]
        except IndexError:
            generate_topology_cmd = [script_path] + ["-f", topo_filepath]
        result = subprocess.run(generate_topology_cmd, capture_output=True, text=True)

        # Partition topology
        script_path = os.path.join(driver_workdir, "scripts", f"partition_topo.py")
        partition_topology_cmd = [script_path, "-f", topo_filepath, "-n", f"{len(servers)}"]
        result = subprocess.run(generate_topology_cmd, capture_output=True, text=True)

        # Send sub-topo to servers
        subtopo_filepaths = {}
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
            subtopo_filepaths[server["ipAddr"]] = (subtopo_src_filepath, subtopo_dst_filepath)
        send_file_to_multiple_machines(
            remote_machines, subtopo_filepaths)
        
        # Run experiments for different network managers and algorithms
        for nm in nms:
            for algo in algos:
                # Prepare setup and destroy commands
                setup_commands, destroy_commands = {}, {}
                for i, server in enumerate(servers):
                    exe_path = os.path.join(server["infraWorkDir"], "bin", "itl_test")
                    subtopo_dst_filename = subtopo_filepaths[server["ipAddr"]]
                    subtopo_filename = os.path.basename(subtopo_dst_filename)
                    setup_command = get_vn_manage_cmd(
                        os.path.join(server["infraWorkDir"], "bin", "itl_test"),
                        "setup", subtopo_dst_filename, nm, algo,
                        server["phyIntf"], server_config_dst_paths[server["ipAddr"]]
                    )
                    setup_command = get_vn_manage_cmd(
                        os.path.join(server["infraWorkDir"], "bin", "itl_test"),
                        "destroy", subtopo_dst_filename, nm, algo,
                        server["phyIntf"], server_config_dst_paths[server["ipAddr"]]
                    )
                    log_path = os.path.join(
                        server["infraWorkDir"], "log", f"{nm}.{algo}.{subtopo_filename}")
                    setup_commands.append((setup_command, server["infraWorkDir"], log_path))
                    destroy_commands.append((setup_command, server["infraWorkDir"], log_path))

                # Setup virtual network
                execute_command_on_multiple_machines(remote_machines, setup_commands)

                # Wait for a while
                time.sleep(30)

                # Destroy virtual network
                execute_command_on_multiple_machines(remote_machines, destroy_commands)

    # Close connection
    for remote_machine in remote_machines:
        remote_machine.close_connection()
