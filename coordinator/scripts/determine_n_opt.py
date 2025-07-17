# Determine the best VM number for multi-VM splitting based on modeling data
import argparse
import csv
import os
import math

########################### Arguments ###########################
parser = argparse.ArgumentParser(description='A script to calculate optimal VM number n_opt for multi-VM splitting')
parser.add_argument('-p', '--platform', type=str, required=True, help='Platform type (amd64 or arm64)')
parser.add_argument('-E', '--E-max-filepath', type=str, required=True, help='Path to the E_max data file')
parser.add_argument('-m', '--m-req', type=int, required=True, help='Total memory required for the emulation (GB)')
parser.add_argument('-M', '--m-platform', type=int, required=True, help='Available memory on the platform (GB)')
parser.add_argument('-s', '--over-subscription', type=float, required=True, help='Maximum over-subscription ratio')
parser.add_argument('-g', '--gain-type', type=str, required=True, choices=['gain1', 'gain2'], help='Type of gain to optimize for')

args = parser.parse_args()

platform = args.platform # 'amd64' or 'arm64'
E_max_filepath = args.E_max_filepath
m_req = args.m_req
m_platform = args.m_platform
over_subscription = args.over_subscription
gain_type = args.gain_type

if platform not in ["amd64", "arm64"]:
    raise ValueError("Platform must be either 'amd64' or 'arm64'.")

############################# Parameters Table ###########################

para_table = {
    "theta_m_conf": { # Unit: GB
        "amd64": {
            8: 2.814,
            25: 3.190,
            50: 3.746,
            100: 4.820,
            200: 7.009,
            300: 8.857,
            400: 10.590,
            500: 10.942,
        },
        "arm64": {
            8: 1.642,
            25: 1.934,
            50: 2.360,
            100: 3.251,
            200: 5.118,
            300: 6.890,
            400: 8.722,
            500: 10.535,
        }
    },
    "X": {
        "amd64": 0.00329,  # Example value, adjust as needed
        "arm64": 0.00931,  # Example value, adjust as needed
    },
    "Y": {
        "amd64": 0.03918,  # Example value, adjust as needed
        "arm64": 0.02624,  # Example value, adjust as needed
    },
    "Z": {
        "amd64": 0.0127,  # Example value, adjust as needed
        "arm64": 0.0037,  # Example value, adjust as needed
    }
}

topos = {
    "grid": (10000, 20000),
    "clos": (9472, 24576),
    "as": (12817, 36234),
}

V_avg = sum(topo[0] for topo in topos.values()) / len(topos)
X = para_table["X"][platform]
Y = para_table["Y"][platform]
Z = para_table["Z"][platform]
search_n_range = range(2, 129)  # Range of n to search for optimal value
search_m_conf_range = [8, 25, 50, 100, 200, 300, 400, 500]  # Range of m_conf to search for optimal value

############################## Functions to Compute Gain ###########################

def read_E_max_data():
    # This function should read the E_max modeling data from a file or database
    # For now, we will just return a placeholder value
    topo_e_max_data = {}
    avg_e_max_data = []

    topo_results_hint = "Results averaged across runs:"
    avg_result_hint = "Results averaged across runs and topos: "
    sep_line = "--------------------"

    in_topo_results = False

    with open(E_max_filepath, 'r') as f:
        # Find the line starting with the hints
        # After the hint there should be a list of E_max values, wrapped with square brackets,
        # e.g., "Results averaged across runs and topos: [10000, 9998, 9996, ...]"
        for line in f:
            if in_topo_results:
                if line.startswith(sep_line):
                    in_topo_results = False
                    continue
                # Extract the string after the hint
                splited_line = line.split(": ")
                topo = splited_line[0].strip()
                topo_e_max_str = splited_line[1].strip()
                # Convert the string to a list of integers
                topo_e_max_data[topo] = eval(topo_e_max_str)
                continue
            if line.startswith(topo_results_hint):
                in_topo_results = True
                continue
            if line.startswith(avg_result_hint):
                # Extract the string after the hint
                avg_e_max_str = line.split(avg_result_hint)[1].strip()
                # Convert the string to a list of integers
                avg_e_max_data = eval(avg_e_max_str)
                break
                
    # If the file does not contain the expected line, return a default value
    return topo_e_max_data, avg_e_max_data

topo_e_max_data, avg_e_max_data = read_E_max_data()  # Placeholder function to read E_max data

def avg_E_max(n):
    return avg_e_max_data[n-1] if 1 <= n <= len(avg_e_max_data) else None

def topo_E_max(n, topo):
    return topo_e_max_data[topo][n-1] if topo in topo_e_max_data and 1 <= n <= len(topo_e_max_data[topo]) else None

def compute_T_mvs(n, topo):
    # Compute T_mvs based on E_max
    topo_E_max_n = topo_E_max(n, topo)
    topo_V = topos[topo][0]
    T_mvs_n = topo_E_max_n * (topo_V / n * X + Z) + topo_E_max_n ** 2 * Y / 2
    return T_mvs_n
T_mvs = lambda n, topo: compute_T_mvs(n, topo)

def compute_M_mvs(n, m_conf):
    theta_m_conf = para_table["theta_m_conf"][platform][m_conf]
    return n * theta_m_conf
M_mvs = lambda n, m_conf: compute_M_mvs(n, m_conf)

def compute_T_sn(n, topo):
    # Compute T_sn based on E_max
    topo_V = topos[topo][0]
    topo_E_max_n = topo_E_max(n, topo)
    T_sn_n_topo = topo_E_max_n * (topo_V / n * X + Z) + topo_E_max_n * math.sqrt(2 * topo_E_max_n * X * Y)
    return T_sn_n_topo
T_sn = lambda n, topo: compute_T_sn(n, topo)

def compute_gain1(n, m_conf, topo):
    numerator = (T_mvs(1, topo) - T_mvs(n, topo)) / T_mvs(1, topo)
    dominator = M_mvs(n, m_conf) / m_req
    gain1 = numerator / dominator
    return gain1
Gain1 = lambda n, m_conf, topo: compute_gain1(n, m_conf, topo)

def compute_gain2(n, m_conf, topo):
    numerator = (T_sn(1, topo) - T_sn(n, topo)) / T_sn(1, topo)
    dominator = M_mvs(n, m_conf) / m_req
    gain2 = numerator / dominator
    return gain2
Gain2 = lambda n, m_conf, topo: compute_gain2(n, m_conf, topo)

if gain_type == 'gain1':
    Gain = Gain1
elif gain_type == 'gain2':
    Gain = Gain2
else:
    raise ValueError("Invalid gain type. Use 'gain1' or 'gain2'.")

def search_n_opt_and_m_conf_for_topo(gain_type, topo):
    # Search for the optimal n and m_conf value that maximizes Gain1
    # Constraint: n * m_conf >= m_req
    n_opt = 1
    m_conf_opt = 8
    m_extra_opt = n_opt * para_table["theta_m_conf"][platform][m_conf_opt]
    max_gain = Gain(n_opt, m_conf_opt, topo)
    # Store all search results
    search_results = []
    for n in search_n_range:
        for m_conf in search_m_conf_range:
            if n * m_conf < m_req or n * m_conf > m_platform * over_subscription:
                continue
            gain = Gain(n, m_conf, topo)
            theta_m_conf = para_table["theta_m_conf"][platform][m_conf]
            m_extra = n * theta_m_conf
            if gain > max_gain:
                max_gain = gain
                n_opt = n
                m_conf_opt = m_conf
                m_extra_opt = m_extra
            search_results.append((n, m_conf, m_extra, gain))
    optimal_result = (n_opt, m_conf_opt, m_extra_opt, max_gain)
    return search_results, optimal_result

def search_n_opt_and_m_conf(gain_type):
    search_results = {}
    optimal_results = {}
    for topo in topos:
        topo_search_results, topo_optimal_result = \
            search_n_opt_and_m_conf_for_topo(gain_type, topo)
        search_results[topo] = topo_search_results
        optimal_results[topo] = topo_optimal_result
    return search_results, optimal_results

def output_results(search_results, gain_type):
    # Output the optimal n and m_conf for each topology to a csv file into separate files
    output_dir = os.path.dirname(E_max_filepath)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for topo in topos:
        output_filepath = os.path.join(output_dir, f"{gain_type}_result_{topo}_{platform}.csv")
        with open(output_filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["n", "m_conf", "m_extra", "Gain"])
            for n, m_conf, m_extra, gain in search_results[topo]:
                # Only keep two decimal places for m_extra and gain
                m_extra = round(m_extra, 2)
                gain = round(gain, 2)
                writer.writerow([n, m_conf, m_extra, gain])
    # output_filepath = os.path.join(output_dir, f"{gain_type}_result_{platform}.csv")
    # with open(output_filepath, 'w', newline='') as csvfile:
    #     writer = csv.writer(csvfile)
    #     writer.writerow(["n", "m_conf", "m_extra", "Gain"])
    #     for n, m_conf, m_extra, gain in search_results:
    #         # Only keep two decimal places for m_extra and gain
    #         m_extra = round(m_extra, 2)
    #         gain = round(gain, 2)
    #         writer.writerow([n, m_conf, m_extra, gain])

####################################################################################

if __name__ == "__main__":
    # Read E_max modeling data
    E_max_data = read_E_max_data()

    # Compute the optimal n and m_conf for each topology
    search_results, optimal_results = search_n_opt_and_m_conf(args.gain_type)

    # Print the search results for each topology
    for topo, results in search_results.items():
        print(f"\nSearch Results for {topo} (sorted by Gain):")
        results.sort(key=lambda x: x[3], reverse=True)
        for n, m_conf, m_extra, gain in results:
            print(f"n: {n}\tm_conf: {m_conf}\tm_extra: {m_extra:.2f}\tGain: {gain:.4f}")

        # Print the optimal n and m_conf for this topology
        n_opt, m_conf_opt, m_extra_opt, max_gain2 = optimal_results[topo]
        print(f"Optimal n for {topo}: {n_opt}\tOptimal m_conf: {m_conf_opt}\tm_extra: {m_extra_opt:.2f}\tMaximum Gain: {max_gain2:.4f}")

    # Output the results to a csv file
    output_results(search_results, args.gain_type)
