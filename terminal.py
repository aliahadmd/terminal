import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from ttkthemes import ThemedTk
import os
import subprocess
from file_explorer import FileExplorer
from text_editor import MultiCursorText
from file_viewer import FileViewer
from utils.theme_manager import ThemeManager
from utils.font_manager import FontManager
from utils.command_processor import CommandProcessor, SSHClient

class Terminal(ThemedTk):
    def __init__(self):
        super().__init__(theme="arc")
        self.title("Advanced Windows Terminal")
        self.geometry("1000x700")

        self.current_directory = os.getcwd()
        self.ssh_client = None

        self.create_widgets()

        self.theme_manager = ThemeManager(self)
        self.font_manager = FontManager(self)
        self.command_processor = CommandProcessor()

        self.create_menu()

    def create_widgets(self):
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        self.file_explorer = FileExplorer(self.paned_window, self)
        self.terminal_frame = self.create_terminal_frame()

        self.paned_window.add(self.file_explorer, weight=1)
        self.paned_window.add(self.terminal_frame, weight=2)

    def create_terminal_frame(self):
        frame = ttk.Frame(self.paned_window)
        self.terminal = MultiCursorText(frame, wrap=tk.WORD, bg="black", fg="white", insertbackground="white")
        self.terminal.pack(fill=tk.BOTH, expand=True)
        self.terminal.bind("<Return>", self.process_command)
        self.terminal.bind("<Up>", self.show_previous_command)
        self.terminal.bind("<Down>", self.show_next_command)
        self.terminal.bind("<Tab>", self.auto_complete)
        self.terminal.insert(tk.END, f"{self.current_directory}> ")
        return frame

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File", command=self.open_file)
        file_menu.add_command(label="Exit", command=self.quit)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Change Theme", command=self.theme_manager.change_theme)
        view_menu.add_command(label="Change Font", command=self.font_manager.change_font)

        ssh_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="SSH", menu=ssh_menu)
        ssh_menu.add_command(label="Connect", command=self.connect_ssh)
        ssh_menu.add_command(label="Disconnect", command=self.disconnect_ssh)
        

    def show_previous_command(self, event):
        prev_command = self.command_processor.get_previous_command()
        if prev_command:
            self.terminal.delete("insert linestart", "insert lineend")
            self.terminal.insert("insert linestart", f"{self.current_directory}> {prev_command}")
        return "break"

    def show_next_command(self, event):
        next_command = self.command_processor.get_next_command()
        if next_command:
            self.terminal.delete("insert linestart", "insert lineend")
            self.terminal.insert("insert linestart", f"{self.current_directory}> {next_command}")
        return "break"

    def auto_complete(self, event):
        current_text = self.terminal.get("insert linestart", "insert")
        command = current_text.split("> ")[-1].strip()
        
        if command:
            possible_completions = self.command_processor.get_possible_completions(command, self.current_directory)
            if len(possible_completions) == 1:
                completion = possible_completions[0][len(command):]
                self.terminal.insert(tk.INSERT, completion)
            elif len(possible_completions) > 1:
                self.terminal.insert(tk.END, "\n" + " ".join(possible_completions))
                self.terminal.insert(tk.END, f"\n{self.current_directory}> {command}")
        
        return "break"



    def connect_ssh(self):
        hostname = simpledialog.askstring("SSH Connection", "Enter hostname:")
        username = simpledialog.askstring("SSH Connection", "Enter username:")
        password = simpledialog.askstring("SSH Connection", "Enter password:", show='*')
        
        self.ssh_client = SSHClient()
        if self.ssh_client.connect(hostname, username, password):
            self.terminal.insert(tk.END, f"\nConnected to {hostname}\n")
            self.current_directory = self.ssh_client.execute_command("pwd").strip()
            self.file_explorer.populate_tree()
        else:
            self.terminal.insert(tk.END, "\nFailed to connect\n")
            self.ssh_client = None

    def disconnect_ssh(self):
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
            self.current_directory = os.getcwd()
            self.terminal.insert(tk.END, "\nDisconnected from SSH\n")
            self.file_explorer.populate_tree()
    
    def open_file(self, path):
        if self.is_ssh_connected():
            self.open_remote_file(path)
        else:
            self.open_local_file(path)

    def open_local_file(self, path):
        if os.path.isfile(path):
            FileViewer(self, path)
        else:
            messagebox.showerror("Error", f"Cannot open {path}: Not a file")

    def open_remote_file(self, path):
        try:
            sftp = self.ssh_client.open_sftp()
            with sftp.open(path, 'r') as remote_file:
                content = remote_file.read().decode('utf-8')
            sftp.close()
            
            # Create a temporary file to display the content
            temp_path = os.path.join(os.getcwd(), "temp_remote_file.txt")
            with open(temp_path, 'w', encoding='utf-8') as temp_file:
                temp_file.write(content)
            
            FileViewer(self, temp_path)
            
            # Clean up the temporary file after viewing
            os.remove(temp_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open remote file: {str(e)}")

    def is_ssh_connected(self):
        return self.ssh_client is not None

    def process_command(self, event):
        command = self.terminal.get("insert linestart", "insert lineend")
        command = command.split("> ")[-1].strip()
        self.terminal.insert(tk.END, "\n")

        if command.lower() == "exit":
            self.quit()
        elif command.lower().startswith("cd "):
            self.change_directory(command[3:].strip())
        else:
            output = self.execute_command(command)
            self.terminal.insert(tk.END, output)

        self.terminal.insert(tk.END, f"\n{self.current_directory}> ")
        self.terminal.see(tk.END)
        return "break"

    def change_directory(self, new_dir):
        if self.is_ssh_connected():
            try:
                self.ssh_client.exec_command(f"cd {new_dir}")
                _, stdout, _ = self.ssh_client.exec_command("pwd")
                self.current_directory = stdout.read().decode().strip()
            except Exception as e:
                self.terminal.insert(tk.END, f"Error changing directory: {str(e)}\n")
        else:
            try:
                os.chdir(new_dir)
                self.current_directory = os.getcwd()
            except FileNotFoundError:
                self.terminal.insert(tk.END, f"Directory not found: {new_dir}\n")
        self.file_explorer.populate_tree()

    def execute_command(self, command):
        if self.is_ssh_connected():
            _, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()
            return output if output else error
        else:
            return self.command_processor.execute(command)