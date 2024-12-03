ip -all netns del all

start=$(($(date +%s%N) / 1000000))
sleep 1
for ((i=0; i<100; i++)); do ip link add test-dummy type dummy; ip link del test-dummy; done
end=$(($(date +%s%N)/1000000))

echo "$((end - start))ms"