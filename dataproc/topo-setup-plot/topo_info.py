def get_chain_node_num(n):
    return n

def get_chain_link_num(n):
    return n - 1

def get_star_node_num(n):
    return n

def get_star_link_num(n):
    return n - 1

def get_fullmesh_node_num(n):
    return n

def get_fullmesh_link_num(n):
    return n * (n - 1) / 2

def get_trie_node_num(n, k):
    return n

def get_trie_link_num(n, k):
    return n - 1

def get_grid_node_num(x, y):
    return x * y

def get_grid_link_num(x, y):
    return 2 * x * y

def get_clos_node_num(k):
    return int((5 / 4) * (k ** 2) + (k ** 3) / 4)

def get_clos_link_num(k):
    pod_num = k
    superspine_num = (k // 2) ** 2
    spine_num = (k // 2) * pod_num
    leaf_num = (k // 2) * pod_num
    client_num = leaf_num * k
    link_num = ((superspine_num + spine_num + leaf_num) * k + client_num) / 2
    return link_num

topo_funcs = {
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
}
