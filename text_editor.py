import tkinter as tk

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