"""Araç Kutusu sayfası (6.9.1): klasör kasası, anahtar dosyası, güvenli imha + tutanak, dijital imza,
maskeli kopya ve kurulum bütünlüğü. Studio'ya karıştırılan arayüz katmanı; motorlara dokunmaz."""
from __future__ import annotations

import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

from elfcaesar.secure import open_bytes

from . import folderlock, keyfile, masking, shred, signing
from . import runtime
from .theme import F, BG, PANEL, INPUT, LINE, FG, FG_2, MUTED, DIM, AMBER, CYAN, GREEN, RED, ORANGE, mix
from .widgets import StudioButton, Segmented


class ToolboxMixin:
    # ------------------------------------------------------------ sayfa
    def _page_toolbox(self):
        self._page_intro("ARAÇ KUTUSU · 6.9.1", "Kasa, imha ve imza araçları",
                         "Bütün bir klasörü tek dosyada kilitle, kasaya ikinci faktör olarak anahtar dosyası ekle, belgeleri "
                         "imzala ve doğrula, kişisel verileri maskeleyerek paylaş, işi biten dosyaları tutanaklı imha et.",
                         CYAN, "YENİ", "key")
        self.tb_keyfile = getattr(self, "tb_keyfile", None)

        # 01 anahtar dosyası
        kf = self._card(self.content, "01 / İKİNCİ FAKTÖR · ANAHTAR DOSYASI", "PAROLA + DOSYA = KASA", "key", AMBER)
        kf.pack(fill="x", pady=(0, 12))
        self._wrap(tk.Label(kf, text="Etkinse klasör kasası parolanın YANINDA bu dosyayı da ister. Herhangi bir dosya (fotoğraf, "
                            "şarkı) ya da üretilen rastgele dosya olabilir. Dosyayı kaybedersen kasa açılmaz — bir USB belleğe "
                            "yedekle.", bg=PANEL, fg=MUTED, font=F["small"], justify="left"), 40).pack(fill="x", padx=16)
        self.tb_kf_label = tk.Label(kf, text="", bg=PANEL, fg=FG_2, font=F["mono_xs"], anchor="w")
        self.tb_kf_label.pack(fill="x", padx=16, pady=(8, 4))
        bar = tk.Frame(kf, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(0, 14))
        self._flow(bar, [StudioButton(bar, "ANAHTAR DOSYASI SEÇ", self.tb_pick_keyfile, "secondary", "open"),
                         StudioButton(bar, "YENİ ANAHTAR ÜRET", self.tb_new_keyfile, "ghost", "key"),
                         StudioButton(bar, "KALDIR", self.tb_clear_keyfile, "ghost", "close")])
        self._tb_kf_render()

        # 02 klasör kasası
        fl = self._card(self.content, "02 / KLASÖR KASASI", "AES-256-GCM · DOSYA ADLARI DA ŞİFRELİ", "lock", GREEN)
        fl.pack(fill="x", pady=(0, 12))
        self._wrap(tk.Label(fl, text="Bir klasörü alt klasörleri ve dosya adlarıyla birlikte tek bir .elfvault dosyasına şifreler. "
                            "Bulut klasörüne (OneDrive, Drive) koymak ve e-postayla göndermek için idealdir.",
                            bg=PANEL, fg=MUTED, font=F["small"], justify="left"), 40).pack(fill="x", padx=16)
        bar = tk.Frame(fl, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(10, 14))
        self._flow(bar, [StudioButton(bar, "KLASÖRÜ KİLİTLE", self.tb_lock_folder, "primary", "lock"),
                         StudioButton(bar, "KLASÖR KASASINI AÇ", self.tb_unlock_folder, "secondary", "unlock")])

        # 03 imza
        sg = self._card(self.content, "03 / DİJİTAL İMZA", "ED25519 · .ELFSIG", "check", CYAN)
        sg.pack(fill="x", pady=(0, 12))
        self._wrap(tk.Label(sg, text="Sözleşme, fatura veya kodu kimliğinle imzala; karşı taraf dosyanın senden geldiğini ve tek bayt "
                            "değişmediğini doğrulasın. İmzalayanın kişi kartı rehberinde doğrulanmışsa sonuç 'GÜVENİLİR' görünür.",
                            bg=PANEL, fg=MUTED, font=F["small"], justify="left"), 40).pack(fill="x", padx=16)
        bar = tk.Frame(sg, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(10, 14))
        self._flow(bar, [StudioButton(bar, "DOSYA İMZALA", self.tb_sign, "primary", "idcard"),
                         StudioButton(bar, "İMZA DOĞRULA", self.tb_verify, "secondary", "check")])

        # 04 maskeli kopya + imha
        kv = self._card(self.content, "04 / KVKK · MASKELE VE İMHA ET", "ORİJİNAL KORUNUR / TUTANAKLI SİLME", "trash", ORANGE)
        kv.pack(fill="x", pady=(0, 12))
        self._wrap(tk.Label(kv, text="Maskeli kopya: T.C. kimlik, IBAN, kart, telefon, e-posta ve parolaları gizleyerek paylaşılabilir "
                            "kopya üretir (metin tabanlı dosyalar). Güvenli imha: dosyanın üzerine rastgele veri yazar, adını "
                            "anonimleştirir, siler ve KVKK imha tutanağı düzenler.", bg=PANEL, fg=MUTED, font=F["small"],
                            justify="left"), 40).pack(fill="x", padx=16)
        row = tk.Frame(kv, bg=PANEL)
        row.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(row, text="MASKE", bg=PANEL, fg=DIM, font=F["label"]).pack(side="left")
        self.tb_mask_style = getattr(self, "tb_mask_style", "partial")
        Segmented(row, [("partial", "KISMİ"), ("full", "TAM")], lambda k: setattr(self, "tb_mask_style", k),
                  self.tb_mask_style).pack(side="left", padx=(8, 20))
        tk.Label(row, text="İMHA", bg=PANEL, fg=DIM, font=F["label"]).pack(side="left")
        self.tb_shred_method = getattr(self, "tb_shred_method", "random1")
        Segmented(row, [("random1", "1 GEÇİŞ"), ("random3", "3 GEÇİŞ")], lambda k: setattr(self, "tb_shred_method", k),
                  self.tb_shred_method).pack(side="left", padx=8)
        bar = tk.Frame(kv, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(10, 6))
        self._flow(bar, [StudioButton(bar, "MASKELİ KOPYA", self.tb_mask, "secondary", "file"),
                         StudioButton(bar, "GÜVENLİ İMHA + TUTANAK", self.tb_shred, "danger", "trash")])
        tk.Label(kv, text="SSD ve bulut eşitlemeli klasörlerde eski kopyalar kalabilir; en güvenlisi veriyi baştan şifreli tutmaktır.",
                 bg=PANEL, fg=DIM, font=F["tiny"], anchor="w").pack(fill="x", padx=16, pady=(0, 14))

        # 05 bütünlük
        it = self._card(self.content, "05 / KURULUM BÜTÜNLÜĞÜ", "DANTE SÜRÜM İMZASI", "shield", AMBER)
        it.pack(fill="x", pady=(0, 12))
        tk.Label(it, text=f"Dante sürüm anahtarı parmak izi:  {signing.release_fingerprint()}", bg=PANEL, fg=FG_2,
                 font=F["mono_xs"], anchor="w").pack(fill="x", padx=16)
        self.tb_integrity = tk.Label(it, text="Uygulama dosyalarının Dante tarafından imzalanan hâliyle aynı olup olmadığını denetler.",
                                     bg=PANEL, fg=MUTED, font=F["small"], anchor="w", justify="left")
        self.tb_integrity.pack(fill="x", padx=16, pady=(6, 0))
        bar = tk.Frame(it, bg=PANEL, height=36)
        bar.pack(fill="x", padx=16, pady=(10, 14))
        self._flow(bar, [StudioButton(bar, "BÜTÜNLÜĞÜ DOĞRULA", self.tb_check_integrity, "accent", "shield")])

    # ------------------------------------------------------------ anahtar dosyası
    def _tb_kf_render(self):
        if not getattr(self, "tb_kf_label", None) or not self.tb_kf_label.winfo_exists():
            return
        if self.tb_keyfile:
            try:
                sid = keyfile.short_id(self.tb_keyfile)
                self.tb_kf_label.configure(text=f"●  ETKİN · {Path(self.tb_keyfile).name} · kimlik {sid}", fg=GREEN)
                return
            except (OSError, ValueError):
                self.tb_keyfile = None
        self.tb_kf_label.configure(text="○  Anahtar dosyası yok — kasa yalnızca parolayla korunur.", fg=MUTED)

    def tb_pick_keyfile(self):
        path = filedialog.askopenfilename(title="Anahtar dosyası seç")
        if not path:
            return
        try:
            keyfile.digest(path)
        except (OSError, ValueError) as exc:
            self.notify("error", "vault", "Anahtar dosyası kullanılamıyor", str(exc))
            return
        self.tb_keyfile = path
        self._tb_kf_render()
        self.notify("success", "vault", "Anahtar dosyası etkin", Path(path).name, toast=False)

    def tb_new_keyfile(self):
        path = filedialog.asksaveasfilename(title="Yeni anahtar dosyasını kaydet", defaultextension=".elfkey",
                                            initialfile="anahtar.elfkey", filetypes=[("ElfCaesar anahtar", "*.elfkey")])
        if not path:
            return
        try:
            if Path(path).exists():
                Path(path).unlink()
            keyfile.create(path)
        except OSError as exc:
            self.notify("error", "vault", "Anahtar dosyası oluşturulamadı", str(exc))
            return
        self.tb_keyfile = path
        self._tb_kf_render()
        self.notify("success", "vault", "512 bit anahtar dosyası üretildi", "Bir USB belleğe yedeklemeyi unutma")

    def tb_clear_keyfile(self):
        self.tb_keyfile = None
        self._tb_kf_render()

    def _tb_secret(self, confirm: bool, purpose: str):
        pw = self._password(confirm=confirm, purpose=purpose + (" Anahtar dosyası da kullanılacak." if self.tb_keyfile else ""))
        if pw is None:
            return None
        try:
            return keyfile.combine(pw, self.tb_keyfile)
        except (OSError, ValueError) as exc:
            self.notify("error", "vault", "Anahtar dosyası okunamadı", str(exc))
            return None

    # ------------------------------------------------------------ klasör kasası
    def tb_lock_folder(self, folder=None):
        folder = folder or filedialog.askdirectory(title="Kilitlenecek klasör")
        if not folder:
            return
        n, size = folderlock.folder_stats(folder)
        if size > folderlock.MAX_FOLDER:
            self.notify("error", "vault", "Klasör çok büyük", "Şimdilik 1 GB'a kadar klasörler kilitlenebilir")
            return
        dst = filedialog.asksaveasfilename(title="Klasör kasasını kaydet", defaultextension=".elfvault",
                                           initialfile=Path(folder).name + ".elfvault", filetypes=[("ELF Vault", "*.elfvault")])
        if not dst:
            return
        secret = self._tb_secret(True, f"“{Path(folder).name}” klasörü ({n} dosya) tek kasaya şifrelenecek.")
        if secret is None:
            return
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            folderlock.lock(folder, dst, secret)
            _c, h = open_bytes(Path(dst).read_bytes(), secret)  # doğrulama
            assert folderlock.is_folder_vault(h)
        except Exception as exc:
            self.notify("error", "vault", "Klasör kilitlenemedi", str(exc))
            return
        finally:
            self.config(cursor="")
        self.notify("success", "vault", "Klasör kasası oluşturuldu ve doğrulandı", f"{n} dosya → {Path(dst).name}")
        if messagebox.askyesno("Orijinal klasör", f"Şifreli kasa doğrulandı.\n\nOrijinal “{Path(folder).name}” klasöründeki "
                               f"{n} dosya güvenli imha edilsin mi?\n\nBu işlem geri alınamaz.", parent=self, default="no"):
            files = [p for p in Path(folder).rglob("*") if p.is_file()]
            recs = shred.shred_many(files, self.tb_shred_method)
            self._tb_after_shred(recs, f"“{Path(folder).name}” klasörü kasaya alındı")

    def tb_unlock_folder(self, src=None):
        src = src or filedialog.askopenfilename(title="Klasör kasası (.elfvault)", filetypes=[("ELF Vault", "*.elfvault")])
        if not src:
            return
        out = filedialog.askdirectory(title="Klasör nereye açılsın?", initialdir=str(Path(src).parent))
        if not out:
            return
        secret = self._tb_secret(False, "Klasör kasasını açmak için parolanı gir.")
        if secret is None:
            return
        try:
            final = folderlock.unlock(src, out, secret)
        except Exception as exc:
            msg = str(exc)
            if self.tb_keyfile is None and "Parola yanlış" in msg:
                msg += " · Kasa anahtar dosyasıyla kilitlendiyse önce anahtar dosyasını seç."
            self.notify("error", "vault", "Klasör kasası açılamadı", msg)
            return
        self.notify("success", "vault", "Klasör kasası açıldı", str(final))
        self._reveal(str(final))

    # ------------------------------------------------------------ imza
    def _tb_identity(self):
        sess = getattr(self, "session", None)
        if not sess and not self.session_open():
            return None
        return self.session["identity"]

    def tb_sign(self, path=None):
        path = path or filedialog.askopenfilename(title="İmzalanacak dosya")
        if not path:
            return
        ident = self._tb_identity()
        if not ident:
            return
        note = simpledialog.askstring("Dosya imzala", "İmza notu (isteğe bağlı, ör. “Onaylıyorum”):", parent=self) or ""
        try:
            out = signing.sign_file(path, ident, note)
        except Exception as exc:
            self.notify("error", "identity", "İmzalanamadı", str(exc))
            return
        self.notify("success", "identity", "Dosya imzalandı", f"{out.name} · dosyayla birlikte gönder")
        self._reveal(str(out))

    def tb_verify(self, path=None):
        path = path or filedialog.askopenfilename(title="Doğrulanacak dosya (imza .elfsig yanında olmalı)")
        if not path:
            return
        if path.endswith(".elfsig"):
            sig, path = path, path[:-7]
        else:
            sig = path + ".elfsig"
        if not Path(sig).exists():
            sig = filedialog.askopenfilename(title="İmza dosyası (.elfsig)", filetypes=[("ELF imza", "*.elfsig")])
            if not sig:
                return
        try:
            r = signing.verify_file(path, sig, getattr(self, "book", None))
        except Exception as exc:
            self.notify("error", "identity", "İmza okunamadı", str(exc))
            return
        s = r["signer"]
        fp = s.get("fingerprint", "")[:16].upper()
        who = f"{s.get('name')} · {fp[:4]} {fp[4:8]} {fp[8:12]} {fp[12:16]}"
        if not r["valid"]:
            self.notify("error", "identity", "İMZA GEÇERSİZ", r["reason"])
            messagebox.showerror("İmza geçersiz", f"{r['reason']}\n\nİddia edilen imzalayan: {who}", parent=self)
            return
        trust = ("GÜVENİLİR — kişi kartı rehberinde doğrulanmış." if r.get("trusted") else
                 "Kişi rehberde var ama henüz doğrulanmadı (güvenlik kelimelerini karşılaştır)." if r.get("known") else
                 "İmzalayan rehberinde yok: imza matematiksel olarak geçerli ama kimden geldiğini bağımsız doğrula.")
        self.notify("success" if r.get("trusted") else "warning", "identity", "İmza geçerli", who)
        messagebox.showinfo("İmza geçerli", f"{Path(path).name}\n\nİmzalayan: {who}\nTarih: {r['signed_at']}\n"
                            f"{('Not: ' + r['note'] + chr(10)) if r['note'] else ''}\n{r['reason']}\n\n{trust}", parent=self)

    # ------------------------------------------------------------ maske / imha
    def tb_mask(self, paths=None):
        paths = paths or filedialog.askopenfilenames(title="Maskelenecek dosyalar")
        if not paths:
            return
        done, total = [], {}
        for p in paths:
            try:
                out, counts = masking.masked_copy(p, self.tb_mask_style)
                done.append(out)
                for k, v in counts.items():
                    total[k] = total.get(k, 0) + v
            except Exception as exc:
                self.notify("error", "file", f"{Path(p).name} maskelenemedi", str(exc))
        if done:
            self.notify("success", "file", f"{len(done)} maskeli kopya oluşturuldu", f"{sum(total.values())} değer maskelendi")
            self._reveal(str(done[0]))

    def tb_shred(self, paths=None):
        paths = paths or filedialog.askopenfilenames(title="Güvenli imha edilecek dosyalar")
        if not paths:
            return
        if not messagebox.askyesno("Güvenli imha", f"{len(paths)} dosyanın üzerine rastgele veri yazılıp silinecek.\n\n"
                                   "Bu işlem GERİ ALINAMAZ. Devam edilsin mi?", parent=self, icon="warning", default="no"):
            return
        recs = shred.shred_many(list(paths), self.tb_shred_method)
        self._tb_after_shred(recs, "")

    def _tb_after_shred(self, recs, reason):
        ok = sum(r.ok for r in recs)
        self.notify("success" if ok == len(recs) else "warning", "file", f"{ok}/{len(recs)} dosya güvenli imha edildi")
        if not messagebox.askyesno("İmha tutanağı", "KVKK imha tutanağı oluşturulsun mu?\n\nTutanak dosya adlarını ve içerik "
                                   "özetlerini (SHA-256) içerir, kişisel veriyi içermez.", parent=self):
            return
        org = simpledialog.askstring("İmha tutanağı", "Kurum / birim adı (isteğe bağlı):", parent=self) or ""
        why = reason or simpledialog.askstring("İmha tutanağı", "İmha gerekçesi:", parent=self,
                                               initialvalue="Saklama süresinin dolması") or ""
        out = filedialog.asksaveasfilename(title="Tutanağı kaydet", defaultextension=".html",
                                           initialfile=f"Imha-Tutanagi-{time.strftime('%Y%m%d-%H%M')}.html", filetypes=[("HTML", "*.html")])
        if not out:
            return
        Path(out).write_text(shred.tutanak_html(recs, org, why, self._app_version_full(), self._signature_b64()), encoding="utf-8")
        self._open_in_browser(Path(out))

    # ------------------------------------------------------------ bütünlük
    def tb_check_integrity(self):
        root = Path(sys.executable).parent if runtime.is_frozen() else None
        if root is None:
            self.tb_integrity.configure(text="Geliştirici modunda çalışıyor: kurulum manifesti yok (yalnızca kurulu sürümde denetlenir).",
                                        fg=MUTED)
            return
        r = signing.verify_install(root)
        if r["status"] == "ok":
            text, col, lvl = f"✓  {r['checked']} dosya Dante imzalı {r['version']} manifestiyle birebir aynı.", GREEN, "success"
        elif r["status"] == "missing":
            text, col, lvl = "Manifest bulunamadı — bu kopya resmi Dante kurulumundan gelmiyor olabilir.", AMBER, "warning"
        elif r["status"] == "bad_signature":
            text, col, lvl = "✗  Manifest imzası GEÇERSİZ — kurulum değiştirilmiş olabilir. Resmi kaynaktan yeniden kurun.", RED, "error"
        else:
            bad = (r["changed"] + r["missing"])[:3]
            text, col, lvl = (f"✗  {len(r['changed'])} dosya değişmiş, {len(r['missing'])} dosya eksik: {', '.join(bad)}"
                              " — yeniden kurun.", RED, "error")
        self.tb_integrity.configure(text=text, fg=col)
        self.notify(lvl, "system", "Kurulum bütünlüğü", text, toast=lvl != "success")
