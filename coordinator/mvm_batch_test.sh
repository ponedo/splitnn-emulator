# for ((n_i=4; n_i<=9; n_i++)); do
#     echo "Running tests with ${n_i} VMs..."
#     python -u test.py -n ${n_i} -k 1
# done
python -u test.py -n 3 -m 200 -k 1
python -u test.py -n 3 -m 300 -k 1
