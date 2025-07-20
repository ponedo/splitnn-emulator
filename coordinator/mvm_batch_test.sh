for ((n_i=4; n_i<=9; n_i++)); do
    echo "Running tests with ${n_i} VMs..."
    python -u test.py -n ${n_i} -k 1
done
