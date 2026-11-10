"""KVKK Kalkanı sayfası, kâğıt kurtarma kitapçığı ve ekran görüntüsü kalkanı (Studio'ya karıştırılan arayüz katmanı)."""
from __future__ import annotations

import base64
import os
import queue
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from elfcaesar.identity import load_identity
from elfcaesar.secure import encrypt_file, open_bytes

from . import capture, kvkk
from . import paperbackup as pb
from .chatarmor import armor_contact, safety_words
from .theme import F, BG, PANEL, INPUT, LINE, LINE_2, FG, FG_2, MUTED, DIM, AMBER, CYAN, GREEN, RED, ORANGE, mix
from .widgets import StudioButton, Segmented

LEVEL_TR = {"high": "YÜKSEK", "medium": "ORTA", "low": "DÜŞÜK"}
LEVEL_COLOR = {"high": RED, "medium": AMBER, "low": CYAN}


class ProMixin:
    # ------------------------------------------------------------ yardımcılar
    def _signature_b64(self) -> str:
        try:
            from .runtime import resource_dir
            return base64.b64encode((resource_dir() / "assets" / "dante_sig_300.png").read_bytes()).decode()
        except OSError:
            return ""

    def _open_in_browser(self, path: Path):
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                webbrowser.open(path.resolve().as_uri())
        except Exception:
            pass

    def _reveal(self, path: str):
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            else:
                webbrowser.open(Path(path).parent.resolve().as_uri())
        except Exception as exc:
            self.notify("error", "file", "Klasör açılamadı", str(exc))

    # ------------------------------------------------------------ ekran görüntüsü kalkanı
    def shield(self, window, sensitive=True):
        mode = self.prefs.get("capture_shield", "sensitive")
        if mode == "all" or (mode == "sensitive" and sensitive):
            capture.protect(window, True)

    def apply_capture_mode(self):
        mode = self.prefs.get("capture_shield", "sensitive")
        capture.protect(self, mode == "all")

    # ------------------------------------------------------------ kâğıt kurtarma kitapçığı (6.8.3)
    def make_paper_backup(self):
        path = filedialog.askopenfilename(title="Yedeklenecek kimlik kasası (.elfid)", filetypes=[("ELF Identity", "*.elfid")],
                                          initialfile=Path(self.prefs.get("identity_path") or "").name or None)
        if not path:
            return
        pw = self._password(purpose="Kitapçık oluşturmadan önce parolanı doğrula. Parola kitapçığa YAZILMAZ; "
                                    "unutursan yedek de açılmaz, bu yüzden şimdi kontrol ediyoruz.")
        if pw is None:
            return
        try:
            identity = load_identity(path, pw)
        except Exception as exc:
            self.notify("error", "identity", "Kimlik açılamadı", str(exc))
            return
        raw = Path(path).read_bytes()
        contact = identity["contact"]
        doc = pb.make_html(raw, contact, safety_words(contact["fingerprint"]), armor_contact(contact),
                           self._app_version_full(), self._signature_b64())
        safe = "".join(ch for ch in contact["name"] if ch.isalnum() or ch in " -_").strip() or "kimlik"
        out = filedialog.asksaveasfilename(title="Kurtarma kitapçığını kaydet", defaultextension=".html",
                                           initialfile=f"ElfCaesar-Kurtarma-{safe}.html", filetypes=[("HTML", "*.html")])
        if not out:
            return
        Path(out).write_text(doc, encoding="utf-8")
        self.prefs["paper_backup_date"] = time.strftime("%d.%m.%Y")
        from .settings import save
        save(self.prefs)
        self.sec.paper_backup = True
        self.refresh_security()
        self.notify("success", "identity", "Kurtarma kitapçığı hazır", "Tarayıcıda açıldı · Yazdır (Ctrl+P) veya PDF olarak kaydet")
        self._open_in_browser(Path(out))

    def restore_paper_backup(self):
        win = tk.Toplevel(self)
        win.title("Kitapçıktan geri yükle")
        win.configure(bg=PANEL)
        win.transient(self)
        self.shield(win)
        body = tk.Frame(win, bg=PANEL)
        body.pack(fill="both", expand=True, padx=22, pady=18)
        tk.Label(body, text="Kitapçıktan geri yükle", bg=PANEL, fg=FG, font=F["h2"]).pack(anchor="w")
        tk.Label(body, text="QR kodundan okunan metni (ELFBACKUP1:…) veya numaralı satırları aşağıya yapıştır ya da yaz.",
                 bg=PANEL, fg=MUTED, font=F["small"]).pack(anchor="w", pady=(2, 10))
        box = tk.Frame(body, bg=INPUT, highlightthickness=1, highlightbackground=LINE_2, highlightcolor=CYAN)
        box.pack(fill="both", expand=True)
        text = tk.Text(box, width=72, height=16, bg=INPUT, fg=FG, insertbackground=AMBER, relief="flat", font=F["mono_sm"],
                       padx=10, pady=8, highlightthickness=0)
        text.pack(fill="both", expand=True)
        status = tk.Label(body, text="", bg=PANEL, fg=MUTED, font=F["small"], anchor="w")
        status.pack(fill="x", pady=(8, 0))

        def do_restore():
            try:
                data = pb.decode_text(text.get("1.0", "end"))
            except pb.BackupError as exc:
                status.configure(text="✕ " + str(exc), fg=RED)
                return
            if not pb.looks_like_identity(data):
                status.configure(text="✕ Çözülen veri bir ElfCaesar kimlik kasası değil.", fg=RED)
                return
            out = filedialog.asksaveasfilename(parent=win, title="Kimlik kasasını kaydet", defaultextension=".elfid",
                                               initialfile="geri-yuklenen-kimlik.elfid", filetypes=[("ELF Identity", "*.elfid")])
            if not out:
                return
            Path(out).write_bytes(data)
            win.destroy()
            pw = self._password(purpose="Geri yüklenen kimliği doğrulamak için parolanı gir.")
            if pw is None:
                self.notify("info", "identity", "Kimlik dosyası geri yüklendi", "Parola doğrulaması atlandı")
                return
            try:
                identity = load_identity(out, pw)
                self.prefs["identity_path"] = out
                self.notify("success", "identity", "Kimlik geri yüklendi ve doğrulandı", identity["contact"]["name"])
            except Exception as exc:
                self.notify("error", "identity", "Dosya geri yüklendi ama parola ile açılamadı", str(exc))
        bar = tk.Frame(body, bg=PANEL)
        bar.pack(fill="x", pady=(12, 0))
        StudioButton(bar, "GERİ YÜKLE", do_restore, "primary", "unlock", min_width=150).pack(side="right")
        StudioButton(bar, "VAZGEÇ", win.destroy, "ghost").pack(side="right", padx=8)
        text.focus_set()

    # ------------------------------------------------------------ KVKK Kalkanı (6.9.0)
    def _page_kvkk(self):
        self._page_intro("10 / KVKK KALKANI · KURUMSAL", "Kişisel veri envanteri ve koruma",
                         "Seçtiğin klasörlerdeki belgelerde T.C. kimlik, IBAN, kart, telefon, e-posta ve parola ifadelerini bulur; "
                         "riskli dosyaları tek tıkla kasaya alır ve yazdırılabilir envanter raporu üretir. Bulunan değerler hiçbir "
                         "yere kaydedilmez ve ekrana yazılmaz; yalnızca tür ve adet gösterilir.", GREEN, "BETA", "search")
        self.kv_roots = getattr(self, "kv_roots", [])
        self.kv_result = getattr(self, "kv_result", None)
        scan = self._card(self.content, "01 / TARAMA", "TXT · CSV · JSON · XML · HTML · EML · DOCX · XLSX · PPTX · ODT", "search", GREEN)
        scan.pack(fill="x", pady=(0, 12))
        self.kv_roots_box = tk.Frame(scan, bg=PANEL)
        self.kv_roots_box.pack(fill="x", padx=16, pady=(0, 8))
        bar = tk.Frame(scan, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(0, 8))
        self.kv_start = StudioButton(bar, "TARAMAYI BAŞLAT", self.kvkk_start, "primary", "search")
        self.kv_stop = StudioButton(bar, "DURDUR", self.kvkk_stop, "danger", "close")
        self.kv_stop.set_enabled(False)
        self._flow(bar, [StudioButton(bar, "KLASÖR EKLE", self.kvkk_add_folder, "secondary", "open"),
                         StudioButton(bar, "BELGELER", lambda: self.kvkk_add_known("Documents"), "ghost", "file"),
                         StudioButton(bar, "MASAÜSTÜ", lambda: self.kvkk_add_known("Desktop"), "ghost", "file"),
                         StudioButton(bar, "İNDİRİLENLER", lambda: self.kvkk_add_known("Downloads"), "ghost", "file"),
                         self.kv_start, self.kv_stop])
        self.kv_prog = tk.Canvas(scan, height=6, bg=PANEL, highlightthickness=0)
        self.kv_prog.pack(fill="x", padx=16)
        self.kv_status = tk.Label(scan, text="Taramak için klasör ekle.", bg=PANEL, fg=MUTED, font=F["mono_xs"], anchor="w")
        self.kv_status.pack(fill="x", padx=16, pady=(4, 14))
        self.kv_tiles = tk.Frame(self.content, bg=BG)
        self.kv_tiles.pack(fill="x", pady=(0, 12))
        res = self._card(self.content, "02 / BULGULAR", "DEĞERLER GÖSTERİLMEZ · YALNIZCA TÜR VE ADET", "alert", AMBER)
        res.pack(fill="both", expand=True, pady=(0, 12))
        tools = tk.Frame(res, bg=PANEL)
        tools.pack(fill="x", padx=16, pady=(0, 8))
        self.kv_filter = Segmented(tools, [("all", "TÜMÜ"), ("high", "YÜKSEK"), ("medium", "ORTA"), ("low", "DÜŞÜK")],
                                   lambda _k: self._kvkk_render())
        self.kv_filter.pack(side="left")
        acts = tk.Frame(tools, bg=PANEL)
        acts.pack(side="right")
        StudioButton(acts, "KASAYA AL", self.kvkk_protect, "primary", "lock", "sm").pack(side="left", padx=3)
        StudioButton(acts, "KLASÖRDE GÖSTER", self.kvkk_reveal, "secondary", "open", "sm").pack(side="left", padx=3)
        StudioButton(acts, "ENVANTER RAPORU", self.kvkk_report, "accent", "export", "sm").pack(side="left", padx=3)
        wrap = tk.Frame(res, bg=PANEL)
        wrap.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.kv_tree = ttk.Treeview(wrap, columns=("risk", "file", "types", "size", "date"), show="headings", height=12,
                                    selectmode="extended")
        for col, text, width, stretch in (("risk", "RİSK", 80, False), ("file", "DOSYA", 420, True), ("types", "VERİ TÜRLERİ", 300, True),
                                          ("size", "BOYUT", 80, False), ("date", "DEĞİŞİKLİK", 100, False)):
            self.kv_tree.heading(col, text=text, anchor="w")
            self.kv_tree.column(col, width=width, stretch=stretch, anchor="w")
        for lvl, col in LEVEL_COLOR.items():
            self.kv_tree.tag_configure(lvl, foreground=col)
        self.kv_tree.tag_configure("done", foreground=GREEN)
        ysb = ttk.Scrollbar(wrap, orient="vertical", command=self.kv_tree.yview)
        self.kv_tree.configure(yscrollcommand=ysb.set)
        self.kv_tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        self.kv_tree.bind("<Double-1>", lambda _e: self.kvkk_reveal())
        note = tk.Frame(self.content, bg=mix(AMBER, BG, .9), highlightthickness=1, highlightbackground=mix(AMBER, BG, .65))
        note.pack(fill="x")
        self._wrap(tk.Label(note, text="Otomatik tespit hatalı sonuç verebilir; T.C. kimlik ve kart numaraları sağlama algoritmasıyla "
                            "doğrulanır. Bu araç ve raporu hukuki görüş değildir; KVKK uyumu için hukuk danışmanına başvurun. "
                            "Taranan klasörler ve sonuçlar uygulama kapanınca bellekten silinir.", bg=note.cget("bg"), fg=AMBER,
                            font=F["tiny"], justify="left"), 30).pack(fill="x", padx=14, pady=10)
        self.kv_done = getattr(self, "kv_done", set())
        self._kvkk_render_roots()
        self._kvkk_render()

    def kvkk_add_folder(self):
        path = filedialog.askdirectory(title="Taranacak klasör")
        if path and path not in self.kv_roots:
            self.kv_roots.append(path)
            self._kvkk_render_roots()

    def kvkk_add_known(self, name):
        path = Path.home() / name
        if path.exists() and str(path) not in self.kv_roots:
            self.kv_roots.append(str(path))
            self._kvkk_render_roots()
        elif not path.exists():
            self.notify("warning", "file", f"{name} klasörü bulunamadı", str(path))

    def _kvkk_render_roots(self):
        f = self.kv_roots_box
        for ch in f.winfo_children():
            ch.destroy()
        if not self.kv_roots:
            tk.Label(f, text="Henüz klasör eklenmedi.", bg=PANEL, fg=DIM, font=F["small"]).pack(anchor="w")
            return
        for r in self.kv_roots:
            row = tk.Frame(f, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            row.pack(fill="x", pady=2)
            tk.Label(row, text="▸  " + r, bg=INPUT, fg=FG_2, font=F["mono_xs"], anchor="w").pack(side="left", fill="x", expand=True, padx=8, pady=5)
            StudioButton(row, "", lambda r=r: (self.kv_roots.remove(r), self._kvkk_render_roots()), "ghost", "close", "sm").pack(side="right")

    def kvkk_start(self):
        if not self.kv_roots:
            self.notify("warning", "file", "Önce taranacak klasör ekle")
            return
        self.kv_cancel = threading.Event()
        self.kv_queue: queue.Queue = queue.Queue()
        self.kv_start.set_enabled(False)
        self.kv_stop.set_enabled(True)
        self.kv_done = set()
        roots = list(self.kv_roots)

        def work():
            res = kvkk.scan(roots, self.kv_cancel, lambda r, p: self.kv_queue.put(("progress", r.files_seen, r.files_scanned,
                                                                                         len(r.findings), p)))
            self.kv_queue.put(("done", res))
        threading.Thread(target=work, name="KvkkScan", daemon=True).start()
        self.log.add("file", "info", "KVKK taraması başladı", f"{len(roots)} konum")
        self.after(120, self._kvkk_poll)

    def kvkk_stop(self):
        if getattr(self, "kv_cancel", None):
            self.kv_cancel.set()

    def _kvkk_poll(self):
        last = None
        try:
            while True:
                last = self.kv_queue.get_nowait()
                if last[0] == "done":
                    break
        except queue.Empty:
            pass
        if last and last[0] == "progress" and self.kv_status.winfo_exists():
            _k, seen, scanned, found, p = last
            self.kv_status.configure(text=f"{seen:,} dosya görüldü · {scanned:,} tarandı · {found} bulgu · {Path(p).name[:60]}".replace(",", "."))
            self._kvkk_bar((seen % 200) / 200)
        if last and last[0] == "done":
            self.kv_result = res = last[1]
            if self.kv_status.winfo_exists():
                self.kv_start.set_enabled(True)
                self.kv_stop.set_enabled(False)
                self._kvkk_bar(1)
                self.kv_status.configure(text=f"{'Durduruldu' if res.cancelled else 'Tamamlandı'} · {res.files_seen:,} dosya · "
                                              f"{res.files_scanned:,} tarandı · {len(res.findings)} dosyada kişisel veri · "
                                              f"{(res.finished - res.started):.1f} sn".replace(",", "."))
                self._kvkk_render()
            lv = res.by_level()
            self.notify("warning" if lv["high"] else "success", "file", "KVKK taraması tamamlandı",
                        f"{len(res.findings)} dosyada kişisel veri · {lv['high']} yüksek risk")
            return
        self.after(150, self._kvkk_poll)

    def _kvkk_bar(self, k):
        c = self.kv_prog
        if not c.winfo_exists():
            return
        c.delete("all")
        w = c.winfo_width()
        c.create_rectangle(0, 0, w, 6, fill=INPUT, outline="")
        c.create_rectangle(0, 0, w * k, 6, fill=GREEN, outline="")

    def _kvkk_render(self):
        if not hasattr(self, "kv_tree") or not self.kv_tree.winfo_exists():
            return
        for ch in self.kv_tiles.winfo_children():
            ch.destroy()
        self.kv_tiles._cols = None
        res = self.kv_result
        totals = res.totals() if res else {}
        lv = res.by_level() if res else {"high": 0, "medium": 0, "low": 0}
        specs = [("TARANAN DOSYA", f"{res.files_scanned:,}".replace(",", ".") if res else "—", CYAN),
                 ("KİŞİSEL VERİ İÇEREN", str(len(res.findings)) if res else "—", AMBER),
                 ("YÜKSEK RİSK", str(lv["high"]) if res else "—", RED),
                 ("T.C. KİMLİK", str(totals.get("tckn", 0)) if res else "—", ORANGE),
                 ("FİNANS (KART + IBAN)", str(totals.get("card", 0) + totals.get("iban", 0)) if res else "—", ORANGE),
                 ("KASAYA ALINAN", str(len(self.kv_done)), GREEN)]
        tiles = []
        for label, value, col in specs:
            t = tk.Frame(self.kv_tiles, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            tk.Frame(t, bg=col, height=2).pack(fill="x")
            tk.Label(t, text=label, bg=PANEL, fg=MUTED, font=F["label"]).pack(anchor="w", padx=12, pady=(8, 0))
            tk.Label(t, text=value, bg=PANEL, fg=FG, font=F["metric"]).pack(anchor="w", padx=12, pady=(0, 8))
            tiles.append(t)
        self._auto_grid(self.kv_tiles, tiles, 170, 6, gap=10)
        self.kv_tree.delete(*self.kv_tree.get_children())
        if not res:
            return
        flt = self.kv_filter.value
        for i, f in enumerate(res.findings):
            if flt != "all" and f.level != flt:
                continue
            done = f.path in self.kv_done
            self.kv_tree.insert("", "end", iid=str(i), tags=("done" if done else f.level,),
                                values=("KORUNDU" if done else LEVEL_TR[f.level], kvkk.display_path(f.path, res.roots), f.summary,
                                        kvkk.human_size(f.size), time.strftime("%d.%m.%Y", time.localtime(f.mtime))))

    def _kvkk_selected(self):
        if not self.kv_result:
            return []
        return [self.kv_result.findings[int(i)] for i in self.kv_tree.selection()]

    def kvkk_reveal(self):
        sel = self._kvkk_selected()
        if sel:
            self._reveal(sel[0].path)

    def kvkk_protect(self):
        sel = [f for f in self._kvkk_selected() if f.path not in self.kv_done]
        if not sel:
            self.notify("warning", "file", "Önce listeden dosya seç", "Ctrl/Shift ile birden çok dosya seçebilirsin")
            return
        pw = self._password(confirm=True, purpose=f"{len(sel)} dosya aynı parolayla AES-256-GCM kasasına alınacak "
                                                  "(her biri yanına .elfvault olarak). Parolayı güvenli bir yerde sakla.")
        if pw is None:
            return
        ok, failed = [], []
        for i, f in enumerate(sel, start=1):
            self.kv_status.configure(text=f"Kasaya alınıyor {i}/{len(sel)} · {Path(f.path).name}")
            self.update_idletasks()
            src, dst = Path(f.path), Path(f.path + ".elfvault")
            try:
                if dst.exists():
                    raise FileExistsError(f"{dst.name} zaten var")
                original = src.read_bytes()
                encrypt_file(src, dst, pw)
                clear, _h = open_bytes(dst.read_bytes(), pw)  # doğrulama: şifreli kopya açılabiliyor mu?
                if clear != original:
                    raise ValueError("doğrulama başarısız")
                ok.append(f)
            except Exception as exc:
                failed.append((f, str(exc)))
        delete = False
        if ok:
            delete = messagebox.askyesno(
                "Orijinal dosyalar",
                f"{len(ok)} dosyanın şifreli kopyası oluşturuldu ve doğrulandı.\n\nOrijinal (şifresiz) dosyalar silinsin mi?\n\n"
                "Not: SSD ve bulut eşitlemeli klasörlerde silinen dosyanın izleri kalabilir; güvenli silme garanti edilemez.",
                default="no", parent=self)
        removed = 0
        for f in ok:
            if delete:
                try:
                    os.remove(f.path)
                    removed += 1
                except OSError as exc:
                    failed.append((f, f"silinemedi: {exc}"))
            self.kv_done.add(f.path)
        self._kvkk_render()
        msg = f"{len(ok)} dosya kasaya alındı" + (f" · {removed} orijinal silindi" if delete else " · orijinaller yerinde")
        self.notify("success" if not failed else "warning", "file", msg,
                    f"{len(failed)} hata: " + "; ".join(e for _f, e in failed[:2]) if failed else "")

    def kvkk_report(self):
        if not self.kv_result:
            self.notify("warning", "file", "Önce tarama yap")
            return
        org = simpledialog.askstring("Envanter raporu", "Kurum / birim adı (isteğe bağlı):", parent=self) or ""
        out = filedialog.asksaveasfilename(title="Envanter raporunu kaydet", defaultextension=".html",
                                           initialfile=f"KVKK-Envanter-{time.strftime('%Y%m%d')}.html", filetypes=[("HTML", "*.html")])
        if not out:
            return
        Path(out).write_text(kvkk.report_html(self.kv_result, org, self._app_version_full(), self._signature_b64()), encoding="utf-8")
        self.notify("success", "file", "Envanter raporu oluşturuldu", "Tarayıcıda açıldı · Yazdır veya PDF olarak kaydet")
        self._open_in_browser(Path(out))
