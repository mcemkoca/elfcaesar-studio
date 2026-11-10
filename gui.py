"""ELFCAESAR STUDIO 6.5 — Advanced Visual Design.

Arayüz katmanı. Şifreleme (secure), kimlik/mesajlaşma (identity) ve ELFC2
(engine) motorları 6.4 ile aynıdır; bu dosya yalnızca onları çağırır.
"""
from __future__ import annotations

import importlib.metadata
import os
import importlib.util
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path

from elfcaesar.engine import (
    encode, decode, brute_force, export_json, VERSION,
    LETTER_TO_TOKEN, ElfFormatError,
)
from elfcaesar.alphabet import ALPHABET
from elfcaesar.secure import encrypt_file, decrypt_file, encrypt_message, decrypt_message, generate_passphrase
from elfcaesar.identity import create_identity, load_identity, import_contact, export_contact, encrypt_for_contact, decrypt_from_contact

from studio_ui import icons, dnd
from studio_ui import settings as user_settings
from studio_ui.security import SecurityState, assess, scan_sensitive, password_strength, SECURITY_TIERS
from studio_ui.dialogs import PasswordDialog, AboutDialog, WhatsNewDialog
from studio_ui.intro import IntroExperience
from studio_ui.crack_ui import CrackTable
from studio_ui.changelog import notes_for
from studio_ui.bridge_ui import BridgeMixin
from studio_ui.kvkk_ui import ProMixin
from studio_ui.toolbox_ui import ToolboxMixin
from studio_ui.guide_ui import GuideMixin, InfoButton
from studio_ui.badge_ui import BadgeMixin
from studio_ui.passwords_ui import PasswordsMixin
from studio_ui import guides
from studio_ui import folderlock
from studio_ui import theme
from studio_ui.theme import (TIER_COLORS, ADVICE_COLORS, ORANGE, BG, SIDEBAR, PANEL, PANEL_2, PANEL_3, INPUT, LINE, LINE_2, FG, FG_2, MUTED, DIM,
                             AMBER, CYAN, GREEN, RED, VIOLET, SELECT, LEVEL_COLORS, CATEGORY_COLORS, mix)
from studio_ui.widgets import (StudioButton, Tooltip, ToastManager, AnimatedCore, ActivityChart, CategoryBars,
                               ScoreChart, Segmented, Chip, DropZone, IdentityCard, ShiftSlider, rounded_points,
                               SecurityGauge, ToggleSwitch, StrengthMeter)
from studio_ui.activity import ActivityLog, CATEGORIES
from studio_ui.scoring import rank, best_shift

from studio_ui import runtime
from studio_ui.version import APP_SHORT_VERSION, APP_VERSION as APP_FULL_VERSION, APP_CODENAME, COPYRIGHT

APP_VERSION = APP_SHORT_VERSION
ASSETS = runtime.resource_dir() / "assets"
F = theme.F

# key, icon, nav label, title, subtitle, group
PAGES = [
    ("home", "home", "Kontrol Merkezi", "CONTROL ROOM", "GENEL BAKIŞ  /  YEREL ŞİFRELEME ÇALIŞMA ALANI", "WORKSPACE"),
    ("encode", "encode", "Kodlama", "ENCODING STUDIO", "METNİ ELFC2 TOKEN FORMATINA DÖNÜŞTÜR", "WORKSPACE"),
    ("decode", "decode", "Çözme", "DECODING STUDIO", "ELFC2 PAKETİNİ DOĞRULA VE METNE GERİ DÖNÜŞTÜR", "WORKSPACE"),
    ("analysis", "analysis", "Kaydırma Analizi", "SHIFT ANALYSIS", "29 KAYDIRMAYI PUANLA VE KARŞILAŞTIR", "WORKSPACE"),
    ("vault", "vault", "Güvenli Kasa", "SECURE VAULT / MESSENGER", "AES-256-GCM  /  X25519  /  ED25519", "SECURITY"),
    ("passwords", "lock", "Parola Kasası", "PASSWORD VAULT", "PAROLALAR  /  DENETİM  /  DOMİNO  /  HIZLI DOLDUR  /  MİRAS", "SECURITY"),
    ("bridge", "send", "Mesaj Köprüsü", "MESSAGE BRIDGE", "WHATSAPP · TELEGRAM · E-POSTA  /  UÇTAN UCA ŞİFRELİ MESAJ", "SECURITY"),
    ("security", "shield", "Güvenlik Merkezi", "SECURITY CENTER", "GÜVENLİK SEVİYESİ  /  ÖNERİ SEVİYELERİ  /  KORUMALAR", "SECURITY"),
    ("toolbox", "key", "Araç Kutusu", "TOOLBOX", "KLASÖR KASASI  /  ANAHTAR DOSYASI  /  DİJİTAL İMZA  /  GÜVENLİ İMHA", "SECURITY"),
    ("kvkk", "search", "KVKK Kalkanı", "KVKK SHIELD", "KİŞİSEL VERİ ENVANTERİ  /  KASAYA ALMA  /  RAPOR", "BUSINESS"),
    ("tengwar", "tengwar", "Sindarin · Tengwar", "TENGWAR WORKSPACE", "YAZI SİSTEMİ HAZIRLIK ALANI  /  DİL ÇEVİRİSİ DEĞİLDİR", "STUDIO"),
    ("alphabet", "alphabet", "Alfabe Laboratuvarı", "ALPHABET LAB", "TÜRKÇE 29 HARFLİ ALFABE VE TOKEN EŞLEŞMELERİ", "STUDIO"),
    ("history", "history", "İşlem Geçmişi", "ACTIVITY LOG", "OTURUM İÇİ İŞLEMLER  /  İÇERİK KAYDEDİLMEZ", "SYSTEM"),
]
PAGE = {p[0]: p for p in PAGES}
# Sade (güvenlik) modu: ELFC2 / Tengwar / alfabe gibi meraklısına yönelik ekranlar menüden gizlenir
SADE_HIDDEN = {"encode", "decode", "analysis", "tengwar", "alphabet"}
COMPACT_BELOW = 1120
TEXT_LIMIT = 5 * 1024 * 1024


def crypto_status():
    if importlib.util.find_spec("cryptography") is None:
        return False, "cryptography paketi eksik · requirements.txt"
    try:
        return True, f"cryptography {importlib.metadata.version('cryptography')} yüklü"
    except importlib.metadata.PackageNotFoundError:
        return True, "cryptography yüklü"


class Studio(PasswordsMixin, BadgeMixin, GuideMixin, ToolboxMixin, ProMixin, BridgeMixin, tk.Tk):
    def __init__(self, start_action=None, instance_server=None):
        super().__init__()
        theme.init_fonts(self)
        self.title(f"ELFCAESAR STUDIO {APP_VERSION}")
        self.geometry("1360x900")
        self.minsize(880, 620)
        self.configure(bg=BG)
        self.shift = tk.IntVar(value=3)
        self.log = ActivityLog()
        self.unread = 0
        self.pages: dict[str, tk.Frame] = {}
        self.tabs: list[str] = []
        self.scroll_pos: dict[str, float] = {}
        self.active_page = None
        self.identity_cards: list[dict] = []
        self.analysis_all_results: list[tuple[int, str, int]] = []
        self.analysis_sort = "shift"
        self._compact = None
        self.dnd_enabled = dnd.enable(self)
        self.crypto_ok, self.crypto_detail = crypto_status()
        self.prefs = user_settings.load()
        self._ui_mode_start = self.prefs.get("ui_mode", "full")
        self.sec = SecurityState(crypto_ok=self.crypto_ok, clipboard_guard=self.prefs["clipboard_guard"],
                                 clipboard_seconds=self.prefs["clipboard_seconds"],
                                 idle_lock_minutes=self.prefs["idle_lock_minutes"],
                                 sensitive_warning=self.prefs["sensitive_warning"])
        self.sec.capture_shield = self.prefs.get("capture_shield", "sensitive")
        self.sec.paper_backup = bool(self.prefs.get("paper_backup_date"))
        self.sec.identity_known = bool(self.prefs.get("identity_path")) and Path(self.prefs.get("identity_path")).exists()
        _pvp = Path(self.prefs.get("pw_vault_path") or "") if self.prefs.get("pw_vault_path") else None
        from studio_ui.pwvault import default_path as _pw_default
        self.sec.password_vault = bool((_pvp or _pw_default()).exists())
        self._locked = False
        self._bridge_init()
        self.assessment = assess(self.sec)
        self._clip_job = None
        self._last_activity = time.monotonic()
        self.images = {}
        self._load_brand()
        self._style()
        self._shell()
        self.toasts = ToastManager(self.main)
        self._bind_keys()
        self.show_page("home")
        self.status("Çekirdek hazır · " + VERSION)
        self.log.add("system", "info", f"Studio {APP_VERSION} başlatıldı",
                     "Sürükle-bırak etkin" if self.dnd_enabled else "Sürükle-bırak pasif")
        self.after(30000, self._periodic)
        self.after(10000, self._idle_check)
        for seq in ("<Any-KeyPress>", "<Any-ButtonPress>", "<Motion>"):
            self.bind_all(seq, self._touch, add="+")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh_security()
        self.instance_server = instance_server
        from studio_ui.browser_bridge import BrowserBridge
        self.browser = BrowserBridge(self)
        if instance_server is not None:
            instance_server.request_handler = self.browser.handle
        self.after(800, self.apply_capture_mode)
        if instance_server is not None:
            self.after(300, self._instance_poll)
        if start_action:
            self.after(500, lambda: self._run_start_action(*start_action))
        elif os.environ.get("ELFCAESAR_NO_SPLASH") != "1":
            if not self.prefs.get("intro_seen"):
                self.after(150, lambda: self.play_intro(first=True))
            else:
                if self.prefs.get("splash", True):
                    self._show_splash()
                self.after(1900, self._maybe_whats_new)

    # ------------------------------------------------------------ setup
    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Treeview", background=PANEL, foreground=FG, fieldbackground=PANEL,
                    rowheight=32, borderwidth=0, font=F["small"])
        s.configure("Treeview.Heading", background=PANEL_2, foreground=AMBER,
                    font=F["label"], relief="flat", padding=(10, 8))
        s.map("Treeview.Heading", background=[("active", PANEL_3)])
        s.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", FG)])
        for orient in ("Vertical", "Horizontal"):
            s.configure(f"{orient}.TScrollbar", gripcount=0, background=PANEL_2,
                        darkcolor=BG, lightcolor=PANEL_2, troughcolor=BG,
                        bordercolor=BG, arrowcolor=MUTED, relief="flat", width=10)
            s.map(f"{orient}.TScrollbar", background=[("active", CYAN), ("!active", PANEL_3)])

    def _shell(self):
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(shell, bg=SIDEBAR, width=244)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Frame(shell, bg=LINE, width=1).pack(side="left", fill="y")
        self.main = tk.Frame(shell, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self._build_sidebar()

        self.topbar = tk.Frame(self.main, bg=BG)
        self.topbar.pack(fill="x", padx=28, pady=(20, 10))
        title_group = tk.Frame(self.topbar, bg=BG)
        title_group.pack(side="left", fill="x", expand=True)
        self.page_title = tk.Label(title_group, text="CONTROL ROOM", bg=BG, fg=FG, font=F["h1"], anchor="w")
        self.page_title.pack(anchor="w")
        self.page_subtitle = tk.Label(title_group, text="", bg=BG, fg=MUTED, font=F["mono_xs"], anchor="w")
        self.page_subtitle.pack(anchor="w", pady=(3, 0))
        right = tk.Frame(self.topbar, bg=BG)
        right.pack(side="right")
        self.pill = tk.Frame(right, bg=PANEL, highlightthickness=1, cursor="hand2")
        self.pill.pack(side="right", padx=(10, 0))
        self.pulse_dot = tk.Canvas(self.pill, width=12, height=12, bg=PANEL, highlightthickness=0)
        self.pulse_dot.pack(side="left", padx=(10, 0))
        self.pulse_dot.create_oval(2, 2, 10, 10, fill=GREEN, outline="", tags="dot")
        self.pill_label = tk.Label(self.pill, text="", bg=PANEL, fg=GREEN, font=F["mono_b"])
        self.pill_label.pack(side="left", padx=(6, 12), pady=7)
        for w in (self.pill, self.pulse_dot, self.pill_label):
            w.bind("<Button-1>", lambda _e: self.show_page("security"))
        Tooltip(self.pill, "Güvenlik seviyesi · Güvenlik Merkezi'ni aç")
        self.clock = tk.Label(right, text="", bg=BG, fg=DIM, font=F["mono_sm"])
        self.clock.pack(side="right", padx=(10, 4))
        bell_wrap = tk.Frame(right, bg=BG)
        bell_wrap.pack(side="right")
        InfoButton(right, lambda: self.open_guide(), "Kılavuz · bu bölüm (F1)", 22, CYAN).pack(side="right", padx=(0, 10))
        self.bell = StudioButton(bell_wrap, "", lambda: self.show_page("history"), "ghost", "bell",
                                 tooltip="Bildirimler ve işlem geçmişi")
        self.bell.pack()
        self.bell_badge = tk.Label(bell_wrap, text="", bg=AMBER, fg="#121a26", font=F["label"], padx=4)
        self._tick_clock()
        self._pulse_phase = 0
        self._pulse()

        self.tabbar = tk.Frame(self.main, bg=BG)
        self.tabbar.pack(fill="x", padx=28, pady=(0, 12))
        self.tab_strip = tk.Frame(self.tabbar, bg=BG)
        self.tab_strip.pack(side="left", fill="x", expand=True)
        self.tab_hint = tk.Label(self.tabbar, text="CTRL+1…0 SAYFA  ·  CTRL+W SEKME KAPAT", bg=BG, fg=DIM, font=F["mono_xs"])
        self.tab_hint.pack(side="right")
        tk.Frame(self.main, bg=LINE, height=1).pack(fill="x", padx=28)

        footer = tk.Frame(self.main, bg="#060a10")
        footer.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="◆ Başlatılıyor")
        tk.Label(footer, text=f"ELFC2 · AES-256-GCM · X25519 · v{APP_VERSION}", bg="#060a10", fg=DIM,
                 font=F["mono_xs"]).pack(side="right", padx=24)
        self.status_icon = tk.Canvas(footer, width=14, height=14, bg="#060a10", highlightthickness=0)
        self.status_icon.pack(side="left", padx=(26, 0))
        self.status_icon.create_oval(3, 3, 11, 11, fill=CYAN, outline="", tags="dot")
        tk.Label(footer, textvariable=self.status_var, bg="#060a10", fg=MUTED,
                 font=F["mono_sm"], anchor="w").pack(side="left", fill="x", expand=True, padx=(8, 0), pady=9)

        viewport = tk.Frame(self.main, bg=BG)
        viewport.pack(fill="both", expand=True, padx=(28, 18), pady=(14, 10))
        self.content_canvas = tk.Canvas(viewport, bg=BG, highlightthickness=0, bd=0)
        self.content_scroll = ttk.Scrollbar(viewport, orient="vertical", command=self.content_canvas.yview)
        self.content_canvas.configure(yscrollcommand=self.content_scroll.set)
        self.content_scroll.pack(side="right", fill="y", padx=(8, 0))
        self.content_canvas.pack(side="left", fill="both", expand=True)
        self.content_root = tk.Frame(self.content_canvas, bg=BG)
        self.content = self.content_root
        self.content_window = self.content_canvas.create_window((0, 0), window=self.content_root, anchor="nw")
        self.content_root.bind("<Configure>", self._content_configure)
        self.content_canvas.bind("<Configure>", self._canvas_configure)
        self.bind_all("<MouseWheel>", self._mousewheel)
        self.bind_all("<Button-4>", self._mousewheel)
        self.bind_all("<Button-5>", self._mousewheel)
        self.bind("<Configure>", self._window_configure, add="+")

    def _build_sidebar(self):
        sb = self.sidebar
        self.brand = tk.Frame(sb, bg=SIDEBAR)
        self.brand.pack(fill="x", padx=18, pady=(24, 22))
        if self.img("mark_40") is not None:
            mark = tk.Label(self.brand, image=self.img("mark_40"), bg=SIDEBAR, cursor="hand2", bd=0)
        else:
            mark = tk.Canvas(self.brand, width=38, height=38, bg=SIDEBAR, highlightthickness=0, cursor="hand2")
            icons.draw(mark, "spark", 19, 19, 14, AMBER, width=1.6)
        mark.pack(side="left")
        mark.bind("<Button-1>", lambda _e: self.show_about())
        Tooltip(mark, "ElfCaesar Studio hakkında")
        self.brand_text = tk.Frame(self.brand, bg=SIDEBAR)
        self.brand_text.pack(side="left", padx=10)
        tk.Label(self.brand_text, text="ELFCAESAR", bg=SIDEBAR, fg=FG, font=F["brand"]).pack(anchor="w")
        tk.Label(self.brand_text, text=f"STUDIO  ·  v{APP_VERSION}", bg=SIDEBAR, fg=MUTED, font=F["mono_xs"]).pack(anchor="w")

        self.nav = {}
        self.nav_groups = []
        group = None
        hidden = SADE_HIDDEN if self.prefs.get("ui_mode") == "sade" else set()
        for key, icon, label, *_rest, grp in PAGES:
            if key in hidden:
                continue
            if grp != group:
                group = grp
                g = tk.Label(sb, text=grp, bg=SIDEBAR, fg=DIM, font=F["label"])
                g.full_text = grp
                g.pack(anchor="w", padx=24, pady=(10, 4))
                self.nav_groups.append(g)
            row = tk.Frame(sb, bg=SIDEBAR, cursor="hand2")
            row.pack(fill="x", padx=10, pady=1)
            bar = tk.Frame(row, bg=SIDEBAR, width=3)
            bar.pack(side="left", fill="y")
            ic = tk.Canvas(row, width=22, height=22, bg=SIDEBAR, highlightthickness=0)
            ic.pack(side="left", padx=(13, 10), pady=7)
            lab = tk.Label(row, text=label, bg=SIDEBAR, fg=MUTED, font=F["body_b"], anchor="w")
            lab.pack(side="left", fill="x", expand=True)
            badge = tk.Label(row, text="", bg=SIDEBAR, fg="#121a26", font=F["label"])
            tip = Tooltip(row, label)
            tip.enabled = False
            item = {"row": row, "bar": bar, "icon": ic, "label": lab, "badge": badge, "glyph": icon, "tip": tip, "hover": False}
            self.nav[key] = item
            for w in (row, ic, lab, bar):
                w.bind("<Button-1>", lambda _e, k=key: self.show_page(k))
                w.bind("<Enter>", lambda _e, k=key: self._nav_hover(k, True))
                w.bind("<Leave>", lambda _e, k=key: self._nav_hover(k, False))
            self._paint_nav(key)

        self.side_bottom = tk.Frame(sb, bg=SIDEBAR)
        self.side_bottom.pack(side="bottom", fill="x", padx=18, pady=18)
        tk.Frame(self.side_bottom, bg=LINE, height=1).pack(fill="x", pady=(0, 12))
        tk.Label(self.side_bottom, text=f"v{APP_VERSION} · LOCAL ENGINE", bg=SIDEBAR, fg=GREEN,
                 font=F["label"]).pack(anchor="w")
        tk.Label(self.side_bottom, text="Offline  ·  Hesap yok  ·  API yok", bg=SIDEBAR, fg=MUTED,
                 font=F["tiny"]).pack(anchor="w", pady=(4, 0))
        if self.img("dante_sig_110") is not None:
            sig = tk.Label(self.side_bottom, image=self.img("dante_sig_110"), bg=SIDEBAR, cursor="hand2")
            sig.pack(anchor="w", pady=(8, 0))
            sig.bind("<Button-1>", lambda _e: self.show_about())
            Tooltip(sig, "Yapımcı: Dante")
        links = tk.Frame(self.side_bottom, bg=SIDEBAR)
        links.pack(anchor="w", pady=(10, 0))
        StudioButton(links, "Hakkında", self.show_about, "ghost", "info", "sm").pack(side="left")
        InfoButton(links, lambda: self.open_guide(), "Kılavuz · F1", 20, CYAN, SIDEBAR).pack(side="left", padx=(2, 0))
        StudioButton(links, "Panik", self.panic, "danger", "lock", "sm", tooltip="Panik modu · Ctrl+Shift+L").pack(side="left", padx=6)

    def _nav_hover(self, key, on):
        self.nav[key]["hover"] = on
        self._paint_nav(key)

    def _paint_nav(self, key):
        item = self.nav[key]
        active = key == self.active_page
        bg = PANEL_2 if active else ("#0f1926" if item["hover"] else SIDEBAR)
        fg = FG if active else (FG_2 if item["hover"] else MUTED)
        for w in (item["row"], item["icon"], item["label"]):
            w.configure(bg=bg)
        item["label"].configure(fg=fg)
        item["bar"].configure(bg=AMBER if active else bg)
        c = item["icon"]
        c.delete("all")
        icons.draw(c, item["glyph"], 11, 11, 16, AMBER if active else (FG_2 if item["hover"] else MUTED), width=1.6)

    def _set_compact(self, compact):
        if compact == self._compact:
            return
        self._compact = compact
        self.sidebar.configure(width=74 if compact else 244)
        if compact:
            self.brand_text.pack_forget()
            self.side_bottom.pack_forget()
            for g in self.nav_groups:
                g.configure(text="───")
                g.pack_configure(padx=26)
        else:
            self.brand_text.pack(side="left", padx=10)
            self.side_bottom.pack(side="bottom", fill="x", padx=18, pady=18)
            for g in self.nav_groups:
                g.configure(text=g.full_text)
                g.pack_configure(padx=24)
        for key, item in self.nav.items():
            item["tip"].enabled = compact
            if compact:
                item["label"].pack_forget()
                item["icon"].pack_configure(padx=(11, 0))
            else:
                item["label"].pack(side="left", fill="x", expand=True)
                item["icon"].pack_configure(padx=(13, 10))
        self._update_badge()
        self._render_tabs()

    def _window_configure(self, event):
        if event.widget is self and event.width != getattr(self, "_last_width", None):
            self._last_width = event.width
            self._set_compact(event.width < COMPACT_BELOW)
            if not self.tab_hint.winfo_ismapped():
                self.tab_hint.pack(side="right")
            if getattr(self, "_tabs_job", None):
                self.after_cancel(self._tabs_job)
            self._tabs_job = self.after(60, self._render_tabs)

    def _bind_keys(self):
        for i, (key, *_r) in enumerate(PAGES, start=1):
            if i <= 10:
                self.bind_all(f"<Control-Key-{i % 10}>", lambda _e, k=key: self.show_page(k))
        self.bind_all("<F1>", lambda _e: (self.open_guide(), "break")[1])
        self.bind_all("<Control-w>", lambda _e: self.close_tab(self.active_page))
        self.bind_all("<Control-W>", lambda _e: self.close_tab(self.active_page))
        self.bind_all("<Control-Tab>", lambda _e: (self._cycle_tab(1), "break")[1])
        self.bind_all("<Control-L>", lambda _e: self.panic())
        self.bind_all("<Control-Shift-l>", lambda _e: self.panic())

    def _tick_clock(self):
        self.clock.configure(text=time.strftime("%H:%M"))
        self.after(15000, self._tick_clock)

    def _pulse(self):
        self._pulse_phase = (self._pulse_phase + 1) % 20
        t = abs(10 - self._pulse_phase) / 10
        r = 2 + 1.6 * t
        self.pulse_dot.coords("dot", 6 - r, 6 - r, 6 + r, 6 + r)
        self.after(90, self._pulse)

    def _periodic(self):
        self.refresh_dashboard()
        self.after(30000, self._periodic)

    def report_callback_exception(self, exc_type, exc, tb):
        """Arayüz geri çağrılarındaki beklenmeyen hatalar: günlüğe yaz, kullanıcıya bildir, uygulamayı kapatma."""
        path = runtime.write_crash(exc_type, exc, tb)
        try:
            self.notify("error", "system", "Beklenmeyen bir hata oluştu",
                        f"{exc_type.__name__}" + (f" · günlük: {path.name}" if path else ""))
        except Exception:
            pass

    def _instance_poll(self):
        server = getattr(self, "instance_server", None)
        if server is None:
            return
        self.browser.pump()
        for cmd in server.poll():
            if cmd["action"] != "background":
                self.deiconify()
                self.lift()
                self.focus_force()
            if cmd["action"] != "show":
                self._run_start_action(cmd["action"], cmd.get("path"))
        self.after(300, self._instance_poll)

    def _on_close(self):
        self._bridge_stop()
        if getattr(self, "instance_server", None) is not None:
            self.instance_server.stop()
        core = getattr(self, "core", None)
        if core is not None:
            core.stop()
        for job in self.tk.splitlist(self.tk.call("after", "info")):
            try:
                self.tk.call("after", "cancel", job)
            except tk.TclError:
                pass
        self.destroy()

    # ------------------------------------------------------------ scrolling
    def _content_configure(self, _event=None):
        self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))

    def _canvas_configure(self, event):
        self.content_canvas.itemconfigure(self.content_window, width=event.width)

    def _mousewheel(self, event):
        """Scroll the workspace without hijacking wheel events from text editors."""
        if not self.winfo_exists() or not self.content_canvas.winfo_ismapped():
            return
        try:
            hovered = self.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return
        if hovered is None or hovered.winfo_toplevel() is not self:
            return
        while hovered is not None:
            if isinstance(hovered, (tk.Text, tk.Listbox, ttk.Treeview)):
                return
            hovered = getattr(hovered, "master", None)
        if getattr(event, "num", None) == 4:
            direction = -1
        elif getattr(event, "num", None) == 5:
            direction = 1
        elif event.delta:
            direction = -1 if event.delta > 0 else 1
        else:
            return
        self.content_canvas.yview_scroll(direction * 2, "units")

    def _scroll_to(self, widget):
        """Scroll the workspace to a visible section card."""
        self.update_idletasks()
        total = max(1, self.content_root.winfo_height())
        y = 0
        w = widget
        while w is not None and w is not self.content_root:
            y += w.winfo_y()
            w = w.master
        self.content_canvas.yview_moveto(max(0.0, (y - 6) / total))

    # ------------------------------------------------------------ notifications
    def status(self, text, level="info"):
        self.status_var.set(text)
        if hasattr(self, "status_icon"):
            self.status_icon.itemconfigure("dot", fill=LEVEL_COLORS.get(level, CYAN))

    def notify(self, level, category, title, detail="", toast=True):
        """Tek noktadan geri bildirim: durum çubuğu + bildirim + işlem geçmişi."""
        self.log.add(category, level, title, detail)
        self.status(title + (f" · {detail}" if detail else ""), level)
        if toast:
            self.toasts.show(level, title, detail)
        if self.active_page != "history":
            self.unread += 1
        self._update_badge()
        self.refresh_dashboard()
        if "history" in self.pages:
            self._render_history()
        self.badge_event(level, title)

    def _update_badge(self):
        text = "" if not self.unread else (str(self.unread) if self.unread < 100 else "99+")
        badge = self.nav["history"]["badge"]
        if text and not self._compact:
            badge.configure(text=f" {text} ", bg=AMBER)
            badge.pack(side="right", padx=(0, 10))
        else:
            badge.pack_forget()
        if text:
            self.bell_badge.configure(text=text)
            self.bell_badge.place(relx=1.0, x=6, y=-1, anchor="ne")
        else:
            self.bell_badge.place_forget()

    # ------------------------------------------------------------ pages & tabs
    def show_page(self, key):
        if key not in PAGE:
            return
        if self.active_page == key and key in self.pages:
            return
        if self.active_page in self.pages:
            self.scroll_pos[self.active_page] = self.content_canvas.yview()[0]
            self.pages[self.active_page].pack_forget()
        prev = self.active_page
        self.active_page = key
        if key not in self.tabs:
            self.tabs.append(key)
        if key not in self.pages:
            frame = tk.Frame(self.content_root, bg=BG)
            self.pages[key] = frame
            self.content = frame
            getattr(self, f"_page_{key}")()
        self.content = self.pages[key]
        self.content.pack(fill="both", expand=True)
        _k, _i, _l, title, subtitle, _g = PAGE[key]
        self.page_title.config(text=title)
        self.page_subtitle.config(text=subtitle)
        for k in self.nav:
            self._paint_nav(k)
        if prev:
            self._paint_nav(prev)
        if key == "history":
            self.unread = 0
            self._update_badge()
            self._render_history()
        core = getattr(self, "core", None)
        if core is not None and core.winfo_exists():
            (core.start if key == "home" else core.stop)()
        if key == "home":
            self.refresh_dashboard()
        self._render_tabs()
        self.update_idletasks()
        self._content_configure()
        self.content_canvas.yview_moveto(self.scroll_pos.get(key, 0.0))
        if prev and prev != key:
            self._slide_in()
        self.badge_visit(key)

    def _slide_in(self, step=0, steps=11, dist=26):
        """Sayfa geçişi: içerik aşağıdan yumuşakça kayarak yerine oturur (ease-out)."""
        from studio_ui.widgets import REDUCED_MOTION
        if REDUCED_MOTION:
            return
        job = getattr(self, "_slide_job", None)
        if step == 0 and job:
            self.after_cancel(job)
        k = step / steps
        y = round(dist * (1 - k) ** 3)
        ease = 1 - (1 - k) ** 3
        try:
            self.content_canvas.coords(self.content_window, 0, y)
            self.page_title.configure(fg=mix(BG, FG, ease))
            self.page_subtitle.configure(fg=mix(BG, MUTED, ease))
        except tk.TclError:
            return
        if step < steps:
            self._slide_job = self.after(15, lambda: self._slide_in(step + 1, steps, dist))
        else:
            self._slide_job = None
            self.content_canvas.coords(self.content_window, 0, 0)

    def close_tab(self, key):
        if key is None or key == "home" or key not in self.tabs:
            return
        idx = self.tabs.index(key)
        self.tabs.remove(key)
        frame = self.pages.pop(key, None)
        self.scroll_pos.pop(key, None)
        if self.active_page == key:
            self.active_page = None
            nxt = self.tabs[max(0, idx - 1)] if self.tabs else "home"
            self.show_page(nxt)
        if frame is not None:
            frame.destroy()
        self._render_tabs()
        self._content_configure()

    def _cycle_tab(self, step):
        if not self.tabs:
            return
        idx = self.tabs.index(self.active_page) if self.active_page in self.tabs else 0
        self.show_page(self.tabs[(idx + step) % len(self.tabs)])

    def _render_tabs(self):
        if not hasattr(self, "tab_strip"):
            return
        for child in self.tab_strip.winfo_children():
            child.destroy()
        self._draw_tabs(bool(self._compact))
        self.tab_strip.update_idletasks()
        avail = self.tabbar.winfo_width() - (self.tab_hint.winfo_reqwidth() + 12 if self.tab_hint.winfo_ismapped() else 0)
        if not self._compact and self.tab_strip.winfo_reqwidth() > avail > 1:
            for child in self.tab_strip.winfo_children():
                child.destroy()
            self._draw_tabs(True)
        need = self.tab_strip.winfo_reqwidth()
        if self.tabbar.winfo_width() > 1:
            fits = need + self.tab_hint.winfo_reqwidth() + 24 <= self.tabbar.winfo_width()
            if not fits and self.tab_hint.winfo_ismapped():
                self.tab_hint.pack_forget()

    def _draw_tabs(self, narrow):
        for key in self.tabs:
            _k, glyph, label, *_r = PAGE[key]
            active = key == self.active_page
            bg = PANEL if active else BG
            tab = tk.Frame(self.tab_strip, bg=bg, cursor="hand2",
                           highlightbackground=LINE_2 if active else LINE, highlightthickness=1)
            tab.pack(side="left", padx=(0, 6))
            inner = tk.Frame(tab, bg=bg)
            inner.pack(fill="both")
            ic = tk.Canvas(inner, width=16, height=16, bg=bg, highlightthickness=0)
            ic.pack(side="left", padx=(10, 6), pady=7)
            icons.draw(ic, glyph, 8, 8, 12, AMBER if active else MUTED, width=1.4)
            widgets = [tab, inner, ic]
            if active or not narrow:
                lab = tk.Label(inner, text=label, bg=bg, fg=FG if active else MUTED, font=F["button_sm"])
                lab.pack(side="left", padx=(0, 6 if key != "home" else 12))
                widgets.append(lab)
            else:
                Tooltip(tab, label)
            if key != "home":
                close = tk.Canvas(inner, width=16, height=16, bg=bg, highlightthickness=0, cursor="hand2")
                close.pack(side="left", padx=(0, 8))
                icons.draw(close, "close", 8, 8, 9, DIM, width=1.4)
                close.bind("<Enter>", lambda _e, c=close: (c.delete("all"), icons.draw(c, "close", 8, 8, 9, RED, width=1.6)))
                close.bind("<Leave>", lambda _e, c=close: (c.delete("all"), icons.draw(c, "close", 8, 8, 9, DIM, width=1.4)))
                close.bind("<Button-1>", lambda _e, k=key: self.close_tab(k))
            if active:
                tk.Frame(tab, bg=AMBER, height=2).pack(fill="x", side="bottom")
            for w in widgets:
                w.bind("<Button-1>", lambda _e, k=key: self.show_page(k))
                w.bind("<Button-2>", lambda _e, k=key: self.close_tab(k))

    # ------------------------------------------------------------ building blocks
    def _card(self, parent, title=None, subtitle=None, icon=None, accent=AMBER):
        box = tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        self._hover_glow(box, accent)
        if title:
            head = tk.Frame(box, bg=PANEL)
            head.pack(fill="x", padx=16, pady=(13, 8))
            if icon:
                icons.icon_label(head, icon, accent, 13, PANEL).pack(side="left", padx=(0, 7))
            tk.Label(head, text=title, bg=PANEL, fg=accent, font=F["label"]).pack(side="left")
            page = getattr(self, "active_page", None)
            if page and guides.section(page, title):
                self.info_button(head, page, title, 17, accent).pack(side="right", padx=(10, 0))
            if subtitle:
                tk.Label(head, text=subtitle, bg=PANEL, fg=DIM, font=F["mono_xs"]).pack(side="right")
            box.head = head
        return box

    def _wrap(self, label, margin=36, maximum=1100):
        host = label.master

        def update(_e=None):
            width = host.winfo_width()
            if width > 40:
                label.configure(wraplength=min(maximum, width - margin))
        label.configure(anchor="w")
        host.bind("<Configure>", update, add="+")
        return label

    def _text(self, parent, height=10):
        return tk.Text(parent, height=height, bg=INPUT, fg=FG, insertbackground=AMBER,
                       selectbackground=SELECT, relief="flat", padx=12, pady=10,
                       wrap="word", font=F["mono"], undo=True, autoseparators=True, maxundo=200,
                       highlightthickness=0, bd=0, spacing1=1, spacing3=1)

    def _button(self, parent, text, command, primary=False, variant=None, icon=None, size="md", tooltip=None):
        return StudioButton(parent, text, command, variant or ("primary" if primary else "secondary"),
                            icon, size, tooltip)

    def _flow(self, host, widgets, gap=8, row_gap=8):
        """Butonları satıra sığdığı kadar dizer, sığmayanı alt satıra taşır."""
        def relayout(_e=None):
            width = host.winfo_width()
            if width <= 1:
                return
            x, y, row_h = 0, 0, 0
            for w in widgets:
                rw, rh = w.winfo_reqwidth(), w.winfo_reqheight()
                if x and x + rw > width:
                    x, y = 0, y + row_h + row_gap
                    row_h = 0
                w.place(x=x, y=y)
                x += rw + gap
                row_h = max(row_h, rh)
            height = y + row_h
            if int(host.cget("height")) != height:
                host.configure(height=height)
        host.bind("<Configure>", relayout, add="+")
        host.after_idle(relayout)
        return relayout

    def _auto_grid(self, host, children, min_width, max_cols, gap=12, weights=None):
        """Genişliğe göre sütun sayısı değişen duyarlı ızgara."""
        uniform = f"u{id(host)}"

        def relayout(_e=None):
            width = host.winfo_width()
            cols = max(1, min(max_cols, width // max(1, min_width))) if width > 1 else 1
            if getattr(host, "_cols", None) == cols:
                return
            host._cols = cols
            for ch in children:
                ch.grid_forget()
            for i in range(max_cols):
                host.grid_columnconfigure(i, weight=0, uniform="", minsize=0)
            use_w = weights if weights and cols == len(weights) else [1] * cols
            for i in range(cols):
                host.grid_columnconfigure(i, weight=use_w[i], uniform="" if weights and cols == len(weights) else uniform)
            half = gap // 2
            for idx, ch in enumerate(children):
                r, c = divmod(idx, cols)
                ch.grid(row=r, column=c, sticky="nsew",
                        padx=(0 if c == 0 else half, 0 if c == cols - 1 else half),
                        pady=(0 if r == 0 else gap, 0))
        host.bind("<Configure>", relayout, add="+")
        relayout()

    def _hover_glow(self, box, accent):
        """Kart kenarı fare üzerindeyken vurgu rengine doğru yumuşakça parlar."""
        state = {"t": 0.0, "target": 0.0, "job": None}

        def step():
            t = state["t"] + (state["target"] - state["t"]) * 0.3
            if abs(state["target"] - t) < 0.03:
                t = state["target"]
            state["t"] = t
            try:
                box.configure(highlightbackground=mix(LINE, accent, t * .55))
            except tk.TclError:
                return
            state["job"] = box.after(16, step) if t != state["target"] else None

        def go(target):
            state["target"] = target
            if state["job"] is None:
                step()

        def leave(e):
            x, y = box.winfo_pointerxy()
            inside = box.winfo_rootx() <= x < box.winfo_rootx() + box.winfo_width() and \
                box.winfo_rooty() <= y < box.winfo_rooty() + box.winfo_height()
            if not inside:
                go(0.0)
        box.bind("<Enter>", lambda _e: go(1.0), add="+")
        box.bind("<Leave>", leave, add="+")

    def _page_intro(self, eyebrow, title, description, accent=AMBER, meta=None, icon=None):
        wrap = tk.Frame(self.content, bg=BG)
        wrap.pack(fill="x", pady=(0, 16))
        badge = tk.Canvas(wrap, width=46, height=46, bg=BG, highlightthickness=0)
        badge.pack(side="left", anchor="n", padx=(0, 14))
        badge.create_oval(1, 1, 45, 45, fill=mix(accent, BG, .86), outline=mix(accent, BG, .55))
        icons.draw(badge, icon or "spark", 23, 23, 20, accent, width=1.8)
        body = tk.Frame(wrap, bg=BG)
        body.pack(side="left", fill="both", expand=True)
        tk.Label(body, text=eyebrow.upper(), bg=BG, fg=accent, font=F["label"]).pack(anchor="w")
        tk.Label(body, text=title, bg=BG, fg=FG, font=F["h1"]).pack(anchor="w", pady=(3, 2))
        self._wrap(tk.Label(body, text=description, bg=BG, fg=MUTED, font=F["small"], justify="left"),
                   20, 900).pack(anchor="w", fill="x")
        page = getattr(self, "active_page", None)
        if page and guides.chapter(page):
            g = tk.Frame(wrap, bg=BG)
            g.pack(side="right", anchor="n", padx=(12, 0), pady=2)
            self.info_button(g, page, None, 24, accent).pack(side="left")
            lab = tk.Label(g, text="KILAVUZ", bg=BG, fg=accent, font=F["label"], cursor="hand2")
            lab.pack(side="left", padx=(6, 0))
            lab.bind("<Button-1>", lambda _e, p=page: self.open_guide(p))
        if meta:
            Chip(wrap, meta, accent).pack(side="right", anchor="n", padx=(12, 0), pady=4)

    # ------------------------------------------------------------ editors
    def _editor_select_all(self, widget):
        widget.tag_add("sel", "1.0", "end-1c")
        widget.mark_set("insert", "1.0")
        widget.see("insert")
        widget.focus_set()

    def _editor_paste(self, widget):
        try:
            value = self.clipboard_get()
        except tk.TclError:
            self.status("Panoda yapıştırılacak metin bulunamadı", "warning")
            return
        if widget.tag_ranges("sel"):
            widget.delete("sel.first", "sel.last")
        widget.insert("insert", value)
        widget.see("insert")
        widget.focus_set()

    def _editor_cut(self, widget):
        if widget.tag_ranges("sel"):
            self.clipboard_clear()
            self.clipboard_append(widget.get("sel.first", "sel.last"))
            widget.delete("sel.first", "sel.last")
            self.status("Seçim kesildi ve panoya alındı")
        widget.focus_set()

    def _editor_history(self, widget, redo=False):
        try:
            widget.edit_redo() if redo else widget.edit_undo()
        except tk.TclError:
            self.status("Yinelenecek işlem yok" if redo else "Geri alınacak işlem yok", "warning")
        widget.focus_set()

    def _editor_clear(self, widget):
        widget.delete("1.0", "end")
        widget.edit_separator()
        widget.focus_set()

    def _editor_panel(self, parent, title, hint, accent, height=14, drop=False):
        """Editör kartı: satır numaraları, kaydırma çubuğu, kapsamlı araç çubuğu ve canlı sayaçlar."""
        card = self._card(parent)
        head = tk.Frame(card, bg=PANEL)
        head.pack(fill="x", padx=14, pady=(12, 2))
        dot = tk.Canvas(head, width=10, height=10, bg=PANEL, highlightthickness=0)
        dot.pack(side="left", padx=(0, 7))
        dot.create_oval(1, 1, 9, 9, fill=accent, outline="")
        tk.Label(head, text=title, bg=PANEL, fg=accent, font=F["mono_b"]).pack(side="left")
        if drop:
            tk.Label(head, text="SÜRÜKLE-BIRAK" if self.dnd_enabled else "DOSYA AÇ İLE YÜKLE", bg=PANEL, fg=DIM,
                     font=F["mono_xs"]).pack(side="right")
        tk.Label(card, text=hint, bg=PANEL, fg=DIM, font=F["tiny"], anchor="w").pack(fill="x", padx=31, pady=(0, 8))

        tools = tk.Frame(card, bg=PANEL, height=30)
        tools.pack(fill="x", padx=12, pady=(0, 8))
        holder = {}
        specs = [("Kopyala", "copy", lambda: self.copy(holder["e"]), "secondary"),
                 ("Kes", "cut", lambda: self._editor_cut(holder["e"]), "ghost"),
                 ("Yapıştır", "paste", lambda: self._editor_paste(holder["e"]), "secondary"),
                 ("Tümünü seç", "select", lambda: self._editor_select_all(holder["e"]), "ghost"),
                 ("Geri al", "undo", lambda: self._editor_history(holder["e"]), "ghost"),
                 ("Yinele", "redo", lambda: self._editor_history(holder["e"], True), "ghost")]
        buttons = []
        for label, glyph, cmd, variant in specs:
            b = StudioButton(tools, label, cmd, variant, glyph, "sm", tooltip=label)
            b.full_text = label
            buttons.append(b)
        clear_btn = StudioButton(tools, "Temizle", lambda: self._editor_clear(holder["e"]), "danger", "clear", "sm",
                                 tooltip="Editörü temizle")
        clear_btn.full_text = "Temizle"

        def adapt(_e=None):
            width = tools.winfo_width()
            if width <= 1:
                return
            tier = 2 if width >= 540 else (1 if width >= 400 else 0)
            if getattr(tools, "_tier", None) != tier:
                tools._tier = tier
                for b in buttons:
                    b.set_text(b.full_text if tier and b.full_text not in ("Kes", "Geri al", "Yinele") else "")
                clear_btn.set_text("Temizle" if tier == 2 else "")
            x = 0
            for b in buttons:
                b.place(x=x, y=0)
                x += b.winfo_reqwidth() + 4
                if b.full_text in ("Tümünü seç",):
                    x += 8
            clear_btn.place(relx=1.0, x=0, y=0, anchor="ne")
        tools.bind("<Configure>", adapt)

        frame = tk.Frame(card, bg=INPUT, highlightthickness=1, highlightbackground=LINE, highlightcolor=CYAN)
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        gutter = tk.Canvas(frame, width=40, bg="#09111b", highlightthickness=0, bd=0)
        gutter.pack(side="left", fill="y")
        editor = self._text(frame, height)
        holder["e"] = editor
        ysb = ttk.Scrollbar(frame, orient="vertical", command=editor.yview)
        ysb.pack(side="right", fill="y")
        editor.pack(side="left", fill="both", expand=True)

        def redraw_gutter(*_a):
            gutter.delete("all")
            idx = editor.index("@0,0")
            while True:
                info = editor.dlineinfo(idx)
                if info is None:
                    break
                line = idx.split(".")[0]
                gutter.create_text(32, info[1] + info[3] / 2, text=line, anchor="e", fill=DIM, font=F["mono_xs"])
                nxt = editor.index(f"{idx}+1line")
                if nxt == idx:
                    break
                idx = nxt

        def yscroll(*args):
            ysb.set(*args)
            redraw_gutter()
        editor.configure(yscrollcommand=yscroll)
        gutter.bind("<Configure>", redraw_gutter)

        foot = tk.Frame(card, bg=PANEL)
        foot.pack(fill="x", padx=14, pady=(0, 10))
        cursor = tk.Label(foot, text="SATIR 1, SÜTUN 1", bg=PANEL, fg=DIM, font=F["mono_xs"])
        cursor.pack(side="left")
        metric = tk.Label(foot, text="0 KARAKTER · 0 KELİME · 0 SATIR", bg=PANEL, fg=MUTED, font=F["mono_xs"])
        metric.pack(side="right")

        def update_metric(_event=None):
            value = self.get(editor)
            lines = value.count("\n") + 1 if value else 0
            words = len(value.split())
            metric.configure(text=f"{len(value):,} KARAKTER · {words:,} KELİME · {lines} SATIR".replace(",", "."),
                             fg=FG_2 if value else MUTED)
            update_cursor()
            redraw_gutter()

        def update_cursor(_event=None):
            line, col = editor.index("insert").split(".")
            sel = ""
            if editor.tag_ranges("sel"):
                sel = f"  ·  SEÇİM {len(editor.get('sel.first', 'sel.last')):,}".replace(",", ".")
            cursor.configure(text=f"SATIR {line}, SÜTUN {int(col) + 1}{sel}")

        def on_modified(_event=None):
            if editor.edit_modified():
                update_metric()
                editor.edit_modified(False)

        editor.bind("<<Modified>>", on_modified)
        editor.bind("<KeyRelease>", update_cursor, add="+")
        editor.bind("<ButtonRelease-1>", update_cursor, add="+")
        editor.bind("<<Selection>>", update_cursor, add="+")
        editor.bind("<Control-a>", lambda _e, w=editor: (self._editor_select_all(w), "break")[1])
        editor.bind("<Control-A>", lambda _e, w=editor: (self._editor_select_all(w), "break")[1])
        editor.bind("<FocusIn>", lambda _e: frame.configure(highlightbackground=mix(accent, PANEL, .35)), add="+")
        editor.bind("<FocusOut>", lambda _e: frame.configure(highlightbackground=LINE), add="+")
        if drop:
            self._register_drop(editor, lambda paths, w=editor: self._load_text_file(w, paths[0]))
        return card, editor, update_metric

    def _layout_editor_pair(self, event, left, right, host):
        """Keep editors side-by-side on wide windows and stack them on narrow ones."""
        stacked = event.width < 900
        if getattr(host, "_stacked_editors", None) == stacked:
            return
        host._stacked_editors = stacked
        for panel in (left, right):
            panel.grid_forget()
        host.grid_columnconfigure(1, weight=0, uniform="")
        host.grid_rowconfigure(1, weight=0)
        if stacked:
            left.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
            right.grid(row=1, column=0, sticky="nsew")
            host.grid_columnconfigure(0, weight=1, uniform="")
            host.grid_rowconfigure(0, weight=1)
            host.grid_rowconfigure(1, weight=1)
        else:
            left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
            right.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            host.grid_columnconfigure(0, weight=1, uniform="ed")
            host.grid_columnconfigure(1, weight=1, uniform="ed")
            host.grid_rowconfigure(0, weight=1)

    def _editor_pair(self, left_spec, right_spec):
        work = tk.Frame(self.content, bg=BG)
        work.pack(fill="both", expand=True)
        left, le, lm = self._editor_panel(work, *left_spec)
        right, re_, rm = self._editor_panel(work, *right_spec)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        work.grid_columnconfigure(0, weight=1, uniform="ed")
        work.grid_columnconfigure(1, weight=1, uniform="ed")
        work.grid_rowconfigure(0, weight=1)
        work.bind("<Configure>", lambda e, l=left, r=right, h=work: self._layout_editor_pair(e, l, r, h))
        return (le, lm), (re_, rm)

    def _shift_control(self, parent, note):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=16, pady=(0, 14))
        value = tk.Label(row, text=f"{self.shift.get():02d}", bg=PANEL_2, fg=AMBER, font=F["metric"], width=3,
                         highlightthickness=1, highlightbackground=LINE_2)
        value.pack(side="left")
        mid = tk.Frame(row, bg=PANEL)
        mid.pack(side="left", fill="x", expand=True, padx=(14, 0))
        top = tk.Frame(mid, bg=PANEL)
        top.pack(fill="x")
        tk.Label(top, text="KAYDIRMA DEĞERİ", bg=PANEL, fg=MUTED, font=F["label"]).pack(side="left")
        letter = tk.Label(top, text="", bg=PANEL, fg=CYAN, font=F["mono_xs"])
        letter.pack(side="right")
        ShiftSlider(mid, self.shift).pack(fill="x", pady=(4, 0))
        self._wrap(tk.Label(mid, text=note, bg=PANEL, fg=DIM, font=F["tiny"], justify="left"), 10).pack(anchor="w")
        presets = tk.Frame(row, bg=PANEL)
        presets.pack(side="right", padx=(14, 0))
        for v in (0, 3, 13):
            StudioButton(presets, f"{v:02d}", lambda v=v: self.shift.set(v), "ghost", None, "sm",
                         tooltip=f"Kaydırmayı {v} yap").pack(side="left", padx=2)

        def sync(*_a):
            if not value.winfo_exists():
                return
            try:
                s = self.shift.get()
            except tk.TclError:
                return
            value.configure(text=f"{s:02d}")
            letter.configure(text=f"A → {ALPHABET[s % len(ALPHABET)].upper()}   ·   Z → {ALPHABET[(28 + s) % len(ALPHABET)].upper()}")
        trace = self.shift.trace_add("write", sync)
        row.bind("<Destroy>", lambda _e: self._untrace(trace))
        sync()

    def _untrace(self, trace):
        try:
            self.shift.trace_remove("write", trace)
        except (tk.TclError, ValueError):
            pass

    # ------------------------------------------------------------ drag & drop
    def _register_drop(self, widget, handler, on_hover=None):
        if not self.dnd_enabled:
            return False
        try:
            widget.drop_target_register(dnd.DND_FILES)

            def dropped(event):
                if on_hover:
                    on_hover(False)
                paths = dnd.parse_drop(event.data)
                if paths:
                    handler(paths)
                return event.action
            widget.dnd_bind("<<Drop>>", dropped)
            if on_hover:
                widget.dnd_bind("<<DropEnter>>", lambda e: (on_hover(True), e.action)[1])
                widget.dnd_bind("<<DropLeave>>", lambda e: (on_hover(False), e.action)[1])
            return True
        except Exception:
            return False

    def _load_text_file(self, widget, path):
        p = Path(path)
        try:
            if not p.is_file():
                raise ValueError("Bırakılan öğe bir dosya değil.")
            if p.stat().st_size > TEXT_LIMIT:
                raise ValueError("Dosya 5 MB metin sınırını aşıyor.")
            self.put(widget, p.read_text(encoding="utf-8-sig"))
            self.status("Dosya yüklendi · " + p.name)
            self.notify("success", "file", "Metin dosyası yüklendi", "Editöre aktarıldı")
        except UnicodeDecodeError:
            self.notify("error", "file", "Dosya metin olarak okunamadı", "UTF-8 metin dosyası bekleniyor")
        except Exception as exc:
            self.notify("error", "file", "Dosya yüklenemedi", str(exc))

    # ------------------------------------------------------------ HOME
    def _page_home(self):
        c = self.content
        hero = tk.Frame(c, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        hero.pack(fill="x", pady=(0, 14))
        inner = tk.Frame(hero, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=26, pady=20)
        left = tk.Frame(inner, bg=PANEL)
        eyebrow = tk.Frame(left, bg=PANEL)
        eyebrow.pack(anchor="w", pady=(8, 12))
        if self.img("logo_48") is not None:
            tk.Label(eyebrow, image=self.img("logo_48"), bg=PANEL).pack(side="left", padx=(0, 10))
        tk.Label(eyebrow, text="ELFCAESAR  /  CONTROL ROOM", bg=PANEL, fg=AMBER, font=F["label"]).pack(side="left")
        self.info_button(eyebrow, "start", None, 18, AMBER).pack(side="left", padx=(10, 0))
        _gl = tk.Label(eyebrow, text="KILAVUZ · F1", bg=PANEL, fg=MUTED, font=F["label"], cursor="hand2")
        _gl.pack(side="left", padx=(6, 0))
        _gl.bind("<Button-1>", lambda _e: self.open_guide("start"))
        sade = self.prefs.get("ui_mode") == "sade"
        tk.Label(left, text=("Parolaların, mesajların, dosyaların.\nŞifreli. Kontrol sende." if sade else
                             "Metnini dönüştür.\nKodunu çöz. Kontrol sende."), bg=PANEL, fg=FG,
                 font=F["display"], justify="left").pack(anchor="w", pady=(0, 10))
        self._wrap(tk.Label(left, text=("Parola kasası, uçtan uca şifreli mesaj, dosya ve klasör kasası, dijital imza ve KVKK araçları. "
                            "AES-256-GCM ve X25519 / Ed25519; hepsi bu bilgisayarda, çevrimdışı." if sade else
                            "29 harfli Türk alfabesi, Elf token sistemi ve Sezar kaydırması bir yanda; "
                            "AES-256-GCM kasası ve X25519 / Ed25519 kimlikleri diğer yanda. Hepsi bu bilgisayarda, çevrimdışı."),
                            bg=PANEL, fg=MUTED, font=F["body"], justify="left"), 10, 560).pack(anchor="w", fill="x")
        actions = tk.Frame(left, bg=PANEL, height=36)
        actions.pack(fill="x", pady=(20, 14))
        self._flow(actions, [
            *([StudioButton(actions, "PAROLA KASASI", lambda: self.show_page("passwords"), "primary", "lock"),
               StudioButton(actions, "GÜVENLİ KASA", lambda: self.show_page("vault"), "accent", "vault"),
               StudioButton(actions, "KVKK KALKANI", lambda: self.show_page("kvkk"), "ghost", "search")]
              if self.prefs.get("ui_mode") == "sade" else
              [StudioButton(actions, "KODLAMAYA BAŞLA", lambda: self.show_page("encode"), "primary", "encode"),
               StudioButton(actions, "GÜVENLİ KASA", lambda: self.show_page("vault"), "accent", "vault"),
               StudioButton(actions, "ANALİZ", lambda: self.show_page("analysis"), "ghost", "analysis")])])
        chips = tk.Frame(left, bg=PANEL)
        chips.pack(anchor="w")
        for text, col in (("OFFLINE", GREEN), ("API YOK", CYAN), ("HESAP YOK", AMBER)):
            Chip(chips, "●  " + text, col).pack(side="left", padx=(0, 6))
        core_wrap = tk.Frame(inner, bg=PANEL)
        self.core = AnimatedCore(core_wrap, 380, 290, center_image=self.img("mark_64"))
        self.core.pack(fill="both", expand=True)
        self._auto_grid(inner, [left, core_wrap], 470, 2, gap=18, weights=(3, 2))

        tiles_host = tk.Frame(c, bg=BG)
        tiles_host.pack(fill="x", pady=(0, 14))
        self.home_tiles = {}
        specs = [
            ("codec", "spark", "ELFC2 ÇEKİRDEĞİ", "Hazır", f"{len(ALPHABET)} harf · kaydırma 0–28", GREEN),
            ("crypto", "shield", "KASA MOTORU", "AES-256-GCM" if self.crypto_ok else "Eksik", self.crypto_detail,
             GREEN if self.crypto_ok else RED),
            ("session", "history", "OTURUM", "0 işlem", "Henüz işlem yapılmadı", CYAN),
            ("security", "shield", "GÜVENLİK SEVİYESİ", "—", "", GREEN),
        ]
        tiles = [self._stat_tile(tiles_host, *s) for s in specs]
        sec_tile = tiles[-1]
        for w in [sec_tile] + list(sec_tile.winfo_children()):
            w.bind("<Button-1>", lambda _e: self.show_page("security"))
            w.configure(cursor="hand2")
        self._auto_grid(tiles_host, tiles, 250, 4)

        tk.Label(c, text="MODÜLLER", bg=BG, fg=DIM, font=F["label"]).pack(anchor="w", pady=(2, 8))
        features_host = tk.Frame(c, bg=BG)
        features_host.pack(fill="x", pady=(0, 14))
        feats = [
            ("encode", "encode", "Kodlama", "Metni ELFC2 token paketine dönüştür; JSON olarak dışa aktar.", "HAZIR", AMBER),
            ("decode", "decode", "Çözme", "ELFC2 paketini doğrula ve özgün metne geri çevir.", "HAZIR", CYAN),
            ("analysis", "analysis", "Kaydırma Analizi", "29 kaydırmayı Türkçe benzerlik puanıyla sırala.", "PUANLAMA", GREEN),
            ("vault", "vault", "Güvenli Kasa", "Parolalı mesaj, kişiye özel paket ve dosya kasası.", "AES-GCM", CYAN),
            ("tengwar", "tengwar", "Sindarin · Tengwar", "Yazım modları ve harf tablosu; aktarım motoru hazırlıkta.", "ÖNİZLEME", VIOLET),
            ("alphabet", "alphabet", "Alfabe Laboratuvarı", "29 harf, token eşleşmeleri ve kaydırma önizlemesi.", "REFERANS", AMBER),
            ("security", "shield", "Güvenlik Merkezi", "Güvenlik seviyesi, öneri seviyeleri, pano ve kilit korumaları.", "YENİ", GREEN),
            ("bridge", "send", "Mesaj Köprüsü", "WhatsApp ve Telegram mesajlarını uçtan uca şifrele, seçip çöz.", "YENİ", CYAN),
        ]
        if self.prefs.get("ui_mode") == "sade":
            feats = [f for f in feats if f[0] not in SADE_HIDDEN]
        cards = [self._feature_card(features_host, *f) for f in feats]
        self._auto_grid(features_host, cards, 260, 4)
        self.badge_home_card(c).pack(fill="x", pady=(0, 14))

        act = self._card(c, "SİSTEM AKTİVİTESİ", "SON 30 DAKİKA  ·  YALNIZCA BU OTURUM", "analysis", CYAN)
        act.pack(fill="x", pady=(0, 6))
        body = tk.Frame(act, bg=PANEL)
        body.pack(fill="x", padx=16, pady=(0, 16))
        chart_box = tk.Frame(body, bg=PANEL)
        self.activity_chart = ActivityChart(chart_box, 190)
        self.activity_chart.pack(fill="x")
        side = tk.Frame(body, bg=PANEL)
        tk.Label(side, text="KATEGORİLER", bg=PANEL, fg=DIM, font=F["label"]).pack(anchor="w", pady=(0, 6))
        self.category_bars = CategoryBars(side, [(k, v, CATEGORY_COLORS[k]) for k, v in CATEGORIES.items()], 160)
        self.category_bars.pack(fill="x")
        recent_box = tk.Frame(body, bg=PANEL)
        head = tk.Frame(recent_box, bg=PANEL)
        head.pack(fill="x", pady=(0, 4))
        tk.Label(head, text="SON İŞLEMLER", bg=PANEL, fg=DIM, font=F["label"]).pack(side="left")
        StudioButton(head, "Tümü", lambda: self.show_page("history"), "ghost", "history", "sm").pack(side="right")
        self.recent_list = tk.Frame(recent_box, bg=PANEL)
        self.recent_list.pack(fill="x")
        self._auto_grid(body, [chart_box, side, recent_box], 300, 3, gap=22, weights=(5, 3, 4))
        self.refresh_dashboard()

    def _stat_tile(self, parent, key, glyph, label, value, sub, color):
        tile = tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        top = tk.Frame(tile, bg=PANEL)
        top.pack(fill="x", padx=16, pady=(14, 4))
        ic = tk.Canvas(top, width=30, height=30, bg=PANEL, highlightthickness=0)
        ic.pack(side="left")
        ic.create_oval(1, 1, 29, 29, fill=mix(color, PANEL, .82), outline="")
        icons.draw(ic, glyph, 15, 15, 14, color, width=1.6)
        tk.Label(top, text=label, bg=PANEL, fg=MUTED, font=F["label"]).pack(side="left", padx=10)
        dot = tk.Canvas(top, width=10, height=10, bg=PANEL, highlightthickness=0)
        dot.pack(side="right")
        dot.create_oval(1, 1, 9, 9, fill=color, outline="", tags="dot")
        val = tk.Label(tile, text=value, bg=PANEL, fg=FG, font=F["metric"], anchor="w")
        val.pack(fill="x", padx=16, pady=(6, 0))
        sub_l = tk.Label(tile, text=sub, bg=PANEL, fg=DIM, font=F["tiny"], anchor="w", justify="left")
        sub_l.pack(fill="x", padx=16, pady=(0, 14))
        self._wrap(sub_l, 32, 400)
        tk.Frame(tile, bg=color, height=2).pack(fill="x", side="bottom")
        self.home_tiles[key] = (val, sub_l, dot)
        return tile

    def _feature_card(self, parent, page, glyph, title, desc, chip, color):
        card = tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1, cursor="hand2")
        top = tk.Frame(card, bg=PANEL)
        top.pack(fill="x", padx=18, pady=(16, 10))
        ic = tk.Canvas(top, width=40, height=40, bg=PANEL, highlightthickness=0)
        ic.pack(side="left")
        ic.create_polygon(*rounded_points(1, 1, 39, 39, 10),
                          smooth=True, fill=mix(color, PANEL, .84), outline=mix(color, PANEL, .6))
        icons.draw(ic, glyph, 20, 20, 18, color, width=1.7)
        Chip(top, chip, color).pack(side="right", anchor="n")
        tk.Label(card, text=title, bg=PANEL, fg=FG, font=F["h3"]).pack(anchor="w", padx=18)
        self._wrap(tk.Label(card, text=desc, bg=PANEL, fg=MUTED, font=F["small"], justify="left"), 36, 420).pack(
            anchor="w", fill="x", padx=18, pady=(5, 12))
        StudioButton(card, "Aç", lambda p=page: self.show_page(p), "ghost", "encode", "sm").pack(anchor="w", padx=12, pady=(0, 12))

        def hover(on):
            card.configure(highlightbackground=mix(color, PANEL, .35) if on else LINE)
        for w in (card, top, ic):
            w.bind("<Enter>", lambda _e: hover(True), add="+")
            w.bind("<Leave>", lambda _e: hover(False), add="+")
            w.bind("<Button-1>", lambda _e, p=page: self.show_page(p))
        return card

    def refresh_dashboard(self):
        if "home" not in self.pages or not hasattr(self, "activity_chart"):
            return
        try:
            if not self.activity_chart.winfo_exists():
                return
        except tk.TclError:
            return
        user_ops = [i for i in self.log.items() if i.category != "system"]
        self.activity_chart.set_data(self.log.per_minute(30))
        self.category_bars.set_values(self.log.by_category())
        self._update_security_tile()
        val, sub, _dot = self.home_tiles["session"]
        val.configure(text=f"{len(user_ops)} işlem")
        rate = self.log.success_rate()
        errors = sum(1 for i in user_ops if i.level == "error")
        sub.configure(text="Henüz işlem yapılmadı" if not user_ops else
                      f"Başarı %{round((rate or 0) * 100)} · {errors} hata")
        for child in self.recent_list.winfo_children():
            child.destroy()
        recent = self.log.recent(5)
        if not recent:
            tk.Label(self.recent_list, text="Henüz kayıt yok.", bg=PANEL, fg=DIM, font=F["small"]).pack(anchor="w", pady=6)
        for item in recent:
            row = tk.Frame(self.recent_list, bg=PANEL)
            row.pack(fill="x", pady=3)
            color = LEVEL_COLORS.get(item.level, CYAN)
            d = tk.Canvas(row, width=10, height=10, bg=PANEL, highlightthickness=0)
            d.pack(side="left", padx=(0, 8))
            d.create_oval(1, 1, 9, 9, fill=color, outline="")
            tk.Label(row, text=item.clock, bg=PANEL, fg=DIM, font=F["mono_xs"]).pack(side="right")
            tk.Label(row, text=item.title, bg=PANEL, fg=FG_2, font=F["small"], anchor="w").pack(side="left", fill="x", expand=True)

    # ------------------------------------------------------------ ENCODE / DECODE
    def _page_encode(self):
        self._page_intro("01 / ENCODING WORKSPACE", "Metni ELFC2 formatına dönüştür",
                         "Kaynak metni gir, Sezar kaydırmasını belirle ve token çıktısını üret. Bu işlem şifreleme değildir; "
                         "gizlilik için Güvenli Kasa'yı kullan.", AMBER, "ELFC2  /  UTF-8", "encode")
        settings = self._card(self.content, "ENCODING PARAMETERS", "29 TÜRKÇE HARF · SHIFT 0–28", "spark")
        settings.pack(fill="x", pady=(0, 12))
        self._shift_control(settings, "Aynı değer çözme işleminde de kullanılmalıdır.")
        (self.enc_in, self.enc_in_metric), (self.enc_out, self.enc_out_metric) = self._editor_pair(
            ("01 / SOURCE TEXT", "GİRDİ · Düz metin veya UTF-8 dosya", CYAN, 14, True),
            ("02 / ELFC2 OUTPUT", "ÇIKTI · Token paketi", AMBER, 14, False))
        actions = self._card(self.content, "WORKSPACE ACTIONS", "İŞLEM ARAÇLARI", "spark")
        actions.pack(fill="x", pady=(12, 0))
        bar = tk.Frame(actions, bg=PANEL, height=36)
        bar.pack(fill="x", padx=14, pady=(0, 14))
        self._flow(bar, [
            StudioButton(bar, "KODLA", self.do_encode, "primary", "encode"),
            StudioButton(bar, "DOSYA AÇ", lambda: self.open_file(self.enc_in), "secondary", "open"),
            StudioButton(bar, "ÇÖZME EKRANINA GÖNDER", self.send_to_decode, "accent", "send"),
            StudioButton(bar, "ELF OLARAK KAYDET", lambda: self.save_file(self.enc_out, ".elf"), "secondary", "save"),
            StudioButton(bar, "JSON DIŞA AKTAR", self.save_json, "ghost", "export"),
        ])

    def _page_decode(self):
        self._page_intro("02 / DECODING WORKSPACE", "ELFC2 içeriğini özgün metne dönüştür",
                         "ELFC2 token verisini içe aktar, kodlama sırasında kullanılan kaydırma değerini seç ve özgün metni geri elde et. "
                         "Kaydırmayı bilmiyorsan paketi analize gönder.", CYAN, "ELFC2  /  REVERSE", "decode")
        settings = self._card(self.content, "DECODING PARAMETERS", "SHIFT 0–28", "spark", CYAN)
        settings.pack(fill="x", pady=(0, 12))
        self._shift_control(settings, "Yanlış kaydırma değeri hatalı veya anlamsız metin üretebilir.")
        (self.dec_in, self.dec_in_metric), (self.dec_out, self.dec_out_metric) = self._editor_pair(
            ("01 / ENCODED INPUT", "GİRDİ · ELFC2 token paketi", AMBER, 14, True),
            ("02 / DECODED TEXT", "ÇIKTI · Özgün metin ve Unicode", CYAN, 14, False))
        actions = self._card(self.content, "WORKSPACE ACTIONS", "İŞLEM ARAÇLARI", "spark", CYAN)
        actions.pack(fill="x", pady=(12, 0))
        bar = tk.Frame(actions, bg=PANEL, height=36)
        bar.pack(fill="x", padx=14, pady=(0, 14))
        self._flow(bar, [
            StudioButton(bar, "ÇÖZ", self.do_decode, "primary", "decode"),
            StudioButton(bar, "PAKET DOSYASI AÇ", lambda: self.open_file(self.dec_in), "secondary", "open"),
            StudioButton(bar, "ANALİZE GÖNDER", self.send_to_analysis, "accent", "analysis"),
            StudioButton(bar, "METİN OLARAK KAYDET", lambda: self.save_file(self.dec_out, ".txt"), "secondary", "save"),
        ])

    def send_to_decode(self):
        payload = self.get(self.enc_out).strip()
        if not payload:
            self.notify("warning", "codec", "Gönderilecek çıktı yok", "Önce KODLA ile çıktı üret")
            return
        self.show_page("decode")
        self.put(self.dec_in, payload)
        self.notify("info", "codec", "Çıktı çözme ekranına aktarıldı", f"Kaydırma {self.shift.get():02d}", toast=False)

    def send_to_analysis(self):
        payload = self.get(self.dec_in).strip()
        if not payload:
            self.notify("warning", "analysis", "Analiz edilecek paket yok", "Önce ELFC2 girdisi ekle")
            return
        self.show_page("analysis")
        self.put(self.brute_in, payload)
        self.do_brute()

    # ------------------------------------------------------------ ANALYSIS
    def _page_analysis(self):
        self._page_intro("03 / CRYPTANALYSIS", "29 kaydırmayı puanla ve karşılaştır",
                         "ELFC2 verisi için bütün Sezar kaydırmalarını üret. Her aday Türkçe harf sıklığına göre puanlanır; "
                         "puan yalnızca bir ipucudur, doğru metni sen seçersin.", GREEN, "29 SHIFT SCAN", "analysis")
        card, self.brute_in, _m = self._editor_panel(self.content, "01 / INPUT PAYLOAD", "ELFC2 TOKEN DATA", GREEN, 5, True)
        card.pack(fill="x")
        bar_card = self._card(self.content, "02 / ANALYSIS CONTROLS", "LOCAL PROCESSING", "spark", GREEN)
        bar_card.pack(fill="x", pady=12)
        bar = tk.Frame(bar_card, bg=PANEL, height=36)
        bar.pack(fill="x", padx=14, pady=(0, 14))
        self._flow(bar, [
            StudioButton(bar, "29 KAYDIRMAYI ANALİZ ET", self.do_brute, "primary", "analysis"),
            StudioButton(bar, "EN OLASI ADAYI ÇÖZMEYE AKTAR", self.use_best, "accent", "send"),
            StudioButton(bar, "SEÇİLİYİ ÇÖZMEYE AKTAR", self.use_brute, "secondary", "decode"),
            StudioButton(bar, "SEÇİLİ ADAYI KOPYALA", self.copy_analysis_candidate, "ghost", "copy"),
        ])
        chart_card = self._card(self.content, "03 / SCORE MAP", "TÜRKÇE BENZERLİK PUANI · 0–100", "analysis", GREEN)
        chart_card.pack(fill="x", pady=(0, 12))
        summary = tk.Frame(chart_card, bg=PANEL)
        summary.pack(fill="x", padx=16, pady=(0, 6))
        self.best_chip = Chip(summary, "EN OLASI · —", AMBER)
        self.best_chip.pack(side="left")
        self.sel_chip = Chip(summary, "SEÇİLİ · —", CYAN)
        self.sel_chip.pack(side="left", padx=6)
        tk.Label(summary, text="Bir çubuğa tıklayarak adayı seç", bg=PANEL, fg=DIM, font=F["tiny"]).pack(side="right")
        self.score_chart = ScoreChart(chart_card, self._select_shift, 160)
        self.score_chart.pack(fill="x", padx=14, pady=(0, 14))

        results = self._card(self.content, "04 / CANDIDATE RESULTS", "SHIFT · PUAN · OLASI METİN", "select", GREEN)
        results.pack(fill="both", expand=True)
        tools = tk.Frame(results, bg=PANEL)
        tools.pack(fill="x", padx=14, pady=(0, 8))
        search = tk.Frame(tools, bg=INPUT, highlightthickness=1, highlightbackground=LINE, highlightcolor=CYAN)
        search.pack(side="left", fill="x", expand=True)
        icons.icon_label(search, "search", MUTED, 13, INPUT).pack(side="left", padx=(8, 2))
        self.analysis_filter = tk.StringVar()
        entry = tk.Entry(search, textvariable=self.analysis_filter, bg=INPUT, fg=FG, insertbackground=CYAN,
                         relief="flat", font=F["small"], bd=0, highlightthickness=0)
        entry.pack(side="left", fill="x", expand=True, padx=6, ipady=7)
        self.analysis_filter.trace_add("write", lambda *_a: self._filter_analysis())
        StudioButton(search, "", lambda: self.analysis_filter.set(""), "ghost", "close", "sm",
                     tooltip="Filtreyi temizle").pack(side="right", padx=2)
        self.sort_control = Segmented(tools, [("shift", "KAYDIRMA"), ("score", "PUAN")], self._set_sort, self.analysis_sort)
        self.sort_control.pack(side="left", padx=(10, 0))
        self.analysis_count = tk.Label(results, text="HENÜZ ANALİZ YOK", bg=PANEL, fg=GREEN, font=F["mono_b"])
        self.analysis_count.pack(anchor="w", padx=16, pady=(0, 6))
        tree_wrap = tk.Frame(results, bg=PANEL)
        tree_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.tree = ttk.Treeview(tree_wrap, columns=("shift", "score", "text"), show="headings", height=12)
        self.tree.heading("shift", text="SHIFT", command=lambda: self._set_sort("shift", True))
        self.tree.heading("score", text="PUAN", command=lambda: self._set_sort("score", True))
        self.tree.heading("text", text="POSSIBLE PLAINTEXT", anchor="w")
        self.tree.heading("shift", anchor="center")
        self.tree.heading("score", anchor="w")
        self.tree.column("shift", width=80, anchor="center", stretch=False)
        self.tree.column("score", width=130, anchor="w", stretch=False)
        self.tree.column("text", width=900)
        self.tree.tag_configure("best", foreground=AMBER)
        self.tree.tag_configure("odd", background="#0d1724")
        tree_y = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        tree_x = ttk.Scrollbar(tree_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_y.set, xscrollcommand=tree_x.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_y.grid(row=0, column=1, sticky="ns")
        tree_x.grid(row=1, column=0, sticky="ew")
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._analysis_selection)
        self.tree.bind("<Double-1>", lambda _e: self.use_brute())
        if self.analysis_all_results:
            self._render_analysis()

    @staticmethod
    def _score_label(score):
        tier = "YÜKSEK" if score >= 50 else ("ORTA" if score >= 25 else "DÜŞÜK")
        return f"{score:>3}  ·  {tier}"

    def _set_sort(self, mode, sync_control=False):
        self.analysis_sort = mode
        if sync_control:
            self.sort_control.set(mode)
        self._filter_analysis()

    def _filter_analysis(self, _event=None):
        """Filter the already-computed candidates without rerunning analysis."""
        if not hasattr(self, "tree") or not self.tree.winfo_exists():
            return
        query = self.analysis_filter.get().strip().casefold()
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = list(self.analysis_all_results)
        if self.analysis_sort == "score":
            rows.sort(key=lambda r: (-r[2], r[0]))
        best = best_shift(self.analysis_all_results)
        shown = 0
        for shift, value, score in rows:
            if not query or query in f"{shift:02d}" or query in str(shift) or query in value.casefold():
                tags = ["best"] if shift == best else []
                if shown % 2:
                    tags.append("odd")
                self.tree.insert("", "end", iid=str(shift), tags=tags,
                                 values=(f"{int(shift):02d}", self._score_label(score), value.replace("\n", "  ⏎  ")))
                shown += 1
        total = len(self.analysis_all_results)
        if total:
            self.analysis_count.configure(text=f"{shown}/{total} ADAY GÖSTERİLİYOR" + ("" if not query else f"  ·  FİLTRE: “{query}”"))
        else:
            self.analysis_count.configure(text="HENÜZ ANALİZ YOK")

    def _render_analysis(self):
        best = best_shift(self.analysis_all_results)
        self.score_chart.set_scores([(s, sc) for s, _t, sc in self.analysis_all_results], best)
        if best is not None:
            score = next(sc for s, _t, sc in self.analysis_all_results if s == best)
            self.best_chip.set(f"EN OLASI · SHIFT {best:02d} · {score}")
        self.sel_chip.set("SEÇİLİ · —")
        self._filter_analysis()

    def _select_shift(self, shift):
        iid = str(shift)
        if not self.tree.exists(iid):
            self.analysis_filter.set("")
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)

    def _analysis_selection(self, _event=None):
        selected = self.tree.selection() if hasattr(self, "tree") else ()
        if selected:
            shift = int(self.tree.item(selected[0], "values")[0])
            score = next((sc for s, _t, sc in self.analysis_all_results if s == shift), 0)
            self.sel_chip.set(f"SEÇİLİ · SHIFT {shift:02d} · {score}")
            self.score_chart.select(shift)
            self.status(f"Aday seçildi · kaydırma {shift:02d}")

    def copy_analysis_candidate(self):
        selected = self.tree.selection()
        if not selected:
            self.notify("warning", "analysis", "Önce bir aday seç", "Tablodan veya puan haritasından")
            return
        shift = int(self.tree.item(selected[0], "values")[0])
        value = next((t for s, t, _sc in self.analysis_all_results if s == shift), "")
        self.clipboard_clear()
        self.clipboard_append(value)
        self.notify("success", "analysis", "Seçili aday panoya kopyalandı", toast=False)

    # ------------------------------------------------------------ TENGWAR
    def _page_tengwar(self):
        self._page_intro("05 / SCRIPT STUDIO", "Sindarin · Tengwar çalışma alanı",
                         "Tengwar bir yazı sistemidir; Sindarin ise bir dildir. Bu alan doğru yazım modunu seçmek ve sonraki "
                         "yazıya aktarım motorunu hazırlamak için tasarlandı. Henüz çeviri veya glif üretimi yapılmaz.",
                         VIOLET, "SCRIPT ≠ LANGUAGE", "tengwar")
        diag = self._card(self.content, "KAVRAM HARİTASI", "DİL → MOD → YAZI", "spark", VIOLET)
        diag.pack(fill="x", pady=(0, 12))
        canvas = tk.Canvas(diag, height=150, bg=PANEL, highlightthickness=0)
        canvas.pack(fill="x", padx=16, pady=(0, 14))

        def draw(_e=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            if w < 300:
                return
            nodes = [("SINDARIN", "dil · ses ve dilbilgisi", CYAN),
                     ("YAZIM MODU", "kural tablosu · ünlü gösterimi", AMBER),
                     ("TENGWAR", "yazı sistemi · glifler", VIOLET)]
            bw = min(230, (w - 120) / 3)
            gapx = (w - bw * 3) / 2
            for i, (title, sub, col) in enumerate(nodes):
                x = i * (bw + gapx)
                canvas.create_polygon(rounded_points(x + 1, 22, x + bw, 112, 12), smooth=True,
                                      fill=mix(col, PANEL, .88), outline=mix(col, PANEL, .45))
                canvas.create_text(x + bw / 2, 52, text=title, fill=col, font=F["h3"])
                canvas.create_text(x + bw / 2, 78, text=sub, fill=MUTED, font=F["tiny"])
                if i < 2:
                    x1, x2 = x + bw + 8, x + bw + gapx - 8
                    canvas.create_line(x1, 67, x2, 67, fill=LINE_2, width=2, arrow="last", arrowshape=(9, 10, 4))
            canvas.create_text(w / 2, 136, fill=DIM, font=F["tiny"],
                               text="Aynı Sindarin metni farklı modlarla farklı Tengwar dizilerine dönüşür.")
        canvas.bind("<Configure>", draw)

        tk.Label(self.content, text="YAZIM MODU SEÇİMİ", bg=BG, fg=DIM, font=F["label"]).pack(anchor="w", pady=(4, 8))
        self.tengwar_mode = getattr(self, "tengwar_mode", None) or tk.StringVar(value="general")
        modes_host = tk.Frame(self.content, bg=BG)
        modes_host.pack(fill="x", pady=(0, 12))
        modes = [("general", "Sindarin General Use", "Ómatehtar", "Ünlüler, harflerin üzerine konan tehtar işaretleriyle gösterilir.",
                  ["Tehtar bir sonraki ünsüzün üzerine yazılır", "Kompakt, yaygın kullanılan mod", "Font + işaret konumlama gerekir"]),
                 ("beleriand", "Mode of Beleriand", "Full Mode", "Ünlüler için ayrı tengwar harfleri kullanılır; tehtar gerekmez.",
                  ["Her ünlünün kendi harfi vardır", "Okuması daha doğrusal", "Moria kapısı yazıtında kullanılan mod"])]
        mode_cards = []
        self._mode_widgets = {}
        for key, title, tag, desc, bullets in modes:
            card = tk.Frame(modes_host, bg=PANEL, highlightthickness=2, highlightbackground=LINE, cursor="hand2")
            top = tk.Frame(card, bg=PANEL)
            top.pack(fill="x", padx=16, pady=(14, 6))
            ring = tk.Canvas(top, width=20, height=20, bg=PANEL, highlightthickness=0)
            ring.pack(side="left")
            tk.Label(top, text=title, bg=PANEL, fg=FG, font=F["h3"]).pack(side="left", padx=8)
            Chip(top, tag.upper(), VIOLET).pack(side="right")
            self._wrap(tk.Label(card, text=desc, bg=PANEL, fg=MUTED, font=F["small"], justify="left"), 36, 460).pack(
                anchor="w", fill="x", padx=16)
            for b in bullets:
                row = tk.Frame(card, bg=PANEL)
                row.pack(anchor="w", padx=16, pady=(6, 0))
                icons.icon_label(row, "check", GREEN, 11, PANEL).pack(side="left")
                tk.Label(row, text=b, bg=PANEL, fg=FG_2, font=F["small"]).pack(side="left", padx=4)
            tk.Frame(card, bg=PANEL, height=14).pack()
            self._mode_widgets[key] = (card, ring)
            for w in [card, top, ring] + list(top.winfo_children()):
                w.bind("<Button-1>", lambda _e, k=key: self._select_mode(k))
            mode_cards.append(card)
        self._auto_grid(modes_host, mode_cards, 380, 2)
        self._select_mode(self.tengwar_mode.get(), quiet=True)

        temar = self._card(self.content, "TÉMAR · TEMEL HARF TABLOSU", "4 SERİ × 6 DERECE · QUENYA ADLARI", "alphabet", VIOLET)
        temar.pack(fill="x", pady=(0, 12))
        grid = tk.Frame(temar, bg=PANEL)
        grid.pack(fill="x", padx=16, pady=(0, 8))
        series = [("I · TINCOTÉMA", "diş sesleri"), ("II · PARMATÉMA", "dudak sesleri"),
                  ("III · CALMATÉMA", "damak / Sindarin'de art damak"), ("IV · QUESSETÉMA", "yuvarlak art damak")]
        grades = ["1 · ötümsüz patlamalı", "2 · ötümlü patlamalı", "3 · ötümsüz sürtünmeli",
                  "4 · ötümlü sürtünmeli", "5 · genizsi", "6 · yarı ünlü"]
        names = [["tinco", "ando", "thúle", "anto", "númen", "óre"],
                 ["parma", "umbar", "formen", "ampa", "malta", "vala"],
                 ["calma", "anga", "harma", "anca", "noldo", "anna"],
                 ["quesse", "ungwe", "hwesta", "unque", "nwalme", "wilya"]]
        colors = [CYAN, AMBER, GREEN, VIOLET]
        tk.Label(grid, text="DERECE", bg=PANEL, fg=DIM, font=F["label"], anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 6))
        for ci, (s, desc) in enumerate(series, start=1):
            h = tk.Frame(grid, bg=PANEL)
            h.grid(row=0, column=ci, sticky="ew", padx=3, pady=(0, 6))
            tk.Frame(h, bg=colors[ci - 1], height=2).pack(fill="x")
            tk.Label(h, text=s, bg=PANEL, fg=colors[ci - 1], font=F["label"]).pack(anchor="w", pady=(5, 0))
            tk.Label(h, text=desc, bg=PANEL, fg=DIM, font=F["tiny"]).pack(anchor="w")
            grid.grid_columnconfigure(ci, weight=1, uniform="temar")
        for ri, g in enumerate(grades, start=1):
            tk.Label(grid, text=g, bg=PANEL, fg=MUTED, font=F["tiny"], anchor="w").grid(row=ri, column=0, sticky="w", padx=(0, 10))
            for ci in range(4):
                cell = tk.Label(grid, text=names[ci][ri - 1], bg=INPUT, fg=FG, font=F["body_b"], pady=8,
                                highlightthickness=1, highlightbackground=LINE)
                cell.grid(row=ri, column=ci + 1, sticky="ew", padx=3, pady=3)
                col = colors[ci]
                cell.bind("<Enter>", lambda _e, c=cell, col=col: c.configure(highlightbackground=col, fg=col))
                cell.bind("<Leave>", lambda _e, c=cell: c.configure(highlightbackground=LINE, fg=FG))
        tk.Label(temar, text="Referans tablosudur: harf adları gösterilir; Tengwar glifleri için uyumlu font sonraki aşamada eklenecek.",
                 bg=PANEL, fg=DIM, font=F["tiny"]).pack(anchor="w", padx=16, pady=(0, 14))

        road = self._card(self.content, "YOL HARİTASI", "AKTARIM MOTORU HAZIRLIĞI", "history", VIOLET)
        road.pack(fill="x", pady=(0, 12))
        steps = [("Dil / yazı ayrımı", "TAMAM", GREEN), ("Mod seçimi arayüzü", "TAMAM", GREEN),
                 ("Fonetik kural tablosu", "PLANLANDI", AMBER), ("Font ve glif çıktısı", "PLANLANDI", DIM)]
        stepper = tk.Canvas(road, height=92, bg=PANEL, highlightthickness=0)
        stepper.pack(fill="x", padx=16, pady=(0, 12))

        def draw_steps(_e=None):
            stepper.delete("all")
            w = stepper.winfo_width()
            if w < 200:
                return
            n = len(steps)
            xs = [30 + i * (w - 60) / (n - 1) for i in range(n)]
            for i in range(n - 1):
                done = steps[i + 1][1] == "TAMAM"
                stepper.create_line(xs[i] + 14, 26, xs[i + 1] - 14, 26, fill=GREEN if done else LINE_2, width=2,
                                    dash=() if done else (4, 4))
            for i, (x, (label, state, col)) in enumerate(zip(xs, steps)):
                stepper.create_oval(x - 13, 13, x + 13, 39, fill=mix(col, PANEL, .8), outline=col, width=1.5)
                if state == "TAMAM":
                    icons.draw(stepper, "check", x, 26, 12, col, width=2, tag="s")
                else:
                    stepper.create_text(x, 26, text=str(i + 1), fill=col, font=F["mono_b"])
                anchor = "w" if i == 0 else ("e" if i == n - 1 else "center")
                tx = x - 13 if i == 0 else (x + 13 if i == n - 1 else x)
                stepper.create_text(tx, 56, text=label, fill=FG_2, font=F["small"], anchor=anchor)
                stepper.create_text(tx, 75, text=state, fill=col, font=F["mono_xs"], anchor=anchor)
        stepper.bind("<Configure>", draw_steps)

        ed, self.tengwar_in, _m = self._editor_panel(self.content, "METİN HAZIRLAMA", "Sindarin metnini yaz veya yapıştır · aktarım motoru henüz etkin değil", VIOLET, 7, True)
        ed.pack(fill="both", expand=True)
        note = tk.Frame(self.content, bg=mix(AMBER, BG, .9), highlightthickness=1, highlightbackground=mix(AMBER, BG, .65))
        note.pack(fill="x", pady=(12, 0))
        icons.icon_label(note, "info", AMBER, 14, note.cget("bg")).pack(side="left", padx=(12, 6), pady=10, anchor="n")
        self._wrap(tk.Label(note, text="Bu sürümde Tengwar karakterleri üretilmez ve Sindarin çevirisi yapılmaz. Gerçek aktarım için fonetik "
                            "kurallar, mod tabloları ve uyumlu font desteği ayrı testlerle eklenecek.",
                            bg=note.cget("bg"), fg=AMBER, font=F["tiny"], justify="left"), 60).pack(side="left", fill="x", expand=True, pady=10)

    def _select_mode(self, key, quiet=False):
        self.tengwar_mode.set(key)
        for k, (card, ring) in self._mode_widgets.items():
            active = k == key
            card.configure(highlightbackground=VIOLET if active else LINE)
            ring.delete("all")
            ring.create_oval(2, 2, 18, 18, outline=VIOLET if active else LINE_2, width=1.5)
            if active:
                ring.create_oval(6, 6, 14, 14, fill=VIOLET, outline="")
        if not quiet:
            self.status("Yazım modu seçildi · " + ("General Use" if key == "general" else "Mode of Beleriand"))

    # ------------------------------------------------------------ ALPHABET
    def _page_alphabet(self):
        self._page_intro("06 / REFERENCE", "Türkçe alfabe ve Elf token eşleşmeleri",
                         "29 harfin her biri iki harfli bir Elf token'ına eşlenir. Bir harfe tıkla; seçili kaydırma değeriyle "
                         "nereye taşındığını gör.", AMBER, f"{len(ALPHABET)} HARF", "alphabet")
        detail = self._card(self.content, "HARF İNCELEME", "KAYDIRMA ÖNİZLEMESİ", "spark")
        detail.pack(fill="x", pady=(0, 12))
        self._shift_control(detail, "Bu değer Kodlama ve Çözme ekranlarıyla paylaşılır.")
        info = tk.Frame(detail, bg=PANEL)
        info.pack(fill="x", padx=16, pady=(0, 14))
        self.alpha_detail = tk.Label(info, text="Bir harf seç.", bg=PANEL, fg=FG_2, font=F["body"], anchor="w", justify="left")
        self.alpha_detail.pack(fill="x")
        grid = tk.Frame(self.content, bg=BG)
        grid.pack(fill="x")
        tiles = []
        self._alpha_tiles = {}
        for i, ch in enumerate(ALPHABET):
            tile = tk.Frame(grid, bg=PANEL, highlightthickness=1, highlightbackground=LINE, cursor="hand2")
            tk.Label(tile, text=f"{i + 1:02d}", bg=PANEL, fg=DIM, font=F["mono_xs"]).pack(anchor="w", padx=8, pady=(6, 0))
            tk.Label(tile, text=ch.upper() if ch != "i" else "İ", bg=PANEL, fg=FG, font=F["letter"]).pack(pady=(0, 0))
            tk.Label(tile, text=LETTER_TO_TOKEN[ch], bg=PANEL, fg=AMBER, font=F["mono_sm"]).pack(pady=(0, 9))
            for w in [tile] + list(tile.winfo_children()):
                w.bind("<Button-1>", lambda _e, idx=i: self._alpha_select(idx))
                w.bind("<Enter>", lambda _e, t=tile: t.configure(highlightbackground=CYAN) if t is not getattr(self, "_alpha_active", None) else None)
                w.bind("<Leave>", lambda _e, t=tile: t.configure(highlightbackground=LINE) if t is not getattr(self, "_alpha_active", None) else None)
            tiles.append(tile)
            self._alpha_tiles[i] = tile
        self._auto_grid(grid, tiles, 96, 10, gap=8)
        trace = self.shift.trace_add("write", lambda *_a: self._alpha_select(getattr(self, "_alpha_index", 0), quiet=True))
        grid.bind("<Destroy>", lambda _e: self._untrace(trace))
        self._alpha_select(0, quiet=True)

    def _alpha_select(self, idx, quiet=False):
        if not hasattr(self, "alpha_detail") or not self.alpha_detail.winfo_exists():
            return
        self._alpha_index = idx
        prev = getattr(self, "_alpha_active", None)
        if prev is not None and prev.winfo_exists():
            prev.configure(highlightbackground=LINE)
        tile = self._alpha_tiles[idx]
        tile.configure(highlightbackground=AMBER)
        self._alpha_active = tile
        try:
            s = self.shift.get()
        except tk.TclError:
            return
        ch = ALPHABET[idx]
        target = ALPHABET[(idx + s) % len(ALPHABET)]
        up = (lambda c: "İ" if c == "i" else c.upper())
        self.alpha_detail.configure(
            text=f"{up(ch)}  ·  sıra {idx + 1:02d}  ·  token “{LETTER_TO_TOKEN[ch]}”      →      kaydırma {s:02d} ile  "
                 f"{up(target)}  ·  token “{LETTER_TO_TOKEN[target]}”")

    # ------------------------------------------------------------ VAULT
    def _page_vault(self):
        self._page_intro("04 / SECURITY CENTER", "Güvenli kasa ve kişisel kimlik",
                         "Gerçek şifreleme, kimlik tabanlı mesaj paketleri ve dosya koruması tek çalışma alanında. "
                         "Bu bölüm ELFC2 metin kodlamasından ayrı çalışır.", CYAN, "AES-256-GCM", "vault")
        nav = tk.Frame(self.content, bg=BG)
        nav.pack(fill="x", pady=(0, 12))
        targets = {}
        self.vault_nav = Segmented(nav, [("msg", "ŞİFRELİ MESAJ"), ("id", "KİMLİKLER"), ("file", "DOSYA KASASI"), ("notes", "NOTLAR")],
                                   lambda k: self._scroll_to(targets[k]))
        self.vault_nav.pack(side="left")
        StudioButton(nav, "PAROLA ÜRET", self.show_passphrase, "ghost", "key", "sm").pack(side="right")

        banner = tk.Frame(self.content, bg=PANEL, highlightthickness=1, highlightbackground=mix(CYAN, PANEL, .6))
        banner.pack(fill="x", pady=(0, 12))
        tk.Frame(banner, bg=CYAN, width=3).pack(side="left", fill="y")
        icons.icon_label(banner, "shield", CYAN, 22, PANEL, 6).pack(side="left", padx=(14, 6), pady=14, anchor="n")
        bt = tk.Frame(banner, bg=PANEL)
        bt.pack(side="left", fill="x", expand=True, pady=12)
        tk.Label(bt, text="ELFC2 kodlamasından ayrı, parola tabanlı gerçek şifreleme.", bg=PANEL, fg=FG, font=F["h3"]).pack(anchor="w")
        chips = tk.Frame(bt, bg=PANEL)
        chips.pack(anchor="w", pady=(8, 0))
        for text in ("AES-256-GCM", "SCRYPT KDF", "RASTGELE SALT / NONCE", "DEĞİŞİKLİK ALGILAMA"):
            Chip(chips, text, CYAN).pack(side="left", padx=(0, 6))
        if not self.crypto_ok:
            Chip(bt, "UYARI · " + self.crypto_detail, RED).pack(anchor="w", pady=(8, 0))

        msg = self._card(self.content, "01 / SECURE MESSAGING", "PAROLA VEYA KİŞİ KARTI İLE ŞİFRELİ PAKET", "lock", CYAN)
        self.vault_msg_card = targets["msg"] = msg
        msg.pack(fill="both", expand=True, pady=(0, 12))
        pair = tk.Frame(msg, bg=PANEL)
        pair.pack(fill="both", expand=True, padx=12)
        left, self.sec_msg_in, _a = self._editor_panel(pair, "GİRDİ", "Düz mesaj veya şifreli paket (.elmsg / .elfdm)", CYAN, 6, True)
        right, self.sec_msg_out, _b = self._editor_panel(pair, "SONUÇ", "Şifreli paket veya çözülen mesaj", AMBER, 6)
        left.grid(row=0, column=0, sticky="nsew")
        right.grid(row=0, column=1, sticky="nsew")
        pair.bind("<Configure>", lambda e, l=left, r=right, h=pair: self._layout_editor_pair(e, l, r, h))
        bar = tk.Frame(msg, bg=PANEL, height=36)
        bar.pack(fill="x", padx=14, pady=(10, 14))
        self._flow(bar, [
            StudioButton(bar, "PAROLAYLA ŞİFRELE", self.secure_message_encrypt, "primary", "lock"),
            StudioButton(bar, "PAROLAYLA ÇÖZ", self.secure_message_decrypt, "secondary", "unlock"),
            StudioButton(bar, "PAKETİ AÇ", self.secure_message_open, "ghost", "open"),
            StudioButton(bar, "PAKETİ KAYDET", self.secure_message_save, "ghost", "save"),
            StudioButton(bar, "SONUCU GİRDİYE TAŞI", self.vault_swap, "ghost", "swap"),
        ])

        identity = self._card(self.content, "02 / PERSONAL CRYPTO IDENTITY", "X25519 · ED25519 · PARMAK İZİ", "idcard", VIOLET)
        self.vault_identity_card = targets["id"] = identity
        identity.pack(fill="x", pady=(0, 12))
        self._wrap(tk.Label(identity, text="Parola korumalı kişisel kimlik oluştur. Açık kişi kartını karşı tarafa gönder; özel anahtar "
                            "kimlik kasasında kalır. Kişiye özel mesajlar yukarıdaki GİRDİ alanından gönderilir.",
                            bg=PANEL, fg=MUTED, font=F["small"], justify="left")).pack(anchor="w", fill="x", padx=16, pady=(0, 10))
        groups = tk.Frame(identity, bg=PANEL)
        groups.pack(fill="x", padx=14, pady=(0, 6))
        g1 = tk.Frame(groups, bg=PANEL)
        g2 = tk.Frame(groups, bg=PANEL)
        for g, title in ((g1, "KİMLİK YÖNETİMİ"), (g2, "KİŞİYE ÖZEL MESAJ")):
            tk.Label(g, text=title, bg=PANEL, fg=DIM, font=F["label"]).pack(anchor="w", pady=(0, 6))
        b1 = tk.Frame(g1, bg=PANEL, height=36)
        b1.pack(fill="x")
        self._flow(b1, [StudioButton(b1, "YENİ KİMLİK", self.identity_create, "primary", "user"),
                        StudioButton(b1, "KİŞİ KARTINI DIŞA AKTAR", self.identity_export_contact, "secondary", "export"),
                        StudioButton(b1, "KİŞİ KARTINI DOĞRULA", self.identity_check_contact, "secondary", "check"),
                        StudioButton(b1, "KURTARMA KİTAPÇIĞI", self.make_paper_backup, "accent", "file"),
                        StudioButton(b1, "KİTAPÇIKTAN GERİ YÜKLE", self.restore_paper_backup, "ghost", "open")])
        b2 = tk.Frame(g2, bg=PANEL, height=36)
        b2.pack(fill="x")
        self._flow(b2, [StudioButton(b2, "KİŞİYE ŞİFRELE", self.identity_encrypt_message, "accent", "send"),
                        StudioButton(b2, "KİMLİĞİMLE ÇÖZ", self.identity_decrypt_message, "secondary", "key")])
        self._auto_grid(groups, [g1, g2], 420, 2, gap=24, weights=(3, 2))
        head = tk.Frame(identity, bg=PANEL)
        head.pack(fill="x", padx=16, pady=(10, 8))
        tk.Label(head, text="KİMLİK KARTLARI · BU OTURUM", bg=PANEL, fg=DIM, font=F["label"]).pack(side="left")
        self.id_count = Chip(head, "0 KART", VIOLET)
        self.id_count.pack(side="right")
        self.id_gallery = tk.Frame(identity, bg=PANEL)
        self.id_gallery.pack(fill="x", padx=14, pady=(0, 14))
        self._render_identity_cards()

        files = self._card(self.content, "03 / FILE & IMAGE VAULT", "PDF · DOCX · XLSX · PNG · JPG · ZIP · VB.", "file", GREEN)
        self.vault_files_card = targets["file"] = files
        files.pack(fill="x", pady=(0, 12))
        self._wrap(tk.Label(files, text="Kaynak dosya bayt düzeyinde şifrelenir; dosya adı şifreli başlıkta tutulur. "
                            ".elfvault dosyası bırakırsan çözme, diğer dosyalarda şifreleme başlar.",
                            bg=PANEL, fg=MUTED, font=F["small"], justify="left")).pack(anchor="w", fill="x", padx=16, pady=(0, 10))
        zone = DropZone(files, "Dosyayı buraya bırak" if self.dnd_enabled else "Dosya seçmek için tıkla",
                        "Şifreleme veya .elfvault çözme otomatik seçilir" if self.dnd_enabled else
                        "Sürükle-bırak için isteğe bağlı paket: tkinterdnd2", self._file_zone_pick)
        zone.pack(fill="x", padx=14)
        self._register_drop(zone, lambda paths: self._file_route(paths[0]), zone.set_active)
        fbar = tk.Frame(files, bg=PANEL, height=36)
        fbar.pack(fill="x", padx=14, pady=(10, 14))
        self._flow(fbar, [StudioButton(fbar, "DOSYA / GÖRÜNTÜ ŞİFRELE", self.secure_file_encrypt, "primary", "lock"),
                          StudioButton(fbar, "ŞİFRELİ DOSYAYI ÇÖZ", self.secure_file_decrypt, "secondary", "unlock")])

        note = self._card(self.content, "SECURITY NOTES", "OKU", "alert", AMBER)
        targets["notes"] = note
        note.pack(fill="x")
        for text in ("Parolayı unutursan kurtarma anahtarı yoktur.",
                     "Kişiye gönderim X25519 + HKDF + AES-256-GCM kullanır; imzalı paketler Ed25519 ile doğrulanır.",
                     "Parmak izini karşı tarafla ayrı bir kanaldan karşılaştır; kimlik mührü yalnızca görsel tanıma kolaylığıdır.",
                     "Bu sürüm sunuculu sohbet değildir; çevrimdışı şifreli paket alışverişidir. Meta verilerin bir kısmı görünür kalabilir.",
                     "İşlem geçmişi yalnızca işlem adlarını tutar; mesaj, parola veya dosya içeriği kaydedilmez ve diske yazılmaz."):
            row = tk.Frame(note, bg=PANEL)
            row.pack(fill="x", padx=16, pady=(0, 6))
            d = tk.Canvas(row, width=8, height=8, bg=PANEL, highlightthickness=0)
            d.pack(side="left", padx=(0, 8), anchor="n", pady=5)
            d.create_oval(1, 1, 7, 7, fill=AMBER, outline="")
            self._wrap(tk.Label(row, text=text, bg=PANEL, fg=FG_2, font=F["small"], justify="left"), 30).pack(side="left", fill="x", expand=True)
        tk.Frame(note, bg=PANEL, height=8).pack()

    def vault_swap(self):
        value = self.get(self.sec_msg_out)
        if not value:
            return
        self.put(self.sec_msg_in, value)
        self.put(self.sec_msg_out, "")
        self.status("Sonuç girdiye taşındı")

    def _file_zone_pick(self):
        src = filedialog.askopenfilename(title="Şifrelenecek dosyayı veya .elfvault kasasını seç")
        if src:
            self._file_route(src)

    def _file_route(self, path):
        if Path(path).suffix.lower() == ".elfvault":
            self.secure_file_decrypt(path)
        else:
            self.secure_file_encrypt(path)

    # identity cards ------------------------------------------------------
    def _add_identity_card(self, contact, role, note):
        fp = contact.get("fingerprint", "")
        self.identity_cards = [c for c in self.identity_cards if not (c["fingerprint"] == fp and c["role"] == role)]
        self.identity_cards.insert(0, {"name": contact.get("name", "?"), "fingerprint": fp, "role": role, "note": note})
        self._render_identity_cards()
        if hasattr(self, "id_gallery") and self.id_gallery.winfo_exists() and self.active_page == "vault":
            self.after(60, lambda: self._scroll_to(self.vault_identity_card))

    def _render_identity_cards(self):
        if not hasattr(self, "id_gallery") or not self.id_gallery.winfo_exists():
            return
        for child in self.id_gallery.winfo_children():
            child.destroy()
        self.id_gallery._cols = None
        self.id_count.set(f"{len(self.identity_cards)} KART")
        if not self.identity_cards:
            empty = tk.Frame(self.id_gallery, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            empty.pack(fill="x")
            icons.icon_label(empty, "idcard", DIM, 26, INPUT, 4).pack(pady=(16, 4))
            tk.Label(empty, text="Henüz kimlik kartı yok", bg=INPUT, fg=FG_2, font=F["body_b"]).pack()
            tk.Label(empty, text="Kimlik oluşturduğunda, kişi kartı doğruladığında veya imzalı mesaj açtığında görsel kart burada belirir.",
                     bg=INPUT, fg=DIM, font=F["tiny"]).pack(pady=(2, 16))
            return
        cards = []
        for data in self.identity_cards:
            fp = data["fingerprint"]
            card = IdentityCard(self.id_gallery, data["name"], fp, data["role"], data["note"],
                                on_copy=lambda f=fp: self._copy_fingerprint(f),
                                on_remove=lambda d=data: self._remove_identity_card(d))
            cards.append(card)
        self._auto_grid(self.id_gallery, cards, 340, 3)

    def _copy_fingerprint(self, fp):
        self.clipboard_clear()
        self.clipboard_append(fp)
        self.notify("success", "identity", "Parmak izi panoya kopyalandı", "Ayrı kanaldan karşılaştır", toast=False)

    def _remove_identity_card(self, data):
        if data in self.identity_cards:
            self.identity_cards.remove(data)
        self._render_identity_cards()

    # ------------------------------------------------------------ brand / logo
    def _load_brand(self):
        names = ["logo_256", "logo_128", "logo_96", "logo_64", "logo_48", "mark_64", "mark_48", "mark_40", "mark_32",
                 "mark_24", "mark_16", "dante_sig_520", "dante_sig_300", "dante_sig_180", "dante_sig_110"]
        names += [f"intro_a{i}" for i in range(1, 7)]
        for name in names:
            path = ASSETS / ("intro/logo_a" + name[-1] + ".png" if name.startswith("intro_a") else f"{name}.png")
            try:
                self.images[name] = tk.PhotoImage(file=str(path))
            except (tk.TclError, OSError):
                self.images[name] = None
        icons_ = [self.images[n] for n in ("logo_256", "logo_64", "mark_32", "mark_16") if self.images.get(n)]
        if icons_:
            try:
                self.iconphoto(True, *icons_)
            except tk.TclError:
                pass
        ico = ASSETS / "elfcaesar.ico"
        if os.name == "nt" and ico.exists():
            try:
                self.iconbitmap(default=str(ico))
            except tk.TclError:
                pass

    def _app_version_full(self):
        return APP_FULL_VERSION

    def _run_start_action(self, action, path=None):
        """Gezgin sağ tık menüsünden veya komut satırından gelen işlem."""
        if action == "encrypt-file" and path:
            self.show_page("vault")
            self.secure_file_encrypt(path)
        elif action == "decrypt-file" and path and folderlock.peek_is_folder_vault(path):
            self.show_page("toolbox")
            self.tb_unlock_folder(path)
        elif action == "lock-folder" and path:
            self.show_page("toolbox")
            self.tb_lock_folder(path)
        elif action == "sign-file" and path:
            self.show_page("toolbox")
            self.tb_sign(path)
        elif action == "verify-sig" and path:
            self.show_page("toolbox")
            self.tb_verify(path)
        elif action == "decrypt-file" and path:
            self.show_page("vault")
            self.secure_file_decrypt(path)
        elif action == "add-contact" and path:
            self.show_page("bridge")
            self.import_contact_file(path)
        elif action == "bridge":
            self.open_mini()
            self.iconify()
        elif action == "background":
            self.iconify()
        elif action == "open-message" and path:
            self.show_page("vault")
            try:
                self.put(self.sec_msg_in, Path(path).read_text(encoding="utf-8"))
                self.notify("info", "vault", "Şifreli mesaj paketi açıldı", "PAROLAYLA ÇÖZ veya KİMLİĞİMLE ÇÖZ")
            except Exception as exc:
                self.notify("error", "vault", "Paket açılamadı", str(exc))

    def img(self, name):
        return self.images.get(name)

    def _ensure_founder(self):
        if not self.prefs.get("founder_id"):
            import secrets as _secrets
            self.prefs["founder_id"] = _secrets.token_hex(8)
            self.prefs["founder_date"] = time.strftime("%d.%m.%Y")
            user_settings.save(self.prefs)

    def play_intro(self, first=False):
        self._ensure_founder()
        core = getattr(self, "core", None)
        if core is not None:
            core.stop()

        def done():
            if first:
                self.prefs["intro_seen"] = True
                self.prefs["last_version"] = APP_FULL_VERSION
                user_settings.save(self.prefs)
                self.notify("success", "system", "Hoş geldin! Kurucu Elf rozetin hazır", "Hakkında penceresinde seninle", toast=True)
            if self.active_page == "home" and core is not None and core.winfo_exists():
                core.start()
        self.intro = IntroExperience(self, done, self.prefs["founder_id"], self.prefs["founder_date"], replay=not first)

    def _maybe_whats_new(self, force=False):
        previous = self.prefs.get("last_version") or ""
        if force or (previous and previous != APP_FULL_VERSION):
            notes = notes_for(APP_FULL_VERSION)
            if notes:
                WhatsNewDialog(self, self.img("mark_48"), notes, previous or None)
        if previous != APP_FULL_VERSION:
            self.prefs["last_version"] = APP_FULL_VERSION
            user_settings.save(self.prefs)

    def show_about(self):
        founder = (self.prefs["founder_id"], self.prefs["founder_date"]) if self.prefs.get("founder_id") else None
        AboutDialog(self, self.img("logo_128"), f"{APP_FULL_VERSION} · {APP_CODENAME}", [
            "ELFC2 kodlama · AES-256-GCM + scrypt kasa · X25519 / Ed25519 kimlik",
            "Mesaj Köprüsü: WhatsApp · Telegram · e-posta için ELF1 sohbet zırhı",
            "Tamamen yerel ve çevrimdışı · hesap yok · API yok",
            f"Güvenlik seviyesi: {self.assessment['tier_name']} · {self.assessment['score']}/100",
            "Bağımsız güvenlik denetiminden geçmemiştir.",
            COPYRIGHT,
            "Ayarlar ve kişi defteri: %APPDATA%\\ElfCaesar · Hata günlükleri: %LOCALAPPDATA%\\ElfCaesar\\logs"],
            signature=self.img("dante_sig_300"), founder=founder,
            actions=[("HATA BİLDİR", lambda: self.report_bug()), ("GİZLİLİK", lambda: self.open_legal()),
                     ("ROZET VİTRİNİ", lambda: self.open_badges()), ("TANITIMI İZLE", lambda: self.play_intro()),
                     ("YENİLİKLER", lambda: self._maybe_whats_new(force=True))])

    def open_legal(self):
        page = runtime.resource_dir() / "docs" / "yasal" / "index.html"
        if page.exists():
            self._open_in_browser(page)

    def report_bug(self):
        from studio_ui import diagnostics
        text = diagnostics.report(self)
        self.clipboard_clear()
        self.clipboard_append(text)
        if messagebox.askyesno("Hata bildir", "Tanı raporu panoya kopyalandı. Rapor yalnızca sürüm, Windows bilgisi, ekran ölçeği, "
                               "sistem denetimi sonuçları ve hata türlerini içerir; parola, mesaj, dosya adı veya kişi bilgisi İÇERMEZ.\n\n"
                               "Beta bildirim sayfası tarayıcıda açılsın mı? Raporu açıklama kutusuna yapıştır (Ctrl+V).", parent=self):
            import webbrowser
            webbrowser.open(diagnostics.BETA_URL)

    def _show_splash(self):
        overlay = tk.Frame(self, bg=BG, cursor="watch")
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        overlay.lift()
        box = tk.Frame(overlay, bg=BG)
        box.place(relx=.5, rely=.46, anchor="center")
        if self.img("logo_256") is not None:
            tk.Label(box, image=self.img("logo_256"), bg=BG).pack()
        tk.Label(box, text="ELFCAESAR STUDIO", bg=BG, fg=FG, font=F["h1"]).pack(pady=(18, 2))
        tk.Label(box, text=f"{APP_VERSION}  ·  {APP_CODENAME.upper()}", bg=BG, fg=AMBER, font=F["mono_b"]).pack()
        if self.img("dante_sig_180") is not None:
            tk.Label(box, text="BİR DANTE ESERİ", bg=BG, fg=DIM, font=F["label"]).pack(pady=(14, 0))
            tk.Label(box, image=self.img("dante_sig_180"), bg=BG).pack()
        bar = tk.Canvas(box, width=280, height=6, bg=BG, highlightthickness=0)
        bar.pack(pady=(20, 6))
        msg = tk.Label(box, text="", bg=BG, fg=DIM, font=F["mono_xs"])
        msg.pack()
        steps = ["Çekirdek yükleniyor", "Kasa motoru denetleniyor", "Güvenlik seviyesi hesaplanıyor", "Hazır"]

        def tick(i=0):
            if not overlay.winfo_exists():
                return
            total = 36
            bar.delete("all")
            bar.create_polygon(rounded_points(0, 0, 280, 6, 3), smooth=True, fill=PANEL_2, outline="")
            bar.create_polygon(rounded_points(0, 0, max(6, 280 * i / total), 6, 3), smooth=True, fill=AMBER, outline="")
            msg.configure(text=steps[min(len(steps) - 1, i * len(steps) // total)].upper())
            if i < total:
                overlay.after(35, lambda: tick(i + 1))
            else:
                overlay.after(180, overlay.destroy)
        overlay.bind("<Button-1>", lambda _e: overlay.destroy())
        tick()

    # ------------------------------------------------------------ protections
    def _sensitive_widgets(self):
        return [w for w in (getattr(self, "sec_msg_in", None), getattr(self, "sec_msg_out", None)) if w is not None]

    def guarded_copy(self, value):
        from studio_ui import clipguard
        if not (self.sec.clipboard_guard and clipguard.set_sensitive(value)):
            self.clipboard_clear()
            self.clipboard_append(value)
        if not self.sec.clipboard_guard:
            self.status("Panoya kopyalandı · pano koruması kapalı", "warning")
            return
        if self._clip_job:
            self.after_cancel(self._clip_job)
        secs = self.sec.clipboard_seconds

        def wipe():
            self._clip_job = None
            try:
                current = self.clipboard_get()
            except tk.TclError:
                current = None
            if current == value:
                self.clipboard_clear()
                self.clipboard_append("")
                self.notify("info", "system", "Pano temizlendi", "Pano koruması", toast=False)
        self._clip_job = self.after(secs * 1000, wipe)
        self.notify("info", "vault", "Hassas içerik panoya kopyalandı", f"Pano koruması: {secs} sn sonra temizlenecek")

    def _touch(self, _event=None):
        self._last_activity = time.monotonic()

    def _idle_check(self):
        mins = self.sec.idle_lock_minutes
        if mins and not self._locked and time.monotonic() - self._last_activity > mins * 60:
            self.lock_screen("idle")
        self.after(10000, self._idle_check)

    def lock_screen(self, reason="manual"):
        if self._locked:
            return
        self._locked = True
        self._bridge_wipe()
        self.pw_lock(silent=True)
        out = getattr(self, "sec_msg_out", None)
        cleared = False
        if out is not None and out.winfo_exists() and self.get(out):
            self.put(out, "")
            cleared = True
        overlay = tk.Frame(self, bg="#05080d")
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        overlay.lift()
        self._lock_overlay = overlay
        box = tk.Frame(overlay, bg="#05080d")
        box.place(relx=.5, rely=.45, anchor="center")
        if self.img("logo_128") is not None:
            tk.Label(box, image=self.img("logo_128"), bg="#05080d").pack()
        title = {"idle": "GİZLİLİK KİLİDİ", "panic": "PANİK MODU", "manual": "EKRAN KİLİTLİ"}[reason]
        tk.Label(box, text=title, bg="#05080d", fg=RED if reason == "panic" else AMBER, font=F["h1"]).pack(pady=(16, 6))
        detail = {"idle": (f"{self.sec.idle_lock_minutes} dakika işlem yapılmadığı için ekran gizlendi."
                           if self.sec.idle_lock_minutes else "Ekran gizlendi."),
                  "panic": "Tüm editörler, analiz sonuçları, kimlik kartları ve pano temizlendi.",
                  "manual": "Ekran gizlendi."}[reason]
        tk.Label(box, text=detail, bg="#05080d", fg=FG_2, font=F["body"]).pack()
        if cleared and reason != "panic":
            tk.Label(box, text="Güvenli Kasa SONUÇ alanındaki açık metin temizlendi.", bg="#05080d", fg=MUTED,
                     font=F["small"]).pack(pady=(4, 0))
        tk.Label(box, text="Bu bir gizlilik perdesidir; hesap parolası yoktur.", bg="#05080d", fg=DIM,
                 font=F["tiny"]).pack(pady=(8, 16))
        btn = StudioButton(box, "DEVAM ET", self._unlock, "primary", "unlock", min_width=160)
        btn.pack()
        btn.focus_set()
        self.notify("warning", "system", title.capitalize(), detail, toast=False)

    def _unlock(self):
        overlay = getattr(self, "_lock_overlay", None)
        if overlay is not None and overlay.winfo_exists():
            overlay.destroy()
        self._locked = False
        self._touch()

    def panic(self):
        self.pw_lock(silent=True)
        for name in ("enc_in", "enc_out", "dec_in", "dec_out", "brute_in", "sec_msg_in", "sec_msg_out", "tengwar_in"):
            w = getattr(self, name, None)
            if w is not None and w.winfo_exists():
                self.put(w, "")
                w.edit_reset()
        self.analysis_all_results = []
        self.analysis_payload = ""
        if hasattr(self, "tree") and self.tree.winfo_exists():
            self.tree.delete(*self.tree.get_children())
            self.score_chart.set_scores([])
            self.best_chip.set("EN OLASI · —")
            self.sel_chip.set("SEÇİLİ · —")
            self.analysis_count.configure(text="HENÜZ ANALİZ YOK")
        self.identity_cards = []
        self._render_identity_cards()
        if self._clip_job:
            self.after_cancel(self._clip_job)
            self._clip_job = None
        self.clipboard_clear()
        self.clipboard_append("")
        self.sec.panic_used += 1
        self.lock_screen("panic")

    def set_pref(self, key, value):
        self.prefs[key] = value
        if key == "ui_mode" and value != self._ui_mode_start:
            self.after(100, lambda: messagebox.showinfo("Arayüz modu", "Yeni arayüz modu uygulamayı yeniden başlatınca uygulanır.", parent=self))
        if key == "capture_shield":
            self.sec.capture_shield = value
            self.apply_capture_mode()
        saved = user_settings.save(self.prefs)
        if hasattr(self.sec, key):
            setattr(self.sec, key, value)
        self.refresh_security()
        self.status("Ayar güncellendi" + ("" if saved else " · diske yazılamadı, bu oturum için geçerli"), "success")

    # ------------------------------------------------------------ security center
    def refresh_security(self):
        self.assessment = a = assess(self.sec)
        if hasattr(self, "log") and hasattr(self, "prefs"):
            self.after_idle(self.badge_check)
        col = TIER_COLORS[a["tier"]]
        bg = mix(col, BG, .86)
        if hasattr(self, "pill"):
            self.pill.configure(bg=bg, highlightbackground=mix(col, BG, .55))
            self.pulse_dot.configure(bg=bg)
            self.pulse_dot.itemconfigure("dot", fill=col)
            self.pill_label.configure(bg=bg, fg=col, text=f"GÜVENLİK · {a['tier_name'].upper()} {a['score']}")
        self._update_security_tile()
        if "security" in self.pages and hasattr(self, "sec_gauge") and self.sec_gauge.winfo_exists():
            self._render_security()

    def _update_security_tile(self):
        tiles = getattr(self, "home_tiles", {})
        if "security" not in tiles:
            return
        val, sub, dot = tiles["security"]
        if not val.winfo_exists():
            return
        a = self.assessment
        col = TIER_COLORS[a["tier"]]
        val.configure(text=f"{a['tier_name']} · {a['score']}", fg=col)
        sub.configure(text="Tüm öneriler uygulandı" if not a["open_issues"] else f"{a['open_issues']} açık öneri · ayrıntı için tıkla")
        dot.itemconfigure("dot", fill=col)

    def _page_security(self):
        self._page_intro("08 / SECURITY INTELLIGENCE", "Güvenlik seviyesi ve öneri seviyeleri",
                         "Uygulama ayarlarından ve bu oturumdaki kasa kullanımından hesaplanan yerel bir güvenlik puanı. "
                         "Hiçbir parola, mesaj veya dosya içeriği puana dahil edilmez ya da kaydedilmez.",
                         GREEN, "YEREL HESAPLAMA", "shield")
        top = tk.Frame(self.content, bg=BG)
        top.pack(fill="x", pady=(0, 12))
        gcard = self._card(top, "GÜVENLİK SEVİYESİ", "0–100", "shield", GREEN)
        self.sec_gauge = SecurityGauge(gcard, 320, center_image=self.img("mark_48"))
        self.sec_gauge.pack(padx=16)
        self.sec_gauge_note = tk.Label(gcard, text="", bg=PANEL, fg=MUTED, font=F["small"])
        self.sec_gauge_note.pack(pady=(0, 14))
        lcard = self._card(top, "GÜVENLİK KADEMELERİ", "ÇIRAK → MİTHRİL", "analysis", GREEN)
        self.sec_ladder = tk.Frame(lcard, bg=PANEL)
        self.sec_ladder.pack(fill="x", padx=16, pady=(0, 6))
        self.sec_next = tk.Label(lcard, text="", bg=PANEL, fg=FG_2, font=F["small"], anchor="w")
        self.sec_next.pack(fill="x", padx=16, pady=(0, 14))
        self._auto_grid(top, [gcard, lcard], 400, 2, gap=12, weights=(2, 3))

        self.sec_factors = tk.Frame(self.content, bg=BG)
        self.sec_factors.pack(fill="x", pady=(0, 12))

        adv = self._card(self.content, "ÖNERİ SEVİYELERİ", "ÖNCELİĞE GÖRE SIRALI", "alert", AMBER)
        adv.pack(fill="x", pady=(0, 12))
        legend = tk.Frame(adv, bg=PANEL)
        legend.pack(fill="x", padx=16, pady=(0, 8))
        for key, label in (("critical", "KRİTİK"), ("high", "YÜKSEK"), ("medium", "ORTA"), ("low", "DÜŞÜK"), ("info", "BİLGİ")):
            Chip(legend, label, ADVICE_COLORS[key]).pack(side="left", padx=(0, 6))
        self.sec_advice = tk.Frame(adv, bg=PANEL)
        self.sec_advice.pack(fill="x", padx=14, pady=(0, 14))

        prot = self._card(self.content, "KORUMALAR", "AYARLAR BU BİLGİSAYARDA SAKLANIR · İÇERİK SAKLANMAZ", "lock", CYAN)
        prot.pack(fill="x", pady=(0, 12))
        self._setting_row(prot, "Pano koruması", "Parola ve kasa içeriği kopyalandığında pano belirli süre sonra temizlenir.",
                          toggle=("clipboard_guard",),
                          segmented=("clipboard_seconds", [(15, "15 SN"), (30, "30 SN"), (60, "60 SN")]))
        self._setting_row(prot, "Otomatik gizlilik kilidi", "İşlem yapılmazsa ekran gizlenir ve kasa SONUÇ alanındaki açık metin silinir.",
                          segmented=("idle_lock_minutes", [(0, "KAPALI"), (2, "2 DK"), (5, "5 DK"), (10, "10 DK")]))
        self._setting_row(prot, "Hassas veri uyarısı", "ELFC2 kodlamasından önce e-posta, IBAN, kart, T.C. kimlik, telefon ve parola ifadelerini yakalar.",
                          toggle=("sensitive_warning",))
        self._setting_row(prot, "Ekran görüntüsü kalkanı", "Seçilen pencereler ekran görüntüsünde ve ekran paylaşımında siyah görünür "
                          "(Windows 10 2004+). Telefonla çekilen fotoğrafı engelleyemez.",
                          segmented=("capture_shield", [("off", "KAPALI"), ("sensitive", "HASSAS PENCERELER"), ("all", "TÜM UYGULAMA")]))
        self._setting_row(prot, "Açılış ekranı", "Uygulama açılırken logolu açılış ekranını gösterir.", toggle=("splash",))
        self._setting_row(prot, "Arayüz modu", "SADE: yalnızca güvenlik araçları (Parola Kasası, Güvenli Kasa, Köprü, KVKK, Araç Kutusu). "
                          "TAM: ELFC2 Elf yazısı, Kaydırma Analizi, Tengwar ve Alfabe de görünür. Değişiklik yeniden başlatınca uygulanır.",
                          segmented=("ui_mode", [("sade", "SADE"), ("full", "TAM")]), last=True)

        lab = self._card(self.content, "PAROLA LABORATUVARI", "KALKAN SEVİYESİ · HİÇBİR YERE KAYDEDİLMEZ", "key", VIOLET)
        self.sec_lab_card = lab
        lab.pack(fill="x", pady=(0, 12))
        row = tk.Frame(lab, bg=PANEL)
        row.pack(fill="x", padx=16, pady=(0, 8))
        box = tk.Frame(row, bg=INPUT, highlightthickness=1, highlightbackground=LINE_2, highlightcolor=VIOLET)
        box.pack(side="left", fill="x", expand=True)
        self.lab_pw = tk.StringVar()
        entry = tk.Entry(box, textvariable=self.lab_pw, show="•", bg=INPUT, fg=FG, insertbackground=VIOLET, relief="flat",
                         font=F["mono"], bd=0, highlightthickness=0)
        entry.pack(fill="x", padx=10, ipady=8)
        self.lab_show = False

        def toggle_show():
            self.lab_show = not self.lab_show
            entry.configure(show="" if self.lab_show else "•")
        StudioButton(row, "", toggle_show, "ghost", "select", tooltip="Göster / gizle").pack(side="left", padx=(8, 0))
        StudioButton(row, "ÜRET", lambda: (self.lab_pw.set(generate_passphrase(5)), self.lab_show or toggle_show()),
                     "secondary", "key").pack(side="left", padx=(6, 0))
        StudioButton(row, "", lambda: self.lab_pw.set(""), "ghost", "clear", tooltip="Temizle").pack(side="left", padx=(6, 0))
        meter = StrengthMeter(lab)
        meter.pack(fill="x", padx=16, pady=(4, 10))
        tk.Label(lab, text="KIRILMA SÜRESİ · SALDIRI SENARYOLARI", bg=PANEL, fg=DIM, font=F["label"]).pack(anchor="w", padx=16, pady=(4, 6))
        crack = CrackTable(lab, self.prefs.get("attacker_hw", "rtx4090"), lambda hw: self.set_pref("attacker_hw", hw))
        crack.pack(fill="x", padx=16, pady=(0, 12))
        ladder = tk.Frame(lab, bg=PANEL)
        ladder.pack(fill="x", padx=16, pady=(0, 14))
        from studio_ui.security import PASSWORD_LEVELS
        from studio_ui.theme import STRENGTH_COLORS
        for i, (_t, name, summary, color) in enumerate(PASSWORD_LEVELS, start=1):
            Chip(ladder, f"{i} · {name.upper()}", STRENGTH_COLORS[color]).pack(side="left", padx=(0, 6), pady=2)
        self.lab_pw.trace_add("write", lambda *_a: (meter.update_result(password_strength(self.lab_pw.get()) if self.lab_pw.get() else None),
                                                   crack.update_password(self.lab_pw.get())))

        pan = tk.Frame(self.content, bg=mix(RED, BG, .9), highlightthickness=1, highlightbackground=mix(RED, BG, .55))
        pan.pack(fill="x")
        icons.icon_label(pan, "alert", RED, 20, pan.cget("bg"), 6).pack(side="left", padx=(14, 6), pady=14, anchor="n")
        pt = tk.Frame(pan, bg=pan.cget("bg"))
        pt.pack(side="left", fill="x", expand=True, pady=12)
        tk.Label(pt, text="Panik modu", bg=pan.cget("bg"), fg=FG, font=F["h3"]).pack(anchor="w")
        self._wrap(tk.Label(pt, text="Tek tuşla bütün editörleri, analiz sonuçlarını, kimlik kartlarını ve panoyu temizler, "
                            "ardından ekranı gizler. Kısayol: Ctrl+Shift+L. Diskteki dosyalara dokunmaz.",
                            bg=pan.cget("bg"), fg=MUTED, font=F["small"], justify="left"), 20).pack(anchor="w", fill="x")
        pb = tk.Frame(pan, bg=pan.cget("bg"))
        pb.pack(side="right", padx=14)
        StudioButton(pb, "EKRANI KİLİTLE", lambda: self.lock_screen("manual"), "secondary", "lock").pack(pady=(0, 6), fill="x")
        StudioButton(pb, "PANİK · TEMİZLE", self.panic, "danger", "trash").pack(fill="x")
        self._render_security(animate=False)

    def _setting_row(self, card, title, desc, toggle=None, segmented=None, last=False):
        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x", padx=16, pady=(0, 0 if last else 2))
        left = tk.Frame(row, bg=PANEL)
        left.pack(side="left", fill="x", expand=True, pady=8)
        tk.Label(left, text=title, bg=PANEL, fg=FG, font=F["body_b"], anchor="w").pack(fill="x")
        self._wrap(tk.Label(left, text=desc, bg=PANEL, fg=MUTED, font=F["tiny"], justify="left"), 10, 620).pack(fill="x")
        right = tk.Frame(row, bg=PANEL)
        right.pack(side="right", padx=(12, 0))
        if segmented:
            key, options = segmented
            seg = Segmented(right, [(v, lab) for v, lab in options], lambda v, k=key: self.set_pref(k, v), self.prefs[key])
            seg.pack(side="right", padx=(10, 0))
        if toggle:
            key = toggle[0]
            ToggleSwitch(right, self.prefs[key], lambda v, k=key: self.set_pref(k, v)).pack(side="right")
        if not last:
            tk.Frame(card, bg=LINE, height=1).pack(fill="x", padx=16)
        else:
            tk.Frame(card, bg=PANEL, height=10).pack()

    def _render_security(self, animate=True):
        a = self.assessment
        col = TIER_COLORS[a["tier"]]
        self.sec_gauge.set(a["score"], a["tier"], a["tier_name"], animate=animate)
        self.sec_gauge_note.configure(text=f"{a['tier_desc']}  ·  {a['open_issues']} açık öneri")
        for child in self.sec_ladder.winfo_children():
            child.destroy()
        bounds = [t for t, *_r in SECURITY_TIERS] + [101]
        for i, (threshold, name, desc) in enumerate(SECURITY_TIERS):
            current = i == a["tier"]
            tc = TIER_COLORS[i]
            r = tk.Frame(self.sec_ladder, bg=mix(tc, PANEL, .86) if current else PANEL,
                         highlightthickness=1, highlightbackground=tc if current else LINE)
            r.pack(fill="x", pady=3)
            d = tk.Canvas(r, width=14, height=14, bg=r.cget("bg"), highlightthickness=0)
            d.pack(side="left", padx=(12, 8), pady=9)
            d.create_oval(2, 2, 12, 12, fill=tc if i <= a["tier"] else r.cget("bg"), outline=tc)
            tk.Label(r, text=name, bg=r.cget("bg"), fg=FG if current else FG_2, font=F["body_b"], width=9, anchor="w").pack(side="left")
            tk.Label(r, text=f"{threshold}–{bounds[i + 1] - 1}", bg=r.cget("bg"), fg=DIM, font=F["mono_xs"], width=7).pack(side="left")
            tk.Label(r, text=desc, bg=r.cget("bg"), fg=MUTED, font=F["tiny"], anchor="w").pack(side="left", fill="x", expand=True)
            if current:
                Chip(r, "ŞU AN", tc).pack(side="right", padx=10)
        nt = a["next_tier"]
        self.sec_next.configure(text="En yüksek kademedesin. Bu düzeni koru." if nt is None else
                                f"Sonraki kademe: {nt[1]} — {nt[0] - a['score']} puan daha. Aşağıdaki önerileri uygula.",
                                fg=col if nt is None else FG_2)
        # faktörler
        for child in self.sec_factors.winfo_children():
            child.destroy()
        self.sec_factors._cols = None
        s = self.sec
        from studio_ui.security import PASSWORD_LEVELS
        pl = s.last_password_level
        total_send = s.signed_sends + s.unsigned_sends
        total_open = s.pinned_opens + s.unpinned_opens
        facts = [
            ("shield", "KASA MOTORU", "Hazır" if s.crypto_ok else "Eksik", "AES-256-GCM · scrypt", s.crypto_ok),
            ("key", "SON KASA PAROLASI", "Henüz yok" if pl is None else PASSWORD_LEVELS[pl][1],
             "Yeni kasa oluşturunca ölçülür" if pl is None else f"Seviye {pl + 1}/5", pl is None or pl >= 3),
            ("copy", "PANO KORUMASI", f"Açık · {s.clipboard_seconds} sn" if s.clipboard_guard else "Kapalı",
             "Hassas kopyalar otomatik silinir", s.clipboard_guard),
            ("lock", "GİZLİLİK KİLİDİ", f"{s.idle_lock_minutes} dk" if s.idle_lock_minutes else "Kapalı",
             "Hareketsizlikte ekranı gizler", bool(s.idle_lock_minutes) and s.idle_lock_minutes <= 10),
            ("send", "İMZALI GÖNDERİM", f"{s.signed_sends}/{total_send}" if total_send else "—",
             "Ed25519 imzalı kişiye özel mesaj", not s.unsigned_sends),
            ("idcard", "SABİTLENMİŞ GÖNDEREN", f"{s.pinned_opens}/{total_open}" if total_open else "—",
             "Güvenilen kişi kartıyla açılan mesaj", not s.unpinned_opens),
        ]
        tiles = []
        for glyph, label, value, sub, ok in facts:
            colr = GREEN if ok else ORANGE
            t = tk.Frame(self.sec_factors, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            top = tk.Frame(t, bg=PANEL)
            top.pack(fill="x", padx=14, pady=(12, 2))
            icons.icon_label(top, glyph, colr, 14, PANEL).pack(side="left")
            tk.Label(top, text=label, bg=PANEL, fg=MUTED, font=F["label"]).pack(side="left", padx=8)
            Chip(top, "İYİ" if ok else "GELİŞTİR", colr).pack(side="right")
            tk.Label(t, text=value, bg=PANEL, fg=FG, font=F["h2"], anchor="w").pack(fill="x", padx=14, pady=(6, 0))
            tk.Label(t, text=sub, bg=PANEL, fg=DIM, font=F["tiny"], anchor="w").pack(fill="x", padx=14, pady=(0, 12))
            tiles.append(t)
        self._auto_grid(self.sec_factors, tiles, 240, 3)
        # öneriler
        for child in self.sec_advice.winfo_children():
            child.destroy()
        labels = {"install": "NASIL KURULUR", "password_lab": "LABORATUVAR", "open_identity": "KİMLİKLERE GİT",
                  "open_vault": "KASAYA GİT", "enable_clipboard": "ETKİNLEŞTİR", "enable_idle": "5 DK YAP",
                  "enable_sensitive": "ETKİNLEŞTİR", "open_bridge": "KÖPRÜYE GİT", "paper_backup": "KİTAPÇIK OLUŞTUR", "create_identity": "KİMLİK OLUŞTUR",
                  "open_passwords": "PAROLA KASASI", "fix_passwords": "DENETİMİ AÇ",
                  "enable_capture": "ETKİNLEŞTİR"}
        for item in a["advice"]:
            c = ADVICE_COLORS[item["level"]]
            r = tk.Frame(self.sec_advice, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            r.pack(fill="x", pady=3)
            tk.Frame(r, bg=c, width=3).pack(side="left", fill="y")
            Chip(r, item["label"], c).pack(side="left", padx=(12, 10), pady=12, anchor="n")
            body = tk.Frame(r, bg=INPUT)
            body.pack(side="left", fill="x", expand=True, pady=9)
            tk.Label(body, text=item["title"], bg=INPUT, fg=FG, font=F["body_b"], anchor="w").pack(fill="x")
            self._wrap(tk.Label(body, text=item["detail"], bg=INPUT, fg=MUTED, font=F["tiny"], justify="left"), 10, 760).pack(fill="x")
            if item["impact"]:
                tk.Label(r, text=f"+{item['impact']} PUAN", bg=INPUT, fg=c, font=F["mono_xs"]).pack(side="right", padx=(0, 12))
            if item["action"]:
                StudioButton(r, labels[item["action"]], lambda act=item["action"]: self._advice_action(act),
                             "secondary", None, "sm").pack(side="right", padx=(0, 10))

    def _advice_action(self, action):
        if action == "install":
            messagebox.showinfo("Kasa motorunu kur", "Komut istemi veya PowerShell'de uygulama klasöründe çalıştır:\n\n"
                                "py -3 -m pip install -r requirements.txt\n\nArdından uygulamayı yeniden başlat.", parent=self)
        elif action == "password_lab":
            self._scroll_to(self.sec_lab_card)
        elif action == "open_identity":
            self.show_page("vault")
            self.after(60, lambda: self._scroll_to(self.vault_identity_card))
        elif action == "open_vault":
            self.show_page("vault")
        elif action == "enable_clipboard":
            self.set_pref("clipboard_guard", True)
            self._rebuild_security_page()
        elif action == "enable_idle":
            self.set_pref("idle_lock_minutes", 5)
            self._rebuild_security_page()
        elif action == "enable_sensitive":
            self.set_pref("sensitive_warning", True)
            self._rebuild_security_page()
        elif action == "open_bridge":
            self.show_page("bridge")
        elif action == "paper_backup":
            self.make_paper_backup()
        elif action == "create_identity":
            self.show_page("vault")
            self.after(60, lambda: self._scroll_to(self.vault_identity_card))
        elif action in ("open_passwords", "fix_passwords"):
            self.show_page("passwords")
        elif action == "enable_capture":
            self.set_pref("capture_shield", "sensitive")
            self._rebuild_security_page()

    def _rebuild_security_page(self):
        """Ayar kontrolleri (anahtar/segment) yeni değeri göstersin diye sayfayı yeniden kur."""
        if self.active_page != "security":
            frame = self.pages.pop("security", None)
            if frame is not None:
                frame.destroy()
            return
        pos = self.content_canvas.yview()[0]
        frame = self.pages.pop("security")
        self.active_page = None
        frame.destroy()
        self.show_page("security")
        self.content_canvas.yview_moveto(pos)

    # ------------------------------------------------------------ HISTORY
    def _page_history(self):
        self._page_intro("07 / ACTIVITY LOG", "Bildirimler ve işlem geçmişi",
                         "Bu oturumda yapılan işlemler. Yalnızca işlem adı, kategori ve sonuç tutulur; içerik, parola ve "
                         "anahtar asla kaydedilmez. Uygulama kapanınca geçmiş silinir.", CYAN, "BELLEKTE · DİSKE YAZILMAZ", "history")
        stats = tk.Frame(self.content, bg=BG)
        stats.pack(fill="x", pady=(0, 12))
        self.hist_stats = {}
        tiles = []
        for key, label, color in (("total", "TOPLAM", CYAN), ("success", "BAŞARILI", GREEN),
                                  ("warning", "UYARI", AMBER), ("error", "HATA", RED)):
            t = tk.Frame(stats, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            tk.Frame(t, bg=color, height=2).pack(fill="x")
            tk.Label(t, text=label, bg=PANEL, fg=MUTED, font=F["label"]).pack(anchor="w", padx=14, pady=(10, 0))
            v = tk.Label(t, text="0", bg=PANEL, fg=FG, font=F["metric"])
            v.pack(anchor="w", padx=14, pady=(0, 10))
            self.hist_stats[key] = v
            tiles.append(t)
        self._auto_grid(stats, tiles, 180, 4)
        card = self._card(self.content, "KAYITLAR", "EN YENİ ÜSTTE", "history", CYAN)
        card.pack(fill="both", expand=True)
        tools = tk.Frame(card, bg=PANEL)
        tools.pack(fill="x", padx=14, pady=(0, 8))
        self.hist_filter = Segmented(tools, [("all", "TÜMÜ")] + [(k, v.upper()) for k, v in CATEGORIES.items()],
                                     lambda _k: self._render_history())
        self.hist_filter.pack(side="left", pady=(0, 6))
        right = tk.Frame(tools, bg=PANEL)
        right.pack(side="right")
        StudioButton(right, "DIŞA AKTAR", self.export_history, "ghost", "export", "sm").pack(side="left", padx=4)
        StudioButton(right, "TEMİZLE", self.clear_history, "danger", "trash", "sm").pack(side="left")
        search = tk.Frame(card, bg=INPUT, highlightthickness=1, highlightbackground=LINE, highlightcolor=CYAN)
        search.pack(fill="x", padx=14, pady=(0, 8))
        icons.icon_label(search, "search", MUTED, 13, INPUT).pack(side="left", padx=(8, 2))
        self.hist_query = tk.StringVar()
        tk.Entry(search, textvariable=self.hist_query, bg=INPUT, fg=FG, insertbackground=CYAN, relief="flat",
                 font=F["small"], bd=0, highlightthickness=0).pack(side="left", fill="x", expand=True, padx=6, ipady=7)
        self.hist_query.trace_add("write", lambda *_a: self._render_history())
        wrap = tk.Frame(card, bg=PANEL)
        wrap.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.hist_tree = ttk.Treeview(wrap, columns=("time", "cat", "level", "title", "detail"), show="headings", height=14)
        for col, text, width, stretch in (("time", "ZAMAN", 90, False), ("cat", "KATEGORİ", 110, False),
                                          ("level", "DURUM", 100, False), ("title", "İŞLEM", 320, True),
                                          ("detail", "AYRINTI", 380, True)):
            self.hist_tree.heading(col, text=text, anchor="w")
            self.hist_tree.column(col, width=width, stretch=stretch, anchor="w")
        for lvl, col in LEVEL_COLORS.items():
            self.hist_tree.tag_configure(lvl, foreground=col)
        ysb = ttk.Scrollbar(wrap, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=ysb.set)
        self.hist_tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        self.hist_empty = tk.Label(card, text="", bg=PANEL, fg=DIM, font=F["small"])
        self._render_history()

    def _render_history(self):
        if not hasattr(self, "hist_tree") or not self.hist_tree.winfo_exists():
            return
        items = self.log.filtered(self.hist_filter.value, self.hist_query.get())
        self.hist_tree.delete(*self.hist_tree.get_children())
        labels = {"success": "BAŞARILI", "info": "BİLGİ", "warning": "UYARI", "error": "HATA"}
        for i, item in enumerate(items):
            self.hist_tree.insert("", "end", iid=str(i), tags=(item.level,),
                                  values=(item.clock, item.category_label, labels[item.level], item.title, item.detail))
        all_items = self.log.items()
        self.hist_stats["total"].configure(text=str(len(all_items)))
        for lvl in ("success", "warning", "error"):
            self.hist_stats[lvl].configure(text=str(sum(1 for i in all_items if i.level == lvl)))
        if not items:
            self.hist_empty.configure(text="Bu filtreye uyan kayıt yok." if all_items else "Henüz kayıt yok.")
            self.hist_empty.pack(pady=(0, 14))
        else:
            self.hist_empty.pack_forget()

    def export_history(self):
        if not len(self.log):
            self.status("Dışa aktarılacak kayıt yok", "warning")
            return
        path = filedialog.asksaveasfilename(title="İşlem geçmişini dışa aktar", defaultextension=".txt",
                                            initialfile="elfcaesar-islem-gecmisi.txt", filetypes=[("Metin", "*.txt")])
        if path:
            try:
                Path(path).write_text(self.log.export_lines(), encoding="utf-8")
                self.notify("success", "system", "İşlem geçmişi dışa aktarıldı")
            except Exception as exc:
                self.notify("error", "system", "Geçmiş kaydedilemedi", str(exc))

    def clear_history(self):
        if len(self.log) and messagebox.askyesno("İşlem geçmişi", "Bu oturumun işlem geçmişi silinsin mi?", parent=self):
            self.log.clear()
            self.unread = 0
            self._update_badge()
            self._render_history()
            self.refresh_dashboard()
            self.status("İşlem geçmişi temizlendi")

    # ------------------------------------------------------------ identity actions (motorlar 6.4 ile aynı)
    def identity_create(self):
        name = simpledialog.askstring("Yeni kripto kimlik", "Görünen ad / takma ad:", parent=self)
        if name is None: return
        path = filedialog.asksaveasfilename(title="Şifreli özel kimliği kaydet", defaultextension=".elfid", initialfile="my-identity.elfid", filetypes=[("ELF Identity", "*.elfid")])
        if not path: return
        password = self._password(confirm=True)
        if password is None: return
        try:
            contact = create_identity(name, password, path)
            self._add_identity_card(contact, "KİMLİĞİN", "Özel anahtar parola korumalı .elfid kasasında. Şimdi açık kişi kartını dışa aktar ve karşı tarafa gönder.")
            self.set_pref("identity_path", str(path))
            self.sec.identity_known = True
            self.notify("success", "identity", "Kimlik oluşturuldu", "X25519 / Ed25519 · özel anahtar şifreli")
        except Exception as exc:
            self.notify("error", "identity", "Kimlik oluşturulamadı", str(exc))

    def identity_export_contact(self):
        src = filedialog.askopenfilename(title="Özel kimlik kasasını seç", filetypes=[("ELF Identity", "*.elfid")])
        if not src: return
        password = self._password()
        if password is None: return
        try:
            identity = load_identity(src, password)
            dst = filedialog.asksaveasfilename(title="Açık kişi kartını kaydet", defaultextension=".elfcontact", initialfile=identity['contact']['name'] + ".elfcontact", filetypes=[("ELF Contact", "*.elfcontact")])
            if not dst: return
            export_contact(identity['contact'], dst)
            self._add_identity_card(identity['contact'], "KİMLİĞİN", "Yalnızca açık anahtarlar dışa aktarıldı. Özel anahtar paylaşılmadı.")
            self.notify("success", "identity", "Açık kişi kartı dışa aktarıldı", "Özel anahtar paylaşılmadı")
        except Exception as exc:
            self.notify("error", "identity", "Kişi kartı dışa aktarılamadı", str(exc))

    def identity_check_contact(self):
        src = filedialog.askopenfilename(title="Doğrulanacak kişi kartını seç", filetypes=[("ELF Contact", "*.elfcontact")])
        if not src: return
        try:
            c = import_contact(src)
            self._add_identity_card(c, "KİŞİ KARTI", "Dosya bütünlüğü geçerli. Kişinin kimliğini doğrulamak için parmak izini ayrı bir kanaldan karşılaştır.")
            self.notify("success", "identity", "Kişi kartı geçerli", "Parmak izini ayrı kanaldan karşılaştır")
        except Exception as exc:
            self.notify("error", "identity", "Kişi kartı geçersiz", str(exc))

    def identity_encrypt_message(self):
        message = self.get(self.sec_msg_in)
        if not message:
            self.notify("warning", "vault", "Şifrelenecek mesaj yok", "GİRDİ alanına mesaj yaz")
            return
        cp = filedialog.askopenfilename(title="Alıcının açık kişi kartını seç", filetypes=[("ELF Contact", "*.elfcontact")])
        if not cp: return
        try: contact = import_contact(cp)
        except Exception as exc: self.notify("error", "identity", "Alıcı kişi kartı okunamadı", str(exc)); return
        sender = None
        if messagebox.askyesno("Gönderen imzası", "Mesajı kendi Ed25519 kimliğinle imzalamak ister misin?\n\nÖnerilir.", parent=self):
            ip = filedialog.askopenfilename(title="Gönderen özel kimlik kasasını seç", filetypes=[("ELF Identity", "*.elfid")])
            if not ip: return
            pw = self._password()
            if pw is None: return
            try: sender = load_identity(ip, pw)
            except Exception as exc: self.notify("error", "identity", "Gönderen kimliği açılamadı", str(exc)); return
        try:
            payload = encrypt_for_contact(message, contact, sender)
            self.put(self.sec_msg_out, payload)
            if sender:
                self.sec.signed_sends += 1
            else:
                self.sec.unsigned_sends += 1
            self.refresh_security()
            self.notify("success", "vault", "Alıcıya özel mesaj paketi üretildi", "X25519" + (" · imzalı" if sender else " · imzasız"))
        except Exception as exc:
            self.notify("error", "vault", "Kişiye mesaj üretilemedi", str(exc))

    def identity_decrypt_message(self):
        payload = self.get(self.sec_msg_in).strip()
        if not payload:
            src = filedialog.askopenfilename(title="Gelen .elfdm mesaj paketini seç", filetypes=[("ELF Direct Message", "*.elfdm"), ("Tüm dosyalar", "*.*")])
            if not src: return
            try: payload = Path(src).read_text(encoding="utf-8")
            except Exception as exc: self.notify("error", "vault", "Mesaj paketi okunamadı", str(exc)); return
        ip = filedialog.askopenfilename(title="Alıcı özel kimlik kasasını seç", filetypes=[("ELF Identity", "*.elfid")])
        if not ip: return
        pw = self._password()
        if pw is None: return
        trusted = None
        if messagebox.askyesno("Göndereni sabitle", "Gönderenin daha önce doğruladığın .elfcontact kartı var mı?\n\nEvet: parmak izini de kontrol et.\nHayır: imza varsa yalnızca kriptografik imza geçerliliğini kontrol et.", parent=self):
            cp = filedialog.askopenfilename(title="Güvendiğin gönderen kişi kartını seç", filetypes=[("ELF Contact", "*.elfcontact")])
            if not cp: return
            try: trusted = import_contact(cp)
            except Exception as exc: self.notify("error", "identity", "Güvenilen kişi kartı okunamadı", str(exc)); return
        try:
            identity = load_identity(ip, pw)
            clear, sender = decrypt_from_contact(payload, identity, trusted)
            self.put(self.sec_msg_out, clear)
            if sender and trusted:
                self.sec.pinned_opens += 1
            elif sender:
                self.sec.unpinned_opens += 1
            self.refresh_security()
            detail = "İmza doğrulandı" if sender else "İmzasız mesaj"
            if sender and not trusted: detail += " · gönderen parmak izi ayrıca doğrulanmalı"
            if sender:
                role = "GÜVENİLEN" if trusted else "GÖNDEREN"
                note = ("İmza ve sabitlenmiş parmak izi eşleşti." if trusted else
                        "İmza kriptografik olarak geçerli. Bu parmak izini ayrı bir kanaldan karşılaştır.")
                self._add_identity_card(sender, role, note)
            self.notify("success" if sender else "warning", "vault", "Mesaj kimliğinle açıldı", detail)
        except Exception as exc:
            self.notify("error", "vault", "Mesaj çözülemedi / imza geçersiz", str(exc))

    # ------------------------------------------------------------ vault actions (motorlar 6.4 ile aynı)
    def _password(self, confirm=False, purpose=None):
        purpose = purpose or ("Yeni kasa için parola cümlesi belirle. Seviye canlı gösterilir; parola hiçbir yere kaydedilmez."
                              if confirm else "Kasayı açmak için parolanı gir.")
        dlg = PasswordDialog(self, "Kasa parolası", purpose, confirm=confirm,
                             generator=lambda: generate_passphrase(5), icon=self.img("mark_48"))
        self.shield(dlg)
        value = dlg.show_modal()
        if value is not None and confirm:
            self.sec.last_password_level = dlg.level
            self.refresh_security()
        return value

    def show_passphrase(self):
        value = generate_passphrase(5)
        self.guarded_copy(value)
        level = password_strength(value)["name"]
        extra = (f"\n\nPano koruması: {self.sec.clipboard_seconds} sn sonra pano temizlenecek." if self.sec.clipboard_guard else "")
        messagebox.showinfo("Yerel parola üretici", "Rastgele parola üretildi ve panoya kopyalandı:\n\n" + value +
                            f"\n\nSeviye: {level}. Bunu parola yöneticine kaydet." + extra, parent=self)
        self.notify("success", "vault", "Parola üretildi ve panoya kopyalandı", toast=False)

    def secure_message_encrypt(self):
        raw = self.get(self.sec_msg_in)
        if not raw:
            self.notify("warning", "vault", "Şifrelenecek mesaj yok", "GİRDİ alanına mesaj yaz")
            return
        password = self._password(confirm=True)
        if password is None: return
        try:
            self.put(self.sec_msg_out, encrypt_message(raw, password))
            self.notify("success", "vault", "Mesaj şifrelendi", "AES-256-GCM paketi hazır")
        except Exception as exc: self.notify("error", "vault", "Şifreleme başarısız", str(exc))

    def secure_message_decrypt(self):
        payload = self.get(self.sec_msg_in).strip()
        if not payload:
            self.notify("warning", "vault", "Çözülecek paket yok", "Paketi GİRDİ alanına yapıştır veya aç")
            return
        password = self._password()
        if password is None: return
        try:
            self.put(self.sec_msg_out, decrypt_message(payload, password))
            self.notify("success", "vault", "Mesaj doğrulandı ve çözüldü")
        except Exception as exc: self.notify("error", "vault", "Çözme / doğrulama başarısız", str(exc))

    def secure_message_open(self):
        path = filedialog.askopenfilename(title="Şifreli mesaj paketini aç", filetypes=[("ELF mesaj paketleri", "*.elmsg *.elfdm"), ("Parolalı mesaj", "*.elmsg"), ("Kişiye özel mesaj", "*.elfdm"), ("Tüm dosyalar", "*.*")])
        if path:
            try:
                self.put(self.sec_msg_in, Path(path).read_text(encoding="utf-8"))
                self.notify("info", "vault", "Şifreli mesaj paketi yüklendi", toast=False)
            except Exception as exc: self.notify("error", "vault", "Paket açılamadı", str(exc))

    def secure_message_save(self):
        payload = self.get(self.sec_msg_out).strip()
        if not payload:
            self.notify("warning", "vault", "Kaydedilecek paket yok")
            return
        is_direct = payload.startswith("ELFDM1\n")
        ext = ".elfdm" if is_direct else ".elmsg"
        path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=[("ELF mesaj paketleri", "*.elmsg *.elfdm"), ("Tüm dosyalar", "*.*")])
        if path:
            try:
                Path(path).write_text(payload, encoding="utf-8")
                self.notify("success", "vault", "Şifreli mesaj paketi kaydedildi")
            except Exception as exc: self.notify("error", "vault", "Paket kaydedilemedi", str(exc))

    def secure_file_encrypt(self, src=None):
        src = src or filedialog.askopenfilename(title="Şifrelenecek belge veya görüntüyü seç")
        if not src: return
        dst = filedialog.asksaveasfilename(title="Şifreli kasayı kaydet", defaultextension=".elfvault", initialfile=Path(src).name + ".elfvault")
        if not dst: return
        password = self._password(confirm=True)
        if password is None: return
        try:
            encrypt_file(src, dst, password)
            self.notify("success", "file", "Dosya kasaya alındı", "AES-256-GCM")
        except Exception as exc: self.notify("error", "file", "Dosya şifrelenemedi", str(exc))

    def secure_file_decrypt(self, src=None):
        src = src or filedialog.askopenfilename(title="ELF Vault dosyasını seç", filetypes=[("ELF Vault", "*.elfvault"), ("Tüm dosyalar", "*.*")])
        if not src: return
        password = self._password()
        if password is None: return
        try:
            from elfcaesar.secure import open_bytes
            _, header = open_bytes(Path(src).read_bytes(), password)
            suggested = header.get("filename") or (Path(src).stem + ".restored")
            dst = filedialog.asksaveasfilename(title="Çözülen dosyayı kaydet", initialfile=Path(suggested).name)
            if not dst: return
            decrypt_file(src, dst, password)
            self.notify("success", "file", "Dosya doğrulandı ve geri yüklendi")
        except Exception as exc: self.notify("error", "file", "Dosya çözülemedi", str(exc))

    # ------------------------------------------------------------ codec actions
    def get(self, widget): return widget.get("1.0", "end-1c")

    def put(self, widget, value):
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.edit_separator()

    def do_encode(self):
        source = self.get(self.enc_in)
        if not source:
            self.notify("warning", "codec", "Kodlanacak metin yok", "SOURCE TEXT alanına metin gir")
            return
        if self.sec.sensitive_warning:
            findings = scan_sensitive(source)
            if findings:
                summary = ", ".join(f"{f['label']} ({f['count']})" for f in findings)
                answer = messagebox.askyesnocancel(
                    "Hassas veri uyarısı",
                    f"Bu metinde hassas veri olabilir:\n{summary}\n\nELFC2 şifreleme değildir; herkes 29 kaydırmayı deneyerek çözebilir.\n\n"
                    "Evet: Metni Güvenli Kasa'ya taşı (önerilen)\nHayır: Yine de ELFC2 ile kodla\nİptal: Vazgeç", parent=self)
                if answer is None:
                    return
                if answer:
                    self.show_page("vault")
                    self.put(self.sec_msg_in, source)
                    self.notify("info", "vault", "Metin Güvenli Kasa'ya taşındı", "PAROLAYLA ŞİFRELE ile koru")
                    return
                self.sec.sensitive_encodes += 1
                self.refresh_security()
        try:
            result = encode(source, self.shift.get())
            self.put(self.enc_out, result)
            self.notify("success", "codec", "Kodlama tamamlandı", f"{VERSION} · kaydırma {self.shift.get():02d}")
        except Exception as exc: self.notify("error", "codec", "Kodlama hatası", str(exc))

    def do_decode(self):
        payload = self.get(self.dec_in).strip()
        if not payload:
            self.notify("warning", "codec", "Çözülecek paket yok", "ENCODED INPUT alanına ELFC2 verisi gir")
            return
        try:
            result = decode(payload, self.shift.get())
            self.put(self.dec_out, result)
            self.notify("success", "codec", "Çözme tamamlandı", f"Kaydırma {self.shift.get():02d}")
        except Exception as exc: self.notify("error", "codec", "Çözme hatası", str(exc))

    def do_brute(self):
        payload = self.get(self.brute_in).strip()
        if not payload:
            self.notify("warning", "analysis", "Analiz edilecek paket yok", "INPUT PAYLOAD alanına ELFC2 verisi gir")
            return
        try:
            self.analysis_all_results = rank(brute_force(payload))
            self.analysis_payload = payload
            self.analysis_filter.set("")
            self._render_analysis()
            best = best_shift(self.analysis_all_results)
            self.notify("success", "analysis", "29 kaydırma analiz edildi", f"En olası kaydırma {best:02d}")
            if best is not None:
                self._select_shift(best)
        except Exception as exc: self.notify("error", "analysis", "Analiz hatası", str(exc))

    def _transfer_to_decode(self, shift):
        value = next((t for s, t, _sc in self.analysis_all_results if s == shift), "")
        payload = getattr(self, "analysis_payload", "")
        self.shift.set(int(shift))
        self.show_page("decode")
        if payload:
            self.put(self.dec_in, payload)
        self.put(self.dec_out, value)
        self.notify("info", "analysis", "Aday çözme ekranına aktarıldı", f"Kaydırma {int(shift):02d}", toast=False)

    def use_brute(self):
        selected = self.tree.selection()
        if not selected:
            self.notify("warning", "analysis", "Önce bir aday seç", "Tablodan veya puan haritasından")
            return
        self._transfer_to_decode(int(self.tree.item(selected[0], "values")[0]))

    def use_best(self):
        best = best_shift(self.analysis_all_results)
        if best is None:
            self.notify("warning", "analysis", "Önce analiz çalıştır")
            return
        self._transfer_to_decode(best)

    def open_file(self, widget):
        path = filedialog.askopenfilename(filetypes=[("Metin / Elf dosyası", "*.txt *.elf *.md *.json"), ("Tüm dosyalar", "*.*")])
        if path:
            self._load_text_file(widget, path)

    def save_file(self, widget, ext):
        if not self.get(widget):
            self.notify("warning", "file", "Kaydedilecek içerik yok")
            return
        path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=[("Uygun dosya", f"*{ext}"), ("Tüm dosyalar", "*.*")])
        if path:
            try:
                Path(path).write_text(self.get(widget), encoding="utf-8")
                self.status("Dosya kaydedildi · " + Path(path).name, "success")
                self.notify("success", "file", "Dosya kaydedildi", ext.upper().lstrip("."))
            except Exception as exc: self.notify("error", "file", "Kaydetme hatası", str(exc))

    def copy(self, widget):
        value = self.get(widget)
        if widget.tag_ranges("sel"):
            value = widget.get("sel.first", "sel.last")
        if widget in self._sensitive_widgets():
            self.guarded_copy(value)
            return
        self.clipboard_clear()
        self.clipboard_append(value)
        self.status("Panoya kopyalandı" + (" · seçim" if widget.tag_ranges("sel") else ""), "success")

    def save_json(self):
        if not self.get(self.enc_in):
            self.notify("warning", "codec", "Dışa aktarılacak metin yok")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            try:
                Path(path).write_text(export_json(self.get(self.enc_in), self.shift.get()), encoding="utf-8")
                self.notify("success", "codec", "JSON dışa aktarıldı")
            except Exception as exc: self.notify("error", "codec", "JSON hatası", str(exc))


def parse_args(argv):
    import argparse
    p = argparse.ArgumentParser(description="ElfCaesar Studio")
    p.add_argument("--action", choices=["encrypt-file", "decrypt-file", "add-contact", "bridge", "background", "open-message",
                                          "lock-folder", "sign-file", "verify-sig"])
    p.add_argument("--version", action="version", version=f"ElfCaesar Studio {APP_FULL_VERSION}")
    p.add_argument("--selftest", action="store_true", help="Sistem denetimi: sonucu %%LOCALAPPDATA%%\\ElfCaesar\\selftest.json dosyasına yazar")
    p.add_argument("path", nargs="?")
    a = p.parse_args(argv)
    if a.selftest:
        return ("selftest", None)
    return (a.action, a.path) if a.action else None


def selftest() -> dict:
    """Arayüz açmadan temel bileşenleri dener (destek ve kurulum doğrulaması için). İçerik kaydetmez."""
    import json
    from studio_ui import leaks
    from elfcaesar.secure import encrypt_message as _enc, decrypt_message as _dec
    result = {"version": APP_FULL_VERSION, "frozen": runtime.is_frozen(), "checks": {}}
    checks = result["checks"]
    try:
        checks["leak_list_entries"] = leaks.size()
        checks["leak_detects_turkish"] = bool(leaks.is_blocked("Galatasaray1905"))
    except Exception as exc:
        checks["leak_error"] = repr(exc)
    try:
        pw = "Selftest-Kalkan-2026!"
        checks["vault_roundtrip"] = _dec(_enc("ElfCaesar", pw), pw) == "ElfCaesar"
    except Exception as exc:
        checks["vault_error"] = repr(exc)
    checks["assets"] = all((ASSETS / n).exists() for n in ("logo_256.png", "dante_sig_300.png", "elfcaesar.ico"))
    try:
        from studio_ui import paperbackup as _pb
        checks["paper_backup_qr"] = "<svg" in _pb.qr_svg(_pb.qr_payload(b"ELFVAULT1\nselftest")) and \
            _pb.decode_text(_pb.qr_payload(b"selftest")) == b"selftest"
    except Exception as exc:
        checks["paper_backup_error"] = repr(exc)
    try:
        import tempfile
        from studio_ui import kvkk as _kv
        with tempfile.TemporaryDirectory() as d:
            Path(d, "ornek.txt").write_text("TC 10000000146", encoding="utf-8")
            checks["kvkk_scan"] = len(_kv.scan([d]).findings) == 1
    except Exception as exc:
        checks["kvkk_error"] = repr(exc)
    try:
        import tempfile
        from studio_ui import folderlock as _fl, keyfile as _kf, masking as _mk, signing as _sg
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "klasor"); src.mkdir(); Path(src, "a.txt").write_text("TC 10000000146", encoding="utf-8")
            k = _kf.create(Path(d, "k.elfkey")); sec = _kf.combine("Selftest-Kalkan-2026!", k)
            _fl.lock(src, Path(d, "v.elfvault"), sec); Path(d, "o").mkdir()
            out = _fl.unlock(Path(d, "v.elfvault"), Path(d, "o"), sec)
            checks["folder_vault"] = Path(out, "a.txt").read_text(encoding="utf-8") == "TC 10000000146"
            checks["masking"] = "10000000146" not in _mk.mask_text("TC 10000000146")[0]
        if runtime.is_frozen():
            import sys as _sys
            checks["integrity"] = _sg.verify_install(Path(_sys.executable).parent)["status"]
            _root = Path(_sys.executable).parent
            checks["browser_host"] = (_root / "ElfCaesarNativeHost.exe").exists() and (_root / "com.dante.elfcaesar.json").exists() \
                and (_root / "com.dante.elfcaesar.firefox.json").exists() \
                and (_root / "TarayiciEklentisi" / "manifest.json").exists()
    except Exception as exc:
        checks["toolbox_error"] = repr(exc)
    try:
        import tempfile
        from studio_ui.pwvault import PasswordVault as _PV, Entry as _En
        from studio_ui import shamir as _sh, pwaudit as _pa
        with tempfile.TemporaryDirectory() as d:
            v = _PV(Path(d, "p.elfvault")); v.create("Selftest-Kalkan-2026!"); v.add(_En("Gmail", "a@gmail.com", "x1"))
            v.add(_En("Site", "a@gmail.com", "x1")); v.save(); v.lock(); v.unlock("Selftest-Kalkan-2026!")
            checks["password_vault"] = len(v.entries) == 2 and len(_pa.domino(v.entries)) >= 1 and \
                _sh.combine_text(_sh.split_text(b"elf", 2, 3)[1:]) == b"elf"
    except Exception as exc:
        checks["password_vault_error"] = repr(exc)
    from studio_ui import badges as _bd
    checks["badges"] = all((ASSETS / "badges" / f"{b[0]}_128.png").exists() for b in _bd.BADGES)
    checks["guide"] = bool(guides.CHAPTERS) and (runtime.resource_dir() / "docs" / "kilavuz" / "index.html").exists()
    result["ok"] = bool(checks.get("password_vault") and checks.get("badges") and checks.get("guide") and checks.get("folder_vault") and checks.get("masking") and checks.get("integrity", "ok") == "ok" and checks.get("leak_list_entries", 0) > 10000 and checks.get("leak_detects_turkish")
                        and checks.get("vault_roundtrip") and checks["assets"] and checks.get("paper_backup_qr")
                        and checks.get("kvkk_scan"))
    out = runtime.local_data_dir() / "selftest.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main(argv=None):
    import sys
    argv = sys.argv[1:] if argv is None else argv
    start = parse_args(argv)
    if start and start[0] == "selftest":
        return 0 if selftest()["ok"] else 1
    runtime.windows_setup()
    if runtime.forward_to_running(*(start or (None, None))):
        return 0  # açık pencere komutu devraldı (ör. Gezgin sağ tık menüsü)
    sys.excepthook = lambda t, e, tb: runtime.write_crash(t, e, tb)
    server = runtime.InstanceServer()
    if not server.start():
        server = None
    app = Studio(start_action=start, instance_server=server)
    try:
        app.mainloop()
    finally:
        if server is not None:
            server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
