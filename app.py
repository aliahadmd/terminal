import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
import os
import subprocess
import json
import csv
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.styles import get_all_styles, get_style_by_name
from tkhtmlview import HTMLLabel
import re
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory

class MultiCursorText(tk.Text):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursors = [(1.0, 1.0)]  # List of (start, end) for each cursor
        self.bind("<Control-B>", self.add_cursor)

    def add_cursor(self, event):
        current_pos = self.index(tk.INSERT)
        self.cursors.append((current_pos, current_pos))
        self.mark_set(f"cursor_{len(self.cursors)}", current_pos)
        self.see(current_pos)
        return "break"

    def insert(self, index, chars, *args):
        for i, (start, end) in enumerate(self.cursors):
            super().insert(start, chars, *args)
            new_end = self.index(f"{start}+{len(chars)}c")
            self.cursors[i] = (new_end, new_end)
            if i > 0:
                self.mark_set(f"cursor_{i+1}", new_end)
        self.see(self.cursors[-1][1])

    def delete(self, index1, index2=None):
        for i, (start, end) in enumerate(self.cursors):
            super().delete(start, end)
            self.cursors[i] = (start, start)
            if i > 0:
                self.mark_set(f"cursor_{i+1}", start)
        self.see(self.cursors[-1][1])

class Terminal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Advanced Windows Terminal")
        self.geometry("1000x700")

        self.style = ttk.Style()
        self.current_style = get_style_by_name("default")
        self.current_directory = os.getcwd()

        self.command_history = InMemoryHistory()
        self.prompt_session = PromptSession(history=self.command_history)

        self.create_widgets()
        self.set_theme("default")
        self.load_fonts()

    def create_widgets(self):
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        self.file_explorer = self.create_file_explorer()
        self.terminal_frame = self.create_terminal_frame()

        self.paned_window.add(self.file_explorer, weight=1)
        self.paned_window.add(self.terminal_frame, weight=2)

        self.create_menu()

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File", command=self.open_file)
        file_menu.add_command(label="Exit", command=self.quit)

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Change Theme", command=self.change_theme)
        view_menu.add_command(label="Change Font", command=self.change_font)

    def create_file_explorer(self):
        frame = ttk.Frame(self.paned_window)
        self.tree = ttk.Treeview(frame)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.heading("#0", text="File Explorer", anchor=tk.W)
        self.tree.bind("<<TreeviewOpen>>", self.update_tree)
        self.tree.bind("<Double-1>", self.on_double_click)

        self.populate_tree()
        return frame

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

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        path = self.current_directory
        node = self.tree.insert("", tk.END, text=path, open=True)
        self.process_directory(node, path)

    def process_directory(self, parent, path):
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
        return os.path.join(*path_parts)

    def on_double_click(self, event):
        item = self.tree.selection()[0]
        path = self.get_selected_path(item)
        if os.path.isfile(path):
            self.view_file(path)

    def view_file(self, path):
        _, ext = os.path.splitext(path)
        ext = ext.lower()

        try:
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()

            if ext == ".md":
                html = markdown.markdown(content)
                self.show_in_new_window(html, "text/html", path)
            elif ext == ".csv":
                table = self.csv_to_table(content)
                self.show_in_new_window(table, "text/plain", path)
            elif ext == ".json":
                formatted_json = json.dumps(json.loads(content), indent=2)
                self.show_in_new_window(formatted_json, "application/json", path)
            else:
                lexer = guess_lexer(content)
                highlighted = highlight(content, lexer, HtmlFormatter(style=self.current_style))
                self.show_in_new_window(highlighted, "text/html", path)
        except Exception as e:
            messagebox.showerror("Error", f"Unable to open file: {str(e)}")

    def csv_to_table(self, content):
        table = []
        for row in csv.reader(content.splitlines()):
            table.append(" | ".join(row))
        return "\n".join(table)

    def show_in_new_window(self, content, content_type, title):
        window = tk.Toplevel(self)
        window.title(f"File Viewer - {title}")
        window.geometry("800x600")

        if content_type in ["text/html", "application/json"]:
            html_label = HTMLLabel(window, html=content)
            html_label.pack(fill=tk.BOTH, expand=True)
        else:
            text = tk.Text(window, wrap=tk.WORD, bg="white", fg="black")
            text.pack(fill=tk.BOTH, expand=True)
            text.insert(tk.END, content)

    def process_command(self, event):
        command = self.terminal.get("insert linestart", "insert lineend")
        command = command.split("> ")[-1].strip()
        self.terminal.insert(tk.END, "\n")

        if command.lower() == "exit":
            self.quit()
        elif command.lower().startswith("cd "):
            new_dir = command[3:].strip()
            try:
                os.chdir(new_dir)
                self.current_directory = os.getcwd()
                self.populate_tree()
            except FileNotFoundError:
                self.terminal.insert(tk.END, f"Directory not found: {new_dir}\n")
        else:
            try:
                output = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
                self.terminal.insert(tk.END, output)
            except subprocess.CalledProcessError as e:
                self.terminal.insert(tk.END, f"Error: {e.output}")

        self.command_history.append_string(command)
        self.terminal.insert(tk.END, f"\n{self.current_directory}> ")
        self.terminal.see(tk.END)
        return "break"

    def show_previous_command(self, event):
        try:
            prev_command = self.command_history.get_previous_history()
            self.terminal.delete("insert linestart", "insert lineend")
            self.terminal.insert("insert linestart", f"{self.current_directory}> {prev_command}")
        except IndexError:
            pass
        return "break"

    def show_next_command(self, event):
        try:
            next_command = self.command_history.get_next_history()
            self.terminal.delete("insert linestart", "insert lineend")
            self.terminal.insert("insert linestart", f"{self.current_directory}> {next_command}")
        except IndexError:
            pass
        return "break"

    def auto_complete(self, event):
        current_text = self.terminal.get("insert linestart", "insert")
        command = current_text.split("> ")[-1].strip()
        
        if command:
            possible_completions = self.get_possible_completions(command)
            if len(possible_completions) == 1:
                completion = possible_completions[0][len(command):]
                self.terminal.insert(tk.INSERT, completion)
            elif len(possible_completions) > 1:
                self.terminal.insert(tk.END, "\n" + " ".join(possible_completions))
                self.terminal.insert(tk.END, f"\n{self.current_directory}> {command}")
        
        return "break"

    def get_possible_completions(self, command):
        all_commands = os.listdir(self.current_directory) + ["cd", "exit"]
        return [cmd for cmd in all_commands if cmd.startswith(command)]

    def set_theme(self, theme_name):
        self.style.theme_use(theme_name)
        self.current_style = get_style_by_name(theme_name)
        bg_color = self.current_style.background_color
        fg_color = self.current_style.styles.get("Text", {}).get("color", "#000000")
        self.terminal.configure(bg=bg_color, fg=fg_color, insertbackground=fg_color)

    def change_theme(self):
        themes = list(get_all_styles())
        theme = tk.StringVar(self)
        theme.set(self.style.theme_use())
        
        theme_window = tk.Toplevel(self)
        theme_window.title("Change Theme")
        
        theme_menu = ttk.OptionMenu(theme_window, theme, theme.get(), *themes, command=self.set_theme)
        theme_menu.pack(padx=20, pady=20)

    def load_fonts(self):
        self.available_fonts = list(font.families())
        self.current_font = font.Font(family="TkDefaultFont", size=10)
        self.terminal.configure(font=self.current_font)

    def change_font(self):
        font_window = tk.Toplevel(self)
        font_window.title("Change Font")
        
        font_var = tk.StringVar(font_window)
        font_var.set(self.current_font.actual()['family'])
        
        font_menu = ttk.OptionMenu(font_window, font_var, font_var.get(), *self.available_fonts)
        font_menu.pack(padx=20, pady=20)
        
        size_var = tk.IntVar(font_window)
        size_var.set(self.current_font.actual()['size'])
        
        size_spinbox = ttk.Spinbox(font_window, from_=6, to=72, textvariable=size_var)
        size_spinbox.pack(padx=20, pady=20)
        
        apply_button = ttk.Button(font_window, text="Apply", command=lambda: self.apply_font(font_var.get(), size_var.get()))
        apply_button.pack(padx=20, pady=20)

    def apply_font(self, family, size):
        self.current_font.configure(family=family, size=size)
        self.terminal.configure(font=self.current_font)

    def open_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.view_file(file_path)

if __name__ == "__main__":
    app = Terminal()
    app.mainloop()