# VM Manager

## Preparation:  the VMs on each physical machine

+ Step 1: Setup the VM mananger on the physical machine
    ```bash
    cd /path/to/repository
    git clone ${URL_TO_THIS_REPOSITORY}
    ```
+ Step 2:
    ```bash
    cd /path/to/vm_definer
    ./define_vm.sh
    ```
    if VMs are no longer needed, undefine them:
    ```bash
    cd /path/to/vm_definer
    ./undefine_vm.sh
    ```



## After preparation and before experiments: Measure θ(M_conf)
```bash
cd /path/to/vm_operator
./measure.sh > vm_mem_measure_results
```

## Alter and operate VMs with the Coordinator



