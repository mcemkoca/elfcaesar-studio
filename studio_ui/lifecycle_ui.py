"""Parola Yaşam Döngüsü arayüzü (6.11.0): Değişim Planı · Süreç Takibi, Parola Üretici ve Sızıntı Merkezi.

PasswordsMixin bu sınıftan türer; şifreleme motorlarına dokunmaz. Bütün durum (bekleyen parolalar, zaman çizelgesi,
puan geçmişi, üretici geçmişi) parola kasasının içinde şifreli tutulur.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from . import breaches, cracktime, lifecycle, pwgen
from .theme import F, BG, PANEL, INPUT, LINE, FG, FG_2, MUTED, DIM, AMBER, CYAN, GREEN, RED, ORANGE, VIOLET, mix
from .widgets import StudioButton, Segmented
from .dialog_base import _Dialog

STATE_COLORS = {"pending": CYAN, "urgent": RED, "recommended": AMBER, "snoozed": DIM, "ok": GREEN}
GEN_DEFAULTS = {"mode": "random", "length": 20, "groups": 4, "pin": 6, "lower": True, "upper": True, "digits": True,
                "symbols": True, "avoid": True}


def _fmt_day(ts: float) -> str:
    return time.strftime("%d.%m.%Y", time.localtime(ts)) if ts else "—"


def crack_text(bits: float) -> str:
    """Üretilen parolanın, sızan hızlı bir özetten (1 GPU, saniyede 10^11 tahmin) ortalama kırılma süresi."""
    secs = 2 ** max(0.0, bits - 1) / 1e11
    return cracktime.format_duration(secs)


class LifecycleMixin:
    # ------------------------------------------------------------ ortak
    @property
    def breach_catalog(self) -> breaches.Catalog:
        if "_breach_cat" not in self.__dict__:
            self._breach_cat = breaches.Catalog.load()
        return self._breach_cat

    def _pw_plan_compute(self):
        self.pw_plan = lifecycle.plan(self.pv.entries, self.breach_catalog)
        self.pw_plan_by_id = {i["entry"].id: i for i in self.pw_plan["items"]}
        if not self.pv.decoy and self.pv.entries and lifecycle.record_score(self.pv.meta, self.pw_plan["score"]):
            try:
                self.pv.save()
            except Exception:
                pass
        return self.pw_plan

    def gen_policy(self, domain: str = "") -> pwgen.Policy:
        g = dict(GEN_DEFAULTS, **(self.prefs.get("pwgen") or {}))
        p = pwgen.Policy(mode=g["mode"], length=g["pin"] if g["mode"] == "pin" else g["length"], groups=g["groups"],
                         lower=g["lower"], upper=g["upper"], digits=g["digits"], symbols=g["symbols"],
                         avoid_ambiguous=g["avoid"])
        rule = ((self.pv.meta.get("site_rules") or {}).get(domain) if self.pv.is_open and domain else None) or {}
        if rule:
            p = pwgen.policy_for_site(p, maxlength=rule.get("max", 0), passwordrules=rule.get("rules", ""))
            if rule.get("mode"):
                p.mode = rule["mode"]
        return p.clamp()

    def remember_site_rule(self, domain: str, text: str):
        if not domain or not self.pv.is_open:
            return
        rules = dict(self.pv.meta.get("site_rules") or {})
        text = (text or "").strip()
        if not text:
            rules.pop(domain, None)
        elif text.isdigit():
            rules[domain] = {"max": int(text)}
        else:
            rules[domain] = {"rules": text[:300]}
        self.pv.meta["site_rules"] = rules

    def generate_for(self, domain: str = "", via: str = "uygulama", policy: pwgen.Policy | None = None) -> str:
        pw = pwgen.generate(policy or self.gen_policy(domain))
        if self.pv.is_open:
            lifecycle.add_generated(self.pv.meta, pw, domain, via)
        return pw

    # ------------------------------------------------------------ 02 değişim planı
    def _pw_plan_card(self, card):
        plan, st = self.pw_plan, lifecycle.stats(self.pv.meta)
        c = plan["counts"]
        head = tk.Frame(card, bg=PANEL)
        head.pack(fill="x", padx=16, pady=(0, 8))
        boxes = []
        for label, value, col in (("ACİL", c["urgent"], RED), ("ÖNERİLEN", c["recommended"], AMBER),
                                  ("SÜRÜYOR", c["pending"], CYAN), ("ERTELENEN", c["snoozed"], MUTED),
                                  ("SON 30 GÜN YENİLENEN", st["changed_30d"], GREEN)):
            b = tk.Frame(head, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            tk.Label(b, text=label, bg=INPUT, fg=DIM, font=F["label"], anchor="w").pack(fill="x", padx=12, pady=(8, 0))
            tk.Label(b, text=str(value), bg=INPUT, fg=col if value else FG_2, font=F["metric"], anchor="w").pack(fill="x", padx=12, pady=(0, 8))
            boxes.append(b)
        spark = tk.Frame(head, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
        tk.Label(spark, text="KASA SAĞLIĞI GEÇMİŞİ", bg=INPUT, fg=DIM, font=F["label"], anchor="w").pack(fill="x", padx=12, pady=(8, 0))
        cv = tk.Canvas(spark, bg=INPUT, height=38, highlightthickness=0)
        cv.pack(fill="x", padx=12, pady=(2, 8))
        cv.bind("<Configure>", lambda _e, cv=cv, s=st: self._pw_spark(cv, s))
        boxes.append(spark)
        self._auto_grid(head, boxes, 150, 6)
        todo = [i for i in plan["items"] if i["state"] != "ok"]
        if not todo:
            tk.Label(card, text="✓ Bütün parolalar güvende: sızıntı, site ihlali, tekrar veya zayıf parola yok.", bg=PANEL, fg=GREEN,
                     font=F["body_b"], anchor="w").pack(fill="x", padx=16, pady=(4, 16))
            return
        self._wrap(tk.Label(card, text="En önemlisi en üstte. DEĞİŞTİRMEYE BAŞLA yeni parolayı hazırlar ve kasaya “bekleyen” olarak "
                            "koyar; sitedeki eski parola kaybolmaz. Sitede değiştirdikten sonra SİTEDE DEĞİŞTİRDİM'e bas.",
                            bg=PANEL, fg=MUTED, font=F["tiny"], justify="left"), 40).pack(fill="x", padx=16, pady=(0, 6))
        wrap = tk.Frame(card, bg=PANEL)
        wrap.pack(fill="x", padx=16)
        tree = ttk.Treeview(wrap, columns=("state", "title", "reason", "detail"), show="headings", height=min(8, max(3, len(todo))))
        for col, text, w, s in (("state", "DURUM", 120, False), ("title", "KAYIT", 210, True), ("reason", "NEDEN", 280, True),
                                ("detail", "AYRINTI", 260, True)):
            tree.heading(col, text=text, anchor="w")
            tree.column(col, width=w, stretch=s, anchor="w")
        for k, col in STATE_COLORS.items():
            tree.tag_configure(k, foreground=col)
        for i in todo:
            e = i["entry"]
            r0 = i["reasons"][0] if i["reasons"] else {"label": "", "detail": ""}
            more = f"  +{len(i['reasons']) - 1}" if len(i["reasons"]) > 1 else ""
            detail = r0.get("detail", "")
            if i["state"] == "pending":
                detail = "Yeni parola hazır · " + _fmt_day(e.pending.get("since", 0))
                if not i["reasons"]:
                    r0 = {"label": e.pending.get("reason") or "Elle başlatıldı"}
            elif i["state"] == "snoozed":
                detail = "Ertelendi · " + _fmt_day(e.snooze_until)
            tree.insert("", "end", iid=e.id, values=(lifecycle.STATES[i["state"]], e.title, r0["label"] + more, detail), tags=(i["state"],))
        ysb = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        wrap.grid_columnconfigure(0, weight=1)
        tree.bind("<Double-1>", lambda _e: self.pw_change_start())
        self.pw_plan_tree = tree
        kids = tree.get_children()
        if kids:
            tree.selection_set(kids[0])
        bar = tk.Frame(card, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(8, 14))
        self._flow(bar, [StudioButton(bar, "DEĞİŞTİRMEYE BAŞLA", self.pw_change_start, "primary", "key", "sm"),
                         StudioButton(bar, "SİTEDE DEĞİŞTİRDİM", self.pw_change_confirm, "accent", "check", "sm"),
                         StudioButton(bar, "VAZGEÇ", self.pw_change_cancel, "ghost", "close", "sm"),
                         StudioButton(bar, "7 GÜN ERTELE", self.pw_snooze, "ghost", "bell", "sm"),
                         StudioButton(bar, "İHLAL BENİ ETKİLEMİYOR", self.pw_ack_breach, "ghost", "shield", "sm",
                                      tooltip="Örneğin o sitede hesabını ihlalden sonra açtıysan"),
                         StudioButton(bar, "ZAMAN ÇİZELGESİ", self.pw_timeline, "secondary", "history", "sm")])

    def _pw_spark(self, cv, st):
        cv.delete("all")
        s = st["series"]
        w, h = max(cv.winfo_width(), 60), 38
        if len(s) < 2:
            cv.create_text(4, h / 2, text=f"{s[-1]}/100 · geçmiş birikiyor" if s else "—", anchor="w", fill=MUTED, font=F["tiny"])
            return
        pts = []
        for k, v in enumerate(s):
            pts += [4 + k * (w - 40) / (len(s) - 1), h - 4 - (h - 8) * v / 100]
        col = GREEN if s[-1] >= 80 else (AMBER if s[-1] >= 50 else RED)
        cv.create_line(*pts, fill=col, width=2, smooth=True)
        cv.create_text(w - 2, pts[-1], text=str(s[-1]), anchor="e", fill=col, font=F["mono_b"])

    def _pw_plan_selected(self):
        tree = getattr(self, "pw_plan_tree", None)
        sel = tree.selection() if tree is not None and tree.winfo_exists() else ()
        e = self.pv.get(sel[0]) if sel else self._pw_selected()
        if e is None:
            self.notify("warning", "vault", "Önce bir kayıt seç")
        return e

    def pw_change_start(self, entry=None):
        e = entry or self._pw_plan_selected()
        if e:
            ChangeDialog(self, e)

    def pw_change_confirm(self, entry=None):
        e = entry or self._pw_plan_selected()
        if not e:
            return
        if not e.pending:
            self.notify("info", "vault", "Bu kayıtta bekleyen yeni parola yok", "Önce DEĞİŞTİRMEYE BAŞLA")
            return
        lifecycle.confirm_change(self.pv.meta, e)
        if self._pw_save():
            self.notify("success", "vault", "Parola yenilendi", f"{e.title} · eski parola geçmişte saklanıyor")
            self._pw_rebuild()

    def pw_change_cancel(self, entry=None):
        e = entry or self._pw_plan_selected()
        if e and e.pending and messagebox.askyesno("Değişimden vazgeç", f"“{e.title}” için hazırlanan yeni parola silinsin mi?\n"
                                                   "Sitede zaten değiştirdiysen VAZGEÇME, SİTEDE DEĞİŞTİRDİM'e bas.", parent=self, default="no"):
            lifecycle.cancel_change(e)
            self._pw_save()
            self._pw_rebuild()

    def pw_snooze(self):
        e = self._pw_plan_selected()
        if not e:
            return
        item = self.pw_plan_by_id.get(e.id)
        if item and item["state"] == "urgent":
            self.notify("warning", "vault", "Acil durumlar ertelenemez", "Sızmış parola veya site ihlali hemen değiştirilmeli")
            return
        lifecycle.snooze(e, 7)
        self._pw_save()
        self._pw_rebuild()

    def pw_ack_breach(self):
        e = self._pw_plan_selected()
        if not e:
            return
        item = self.pw_plan_by_id.get(e.id) or {"reasons": []}
        names = [r["breach"] for r in item["reasons"] if r.get("breach")]
        if not names:
            self.notify("info", "vault", "Bu kayıtta açık site ihlali yok")
            return
        if messagebox.askyesno("İhlal beni etkilemiyor", f"“{e.title}” için {names[0]} ihlali işaretlensin mi?\n\nYalnızca hesabını ihlalden SONRA "
                               "açtıysan veya o tarihten sonra parolanı başka bir yoldan değiştirdiysen işaretle.", parent=self, default="no"):
            lifecycle.ack_breach(e, names[0])
            lifecycle.log_event(self.pv.meta, "ack", e, f"{names[0]} ihlali etkilemiyor olarak işaretlendi")
            self._pw_save()
            self._pw_rebuild()

    def pw_timeline(self):
        e = self._pw_plan_selected()
        if e:
            TimelineDialog(self, e)

    # ------------------------------------------------------------ 03 parola üretici
    def _pw_gen_card(self, card):
        g = dict(GEN_DEFAULTS, **(self.prefs.get("pwgen") or {}))
        self.gen_state = g
        top = tk.Frame(card, bg=PANEL)
        top.pack(fill="x", padx=16, pady=(0, 8))
        self.gen_mode = Segmented(top, [("random", "RASTGELE"), ("syllable", "HECELİ"), ("pin", "PIN")],
                                  command=lambda _k: self._gen_changed(), value=g["mode"])
        self.gen_mode.pack(side="left")
        out = tk.Frame(card, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
        out.pack(fill="x", padx=16)
        self.gen_out = tk.Label(out, text="", bg=INPUT, fg=FG, font=("Consolas", 15, "bold"), anchor="w", padx=12, pady=10)
        self.gen_out.pack(fill="x")
        self.gen_meter = tk.Canvas(card, height=6, bg=PANEL, highlightthickness=0)
        self.gen_meter.pack(fill="x", padx=16, pady=(6, 0))
        self.gen_info = tk.Label(card, text="", bg=PANEL, fg=MUTED, font=F["tiny"], anchor="w", justify="left")
        self.gen_info.pack(fill="x", padx=16, pady=(4, 6))
        self.gen_info.bind("<Configure>", lambda e: e.widget.configure(wraplength=max(200, e.width - 4)))
        ctl = tk.Frame(card, bg=PANEL)
        ctl.pack(fill="x", padx=16)
        tk.Label(ctl, text="UZUNLUK", bg=PANEL, fg=DIM, font=F["label"]).pack(side="left")
        self.gen_len = tk.IntVar(value=g["length"])
        self.gen_range = (8, 64)  # _gen_changed kayıtlı türe göre ayarlar
        StudioButton(ctl, "−", lambda: self._gen_step(-1), "ghost", None, "sm").pack(side="left", padx=(8, 2))
        self.gen_len_lab = tk.Label(ctl, text=str(g["length"]), bg=INPUT, fg=AMBER, font=F["mono_b"], width=4, pady=4)
        self.gen_len_lab.pack(side="left")
        StudioButton(ctl, "+", lambda: self._gen_step(1), "ghost", None, "sm").pack(side="left", padx=(2, 8))
        self.gen_len_hint = tk.Label(ctl, text="", bg=PANEL, fg=DIM, font=F["tiny"])
        self.gen_len_hint.pack(side="left")
        for w in (self.gen_len_lab, ctl):
            w.bind("<MouseWheel>", lambda e: self._gen_step(1 if e.delta > 0 else -1))
        boxes = tk.Frame(card, bg=PANEL)
        boxes.pack(fill="x", padx=16, pady=(2, 0))
        self.gen_vars = {}
        for key, label in (("lower", "a-z"), ("upper", "A-Z"), ("digits", "0-9"), ("symbols", "!#$%"), ("avoid", "Karışan harf yok (l 1 O 0)")):
            v = tk.BooleanVar(value=g[key])
            tk.Checkbutton(boxes, text=label, variable=v, command=self._gen_changed, bg=PANEL, fg=FG_2, selectcolor=INPUT,
                           activebackground=PANEL, activeforeground=FG, font=F["small"]).pack(side="left", padx=(0, 8))
            self.gen_vars[key] = v
        rr = tk.Frame(card, bg=PANEL)
        rr.pack(fill="x", padx=16, pady=(6, 0))
        tk.Label(rr, text="SİTE KURALI", bg=PANEL, fg=DIM, font=F["label"]).pack(side="left")
        self.gen_rule = tk.StringVar()
        ent = tk.Entry(rr, textvariable=self.gen_rule, bg=INPUT, fg=FG, insertbackground=FG, relief="flat", font=F["small"],
                       highlightthickness=1, highlightbackground=LINE, highlightcolor=VIOLET)
        ent.pack(side="left", fill="x", expand=True, padx=8, ipady=4)
        ent.bind("<KeyRelease>", lambda _e: self._gen_changed())
        tk.Label(card, text="İsteğe bağlı: “16” (en fazla 16 karakter) veya sitenin kuralı, ör. "
                 "“maxlength: 12; required: lower, upper, digit; allowed: [-_!]”", bg=PANEL, fg=DIM, font=F["tiny"],
                 anchor="w", justify="left", wraplength=520).pack(fill="x", padx=16, pady=(2, 0))
        bar = tk.Frame(card, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(10, 14))
        self._flow(bar, [StudioButton(bar, "YENİ ÜRET", self._gen_new, "primary", "spark", "sm"),
                         StudioButton(bar, "KOPYALA", self._gen_copy, "secondary", "copy", "sm"),
                         StudioButton(bar, "YENİ KAYITTA KULLAN", self._gen_use, "accent", "key", "sm"),
                         StudioButton(bar, "SON ÜRETİLENLER", lambda: GenHistoryDialog(self), "ghost", "history", "sm")])
        self._gen_changed()

    def _gen_policy_from_ui(self) -> pwgen.Policy:
        mode = self.gen_mode.value
        v = {k: x.get() for k, x in self.gen_vars.items()}
        n = int(self.gen_len.get())
        p = pwgen.Policy(mode=mode, length=n, groups=max(3, min(8, n)), lower=v["lower"], upper=v["upper"],
                         digits=v["digits"], symbols=v["symbols"], avoid_ambiguous=v["avoid"])
        rule = self.gen_rule.get().strip()
        if rule:
            p = pwgen.policy_for_site(p, maxlength=int(rule) if rule.isdigit() else 0,
                                      passwordrules="" if rule.isdigit() else rule)
        return p.clamp()

    def _gen_step(self, d):
        lo, hi = self.gen_range
        step = 4 if self.gen_mode.value == "random" and abs(d) == 1 and self.gen_len.get() >= 24 else 1
        self.gen_len.set(max(lo, min(hi, self.gen_len.get() + d * step)))
        self._gen_changed()

    def _gen_changed(self):
        mode = self.gen_mode.value
        rng = {"random": (8, 64), "syllable": (3, 8), "pin": (4, 12)}[mode]
        if rng != self.gen_range:
            self.gen_range = rng
            cur = self.gen_state["groups"] if mode == "syllable" else self.gen_state["pin"] if mode == "pin" else self.gen_state["length"]
            self.gen_len.set(max(rng[0], min(rng[1], cur)))
        self.gen_len_lab.configure(text=str(self.gen_len.get()))
        self.gen_len_hint.configure(text={"random": "karakter (8–64)", "syllable": "hece grubu (3–8)", "pin": "hane (4–12)"}[mode])
        n = int(self.gen_len.get())
        g = self.gen_state
        g["mode"] = mode
        g["groups" if mode == "syllable" else "pin" if mode == "pin" else "length"] = n
        for k, x in self.gen_vars.items():
            g[k] = x.get()
        if getattr(self, "_gen_save_job", None):
            self.after_cancel(self._gen_save_job)
        self._gen_save_job = self.after(800, lambda: self.set_pref("pwgen", dict(self.gen_state)))
        self._gen_new(record=False)

    def _gen_new(self, record=True):
        p = self._gen_policy_from_ui()
        pw = pwgen.generate(p)
        self.gen_current = pw
        self.gen_out.configure(text=pw)
        bits = pwgen.entropy_bits(p)
        frac = min(1.0, bits / 128)
        col = RED if bits < 40 else ORANGE if bits < 60 else AMBER if bits < 80 else GREEN
        cv = self.gen_meter
        cv.delete("all")
        w = max(cv.winfo_width(), 300)
        cv.create_rectangle(0, 0, w, 6, fill=INPUT, width=0)
        cv.create_rectangle(0, 0, w * frac, 6, fill=col, width=0)
        self.gen_info.configure(text=f"{pwgen.describe(p)} · {bits:.0f} bit (üretim yönteminden tam hesap) · sızan hızlı özetten "
                                f"1 GPU ile ortalama kırılma: {crack_text(bits)} · sızıntı listesinde yok ✓", fg=col if bits < 60 else MUTED)
        if record and self.pv.is_open:
            lifecycle.add_generated(self.pv.meta, pw, "", "üretici")
            self._pw_save()

    def _gen_copy(self):
        pw = getattr(self, "gen_current", "")
        if pw:
            if self.pv.is_open:
                lifecycle.add_generated(self.pv.meta, pw, "", "üretici")
                self._pw_save()
            self.guarded_copy(pw)
            self.notify("success", "vault", "Üretilen parola kopyalandı", "Son üretilenler listesinde de saklanıyor", toast=False)

    def _gen_use(self):
        from .passwords_ui import EntryDialog
        pw = getattr(self, "gen_current", "")
        dlg = EntryDialog(self, None, self._pw_saved)
        dlg.v_pw.set(pw)
        dlg.pw_e.configure(show="")

    # ------------------------------------------------------------ 04 sızıntı merkezi
    def _pw_leak_card(self, card):
        cat = self.breach_catalog
        hits = []
        for e in self.pv.entries:
            st = cat.status(e)
            if st:
                hits.append((e, st))
        open_n = sum(1 for _e, s in hits if s["open"])
        safe_n = sum(1 for _e, s in hits if not s["open"])
        checked = [e for e in self.pv.entries if lifecycle.hibp_valid(e)]
        leaked = [e for e in checked if e.hibp.get("count", 0) > 0]
        last = max((e.hibp.get("at", 0) for e in checked), default=0)
        rows = [("SİTE İHLALİ · PAROLAN DEĞİŞMEMİŞ", open_n, RED), ("SİTE İHLALİ · SONRADAN DEĞİŞTİRİLMİŞ", safe_n, GREEN),
                ("ÇEVRİM İÇİ KONTROLDE SIZMIŞ", len(leaked), RED),
                ("ÇEVRİM İÇİ KONTROL EDİLEN", f"{len(checked)}/{len(self.pv.entries)}", FG_2)]
        for label, n, col in rows:
            r = tk.Frame(card, bg=PANEL)
            r.pack(fill="x", padx=16, pady=1)
            tk.Frame(r, bg=col if n not in (0, "0") else LINE, width=3, height=22).pack(side="left", padx=(0, 10))
            tk.Label(r, text=label, bg=PANEL, fg=FG_2, font=F["small"], anchor="w").pack(side="left")
            tk.Label(r, text=str(n), bg=PANEL, fg=col if n not in (0, "0") else DIM, font=F["mono_b"]).pack(side="right")
        for e, s in [h for h in hits if h[1]["open"]][:3]:
            b = s["open"][0]
            tk.Label(card, text=f"• {e.title}: {b['t']} ihlali · {breaches.fmt_date(b['bd'])} · {breaches.fmt_count(b['c'])} hesap · "
                     f"parolan {_fmt_day(e.changed)} tarihinden beri aynı", bg=PANEL, fg=RED, font=F["tiny"], anchor="w",
                     justify="left", wraplength=520).pack(fill="x", padx=16, pady=(2, 0))
        tk.Label(card, text=f"Katalog: {cat.size} site ihlali · en yeni kayıt {breaches.fmt_date(cat.latest)} · "
                 f"son çevrim içi parola kontrolü {_fmt_day(last)}", bg=PANEL, fg=DIM, font=F["tiny"], anchor="w").pack(fill="x", padx=16, pady=(8, 0))
        tk.Label(card, text=breaches.ATTRIBUTION, bg=PANEL, fg=DIM, font=F["tiny"], anchor="w").pack(fill="x", padx=16)
        bar = tk.Frame(card, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(10, 14))
        self._flow(bar, [StudioButton(bar, "PAROLALARIMI KONTROL ET", self.pw_hibp, "primary", "search", "sm",
                                      tooltip="İsteğe bağlı · yalnızca SHA-1 özetinin ilk 5 karakteri gönderilir"),
                         StudioButton(bar, "İHLAL KATALOĞUNU GÜNCELLE", self.pw_refresh_breaches, "secondary", "export", "sm",
                                      tooltip="İsteğe bağlı · tüm katalog indirilir, hangi sitelerde hesabın olduğu gönderilmez"),
                         StudioButton(bar, "E-POSTAM SIZDI MI?", self.pw_email_check, "ghost", "user", "sm")])

    def pw_refresh_breaches(self):
        if not messagebox.askyesno("İhlal kataloğunu güncelle",
                                   "ElfCaesar normalde internete bağlanmaz. Bu güncelleme İSTEĞE BAĞLIDIR.\n\n"
                                   "haveibeenpwned.com'dan herkese açık site ihlalleri listesinin TAMAMI indirilir. Hangi sitelerde "
                                   "hesabın olduğu, e-posta adresin veya parolaların gönderilmez.\n\nDevam edilsin mi?", parent=self):
            return
        self.config(cursor="watch")

        def work():
            try:
                cat = breaches.refresh()
                self.after(0, lambda: self._breach_done(cat, None))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda exc=exc: self._breach_done(None, exc))
        threading.Thread(target=work, daemon=True).start()

    def _breach_done(self, cat, exc):
        self.config(cursor="")
        if exc:
            self.notify("error", "vault", "İhlal kataloğu güncellenemedi", str(exc))
            return
        self.__dict__.pop("_breach_cat", None)
        self.notify("success", "vault", "İhlal kataloğu güncellendi", f"{len(cat['items'])} site ihlali · en yeni {breaches.fmt_date(cat['latest'])}")
        self._pw_rebuild()

    def pw_email_check(self):
        if messagebox.askyesno("E-postam sızdı mı?", "E-posta adresi kontrolü Have I Been Pwned sitesinde yapılır; ElfCaesar e-posta "
                               "adresini hiçbir yere göndermez.\n\nTarayıcıda haveibeenpwned.com açılsın mı? Adresini sitede sen yazacaksın.",
                               parent=self):
            import webbrowser
            webbrowser.open("https://haveibeenpwned.com/")

    def pw_hibp(self):
        """Çevrim içi parola sızıntı kontrolü: sonuçlar kayda tarihiyle yazılır ve değişim planına girer."""
        from . import pwaudit
        if not self.pv.entries:
            return
        if not messagebox.askyesno(
                "Çevrim içi sızıntı kontrolü",
                "ElfCaesar normalde hiç internete bağlanmaz. Bu kontrol İSTEĞE BAĞLIDIR.\n\n"
                "Her parolanın SHA-1 özetinin yalnızca ilk 5 karakteri api.pwnedpasswords.com adresine gönderilir "
                "(k-anonimlik). Parolanın kendisi veya tam özeti asla gönderilmez.\n\nDevam edilsin mi?", parent=self):
            return
        import urllib.request

        def fetch(prefix):
            req = urllib.request.Request(f"https://api.pwnedpasswords.com/range/{prefix}",
                                         headers={"User-Agent": "ElfCaesarStudio", "Add-Padding": "true"})
            with urllib.request.urlopen(req, timeout=10) as r:  # nosec B310
                return r.read().decode()
        cache, now = {}, time.time()
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            for e in self.pv.entries:
                if not e.password:
                    continue
                if e.password not in cache:
                    cache[e.password] = pwaudit.hibp_count(e.password, fetch)
                lifecycle.record_hibp(e, cache[e.password], now)
        except Exception as exc:
            self.notify("error", "vault", "Çevrim içi kontrol yapılamadı", str(exc))
            return
        finally:
            self.config(cursor="")
        found = [e for e in self.pv.entries if e.hibp.get("count")]
        lifecycle.log_event(self.pv.meta, "hibp", None, f"{len(cache)} parola kontrol edildi, {len(found)} sızmış")
        self._pw_save()
        if found:
            self.notify("error", "vault", f"{len(found)} parola bilinen sızıntılarda", "DEĞİŞİM PLANI'nda en üste alındı")
        else:
            self.notify("success", "vault", "Hiçbir parola bilinen sızıntılarda yok", f"{len(cache)} farklı parola denetlendi")
        self._pw_rebuild()


# ================================================================== pencereler
class ChangeDialog(_Dialog):
    """Bir parolayı değiştirme süreci: yeni parola hazırla → sitenin değiştirme sayfasını aç → kopyala/doldur → onayla."""

    def __init__(self, app, entry):
        super().__init__(app, "Parolayı değiştir", 600)
        self.e = entry
        b = self.body
        item = app.pw_plan_by_id.get(entry.id) or {"reasons": []}
        tk.Label(b, text="PAROLA DEĞİŞİMİ", bg=PANEL, fg=CYAN, font=F["label"]).pack(anchor="w")
        tk.Label(b, text=entry.title, bg=PANEL, fg=FG, font=F["h2"]).pack(anchor="w")
        tk.Label(b, text=f"{entry.username or '—'} · {entry.domain or 'adres yok'}", bg=PANEL, fg=MUTED, font=F["small"]).pack(anchor="w")
        for r in item["reasons"][:4]:
            tk.Label(b, text=f"• {r['label']}" + (f" — {r['detail']}" if r.get("detail") else ""), bg=PANEL,
                     fg=RED if lifecycle.REASONS[r["key"]][0] >= lifecycle.URGENT else AMBER, font=F["small"], anchor="w").pack(fill="x")
        tk.Label(b, text="1 · YENİ PAROLA", bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(fill="x", pady=(12, 2))
        row = tk.Frame(b, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
        row.pack(fill="x")
        self.v_new = tk.StringVar(value=entry.pending.get("password") or app.generate_for(entry.domain, "değişim"))
        tk.Entry(row, textvariable=self.v_new, bg=INPUT, fg=FG, relief="flat", font=("Consolas", 13, "bold"),
                 insertbackground=FG).pack(side="left", fill="x", expand=True, padx=10, ipady=7)
        StudioButton(row, "YENİDEN", self._regen, "ghost", "spark", "sm").pack(side="right", padx=4)
        rule = ((app.pv.meta.get("site_rules") or {}).get(entry.domain) or {})
        rr = tk.Frame(b, bg=PANEL)
        rr.pack(fill="x", pady=(4, 0))
        tk.Label(rr, text="Site kuralı:", bg=PANEL, fg=DIM, font=F["tiny"]).pack(side="left")
        self.v_rule = tk.StringVar(value=str(rule.get("max") or rule.get("rules") or ""))
        tk.Entry(rr, textvariable=self.v_rule, bg=INPUT, fg=FG, relief="flat", font=F["tiny"], width=40,
                 insertbackground=FG).pack(side="left", padx=6, ipady=3)
        tk.Label(rr, text="ör. 16 veya passwordrules", bg=PANEL, fg=DIM, font=F["tiny"]).pack(side="left")
        self.info = tk.Label(b, text="", bg=PANEL, fg=MUTED, font=F["tiny"], anchor="w")
        self.info.pack(fill="x", pady=(3, 0))
        self.v_new.trace_add("write", lambda *_: self._info())
        self._info()
        tk.Label(b, text="2 · SİTEDE DEĞİŞTİR", bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(fill="x", pady=(12, 2))
        tk.Label(b, text="Sitenin parola değiştirme sayfasını aç; eski parolayı ve yeni parolayı sırayla kopyala (pano geçmişine düşmez).",
                 bg=PANEL, fg=MUTED, font=F["tiny"], anchor="w", justify="left", wraplength=540).pack(fill="x")
        bar = tk.Frame(b, bg=PANEL, height=36)
        bar.pack(fill="x", pady=(6, 0))
        app._flow(bar, [StudioButton(bar, "DEĞİŞTİRME SAYFASINI AÇ", self._open, "accent", "open", "sm"),
                        StudioButton(bar, "ESKİ PAROLAYI KOPYALA", lambda: self._copy(self.e.password), "secondary", "copy", "sm"),
                        StudioButton(bar, "YENİ PAROLAYI KOPYALA", lambda: self._copy(self.v_new.get()), "secondary", "copy", "sm")])
        tk.Label(b, text="3 · ONAYLA", bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(fill="x", pady=(12, 2))
        bot = tk.Frame(b, bg=PANEL)
        bot.pack(fill="x", pady=(4, 0))
        StudioButton(bot, "SİTEDE DEĞİŞTİRDİM", self._done, "primary", "check", min_width=170).pack(side="right")
        StudioButton(bot, "SONRA BİTİRECEĞİM", self._later, "ghost", "bell").pack(side="right", padx=8)
        # pencere açılır açılmaz yeni parola kasaya "bekleyen" olarak yazılır: kopyalayıp sitede kullanırsan kaybolmaz
        self._stash()
        self.protocol("WM_DELETE_WINDOW", self._later)
        self.center()

    def _info(self):
        from .security import password_strength
        pw = self.v_new.get()
        s = password_strength(pw)
        same = pw == self.e.password or any(h.get("password") == pw for h in self.e.history)
        self.info.configure(text=("BU PAROLA DAHA ÖNCE KULLANILDI · " if same else "") + f"{s['name']} · {len(pw)} karakter",
                            fg=RED if same or s["level"] < 3 else MUTED)

    def _stash(self):
        app = self.app
        app.remember_site_rule(self.e.domain, self.v_rule.get())
        lifecycle.start_change(self.e, self.v_new.get(), ", ".join(r["label"] for r in (app.pw_plan_by_id.get(self.e.id) or {"reasons": []})["reasons"][:2]))
        app._pw_save()

    def _regen(self):
        app = self.app
        app.remember_site_rule(self.e.domain, self.v_rule.get())
        self.v_new.set(app.generate_for(self.e.domain, "değişim"))
        self._stash()

    def _open(self):
        import webbrowser
        url = pwgen.change_password_url(self.e.url or self.e.domain)
        if not url:
            self.app.notify("warning", "vault", "Kayıtta adres yok", "Kaydı düzenleyip sitenin adresini ekle")
            return
        self._stash()
        webbrowser.open(url)

    def _copy(self, value):
        self._stash()
        self.app.guarded_copy(value)
        self.app.notify("success", "vault", "Panoya kopyalandı", self.e.title, toast=False)

    def _later(self):
        self._stash()
        self.destroy()
        self.app.notify("info", "vault", "Değişim sürüyor olarak işaretlendi", f"{self.e.title} · yeni parola kasada bekliyor", toast=False)
        self.app._pw_rebuild()

    def _done(self):
        self._stash()
        self.destroy()
        self.app.pw_change_confirm(self.e)


class TimelineDialog(_Dialog):
    def __init__(self, app, entry):
        super().__init__(app, "Zaman çizelgesi", 560)
        b = self.body
        tk.Label(b, text="PAROLANIN YOLCULUĞU", bg=PANEL, fg=VIOLET, font=F["label"]).pack(anchor="w")
        tk.Label(b, text=entry.title, bg=PANEL, fg=FG, font=F["h2"]).pack(anchor="w", pady=(0, 6))
        st = app.breach_catalog.status(entry)
        events = lifecycle.entry_timeline(app.pv.meta, entry)
        if st:
            from .breaches import _ts
            for x in st["all"]:
                events.append({"t": max(_ts(x["bd"]), _ts(x["ad"])),
                               "text": f"{x['t']} veri ihlali duyuruldu (ihlal {breaches.fmt_date(x['bd'])} · {breaches.fmt_count(x['c'])} hesap"
                                       + (", parolalar dahil)" if x["pw"] else ")")})
            events.sort(key=lambda x: -x["t"])
        for ev in events[:16]:
            r = tk.Frame(b, bg=PANEL)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=_fmt_day(ev["t"]), bg=PANEL, fg=DIM, font=F["mono_xs"], width=11, anchor="w").pack(side="left")
            tk.Frame(r, bg=CYAN if "ihlal" not in ev["text"] else RED, width=3, height=18).pack(side="left", padx=8)
            tk.Label(r, text=ev["text"], bg=PANEL, fg=FG_2, font=F["small"], anchor="w", justify="left", wraplength=420).pack(side="left", fill="x")
        rot = dict(lifecycle.ROTATE_CHOICES).get(entry.rotate_days, f"{entry.rotate_days} günde bir")
        tk.Label(b, text=f"Yenileme hatırlatması: {rot} · parola yaşı {int((time.time() - entry.changed) / 86400)} gün · "
                 f"{len(entry.history)} eski parola saklanıyor", bg=PANEL, fg=MUTED, font=F["tiny"], anchor="w").pack(fill="x", pady=(10, 0))
        StudioButton(b, "KAPAT", self.destroy, "ghost").pack(anchor="e", pady=(12, 0))
        self.center()


class GenHistoryDialog(_Dialog):
    def __init__(self, app):
        super().__init__(app, "Son üretilen parolalar", 600)
        b = self.body
        tk.Label(b, text="SON ÜRETİLENLER", bg=PANEL, fg=AMBER, font=F["label"]).pack(anchor="w")
        tk.Label(b, text="Üretilen parolalar kasada şifreli saklanır: sitede kullanıp kaydetmeyi unutsan da kaybolmaz.", bg=PANEL,
                 fg=MUTED, font=F["tiny"], anchor="w").pack(fill="x", pady=(0, 8))
        hist = app.pv.meta.get("gen_history", []) if app.pv.is_open else []
        if not hist:
            tk.Label(b, text="Henüz kayıt yok (kasa açıkken üretilenler burada görünür).", bg=PANEL, fg=DIM, font=F["small"]).pack(anchor="w")
        self.show = False
        self.rows = []
        for h in hist[:15]:
            r = tk.Frame(b, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            r.pack(fill="x", pady=2)
            lab = tk.Label(r, text="•" * min(16, len(h["p"])), bg=INPUT, fg=FG, font=F["mono"], width=26, anchor="w")
            lab.pack(side="left", padx=8, pady=4)
            self.rows.append((lab, h["p"]))
            tk.Label(r, text=f"{_fmt_day(h['t'])} · {h.get('d') or '—'} · {h.get('via', '')}", bg=INPUT, fg=DIM, font=F["tiny"]).pack(side="left")
            StudioButton(r, "", lambda p=h["p"]: (app.guarded_copy(p), app.notify("success", "vault", "Kopyalandı", toast=False)),
                         "ghost", "copy", "sm", tooltip="Kopyala").pack(side="right", padx=4)
        bar = tk.Frame(b, bg=PANEL)
        bar.pack(fill="x", pady=(10, 0))
        StudioButton(bar, "KAPAT", self.destroy, "ghost").pack(side="right")
        StudioButton(bar, "GÖSTER / GİZLE", self._toggle, "secondary", "search", "sm").pack(side="right", padx=8)
        self.center()

    def _toggle(self):
        self.show = not self.show
        for lab, p in self.rows:
            lab.configure(text=p if self.show else "•" * min(16, len(p)))
