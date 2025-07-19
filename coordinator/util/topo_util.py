import os
import json
import subprocess

COORDINATOR_WORKDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
AS_DATA_DIR = os.path.join(COORDINATOR_WORKDIR, "data")
AS_TOPO_CONFIG_FILEPATH = os.path.join(AS_DATA_DIR, "as_topo_config.json")
LOCAL_TOPO_DIR = os.path.join(COORDINATOR_WORKDIR, "topo")


##################################
# Scripts to generate topologies #
##################################

def get_full_topo_filename(topo_args):
    return f"{'_'.join(topo_args)}.txt"

def get_sub_topo_filename(topo_args, i):
    full_topo_filename = get_full_topo_filename(topo_args)
    splited_topo_filename = full_topo_filename.split('.')
    if len(splited_topo_filename) == 1:
        splited_sub_topo_filename = splited_topo_filename + [f"sub{i}"] # without .txt suffix
    else:
        splited_sub_topo_filename = splited_topo_filename[:-1] + [f"sub{i}"] + splited_topo_filename[-1:] # with .txt suffix
    sub_topo_filename = '.'.join(splited_sub_topo_filename)
    return sub_topo_filename

def generate_topo(topo, output_dir):
    topo_type = topo[0]
    full_topo_filename = get_full_topo_filename(topo)
    full_topo_filepath = os.path.join(output_dir, full_topo_filename)
    generate_topo_type_script_path = os.path.join(COORDINATOR_WORKDIR, "scripts", "topo", f"generate_{topo_type}_topo.py")
    try:
        generate_topology_cmd = \
            ["python3", generate_topo_type_script_path] + topo[1:] + [full_topo_filepath]
    except IndexError:
        generate_topology_cmd = \
            ["python3", generate_topo_type_script_path, full_topo_filepath]
    result = subprocess.run(generate_topology_cmd, capture_output=True, text=True)
    return full_topo_filepath


###################################################################
# Functions to get node and link numbers for different topologies #
###################################################################

def get_isolated_node_num(n):
    n = int(n)
    return int(n)

def get_isolated_link_num(n):
    n = int(n)
    return int(0)

def get_sudoisolated_node_num(l, n):
    l, n = int(l, n)
    return int(n + 2)

def get_sudoisolated_link_num(l, n):
    l, n = int(l, n)
    return int(l)

def get_pairs_node_num(n):
    n = int(n)
    return int(2 * n)

def get_pairs_link_num(n):
    n = int(n)
    return int(n)

def get_chain_node_num(n):
    n = int(n)
    return int(n)

def get_chain_link_num(n):
    n = int(n)
    return int(n - 1)

def get_star_node_num(n):
    n = int(n)
    return int(n)

def get_star_link_num(n):
    n = int(n)
    return int(n - 1)

def get_fullmesh_node_num(n):
    n = int(n)
    return int(n)

def get_fullmesh_link_num(n):
    n = int(n)
    return int(n * (n - 1) / 2)

def get_trie_node_num(n, k):
    n, k = int(n), int(k)
    return int(n)

def get_trie_link_num(n, k):
    n, k = int(n), int(k)
    return int(n - 1)

def get_grid_node_num(x, y):
    x, y = int(x), int(y)
    return int(x * y)

def get_grid_link_num(x, y):
    x, y = int(x), int(y)
    return int(2 * x * y)

def get_clos_node_num(k):
    k = int(k)
    return int((5 / 4) * (k ** 2) + (k ** 3) / 4)

def get_clos_link_num(k):
    k = int(k)
    pod_num = k
    superspine_num = (k // 2) ** 2
    spine_num = (k // 2) * pod_num
    leaf_num = (k // 2) * pod_num
    client_num = leaf_num * k
    link_num = ((superspine_num + spine_num + leaf_num) * k + client_num) / 2
    return int(link_num)

def get_as_node_num(size):
    with open(AS_TOPO_CONFIG_FILEPATH, 'r') as f:
        as_topo_config = json.load(f)
    try:
        src_filepath = os.path.join(AS_DATA_DIR, as_topo_config[size])
    except KeyError:
        print(f"Invalid size: {size}")
        exit(1)
    with open(src_filepath, 'r') as f:
        first_line = f.readline().strip()
        node_num = len(first_line.split())
    return node_num

def get_as_link_num(size):
    with open(AS_TOPO_CONFIG_FILEPATH, 'r') as f:
        as_topo_config = json.load(f)
    try:
        src_filepath = os.path.join(AS_DATA_DIR, as_topo_config[size])
    except KeyError:
        print(f"Invalid size: {size}")
        exit(1)
    with open(src_filepath, 'r') as f:
        line_num = 0
        for line in f:
            line_num += 1
    link_num = line_num - 1
    return link_num

topo_funcs = {
    "isolated": {
        "get_node_num": get_isolated_node_num,
        "get_link_num": get_isolated_link_num,
    },
    "sudoisolated": {
        "get_node_num": get_sudoisolated_node_num,
        "get_link_num": get_sudoisolated_link_num,
    },
    "pairs": {
        "get_node_num": get_pairs_node_num,
        "get_link_num": get_pairs_link_num,
    },
    "chain": {
        "get_node_num": get_chain_node_num,
        "get_link_num": get_chain_link_num,
    },
    "star": {
        "get_node_num": get_star_node_num,
        "get_link_num": get_star_link_num,
    },
    "fullmesh": {
        "get_node_num": get_fullmesh_node_num,
        "get_link_num": get_fullmesh_link_num,
    },
    "trie": {
        "get_node_num": get_trie_node_num,
        "get_link_num": get_trie_link_num,
    },
    "grid": {
        "get_node_num": get_grid_node_num,
        "get_link_num": get_grid_link_num,
    },
    "clos": {
        "get_node_num": get_clos_node_num,
        "get_link_num": get_clos_link_num,
    },
    "as": {
        "get_node_num": get_as_node_num,
        "get_link_num": get_as_link_num,
    },
}
