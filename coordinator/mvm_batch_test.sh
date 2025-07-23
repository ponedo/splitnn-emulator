for ((n_i=4; n_i<=30; n_i++)); do
    echo "Running tests with ${n_i} VMs..."
    python -u test.py -n ${n_i} -k 1
done
python -u test.py -n 3 -m 200 -k 1
python -u test.py -n 3 -m 300 -k 1
python -u test.py -n 2 -m 300 -k 1
python -u test.py -n 2 -m 400 -k 1
python -u test.py -n 1 -k 1
