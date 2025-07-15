#!/bin/bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source ${SCRIPT_DIR}/../vm_config.sh

for i in $(seq 0 $((MAX_VM_NUM-1))); do
    VM_ID=$((i * 2))
    virsh destroy ${VM_PREFIX}-${HOST_ID}-${VM_ID}
    virsh undefine --nvram ${VM_PREFIX}-${HOST_ID}-${VM_ID}
    rm /var/lib/libvirt/images/${VM_PREFIX}-${HOST_ID}-${VM_ID}.qcow2
done
