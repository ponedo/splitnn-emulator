import os
import time
import sys

def read_cpu_stats():
    with open('/proc/stat', 'r') as file:
        # Read the first line (cpu stats)
        line = file.readline()
        # Split the line into individual stats
        stats = line.split()
        
        # User mode time (jiffies)
        user = int(stats[1])
        # Nice mode time (jiffies)
        nice = int(stats[2])
        # System mode time (jiffies)
        system = int(stats[3])
        # Idle time (jiffies)
        idle = int(stats[4])
        # I/O wait time (jiffies)
        iowait = int(stats[5])
        # IRQ time (jiffies)
        irq = int(stats[6])
        # SoftIRQ time (jiffies)
        softirq = int(stats[7])
        # Steal time (jiffies)
        steal = int(stats[8])
        # Guest time (jiffies)
        guest = int(stats[9])
        # Guest nice time (jiffies)
        guest_nice = int(stats[10])

        # Kernel time is the sum of system, iowait, irq, softirq, steal
        kernel = system + iowait + irq + softirq + steal
        # User time is the sum of user and nice
        user_mode = user + nice
        # Total CPU time is the sum of all the above times
        total = user_mode + kernel + idle + guest + guest_nice

        return user_mode, kernel, total, idle

def get_cpu_core_count():
    # Get the number of CPU cores
    return os.cpu_count()

def log_cpu_usage(log_file):
    core_count = get_cpu_core_count()

    with open(log_file, 'w') as log:
        prev_user, prev_kernel, prev_total, prev_idle = read_cpu_stats()

        while True:
            time.sleep(1)
            curr_user, curr_kernel, curr_total, curr_idle = read_cpu_stats()

            # Calculate CPU usage per core
            user_usage = (curr_user - prev_user) / (curr_total - prev_total) * 100 * core_count
            kernel_usage = (curr_kernel - prev_kernel) / (curr_total - prev_total) * 100 * core_count
            total_usage = (curr_total - prev_total - (curr_idle - prev_idle)) / (curr_total - prev_total) * 100 * core_count

            log.write(f"User: {user_usage:.2f}% | Kernel: {kernel_usage:.2f}% | Total: {total_usage:.2f}%\n")
            log.flush()

            prev_user, prev_kernel, prev_total, prev_idle = curr_user, curr_kernel, curr_total, curr_idle

if __name__ == "__main__":
    # log_file = "cpu_usage.log"
    log_file = sys.argv[1]
    log_cpu_usage(log_file)
