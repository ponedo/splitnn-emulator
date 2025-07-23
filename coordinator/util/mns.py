import math
from .topo_util import *
from .common import count_lines_islice

def get_bbns_num_for_all_vms(topo, pm_config_list, vm_config_list, FIXED_BBNS_NUM):
    serverid2bbnsnum = {}
    for server_id, vm_config in enumerate(vm_config_list):
        pm_id = vm_config["physicalMachineId"]
        pm_config = pm_config_list[pm_id]
        X = pm_config["Parameters"]["X"]
        Y = pm_config["Parameters"]["Y"]

        sub_topo_filename = get_sub_topo_filename(topo, server_id)
        sub_topo_filepath = os.path.join(LOCAL_TOPO_DIR, sub_topo_filename)
        line_num = count_lines_islice(sub_topo_filepath)
        link_num = line_num - 1

        if FIXED_BBNS_NUM == 0:
            k_opt = math.sqrt((link_num * Y) / (2 * X))
            serverid2bbnsnum[server_id] = math.ceil(k_opt)
        else:
            serverid2bbnsnum[server_id] = math.ceil(min(link_num, FIXED_BBNS_NUM))

    return serverid2bbnsnum