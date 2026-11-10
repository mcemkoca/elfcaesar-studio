"""Rozet arayüzü: kazanma kutlaması, Rozet Vitrini penceresi ve Kontrol Merkezi kartı."""
from __future__ import annotations

import tkinter as tk

from . import badges as B
from .runtime import resource_dir
from .theme import F, BG, PANEL, INPUT, LINE, FG, FG_2, MUTED, DIM, AMBER, CYAN, GREEN, mix
from .widgets import StudioButton

BADGE_DIR = resource_dir() / "assets" / "badges"


class BadgeMixin:
    # ------------------------------------------------------------ görseller
    def badge_img(self, bid: str, size: int = 64, earned: bool = True):
        cache = self.__dict__.setdefault("_badge_cache", {})
        key = (bid, size, earned)
        if key not in cache:
            name = f"{bid}_{size}{'' if earned else '_off'}.png"
            try:
                cache[key] = tk.PhotoImage(file=str(BADGE_DIR / name))
            except tk.TclError:
                cache[key] = None
        return cache[key]

    def badge_earned(self) -> dict:
        return self.prefs.get("badges") or {}

    # ------------------------------------------------------------ olaylar
    def badge_event(self, level, title):
        if level == "error" or not hasattr(self, "prefs"):
            return
        for bid in B.for_event(title):
            self.badge_award(bid)

    def badge_visit(self, key):
        if not hasattr(self, "prefs"):
            return
        visited = list(self.prefs.get("visited") or [])
        if key not in visited:
            visited.append(key)
            self.prefs["visited"] = visited
            self._badge_save()
        self.badge_check()

    def badge_check(self):
        score = (getattr(self, "assessment", None) or {}).get("score", 0)
        for bid in B.state_badges(self.prefs, score):
            self.badge_award(bid)

    def badge_award(self, bid):
        if not B.award(self.prefs, bid):
            return
        self._badge_save()
        name = B.BY_ID[bid][1]
        try:
            self.log.add("system", "success", f"Yeni rozet: {name}", B.BY_ID[bid][4])
        except Exception:
            pass
        queue = self.__dict__.setdefault("_badge_queue", [])
        queue.append(bid)
        if len(queue) == 1:
            self.after(350, self._badge_next)
        self._badge_refresh_home()
        if bid != "aran":
            self.after(50, self.badge_check)

    def _badge_save(self):
        from . import settings as user_settings
        user_settings.save(self.prefs)

    def _badge_next(self):
        queue = self.__dict__.get("_badge_queue") or []
        if not queue:
            return
        BadgeUnlock(self, queue[0], on_close=self._badge_done, on_open=self.open_badges)

    def _badge_done(self):
        queue = self.__dict__.get("_badge_queue") or []
        if queue:
            queue.pop(0)
        if queue:
            self.after(250, self._badge_next)

    # ------------------------------------------------------------ vitrin
    def open_badges(self):
        w = self.__dict__.get("_badge_win")
        if w is not None and w.winfo_exists():
            w.render()
            w.deiconify()
            w.lift()
            return
        self._badge_win = BadgeShowcase(self)

    def badge_home_card(self, parent):
        card = tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        head = tk.Frame(card, bg=PANEL)
        head.pack(fill="x", padx=16, pady=(13, 6))
        tk.Label(head, text="ROZET VİTRİNİ", bg=PANEL, fg=AMBER, font=F["label"]).pack(side="left")
        self._badge_home_count = tk.Label(head, text="", bg=PANEL, fg=DIM, font=F["mono_xs"])
        self._badge_home_count.pack(side="left", padx=10)
        StudioButton(head, "VİTRİNİ AÇ", self.open_badges, "accent", "spark", "sm").pack(side="right")
        self._badge_home_row = tk.Frame(card, bg=PANEL)
        self._badge_home_row.pack(fill="x", padx=12, pady=(2, 14))
        self._badge_refresh_home()
        return card

    def _badge_refresh_home(self):
        row = self.__dict__.get("_badge_home_row")
        if row is None or not row.winfo_exists():
            return
        for ch in row.winfo_children():
            ch.destroy()
        earned = self.badge_earned()
        for bid, name, *_r in B.BADGES:
            got = bid in earned
            img = self.badge_img(bid, 40, got)
            lab = tk.Label(row, image=img, bg=PANEL, cursor="hand2")
            lab.pack(side="left", padx=2)
            lab.bind("<Button-1>", lambda _e: self.open_badges())
            from .widgets import Tooltip
            Tooltip(lab, f"{name} · {B.BY_ID[bid][4]}" + ("" if got else " (kilitli)"))
        n, total = B.progress(self.prefs)
        self._badge_home_count.configure(text=f"{n} / {total}  ·  ADLAR ELF DİLLERİNDEN")


class BadgeUnlock(tk.Toplevel):
    """Yeni rozet kutlaması: alttan kayarak gelir, parlar, 5 sn sonra kaybolur."""

    def __init__(self, app, bid, on_close=None, on_open=None):
        super().__init__(app)
        self.app, self.bid, self.on_close, self.on_open = app, bid, on_close, on_open
        _id, name, lang, meaning, title, how, rarity = B.BY_ID[bid]
        rname, rcol = B.RARITY[rarity]
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.configure(bg=rcol)
        body = tk.Frame(self, bg=PANEL)
        body.pack(padx=1, pady=1)
        self.glow = tk.Canvas(body, width=150, height=150, bg=PANEL, highlightthickness=0)
        self.glow.pack(side="left", padx=(18, 8), pady=16)
        self.img = app.badge_img(bid, 128, True)
        text = tk.Frame(body, bg=PANEL)
        text.pack(side="left", padx=(4, 26), pady=16)
        tk.Label(text, text=f"YENİ ROZET  ·  {rname}", bg=PANEL, fg=rcol, font=F["label"]).pack(anchor="w")
        tk.Label(text, text=name, bg=PANEL, fg=FG, font=F["display"]).pack(anchor="w", pady=(2, 0))
        tk.Label(text, text=f"{lang} · “{meaning}”", bg=PANEL, fg=AMBER, font=F["mono_sm"]).pack(anchor="w")
        tk.Label(text, text=title, bg=PANEL, fg=FG_2, font=F["body_b"]).pack(anchor="w", pady=(10, 0))
        tk.Label(text, text=how, bg=PANEL, fg=MUTED, font=F["small"], wraplength=300, justify="left").pack(anchor="w")
        tk.Label(text, text="Vitrini açmak için tıkla", bg=PANEL, fg=DIM, font=F["tiny"]).pack(anchor="w", pady=(8, 0))
        for w in [self, body, self.glow, text, *text.winfo_children()]:
            w.bind("<Button-1>", lambda _e: self._open())
        self.rcol = rcol
        self.update_idletasks()
        self.w, self.h = self.winfo_reqwidth(), self.winfo_reqheight()
        ax, ay, aw, ah = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
        self.x = ax + (aw - self.w) // 2
        self.y_end = ay + ah - self.h - 70
        self.y = self.y_end + 60
        self.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        self._alpha(0.0)
        self.frame = 0
        self._tick()
        self.after(5200, self._leave)

    def _alpha(self, a):
        try:
            self.attributes("-alpha", a)
        except tk.TclError:
            pass

    def _draw(self, k):
        c = self.glow
        c.delete("all")
        cx = cy = 75
        for i, r in enumerate((74, 66, 58)):
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=mix(PANEL, self.rcol, max(0, .55 * k - i * .15)), width=2)
        # dönen ışık parçacıkları
        import math
        for i in range(10):
            ang = self.frame * .06 + i * math.tau / 10
            rr = 70
            x, y = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
            col = AMBER if i % 2 else CYAN
            c.create_oval(x - 2, y - 2, x + 2, y + 2, fill=mix(PANEL, col, k), outline="")
        if self.img is not None:
            c.create_image(cx, cy, image=self.img)

    def _tick(self):
        if not self.winfo_exists():
            return
        self.frame += 1
        k = min(1.0, self.frame / 14)
        ease = 1 - (1 - k) ** 3
        y = int(self.y + (self.y_end - self.y) * ease)
        self.geometry(f"+{self.x}+{y}")
        self._alpha(ease)
        self._draw(.6 + .4 * abs(((self.frame % 60) / 30) - 1))
        if self.frame < 400:
            self.after(30, self._tick)

    def _open(self):
        self._close()
        if self.on_open:
            self.on_open()

    def _leave(self, step=0):
        if not self.winfo_exists():
            return
        if step >= 8:
            self._close()
            return
        self._alpha(1 - step / 8)
        self.after(30, lambda: self._leave(step + 1))

    def _close(self):
        if self.winfo_exists():
            self.destroy()
            if self.on_close:
                self.on_close()


class BadgeShowcase(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("ElfCaesar Studio · Rozet Vitrini")
        self.configure(bg=BG)
        self.geometry("1040x700")
        self.minsize(760, 520)
        try:
            self.transient(app)
        except tk.TclError:
            pass
        self.bind("<Escape>", lambda _e: self.withdraw())
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=24, pady=(18, 6))
        tk.Label(head, text="ROZET VİTRİNİ · ADLAR TOLKIEN'İN ELF DİLLERİNDEN", bg=BG, fg=AMBER, font=F["label"]).pack(anchor="w")
        self.title_lab = tk.Label(head, text="", bg=BG, fg=FG, font=F["h1"])
        self.title_lab.pack(anchor="w")
        self.bar = tk.Canvas(self, height=8, bg=BG, highlightthickness=0)
        self.bar.pack(fill="x", padx=24, pady=(4, 10))
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(fill="both", expand=True, padx=(24, 0), pady=(0, 16))
        self.grid_host = tk.Frame(self.canvas, bg=BG)
        self.win = self.canvas.create_window((0, 0), window=self.grid_host, anchor="nw")
        self.grid_host.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: (self.canvas.itemconfigure(self.win, width=e.width), self._layout()))
        self.bar.bind("<Configure>", lambda _e: self._paint_bar())
        self.render()

    def _paint_bar(self):
        n, total = B.progress(self.app.prefs)
        c = self.bar
        c.delete("all")
        w = c.winfo_width()
        c.create_rectangle(0, 2, w, 6, fill=INPUT, outline="")
        c.create_rectangle(0, 2, w * n / total, 6, fill=AMBER, outline="")

    def render(self):
        n, total = B.progress(self.app.prefs)
        self.title_lab.configure(text=f"{n} / {total} rozet kazanıldı")
        self._paint_bar()
        for ch in self.grid_host.winfo_children():
            ch.destroy()
        earned = self.app.badge_earned()
        self.tiles = []
        for bid, name, lang, meaning, title, how, rarity in B.BADGES:
            got = bid in earned
            rname, rcol = B.RARITY[rarity]
            t = tk.Frame(self.grid_host, bg=PANEL, highlightthickness=1,
                         highlightbackground=mix(rcol, PANEL, .45) if got else LINE)
            tk.Label(t, image=self.app.badge_img(bid, 128, got), bg=PANEL).pack(pady=(14, 4))
            tk.Label(t, text=name, bg=PANEL, fg=FG if got else MUTED, font=F["h2"]).pack()
            tk.Label(t, text=f"{lang} · “{meaning}”", bg=PANEL, fg=AMBER if got else DIM, font=F["mono_xs"],
                     wraplength=170, justify="center").pack()
            tk.Label(t, text=f"{rname}", bg=PANEL, fg=rcol if got else DIM, font=F["label"]).pack(pady=(6, 0))
            tk.Label(t, text=title, bg=PANEL, fg=FG_2 if got else MUTED, font=F["body_b"]).pack(pady=(4, 0))
            tk.Label(t, text=how, bg=PANEL, fg=MUTED if got else DIM, font=F["tiny"], wraplength=170,
                     justify="center").pack(padx=10)
            tk.Label(t, text=(f"✦ {earned[bid]}" if got else "KİLİTLİ"), bg=PANEL, fg=GREEN if got else DIM,
                     font=F["mono_xs"]).pack(pady=(6, 14))
            self.tiles.append(t)
        self._layout()

    def _layout(self):
        w = max(self.canvas.winfo_width(), 400)
        cols = max(2, min(5, w // 196))
        for i, t in enumerate(self.tiles):
            t.grid(row=i // cols, column=i % cols, padx=6, pady=6, sticky="nsew")
        for c in range(5):
            self.grid_host.grid_columnconfigure(c, weight=1 if c < cols else 0, uniform="b" if c < cols else "")
