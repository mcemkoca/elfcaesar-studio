"""Parola Kasası sayfası (6.10.0): kayıtlar, otomatik tamamlamalı arama, tarayıcıdan içe aktarma, Parola Denetimi,
Domino analizi, Hızlı Doldur (Ctrl+Alt+P) + Oltalama Kalkanı, Dijital Miras (Shamir), Baskı Parolası ve
kişiye şifreli paylaşım. Studio'ya karıştırılan arayüz katmanı; şifreleme motorlarına dokunmaz."""
from __future__ import annotations

import re
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import autotype, pwaudit, shred
from .pwvault import BROWSER_EXPORT_STEPS, Entry, PasswordVault, parse_share, registrable_domain, share_payload
from .security import password_strength
from .theme import F, BG, PANEL, INPUT, LINE, FG, FG_2, MUTED, DIM, AMBER, CYAN, GREEN, RED, ORANGE, VIOLET, mix
from .widgets import StudioButton, Segmented, Tooltip
from .dialog_base import _Dialog
from .lifecycle_ui import LifecycleMixin
from . import lifecycle

ISSUE_COLORS = {"leaked": RED, "reused": ORANGE, "weak": ORANGE, "similar": AMBER, "old": AMBER, "insecure_url": AMBER}
URL_RE = re.compile(r"^\s*(https?://|www\.)\S+\s*$", re.I)


class PasswordsMixin(LifecycleMixin):
    # ------------------------------------------------------------ yardımcılar
    @property
    def pv(self) -> PasswordVault:
        if "_pv" not in self.__dict__:
            path = self.prefs.get("pw_vault_path") or None
            self._pv = PasswordVault(Path(path) if path else None)
        return self._pv

    def _pw_rebuild(self):
        if "passwords" in self.pages and self.active_page == "passwords":
            frame = self.pages.pop("passwords")
            frame.destroy()
            self.active_page = None
            self.show_page("passwords")
        elif "passwords" in self.pages:
            self.pages.pop("passwords").destroy()

    def _pw_save(self):
        try:
            self.pv.save()
            m = self.pv.last_merge
            if m and m.get("conflict_copy"):
                self.notify("warning", "vault", "Diskteki kasa başka parolayla değiştirilmiş",
                            "O sürüm çakışma kopyası olarak saklandı · YEDEK VE SENKRON kartından birleştirebilirsin")
            elif m and any(m.values()):
                self.notify("success", "vault", "Başka cihazdaki değişiklikler birleştirildi",
                            f"{m['added']} yeni · {m['updated']} güncel · {m['removed']} silinen")
            return True
        except Exception as exc:
            self.notify("error", "vault", "Parola kasası kaydedilemedi", str(exc))
            return False

    # ------------------------------------------------------------ sayfa
    def _page_passwords(self):
        self._page_intro("11 / PAROLA KASASI", "Parolaların, denetimli ve tek ana parolayla",
                         "Bütün parolaların AES-256-GCM kasasında. Tarayıcılardan tek dosyayla içe aktar, sızmış / tekrar eden / "
                         "zayıf parolaları gör, bir hesap düşerse hangilerinin domino gibi düşeceğini öğren, Ctrl+Alt+P ile "
                         "panoya dokunmadan doldur.", VIOLET, "YENİ", "key")
        if not self.pv.is_open:
            self._pw_locked_view()
            return
        self.pw_audit = pwaudit.audit(self.pv.entries)
        self._pw_plan_compute()
        if not self.pv.decoy:
            self.sec.vault_health = self.pw_plan["score"] if self.pv.entries else None
            self.sec.password_vault = True
            self.after_idle(self.refresh_security)
        self._pw_tiles()
        self._pw_list_card()
        pl = self._card(self.content, "02 / DEĞİŞİM PLANI · SÜREÇ TAKİBİ", "ÖNCELİKLİ · BEKLEYEN · ERTELENEN · GEÇMİŞ", "history", RED)
        pl.pack(fill="x", pady=(0, 12))
        self._pw_plan_card(pl)
        row0 = tk.Frame(self.content, bg=BG)
        row0.pack(fill="x", pady=(0, 12))
        gc = self._card(row0, "03 / PAROLA ÜRETİCİ", "RASTGELE · HECELİ · PIN · SİTE KURALI", "spark", AMBER)
        lc = self._card(row0, "04 / SIZINTI MERKEZİ", "SİTE İHLALLERİ · PAROLA SIZINTISI", "alert", RED)
        self._auto_grid(row0, [gc, lc], 460, 2)
        self._pw_gen_card(gc)
        self._pw_leak_card(lc)
        row = tk.Frame(self.content, bg=BG)
        row.pack(fill="x", pady=(0, 12))
        a = self._card(row, "05 / PAROLA DENETİMİ", "ÇEVRİMDIŞI · SIZINTI · TEKRAR · BENZERLİK · YAŞ", "shield", GREEN)
        d = self._card(row, "06 / DOMİNO ANALİZİ", "BİR HESAP DÜŞERSE HANGİLERİ DÜŞER?", "alert", RED)
        self._auto_grid(row, [a, d], 460, 2)
        self._pw_audit_card(a)
        self._pw_domino_card(d)
        row2 = tk.Frame(self.content, bg=BG)
        row2.pack(fill="x", pady=(0, 12))
        q = self._card(row2, "07 / HIZLI DOLDUR · OLTALAMA KALKANI", "CTRL+ALT+P", "send", CYAN)
        m = self._card(row2, "08 / DİJİTAL MİRAS", "SHAMIR", "idcard", AMBER)
        b = self._card(row2, "09 / BASKI PAROLASI", "SAHTE KASA", "lock", VIOLET)
        self._auto_grid(row2, [q, m, b], 330, 3)
        self._pw_quick_card(q)
        self._pw_miras_card(m)
        self._pw_duress_card(b)
        sy = self._card(self.content, "10 / YEDEK VE SENKRON", "OTOMATİK YEDEK · BULUT KLASÖRÜ · ÇAKIŞMA BİRLEŞTİRME", "save", GREEN)
        sy.pack(fill="x", pady=(0, 12))
        self._pw_sync_card(sy)

    # ------------------------------------------------------------ kilitli görünüm
    def _pw_locked_view(self):
        card = self._card(self.content, "PAROLA KASASI KİLİTLİ", "ANA PAROLA HİÇBİR YERE YAZILMAZ", "lock", VIOLET)
        card.pack(fill="x", pady=(0, 12))
        exists = self.pv.exists()
        self._wrap(tk.Label(card, text=("Kasa bu bilgisayarda hazır. Açmak için ana parolanı gir. Kasa, kilitlediğinde, panik "
                                        "modunda veya otomatik kilitte bellekten silinir." if exists else
                                        "Henüz parola kasan yok. Güçlü bir ana parola cümlesi belirle: bu parolayı unutursan kasayı "
                                        "kimse açamaz. Dijital Miras ile güvendiğin kişilere kurtarma parçaları bırakabilirsin."),
                            bg=PANEL, fg=MUTED, font=F["small"], justify="left"), 40).pack(fill="x", padx=16)
        tk.Label(card, text=str(self.pv.path), bg=PANEL, fg=DIM, font=F["mono_xs"], anchor="w").pack(fill="x", padx=16, pady=(6, 0))
        bar = tk.Frame(card, bg=PANEL, height=40)
        bar.pack(fill="x", padx=16, pady=(12, 16))
        btns = ([StudioButton(bar, "KASAYI AÇ", self.pw_unlock, "primary", "unlock")] if exists else
                [StudioButton(bar, "KASA OLUŞTUR", self.pw_create, "primary", "key")])
        btns += [StudioButton(bar, "BAŞKA KASA DOSYASI", self.pw_choose_file, "ghost", "open"),
                 StudioButton(bar, "MİRASTAN KURTAR", self.pw_miras_recover, "ghost", "idcard")]
        self._flow(bar, btns)
        feats = self._card(self.content, "BU BÖLÜMDE NELER VAR", "6.11.0", "spark", AMBER)
        feats.pack(fill="x", pady=(0, 12))
        for title, text in (
                ("Tarayıcılardan içe aktar", "Chrome, Edge, Brave, Opera, Firefox, Bitwarden, KeePass dışa aktarma dosyası; içe aktardıktan sonra açık CSV güvenle imha edilir."),
                ("Değişim Planı", "Hangi parola neden değişmeli, adım adım değiştir; bekleyen değişiklikler, zaman çizelgesi, hatırlatma."),
                ("Parola Üretici + Sızıntı Merkezi", "Site kurallarına uyan güçlü parolalar; site veri ihlalleri ve çevrim içi sızıntı kontrolü."),
                ("Parola Denetimi", "Sızmış, tekrar eden, birbirine benzeyen, zayıf ve 1 yıldan eski parolalar; kasa sağlık puanı."),
                ("Domino Analizi", "E-posta hesabın düşerse 'parolamı unuttum' ile hangi hesapların ele geçirilebileceğini gösterir."),
                ("Hızlı Doldur + Oltalama Kalkanı", "Ctrl+Alt+P: açık pencereyi tanır, panoya dokunmadan yazar; kopyaladığın sahte bağlantıyı yakalar."),
                ("Dijital Miras", "Kurtarma anahtarını 2–10 parçaya böl; yalnızca belirlediğin sayıda kişi bir araya gelince açılır."),
                ("Baskı Parolası", "Zorla açtırılırsan ikinci parola zararsız bir sahte kasa açar.")):
            r = tk.Frame(feats, bg=PANEL)
            r.pack(fill="x", padx=16, pady=3)
            tk.Label(r, text="✦  " + title, bg=PANEL, fg=FG, font=F["body_b"], width=30, anchor="w").pack(side="left")
            tk.Label(r, text=text, bg=PANEL, fg=MUTED, font=F["small"], anchor="w", justify="left", wraplength=760).pack(side="left", fill="x")
        tk.Frame(feats, bg=PANEL, height=10).pack()

    def pw_choose_file(self):
        path = filedialog.askopenfilename(title="Parola kasası (.elfvault)", filetypes=[("ELF Vault", "*.elfvault")])
        if path:
            self.set_pref("pw_vault_path", path)
            self.__dict__.pop("_pv", None)
            self._pw_rebuild()

    def pw_create(self):
        pw = self._password(confirm=True, purpose="Parola kasası için ANA PAROLA belirle. Unutursan kasa açılmaz; "
                                                  "Dijital Miras ile güvendiğin kişilere kurtarma bırakabilirsin.")
        if pw is None:
            return
        self.pv.create(pw)
        self.notify("success", "vault", "Parola kasası oluşturuldu", str(self.pv.path))
        self._pw_rebuild()

    def pw_unlock(self):
        pw = self._password(purpose="Parola kasasını açmak için ana parolanı gir.")
        if pw is None:
            return
        decoy = self.prefs.get("pw_decoy_path") or None
        try:
            self.pv.unlock(pw, Path(decoy) if decoy else None)
        except Exception as exc:
            self.notify("error", "vault", "Parola kasası açılamadı", str(exc))
            return
        self.notify("success", "vault", "Parola kasası açıldı", f"{len(self.pv.entries)} kayıt", toast=False)
        try:
            urgent = lifecycle.plan(self.pv.entries, self.breach_catalog)["counts"]["urgent"]
            if urgent and not self.pv.decoy:
                self.notify("warning", "vault", f"{urgent} parola acil değişim bekliyor", "DEĞİŞİM PLANI kartında en üstte")
        except Exception:
            pass
        self._pw_rebuild()

    def pw_lock(self, silent=False):
        if "_pv" in self.__dict__ and self.pv.is_open:
            self.pv.lock()
            if not silent:
                self.notify("info", "vault", "Parola kasası kilitlendi")
            self._pw_rebuild()

    # ------------------------------------------------------------ özet karoları
    def _pw_tiles(self):
        a = self.pw_audit
        tiles = tk.Frame(self.content, bg=BG)
        tiles.pack(fill="x", pady=(0, 12))
        sc = self.pw_plan["score"]
        pc = self.pw_plan["counts"]
        items = [("KAYIT", len(self.pv.entries), FG), ("KASA SAĞLIĞI", f"{sc}/100",
                                                       GREEN if sc >= 80 else (AMBER if sc >= 50 else RED)),
                 ("ACİL DEĞİŞİM", pc["urgent"], RED), ("SIZMIŞ", a["counts"]["leaked"], RED),
                 ("TEKRAR EDEN", a["counts"]["reused"], ORANGE), ("DEĞİŞİM SÜRÜYOR", pc["pending"], CYAN)]
        boxes = []
        for label, value, col in items:
            t = tk.Frame(tiles, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            tk.Frame(t, bg=col, height=2).pack(fill="x")
            tk.Label(t, text=label, bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(fill="x", padx=14, pady=(10, 0))
            tk.Label(t, text=str(value), bg=PANEL, fg=col if value not in (0, "0") else FG, font=F["metric"], anchor="w").pack(
                fill="x", padx=14, pady=(0, 10))
            boxes.append(t)
        self._auto_grid(tiles, boxes, 150, 6)

    # ------------------------------------------------------------ liste + otomatik tamamlama
    def _pw_list_card(self):
        card = self._card(self.content, "01 / KAYITLAR", "ARAMA OTOMATİK TAMAMLANIR · ÇİFT TIK DÜZENLER", "key", VIOLET)
        card.pack(fill="both", expand=True, pady=(0, 12))
        top = tk.Frame(card, bg=PANEL)
        top.pack(fill="x", padx=16, pady=(0, 8))
        self.pw_q = tk.StringVar()
        ent = tk.Entry(top, textvariable=self.pw_q, bg=INPUT, fg=FG, insertbackground=FG, relief="flat", font=F["body"],
                       highlightthickness=1, highlightbackground=LINE, highlightcolor=VIOLET)
        ent.pack(side="left", fill="x", expand=True, ipady=7)
        self.pw_entry = ent
        self.pw_filter = None
        acts = tk.Frame(top, bg=PANEL)
        acts.pack(side="right", padx=(10, 0))
        StudioButton(acts, "YENİ KAYIT", self.pw_new, "primary", "key", "sm").pack(side="left", padx=3)
        StudioButton(acts, "TARAYICIDAN İÇE AKTAR", self.pw_import, "accent", "open", "sm").pack(side="left", padx=3)
        StudioButton(acts, "KİLİTLE", self.pw_lock, "secondary", "lock", "sm").pack(side="left", padx=3)
        # öneri listesi (otomatik tamamlama)
        self.pw_sugg = tk.Listbox(card, bg=INPUT, fg=FG_2, selectbackground=mix(VIOLET, PANEL, .5), relief="flat", height=0,
                                  font=F["body"], highlightthickness=1, highlightbackground=VIOLET, activestyle="none")
        self.pw_q.trace_add("write", lambda *_: self._pw_on_query())
        ent.bind("<Down>", lambda _e: self._pw_sugg_move(1))
        ent.bind("<Up>", lambda _e: self._pw_sugg_move(-1))
        ent.bind("<Return>", lambda _e: self._pw_sugg_pick())
        ent.bind("<Tab>", lambda _e: (self._pw_sugg_pick(), "break")[1])
        ent.bind("<Escape>", lambda _e: self._pw_sugg_hide())
        ent.bind("<FocusOut>", lambda _e: self.after(150, self._pw_sugg_hide))
        self.pw_sugg.bind("<ButtonRelease-1>", lambda _e: self._pw_sugg_pick())
        self.pw_hint = tk.Label(card, text="", bg=PANEL, fg=DIM, font=F["tiny"], anchor="w")
        self.pw_hint.pack(fill="x", padx=16)
        wrap = tk.Frame(card, bg=PANEL)
        wrap.pack(fill="both", expand=True, padx=16, pady=(4, 8))
        self.pw_tree = ttk.Treeview(wrap, columns=("title", "user", "domain", "issues", "changed"), show="headings", height=11)
        for col, text, w, st in (("title", "BAŞLIK", 200, True), ("user", "KULLANICI", 220, True), ("domain", "ALAN ADI", 170, True),
                                 ("issues", "DENETİM", 300, True), ("changed", "PAROLA YAŞI", 100, False)):
            self.pw_tree.heading(col, text=text, anchor="w")
            self.pw_tree.column(col, width=w, stretch=st, anchor="w")
        for tag, col in (("bad", RED), ("warn", AMBER), ("ok", GREEN)):
            self.pw_tree.tag_configure(tag, foreground=col)
        ysb = ttk.Scrollbar(wrap, orient="vertical", command=self.pw_tree.yview)
        self.pw_tree.configure(yscrollcommand=ysb.set)
        self.pw_tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        self.pw_tree.bind("<Double-1>", lambda _e: self.pw_edit())
        self.pw_tree.bind("<Return>", lambda _e: self.pw_copy("password"))
        bar = tk.Frame(card, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(4, 14))
        self._flow(bar, [StudioButton(bar, "KULLANICI ADINI KOPYALA", lambda: self.pw_copy("username"), "secondary", "copy", "sm"),
                         StudioButton(bar, "PAROLAYI KOPYALA", lambda: self.pw_copy("password"), "secondary", "copy", "sm"),
                         StudioButton(bar, "HIZLI DOLDUR", lambda: self.quick_fill(self._pw_selected()), "accent", "send", "sm"),
                         StudioButton(bar, "KİŞİYE ŞİFRELİ GÖNDER", self.pw_share, "accent", "user", "sm"),
                         StudioButton(bar, "DÜZENLE", self.pw_edit, "ghost", "key", "sm"),
                         StudioButton(bar, "SİL", self.pw_delete, "danger", "trash", "sm")])
        self._pw_render()

    def _pw_on_query(self):
        q = self.pw_q.get()
        self._pw_render()
        sugg = [s for s in self.pv.suggest(q) if s.casefold() != q.casefold().strip()]
        lb = self.pw_sugg
        lb.delete(0, "end")
        if not sugg or not q.strip():
            self._pw_sugg_hide()
            return
        for s in sugg:
            lb.insert("end", "  " + s)
        lb.configure(height=len(sugg))
        e = self.pw_entry
        lb.place(in_=e, x=0, y=e.winfo_height() + 2, width=e.winfo_width())
        lb.lift()
        lb.selection_clear(0, "end")
        lb.selection_set(0)
        self.pw_hint.configure(text="↑↓ öneriler · Tab / Enter tamamla · Esc kapat")

    def _pw_sugg_hide(self):
        try:
            self.pw_sugg.place_forget()
            self.pw_hint.configure(text="")
        except tk.TclError:
            pass

    def _pw_sugg_move(self, d):
        lb = self.pw_sugg
        if not lb.winfo_ismapped() or not lb.size():
            return
        cur = (lb.curselection() or (0,))[0]
        nxt = max(0, min(lb.size() - 1, cur + d))
        lb.selection_clear(0, "end")
        lb.selection_set(nxt)
        return "break"

    def _pw_sugg_pick(self):
        lb = self.pw_sugg
        if lb.winfo_ismapped() and lb.curselection():
            value = lb.get(lb.curselection()[0]).strip()
            self.pw_q.set(value)
            self.pw_entry.icursor("end")
            self._pw_sugg_hide()
            kids = self.pw_tree.get_children()
            if len(kids) == 1:
                self.pw_tree.selection_set(kids[0])
            return "break"

    def _pw_render(self):
        tree = getattr(self, "pw_tree", None)
        if tree is None or not tree.winfo_exists():
            return
        tree.delete(*tree.get_children())
        a = self.pw_audit["entries"]
        now = time.time()
        rows = self.pv.search(self.pw_q.get() if hasattr(self, "pw_q") else "")
        if self.pw_filter:
            rows = [e for e in rows if self.pw_filter in a.get(e.id, {}).get("issues", [])]
        for e in rows:
            item = getattr(self, "pw_plan_by_id", {}).get(e.id) or {"reasons": [], "state": "ok"}
            text = " · ".join(r["label"] for r in item["reasons"]) or "✓ Sağlam"
            if item["state"] == "pending":
                text = "⟳ Değişim sürüyor · " + text
            tag = {"urgent": "bad", "recommended": "warn", "snoozed": "warn", "pending": "warn"}.get(item["state"], "ok")
            age = (now - e.changed) / 86400
            age_t = "bugün" if age < 1 else (f"{age:.0f} gün" if age < 60 else (f"{age / 30:.0f} ay" if age < 730 else f"{age / 365:.0f} yıl"))
            tree.insert("", "end", iid=e.id, values=(e.title, e.username, e.domain, text, age_t), tags=(tag,))

    def _pw_selected(self) -> Entry | None:
        tree = getattr(self, "pw_tree", None)
        if tree is None:
            return None
        sel = tree.selection()
        if not sel:
            kids = tree.get_children()
            if len(kids) == 1:
                return self.pv.get(kids[0])
            return None
        return self.pv.get(sel[0])

    def pw_copy(self, field):
        e = self._pw_selected()
        if not e:
            self.notify("warning", "vault", "Önce listeden bir kayıt seç")
            return
        self.guarded_copy(getattr(e, field))
        e.used = time.time()
        self._pw_save()
        self.notify("success", "vault", ("Parola" if field == "password" else "Kullanıcı adı") + " panoya kopyalandı",
                    e.title + (f" · {self.sec.clipboard_seconds} sn sonra silinir" if self.sec.clipboard_guard else ""), toast=False)

    def pw_new(self):
        EntryDialog(self, None, self._pw_saved)

    def pw_edit(self):
        e = self._pw_selected()
        if e:
            EntryDialog(self, e, self._pw_saved)

    def _pw_saved(self, entry: Entry, is_new: bool):
        if is_new:
            self.pv.add(entry)
        if self._pw_save():
            self.notify("success", "vault", "Parola kaydedildi", entry.title, toast=False)
            self._pw_rebuild()

    def pw_delete(self):
        e = self._pw_selected()
        if not e or not messagebox.askyesno("Kaydı sil", f"“{e.title}” kaydı silinsin mi?", parent=self, default="no"):
            return
        self.pv.remove(e.id)
        self._pw_save()
        self._pw_rebuild()

    # ------------------------------------------------------------ içe aktarma
    def pw_import(self):
        ImportDialog(self)

    def _pw_do_import(self, path: str, wipe: bool):
        try:
            raw = Path(path).read_bytes()
            text = None
            for enc in ("utf-8-sig", "utf-8", "cp1254"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            res = self.pv.import_csv(text or "")
        except Exception as exc:
            self.notify("error", "vault", "İçe aktarılamadı", str(exc))
            return
        if not self._pw_save():
            return
        msg = f"{res['source']}: {res['added']} yeni, {res['updated']} güncellendi, {res['skipped']} atlandı"
        self.notify("success", "vault", "Parolalar içe aktarıldı", msg)
        if wipe:
            rec = shred.shred_file(path, "random1")
            self.notify("success" if rec.ok else "warning", "file",
                        "Açık CSV dosyası güvenle imha edildi" if rec.ok else "CSV imha edilemedi", rec.error or Path(path).name)
        self._pw_rebuild()

    # ------------------------------------------------------------ denetim
    def _pw_audit_card(self, card):
        a = self.pw_audit
        sc = self.pw_plan["score"]
        body = tk.Frame(card, bg=PANEL)
        body.pack(fill="x", padx=16, pady=(0, 6))
        col = GREEN if sc >= 80 else (AMBER if sc >= 50 else RED)
        tk.Label(body, text=f"{sc}", bg=PANEL, fg=col, font=F["display"]).pack(side="left")
        tk.Label(body, text=" / 100  kasa sağlığı" + (" · site ihlalleri dahil" if self.pw_plan.get("breached") else ""),
                 bg=PANEL, fg=MUTED, font=F["small"]).pack(side="left", anchor="s", pady=6)
        for key, label in pwaudit.LABELS.items():
            n = a["counts"][key]
            r = tk.Frame(card, bg=PANEL)
            r.pack(fill="x", padx=16, pady=1)
            tk.Frame(r, bg=ISSUE_COLORS[key] if n else LINE, width=3, height=22).pack(side="left", padx=(0, 10))
            tk.Label(r, text=label, bg=PANEL, fg=FG_2 if n else DIM, font=F["body"], anchor="w").pack(side="left")
            tk.Label(r, text=str(n), bg=PANEL, fg=ISSUE_COLORS[key] if n else DIM, font=F["mono_b"]).pack(side="right")
            if n:
                b = tk.Label(r, text="GÖSTER", bg=PANEL, fg=CYAN, font=F["label"], cursor="hand2")
                b.pack(side="right", padx=10)
                b.bind("<Button-1>", lambda _e, k=key: self._pw_set_filter(k))
        bar = tk.Frame(card, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(10, 14))
        self._flow(bar, [StudioButton(bar, "FİLTREYİ KALDIR", lambda: self._pw_set_filter(None), "ghost", "close", "sm"),
                         StudioButton(bar, "ÇEVRİM İÇİ SIZINTI KONTROLÜ", self.pw_hibp, "secondary", "search", "sm",
                                      tooltip="İsteğe bağlı · Have I Been Pwned · yalnızca özetin ilk 5 karakteri gönderilir")])

    def _pw_set_filter(self, key):
        self.pw_filter = key
        self._pw_render()
        self.content_canvas.yview_moveto(0.12)

    # ------------------------------------------------------------ domino
    def _pw_domino_card(self, card):
        chains = pwaudit.domino(self.pv.entries)[:6]
        if not chains:
            tk.Label(card, text="Zincirleme risk yok: hiçbir hesap başka bir hesabı düşürmüyor. 👍".replace(" 👍", ""),
                     bg=PANEL, fg=GREEN, font=F["small"], anchor="w").pack(fill="x", padx=16, pady=(0, 14))
            return
        self._wrap(tk.Label(card, text="Aynı parolayı paylaşan hesaplar birlikte düşer. E-posta hesabın düşerse, o adresle açılmış "
                            "hesaplar “parolamı unuttum” ile ele geçirilebilir. En büyük etki alanı en üstte.",
                            bg=PANEL, fg=MUTED, font=F["tiny"], justify="left"), 40).pack(fill="x", padx=16, pady=(0, 6))
        n_total = len(self.pv.entries)
        for c in chains:
            e, fallen = c["entry"], c["fallen"]
            r = tk.Frame(card, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            r.pack(fill="x", padx=16, pady=2)
            share = len(fallen) / max(1, n_total - 1)
            col = RED if share >= .3 else (ORANGE if share >= .15 else AMBER)
            tk.Frame(r, bg=col, width=3).pack(side="left", fill="y")
            t = tk.Frame(r, bg=INPUT)
            t.pack(side="left", fill="x", expand=True, padx=10, pady=5)
            tk.Label(t, text=f"{e.title}{'  · e-posta' if c['is_email'] else ''} ele geçirilirse → {len(fallen)} hesap düşer",
                     bg=INPUT, fg=FG, font=F["body_b"], anchor="w").pack(fill="x")
            names = ", ".join(x.title for x in fallen[:6]) + (f" +{len(fallen) - 6}" if len(fallen) > 6 else "")
            tk.Label(t, text=names, bg=INPUT, fg=MUTED, font=F["tiny"], anchor="w").pack(fill="x")
        tk.Label(card, text="Çözüm: zincirin başındaki hesaba benzersiz, güçlü bir parola ve iki adımlı doğrulama.",
                 bg=PANEL, fg=DIM, font=F["tiny"], anchor="w").pack(fill="x", padx=16, pady=(6, 14))

    # ------------------------------------------------------------ hızlı doldur + oltalama
    def _pw_quick_card(self, card):
        on = autotype.IS_WINDOWS and getattr(self, "hotkeys_ok", False)
        self._wrap(tk.Label(card, text="Herhangi bir giriş ekranında Ctrl+Alt+P: ElfCaesar ön plandaki pencereyi tanır, uygun kaydı "
                            "önerir; seçince kullanıcı adı + Tab + parolayı klavyeden yazar. Parola panoya hiç girmez.",
                            bg=PANEL, fg=MUTED, font=F["small"], justify="left"), 30).pack(fill="x", padx=16)
        tk.Label(card, text=("● Ctrl+Alt+P etkin" if on else "○ Yalnızca Windows'ta ve kısayollar açıkken"), bg=PANEL,
                 fg=GREEN if on else DIM, font=F["mono_xs"], anchor="w").pack(fill="x", padx=16, pady=(6, 8))
        tk.Label(card, text="OLTALAMA KALKANI · BAĞLANTI DENETLE", bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(fill="x", padx=16)
        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x", padx=16, pady=(4, 4))
        self.pw_link = tk.StringVar()
        ent = tk.Entry(row, textvariable=self.pw_link, bg=INPUT, fg=FG, insertbackground=FG, relief="flat", font=F["mono_sm"],
                       highlightthickness=1, highlightbackground=LINE)
        ent.pack(side="left", fill="x", expand=True, ipady=5)
        ent.bind("<Return>", lambda _e: self._pw_link_check())
        StudioButton(row, "DENETLE", self._pw_link_check, "secondary", "search", "sm").pack(side="left", padx=(6, 0))
        self.pw_link_res = tk.Label(card, text="Kopyaladığın bağlantılar da pano radarıyla otomatik denetlenir.", bg=PANEL,
                                    fg=DIM, font=F["tiny"], anchor="w", justify="left", wraplength=360)
        self.pw_link_res.pack(fill="x", padx=16, pady=(2, 10))
        tk.Label(card, text="TARAYICI EKLENTİSİ · CHROME · EDGE · BRAVE · OPERA · FIREFOX", bg=PANEL, fg=DIM, font=F["label"],
                 anchor="w").pack(fill="x", padx=16)
        keys = self.prefs.get("browser_keys") or []
        tk.Label(card, text=(f"● {len(keys)} tarayıcı eşleşti: " + ", ".join(k.get("browser", "?") for k in keys)) if keys else
                 "○ Henüz eşleşen tarayıcı yok", bg=PANEL, fg=GREEN if keys else DIM, font=F["mono_xs"], anchor="w",
                 wraplength=360, justify="left").pack(fill="x", padx=16, pady=(4, 0))
        self._wrap(tk.Label(card, text="Eklenti sayfadaki giriş formunu tanır, adres çubuğundaki gerçek alan adını doğrular ve yalnızca "
                            "birebir eşleşen kaydı doldurur; taklit sitelerde kırmızı uyarı gösterir.", bg=PANEL, fg=MUTED,
                            font=F["tiny"], justify="left"), 30).pack(fill="x", padx=16, pady=(4, 0))
        bar = tk.Frame(card, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(8, 14))
        btns = [StudioButton(bar, "EKLENTİYİ KUR", self.pw_install_extension, "accent", "open", "sm")]
        if keys:
            btns.append(StudioButton(bar, "EŞLEŞMELERİ SIFIRLA", lambda: (self.set_pref("browser_keys", []), self._pw_rebuild()),
                                     "ghost", "close", "sm"))
        self._flow(bar, btns)

    def pw_install_extension(self):
        from .runtime import is_frozen, resource_dir
        import sys as _sys
        folder = (Path(_sys.executable).parent / "TarayiciEklentisi") if is_frozen() else (resource_dir() / "browser-extension")
        steps = ("1) Chrome / Edge / Brave adres çubuğuna yaz:  chrome://extensions   (Edge: edge://extensions)\n"
                 "2) Sağ üstteki “Geliştirici modu”nu aç.\n"
                 "3) “Paketlenmemiş öğe yükle” → açılan klasörü seç:\n   " + str(folder) + "\n"
                 "4) Araç çubuğundaki ElfCaesar simgesi → EŞLEŞTİR → uygulamada kodu onayla.\n\n"
                 "Firefox: about:debugging → Bu Firefox → Geçici eklenti yükle → TarayiciEklentisi\\Firefox\\manifest.json "
                 "(Mozilla imzası alınana kadar Firefox kapanınca kaldırılır).\n\n"
                 "Kurulumda “Tarayıcı eklentisi yardımcısı” seçeneği işaretli olmalı (varsayılan).")
        try:
            self.clipboard_clear()
            self.clipboard_append("chrome://extensions")
        except tk.TclError:
            pass
        messagebox.showinfo("Tarayıcı eklentisini kur", steps + "\n\n“chrome://extensions” panoya kopyalandı.", parent=self)
        self._reveal(str(folder / "manifest.json")) if folder.exists() else None

    def _known_domains(self):
        return {e.domain for e in self.pv.entries if e.domain} if self.pv.is_open else set()

    def _pw_link_check(self):
        url = self.pw_link.get().strip()
        if not url:
            return
        hit = pwaudit.lookalike(url, self._known_domains())
        d = registrable_domain(url)
        if hit:
            self.pw_link_res.configure(text=f"✗ SAHTE OLABİLİR: {hit['fake']} → gerçek {hit['real']}. {hit['why']}.", fg=RED)
        elif d in self._known_domains():
            self.pw_link_res.configure(text=f"✓ {d} kasandaki gerçek alan adıyla birebir aynı.", fg=GREEN)
        else:
            self.pw_link_res.configure(text=f"? {d or 'alan adı okunamadı'} kasanda yok; benzerlik bulunmadı.", fg=MUTED)

    def pw_clipboard_guard(self, text):
        """Pano radarı: kopyalanan bağlantı kasadaki bir siteyi taklit ediyorsa uyar."""
        if not text or len(text) > 2000 or not URL_RE.match(text) or "_pv" not in self.__dict__ or not self.pv.is_open:
            return
        hit = pwaudit.lookalike(text.strip(), self._known_domains())
        if hit:
            self.notify("error", "vault", "Oltalama uyarısı: sahte bağlantı",
                        f"{hit['fake']} gerçek {hit['real']} değil · {hit['why']}")

    def quick_fill(self, entry: Entry | None = None):
        if not self.pv.is_open:
            self.deiconify()
            self.show_page("passwords")
            self.notify("info", "vault", "Önce parola kasasını aç", "Ctrl+Alt+P kasa açıkken çalışır")
            return
        hwnd, title = autotype.foreground()
        if hwnd and hwnd == self.winfo_id():
            hwnd, title = 0, ""
        QuickFill(self, hwnd, title, entry)

    # ------------------------------------------------------------ yedek ve senkron
    CLOUD_HINTS = ("onedrive", "dropbox", "google drive", "googledrive", "icloud", "yandex.disk", "mega")

    def _pw_sync_card(self, card):
        if self.pv.decoy:
            tk.Label(card, text="Bu kasada yedekleme ayarı yok.", bg=PANEL, fg=DIM, font=F["small"], anchor="w").pack(
                fill="x", padx=16, pady=(0, 14))
            return
        backups = self.pv.list_backups()
        path_l = str(self.pv.path).casefold()
        cloud = next((h for h in self.CLOUD_HINTS if h in path_l), None)
        conflicts = self.pv.conflict_files()
        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x", padx=16)
        for label, value, col in (
                ("OTOMATİK YEDEK", f"{len(backups)} yedek" + (f" · son: {time.strftime('%d.%m %H:%M', time.localtime(backups[0].stat().st_mtime))}" if backups else ""), GREEN if backups else DIM),
                ("SENKRON", ("● " + cloud.title() + " klasöründe · cihazlar arası birleştirme açık") if cloud else "○ Yalnızca bu bilgisayar", GREEN if cloud else DIM),
                ("ÇAKIŞAN KOPYA", f"{len(conflicts)} dosya" if conflicts else "yok", ORANGE if conflicts else DIM)):
            c = tk.Frame(row, bg=PANEL)
            c.pack(side="left", padx=(0, 30))
            tk.Label(c, text=label, bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(anchor="w")
            tk.Label(c, text=value, bg=PANEL, fg=col, font=F["mono_xs"], anchor="w").pack(anchor="w")
        self._wrap(tk.Label(card, text="Her kaydetmede önceki sürümün şifreli kopyası “yedekler” klasörüne alınır (son 20). Kasayı OneDrive, "
                            "Dropbox veya Google Drive klasörüne taşırsan diğer bilgisayarındaki ElfCaesar aynı kasayı açar; iki cihazdaki "
                            "değişiklikler kayıt kayıt birleştirilir, hiçbir sunucu kullanılmaz ve dosya uçtan uca şifreli kalır.",
                            bg=PANEL, fg=MUTED, font=F["tiny"], justify="left"), 40).pack(fill="x", padx=16, pady=(8, 0))
        bar = tk.Frame(card, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(10, 14))
        btns = [StudioButton(bar, "YEDEKLER", self.pw_backups, "secondary", "history", "sm"),
                StudioButton(bar, "BULUT KLASÖRÜNE TAŞI", self.pw_move_vault, "accent", "open", "sm")]
        if conflicts:
            btns.append(StudioButton(bar, f"ÇAKIŞMALARI BİRLEŞTİR ({len(conflicts)})", self.pw_merge_conflicts, "primary", "swap", "sm"))
        self._flow(bar, btns)

    def pw_backups(self):
        BackupsDialog(self)

    def pw_move_vault(self):
        folder = filedialog.askdirectory(title="Kasanın taşınacağı klasör (ör. OneDrive)")
        if not folder:
            return
        old = self.pv.path
        new = Path(folder) / old.name
        if new.exists():
            messagebox.showwarning("Bulut klasörü", f"Bu klasörde zaten {new.name} var. Diğer cihazdaki kasayı açmak için "
                                   "“BAŞKA KASA DOSYASI” kullan veya önce o dosyayı yeniden adlandır.", parent=self)
            return
        try:
            self.pv.path = new
            self.pv._disk_sig = None
            self.pv.save()
            for side in (old.with_name(old.stem + ".miras.elfvault"),):
                if side.exists():
                    side.replace(new.with_name(side.name))
        except Exception as exc:
            self.pv.path = old
            self.notify("error", "vault", "Kasa taşınamadı", str(exc))
            return
        self.set_pref("pw_vault_path", str(new))
        if messagebox.askyesno("Bulut klasörü", f"Kasa taşındı:\n{new}\n\nEski konumdaki kopya güvenle imha edilsin mi?", parent=self):
            shred.shred_file(old)
        self.notify("success", "vault", "Parola kasası bulut klasörüne taşındı", str(new.parent))
        self._pw_rebuild()

    def pw_merge_conflicts(self):
        total = {"added": 0, "updated": 0, "removed": 0}
        failed = []
        for f in self.pv.conflict_files():
            try:
                r = self.pv.merge_file(f)
                for k in total:
                    total[k] += r.get(k, 0)
                shred.shred_file(f)
            except Exception:
                pw = self._password(purpose=f"{f.name} farklı bir ana parolayla şifrelenmiş. O kopyanın parolasını gir.")
                try:
                    if pw is None:
                        raise ValueError
                    r = self.pv.merge_file(f, pw)
                    for k in total:
                        total[k] += r.get(k, 0)
                    shred.shred_file(f)
                except Exception:
                    failed.append(f.name)
        self.notify("success" if not failed else "warning", "vault", "Çakışan kopyalar birleştirildi",
                    f"{total['added']} yeni · {total['updated']} güncel · {total['removed']} silinen"
                    + (f" · açılamayan: {', '.join(failed)}" if failed else ""))
        self._pw_rebuild()

    # ------------------------------------------------------------ dijital miras
    def _pw_miras_card(self, card):
        m = self.pv.meta.get("miras")
        self._wrap(tk.Label(card, text="Kasanın kurtarma anahtarını parçalara böl ve güvendiğin kişilere ver. Örneğin 5 kişiden "
                            "herhangi 3'ü bir araya gelince kasa açılır; 2 parça tek başına hiçbir şey açıklamaz.",
                            bg=PANEL, fg=MUTED, font=F["small"], justify="left"), 30).pack(fill="x", padx=16)
        status = (f"● Etkin · {m['k']} / {m['n']} · {m['date']}" + (f" · {', '.join(m.get('heirs') or [])}" if m.get("heirs") else "")
                  if m else "○ Kurulmadı")
        tk.Label(card, text=status, bg=PANEL, fg=GREEN if m else DIM, font=F["mono_xs"], anchor="w", wraplength=360,
                 justify="left").pack(fill="x", padx=16, pady=(6, 0))
        if m:
            tk.Label(card, text=f"Miras kasası: {self.pv.miras_path.name} (her kayıtta güncellenir)", bg=PANEL, fg=DIM,
                     font=F["tiny"], anchor="w").pack(fill="x", padx=16)
        bar = tk.Frame(card, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(10, 14))
        btns = [StudioButton(bar, "YENİDEN KUR" if m else "MİRAS KUR", self.pw_miras_setup, "primary" if not m else "secondary", "idcard", "sm")]
        if m:
            btns.append(StudioButton(bar, "KAPAT", self._pw_miras_off, "ghost", "close", "sm"))
        self._flow(bar, btns)

    def pw_miras_setup(self):
        if self.pv.decoy:
            self.notify("warning", "vault", "Bu işlem şu an kullanılamıyor")
            return
        MirasSetupDialog(self)

    def _pw_miras_off(self):
        if messagebox.askyesno("Dijital Miras", "Miras kapatılsın ve miras kasası silinsin mi? Dağıttığın parçalar geçersiz olur.",
                               parent=self, default="no"):
            self.pv.disable_miras()
            self._pw_rebuild()

    def pw_miras_recover(self):
        MirasRecoverDialog(self)

    # ------------------------------------------------------------ baskı parolası
    def _pw_duress_card(self, card):
        on = bool(self.prefs.get("pw_decoy_path")) and Path(self.prefs.get("pw_decoy_path")).exists()
        self._wrap(tk.Label(card, text="Biri seni kasayı açmaya zorlarsa ana parola yerine baskı parolasını gir: içinde yalnızca "
                            "zararsız kayıtlar olan ayrı bir kasa açılır. Ekranda hiçbir fark görünmez.",
                            bg=PANEL, fg=MUTED, font=F["small"], justify="left"), 30).pack(fill="x", padx=16)
        tk.Label(card, text="● Ayarlı" if on else "○ Kurulmadı", bg=PANEL, fg=GREEN if on else DIM, font=F["mono_xs"],
                 anchor="w").pack(fill="x", padx=16, pady=(6, 0))
        bar = tk.Frame(card, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(10, 14))
        btns = [StudioButton(bar, "BASKI PAROLASI KUR" if not on else "YENİDEN KUR", self.pw_duress_setup,
                             "secondary", "lock", "sm")]
        if on:
            btns.append(StudioButton(bar, "KALDIR", self._pw_duress_off, "ghost", "close", "sm"))
        self._flow(bar, btns)

    def pw_duress_setup(self):
        if self.pv.decoy:
            self.notify("warning", "vault", "Bu işlem şu an kullanılamıyor")
            return
        pw = self._password(confirm=True, purpose="BASKI PAROLASI belirle. Ana paroladan farklı olmalı. Bu parolayla, içinde "
                                                  "birkaç zararsız kayıt bulunan sahte bir kasa açılır.")
        if pw is None:
            return
        if self.pv.check_master(pw):
            self.notify("error", "vault", "Baskı parolası ana parolayla aynı olamaz")
            return
        path = self.pv.path.with_name("parola-kasasi.yedek.elfvault")
        d = PasswordVault(path)
        d.create(pw)
        for title, user, url in (("Forum", "kullanici", "https://forum.example.com"), ("Haber sitesi", "okuyucu", "https://haber.example.com"),
                                 ("Tarif sitesi", "mutfak", "https://tarif.example.com")):
            from .secure_gen import random_password
            d.add(Entry(title, user, random_password(), url))
        d.save()
        d.lock()
        self.set_pref("pw_decoy_path", str(path))
        self.notify("success", "vault", "Baskı parolası kuruldu", "Sahte kasa: 3 zararsız kayıt · istersen içine kayıt ekleyebilirsin")
        self._pw_rebuild()

    def _pw_duress_off(self):
        path = self.prefs.get("pw_decoy_path")
        self.set_pref("pw_decoy_path", "")
        if path:
            shred.shred_file(path)
        self._pw_rebuild()

    # ------------------------------------------------------------ kişiye şifreli paylaşım
    def pw_share(self):
        e = self._pw_selected()
        if not e:
            self.notify("warning", "vault", "Önce paylaşılacak kaydı seç")
            return
        contacts = self.book.sorted() if hasattr(self, "book") else []
        if not contacts:
            self.notify("warning", "identity", "Kişi defterin boş", "Mesaj Köprüsü > KİŞİ DEFTERİ ile kişi ekle")
            return
        ShareDialog(self, e, contacts)

    def _pw_send_share(self, e: Entry, contact: dict, note: str):
        if not self.session and not self.session_open():
            return
        from elfcaesar.identity import encrypt_for_contact
        from . import chatarmor as ca
        payload = encrypt_for_contact(share_payload(e, note), contact["card"], self.session["identity"])
        self._set_clipboard(ca.armor_dm(payload))
        self.notify("success", "vault", "Sohbet mesajı şifrelendi",
                    f"“{e.title}” → {contact['alias']} · sohbete yapıştır (Ctrl+V)")

    def receive_shared_password(self, clear: str, sender, trust) -> bool:
        got = parse_share(clear)
        if not got:
            return False
        entry, note = got
        who = (sender or {}).get("name", "imzasız gönderen")
        msg = (f"{who} sana bir parola gönderdi:\n\n{entry.title}\n{entry.username}\n{entry.url}\n"
               + (f"\nNot: {note}\n" if note else "") + f"\nGüven: {trust}\n\nParola kasana eklensin mi?")
        if not self.pv.is_open:
            messagebox.showinfo("Paylaşılan parola", msg.replace("Parola kasana eklensin mi?", "Eklemek için önce parola kasanı aç ve mesajı yeniden çöz."), parent=self)
            return True
        if messagebox.askyesno("Paylaşılan parola", msg, parent=self):
            self.pv.add(entry)
            self._pw_save()
            self.notify("success", "vault", "Paylaşılan parola kasaya eklendi", entry.title)
            self._pw_rebuild()
        return True


# ================================================================== pencereler
class EntryDialog(_Dialog):
    def __init__(self, app, entry: Entry | None, on_save):
        super().__init__(app, "Parola kaydı" if entry else "Yeni parola kaydı")
        self.entry, self.on_save = entry, on_save
        e = entry or Entry("")
        tk.Label(self.body, text="KAYDI DÜZENLE" if entry else "YENİ KAYIT", bg=PANEL, fg=VIOLET, font=F["label"]).pack(anchor="w")
        self.v_title, t = self.field("BAŞLIK", e.title)
        self.v_url, _ = self.field("ADRES (URL)", e.url)
        self.v_user, _ = self.field("KULLANICI ADI / E-POSTA", e.username)
        tk.Label(self.body, text="PAROLA", bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(fill="x", pady=(8, 2))
        row = tk.Frame(self.body, bg=PANEL)
        row.pack(fill="x")
        self.v_pw = tk.StringVar(value=e.password)
        self.pw_e = tk.Entry(row, textvariable=self.v_pw, show="•", bg=INPUT, fg=FG, insertbackground=FG, relief="flat",
                             font=F["mono"], highlightthickness=1, highlightbackground=LINE, highlightcolor=VIOLET)
        self.pw_e.pack(side="left", fill="x", expand=True, ipady=6)
        StudioButton(row, "", self._toggle, "ghost", "search", "sm", tooltip="Göster / gizle").pack(side="left", padx=4)
        StudioButton(row, "ÜRET", self._gen, "secondary", "key", "sm").pack(side="left")
        self.st = tk.Label(self.body, text="", bg=PANEL, fg=MUTED, font=F["tiny"], anchor="w")
        self.st.pack(fill="x", pady=(3, 0))
        self.v_pw.trace_add("write", lambda *_: self._strength())
        if e.pending:
            tk.Label(self.body, text="⟳ Bu kayıt için hazırlanmış, sitede değiştirilmeyi bekleyen yeni bir parola var (DEĞİŞİM PLANI).",
                     bg=PANEL, fg=CYAN, font=F["tiny"], anchor="w").pack(fill="x", pady=(3, 0))
        tk.Label(self.body, text="YENİLEME HATIRLATMASI", bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(fill="x", pady=(8, 2))
        self.rot_labels = [lab for _d, lab in lifecycle.ROTATE_CHOICES]
        cur = dict(lifecycle.ROTATE_CHOICES).get(e.rotate_days, self.rot_labels[0])
        self.v_rot = tk.StringVar(value=cur)
        ttk.Combobox(self.body, textvariable=self.v_rot, values=self.rot_labels, state="readonly", width=30).pack(anchor="w")
        self.v_rec, _ = self.field("KURTARMA E-POSTASI (DOMİNO ANALİZİ İÇİN, İSTEĞE BAĞLI)", e.recovery_email)
        self.v_notes, _ = self.field("NOTLAR", e.notes)
        if entry and entry.history:
            tk.Label(self.body, text=f"Parola geçmişi: {len(entry.history)} eski parola saklanıyor", bg=PANEL, fg=DIM,
                     font=F["tiny"], anchor="w").pack(fill="x", pady=(6, 0))
        bar = tk.Frame(self.body, bg=PANEL)
        bar.pack(fill="x", pady=(16, 0))
        StudioButton(bar, "KAYDET", self._save, "primary", "check", min_width=140).pack(side="right")
        StudioButton(bar, "VAZGEÇ", self.destroy, "ghost").pack(side="right", padx=8)
        self._strength()
        self.center()
        t.focus_set()

    def _toggle(self):
        self.pw_e.configure(show="" if self.pw_e.cget("show") else "•")

    def _gen(self):
        self.v_pw.set(self.app.generate_for(registrable_domain(self.v_url.get()), "kayıt"))
        self.pw_e.configure(show="")

    def _strength(self):
        pw = self.v_pw.get()
        if not pw:
            self.st.configure(text="")
            return
        s = password_strength(pw)
        col = [RED, ORANGE, AMBER, GREEN, CYAN][min(4, s["level"])]
        known = {x.password for x in self.app.pv.entries if not self.entry or x.id != self.entry.id}
        extra = " · BU PAROLA BAŞKA BİR KAYITTA DA VAR" if pw in known else ""
        self.st.configure(text=f"{s['name']} · ≈{s['bits']:.0f} bit · {s['summary']}{extra}", fg=RED if extra else col)

    def _save(self):
        title = self.v_title.get().strip() or registrable_domain(self.v_url.get()) or "Kayıt"
        e = self.entry or Entry(title)
        e.title, e.url, e.username = title, self.v_url.get().strip(), self.v_user.get().strip()
        e.recovery_email, e.notes = self.v_rec.get().strip(), self.v_notes.get()
        e.rotate_days = {lab: d for d, lab in lifecycle.ROTATE_CHOICES}.get(self.v_rot.get(), 0)
        changed = bool(self.entry) and self.v_pw.get() != e.password
        e.set_password(self.v_pw.get())
        if changed:
            if e.pending.get("password") == e.password:
                e.pending = {}
            lifecycle.log_event(self.app.pv.meta, "changed", e, "Elle değiştirildi")
        e.modified = time.time()
        self.destroy()
        self.on_save(e, self.entry is None)


class ImportDialog(_Dialog):
    def __init__(self, app):
        super().__init__(app, "Tarayıcıdan içe aktar")
        tk.Label(self.body, text="TARAYICILARDAN VE YÖNETİCİLERDEN İÇE AKTAR", bg=PANEL, fg=CYAN, font=F["label"]).pack(anchor="w")
        tk.Label(self.body, text="1) Tarayıcında parolaları dışa aktar   2) Oluşan .csv dosyasını seç", bg=PANEL, fg=FG,
                 font=F["h3"]).pack(anchor="w", pady=(4, 8))
        for name, steps in BROWSER_EXPORT_STEPS.items():
            r = tk.Frame(self.body, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=name, bg=INPUT, fg=FG, font=F["body_b"], width=16, anchor="w").pack(side="left", padx=10, pady=5)
            tk.Label(r, text=steps, bg=INPUT, fg=MUTED, font=F["mono_xs"], anchor="w").pack(side="left")
            if name not in ("Bitwarden", "KeePass"):
                addr = steps.split(" ")[0]
                b = tk.Label(r, text="KOPYALA", bg=INPUT, fg=CYAN, font=F["label"], cursor="hand2")
                b.pack(side="right", padx=10)
                b.bind("<Button-1>", lambda _e, a=addr: (app.clipboard_clear(), app.clipboard_append(a),
                                                         app.status(f"{a} panoya kopyalandı · tarayıcının adres çubuğuna yapıştır")))
        self.wipe = tk.BooleanVar(value=True)
        tk.Checkbutton(self.body, text="İçe aktardıktan sonra açık CSV dosyasını güvenle imha et (önerilir)", variable=self.wipe,
                       bg=PANEL, fg=FG_2, selectcolor=INPUT, activebackground=PANEL, activeforeground=FG,
                       font=F["small"]).pack(anchor="w", pady=(12, 0))
        tk.Label(self.body, text="Neden doğrudan tarayıcıdan okumuyoruz? Tarayıcıların şifreli parola veritabanını okumak, parola "
                 "çalan kötü amaçlı yazılımların yöntemidir; modern Chrome ve Edge bunu bilerek engeller. Dışa aktarma dosyası "
                 "senin onayınla oluşur ve işi bitince imha edilir.", bg=PANEL, fg=DIM, font=F["tiny"], wraplength=640,
                 justify="left").pack(anchor="w", pady=(10, 0))
        bar = tk.Frame(self.body, bg=PANEL)
        bar.pack(fill="x", pady=(16, 0))
        StudioButton(bar, "CSV DOSYASINI SEÇ", self._pick, "primary", "open", min_width=180).pack(side="right")
        StudioButton(bar, "VAZGEÇ", self.destroy, "ghost").pack(side="right", padx=8)
        self.center()

    def _pick(self):
        path = filedialog.askopenfilename(parent=self, title="Parola dışa aktarma dosyası (.csv)",
                                          filetypes=[("CSV", "*.csv"), ("Tüm dosyalar", "*.*")])
        if path:
            wipe = self.wipe.get()
            self.destroy()
            self.app._pw_do_import(path, wipe)


class ShareDialog(_Dialog):
    def __init__(self, app, entry, contacts):
        super().__init__(app, "Parolayı kişiye şifreli gönder")
        self.e, self.contacts = entry, contacts
        tk.Label(self.body, text="KİŞİYE ŞİFRELİ GÖNDER · X25519 + ED25519", bg=PANEL, fg=CYAN, font=F["label"]).pack(anchor="w")
        tk.Label(self.body, text=f"“{entry.title}” kaydını kime göndereceksin?", bg=PANEL, fg=FG, font=F["h3"]).pack(anchor="w", pady=(4, 8))
        self.lb = tk.Listbox(self.body, bg=INPUT, fg=FG, selectbackground=mix(CYAN, PANEL, .5), relief="flat", height=min(8, len(contacts)),
                             font=F["body"], highlightthickness=1, highlightbackground=LINE, activestyle="none")
        for c in contacts:
            self.lb.insert("end", f"  {'✓' if c['verified'] else '·'}  {c['alias']}")
        self.lb.pack(fill="x")
        self.lb.selection_set(0)
        self.v_note, _ = self.field("NOT (İSTEĞE BAĞLI)", "")
        tk.Label(self.body, text="Şifreli metin panoya kopyalanır; WhatsApp / Telegram / e-postaya yapıştır. Yalnızca seçtiğin kişi "
                 "açabilir; Mesaj Köprüsü'nde çözünce kasasına eklemesi önerilir.", bg=PANEL, fg=DIM, font=F["tiny"],
                 wraplength=480, justify="left").pack(anchor="w", pady=(8, 0))
        bar = tk.Frame(self.body, bg=PANEL)
        bar.pack(fill="x", pady=(16, 0))
        StudioButton(bar, "ŞİFRELE VE KOPYALA", self._send, "primary", "lock", min_width=180).pack(side="right")
        StudioButton(bar, "VAZGEÇ", self.destroy, "ghost").pack(side="right", padx=8)
        self.center()

    def _send(self):
        sel = self.lb.curselection()
        if not sel:
            return
        c = self.contacts[sel[0]]
        note = self.v_note.get()
        self.destroy()
        self.app._pw_send_share(self.e, c, note)


class MirasSetupDialog(_Dialog):
    def __init__(self, app):
        super().__init__(app, "Dijital Miras")
        tk.Label(self.body, text="DİJİTAL MİRAS · SHAMIR'İN GİZLİ PAYLAŞIMI", bg=PANEL, fg=AMBER, font=F["label"]).pack(anchor="w")
        tk.Label(self.body, text="Kaç kişiye parça vereceksin, kaçı bir araya gelince açılsın?", bg=PANEL, fg=FG,
                 font=F["h3"]).pack(anchor="w", pady=(4, 8))
        row = tk.Frame(self.body, bg=PANEL)
        row.pack(fill="x")
        tk.Label(row, text="EŞİK", bg=PANEL, fg=DIM, font=F["label"]).pack(side="left")
        self.k = 3
        self.n = 5
        Segmented(row, [(2, "2"), (3, "3"), (4, "4")], lambda v: setattr(self, "k", v), 3).pack(side="left", padx=(8, 20))
        tk.Label(row, text="PARÇA", bg=PANEL, fg=DIM, font=F["label"]).pack(side="left")
        Segmented(row, [(3, "3"), (4, "4"), (5, "5"), (7, "7")], lambda v: setattr(self, "n", v), 5).pack(side="left", padx=8)
        self.v_heirs, _ = self.field("KİŞİLER (VİRGÜLLE, İSTEĞE BAĞLI · ör. Annem, Kardeşim, Avukatım)", "")
        tk.Label(self.body, text="Her kişiye bir parça (kısa bir metin) ve miras kasası dosyasını ver. Parçalar ayrı ayrı hiçbir şey "
                 "açmaz. Ana parolan değişse bile miras kasası her kayıtta güncel kalır.", bg=PANEL, fg=DIM, font=F["tiny"],
                 wraplength=520, justify="left").pack(anchor="w", pady=(8, 0))
        bar = tk.Frame(self.body, bg=PANEL)
        bar.pack(fill="x", pady=(16, 0))
        StudioButton(bar, "PARÇALARI ÜRET", self._go, "primary", "idcard", min_width=170).pack(side="right")
        StudioButton(bar, "VAZGEÇ", self.destroy, "ghost").pack(side="right", padx=8)
        self.center()

    def _go(self):
        k, n = self.k, self.n
        if k > n:
            messagebox.showerror("Dijital Miras", "Eşik, parça sayısından büyük olamaz.", parent=self)
            return
        heirs = [h.strip() for h in self.v_heirs.get().split(",") if h.strip()]
        parts = self.app.pv.setup_miras(k, n, heirs)
        self.destroy()
        SharesWindow(self.app, parts, k, n, heirs)
        self.app.notify("success", "vault", "Dijital Miras kuruldu", f"{k} / {n} parça · {self.app.pv.miras_path.name}")
        self.app._pw_rebuild()


class SharesWindow(_Dialog):
    def __init__(self, app, parts, k, n, heirs):
        super().__init__(app, "Miras parçaları")
        tk.Label(self.body, text=f"MİRAS PARÇALARI · HERHANGİ {k} / {n}", bg=PANEL, fg=AMBER, font=F["label"]).pack(anchor="w")
        tk.Label(self.body, text="Her parçayı ayrı bir kişiye ver. Bu pencere kapanınca parçalar bir daha gösterilmez.",
                 bg=PANEL, fg=FG, font=F["body_b"]).pack(anchor="w", pady=(4, 8))
        self.parts = parts
        for i, p in enumerate(parts):
            who = heirs[i] if i < len(heirs) else f"Kişi {i + 1}"
            r = tk.Frame(self.body, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=who, bg=INPUT, fg=AMBER, font=F["body_b"], width=12, anchor="w").pack(side="left", padx=10)
            t = tk.Text(r, height=2, width=62, bg=INPUT, fg=FG_2, font=F["mono_xs"], relief="flat", wrap="char")
            t.insert("1.0", p)
            t.configure(state="disabled")
            t.pack(side="left", pady=4)
            StudioButton(r, "KOPYALA", lambda p=p: app.guarded_copy(p), "ghost", "copy", "sm").pack(side="right", padx=6)
        bar = tk.Frame(self.body, bg=PANEL)
        bar.pack(fill="x", pady=(14, 0))
        StudioButton(bar, "YAZDIRILABİLİR SAYFALAR", lambda: self._print(heirs, k, n), "accent", "export").pack(side="left")
        StudioButton(bar, "TAMAM", self.destroy, "primary", min_width=120).pack(side="right")
        self.center()

    def _print(self, heirs, k, n):
        import html as H
        out = filedialog.asksaveasfilename(parent=self, title="Miras sayfalarını kaydet", defaultextension=".html",
                                           initialfile="ElfCaesar-Miras-Parcalari.html", filetypes=[("HTML", "*.html")])
        if not out:
            return
        pages = "".join(
            f"<section><h1>ElfCaesar Dijital Miras</h1><p class='who'>{H.escape(heirs[i] if i < len(heirs) else f'Kişi {i + 1}')} için · "
            f"Parça {i + 1} / {n}</p><pre>{H.escape(p)}</pre><p>Bu parça tek başına hiçbir şey açmaz. Parola kasası, "
            f"<b>{k}</b> farklı parça ve <code>{H.escape(self.app.pv.miras_path.name)}</code> dosyası bir araya getirilince "
            f"ElfCaesar Studio → Parola Kasası → MİRASTAN KURTAR ile açılır.</p><p class='d'>{time.strftime('%d.%m.%Y')}</p></section>"
            for i, p in enumerate(self.parts))
        Path(out).write_text(
            "<!doctype html><meta charset='utf-8'><title>Miras parçaları</title><style>body{font:12pt Segoe UI,Arial;margin:0}"
            "section{page-break-after:always;padding:30mm 22mm}h1{font-size:20pt;margin:0}.who{color:#a96a12;font-weight:700}"
            "pre{white-space:pre-wrap;word-break:break-all;font:13pt Consolas,monospace;border:2px solid #222;padding:12px}"
            ".d{color:#666}</style>" + pages, encoding="utf-8")
        self.app._open_in_browser(Path(out))


class MirasRecoverDialog(_Dialog):
    def __init__(self, app):
        super().__init__(app, "Mirastan kurtar")
        tk.Label(self.body, text="MİRASTAN KURTAR", bg=PANEL, fg=AMBER, font=F["label"]).pack(anchor="w")
        tk.Label(self.body, text="Miras kasası dosyasını seç ve yeterli sayıda parçayı her satıra bir tane yapıştır.",
                 bg=PANEL, fg=FG, font=F["body_b"]).pack(anchor="w", pady=(4, 8))
        row = tk.Frame(self.body, bg=PANEL)
        row.pack(fill="x")
        self.v_file = tk.StringVar()
        tk.Entry(row, textvariable=self.v_file, bg=INPUT, fg=FG, relief="flat", font=F["mono_xs"], width=56,
                 highlightthickness=1, highlightbackground=LINE).pack(side="left", fill="x", expand=True, ipady=5)
        StudioButton(row, "SEÇ", self._pick, "secondary", "open", "sm").pack(side="left", padx=6)
        self.t = tk.Text(self.body, height=7, width=72, bg=INPUT, fg=FG, insertbackground=FG, font=F["mono_xs"], relief="flat",
                         highlightthickness=1, highlightbackground=LINE)
        self.t.pack(fill="x", pady=(8, 0))
        bar = tk.Frame(self.body, bg=PANEL)
        bar.pack(fill="x", pady=(14, 0))
        StudioButton(bar, "KURTAR", self._go, "primary", "unlock", min_width=140).pack(side="right")
        StudioButton(bar, "VAZGEÇ", self.destroy, "ghost").pack(side="right", padx=8)
        self.center()

    def _pick(self):
        p = filedialog.askopenfilename(parent=self, title="Miras kasası", filetypes=[("Miras kasası", "*.miras.elfvault"), ("ELF Vault", "*.elfvault")])
        if p:
            self.v_file.set(p)

    def _go(self):
        lines = [l for l in self.t.get("1.0", "end").splitlines() if l.strip()]
        try:
            entries = PasswordVault.recover_miras(Path(self.v_file.get()), lines)
        except Exception as exc:
            messagebox.showerror("Mirastan kurtar", str(exc), parent=self)
            return
        app = self.app
        self.destroy()
        target = filedialog.asksaveasfilename(parent=app, title="Kurtarılan kasayı kaydet", defaultextension=".elfvault",
                                              initialfile="kurtarilan-parola-kasasi.elfvault", filetypes=[("ELF Vault", "*.elfvault")])
        if not target:
            return
        pw = app._password(confirm=True, purpose=f"{len(entries)} kayıt kurtarıldı. Yeni kasa için yeni bir ANA PAROLA belirle.")
        if pw is None:
            return
        v = PasswordVault(Path(target))
        v.create(pw)
        v.entries = entries
        v.save()
        v.lock()
        app.set_pref("pw_vault_path", target)
        app.__dict__.pop("_pv", None)
        app.notify("success", "vault", "Parola kasası mirastan kurtarıldı", f"{len(entries)} kayıt · {Path(target).name}")
        app._pw_rebuild()


class BackupsDialog(_Dialog):
    def __init__(self, app):
        super().__init__(app, "Parola kasası yedekleri")
        tk.Label(self.body, text="OTOMATİK YEDEKLER · EN YENİ ÜSTTE", bg=PANEL, fg=GREEN, font=F["label"]).pack(anchor="w")
        self.items = app.pv.list_backups()
        tk.Label(self.body, text=str(app.pv.backup_dir), bg=PANEL, fg=DIM, font=F["mono_xs"]).pack(anchor="w", pady=(2, 8))
        self.lb = tk.Listbox(self.body, bg=INPUT, fg=FG, selectbackground=mix(GREEN, PANEL, .5), relief="flat", height=10,
                             width=60, font=F["mono_sm"], highlightthickness=1, highlightbackground=LINE, activestyle="none")
        for p in self.items:
            st = p.stat()
            self.lb.insert("end", f"  {time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(st.st_mtime))}   ·   {st.st_size // 1024 or 1} KB")
        if not self.items:
            self.lb.insert("end", "  Henüz yedek yok · ilk değişiklikte oluşur")
        self.lb.pack(fill="x")
        tk.Label(self.body, text="Geri yüklerken yedeğin oluşturulduğu andaki ana parola sorulur. Şu anki kasa da önce yedeklenir.",
                 bg=PANEL, fg=DIM, font=F["tiny"], wraplength=520, justify="left").pack(anchor="w", pady=(8, 0))
        bar = tk.Frame(self.body, bg=PANEL)
        bar.pack(fill="x", pady=(14, 0))
        StudioButton(bar, "GERİ YÜKLE", self._restore, "primary", "unlock", min_width=140).pack(side="right")
        StudioButton(bar, "KAPAT", self.destroy, "ghost").pack(side="right", padx=8)
        self.center()

    def _restore(self):
        sel = self.lb.curselection()
        if not sel or not self.items:
            return
        p = self.items[sel[0]]
        app = self.app
        self.destroy()
        pw = app._password(purpose="Bu yedeğin oluşturulduğu andaki ana parolayı gir.")
        if pw is None:
            return
        try:
            n = app.pv.restore_backup(p, pw)
        except Exception as exc:
            app.notify("error", "vault", "Yedek geri yüklenemedi", str(exc))
            return
        app.notify("success", "vault", "Yedek geri yüklendi", f"{n} kayıt · {p.name}")
        app._pw_rebuild()


class QuickFill(tk.Toplevel):
    """Ctrl+Alt+P penceresi: öneriler + otomatik tamamlamalı arama; seçilen kaydı hedef pencereye yazar."""

    def __init__(self, app, hwnd, title, entry=None):
        super().__init__(app)
        self.app, self.hwnd, self.target_title = app, hwnd, title
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.configure(bg=VIOLET)
        body = tk.Frame(self, bg=PANEL)
        body.pack(padx=1, pady=1)
        head = tk.Frame(body, bg=PANEL)
        head.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(head, text="HIZLI DOLDUR", bg=PANEL, fg=VIOLET, font=F["label"]).pack(side="left")
        tk.Label(head, text="Enter yaz · Shift+Enter yaz ve gönder · Esc", bg=PANEL, fg=DIM, font=F["tiny"]).pack(side="right")
        tk.Label(body, text=("Hedef: " + (title[:70] or "—")), bg=PANEL, fg=MUTED, font=F["tiny"], anchor="w").pack(fill="x", padx=14)
        self.q = tk.StringVar()
        self.e = tk.Entry(body, textvariable=self.q, bg=INPUT, fg=FG, insertbackground=FG, relief="flat", font=F["body"], width=48,
                          highlightthickness=1, highlightbackground=LINE, highlightcolor=VIOLET)
        self.e.pack(fill="x", padx=14, pady=(8, 6), ipady=6)
        self.lb = tk.Listbox(body, bg=INPUT, fg=FG_2, selectbackground=mix(VIOLET, PANEL, .45), relief="flat", height=6, font=F["body"],
                             highlightthickness=0, activestyle="none")
        self.lb.pack(fill="x", padx=14)
        self.warn = tk.Label(body, text="", bg=PANEL, fg=AMBER, font=F["tiny"], anchor="w", wraplength=420, justify="left")
        self.warn.pack(fill="x", padx=14, pady=(6, 0))
        self.mode = "both"
        seg = tk.Frame(body, bg=PANEL)
        seg.pack(fill="x", padx=14, pady=(6, 12))
        Segmented(seg, [("both", "KULLANICI + PAROLA"), ("user", "KULLANICI"), ("pass", "PAROLA")],
                  lambda v: setattr(self, "mode", v), "both").pack(side="left")
        self.matches = app.pv.for_window(title) if title else []
        self.items: list[Entry] = []
        self.q.trace_add("write", lambda *_: self._refresh())
        self.e.bind("<Down>", lambda _e: self._move(1))
        self.e.bind("<Up>", lambda _e: self._move(-1))
        self.e.bind("<Return>", lambda _e: self._go(False))
        self.e.bind("<Shift-Return>", lambda _e: self._go(True))
        self.e.bind("<Tab>", lambda _e: (self._complete(), "break")[1])
        self.bind("<Escape>", lambda _e: self.destroy())
        self.lb.bind("<Double-1>", lambda _e: self._go(False))
        if entry is not None:
            self.items = [entry]
            self.lb.insert("end", f"  {entry.title}  ·  {entry.username}")
            self.lb.selection_set(0)
        else:
            self._refresh()
        if title and not self.matches:
            self.warn.configure(text="Bu pencere kasandaki hiçbir siteyle eşleşmedi. Adres çubuğundaki alan adını kontrol et; "
                                     "benzer görünen sahte siteler parolanı çalabilir.")
        self.update_idletasks()
        pos = None
        try:
            from . import winbridge
            pos = winbridge.cursor_pos()
        except Exception:
            pass
        x, y = pos or (app.winfo_rootx() + 200, app.winfo_rooty() + 160)
        self.geometry(f"+{max(0, x - 40)}+{max(0, y + 16)}")
        self.focus_force()
        self.e.focus_set()

    def _refresh(self):
        q = self.q.get()
        items = self.app.pv.search(q) if q else (self.matches or self.app.pv.search(""))
        self.items = items[:8]
        self.lb.delete(0, "end")
        for x in self.items:
            mark = "★ " if x in self.matches else "  "
            self.lb.insert("end", f"{mark}{x.title}  ·  {x.username}  ·  {x.domain}")
        if self.items:
            self.lb.selection_set(0)

    def _move(self, d):
        cur = (self.lb.curselection() or (0,))[0]
        nxt = max(0, min(self.lb.size() - 1, cur + d))
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(nxt)
        return "break"

    def _complete(self):
        s = self.app.pv.suggest(self.q.get(), 1)
        if s:
            self.q.set(s[0])
            self.e.icursor("end")

    def _go(self, submit):
        sel = self.lb.curselection()
        if not sel or sel[0] >= len(self.items):
            return
        entry = self.items[sel[0]]
        steps = autotype.sequence(entry, self.mode, submit)
        hwnd = self.hwnd
        self.destroy()
        entry.used = time.time()
        self.app._pw_save()
        if not autotype.IS_WINDOWS or not hwnd:
            self.app.guarded_copy(entry.password)
            self.app.notify("info", "vault", "Parola panoya kopyalandı", "Otomatik yazma yalnızca Windows'ta")
            return

        def run():
            if autotype.perform_to(hwnd, steps):
                self.app.notify("success", "vault", "Hızlı Doldur", entry.title, toast=False)
            else:
                self.app.guarded_copy(entry.password)
                self.app.notify("warning", "vault", "Hedef pencere öne getirilemedi",
                                "Güvenlik için hiçbir şey yazılmadı · parola pano korumasıyla kopyalandı")
        self.app.after(120, run)
