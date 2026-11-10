"""ELFCAESAR STUDIO 6.5 — özel görsel bileşenler (yalnızca tkinter)."""
from __future__ import annotations

import math
import time
import tkinter as tk
import tkinter.font as tkfont

from . import icons
from .theme import (TIER_COLORS, STRENGTH_COLORS, F, BG, PANEL, PANEL_2, PANEL_3, INPUT, LINE, LINE_2, FG, FG_2, MUTED, DIM,
                    AMBER, AMBER_2, CYAN, GREEN, RED, VIOLET, LEVEL_COLORS, mix)
from .sigil import sigil, short_fingerprint, format_fingerprint


def rounded_points(x1, y1, x2, y2, r):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y1 + r,
            x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1]


def bg_of(widget) -> str:
    try:
        return widget.cget("bg")
    except tk.TclError:
        return BG


# ---------------------------------------------------------------- buttons
import os as _os
REDUCED_MOTION = _os.environ.get("ELFCAESAR_REDUCED_MOTION") == "1"

VARIANTS = {
    #            fill       outline     text       hover_fill  hover_outline  hover_text
    "primary":  (AMBER,     AMBER,      "#121a26", AMBER_2,    AMBER_2,       "#121a26"),
    "accent":   ("#0f2a33", "#2c6f7a",  CYAN,      "#143844",  CYAN,          "#a9f0f8"),
    "secondary": (PANEL_2,  LINE_2,     FG_2,      PANEL_3,    "#45657f",     FG),
    "ghost":    (None,      None,       MUTED,     PANEL_2,    None,          FG),
    "danger":   ("#2a1519", "#6b2a33",  RED,       "#3a1a20",  RED,           "#ffb0b0"),
}


class StudioButton(tk.Canvas):
    """Yuvarlatılmış, ikonlu, klavye erişimli buton.

    Varyantlar: primary · accent · secondary · ghost · danger. Boyutlar: md · sm.
    """

    def __init__(self, parent, text="", command=None, variant="secondary", icon=None,
                 size="md", tooltip=None, min_width=0):
        self._bg = bg_of(parent)
        self._text = text
        self._icon = icon
        self._command = command
        self._variant = variant if variant in VARIANTS else "secondary"
        self._size = size
        self._enabled = True
        self._state = "normal"
        self._focus = False
        self._min_width = min_width
        self._font = F["button_sm"] if size == "sm" else F["button"]
        w, h = self._measure()
        super().__init__(parent, width=w, height=h, bg=self._bg, highlightthickness=0, bd=0,
                         cursor="hand2", takefocus=1)
        self._paint()
        self.bind("<Enter>", lambda _e: self._set("hover"))
        self.bind("<Leave>", lambda _e: self._set("normal"))
        self.bind("<ButtonPress-1>", lambda _e: self._set("pressed"))
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<FocusIn>", lambda _e: self._focus_change(True))
        self.bind("<FocusOut>", lambda _e: self._focus_change(False))
        self.bind("<Return>", lambda _e: self.invoke())
        self.bind("<space>", lambda _e: self.invoke())
        if tooltip:
            Tooltip(self, tooltip)

    # ---- 3B görünüm: alt kenar (derinlik), parlak üst yüz, yumuşak hover geçişi, basınca içeri gömülme
    DEPTH = 3

    def _colors(self):
        fill, outline, text, hfill, houtline, htext = VARIANTS[self._variant]
        if not self._enabled:
            return (PANEL if fill else None), (LINE if outline else None), DIM
        t = getattr(self, "_t", 0.0)
        if fill is None and hfill is not None:
            f = mix(self._bg, hfill, t) if t > 0.02 else None
        elif fill is not None and hfill is not None:
            f = mix(fill, hfill, t)
        else:
            f = fill
        o = (mix(outline, houtline, t) if outline and houtline else (houtline if houtline and t > .5 else outline))
        tx = mix(text, htext, t)
        if self._state == "pressed" and f:
            f = mix(f, BG, .18)
        return f, o, tx

    def _paint(self):
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        fill, outline, text = self._colors()
        t = getattr(self, "_t", 0.0)
        d = self.DEPTH
        solid = fill is not None
        if self._focus and self._enabled:
            outline = CYAN
        r = 8
        # gömülme ofseti: normal 1px, hover 0px (kalkar), basılı = derinlik (içeri)
        if not self._enabled or not solid:
            off = d if not solid else 1
        elif self._state == "pressed":
            off = d
        else:
            off = round(1 - t)
        top, bottom = 1 + off, h - 1 - d + off
        if solid:
            edge = mix(fill, "#000000", .55 if self._variant != "primary" else .42)
            self.create_polygon(rounded_points(1, 1 + d, w - 1, h - 1, r), smooth=True, fill=edge, outline=edge)
            self.create_polygon(rounded_points(1, top, w - 1, bottom, r), smooth=True, fill=fill,
                                outline=outline or fill, width=1)
            if self._enabled:
                mid = top + (bottom - top) * .48
                gloss = mix(fill, "#ffffff", (.10 if self._variant == "primary" else .05) + .05 * t)
                self.create_polygon(rounded_points(3, top + 2, w - 3, mid, r - 2), smooth=True, fill=gloss, outline=gloss)
                hl = mix(fill, "#ffffff", .38 if self._variant == "primary" else .16)
                self.create_line(r, top + 1, w - r, top + 1, fill=hl)
                shine = getattr(self, "_shine", None)
                if shine is not None:
                    sc = mix(fill, "#ffffff", .32 if self._variant == "primary" else .14)
                    x0 = shine
                    pts = [x0, bottom - 1, x0 + 9, top + 1, x0 + 21, top + 1, x0 + 12, bottom - 1]
                    pts = [min(max(v, 5), w - 5) if i % 2 == 0 else v for i, v in enumerate(pts)]
                    self.create_polygon(pts, fill=sc, outline="")
        elif outline:
            self.create_polygon(rounded_points(1, top, w - 1, bottom, r), smooth=True, fill=self._bg, outline=outline, width=1)
        cy = (top + bottom) / 2
        isz = 12 if self._size == "sm" else 14
        pad = 11 if self._size == "sm" else 15
        if self._text:
            x = pad
            if self._icon:
                icons.draw(self, self._icon, x + isz / 2, cy, isz, text, width=1.5)
                x += isz + 8
            tw = tkfont.Font(font=self._font).measure(self._text)
            used = (isz + 8 if self._icon else 0) + tw
            if w > used + pad * 2:  # min_width: içeriği ortala
                shift = (w - used - pad * 2) / 2
                self.move("icon", shift, 0)
                x += shift
            if solid and self._variant == "primary" and self._enabled:
                self.create_text(x, cy + 1.5, text=self._text, anchor="w", fill=mix(fill, "#ffffff", .35), font=self._font)
            self.create_text(x, cy + 0.5, text=self._text, anchor="w", fill=text, font=self._font)
        elif self._icon:
            icons.draw(self, self._icon, w / 2, cy, isz, text, width=1.5)

    def _measure(self):
        h = (30 if self._size == "sm" else 36) + 2
        pad = 11 if self._size == "sm" else 15
        isz = 12 if self._size == "sm" else 14
        tw = tkfont.Font(font=self._font).measure(self._text) if self._text else 0
        if not self._text:
            return h, h
        w = pad * 2 + tw + ((isz + 8) if self._icon else 0)
        return max(w, self._min_width), h

    def _animate(self):
        target = 1.0 if self._state in ("hover", "pressed") else 0.0
        t = getattr(self, "_t", 0.0)
        t += (target - t) * 0.38
        if abs(target - t) < 0.03:
            t = target
        self._t = t
        try:
            self._paint()
            if t != target:
                self._anim = self.after(16, self._animate)
            else:
                self._anim = None
        except tk.TclError:
            pass

    def _sweep(self, x=None):
        try:
            w = int(self["width"])
            x = -24 if x is None else x
            if x > w + 4 or self._state == "normal":
                self._shine = None
                self._paint()
                return
            self._shine = x
            self._paint()
            self.after(14, lambda: self._sweep(x + max(6, w / 26)))
        except tk.TclError:
            pass

    def _set(self, state):
        if not self._enabled:
            return
        prev = self._state
        self._state = state
        if state == "hover" and prev == "normal" and self._variant in ("primary", "accent") and not REDUCED_MOTION:
            self._sweep()
        if REDUCED_MOTION:
            self._t = 1.0 if state != "normal" else 0.0
            self._paint()
        elif getattr(self, "_anim", None) is None:
            self._animate()
        if state == "pressed":
            self._paint()

    def _focus_change(self, value):
        self._focus = value
        self._paint()

    def _release(self, event):
        inside = 0 <= event.x <= int(self["width"]) and 0 <= event.y <= int(self["height"])
        self._set("hover" if inside else "normal")
        if inside:
            self.invoke()

    def invoke(self):
        if self._enabled and self._command:
            self._command()

    def set_command(self, command):
        self._command = command

    def set_enabled(self, enabled: bool):
        self._enabled = bool(enabled)
        self.configure(cursor="hand2" if enabled else "arrow")
        self._state = "normal"
        self._t = 0.0
        self._paint()

    def set_text(self, text):
        self._text = text
        w, h = self._measure()
        self.configure(width=w, height=h)
        self._paint()

    @property
    def text(self):
        return self._text


class Tooltip:
    def __init__(self, widget, text, delay=450):
        self.widget, self.text, self.delay = widget, text, delay
        self.tip = None
        self._job = None
        self.enabled = True
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e=None):
        if not self.enabled or not self.text:
            return
        self._job = self.widget.after(self.delay, self._show)

    def _show(self):
        if self.tip or not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 8
        y = self.widget.winfo_rooty() + self.widget.winfo_height() // 2 - 12
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.configure(bg=LINE_2)
        tk.Label(self.tip, text=self.text, bg=PANEL_3, fg=FG, font=F["small"],
                 padx=9, pady=5).pack(padx=1, pady=1)
        self.tip.wm_geometry(f"+{x}+{y}")

    def _hide(self, _e=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ---------------------------------------------------------------- toasts
class ToastManager:
    """Sağ altta kayarak gelen, kendiliğinden kapanan bildirimler."""

    WIDTH = 344

    def __init__(self, host):
        self.host = host
        self.toasts: list[tk.Frame] = []

    def show(self, level, title, detail="", action=None, duration=None):
        color = LEVEL_COLORS.get(level, CYAN)
        icon = {"success": "check", "info": "info", "warning": "alert", "error": "alert"}.get(level, "info")
        outer = tk.Frame(self.host, bg=mix(color, PANEL, .55), bd=0)
        card = tk.Frame(outer, bg=PANEL_2)
        card.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(card, bg=color, width=3).pack(side="left", fill="y")
        ic = tk.Canvas(card, width=30, height=30, bg=PANEL_2, highlightthickness=0)
        ic.pack(side="left", padx=(10, 2), pady=10, anchor="n")
        ic.create_oval(3, 3, 27, 27, fill=mix(color, PANEL_2, .78), outline="")
        icons.draw(ic, icon, 15, 15, 13, color, width=1.6)
        body = tk.Frame(card, bg=PANEL_2)
        body.pack(side="left", fill="both", expand=True, padx=(6, 4), pady=(9, 10))
        tk.Label(body, text=title, bg=PANEL_2, fg=FG, font=F["body_b"], anchor="w",
                 justify="left", wraplength=self.WIDTH - 110).pack(fill="x")
        if detail:
            tk.Label(body, text=detail, bg=PANEL_2, fg=MUTED, font=F["tiny"], anchor="w",
                     justify="left", wraplength=self.WIDTH - 110).pack(fill="x", pady=(2, 0))
        if action:
            label, callback = action
            StudioButton(body, label, lambda o=outer, cb=callback: (self.dismiss(o), cb()), "accent", "unlock", "sm").pack(
                anchor="w", pady=(8, 0))
        close = StudioButton(card, "", lambda o=outer: self.dismiss(o), variant="ghost", icon="close", size="sm")
        close.pack(side="right", anchor="n", padx=6, pady=6)
        self.toasts.append(outer)
        while len(self.toasts) > 4:
            self.dismiss(self.toasts[0], animate=False)
        outer._slide = self.WIDTH + 40  # type: ignore[attr-defined]
        self._layout()
        self._animate_in(outer)
        outer.after(duration or (12000 if action else 6500 if level == "error" else 4000), lambda o=outer: self.dismiss(o))
        return outer

    def _layout(self):
        self.host.update_idletasks()
        y = -54  # alt durum çubuğunun üstünde
        for toast in reversed(self.toasts):
            if not toast.winfo_exists():
                continue
            toast.place(relx=1.0, rely=1.0, x=-22 + getattr(toast, "_slide", 0), y=y,
                        anchor="se", width=self.WIDTH)
            toast.lift()
            y -= toast.winfo_reqheight() + 10

    def _animate_in(self, toast, step=0):
        if not toast.winfo_exists():
            return
        steps = 9
        t = (step + 1) / steps
        toast._slide = int((self.WIDTH + 40) * (1 - t) ** 3)  # ease-out
        self._layout()
        if step + 1 < steps:
            toast.after(16, lambda: self._animate_in(toast, step + 1))

    def dismiss(self, toast, animate=True):
        if toast not in self.toasts:
            return
        self.toasts.remove(toast)
        if toast.winfo_exists():
            toast.destroy()
        self._layout()


# ---------------------------------------------------------------- animated core
class AnimatedCore(tk.Canvas):
    """Kontrol merkezindeki animasyonlu kripto çekirdeği."""

    LABELS = (("ELFC2", 225, AMBER), ("AES-256-GCM", 315, CYAN), ("X25519", 45, GREEN), ("ED25519", 135, VIOLET))

    def __init__(self, parent, width=340, height=280, center_image=None):
        super().__init__(parent, width=width, height=height, bg=bg_of(parent), highlightthickness=0, bd=0)
        self.center_image = center_image
        self._running = False
        self._job = None
        self._t0 = time.monotonic()
        self._build()
        self.bind("<Configure>", lambda _e: self._build())

    def _geom(self):
        w = max(200, self.winfo_width() if self.winfo_width() > 1 else int(self["width"]))
        h = max(180, self.winfo_height() if self.winfo_height() > 1 else int(self["height"]))
        return w / 2, h / 2 - 4, min(w * .62, h) * .36

    def _build(self):
        self.delete("all")
        cx, cy, R = self._geom()
        self.cx, self.cy, self.R = cx, cy, R
        bg = bg_of(self)
        for i, k in enumerate((1.25, 1.05, .85, .62)):
            col = mix(bg, "#123247", .25 + i * .18)
            self.create_oval(cx - R * k, cy - R * k, cx + R * k, cy + R * k, fill=col, outline="")
        for i in range(72):
            a = math.radians(i * 5)
            long = i % 6 == 0
            r1, r2 = R * 1.1, R * (1.18 if long else 1.14)
            self.create_line(cx + r1 * math.cos(a), cy + r1 * math.sin(a), cx + r2 * math.cos(a),
                             cy + r2 * math.sin(a), fill="#3b5a72" if long else "#24394d", width=1)
        self.create_oval(cx - R, cy - R, cx + R, cy + R, outline="#1f3a50", width=1)
        self.create_oval(cx - R * .72, cy - R * .72, cx + R * .72, cy + R * .72, outline="#1d3447", width=1)
        self.pulse = self.create_oval(0, 0, 0, 0, outline=CYAN, width=1)
        self.outer = [self.create_arc(cx - R, cy - R, cx + R, cy + R, start=0, extent=68,
                                      style="arc", outline=CYAN, width=2) for _ in range(3)]
        rm = R * .72
        self.middle = [self.create_arc(cx - rm, cy - rm, cx + rm, cy + rm, start=0, extent=30,
                                       style="arc", outline=mix(AMBER, bg, .25), width=2) for _ in range(6)]
        self.sweep = [self.create_line(cx, cy, cx, cy, fill=mix(CYAN, bg, .35 + i * .16), width=2 if i == 0 else 1)
                      for i in range(5)]
        self.hexagon = self.create_polygon(0, 0, 0, 0, outline="#47708a", fill="", width=1.4)
        self.tri_a = self.create_polygon(0, 0, 0, 0, outline=mix(AMBER, bg, .45), fill="", width=1)
        self.tri_b = self.create_polygon(0, 0, 0, 0, outline=mix(CYAN, bg, .45), fill="", width=1)
        rc = R * .2
        if self.center_image is not None:
            rc = max(rc, self.center_image.width() / 2 + 6)
            self.create_oval(cx - rc, cy - rc, cx + rc, cy + rc, fill="#0b1118", outline=AMBER, width=2)
            self.create_image(cx, cy, image=self.center_image)
            self.star = None
        else:
            self.create_oval(cx - rc, cy - rc, cx + rc, cy + rc, fill="#112838", outline=CYAN, width=2)
            self.star = self.create_polygon(0, 0, 0, 0, fill=AMBER, outline="")
        self.core_r = rc
        self.nodes = []
        for color, radius in ((AMBER, .86), (CYAN, .86), (GREEN, .5)):
            trail = [self.create_oval(0, 0, 0, 0, fill=mix(color, bg, .45 + i * .2), outline="") for i in range(2)]
            dot = self.create_oval(0, 0, 0, 0, fill=color, outline="")
            self.nodes.append((dot, trail, radius))
        for text, ang, color in self.LABELS:
            a = math.radians(ang)
            x, y = cx + R * 1.18 * math.cos(a), cy + R * 1.18 * math.sin(a)
            lx = x + (34 if math.cos(a) > 0 else -34)
            ly = y + (12 if math.sin(a) > 0 else -12)
            self.create_line(x, y, lx, ly, fill="#2b4a60")
            self.create_oval(x - 2.5, y - 2.5, x + 2.5, y + 2.5, fill=color, outline="")
            self.create_text(lx + (4 if math.cos(a) > 0 else -4), ly, text=text, fill=MUTED,
                             font=F["mono_xs"], anchor="w" if math.cos(a) > 0 else "e")
        self._frame()

    def _poly(self, n, radius, rot, item):
        pts = []
        for i in range(n):
            a = rot + i * 2 * math.pi / n
            pts += [self.cx + radius * math.cos(a), self.cy + radius * math.sin(a)]
        self.coords(item, *pts)

    def _frame(self):
        t = time.monotonic() - self._t0
        cx, cy, R = self.cx, self.cy, self.R
        bg = bg_of(self)
        a = (t * 24) % 360
        for i, arc in enumerate(self.outer):
            self.itemconfigure(arc, start=a + i * 120)
        for i, arc in enumerate(self.middle):
            self.itemconfigure(arc, start=-a * 1.6 + i * 60)
        rot = math.radians(t * 12)
        inner = max(R * .44, self.core_r + 12)
        self._poly(6, inner, rot, self.hexagon)
        self._poly(3, inner * .95, -rot * 1.5, self.tri_a)
        self._poly(3, inner * .95, -rot * 1.5 + math.pi, self.tri_b)
        # Nabız halkası
        p = (t % 2.6) / 2.6
        pr = self.core_r + (R * 1.1 - self.core_r) * p
        self.coords(self.pulse, cx - pr, cy - pr, cx + pr, cy + pr)
        self.itemconfigure(self.pulse, outline=mix(CYAN, bg, min(1, p * 1.1)))
        # Merkez yıldız (nefes alan)
        if self.star is None:
            s = 0
        else:
            s = R * (.13 + .018 * math.sin(t * 2.4))
        if self.star is not None:
            pts = []
            for i in range(8):
                ang = -math.pi / 2 + i * math.pi / 4
                rr = s if i % 2 == 0 else s * .38
                pts += [cx + rr * math.cos(ang), cy + rr * math.sin(ang)]
            self.coords(self.star, *pts)
        # Tarama çizgisi
        for i, line in enumerate(self.sweep):
            ang = math.radians(t * 70 - i * 5)
            r0 = self.core_r + 2
            self.coords(line, cx + r0 * math.cos(ang), cy + r0 * math.sin(ang),
                        cx + R * .98 * math.cos(ang), cy + R * .98 * math.sin(ang))
        # Yörünge düğümleri
        speeds = (.9, -.6, 1.7)
        for (dot, trail, radius), sp, ph in zip(self.nodes, speeds, (0, 2.1, 4.2)):
            for j, item in enumerate([dot] + trail):
                ang = t * sp + ph - j * .09 * (1 if sp > 0 else -1)
                r = 4.5 - j * 1.2
                x, y = cx + R * radius * math.cos(ang), cy + R * radius * math.sin(ang)
                self.coords(item, x - r, y - r, x + r, y + r)

    def _tick(self):
        if not self._running:
            return
        if self.winfo_exists() and self.winfo_ismapped():
            self._frame()
        self._job = self.after(33, self._tick)

    def start(self):
        if not self._running:
            self._running = True
            self._tick()

    def stop(self):
        self._running = False
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None


# ---------------------------------------------------------------- charts
class ActivityChart(tk.Canvas):
    """Son 30 dakikanın dakika bazlı işlem grafiği."""

    def __init__(self, parent, height=170):
        super().__init__(parent, height=height, bg=bg_of(parent), highlightthickness=0, bd=0)
        self.data: list[int] = []
        self._hover = None
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda _e: self._set_hover(None))

    def set_data(self, data):
        self.data = list(data)
        self.redraw()

    def _set_hover(self, idx):
        if idx != self._hover:
            self._hover = idx
            self.redraw()

    def _motion(self, e):
        if not self.data:
            return
        left, right = 34, self.winfo_width() - 8
        step = (right - left) / len(self.data)
        idx = int((e.x - left) // step) if left <= e.x <= right else None
        self._set_hover(idx if idx is not None and 0 <= idx < len(self.data) else None)

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50 or not self.data:
            return
        left, right, top, bottom = 34, w - 8, 14, h - 22
        peak = max(max(self.data), 4)
        for i in range(4):
            y = bottom - (bottom - top) * i / 3
            self.create_line(left, y, right, y, fill="#1a2a3b" if i else LINE)
            self.create_text(left - 8, y, text=str(round(peak * i / 3)), fill=DIM, font=F["mono_xs"], anchor="e")
        n = len(self.data)
        step = (right - left) / n
        bw = max(3, step * .62)
        for i, v in enumerate(self.data):
            x = left + step * i + (step - bw) / 2
            if v == 0:
                self.create_line(x, bottom - 1, x + bw, bottom - 1, fill="#21364a", width=2)
                continue
            y = bottom - (bottom - top) * v / peak
            hot = i == self._hover
            col = AMBER if hot else mix("#2f6f80", CYAN, v / peak)
            self.create_polygon(rounded_points(x, y, x + bw, bottom, min(3, bw / 2)), smooth=True, fill=col, outline="")
        if self._hover is not None:
            v = self.data[self._hover]
            ago = n - 1 - self._hover
            x = left + step * self._hover + step / 2
            label = f"{v} işlem · {'şimdi' if ago == 0 else f'{ago} dk önce'}"
            tw = tkfont.Font(font=F["mono_xs"]).measure(label) + 16
            bx = min(max(left, x - tw / 2), right - tw)
            self.create_polygon(rounded_points(bx, top - 12, bx + tw, top + 8, 5), smooth=True, fill=PANEL_3, outline=LINE_2)
            self.create_text(bx + tw / 2, top - 2, text=label, fill=FG, font=F["mono_xs"])
        for label, idx in (("-30 dk", 0), ("-15 dk", n // 2), ("şimdi", n - 1)):
            x = left + step * idx + step / 2
            self.create_text(x, h - 9, text=label, fill=DIM, font=F["mono_xs"])
        if not any(self.data):
            self.create_text((left + right) / 2, (top + bottom) / 2, fill=MUTED, font=F["small"],
                             text="Henüz işlem yok — bir işlem yaptığında grafik canlanır.")


class CategoryBars(tk.Canvas):
    def __init__(self, parent, rows, height=170):
        super().__init__(parent, height=height, bg=bg_of(parent), highlightthickness=0, bd=0)
        self.rows = rows  # [(key, label, color)]
        self.values: dict[str, int] = {}
        self.bind("<Configure>", lambda _e: self.redraw())

    def set_values(self, values):
        self.values = dict(values)
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 60:
            return
        peak = max([1] + list(self.values.values()))
        y = 10
        label_w = 70
        for key, label, color in self.rows:
            v = self.values.get(key, 0)
            self.create_text(0, y + 5, text=label.upper(), fill=MUTED, font=F["mono_xs"], anchor="w")
            x1, x2 = label_w, w - 34
            self.create_polygon(rounded_points(x1, y, x2, y + 10, 5), smooth=True, fill="#16263a", outline="")
            if v:
                xe = x1 + max(10, (x2 - x1) * v / peak)
                self.create_polygon(rounded_points(x1, y, xe, y + 10, 5), smooth=True, fill=color, outline="")
            self.create_text(w - 2, y + 5, text=str(v), fill=FG if v else DIM, font=F["mono_b"], anchor="e")
            y += 26


class ScoreChart(tk.Canvas):
    """29 kaydırmanın Türkçe benzerlik puanları; tıklanınca aday seçilir."""

    def __init__(self, parent, on_select=None, height=150):
        super().__init__(parent, height=height, bg=bg_of(parent), highlightthickness=0, bd=0, cursor="hand2")
        self.scores: list[tuple[int, int]] = []
        self.best = None
        self.selected = None
        self._hover = None
        self.on_select = on_select
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda _e: self._set_hover(None))
        self.bind("<Button-1>", self._click)

    def set_scores(self, scores, best=None):
        self.scores, self.best, self.selected = list(scores), best, None
        self.redraw()

    def select(self, shift):
        self.selected = shift
        self.redraw()

    def _index_at(self, x):
        if not self.scores:
            return None
        left, right = 30, self.winfo_width() - 6
        step = (right - left) / len(self.scores)
        i = int((x - left) // step)
        return i if 0 <= i < len(self.scores) else None

    def _set_hover(self, idx):
        if idx != self._hover:
            self._hover = idx
            self.redraw()

    def _motion(self, e):
        self._set_hover(self._index_at(e.x))

    def _click(self, e):
        i = self._index_at(e.x)
        if i is not None and self.on_select:
            self.on_select(self.scores[i][0])

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 60:
            return
        left, right, top, bottom = 30, w - 6, 18, h - 20
        for v in (0, 50, 100):
            y = bottom - (bottom - top) * v / 100
            self.create_line(left, y, right, y, fill=LINE if v == 0 else "#192a3c")
            self.create_text(left - 6, y, text=str(v), fill=DIM, font=F["mono_xs"], anchor="e")
        if not self.scores:
            self.create_text((left + right) / 2, (top + bottom) / 2, fill=MUTED, font=F["small"],
                             text="Analiz çalıştırıldığında 29 kaydırmanın benzerlik puanı burada görünür.")
            return
        step = (right - left) / len(self.scores)
        bw = max(3, step * .64)
        for i, (shift, score) in enumerate(self.scores):
            x = left + step * i + (step - bw) / 2
            y = bottom - (bottom - top) * max(score, 2) / 100
            if shift == self.best:
                col = AMBER
            elif shift == self.selected:
                col = CYAN
            else:
                col = mix("#254a5c", "#4fb3c2", score / 100)
            if i == self._hover:
                col = mix(col, "#ffffff", .25)
            self.create_polygon(rounded_points(x, y, x + bw, bottom, min(3, bw / 2)), smooth=True, fill=col, outline="")
            if shift == self.selected:
                self.create_line(x, bottom + 3, x + bw, bottom + 3, fill=CYAN, width=2)
            if len(self.scores) <= 29 and (i % 2 == 0 or step > 26):
                self.create_text(x + bw / 2, h - 8, text=f"{shift:02d}", fill=DIM, font=F["mono_xs"])
        if self._hover is not None:
            shift, score = self.scores[self._hover]
            label = f"SHIFT {shift:02d} · PUAN {score}"
            tw = tkfont.Font(font=F["mono_xs"]).measure(label) + 16
            x = left + step * self._hover + step / 2
            bx = min(max(left, x - tw / 2), right - tw)
            self.create_polygon(rounded_points(bx, 0, bx + tw, 16, 5), smooth=True, fill=PANEL_3, outline=LINE_2)
            self.create_text(bx + tw / 2, 8, text=label, fill=FG, font=F["mono_xs"])


# ---------------------------------------------------------------- misc
class Segmented(tk.Frame):
    """Sekmeli seçim kontrolü."""

    def __init__(self, parent, options, command=None, value=None):
        super().__init__(parent, bg=INPUT, highlightbackground=LINE, highlightthickness=1)
        self.command = command
        self.items = {}
        self.value = value or options[0][0]
        for key, label in options:
            lab = tk.Label(self, text=label, bg=INPUT, fg=MUTED, font=F["button_sm"], padx=12, pady=6, cursor="hand2")
            lab.pack(side="left", padx=2, pady=2)
            lab.bind("<Button-1>", lambda _e, k=key: self.set(k, notify=True))
            lab.bind("<Enter>", lambda _e, k=key: self._hover(k, True))
            lab.bind("<Leave>", lambda _e, k=key: self._hover(k, False))
            self.items[key] = lab
        self._paint()

    def _hover(self, key, on):
        if key != self.value:
            self.items[key].configure(fg=FG if on else MUTED)

    def _paint(self):
        for key, lab in self.items.items():
            active = key == self.value
            lab.configure(bg=PANEL_3 if active else INPUT, fg=AMBER if active else MUTED)

    def set(self, key, notify=False):
        self.value = key
        self._paint()
        if notify and self.command:
            self.command(key)


class Chip(tk.Label):
    def __init__(self, parent, text, color=CYAN):
        super().__init__(parent, text=text, bg=mix(color, PANEL, .82), fg=color, font=F["label"], padx=8, pady=3)

    def set(self, text, color=None):
        if color:
            self.configure(fg=color, bg=mix(color, PANEL, .82))
        self.configure(text=text)


class DropZone(tk.Canvas):
    """Kesikli çerçeveli dosya bırakma alanı; tıklanınca dosya seçtirir."""

    def __init__(self, parent, title, subtitle, on_click=None, height=128):
        super().__init__(parent, height=height, bg=bg_of(parent), highlightthickness=0, bd=0, cursor="hand2", takefocus=1)
        self.title, self.subtitle, self.on_click = title, subtitle, on_click
        self.active = False
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Enter>", lambda _e: self.set_active(True))
        self.bind("<Leave>", lambda _e: self.set_active(False))
        self.bind("<Button-1>", lambda _e: self.on_click and self.on_click())
        self.bind("<Return>", lambda _e: self.on_click and self.on_click())

    def set_active(self, value):
        self.active = value
        self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40:
            return
        color = CYAN if self.active else LINE_2
        fill = mix(CYAN, bg_of(self), .9) if self.active else INPUT
        self.create_polygon(rounded_points(2, 2, w - 2, h - 2, 12), smooth=True, fill=fill, outline="")
        self.create_polygon(rounded_points(2, 2, w - 2, h - 2, 12), smooth=True, fill="", outline=color, dash=(6, 4), width=1.4)
        cy = h / 2 - 16
        self.create_oval(w / 2 - 19, cy - 19, w / 2 + 19, cy + 19, fill=mix(color, fill, .8), outline="")
        icons.draw(self, "drop", w / 2, cy, 18, CYAN if self.active else MUTED, width=1.7)
        self.create_text(w / 2, cy + 34, text=self.title, fill=FG, font=F["body_b"])
        self.create_text(w / 2, cy + 52, text=self.subtitle, fill=MUTED, font=F["tiny"])


class IdentityCard(tk.Frame):
    """Görsel kimlik kartı: mühür, ad, rol ve parmak izi."""

    ROLE_COLORS = {"KİMLİĞİN": AMBER, "KİŞİ KARTI": CYAN, "GÖNDEREN": GREEN, "GÜVENİLEN": VIOLET}

    def __init__(self, parent, name, fingerprint, role, note, on_copy=None, on_remove=None):
        accent = self.ROLE_COLORS.get(role, CYAN)
        super().__init__(parent, bg=mix(accent, PANEL, .7))
        inner = tk.Frame(self, bg=PANEL_2)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(inner, bg=accent, height=3).pack(fill="x")
        top = tk.Frame(inner, bg=PANEL_2)
        top.pack(fill="x", padx=14, pady=(12, 6))
        sg = sigil(fingerprint)
        size, cell = sg["size"], 9
        box = size * cell + 12
        canvas = tk.Canvas(top, width=box, height=box, bg=INPUT, highlightthickness=1,
                           highlightbackground=LINE_2)
        canvas.pack(side="left")
        for r, c in sg["cells"]:
            col = sg["primary"] if (r + c) % 3 else sg["secondary"]
            x, y = 6 + c * cell, 6 + r * cell
            canvas.create_rectangle(x + 1, y + 1, x + cell - 1, y + cell - 1, fill=col, outline="")
        meta = tk.Frame(top, bg=PANEL_2)
        meta.pack(side="left", fill="both", expand=True, padx=(12, 0))
        Chip(meta, role, accent).pack(anchor="w")
        tk.Label(meta, text=name, bg=PANEL_2, fg=FG, font=F["h3"], anchor="w").pack(anchor="w", pady=(6, 1))
        tk.Label(meta, text=short_fingerprint(fingerprint), bg=PANEL_2, fg=accent, font=F["mono_b"]).pack(anchor="w")
        tk.Label(inner, text="PARMAK İZİ · SHA-256", bg=PANEL_2, fg=DIM, font=F["label"]).pack(anchor="w", padx=14, pady=(6, 2))
        tk.Label(inner, text=format_fingerprint(fingerprint), bg=PANEL_2, fg=FG_2, font=F["mono_xs"],
                 justify="left").pack(anchor="w", padx=14)
        tk.Label(inner, text=note, bg=PANEL_2, fg=MUTED, font=F["tiny"], justify="left",
                 wraplength=300).pack(anchor="w", padx=14, pady=(8, 6))
        bar = tk.Frame(inner, bg=PANEL_2)
        bar.pack(fill="x", padx=12, pady=(0, 12))
        if on_copy:
            StudioButton(bar, "PARMAK İZİNİ KOPYALA", on_copy, "secondary", "copy", "sm").pack(side="left")
        if on_remove:
            StudioButton(bar, "", on_remove, "ghost", "close", "sm", tooltip="Kartı listeden kaldır").pack(side="right")


class ShiftSlider(tk.Canvas):
    """Özel çizimli kaydırma seçici (0–28); fare, sürükleme ve ok tuşlarıyla çalışır."""

    def __init__(self, parent, variable, maximum=28, height=34):
        super().__init__(parent, height=height, bg=bg_of(parent), highlightthickness=0, bd=0,
                         cursor="hand2", takefocus=1)
        self.var, self.maximum = variable, maximum
        self._hover = False
        self._focus = False
        self._trace = variable.trace_add("write", lambda *_a: self.redraw())
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Button-1>", self._pick)
        self.bind("<B1-Motion>", self._pick)
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Left>", lambda _e: self._step(-1))
        self.bind("<Right>", lambda _e: self._step(1))
        self.bind("<Home>", lambda _e: self.var.set(0))
        self.bind("<End>", lambda _e: self.var.set(self.maximum))
        self.bind("<FocusIn>", lambda _e: self._set_focus(True))
        self.bind("<FocusOut>", lambda _e: self._set_focus(False))
        self.bind("<Destroy>", self._cleanup)

    def _cleanup(self, _e=None):
        try:
            self.var.trace_remove("write", self._trace)
        except (tk.TclError, ValueError):
            pass

    def _set_hover(self, v):
        self._hover = v
        self.redraw()

    def _set_focus(self, v):
        self._focus = v
        self.redraw()

    def _value(self):
        try:
            return max(0, min(self.maximum, int(self.var.get())))
        except (tk.TclError, ValueError):
            return 0

    def _step(self, d):
        self.var.set(max(0, min(self.maximum, self._value() + d)))
        return "break"

    def _pick(self, e):
        self.focus_set()
        w = self.winfo_width()
        x1, x2 = 12, w - 12
        ratio = (e.x - x1) / max(1, x2 - x1)
        self.var.set(max(0, min(self.maximum, round(ratio * self.maximum))))

    def redraw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40:
            return
        x1, x2, cy = 12, w - 12, h / 2 - 3
        v = self._value()
        kx = x1 + (x2 - x1) * v / self.maximum
        for i in range(self.maximum + 1):
            x = x1 + (x2 - x1) * i / self.maximum
            major = i % 7 == 0
            self.create_line(x, cy + 9, x, cy + (15 if major else 12),
                             fill=(MUTED if major else LINE_2) if i > v else mix(AMBER, PANEL, .35), width=1)
        self.create_polygon(rounded_points(x1, cy - 3, x2, cy + 3, 3), smooth=True, fill=INPUT, outline=LINE)
        if v:
            self.create_polygon(rounded_points(x1, cy - 3, kx, cy + 3, 3), smooth=True, fill=AMBER, outline="")
        r = 10 if (self._hover or self._focus) else 8
        if self._focus:
            self.create_oval(kx - r - 4, cy - r - 4, kx + r + 4, cy + r + 4, outline=mix(CYAN, PANEL, .4), width=1)
        self.create_oval(kx - r, cy - r, kx + r, cy + r, fill=AMBER, outline=mix(AMBER, "#ffffff", .3))
        self.create_oval(kx - 3, cy - 3, kx + 3, cy + 3, fill="#121a26", outline="")


class SecurityGauge(tk.Canvas):
    """Yarım daire güvenlik seviyesi göstergesi (0–100), kademe renkli ve animasyonlu."""

    THRESHOLDS = (0, 40, 60, 80, 92, 100)

    def __init__(self, parent, size=300, center_image=None):
        super().__init__(parent, width=size, height=int(size * .74), bg=bg_of(parent), highlightthickness=0, bd=0)
        self.size = size
        self.value = 0.0
        self.target = 0
        self.tier_name = ""
        self.tier = 0
        self.center_image = center_image
        self._job = None
        self.redraw()

    def set(self, score, tier, tier_name, animate=True):
        self.target, self.tier, self.tier_name = score, tier, tier_name
        if not animate:
            self.value = score
            self.redraw()
            return
        if self._job is None:
            self._animate()

    def _animate(self):
        if not self.winfo_exists():
            return
        diff = self.target - self.value
        if abs(diff) < .6:
            self.value = self.target
            self._job = None
            self.redraw()
            return
        self.value += diff * .18
        self.redraw()
        self._job = self.after(16, self._animate)

    def redraw(self):
        self.delete("all")
        S = self.size
        cx, cy, r = S / 2, S * .58, S * .42
        box = (cx - r, cy - r, cx + r, cy + r)
        # kademe bantları
        for i in range(5):
            a, b = self.THRESHOLDS[i], self.THRESHOLDS[i + 1]
            start = 180 - b * 1.8
            self.create_arc(*box, start=start + .8, extent=(b - a) * 1.8 - 1.6, style="arc",
                            outline=mix(TIER_COLORS[i], bg_of(self), .7), width=14)
        # değer yayı
        col = TIER_COLORS[self.tier] if self.tier < len(TIER_COLORS) else CYAN
        if self.value > 0.5:
            self.create_arc(*box, start=180 - self.value * 1.8, extent=self.value * 1.8, style="arc",
                            outline=col, width=14)
        # kademe eşik çizgileri
        for t in self.THRESHOLDS[1:-1]:
            ang = math.radians(180 - t * 1.8)
            x1, y1 = cx + (r - 12) * math.cos(ang), cy - (r - 12) * math.sin(ang)
            x2, y2 = cx + (r + 12) * math.cos(ang), cy - (r + 12) * math.sin(ang)
            self.create_line(x1, y1, x2, y2, fill=bg_of(self), width=3)
            lx, ly = cx + (r + 24) * math.cos(ang), cy - (r + 24) * math.sin(ang)
            self.create_text(lx, ly, text=str(t), fill=DIM, font=F["mono_xs"])
        # uç noktası
        ang = math.radians(180 - self.value * 1.8)
        kx, ky = cx + r * math.cos(ang), cy - r * math.sin(ang)
        self.create_oval(kx - 10, ky - 10, kx + 10, ky + 10, fill=col, outline=bg_of(self), width=3)
        if self.center_image is not None:
            self.create_image(cx, cy - r * .48, image=self.center_image)
        self.create_text(cx, cy - r * .1, text=f"{round(self.value)}", fill=FG, font=F["display"])
        self.create_text(cx, cy + 30, text=self.tier_name.upper(), fill=col, font=F["mono_b"])


class ToggleSwitch(tk.Canvas):
    """Açık/kapalı anahtarı."""

    def __init__(self, parent, value=False, command=None):
        super().__init__(parent, width=46, height=24, bg=bg_of(parent), highlightthickness=0, bd=0,
                         cursor="hand2", takefocus=1)
        self.value, self.command = bool(value), command
        self.bind("<Button-1>", lambda _e: self.toggle())
        self.bind("<space>", lambda _e: self.toggle())
        self.bind("<Return>", lambda _e: self.toggle())
        self.redraw()

    def set(self, value):
        self.value = bool(value)
        self.redraw()

    def toggle(self):
        self.set(not self.value)
        if self.command:
            self.command(self.value)

    def redraw(self):
        self.delete("all")
        on = self.value
        self.create_polygon(rounded_points(2, 3, 44, 21, 9), smooth=True,
                            fill=mix(GREEN, PANEL, .55) if on else INPUT, outline=GREEN if on else LINE_2)
        x = 33 if on else 13
        self.create_oval(x - 7, 5, x + 7, 19, fill=GREEN if on else MUTED, outline="")


class StrengthMeter(tk.Frame):
    """Parola seviyesi göstergesi: 5 kalkan segmenti, ad, bit tahmini ve ipuçları."""

    def __init__(self, parent, show_hints=True):
        super().__init__(parent, bg=bg_of(parent))
        self.bar = tk.Canvas(self, height=12, bg=bg_of(parent), highlightthickness=0)
        self.bar.pack(fill="x")
        row = tk.Frame(self, bg=bg_of(parent))
        row.pack(fill="x", pady=(6, 0))
        self.name = tk.Label(row, text="", bg=bg_of(parent), fg=MUTED, font=F["body_b"])
        self.name.pack(side="left")
        self.bits = tk.Label(row, text="", bg=bg_of(parent), fg=DIM, font=F["mono_xs"])
        self.bits.pack(side="right")
        self.summary = tk.Label(self, text="", bg=bg_of(parent), fg=MUTED, font=F["tiny"], anchor="w")
        self.summary.pack(fill="x")
        self.hints = tk.Label(self, text="", bg=bg_of(parent), fg=DIM, font=F["tiny"], anchor="w",
                              justify="left") if show_hints else None
        if self.hints:
            self.hints.pack(fill="x", pady=(4, 0))
        self.result = None
        self.bar.bind("<Configure>", lambda _e: self._paint())
        self.update_result(None)

    def update_result(self, result):
        self.result = result
        if not result:
            self.name.configure(text="—", fg=MUTED)
            self.bits.configure(text="")
            self.summary.configure(text="Parola girildikçe seviye burada görünür. Parola saklanmaz.")
            if self.hints:
                self.hints.configure(text="")
        else:
            col = STRENGTH_COLORS.get(result["color"], CYAN)
            self.name.configure(text=f"{result['level'] + 1}/5 · {result['name']}", fg=col)
            self.bits.configure(text=f"≈ {result['bits']} bit")
            self.summary.configure(text=result["summary"])
            if self.hints:
                self.hints.configure(text="\n".join("• " + h for h in result["hints"]))
        self._paint()

    def _paint(self):
        c = self.bar
        c.delete("all")
        w = c.winfo_width()
        if w < 20:
            return
        gap = 5
        seg = (w - gap * 4) / 5
        level = self.result["level"] if self.result else -1
        col = STRENGTH_COLORS.get(self.result["color"], CYAN) if self.result else LINE
        for i in range(5):
            x = i * (seg + gap)
            c.create_polygon(rounded_points(x, 1, x + seg, 11, 4), smooth=True,
                             fill=col if i <= level else INPUT, outline="" if i <= level else LINE)
