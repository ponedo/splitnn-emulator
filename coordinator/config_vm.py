import os

from util.remote import *

COORDINATOR_WORKDIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(COORDINATOR_WORKDIR) # Change cuurent working directory

COORDINATOR_CONFIG_DIR = "config"
PM_CONFIG_PATH = os.path.join(COORDINATOR_CONFIG_DIR, "pm_config.json")






################################# Main ##################################

if __name__ == "__main__":
    
    # Read configuration of physical machines and servers (VMs)
    with open(PM_CONFIG_PATH, 'r') as f:
        pm_config = json.load(f)
        pm_config_list = pm_config["physicalMachines"]

    # Connect to remote PMs
    remote_pms = connect_remote_machines(pm_config_list)