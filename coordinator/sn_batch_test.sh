for ((n_i=5; n_i>=1; n_i--)); do
    echo "Running tests with ${n_i} VMs..."
    python -u test.py -n ${n_i} -k 0
done
