import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedStyle

class ThemeManager:
    def __init__(self, terminal):
        self.terminal = terminal
        self.style = ThemedStyle(terminal)

    def set_theme(self, theme_name):
        self.style.set_theme(theme_name)
        bg_color = self.style.lookup('TFrame', 'background')
        fg_color = self.style.lookup('TFrame', 'foreground')
        self.terminal.terminal.configure(bg=bg_color, fg=fg_color, insertbackground=fg_color)

    def change_theme(self):
        themes = self.style.theme_names()
        theme = tk.StringVar(self.terminal)
        theme.set(self.style.theme_use())
        
        theme_window = tk.Toplevel(self.terminal)
        theme_window.title("Change Theme")
        
        theme_menu = ttk.OptionMenu(theme_window, theme, theme.get(), *themes, command=self.set_theme)
        theme_menu.pack(padx=20, pady=20)