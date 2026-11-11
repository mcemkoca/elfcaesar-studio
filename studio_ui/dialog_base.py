"""Ortak modal pencere tabanı (parola kasası pencereleri)."""
from __future__ import annotations

import tkinter as tk

from .theme import F, PANEL, INPUT, LINE, FG, DIM, VIOLET


class _Dialog(tk.Toplevel):
    def __init__(self, app, title, width=560):
        super().__init__(app)
        self.app = app
        self.title(title)
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(app)
        self.body = tk.Frame(self, bg=PANEL)
        self.body.pack(fill="both", expand=True, padx=24, pady=20)
        self.bind("<Escape>", lambda _e: self.destroy())
        try:
            app.shield(self)
        except Exception:
            pass

    def field(self, label, value="", show=None, width=46):
        tk.Label(self.body, text=label, bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(fill="x", pady=(8, 2))
        var = tk.StringVar(value=value)
        e = tk.Entry(self.body, textvariable=var, bg=INPUT, fg=FG, insertbackground=FG, relief="flat", font=F["body"],
                     highlightthickness=1, highlightbackground=LINE, highlightcolor=VIOLET, width=width, show=show or "")
        e.pack(fill="x", ipady=6)
        return var, e

    def center(self):
        self.update_idletasks()
        a = self.app
        x = a.winfo_rootx() + (a.winfo_width() - self.winfo_reqwidth()) // 2
        y = a.winfo_rooty() + (a.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.grab_set()
