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
