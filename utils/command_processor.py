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
        all_commands = os.listdir(current_directory) + ["cd", "exit"]
        return [cmd for cmd in all_commands if cmd.startswith(command)]

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