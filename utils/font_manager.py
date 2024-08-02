import tkinter as tk
from tkinter import ttk, font

class FontManager:
    def __init__(self, terminal):
        self.terminal = terminal
        self.available_fonts = list(font.families())
        self.current_font = font.Font(family="TkDefaultFont", size=10)
        self.apply_font("TkDefaultFont", 10)

    def change_font(self):
        font_window = tk.Toplevel(self.terminal)
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
        if hasattr(self.terminal, 'terminal'):
            self.terminal.terminal.configure(font=self.current_font)