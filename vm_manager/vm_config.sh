MAX_VM_NUM=30
RAM=500000 # Default memory in KiB per VM
MAX_VCPUS=128 # Maximum number of vCPUs per VM. Please set this to the number of CPU cores on the host

# Base image configuration
OS_VARIANT="ubuntu22.04"
BACKING_DISK="/var/lib/libvirt/images/splitnn-vm-batch-base.qcow2"
# BACKING_NVRAM="/var/lib/libvirt/qemu/nvram/base-ubuntu22-vm-arm_VARS.template.fd"

# VM network configuration
VM_PREFIX="splitnn-vm"
BRIDGE_IF="br1" # Bridge interface for VM networking, other example: BRIDGE_IF="reals-vm-br"
RAW_VIRTIO_IP_PREFIX="10.100.115." # The subnet for the VMs
SUBNET_MASK="16" # The subnet mask length for the VMs
RAW_MAC_PREFIX="52:54:00:ab:73:" # The MAC address prefix for the VMs
DNS="159.226.8.7" # The DNS server for the VMs
GATEWAY="10.100.0.1" # The network gateway for the VMs

# The IP address of the i-th VM is calculated as:
# VM_IP = RAW_VIRTIO_IP_PREFIX :: (i * 2 + VM_IP_OFFSET)
# Be aware that VM_IP of the "MAX_VM_NUM"-th VM should not exceed 255!!!!!
VM_IP_OFFSET=88

# If the BRIDGE_IF need to be connected to a specific physical interface, uncomment the line below
# MASTER_INTF="eno2" # The physical interface on the host that connects to the bridge
