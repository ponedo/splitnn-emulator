import paramiko
from concurrent.futures import ThreadPoolExecutor, as_completed

class RemoteMachine:
    def __init__(self, hostname, username, password, port=22, working_dir='/tmp'):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.working_dir = working_dir
        self.ssh = None
        self.sftp = None

    def connect(self):
        """
        Connects to the remote machine and returns the remote machine identifier (self).
        """
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.hostname, port=self.port, username=self.username, password=self.password)
            print(f"Connected to {self.hostname}")
        except Exception as e:
            print(f"Failed to connect to {self.hostname}: {str(e)}")
            return None
        return self

    def execute_command(self, command, output_file=None):
        """
        Executes a command with privilege on the remote machine.
        Optionally redirects stdout to a file on the remote machine.
        
        :param command: The command to execute.
        :param output_file: Path to the file on the remote machine where stdout should be redirected.
        """
        if self.ssh is None:
            print("Not connected to any remote machine.")
            return None

        try:
            # If an output file is provided, redirect stdout to that file
            if output_file:
                full_command = f"cd {self.working_dir} && sudo {command} > {output_file} 2>&1"
            else:
                full_command = f"cd {self.working_dir} && sudo {command}"

            stdin, stdout, stderr = self.ssh.exec_command(full_command)
            stdin.write(self.password + '\n')
            stdin.flush()

            # Even though stdout is redirected, you still may want to capture stderr in case of errors
            errors = stderr.read().decode()

            if errors:
                print(f"Errors:\n{errors}")
            else:
                if output_file:
                    print(f"Command output has been redirected to {output_file}")
                else:
                    output = stdout.read().decode()
                    return output
        except Exception as e:
            print(f"Failed to execute command: {str(e)}")
            return None

    def send_file(self, local_file_path, remote_file_path):
        """
        Sends and overwrites a file to the remote machine.
        """
        if self.ssh is None:
            print("Not connected to any remote machine.")
            return None
        try:
            if self.sftp is None:
                self.sftp = self.ssh.open_sftp()

            self.sftp.put(local_file_path, remote_file_path)
            print(f"File {local_file_path} successfully transferred to {remote_file_path}")
        except Exception as e:
            print(f"Failed to send file: {str(e)}")
            return None

    def close_connection(self):
        """
        Closes the connection to the remote machine.
        """
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        print(f"Connection to {self.hostname} closed.")


def execute_command_on_multiple_machines(machines, commands):
    """
    Executes commands concurrently on multiple machines and waits until all machines finish.
    Supports both formats for the commands:
      1. A string (command) - outputs to stdout.
      2. A tuple (command, output_file) - redirects output to the specified file on the remote machine.
    
    :param machines: A list of RemoteMachine objects.
    :param commands: A dictionary where the key is the machine hostname and the value is either:
                     - A string representing the command (output will be printed).
                     - A tuple (command, output_file) where the command is executed, and stdout is redirected to the output_file on the remote machine.
    """
    def execute_on_machine(machine, command, output_file=None):
        return machine.execute_command(command, output_file)

    results = {}
    with ThreadPoolExecutor(max_workers=len(machines)) as executor:
        # Submit tasks to execute commands on machines
        future_to_machine = {}
        for machine in machines:
            if machine.hostname in commands:
                command_info = commands[machine.hostname]
                
                # If command_info is a tuple, it includes output redirection
                if isinstance(command_info, tuple):
                    command, output_file = command_info
                else:
                    command, output_file = command_info, None  # No output file, print stdout
                
                future_to_machine[executor.submit(execute_on_machine, machine, command, output_file)] = machine

        # Collect results as they complete
        for future in as_completed(future_to_machine):
            machine = future_to_machine[future]
            try:
                result = future.result()
                if result:
                    results[machine.hostname] = result
                else:
                    if isinstance(commands[machine.hostname], tuple):
                        results[machine.hostname] = f"Output redirected to {commands[machine.hostname][1]}"
                    else:
                        results[machine.hostname] = "Command executed successfully"
            except Exception as e:
                results[machine.hostname] = f"Error: {str(e)}"

    return results


def send_file_to_multiple_machines(machines, file_paths):
    """
    Sends files concurrently to multiple machines with different local and remote file paths, 
    and waits until all transfers finish.
    
    :param machines: A list of RemoteMachine objects.
    :param file_paths: A dictionary where the key is the machine hostname and the value is a tuple (local_file_path, remote_file_path).
    """
    def send_file_to_machine(machine, local_file_path, remote_file_path):
        return machine.send_file(local_file_path, remote_file_path)

    results = {}
    with ThreadPoolExecutor(max_workers=len(machines)) as executor:
        # Submit tasks to send different files to different remote paths on each machine
        future_to_machine = {
            executor.submit(send_file_to_machine, machine, file_paths[machine.hostname][0], file_paths[machine.hostname][1]): machine
            for machine in machines if machine.hostname in file_paths
        }

        # Collect results as they complete
        for future in as_completed(future_to_machine):
            machine = future_to_machine[future]
            try:
                result = future.result()
                results[machine.hostname] = "File transfer succeeded"
            except Exception as e:
                results[machine.hostname] = f"Error: {str(e)}"

    return results
