# Code of SplitNN

## 1. Overview

SplitNN is a new methodological framework that enables fast construction of large-scale virtual networks (VNs) for network emulation. SplitNN leverages two "splitting" methods on a physical machine to accelerate VN construction:

1. *Multi-VM splitting*: to address the serialization bottleneck, SplitNN creates multiple VMs on a single machine and distributes the VN across them, allowing independent kernel instances to handle vlink operations in parallel.

2. *Multi-netns splitting*: to reduce the notifier chain overhead, SplitNN further distributes vlinks of each sub-VN into multiple backbone network namespaces within each VM, reducing the number of devices a BBNS carries, thereby lowering the device traversal overhead during vlink construction.

With multi-VM splitting and multi-netns splitting architecture, construction of 10K-node VNs can be done within minute-level time-cost.

## 2. Project Structure

The project contains following directories:

1. vm_manager: a series of shell scripts that start/destroy VMs, as well as configuring settings of VMs (such as CPU/Memory).

2. coordinator: a python program run by the master VM that (1) distribute topology infomation and reap VN construction/destruction time-costs from slave VMs; (2) manage experiment workflow.

3. agent: a Golang project that construct/destruct virtual networks on a slave VM. 

4. dataproc: a python program that output tables and figures with experimental results (just ignore it if you feel it hard to use).

## 3. How To Run the Project

Running the project include following steps:

1. [Setup cluster](doc/setup_cluster.md);

2. [Setup the coordinator](doc/setup_coordinator.md);

3. [Setup and run experiments](doc/setup_experiment.md);

## Usage

### Run VN construction/destruction experiements

1. On the master VM (1) change into "coordinator" directory; (2) switch into "tstenv" python virtual environment.

2. **(Important)** Switch into "rigid" branch (dedicated branch for experiments) of this repository:

    ```bash
    git checkout rigid
    ```

3. Modify the "coordinator/batch_test.py" script on demand:

    3.1. For uni-BBNS experiments, set USE_BEST_BBNS_NUM to False, and set BBNS number to 1.

    ```python
    SERVER_BBNS_NUM_TEST = False
    USE_BEST_BBNS_NUM = False
    ```

    ```python
    "b": [
        1 # Use only one backbone namespace
    ],
    ```

    3.2. For multi-BBNS experiments: if you want to test VN construction/destruction time-cost under different BBNS number (factors of vlink number), set like below:
    ```python
    SERVER_BBNS_NUM_TEST = True
    USE_BEST_BBNS_NUM = False
    ```

    if you want to test with optimal BBNS number, set like below:
    ```python
    SERVER_BBNS_NUM_TEST = False
    USE_BEST_BBNS_NUM = True
    ```
    
    if you want to test with some specific BBNS number, set like below:
    ```python
    SERVER_BBNS_NUM_TEST = False
    USE_BEST_BBNS_NUM = False
    
    "b": [
        1,
        2,
        4,
        #...
    ],
    ```

    3.3. ***Uncomment*** lines of topologies you want to test, where "grid", "clos", and "as" represents "+Grid", "Fattree", and "BGP AS" topologies in our paper:
    ```python
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

    # ["clos", "8"],
    # ["clos", "12"],
    # ["clos", "16"],
    # ["clos", "20"],
    # ["clos", "24"],
    # ["clos", "28"],
    # ["clos", "32"],
    
    # ["as", "small"],
    # ["as", "medium"],
    # ["as", "large"],
    ```

4. Run the batch_test.py script:
    ```bash
    cd /path/to/repository
    source tstenv/bin/activate
    cd coordinator
    python -u batch_test.py > batch_test_log
    ```
    Results will be placed at the directory "coordinator/raw_results/result-XX-servers", in which VN construction/destruction time will be shown in setup_log.txt/clean_log.txt with "Operation time" entry.

### Measuring platform-specific parameters

1. Prepare code and executable files for measurement:

    ```bash
    cd /path/to/repository
    git checkout measure
    cd agent
    make
    ```

2. Modify agent/server_config. Set only one slave VM (recommend using master VM as the slave for measurement)
