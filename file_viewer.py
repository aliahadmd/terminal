import os
import tkinter as tk
from tkinter import ttk
from tkhtmlview import HTMLLabel
import json
import csv
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

class FileViewer:
    def __init__(self, parent, file_path):
        self.window = tk.Toplevel(parent)
        self.window.title(f"File Viewer - {file_path}")
        self.window.geometry("800x600")

        self.file_path = file_path
        self.load_file()

    def load_file(self):
        _, ext = os.path.splitext(self.file_path)
        ext = ext.lower()

        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                content = file.read()

            if ext == ".md":
                html = markdown.markdown(content)
                self.show_html(html)
            elif ext == ".csv":
                table = self.csv_to_table(content)
                self.show_text(table)
            elif ext == ".json":
                formatted_json = json.dumps(json.loads(content), indent=2)
                self.show_text(formatted_json)
            else:
                lexer = guess_lexer(content)
                highlighted = highlight(content, lexer, HtmlFormatter(style="default"))
                self.show_html(highlighted)
        except Exception as e:
            self.show_text(f"Error opening file: {str(e)}")

    def show_html(self, content):
        html_label = HTMLLabel(self.window, html=content)
        html_label.pack(fill=tk.BOTH, expand=True)

    def show_text(self, content):
        text = tk.Text(self.window, wrap=tk.WORD, bg="white", fg="black")
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, content)

    def csv_to_table(self, content):
        table = []
        for row in csv.reader(content.splitlines()):
            table.append(" | ".join(row))
        return "\n".join(table)