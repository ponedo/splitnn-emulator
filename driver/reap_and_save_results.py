import os
import json
import argparse
import sqlite3
from util.remote import RemoteMachine, \
    receive_files_from_multiple_machines

MAX_RUNTIME=5
server_num=None

def reap_results(reap_dir):
    # Read configuration of servers
    with open('server_config.json', 'r') as f:
        server_config = json.load(f)
        servers = server_config["servers"]
    server_num = len(servers)

    # Connect to remote machine
    remote_machines = []
    for server in servers:
        remote_machine = RemoteMachine(
            server["ipAddr"], server["user"],
            server["password"], working_dir=server["infraWorkDir"])
        machine = remote_machine.connect()
        remote_machines.append(machine)

    # Define different remote and local directories for each machine
    results_dir = reap_dir
    directories = {
        server["ipAddr"]: (
            os.path.join(server["infraWorkDir"], "log"), results_dir) \
        for server in servers
    }

    # Receive all files from remote directories concurrently
    receive_files_from_multiple_machines(remote_machines, directories)

    # Close connection
    for remote_machine in remote_machines:
        remote_machine.close_connection()


def save_results(reap_dir, db_path):
    tmp_map = {}
    for filename in os.listdir(reap_dir):
        if not filename.endswith(".txt"):
            continue
        nm, algo, op, run_turn, topo, sub_i, _ = filename.strip().split()
        k = (nm, algo, op, topo)
        if k not in tmp_map:
            tmp_map[k] = [[0 for _ in range(server_num)] for _ in range(MAX_RUNTIME)]
        if op == "setup":
            pass

        elif op == "destroy":
            pass

        tmp_map[k][run_turn][sub_i] = 


    # Example data (list of dictionaries)
    data = [
        {"nm": 1, "algo": "Alice", "op": 30, "topo": "xxx", "node_scale": 1, "edge_scale": 1, "time": 12},
    ]

    # Connect to SQLite database (or create it)
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Create a table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER
        )
    ''')

    # Insert data into the table
    for item in data:
        cursor.execute('''
            INSERT INTO users (id, name, age) VALUES (?, ?, ?)
        ''', (item['id'], item['name'], item['age']))

    # Commit and close connection
    conn.commit()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A script to reap and save results from all servers')
    parser.add_argument('-r', '--reap-dir', type=str, required=False, default="results", help='Directory where reaped logs are saved')
    parser.add_argument('-d', '--db-path', type=str, required=False, default="data.db", help='Sqlite3 db file storing results')
    args = parser.parse_args()

    reap_results(args.reap_dir)
    save_results(args.reap_dir, args.db_path)