#!/usr/bin/bash
vm_num=10
mem_values=('500000000 400000000 300000000 200000000 100000000 50000000 25000000 8000000')
vcpu_num=2

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source ${SCRIPT_DIR}/../vm_config.sh

get_cur_mem()
{
	echo $(free | awk '/Mem:/ {print $3}')
}

get_wait_time()
{
	cur_vm_num=$1
	echo $((60 + cur_vm_num * 20))
}

for mem_value in ${mem_values}; do
	./alter_vm.sh ${vm_num} ${mem_value} ${vcpu_num} > /dev/null 2>&1
	sleep 10
	mem_before=$(get_cur_mem)
	for i in $(seq 0 $((vm_num-1))); do
		VM_ID=$((i * 2))
		VM_NAME="${VM_PREFIX}-${VM_ID}"
		virsh start ${VM_NAME} > /dev/null 2>&1
		wait_time=$(get_wait_time $i)
		sleep $wait_time
		mem_after=$(get_cur_mem)
		mem_cost=$((mem_after - mem_before))
		echo "vm_num: ${i} | mem_value(KiB): ${mem_value} | mem_cost(KiB): ${mem_cost}"
	done
	./operate_vm.sh destroy ${vm_num} > /dev/null 2>&1
	sleep 10
done
