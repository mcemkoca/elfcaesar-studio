"""ⓘ kılavuz düğmesi ve Kılavuz penceresi (F1)."""
from __future__ import annotations

import tkinter as tk

from . import guides, icons
from .theme import F, BG, PANEL, INPUT, LINE, FG, FG_2, MUTED, DIM, AMBER, CYAN, mix
from .widgets import Tooltip, StudioButton


class InfoButton(tk.Canvas):
    """Daire içinde i harfi. Tıklanınca kılavuzu ilgili bölümde açar."""

    def __init__(self, parent, command, tip="Kılavuz", size=20, color=CYAN, bg=None):
        bg = bg or parent.cget("bg")
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0, cursor="hand2", takefocus=1)
        self.size, self.color, self.bgc, self.command = size, color, bg, command
        self._draw(False)
        self.bind("<Enter>", lambda _e: self._draw(True))
        self.bind("<Leave>", lambda _e: self._draw(False))
        self.bind("<Button-1>", lambda _e: command())
        self.bind("<Return>", lambda _e: command())
        self.bind("<space>", lambda _e: command())
        Tooltip(self, tip)

    def _draw(self, hover):
        s = self.size
        self.delete("all")
        fill = mix(self.color, self.bgc, .55 if hover else .86)
        self.create_oval(1, 1, s - 1, s - 1, fill=fill, outline=self.color if hover else mix(self.color, self.bgc, .4), width=1.2)
        c = s / 2
        dot = max(1.2, s * .07)
        self.create_oval(c - dot, s * .25 - dot, c + dot, s * .25 + dot, fill=FG if hover else self.color, outline="")
        self.create_line(c, s * .42, c, s * .74, fill=FG if hover else self.color, width=max(1.6, s * .11), capstyle="round")


class GuideWindow(tk.Toplevel):
    """Bölüm listesi + aranabilir kılavuz metni. Tek örnek: open() mevcut pencereyi yeniden kullanır."""

    _instance = None

    @classmethod
    def open(cls, parent, page="start", section=None):
        if cls._instance is not None and cls._instance.winfo_exists():
            w = cls._instance
            w.deiconify()
            w.lift()
        else:
            w = cls._instance = cls(parent)
        w.show(page if guides.chapter(page) else "start", section)
        w.focus_force()
        return w

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("ElfCaesar Studio · Kılavuz")
        self.configure(bg=BG)
        self.geometry("980x680")
        self.minsize(760, 480)
        try:
            self.transient(parent)
        except tk.TclError:
            pass
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=20, pady=(16, 10))
        InfoButton(head, lambda: None, "Kılavuz", 30, AMBER, BG).pack(side="left", padx=(0, 12))
        tt = tk.Frame(head, bg=BG)
        tt.pack(side="left")
        tk.Label(tt, text="KILAVUZ · BÖLÜM BÖLÜM", bg=BG, fg=AMBER, font=F["label"]).pack(anchor="w")
        tk.Label(tt, text="ElfCaesar Studio’yu tanı", bg=BG, fg=FG, font=F["h1"]).pack(anchor="w")
        self.query = tk.StringVar()
        ent = tk.Entry(head, textvariable=self.query, bg=INPUT, fg=FG, insertbackground=FG, relief="flat",
                       highlightthickness=1, highlightbackground=LINE, highlightcolor=CYAN, font=F["body"], width=28)
        ent.pack(side="right", ipady=6)
        tk.Label(head, text="ARA", bg=BG, fg=DIM, font=F["label"]).pack(side="right", padx=8)
        self.query.trace_add("write", lambda *_: self._search())

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self.nav = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE, width=230)
        self.nav.pack(side="left", fill="y")
        self.nav.pack_propagate(False)
        self.nav_rows = {}
        for i, c in enumerate(guides.CHAPTERS, 1):
            row = tk.Frame(self.nav, bg=PANEL, cursor="hand2")
            row.pack(fill="x", padx=6, pady=1)
            ic = tk.Canvas(row, width=18, height=18, bg=PANEL, highlightthickness=0)
            ic.pack(side="left", padx=(8, 8), pady=7)
            icons.draw(ic, c["icon"], 9, 9, 15, MUTED, width=1.4)
            lab = tk.Label(row, text=f"{i:02d}  {c['title']}", bg=PANEL, fg=MUTED, font=F["body_b"], anchor="w")
            lab.pack(side="left", fill="x", expand=True)
            for w in (row, ic, lab):
                w.bind("<Button-1>", lambda _e, k=c["key"]: self.show(k))
            self.nav_rows[c["key"]] = (row, ic, lab, c["icon"])

        right = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.text = tk.Text(right, bg=PANEL, fg=FG_2, wrap="word", relief="flat", padx=26, pady=20, cursor="arrow",
                            font=F["body"], spacing1=2, spacing3=4, highlightthickness=0, borderwidth=0)
        sb = tk.Scrollbar(right, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        t = self.text
        t.tag_configure("eyebrow", foreground=AMBER, font=F["label"], spacing3=2)
        t.tag_configure("h1", foreground=FG, font=F["h1"], spacing3=8)
        t.tag_configure("summary", foreground=FG_2, font=F["body"], spacing3=12)
        t.tag_configure("h2", foreground=CYAN, font=F["label"], spacing1=14, spacing3=6)
        t.tag_configure("step", lmargin1=8, lmargin2=34, font=F["body"], spacing3=5)
        t.tag_configure("num", foreground=AMBER, font=F["body_b"])
        t.tag_configure("tip", lmargin1=8, lmargin2=26, foreground=MUTED, font=F["small"], spacing3=4)
        t.tag_configure("sech", foreground=FG, font=F["h3"], spacing1=12, spacing3=3)
        t.tag_configure("sectext", lmargin1=0, foreground=MUTED, font=F["small"], spacing3=3)
        t.tag_configure("focus", background=mix(CYAN, PANEL, .85))
        t.tag_configure("hit", background=mix(AMBER, PANEL, .6), foreground=FG)

        foot = tk.Frame(self, bg=BG)
        foot.pack(fill="x", padx=20, pady=(0, 14))
        tk.Label(foot, text="F1 her yerde bu pencereyi açar · bölüm ve kart başlıklarındaki ⓘ ilgili kısma götürür",
                 bg=BG, fg=DIM, font=F["tiny"]).pack(side="left")
        StudioButton(foot, "KAPAT", self.withdraw, "secondary", None, "sm").pack(side="right")
        StudioButton(foot, "RESİMLİ KILAVUZ", self.open_full, "accent", "export", "sm",
                     tooltip="Ekran görüntülü tam kılavuzu tarayıcıda aç (internet gerekmez)").pack(side="right", padx=(0, 8))
        self.prev_btn = StudioButton(foot, "ÖNCEKİ", lambda: self._step(-1), "ghost", None, "sm")
        self.next_btn = StudioButton(foot, "SONRAKİ", lambda: self._step(1), "ghost", None, "sm")
        self.next_btn.pack(side="right", padx=4)
        self.prev_btn.pack(side="right")
        self.bind("<Escape>", lambda _e: self.withdraw())
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        self.current = None

    def open_full(self):
        import os
        import webbrowser
        from .runtime import resource_dir
        page = resource_dir() / "docs" / "kilavuz" / "index.html"
        if not page.exists():
            return
        anchor = f"#{self.current}" if self.current else ""
        try:
            webbrowser.open(page.resolve().as_uri() + anchor)
        except Exception:
            if os.name == "nt":
                os.startfile(str(page))  # type: ignore[attr-defined]

    def _step(self, d):
        keys = [c["key"] for c in guides.CHAPTERS]
        i = (keys.index(self.current) + d) % len(keys)
        self.show(keys[i])

    def show(self, key, section=None):
        self.current = key
        for k, (row, ic, lab, icon) in self.nav_rows.items():
            on = k == key
            bg = mix(AMBER, PANEL, .85) if on else PANEL
            for w in (row, ic, lab):
                w.configure(bg=bg)
            lab.configure(fg=AMBER if on else MUTED)
            ic.delete("all")
            icons.draw(ic, icon, 9, 9, 15, AMBER if on else MUTED, width=1.4)
        c = guides.chapter(key)
        idx = [x["key"] for x in guides.CHAPTERS].index(key) + 1
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        t.insert("end", f"BÖLÜM {idx:02d} / {len(guides.CHAPTERS):02d}\n", "eyebrow")
        t.insert("end", c["title"] + "\n", "h1")
        t.insert("end", c["summary"] + "\n", "summary")
        if c["steps"]:
            t.insert("end", "NASIL KULLANILIR\n", "h2")
            for i, s in enumerate(c["steps"], 1):
                t.insert("end", f"{i:>2}  ", ("step", "num"))
                t.insert("end", s + "\n", "step")
        if c["tips"]:
            t.insert("end", "İPUÇLARI\n", "h2")
            for s in c["tips"]:
                t.insert("end", "✦  " + s + "\n", "tip")
        if c["sections"]:
            t.insert("end", "BU EKRANDAKİ KARTLAR\n", "h2")
            for title, s in c["sections"].items():
                start = t.index("end-1c")
                t.mark_set("sec:" + title, start)
                t.mark_gravity("sec:" + title, "left")
                t.insert("end", "ⓘ  " + title + "\n", "sech")
                t.insert("end", s["text"] + "\n", "sectext")
                for i, st in enumerate(s.get("steps", []), 1):
                    t.insert("end", f"   {i}. {st}\n", "sectext")
                if section == title:
                    t.tag_add("focus", start, "end-1c")
        t.configure(state="disabled")
        if section and ("sec:" + section) in t.mark_names():
            t.see("end")
            t.see("sec:" + section)
        else:
            t.yview_moveto(0)
        if self.query.get().strip():
            self._search()

    def _search(self):
        q = self.query.get().strip().casefold()
        t = self.text
        t.tag_remove("hit", "1.0", "end")
        if len(q) < 2:
            return
        if self.current and q not in guides.as_text(self.current).casefold():
            for c in guides.CHAPTERS:
                if q in guides.as_text(c["key"]).casefold():
                    self.show(c["key"])
                    return
        first = None
        pos = "1.0"
        while True:
            pos = t.search(q, pos, "end", nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(q)}c"
            t.tag_add("hit", pos, end)
            first = first or pos
            pos = end
        if first:
            t.see(first)


class GuideMixin:
    def open_guide(self, page=None, section=None):
        GuideWindow.open(self, page or getattr(self, "active_page", None) or "start", section)
        if hasattr(self, "badge_award"):
            self.badge_award("parf")

    def info_button(self, parent, page, section=None, size=18, color=CYAN):
        tip = f"Kılavuz · {section if section else guides.chapter(page)['title']}"
        return InfoButton(parent, lambda: self.open_guide(page, section), tip, size, color)
