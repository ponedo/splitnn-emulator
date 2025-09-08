# Setup and run experiment

This document illustrates how to configure an experiment before its running. Before going ahead, the steps in [setup cluster tutorial](./setup_cluster.md) and [setup coordinator tutorial](./setup_coordinator.md) should be finished.

The core of coordinator is the python program [test.py](../coordinator/test.py), which
1. parses input configurations
2. construct worker VMs across physical machines
3. distribute configurations (topologies, IP addresses of VMs, container images, etc.) to agents across all worker VMs
4. let worker VMs to execute VN construction (vnodes and vlinks)
5. collect experiment results
6. clean VMs after experiment

To run the program, please follow the instructions below:

## 1. Configure experiment options
In the master VM, configure the [exp_config.json](../coordinator/config/exp_config.json) for the coordinator

```bash
cd /path/to/repository
cd coordinator/config
vim exp_config.json # Write according to the exp_config.json contents shown below
```

```json
{
    "VMuser": "cnic", // Login users for all worker VMs
    "VMpassword": "thisisapassword", // Password users for all worker VMs
    "VMphyIntf": "enp1s0", // The interface that each worker VM uses to connect to other VMs
    "VMagentWorkDir": "/home/cnic/splitnn/agent", // The agent subdirectory path in repository within each worker VM
    "dockerImageName": "ponedo/frr-ubuntu20", // The docker image used for virtual node construction
    "MemoryReq(GB)": 500, // Anticipated memory usage of ALL vnodes and vlinks across all VMs
    "CrossPMPartitioning": "metis", // Cross-PM topology partitioning method (allowed: naive, metis, tbs)
    /* (Can be ignored) Monitored kernel functions at experiment runtime */
    "kernFuncsToMonitor":  [
        ["setup", "cctr", "chroot_fs_refs"],
        ["setup", "splitnn_agent", "wireless_nlevent_flush"],
        ["setup", "splitnn_agent", "fib6_clean_tree"],
        ["clean", "", "br_vlan_flush"]
    ]
}
```

## 2. Configure topologies to run

The topologies to be constructed is configured in [test.py](../coordinator/test.py)

```python
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
    ...
}
```

Just uncomment topology entries you want to test. Currently, just ignore other options in `var_options`.

## 3. Run the experiments

After configuring topologies, execute the command below to run experiments
```bash
cd /path/to/repository
cd coordinator
# Since the experiments can take very long time, we recommand execute the command below with a "screen" or "tmux" envrionment
python -u test.py
```

During execution of `test.py`, logs and outputs will be placed under the directory `/path/to/repository/coordinator/raw_results`.

NOTE: if the experiment exit abnormally, please clean the VMs on your physical machines manually! To do this, on each physical machine, execute:
```bash
cd /path/to/vm_manager
./vm_operator/operate_vm.sh destroy <VM_NUM>
```
