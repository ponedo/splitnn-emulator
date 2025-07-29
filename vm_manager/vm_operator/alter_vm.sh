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

set_vcpu_num()
{
	VM_NAME=$1
	new_vcpu_num=$2

	tmp_filepath=/tmp/splitnn-vm-tmp.xml

	virsh dumpxml ${VM_NAME} > ${tmp_filepath}
	sed -i -E "s|<vcpu placement=['\"]static['\"]>[0-9]+</vcpu>|<vcpu placement='static'>${new_vcpu_num}</vcpu>|" ${tmp_filepath}
	if [ -n "${BACKING_NVRAM}" ]; then
		virsh undefine ${VM_NAME} --nvram
		VM_NVRAM="/var/lib/libvirt/qemu/nvram/${VM_NAME}_VARS.fd"
		cp ${BACKING_NVRAM} ${VM_NVRAM}
	else
		virsh undefine ${VM_NAME}
	fi
	virsh define ${tmp_filepath}
}

rm vm_ips.txt

for i in $(seq 0 $((vm_num-1))); do
	VM_ID=$((i * 2))
	VM_NAME="${VM_PREFIX}-${VM_ID}"

	VM_IP_SUFFIX=$((VM_ID + VM_IP_OFFSET))
	RAW_VIRTIO_IP="${RAW_VIRTIO_IP_PREFIX}${VM_IP_SUFFIX}"
	echo ${RAW_VIRTIO_IP} >> vm_ips.txt

	virsh setmaxmem ${VM_NAME} ${new_mem_value} --config > /dev/null
	virsh setmem ${VM_NAME} ${new_mem_value} --config > /dev/null
	# virsh setvcpus ${VM_NAME} ${new_vcpu_num} --config > /dev/null
	set_vcpu_num ${VM_NAME} ${new_vcpu_num}
done
