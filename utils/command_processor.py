import subprocess
import os
import paramiko

class CommandProcessor:
    def __init__(self):
        self.command_history = []
        self.history_index = -1

    def execute(self, command, ssh_client=None):
        self.command_history.append(command)
        self.history_index = len(self.command_history)

        if ssh_client:
            return ssh_client.execute_command(command)
        else:
            try:
                output = subprocess.check_output(f"powershell.exe -Command {command}", shell=True, text=True, stderr=subprocess.STDOUT)
                return output
            except subprocess.CalledProcessError as e:
                return f"Error: {e.output}"

    def get_previous_command(self):
        if self.history_index > 0:
            self.history_index -= 1
            return self.command_history[self.history_index]
        return None

    def get_next_command(self):
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            return self.command_history[self.history_index]
        return None

    def get_possible_completions(self, command, current_directory):
        parts = command.split()
        if len(parts) == 1:
            # Complete command names
            all_commands = self.get_all_commands() + os.listdir(current_directory)
            return [cmd for cmd in all_commands if cmd.startswith(parts[0])]
        else:
            # Complete file paths and command options
            if parts[0] in ['cd', 'dir', 'type']:
                return self.complete_file_path(parts[-1], current_directory)
            else:
                return self.complete_command_options(parts[0], parts[-1])
    
    def get_all_commands(self):
        try:
            output = subprocess.check_output("powershell.exe Get-Command", shell=True, text=True)
            return [line.split()[0] for line in output.splitlines()[3:]]
        except subprocess.CalledProcessError:
            return []

    def complete_file_path(self, partial_path, current_directory):
        full_path = os.path.join(current_directory, partial_path)
        dir_name = os.path.dirname(full_path)
        file_name = os.path.basename(full_path)
        try:
            return [os.path.join(dir_name, f) for f in os.listdir(dir_name) if f.startswith(file_name)]
        except OSError:
            return []

    def complete_command_options(self, command, partial_option):
        try:
            output = subprocess.check_output(f"powershell.exe Get-Help {command}", shell=True, text=True)
            options = [line.split()[0] for line in output.splitlines() if line.strip().startswith('-')]
            return [opt for opt in options if opt.startswith(partial_option)]
        except subprocess.CalledProcessError:
            return []

class SSHClient:
    def __init__(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.current_directory = None

    def connect(self, hostname, username, password):
        try:
            self.client.connect(hostname, username=username, password=password)
            _, stdout, _ = self.client.exec_command("pwd")
            self.current_directory = stdout.read().decode().strip()
            return True
        except Exception as e:
            print(f"Failed to connect: {str(e)}")
            return False

    def execute_command(self, command):
        if not self.client:
            return "Not connected to any server"
        
        if command.startswith("cd "):
            return self.change_directory(command[3:].strip())
        else:
            stdin, stdout, stderr = self.client.exec_command(f"cd {self.current_directory}; {command}")
            return stdout.read().decode()

    def change_directory(self, new_dir):
        _, stdout, stderr = self.client.exec_command(f"cd {self.current_directory}; cd {new_dir}; pwd")
        new_path = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if error:
            return f"Error: {error}"
        else:
            self.current_directory = new_path
            return f"Changed directory to {new_path}"

    def open_sftp(self):
        return self.client.open_sftp()

    def close(self):
        if self.client:
            self.client.close()