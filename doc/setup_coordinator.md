# Setting up the Coordinator

This document illustrates how to setup a master VM and the coordinator in it. Before going ahead, the steps in [setup cluster tutorial](./setup_cluster.md) should be finished.

## 1. Start the master VM

On any physical machine in your cluster, start a master VM using the command below (for example):
```bash
RAM=8000000 # 8GB memory for master VM
MAX_VCPUS=4 # 4 CPUs for master VM
VM_NAME=splitnn_master # VM name of the master VM
MASTER_IP=192.168.1.2 # IP address of the master VM
MASTER_IP_MASK=24 # IP address mask of the master VM
MASTER_GATEWAY=192.168.1.1 # Gateway of the master VM, which should be able to access public network
MASTER_DNS=159.226.8.7 # The DNS server master VM uses
BRIDGE_IF=br1 # By default, we use bridge mode network in KVM to connect master VM to public network

virt-install --name ${VM_NAME} \
--ram ${RAM} --vcpus ${MAX_VCPUS} \
--disk path=/path/to/qcow2,format=qcow2 \
--network bridge=${BRIDGE_IF},model=virtio \
--os-variant ${OS_VARIANT} \
# If a downloaded NVRAM file (mentioned in [#2 in setup cluster tutorial], uncommenent the following lind
# --boot uefi,nvram=/path/to/nvram \
--import --noreboot --noautoconsole

cat << EOF > /tmp/00-installer-config.yaml
network:
  version: 2
  ethernets:
    enp1s0:
      dhcp4: false
      addresses:
        - ${MASTER_IP}/${MASTER_IP_MASK}
      routes:
        - to: default
          via: ${MASTER_GATEWAY}
      nameservers:
        addresses:
          - ${MASTER_DNS}
EOF

  echo "Copying Netplan configuration to ${VM_NAME}..."
  virt-copy-in -d ${VM_NAME} /tmp/00-installer-config.yaml /etc/netplan/
  rm /tmp/00-installer-config.yaml
```

where `/path/to/qcow2` is the path to the .qcow2 VM disk file mentioned in [setup cluster tutorial](./setup_cluster.md#1-preparing-the-vm-image)

## 2. Pull the repository in master VM
First, enter the master VM.

If you are using the .qcow2 downloaded from our links [setup cluster tutorial](./setup_cluster.md#11-using-the-out-of-the-box-image-recommended). The default login user is `cnic` and the login password is `thisisapassword`

Then, pull the repository:
```bash
# Run commands below in the master VM
cd /path/to/repository_parent_dir
git clone <url_to_this_repository>
```

## 3. Install python dependencies of coordinator
```bash
cd /path/to/repository
python -m venv tstenv
source tstenv/bin/activate
pip install -r requirements.txt
```

## 4. Build the agent, Measure the parameters

1. Build the agent executable file
    ```bash
    cd /path/to/repository
    cd agent
    make
    ```
    We will use the measurement mode of agent to measure parameters X, Y, and Z mentioned in paper for this physical machine.

2. Modify server_config.json
    The agent program need an input config file at runtime:
    ```bash
    cd /path/to/repository
    cd agent
    vim server_config.json # Write the json contents shown below
    ```

    ```json
    {
        "servers": [
            {
                "ipAddr": "10.10.30.148", // IP addresss of this master VM
                "user": "cnic", // Login user of the master VM
                "password": "thisisapassword", // Password of the master VM
                "phyIntf": "enp1s0", // The interface master VM uses to access
                "agentWorkDir": "/path/to/repository/agent", // The working directory of agent
                "dockerImageName": "ponedo/frr-ubuntu20:tinycmd",
                "kernFuncsToMonitor":  [
                    ["setup", "cctr", "chroot_fs_refs"],
                    ["setup", "topo_setup_test", "wireless_nlevent_flush"],
                    ["setup", "topo_setup_test", "fib6_clean_tree"],
                    ["clean", "", "br_vlan_flush"]
                ],
                "physicalMachineId": 0
            }
        ]
    }
    ```

32. Execute measurement for parameter *X* (increasing rate of vlink construction time w.r.t. the number of system-wide netns’es):
    ```bash
    bin/splitnn_agent -o node-measure -P 10000 -Q 1250 -S 9 -N cctr -l ntlbr -s server_config.json
    ```
    the results will be written in agent/tmp/node-measure_log.txt.

4. Execute measurement for parameter *Y* (ncreasing rate of per-vlink construction time with respect to the pre-existing vlink number in the BBNS that carries the vlink.):
    ```bash
    bin/splitnn_agent -o link-measure -P 10000 -Q 1250 -S 9 -N cctr -l ntlbr -s server_config.json
    ```
    the results will be written in agent/tmp/link-measure_log.txt.


## 5. Configure information of physical machines
The master VM should be able to connect to all physical machines in your network emulation cluster. To let the master VM connect to them, the [pm_config.json](../coordinator/config/pm_config.json) should be configured as follows:
```json
{
    "physicalMachines": [
        {
            "ipAddr": "192.168.1.30", // IP address of the physical machine
            "user": "root", // Login user (need to be a privileged user, using "root" is recommended)
            "password": "thisisapassword", // Login password
            "vmManagerWorkDir": "/path/to/vm_manager", // The path to vm_manager directory on the physical machine
            "maxVMNum": 30, // Max VM number that can be created on this physical machine
            "coreNum": 128, // Available core number on this physcial machine
            "Memory": 968, // Available RAM on this physical machine
            "Parameters": {
                /* Measured theta(m) parameters on the physical machine*/
                "theta_m_table": {
                    "8": 2.814,
                    "25": 3.190,
                    "50": 3.746,
                    "100": 4.820,
                    "200": 7.009,
                    "300": 8.857,
                    "400": 10.590,
                    "500": 10.942
                },
                /* Measured X, Y, Z parameters in a VM on the physical machine*/
                "X": 0.00329,
                "Y": 0.03918,
                "Z": 0.0127
            }
        }
    ]
}
```

The `vmManagerWorkDir` is configured as the path to the root directory of vm_manager (see [setup cluster tutorial](./setup_cluster.md#3-configure-the-vm-manager-on-physical-machine)).

The `maxVMNum` is recommended to be configured no greater than `coreNum / 4`, so that each VM can have 4 cores.

The `theta_m_table` is a table mapping per-VM configured memory to its memory overhead (see [setup cluster tutorial](./setup_cluster.md#6-measure-the-θm-parameter)).

The `X`, `Y`, and `Z` are contributors of per-vlink construction cost (see [setup coordinator tutorial](./setup_coordinator.md#4-build-the-agent-measure-the-parameters))
