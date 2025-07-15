#!/usr/bin/bash
vm_num=$1
new_mem_value=$2
new_vcpu_num=$3

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source ${SCRIPT_DIR}/../vm_config.sh

VM_START_IP=4
if [ -z "$vm_num" ] || [ -z "$new_mem_value" ]; then
	echo "Usage:"
	echo "    $0 <vm_num> <new_mem_value>"
	exit
fi

for i in $(seq 0 $((vm_num-1))); do
	VM_ID=$((i * 2))
	VM_NAME="${VM_PREFIX}-${HOST_ID}-${VM_ID}"
	virsh setmaxmem ${VM_NAME} ${new_mem_value} --config > /dev/null
	virsh setmem ${VM_NAME} ${new_mem_value} --config > /dev/null
	virsh setvcpus ${VM_NAME} ${new_vcpu_num} --config > /dev/null
done
