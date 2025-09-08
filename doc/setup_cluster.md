# Setting the Cluster

This document illustrates how to setup the environment on each physical machine to run our SplitNN emulator.

Before going ahead, we assume that following conditions are satisfied:

+ You have SSH access to at least one physical machine where you deploy the VM cluster.
+ Physical machines are mutually Layer-3 reachable.
+ KVM is avalabibe on all physical machines.
+ KVM uses bridge mode to provide network connection for all VMs.

## 1. Preparing the VM image

The first step is to prepare the VM image of worker VMs and agent VMs. The image should be in *.qcow2* disk format, with its path configured as the `BACKING_DISK` field in the [config file of vm_manager](../vm_manager/vm_config.sh). 

To get the *.qcow2* disk. We provide two options: (1) using the out-of-the-box image; (2) build an image from the scratch.

### 1.1 Using the out-of-the-box image (Recommended)

We provide out-of-the-box *.qcow2* disk at links below:

+ For AMD64 platform: download [here](https://pan.baidu.com/s/1NndHBaLWU-fMK8Pdq0eedQ?pwd=hdqf).

+ For ARM64 platform: downlodd [here](https://pan.baidu.com/s/1N-uPtPny88C-JMAFFQPZ-w?pwd=hixx).

After downloading, put the downloaded .qcow2 file at /var/lib/libvirt/images/.

### 1.2 Build an image from the scratch (Optional)

To build a new image, please CAREFULLY with following steps to setup your environment:

1. Prepare a runnable VM on your physical machine. If you don't have an available VM on your physical machine, you can create new one. First, download the .iso image from [this link](https://ubuntu.com/download/desktop). Then, create the new VM using the command:

    ```bash
    virt-install --name ${VM_NAME} \
    --ram ${RAM_SIZE} --vcpus ${VCPU_NUM} \
    --disk path=/var/lib/libvirt/images/myvm.qcow2,size=20 \
    --cdrom /path/to/ubuntu.iso
    --network bridge=${BRIDGE_IF},model=virtio,mac=${MAC_ADDRESS} \
    --os-variant ${OS_VARIANT} \
    --import --noreboot --noautoconsole
    ```

2. Enter your running VM.

3. Git clone this repo in the VMs.

    ```bash
    git clone <url_to_this_repository>
    ```

4. **(Important)** Setup an SSH key on the VM:
    ```bash
    # If any confirmation needed, press ENTER (use default configuration)
    ssh-keygen -t ed25519 -C "your_email@example.com"
    ```
    This step enables automatic SSH communication between VMs. Once configured SSH keys, please execute the following commnand on master VM for all slave VMs to check whether password-free communication is enabled:

    ```bash
    # When executing this command on the master, an interactive prompt requesting password should NOT come out!
    ssh ${USER}@${SLAVE_VM_IP} 'echo hello'
    ```

5. Install Docker engine in the VM.

    ```bash
    wget -O install_docker.sh https://get.docker.com/
    ./install_docker.sh
    ```

6. Pull the docker image configured in server_config.json on all slave VMs.

    ```bash
    docker pull harbor.fir.ac.cn/ponedo/frr-ubuntu20@sha256:1a1405893f98218d661094c8bcd9ea0cb6215be89540f2a12d3b3a3a5d340c87
    docker tag harbor.fir.ac.cn/ponedo/frr-ubuntu20 ponedo/frr-ubuntu20
    ```

7. Setup a python virtual enviroment and install python dependencies on the master VM with following commands:
    ```bash
    cd /path/to/repository
    python -m venv tstenv
    source tstenv/bin/activate
    pip install -r requirements.txt
    ```
    Operations on the master VM should be executed in this virtual environment

8. Install dependencies of METIS topology partitioning:

    8.1 Install [GKlib](https://github.com/KarypisLab/GKlib):

    ```bash
    git clone https://github.com/KarypisLab/GKlib.git
    cd GKlib
    # For x86 platform
    make config prefix=~/local CONFIG_FLAGS='-D BUILD_SHARED_LIBS=ON'
    # For ARM platform
    make config prefix=~/local CONFIG_FLAGS='-D BUILD_SHARED_LIBS=ON -D NO_X86=1'
    make
    make install
    ```

    8.2 Install [METIS](https://github.com/KarypisLab/METIS):

    ```bash
    git clone https://github.com/KarypisLab/METIS.git
    cd METIS
    sed -i '/add_library(metis ${METIS_LIBRARY_TYPE} ${metis_sources})/ s/$/\ntarget_link_libraries(metis GKlib)/' libmetis/CMakeLists.txt
    sed -i '/^CONFIG_FLAGS \?= / s,$, -DCMAKE_BUILD_RPATH=/usr/local/lib -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON,' Makefile
    make config shared=1 cc=gcc prefix=~/local gklib_path=/usr/local
    make install
    echo 'export METIS_DLL=~/local/lib/libmetis.so' >> ~/.bashrc
    source ~/.bashrc
    ```

9. Install dependencies of TBR-TBS (If you find this step diffcult to setup, you can skip this. But you cannot use TBS algorithm as multi-machine partitiong method in experiments):

    9.1 Clone and compile a modified version of [TBR-TBS](https://github.com/ponedo/tbs):
    ```bash
    git clone git@github.com:ponedo/tbs.git
    cd tbs
    mkdir build
    cd build
    cmake .. && make
    ```

    9.2 Install Gurobi optimizer, which is a necessary dependency of [TBR-TBS](https://github.com/tbs2022/tbs) topoology partitioning algorithm. Please install a *full-licensed* Gurobi optimizer (Please find help at [How do I install Gurobi Optimizer?](https://support.gurobi.com/hc/en-us/articles/4534161999889-How-do-I-install-Gurobi-Optimizer)).

    9.3 Modify the hardcoded path in the [python code](../coordinator/util/mvs/partition/algorithm.py)

    ```python
    TBS_BIN_DIR = "/path/to/tbs/build"
    ```

## 2. Preparing the NVRAM files

Cuurently, we found it is also necessary to provide NVRAM files for VMs on ARM platforms. If you are using the out-of-the-box ARM64 .qcow2 disk, please download the corresponding NVRAM file from [this link](https://pan.baidu.com/s/1gAb4nz--SVt4WYoCPkolXw?pwd=9cyx). Please place this file at */var/lib/libvirt/qemu/nvram/base-ubuntu22-vm-arm_VARS.template.fd* on your physical machine. This path should be configured as the `BACKING_NVRAM` field in the [config file of vm_manager](../vm_manager/vm_config.sh). 

## 3. Configure the VM manager on physical machine

On your physical machine, clone the code of VM manager at a certain path (say /path/to/vm_manager):
```bash
git clone <url_to_this_repository>
cp splitnn/vm_manager /path/to/vm_manager
```

Modify the configuration of the VM manager
```bash
vim /path/to/vm_manager/vm_config.sh # Modify contents on demand
```

The explanation of all configurable fields are written in the vm_config.sh as comments. Please read them carefully. You can set VM network configuration on demand, as long as the master VM can reach the subnet of worker VMs. Note that if you put master VM and worker VMs in same subnet, please avoid accidential conflict of IP addresses between master VM and worker VMs. We recommend assign the master VM with *".2"* address, and set VM_IP_OFFSET with 4, which will assign worker VMs with *".4"*, *".6* , *".8"*... addresses.

Example: suppose you are assigning master VM with `192.168.1.2`, and wish to assign worker VMs with `192.168.1.4`, `192.168.1.6`, `192.168.1.8`... configure as:
```bash
VM_PREFIX="splitnn-vm"
BRIDGE_IF="br1" # Bridge interface for VM networking, other example: BRIDGE_IF="reals-vm-br"
RAW_VIRTIO_IP_PREFIX="192.168.1." # The subnet for the VMs
SUBNET_MASK="16" # The subnet mask length for the VMs
RAW_MAC_PREFIX="52:54:00:ab:73:" # The MAC address prefix for the VMs
DNS="159.226.8.7" # The DNS server for the VMs
GATEWAY="192.168.1.1" # The network gateway for the VMs

# The IP address of the i-th VM is calculated as:
# VM_IP = RAW_VIRTIO_IP_PREFIX :: (i * 2 + VM_IP_OFFSET)
# Be aware that VM_IP of the "MAX_VM_NUM"-th VM should not exceed 255!!!!!
VM_IP_OFFSET=4
```

## 3. Define the VMs on physical machine
After configuring the VM manager, it is time to define the VMs (create a VM pool) on the physical machine:
```bash
cd /path/to/vm_manager/
./vm_definer/define_vm.sh
```

If the VM pool is no longer needed, you can undefine the VMs by commands below:
```bash
cd /path/to/vm_manager/
./vm_definer/undefine_vm.sh
```

## 4. Configure multiple physical machines in one cluster (Optional)

If you are using a multi-machine cluster, please execute step 3 for each physical machine.

## 5. Measure the θ(*m*) parameter

The VM manager can be run in an independent *measuring mode*. This is used for measuring the paremeter θ(*m*), which represents extra memory overhead of a VM configured with maximum memory of *m*.

To measure θ(*m*), run:
```bash
cd /path/to/vm_manager
./vm_opearator/measure.sh > measure.log
```

This command will output memory cost of different number of VMs configured with certain *m*. 

Example output:
```
vm_num: 1 | mem_value(KiB): 8000000 | mem_cost(KiB): 1000000
vm_num: 2 | mem_value(KiB): 8000000 | mem_cost(KiB): 2000001
vm_num: 3 | mem_value(KiB): 8000000 | mem_cost(KiB): 2999999
```
This output memory cost of different number of VMs configured with certain `*m*=8GB`. Then, a linear regression can be performed with (vm_num, mem_cost) samples, which leads to `θ(*m*) ~= 1GB` for `*m*=8GB`.
