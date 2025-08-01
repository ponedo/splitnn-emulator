for ((n_i=4; n_i<=30; n_i++)); do
    echo "Running tests with ${n_i} VMs..."
    python -u test.py -n ${n_i} -k 1
done
echo "Running tests with 3 VMs..."
python -u test.py -n 3 -m 200 -k 1
python -u test.py -n 3 -m 300 -k 1
echo "Running tests with 2 VMs..."
python -u test.py -n 2 -m 300 -k 1
python -u test.py -n 2 -m 400 -k 1
echo "Running tests with 1 VM..."
python -u test.py -n 1 -m 500 -k 1