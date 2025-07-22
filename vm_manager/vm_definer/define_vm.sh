#!/bin/bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source ${SCRIPT_DIR}/../vm_config.sh

# Function to create a VM
define_vm() {
  VM_I=$1
  VM_ID=$((VM_I * 2))
  VM_NAME="${VM_PREFIX}-${VM_ID}"
  VM_DISK="/var/lib/libvirt/images/${VM_NAME}.qcow2"
  MAC_ADDRESS_ID=$((VM_ID + VM_IP_OFFSET))
  MAC_ADDRESS_SUFFIX=$(printf %x ${MAC_ADDRESS_ID})
  MAC_ADDRESS="${RAW_MAC_PREFIX}${MAC_ADDRESS_SUFFIX}"
  VM_IP_SUFFIX=$((VM_ID + VM_IP_OFFSET))
  RAW_VIRTIO_IP="${RAW_VIRTIO_IP_PREFIX}${VM_IP_SUFFIX}"
  
  echo "Creating disk for ${VM_NAME}..."
  qemu-img create -f qcow2 -b ${BACKING_DISK} -F qcow2 ${VM_DISK}

  install_vm_cmd="virt-install --name ${VM_NAME} \
  --ram ${RAM} --vcpus ${MAX_VCPUS} \
  --disk path=${VM_DISK},format=qcow2 \
  --network bridge=${BRIDGE_IF},model=virtio,mac=${MAC_ADDRESS} \
  --os-variant ${OS_VARIANT} \
  --import --noreboot --noautoconsole
"
  # --network network=default,model=virtio,driver.name=vhost \

  if [ -n "${BACKING_NVRAM}" ]; then
    echo "Creating nvram firmware for ${VM_NAME}..."
    VM_NVRAM="/var/lib/libvirt/qemu/nvram/${VM_NAME}_VARS.fd"
    cp ${BACKING_NVRAM} ${VM_NVRAM}
    chown libvirt-qemu:kvm ${VM_NVRAM}
    install_vm_cmd="${install_vm_cmd} \
--boot uefi,nvram=${VM_NVRAM}
    "
#   else
#     install_vm_cmd="${install_vm_cmd} \
# --boot uefi
#     "
  fi

  echo "Installing ${VM_NAME}..."
  ${install_vm_cmd}

  echo "Configuring network for ${VM_NAME}..."
  cat << EOF > /tmp/00-installer-config.yaml
network:
  version: 2
  ethernets:
    enp1s0:
      dhcp4: false
      addresses:
        - ${RAW_VIRTIO_IP}/${SUBNET_MASK}
      routes:
        - to: default
          via: ${GATEWAY}
      nameservers:
        addresses:
          - ${DNS}
EOF

  echo "Copying Netplan configuration to ${VM_NAME}..."
  virt-copy-in -d ${VM_NAME} /tmp/00-installer-config.yaml /etc/netplan/
  rm /tmp/00-installer-config.yaml
}

##### Main #####
ip link add ${BRIDGE_IF} type bridge
ip link set ${BRIDGE_IF} up
ip addr add ${RAW_VIRTIO_IP_PREFIX}1/16 dev ${BRIDGE_IF}
if [ -n "${MASTER_INTF}" ]; then
  echo "Connecting ${BRIDGE_IF} to ${MASTER_INTF}..."
  ip link set ${MASTER_INTF} master ${BRIDGE_IF}
else
  echo "No MASTER_INTF specified, skipping connection to physical interface."
fi
brctl show ${BRIDGE_IF}
ip addr show ${BRIDGE_IF}


# Loop to create ${MAX_VM_NUM} VMs
for i in $(seq 0 $((MAX_VM_NUM-1))); do
  define_vm ${i}
done

echo "All VMs created and configured."
