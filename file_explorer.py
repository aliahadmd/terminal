import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import shutil
import stat
import posixpath

class FileExplorer(ttk.Frame):
    def __init__(self, parent, terminal):
        super().__init__(parent)
        self.terminal = terminal
        self.create_widgets()

    def create_widgets(self):
        self.tree = ttk.Treeview(self)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.heading("#0", text="File Explorer", anchor=tk.W)
        self.tree.bind("<<TreeviewOpen>>", self.update_tree)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="New File", command=self.create_file)
        self.context_menu.add_command(label="New Folder", command=self.create_folder)
        self.context_menu.add_command(label="Rename", command=self.rename_item)
        self.context_menu.add_command(label="Delete", command=self.delete_item)

        self.populate_tree()

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        path = self.terminal.current_directory
        node = self.tree.insert("", tk.END, text=path, open=True)
        self.process_directory(node, path)

    def process_directory(self, parent, path):
        if self.terminal.is_ssh_connected():
            self.process_remote_directory(parent, path)
        else:
            self.process_local_directory(parent, path)

    def process_local_directory(self, parent, path):
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    folder = self.tree.insert(parent, tk.END, text=item, open=False)
                    self.tree.insert(folder, tk.END, text="")
                else:
                    self.tree.insert(parent, tk.END, text=item)
        except PermissionError:
            pass

    def process_remote_directory(self, parent, path):
        try:
            sftp = self.terminal.ssh_client.open_sftp()
            for item in sftp.listdir(path):
                item_path = posixpath.join(path, item)
                try:
                    attr = sftp.lstat(item_path)
                    if stat.S_ISDIR(attr.st_mode):
                        folder = self.tree.insert(parent, tk.END, text=item, open=False)
                        self.tree.insert(folder, tk.END, text="")
                    else:
                        self.tree.insert(parent, tk.END, text=item)
                except IOError:
                    pass  # Skip items we can't access
            sftp.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list remote directory: {str(e)}")


    def update_tree(self, event):
        selected_item = self.tree.focus()
        self.tree.delete(*self.tree.get_children(selected_item))
        path = self.get_selected_path(selected_item)
        self.process_directory(selected_item, path)

    def get_selected_path(self, item):
        path_parts = []
        while item:
            path_parts.insert(0, self.tree.item(item)["text"])
            item = self.tree.parent(item)
        if self.terminal.is_ssh_connected():
            return posixpath.join(*path_parts)
        else:
            return os.path.join(*path_parts)

    def on_double_click(self, event):
        item = self.tree.selection()[0]
        path = self.get_selected_path(item)
        self.terminal.open_file(path)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def create_file(self):
        parent_item = self.tree.selection()[0]
        parent_path = self.get_selected_path(parent_item)
        file_name = simpledialog.askstring("New File", "Enter file name:")
        if file_name:
            file_path = os.path.join(parent_path, file_name)
            try:
                with open(file_path, 'w') as f:
                    pass
                self.update_tree(None)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create file: {str(e)}")

    def create_folder(self):
        parent_item = self.tree.selection()[0]
        parent_path = self.get_selected_path(parent_item)
        folder_name = simpledialog.askstring("New Folder", "Enter folder name:")
        if folder_name:
            folder_path = os.path.join(parent_path, folder_name)
            try:
                os.mkdir(folder_path)
                self.update_tree(None)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create folder: {str(e)}")

    def rename_item(self):
        item = self.tree.selection()[0]
        old_path = self.get_selected_path(item)
        old_name = os.path.basename(old_path)
        new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=old_name)
        if new_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
                self.update_tree(None)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename: {str(e)}")

    def delete_item(self):
        item = self.tree.selection()[0]
        path = self.get_selected_path(item)
        if messagebox.askyesno("Delete", f"Are you sure you want to delete {path}?"):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
                self.update_tree(None)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {str(e)}")