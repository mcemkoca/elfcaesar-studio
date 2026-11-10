"""ELFCAESAR STUDIO özel pencereleri: parola penceresi ve hakkında penceresi."""
from __future__ import annotations

import tkinter as tk

from .theme import F, PANEL, INPUT, LINE_2, FG, FG_2, MUTED, DIM, AMBER, CYAN, GREEN, RED
from .widgets import StudioButton, StrengthMeter
from .security import password_strength
from .crack_ui import crack_summary
from .leaks import is_blocked


class PasswordDialog(tk.Toplevel):
    """Canlı ‘kalkan seviyesi’ ölçerli parola penceresi. Parola yalnızca çağırana döner."""

    def __init__(self, parent, title, purpose, confirm=False, generator=None, icon=None):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self.level = None
        self.confirm = confirm
        if icon is not None:
            try:
                self.iconphoto(False, icon)
            except tk.TclError:
                pass
        body = tk.Frame(self, bg=PANEL)
        body.pack(fill="both", expand=True, padx=22, pady=18)
        head = tk.Frame(body, bg=PANEL)
        head.pack(fill="x")
        if icon is not None:
            tk.Label(head, image=icon, bg=PANEL).pack(side="left", padx=(0, 12))
        ht = tk.Frame(head, bg=PANEL)
        ht.pack(side="left", fill="x")
        tk.Label(ht, text=title, bg=PANEL, fg=FG, font=F["h2"]).pack(anchor="w")
        tk.Label(ht, text=purpose, bg=PANEL, fg=MUTED, font=F["small"], wraplength=380, justify="left").pack(anchor="w")

        self.show = tk.BooleanVar(value=False)
        self.pw = tk.StringVar()
        self.pw2 = tk.StringVar()
        tk.Label(body, text="PAROLA CÜMLESİ", bg=PANEL, fg=DIM, font=F["label"]).pack(anchor="w", pady=(16, 4))
        self.entry = self._entry(body, self.pw)
        self.meter = StrengthMeter(body)
        self.meter.pack(fill="x", pady=(10, 0))
        self.crack = tk.Label(body, text="", bg=PANEL, fg=MUTED, font=F["tiny"], anchor="w", justify="left", wraplength=400)
        self.crack.pack(fill="x", pady=(6, 0))
        if confirm:
            tk.Label(body, text="TEKRAR", bg=PANEL, fg=DIM, font=F["label"]).pack(anchor="w", pady=(14, 4))
            self.entry2 = self._entry(body, self.pw2)
            self.match = tk.Label(body, text="", bg=PANEL, fg=MUTED, font=F["tiny"], anchor="w")
            self.match.pack(fill="x", pady=(4, 0))
        opts = tk.Frame(body, bg=PANEL)
        opts.pack(fill="x", pady=(12, 0))
        tk.Checkbutton(opts, text="Parolayı göster", variable=self.show, command=self._toggle_show,
                       bg=PANEL, fg=FG_2, selectcolor=INPUT, activebackground=PANEL, activeforeground=AMBER,
                       font=F["small"], highlightthickness=0, bd=0).pack(side="left")
        if generator and confirm:
            StudioButton(opts, "PAROLA ÜRET", lambda: self._generate(generator), "ghost", "key", "sm").pack(side="right")
        bar = tk.Frame(body, bg=PANEL)
        bar.pack(fill="x", pady=(18, 0))
        self.ok = StudioButton(bar, "ONAYLA", self._ok, "primary", "check", min_width=120)
        self.ok.pack(side="right")
        StudioButton(bar, "VAZGEÇ", self._cancel, "ghost").pack(side="right", padx=8)
        self.pw.trace_add("write", lambda *_a: self._update())
        self.pw2.trace_add("write", lambda *_a: self._update())
        self.bind("<Return>", lambda _e: self._ok())
        self.bind("<Escape>", lambda _e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._update()
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.deiconify()
        self.entry.focus_set()

    def _entry(self, parent, var):
        box = tk.Frame(parent, bg=INPUT, highlightthickness=1, highlightbackground=LINE_2, highlightcolor=CYAN)
        box.pack(fill="x")
        e = tk.Entry(box, textvariable=var, show="•", bg=INPUT, fg=FG, insertbackground=AMBER, relief="flat",
                     font=F["mono"], bd=0, highlightthickness=0, width=40)
        e.pack(fill="x", padx=10, ipady=8)
        e.bind("<FocusIn>", lambda _e: box.configure(highlightbackground=CYAN))
        e.bind("<FocusOut>", lambda _e: box.configure(highlightbackground=LINE_2))
        return e

    def _toggle_show(self):
        char = "" if self.show.get() else "•"
        self.entry.configure(show=char)
        if self.confirm:
            self.entry2.configure(show=char)

    def _generate(self, generator):
        value = generator()
        self.pw.set(value)
        self.pw2.set(value)
        self.show.set(True)
        self._toggle_show()

    def _update(self):
        value = self.pw.get()
        result = password_strength(value) if value else None
        text, color = crack_summary(value)
        self.crack.configure(text=text, fg=color)
        self.meter.update_result(result)
        ok = bool(value)
        if self.confirm:
            blocked = is_blocked(value) if value else None
            ok = bool(result and result["meets_min"]) and self.pw.get() == self.pw2.get() and not blocked
            if blocked:
                self.crack.configure(text=f"✕ Bu parola sızıntı/yaygın parola listesinde (“{blocked['base']}” tabanı, "
                                     f"#{blocked['rank']}). Güvenliğin için kasa parolası olarak kabul edilmez.", fg=RED)
            if not self.pw2.get():
                self.match.configure(text="Parolayı doğrulamak için tekrar gir.", fg=MUTED)
            elif self.pw.get() == self.pw2.get():
                self.match.configure(text="✓ Parolalar eşleşiyor", fg=GREEN)
            else:
                self.match.configure(text="✕ Parolalar eşleşmiyor", fg=RED)
        self.ok.set_enabled(ok)
        self.level = result["level"] if result else None

    def _ok(self):
        if not self.ok._enabled:
            return
        if self.confirm and self.level is not None and self.level <= 1:
            from tkinter import messagebox
            if not messagebox.askyesno("Zayıf parola",
                                       "Bu parola ‘Tahta Kalkan’ seviyesinin altında ve çevrimdışı tahmin saldırısına dayanıksız.\n\n"
                                       "Yine de bu parolayla devam etmek istiyor musun?", parent=self):
                return
        self.result = self.pw.get()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def show_modal(self):
        self.grab_set()
        self.wait_window()
        return self.result


class AboutDialog(tk.Toplevel):
    def __init__(self, parent, logo, version, lines, signature=None, founder=None, actions=()):
        super().__init__(parent)
        self.title("ElfCaesar Studio hakkında")
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(parent)
        body = tk.Frame(self, bg=PANEL)
        body.pack(padx=34, pady=24)
        if logo is not None:
            tk.Label(body, image=logo, bg=PANEL).pack()
        tk.Label(body, text="ELFCAESAR STUDIO", bg=PANEL, fg=FG, font=F["h1"]).pack(pady=(12, 0))
        tk.Label(body, text=f"Sürüm {version}", bg=PANEL, fg=AMBER, font=F["mono_b"]).pack(pady=(4, 10))
        tk.Label(body, text="YAPIMCI", bg=PANEL, fg=DIM, font=F["label"]).pack()
        if signature is not None:
            tk.Label(body, image=signature, bg=PANEL).pack(pady=(2, 10))
        else:
            tk.Label(body, text="Dante", bg=PANEL, fg=AMBER, font=F["h1"]).pack(pady=(2, 10))
        if founder:
            fr = tk.Frame(body, bg=INPUT, highlightthickness=1, highlightbackground=LINE_2)
            fr.pack(pady=(0, 12))
            tk.Label(fr, text=f"✦  KURUCU ELF ROZETİ  ·  № {founder[0][:4].upper()}-{founder[0][4:8].upper()}  ·  {founder[1]}",
                     bg=INPUT, fg=AMBER, font=F["mono_xs"], padx=12, pady=6).pack()
        for text in lines:
            tk.Label(body, text=text, bg=PANEL, fg=MUTED, font=F["small"]).pack()
        bar = tk.Frame(body, bg=PANEL)
        bar.pack(pady=(18, 0))
        for label, cb in actions:
            StudioButton(bar, label, lambda cb=cb: (self.destroy(), cb()), "ghost", None, "sm").pack(side="left", padx=4)
        StudioButton(bar, "KAPAT", self.destroy, "secondary", min_width=110).pack(side="left", padx=(8, 0))
        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_reqheight()) // 4
        self.geometry(f"+{max(0, x)}+{max(0, y)}")


class WhatsNewDialog(tk.Toplevel):
    def __init__(self, parent, icon, notes, previous=None):
        super().__init__(parent)
        version, date, title, items = notes
        self.title(f"Yenilikler · {version}")
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(parent)
        body = tk.Frame(self, bg=PANEL)
        body.pack(padx=28, pady=22)
        head = tk.Frame(body, bg=PANEL)
        head.pack(fill="x")
        if icon is not None:
            tk.Label(head, image=icon, bg=PANEL).pack(side="left", padx=(0, 12))
        ht = tk.Frame(head, bg=PANEL)
        ht.pack(side="left")
        tk.Label(ht, text="YENİLİKLER", bg=PANEL, fg=AMBER, font=F["label"]).pack(anchor="w")
        tk.Label(ht, text=f"{version} · {title}", bg=PANEL, fg=FG, font=F["h2"]).pack(anchor="w")
        sub = date + (f"  ·  önceki sürüm {previous}" if previous else "")
        tk.Label(ht, text=sub, bg=PANEL, fg=DIM, font=F["mono_xs"]).pack(anchor="w")
        for item in items:
            row = tk.Frame(body, bg=PANEL)
            row.pack(fill="x", pady=3, anchor="w")
            tk.Label(row, text="✦", bg=PANEL, fg=GREEN, font=F["small"]).pack(side="left", anchor="n")
            tk.Label(row, text=item, bg=PANEL, fg=FG_2, font=F["small"], wraplength=460, justify="left").pack(side="left", padx=8)
        StudioButton(body, "TAMAM", self.destroy, "primary", "check", min_width=120).pack(anchor="e", pady=(16, 0))
        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
