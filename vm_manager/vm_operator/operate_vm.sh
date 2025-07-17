#!/usr/bin/bash
op=$1
vm_num=$2

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source ${SCRIPT_DIR}/../vm_config.sh

VM_START_IP=4
if [ -z "$op" ] || [ -z "$vm_num" ]; then
	echo "Usage:"
	echo "    $0 <op> <vm_num>"
	echo "Arguments:"
	echo "    op    [start|destroy]"
	exit
fi

for i in $(seq 0 $((vm_num-1))); do
	VM_ID=$((i * 2))
	VM_NAME="${VM_PREFIX}-${VM_ID}"
	virsh ${op} ${VM_NAME}
done
