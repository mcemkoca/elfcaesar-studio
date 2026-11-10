"""Hoş geldin tanıtımı: uygulamayı kuranlara hediye — ilk açılışta oynayan sinematik intro.

Yıldız alanı → altın parçacıklar çekirdekte toplanır → halkalar → logo belirir → başlık yazılır →
Dante imzası kalemle yazılır gibi açılır → “Kurucu Elf” rozeti hediye kartı. Esc / GEÇ ile atlanabilir.
"""
from __future__ import annotations

import math
import random
import time
import tkinter as tk

from .theme import F, AMBER, CYAN, FG, FG_2, MUTED, DIM, GREEN, mix
from .widgets import StudioButton, rounded_points
from .sigil import sigil

BG = "#04070c"


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class IntroExperience:
    DURATION = 9.0  # hediye kartı bu andan sonra açılır

    def __init__(self, app, on_done, founder_id: str, founder_date: str, replay=False):
        self.app, self.on_done = app, on_done
        self.founder_id, self.founder_date, self.replay = founder_id, founder_date, replay
        self.frame = tk.Frame(app, bg=BG)
        self.frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.frame.lift()
        self.c = tk.Canvas(self.frame, bg=BG, highlightthickness=0, bd=0)
        self.c.pack(fill="both", expand=True)
        self.t0 = time.monotonic()
        self.rng = random.Random(7)
        self.logo_frames = [app.img(f"intro_a{i}") for i in range(1, 7)]
        self.sig = app.img("dante_sig_300")
        self.done = False
        self.card_shown = False
        self._job = None
        self.dy = 0.0
        self.card_k = 0.0
        self.app.update_idletasks()
        self._build()
        skip = StudioButton(self.c, "GEÇ  ›", self.finish, "ghost", None, "sm")
        self.skip_win = self.c.create_window(0, 0, window=skip, anchor="ne")
        self.c.bind("<Configure>", lambda _e: self._layout())
        app.bind("<Escape>", lambda _e: self.finish(), add="+")
        self._layout()
        self._tick()

    # ------------------------------------------------------------ sahne
    def _size(self):
        w = max(self.c.winfo_width(), self.app.winfo_width(), 800)
        h = max(self.c.winfo_height(), self.app.winfo_height(), 560)
        return w, h

    def _build(self):
        w, h = self._size()
        self.stars = []
        for _ in range(160):
            x, y = self.rng.random(), self.rng.random()
            r = self.rng.choice((1, 1, 1, 1.5, 2))
            item = self.c.create_oval(0, 0, 0, 0, fill=BG, outline="")
            self.stars.append((item, x, y, r, self.rng.random() * 6.28, .4 + self.rng.random() * 1.6))
        self.rings = [self.c.create_arc(0, 0, 0, 0, start=0, extent=0, style="arc", outline=col, width=wd)
                      for col, wd in ((mix(AMBER, BG, .2), 2), (mix(CYAN, BG, .35), 1), (mix(AMBER, BG, .6), 1))]
        self.pulse = self.c.create_oval(0, 0, 0, 0, outline=BG, width=1)
        self.particles = []
        for i in range(80):
            ang = self.rng.random() * 6.28
            dist = .55 + self.rng.random() * .5
            target = i / 80 * 6.28
            col = self.rng.choice((AMBER, AMBER, "#ffd994", CYAN))
            item = self.c.create_oval(0, 0, 0, 0, fill=BG, outline="")
            self.particles.append((item, ang, dist, target, col, .7 + self.rng.random() * .9, self.rng.random() * .6))
        self.logo = self.c.create_image(0, 0, image=None)
        self.title = self.c.create_text(0, 0, text="", fill=FG, font=F["display"])
        self.tagline = self.c.create_text(0, 0, text="Metnini dönüştür.  Kodunu çöz.  Kontrol sende.", fill=BG, font=F["body"])
        self.byline = self.c.create_text(0, 0, text="BİR DANTE ESERİ", fill=BG, font=F["label"])
        self.sig_item = self.c.create_image(0, 0, image=self.sig, anchor="w") if self.sig else None
        self.cover = self.c.create_rectangle(0, 0, 0, 0, fill=BG, outline="")
        self.pen = self.c.create_oval(0, 0, 0, 0, fill=BG, outline="")

    def _layout(self):
        w, h = self._size()
        self.w, self.h = w, h
        self.cx, self.cy = w / 2, h * .36 - self.dy
        self.R = min(w, h) * .2
        self.c.coords(self.skip_win, w - 24, 22)
        self.c.coords(self.logo, self.cx, self.cy)
        self.c.coords(self.title, self.cx, self.cy + self.R + 58)
        self.c.coords(self.tagline, self.cx, self.cy + self.R + 100)
        self.c.coords(self.byline, self.cx, self.cy + self.R + 140)
        if self.sig_item:
            sw = self.sig.width()
            self.sig_x0 = self.cx - sw / 2
            far = self.cy + self.R + 140 + 18 + self.sig.height() / 2
            near = self.cy + self.R + 58 + 34 + self.sig.height() / 2
            self.sig_y = far + (near - far) * self.card_k
            self.c.coords(self.sig_item, self.sig_x0, self.sig_y)

    # ------------------------------------------------------------ zaman çizelgesi
    def _tick(self):
        if self.done or not self.c.winfo_exists():
            return
        t = time.monotonic() - self.t0
        self._frame(t)
        if t >= self.DURATION and not self.card_shown:
            self._show_card()
        self._job = self.app.after(33, self._tick)

    def _frame(self, t):
        w, h, cx, cy, R = self.w, self.h, self.cx, self.cy, self.R
        fade = ease(t / 1.2)
        for item, x, y, r, ph, sp in self.stars:
            tw = .45 + .55 * (0.5 + 0.5 * math.sin(ph + t * sp))
            self.c.coords(item, x * w - r, y * h - r, x * w + r, y * h + r)
            self.c.itemconfigure(item, fill=mix(BG, "#c9d6e6", fade * tw * .8))
        # parçacıklar: dağınık → yörünge
        for item, ang, dist, target, col, sp, delay in self.particles:
            k = ease((t - .5 - delay) / 2.2)
            orbit = target + t * .25 * sp
            fx, fy = cx + math.cos(ang) * dist * w, cy + math.sin(ang) * dist * h
            tx, ty = cx + math.cos(orbit) * R * 1.32, cy + math.sin(orbit) * R * 1.32
            x, y = fx + (tx - fx) * k, fy + (ty - fy) * k
            r = 1.6 + 1.4 * k
            self.c.coords(item, x - r, y - r, x + r, y + r)
            self.c.itemconfigure(item, fill=mix(BG, col, min(1, (t - delay) / 1.0) if t > delay else 0))
        # halkalar
        g = ease((t - 1.2) / 2.0)
        for i, (arc, k, spd) in enumerate(zip(self.rings, (1.12, .96, 1.25), (30, -45, 18))):
            rr = R * k
            self.c.coords(arc, cx - rr, cy - rr, cx + rr, cy + rr)
            self.c.itemconfigure(arc, start=(t * spd) % 360, extent=-359 * g if i % 2 else 359 * g)
        # nabız
        if t > 3.2:
            p = ((t - 3.2) % 2.4) / 2.4
            pr = R * (.6 + .9 * p)
            self.c.coords(self.pulse, cx - pr, cy - pr, cx + pr, cy + pr)
            self.c.itemconfigure(self.pulse, outline=mix(AMBER, BG, min(1, .35 + p)))
        # logo belirir
        if t > 2.4 and self.logo_frames[0] is not None:
            idx = min(5, int((t - 2.4) / .16))
            self.c.itemconfigure(self.logo, image=self.logo_frames[idx])
        # başlık daktilo
        text = "ElfCaesar Studio"
        n = int(max(0, min(len(text), (t - 3.6) / 1.2 * len(text))))
        self.c.itemconfigure(self.title, text=text[:n] + ("▍" if 3.6 < t < 5.2 and int(t * 4) % 2 else ""))
        gone = 1 - min(1.0, self.card_k * 2)
        self.c.itemconfigure(self.tagline, fill=mix(BG, MUTED, ease((t - 5.0) / .8) * gone))
        self.c.itemconfigure(self.byline, fill=mix(BG, AMBER, ease((t - 5.8) / .6) * gone))
        # Dante imzası kalemle yazılır
        if self.sig_item:
            sw, sh = self.sig.width(), self.sig.height()
            k = ease((t - 6.1) / 1.9) if t > 6.1 else 0
            x = self.sig_x0 + sw * k
            self.c.coords(self.cover, x, self.sig_y - sh / 2 - 2, self.sig_x0 + sw + 4, self.sig_y + sh / 2 + 2)
            if 6.1 < t < 8.2:
                py = self.sig_y + math.sin(t * 22) * sh * .18
                self.c.coords(self.pen, x - 3, py - 3, x + 3, py + 3)
                self.c.itemconfigure(self.pen, fill="#ffe3a8")
            else:
                self.c.itemconfigure(self.pen, fill=BG)

    # ------------------------------------------------------------ hediye kartı
    def _show_card(self):
        self.card_shown = True
        card = tk.Frame(self.c, bg="#0d1622", highlightthickness=1, highlightbackground=mix(AMBER, BG, .45))
        top = tk.Frame(card, bg="#0d1622")
        top.pack(fill="x", padx=22, pady=(18, 8))
        badge = tk.Canvas(top, width=74, height=74, bg="#0d1622", highlightthickness=0)
        badge.pack(side="left")
        badge.create_polygon(rounded_points(2, 2, 72, 72, 16), smooth=True, fill="#0a0f16", outline=AMBER, width=2)
        sg = sigil(self.founder_id)
        cell = 8
        for r, col in sg["cells"]:
            badge.create_rectangle(9 + col * cell, 9 + r * cell, 9 + col * cell + cell - 1, 9 + r * cell + cell - 1,
                                   fill=AMBER if (r + col) % 3 else "#ffd994", outline="")
        txt = tk.Frame(top, bg="#0d1622")
        txt.pack(side="left", padx=16)
        tk.Label(txt, text="HOŞ GELDİN HEDİYEN", bg="#0d1622", fg=AMBER, font=F["label"]).pack(anchor="w")
        tk.Label(txt, text="Kurucu Elf Rozeti", bg="#0d1622", fg=FG, font=F["h1"]).pack(anchor="w", pady=(2, 0))
        tk.Label(txt, text=f"№ {self.founder_id[:4].upper()}-{self.founder_id[4:8].upper()}  ·  {self.founder_date}",
                 bg="#0d1622", fg=MUTED, font=F["mono_sm"]).pack(anchor="w")
        for line in ("Bu rozet yalnızca senin bilgisayarında üretildi; Hakkında penceresinde seninle kalır.",
                     "Güvenlik Merkezi'nde parolanın kırılma süresini ve kırma maliyetini ölçebilirsin.",
                     "Mesaj Köprüsü ile WhatsApp ve Telegram mesajlarını uçtan uca şifreleyebilirsin."):
            row = tk.Frame(card, bg="#0d1622")
            row.pack(fill="x", padx=24, pady=2)
            tk.Label(row, text="✦", bg="#0d1622", fg=GREEN, font=F["small"]).pack(side="left")
            tk.Label(row, text=line, bg="#0d1622", fg=FG_2, font=F["small"]).pack(side="left", padx=6)
        bar = tk.Frame(card, bg="#0d1622")
        bar.pack(fill="x", padx=22, pady=(14, 18))
        StudioButton(bar, "BAŞLAYALIM", self.finish, "primary", "spark", min_width=170).pack(side="right")
        tk.Label(bar, text="Tanıtımı Hakkında penceresinden yeniden izleyebilirsin.", bg="#0d1622", fg=DIM,
                 font=F["tiny"]).pack(side="left")
        win = self.c.create_window(self.cx, self.h + 400, window=card, anchor="s")
        target = self.h - 24
        self.c.update_idletasks()
        card_h = card.winfo_reqheight()
        sig_h = self.sig.height() if self.sig else 0
        bottom = self.h * .36 + self.R + 58 + 34 + sig_h
        need = max(0.0, bottom + 16 - (target - card_h))
        room = max(0.0, self.h * .36 - self.R * 1.35 - 8)
        dy_target = min(need, room)

        def rise(i=0):
            if self.done:
                return
            k = ease(i / 22)
            self.dy = dy_target * k  # sahne yukarı kayar ki kart imzayı kapatmasın
            self.card_k = k
            self._layout()
            self.c.coords(win, self.cx, self.h + 400 + (target - self.h - 400) * k)
            if i < 22:
                self.app.after(16, lambda: rise(i + 1))
        rise()

    def finish(self):
        if self.done:
            return
        self.done = True
        if self._job:
            try:
                self.app.after_cancel(self._job)
            except tk.TclError:
                pass
        if self.frame.winfo_exists():
            self.frame.destroy()
        self.on_done()
