"""Mesaj Köprüsü: WhatsApp / Telegram / e-posta gibi kanallar için uçtan uca şifreli mesaj akışı.

Bu modül Studio'ya karıştırılan (mixin) arayüz katmanıdır. Şifreleme ve imza motorları
(elfcaesar.identity, elfcaesar.secure) değiştirilmeden çağrılır; chatarmor yalnızca taşıma biçimidir.
"""
from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from types import SimpleNamespace

from elfcaesar.identity import (load_identity, import_contact, encrypt_for_contact, decrypt_from_contact,
                                validate_contact)
from elfcaesar.secure import encrypt_message, decrypt_message

from . import chatarmor as ca
from . import winbridge
from .contacts import ContactBook
from .sigil import sigil, short_fingerprint
from .theme import (F, BG, PANEL, INPUT, LINE, LINE_2, FG, FG_2, MUTED, DIM,
                    AMBER, CYAN, GREEN, RED, VIOLET, ORANGE, SELECT, mix)
from .widgets import StudioButton, Chip, Segmented, ToggleSwitch, Tooltip, rounded_points

TRUST = {
    "verified": ("DOĞRULANMIŞ KİŞİ", GREEN, "check"),
    "known": ("DEFTERDE · DOĞRULANMAMIŞ", AMBER, "alert"),
    "unknown": ("İMZALI · BİLİNMEYEN ANAHTAR", ORANGE, "alert"),
    "unsigned": ("İMZASIZ · GÖNDEREN BELİRSİZ", RED, "alert"),
    "password": ("PAROLALI MESAJ", CYAN, "key"),
}
CHUNK_PRESETS = [(1000, "KISA"), (3500, "TELEGRAM"), (60000, "WHATSAPP")]
BURN_PRESETS = [(0, "KAPALI"), (30, "30 SN"), (60, "60 SN"), (120, "2 DK")]


def mini_sigil(parent, fp, size=30, bg=PANEL):
    sg = sigil(fp)
    n = sg["size"]
    cell = (size - 4) / n
    c = tk.Canvas(parent, width=size, height=size, bg=INPUT, highlightthickness=1, highlightbackground=LINE_2)
    for r, col in sg["cells"]:
        x, y = 2 + col * cell, 2 + r * cell
        c.create_rectangle(x, y, x + cell, y + cell, fill=sg["primary"] if (r + col) % 3 else sg["secondary"], outline="")
    return c


class BridgeMixin:
    # ------------------------------------------------------------ kurulum
    def _bridge_init(self):
        self.book = ContactBook(validator=validate_contact)
        self.session = None
        self.reasm = ca.Reassembler()
        self._radar_last = None
        self._radar_pending = []
        self._own_armor: set[str] = set()
        self.bubbles: list[tk.Toplevel] = []
        self.mini = None
        self.composers = []
        self._poll_tick = 0
        self.hotkeys = winbridge.HotkeyListener()
        self.hotkeys_ok = bool(self.prefs.get("hotkeys")) and self.hotkeys.start()
        self._sync_contact_stats()
        self.after(400, self._bridge_poll)

    def _sync_contact_stats(self):
        total, verified = self.book.stats()
        self.sec.contacts_total, self.sec.contacts_verified = total, verified

    def _bridge_stop(self):
        try:
            self.hotkeys.stop()
        except Exception:
            pass

    def _bridge_wipe(self):
        """Kilit/panik: kimlik oturumunu kapat, açık mesaj balonlarını ve taslakları temizle."""
        self.session = None
        for b in list(self.bubbles):
            if b.winfo_exists():
                b.destroy()
        self.bubbles.clear()
        for comp in self.composers:
            if comp.text.winfo_exists():
                comp.text.delete("1.0", "end")
        self.reasm = ca.Reassembler()
        self._refresh_session_widgets()

    # ------------------------------------------------------------ olay döngüsü (kısayol + pano radarı)
    def _bridge_poll(self):
        try:
            for event in self.hotkeys.poll():
                {"encrypt": self.hotkey_encrypt, "decrypt": self.hotkey_decrypt, "bridge": self.toggle_mini,
                 "fill": self.quick_fill}[event]()
            self._poll_tick += 1
            if self.prefs.get("radar") and self._poll_tick % 3 == 0 and not self._locked:
                self._radar_scan()
        finally:
            self.after(250, self._bridge_poll)

    def _clipboard_text(self):
        try:
            return self.clipboard_get()
        except tk.TclError:
            return None

    def _set_clipboard(self, text, own=True):
        self.clipboard_clear()
        self.clipboard_append(text)
        if own:
            self._own_armor.add(text)
            self._radar_last = text

    def _radar_scan(self):
        text = self._clipboard_text()
        if text == self._radar_last:
            return
        self._radar_last = text
        if text and not ca.detect(text):
            self.pw_clipboard_guard(text)
        if not text or text in self._own_armor or not ca.detect(text):
            return
        try:
            items = self.reasm.feed(text)
        except ca.ArmorError as exc:
            self.notify("warning", "vault", "Bozuk şifreli mesaj algılandı", str(exc))
            return
        if not items:
            pend = self.reasm.pending()
            if pend:
                kind, got, total = pend[-1]
                self.notify("info", "vault", f"Parça alındı · {got}/{total}", f"{kind}: kalan parçaları da kopyala")
            return
        self._radar_pending = items
        kinds = {k for k, _ in items}
        title = "Panoda kişi kartı algılandı" if kinds == {"K"} else "Panoda şifreli mesaj algılandı"
        self.toasts.show("info", title, "Pano radarı · " + ", ".join(ca.KIND_NAMES[k] for k in sorted(kinds)),
                         action=("AÇ" if kinds == {"K"} else "ÇÖZ", lambda its=items: self.open_items(its)))
        self.log.add("vault", "info", title)

    # ------------------------------------------------------------ kimlik oturumu
    def session_open(self) -> bool:
        path = self.prefs.get("identity_path") or ""
        if not path or not Path(path).exists() or not messagebox.askyesno(
                "Kimlik oturumu", f"Bu kimlikle oturum açılsın mı?\n\n{Path(path).name}\n\nHayır: başka bir .elfid seç", parent=self):
            path = filedialog.askopenfilename(title="Özel kimlik kasanı (.elfid) seç", filetypes=[("ELF Identity", "*.elfid")])
            if not path:
                return False
        pw = self._password(purpose="Kimlik oturumu açmak için kimlik kasası parolanı gir. Oturum kilit veya panikte kapanır.")
        if pw is None:
            return False
        try:
            identity = load_identity(path, pw)
        except Exception as exc:
            self.notify("error", "identity", "Kimlik açılamadı", str(exc))
            return False
        self.session = {"identity": identity, "path": path, "opened": time.time()}
        self.set_pref("identity_path", str(path))
        self.notify("success", "identity", "Kimlik oturumu açıldı", identity["contact"]["name"])
        self._refresh_session_widgets()
        return True

    def session_close(self):
        self.session = None
        self.notify("info", "identity", "Kimlik oturumu kapatıldı", toast=False)
        self._refresh_session_widgets()

    def _own_contact(self):
        return self.session["identity"]["contact"] if self.session else None

    def _refresh_session_widgets(self):
        for comp in self.composers:
            if comp.session_chip.winfo_exists():
                self._paint_session(comp)
        page_chip = getattr(self, "br_session_chip", None)
        if page_chip is not None and page_chip.winfo_exists():
            self._paint_session_card()

    def _paint_session(self, comp):
        if self.session:
            comp.session_chip.set("● " + self.session["identity"]["contact"]["name"].upper(), GREEN)
            comp.session_btn.set_text("KAPAT")
            comp.session_btn.set_command(self.session_close)
        else:
            comp.session_chip.set("○ KİMLİK KAPALI", AMBER)
            comp.session_btn.set_text("KİMLİĞİ AÇ")
            comp.session_btn.set_command(self.session_open)

    # ------------------------------------------------------------ şifreleme / çözme çekirdeği
    def bridge_encrypt(self, message: str, fps: list[str], sign=True, mode="contact"):
        if not message.strip():
            self.notify("warning", "vault", "Şifrelenecek mesaj yok")
            return None
        try:
            if mode == "password":
                pw = self._password(confirm=True, purpose="Bu mesaj için ortak bir parola belirle. Parolayı karşı tarafa ayrı kanaldan ilet.")
                if pw is None:
                    return None
                armored = ca.armor_password(encrypt_message(message, pw))
                self.sec.unsigned_sends += 0
            else:
                cards = [self.book.get(fp)["card"] for fp in fps if self.book.get(fp)]
                if not cards:
                    self.notify("warning", "vault", "Alıcı seçilmedi", "Kişi defterinden en az bir alıcı seç")
                    return None
                sender = None
                if sign:
                    if not self.session and not self.session_open():
                        return None
                    sender = self.session["identity"]
                payloads = [encrypt_for_contact(message, c, sender) for c in cards]
                armored = ca.armor_dm(payloads[0]) if len(payloads) == 1 else ca.armor_group(payloads)
                if sender:
                    self.sec.signed_sends += 1
                else:
                    self.sec.unsigned_sends += 1
                self.set_pref("last_recipients", ",".join(fps))
            parts = ca.split(armored, int(self.prefs.get("chunk_limit") or ca.DEFAULT_LIMIT))
        except Exception as exc:
            self.notify("error", "vault", "Mesaj şifrelenemedi", str(exc))
            return None
        self._own_armor.update(parts)
        to = "parolalı" if mode == "password" else ", ".join(self.book.get(f)["alias"] for f in fps if self.book.get(f))
        self.notify("success", "vault", "Sohbet mesajı şifrelendi", f"{to} · {len(parts)} parça" if len(parts) > 1 else to, toast=False)
        self.refresh_security()
        return parts

    def open_text(self, text: str):
        if not ca.detect(text or ""):
            self.notify("warning", "vault", "Şifreli ElfCaesar mesajı bulunamadı", "Metin “🔐ELF1:” ile başlayan bir blok içermeli")
            return
        try:
            items = self.reasm.feed(text)
        except ca.ArmorError as exc:
            self.notify("error", "vault", "Mesaj bozuk", str(exc))
            return
        if not items:
            pend = self.reasm.pending()
            if pend:
                kind, got, total = pend[-1]
                self.notify("info", "vault", f"Parça alındı · {got}/{total}", "Kalan parçaları da kopyalayıp aç")
            return
        self.open_items(items)

    def open_items(self, items):
        for kind, blob in items:
            try:
                if kind == "K":
                    self._offer_contact(ca.unpack_contact(blob))
                elif kind == "P":
                    pw = self._password(purpose="Bu parolalı mesajı açmak için gönderenin paylaştığı parolayı gir.")
                    if pw is None:
                        continue
                    self.show_bubble(decrypt_message(blob.decode("utf-8"), pw), None, "password")
                else:
                    self._open_dm(kind, blob)
            except Exception as exc:
                self.notify("error", "vault", "Mesaj açılamadı", str(exc))

    def _open_dm(self, kind, blob):
        if not self.session and not self.session_open():
            return
        own_fp = self._own_contact()["fingerprint"]
        if kind == "G":
            mine = [b for b in ca.unpack_group(blob) if ca.dm_recipient(b) == own_fp]
            if not mine:
                self.notify("warning", "vault", "Bu grup mesajında sana ait kopya yok", "Gönderen seni alıcı olarak seçmemiş")
                return
            blob = mine[0]
        elif ca.dm_recipient(blob) != own_fp:
            entry = self.book.get(ca.dm_recipient(blob))
            self.notify("warning", "vault", "Bu mesaj sana gönderilmemiş",
                        f"Alıcı: {entry['alias'] if entry else short_fingerprint(ca.dm_recipient(blob))}")
            return
        clear, sender = decrypt_from_contact(ca.unpack_dm(blob), self.session["identity"], None)
        trust = "unsigned"
        if sender:
            entry = self.book.get(sender["fingerprint"])
            trust = "verified" if entry and entry["verified"] else ("known" if entry else "unknown")
            if trust == "verified":
                self.sec.pinned_opens += 1
            else:
                self.sec.unpinned_opens += 1
            if entry:
                self.book.touch(sender["fingerprint"])
        self.refresh_security()
        self.notify("success" if trust == "verified" else "warning", "vault", "Mesaj çözüldü", TRUST[trust][0], toast=False)
        if self.receive_shared_password(clear, sender, TRUST[trust][0]):
            return
        self.show_bubble(clear, sender, trust)

    # ------------------------------------------------------------ mühürlü mesaj balonu
    def show_bubble(self, text, sender, trust):
        label, color, glyph = TRUST[trust]
        win = tk.Toplevel(self)
        win.withdraw()
        win.title("ElfCaesar · mühürlü mesaj")
        win.configure(bg=mix(color, BG, .5))
        win.attributes("-topmost", True)
        if self.img("mark_32") is not None:
            try:
                win.iconphoto(False, self.img("mark_32"))
            except tk.TclError:
                pass
        self.bubbles.append(win)
        card = tk.Frame(win, bg=PANEL)
        card.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(card, bg=color, height=3).pack(fill="x")
        head = tk.Frame(card, bg=PANEL)
        head.pack(fill="x", padx=16, pady=(12, 6))
        if self.img("mark_32") is not None:
            tk.Label(head, image=self.img("mark_32"), bg=PANEL).pack(side="left", padx=(0, 10))
        ht = tk.Frame(head, bg=PANEL)
        ht.pack(side="left", fill="x", expand=True)
        Chip(ht, label, color).pack(anchor="w")
        who = "Gönderen imzası yok" if not sender else (
            (self.book.get(sender["fingerprint"]) or {}).get("alias") or sender.get("name", "?"))
        if trust == "password":
            who = "Ortak parola ile şifrelenmiş"
        tk.Label(ht, text=who, bg=PANEL, fg=FG, font=F["h3"]).pack(anchor="w", pady=(4, 0))
        if sender:
            row = tk.Frame(card, bg=PANEL)
            row.pack(fill="x", padx=16, pady=(0, 6))
            mini_sigil(row, sender["fingerprint"], 26).pack(side="left")
            tk.Label(row, text=" · ".join(ca.safety_words(sender["fingerprint"])), bg=PANEL, fg=color,
                     font=F["mono_xs"]).pack(side="left", padx=8)
        body = tk.Text(card, height=min(14, max(4, text.count("\n") + 2 + len(text) // 60)), width=56, wrap="word",
                       bg=INPUT, fg=FG, font=F["mono"], relief="flat", padx=12, pady=10, highlightthickness=0)
        body.insert("1.0", text)
        body.configure(state="disabled")
        body.pack(fill="both", expand=True, padx=14, pady=(4, 8))
        if trust in ("unknown", "unsigned"):
            msg = ("İmza geçerli ama bu anahtar kişi defterinde yok. Kişiyi ekleyip güvenlik kelimelerini sesli karşılaştır."
                   if trust == "unknown" else "Bu mesaj imzasız: içeriği kimin yazdığı doğrulanamaz.")
            tk.Label(card, text=msg, bg=PANEL, fg=color, font=F["tiny"], wraplength=440, justify="left").pack(anchor="w", padx=16)
        burn = int(self.prefs.get("burn_seconds") or 0)
        bar = tk.Canvas(card, height=4, bg=PANEL, highlightthickness=0)
        bar.pack(fill="x", padx=16, pady=(8, 0))
        info = tk.Label(card, text="", bg=PANEL, fg=DIM, font=F["mono_xs"])
        info.pack(anchor="w", padx=16)
        btns = tk.Frame(card, bg=PANEL)
        btns.pack(fill="x", padx=14, pady=(8, 14))
        StudioButton(btns, "KOPYALA", lambda: self.guarded_copy(text), "secondary", "copy", "sm").pack(side="left")
        if sender:
            entry = self.book.get(sender["fingerprint"])
            if entry:
                StudioButton(btns, "YANITLA", lambda fp=sender["fingerprint"]: (self._close_bubble(win), self.reply_to(fp)),
                             "accent", "send", "sm").pack(side="left", padx=6)
            else:
                StudioButton(btns, "DEFTERİME EKLE", lambda s=sender: self._offer_contact(s), "accent", "user", "sm").pack(
                    side="left", padx=6)
        StudioButton(btns, "KAPAT", lambda: self._close_bubble(win), "ghost", "close", "sm").pack(side="right")
        win.bind("<Escape>", lambda _e: self._close_bubble(win))
        start = time.monotonic()

        def tick():
            if not win.winfo_exists():
                return
            if not burn:
                info.configure(text="OKUDUKTAN SONRA YOK ET: KAPALI · METİN HİÇBİR YERE KAYDEDİLMEDİ")
                return
            left = burn - (time.monotonic() - start)
            if left <= 0:
                self._close_bubble(win)
                return
            w = bar.winfo_width()
            bar.delete("all")
            bar.create_rectangle(0, 0, w * left / burn, 4, fill=color, outline="")
            info.configure(text=f"OKUDUKTAN SONRA YOK ET · {int(left) + 1} SN · METİN HİÇBİR YERE KAYDEDİLMEDİ")
            win.after(200, tick)
        win.update_idletasks()
        pos = winbridge.cursor_pos()
        if pos:
            x, y = pos[0] - win.winfo_reqwidth() // 2, pos[1] + 18
        else:
            x = self.winfo_rootx() + (self.winfo_width() - win.winfo_reqwidth()) // 2
            y = self.winfo_rooty() + 120
        win.geometry(f"+{max(0, x)}+{max(0, y)}")
        win.deiconify()
        self.shield(win)
        win.lift()
        win.focus_force()
        tick()
        return win

    def _close_bubble(self, win):
        if win in self.bubbles:
            self.bubbles.remove(win)
        if win.winfo_exists():
            win.destroy()

    def reply_to(self, fp):
        comp = self._ensure_composer()
        comp.select([fp])
        comp.mode.set("contact", notify=True)
        comp.text.focus_set()

    def _ensure_composer(self):
        live = [c for c in self.composers if c.text.winfo_exists()]
        if live:
            return live[0]
        self.open_mini()
        return self.composers[-1]

    # ------------------------------------------------------------ kişi kartları
    def _offer_contact(self, card):
        try:
            card = validate_contact(card)
        except Exception as exc:
            self.notify("error", "identity", "Kişi kartı geçersiz", str(exc))
            return
        if self.session and card["fingerprint"] == self._own_contact()["fingerprint"]:
            self.notify("info", "identity", "Bu senin kendi kişi kartın")
            return
        words = " · ".join(ca.safety_words(card["fingerprint"]))
        existing = self.book.get(card["fingerprint"])
        if existing:
            self.notify("info", "identity", "Kişi zaten defterde", existing["alias"])
            return
        if not messagebox.askyesno("Kişi kartı", f"Ad: {card['name']}\nParmak izi: {short_fingerprint(card['fingerprint'])}\n"
                                   f"Güvenlik kelimeleri:\n{words}\n\nKişi defterine eklensin mi?", parent=self):
            return
        self.book.add(card)
        verified = messagebox.askyesno("Güvenlik kelimelerini doğrula",
                                       f"Şimdi {card['name']} ile telefonda veya yüz yüze konuş ve kelimeleri karşılaştır:\n\n"
                                       f"{words}\n\nKarşı taraf aynı 6 kelimeyi aynı sırayla okudu mu?", parent=self)
        if verified:
            self.book.set_verified(card["fingerprint"])
        self._contacts_changed()
        self.notify("success", "identity", "Kişi defterine eklendi",
                    card["name"] + (" · doğrulandı" if verified else " · doğrulama bekliyor"))

    def verify_contact(self, fp):
        entry = self.book.get(fp)
        if not entry:
            return
        words = " · ".join(ca.safety_words(fp))
        if messagebox.askyesno("Güvenlik kelimeleri", f"{entry['alias']} ile sesli karşılaştır:\n\n{words}\n\n"
                               "Karşı taraf aynı kelimeleri okudu mu?", parent=self):
            self.book.set_verified(fp, True)
            self.notify("success", "identity", "Kişi doğrulandı", entry["alias"])
        self._contacts_changed()

    def remove_contact(self, fp):
        entry = self.book.get(fp)
        if entry and messagebox.askyesno("Kişiyi sil", f"{entry['alias']} kişi defterinden silinsin mi?", parent=self):
            self.book.remove(fp)
            self._contacts_changed()

    def import_contact_file(self, path=None):
        path = path or filedialog.askopenfilename(title="Kişi kartı seç", filetypes=[("ELF Contact", "*.elfcontact")])
        if not path:
            return
        try:
            self._offer_contact(import_contact(path))
        except Exception as exc:
            self.notify("error", "identity", "Kişi kartı okunamadı", str(exc))

    def share_my_card(self):
        if not self.session and not self.session_open():
            return
        self._set_clipboard(ca.armor_contact(self._own_contact()))
        self.notify("success", "identity", "Kişi kartın panoya kopyalandı",
                    "WhatsApp/Telegram'a yapıştır · kelimeler: " + " ".join(ca.safety_words(self._own_contact()["fingerprint"])[:3]) + " …")

    def _contacts_changed(self):
        self._sync_contact_stats()
        self.refresh_security()
        for comp in self.composers:
            if comp.listbox.winfo_exists():
                comp.reload()
        if getattr(self, "br_contacts", None) is not None and self.br_contacts.winfo_exists():
            self._render_contacts()

    # ------------------------------------------------------------ yazım alanı (sayfa + mini pencere)
    def _composer(self, parent, compact=False):
        c = SimpleNamespace()
        top = tk.Frame(parent, bg=PANEL)
        top.pack(fill="x", pady=(0, 8))
        c.session_chip = Chip(top, "", AMBER)
        c.session_chip.pack(side="left")
        c.session_btn = StudioButton(top, "KİMLİĞİ AÇ", self.session_open, "ghost", "key", "sm")
        c.session_btn.pack(side="right")
        modes = tk.Frame(parent, bg=PANEL)
        modes.pack(fill="x", pady=(0, 8))
        c.mode = Segmented(modes, [("contact", "KİŞİYE / GRUBA"), ("password", "ORTAK PAROLA")], lambda _m: _mode_changed())
        c.mode.pack(side="left")
        sign_box = tk.Frame(modes, bg=PANEL)
        sign_box.pack(side="right")
        tk.Label(sign_box, text="İMZALA", bg=PANEL, fg=MUTED, font=F["label"]).pack(side="left", padx=(0, 6))
        c.sign = ToggleSwitch(sign_box, True)
        c.sign.pack(side="left")
        Tooltip(c.sign, "Ed25519 imzası: alıcı mesajı senin yazdığını doğrular (önerilir)")
        c.rec_label = tk.Label(parent, text="ALICILAR · CTRL/SHIFT İLE ÇOKLU SEÇİM = GRUP MESAJI", bg=PANEL, fg=DIM,
                               font=F["label"], anchor="w")
        c.rec_label.pack(fill="x")
        c.rec_frame = tk.Frame(parent, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
        c.rec_frame.pack(fill="x", pady=(4, 8))
        c.listbox = tk.Listbox(c.rec_frame, selectmode="extended", height=3 if compact else 4, bg=INPUT, fg=FG,
                               selectbackground=SELECT, selectforeground=AMBER, relief="flat", highlightthickness=0,
                               font=F["small"], activestyle="none", exportselection=False, bd=0)
        c.listbox.pack(fill="x", padx=6, pady=4)
        c.fps = []

        def reload():
            sel = set(c.selected()) if c.fps else set(filter(None, (self.prefs.get("last_recipients") or "").split(",")))
            c.listbox.delete(0, "end")
            c.fps = []
            for e in self.book.sorted():
                mark = "✓" if e["verified"] else "!"
                c.listbox.insert("end", f" {mark}  {e['alias']}   ·   {short_fingerprint(e['card']['fingerprint'])}")
                c.fps.append(e["card"]["fingerprint"])
            if not c.fps:
                c.listbox.insert("end", "  Kişi defteri boş · Mesaj Köprüsü > Kişi Defteri'nden kişi ekle")
                c.listbox.itemconfigure(0, fg=DIM)
            for i, fp in enumerate(c.fps):
                if fp in sel:
                    c.listbox.selection_set(i)
        c.reload = reload
        c.selected = lambda: [c.fps[i] for i in c.listbox.curselection() if i < len(c.fps)]

        def select(fps):
            c.listbox.selection_clear(0, "end")
            for i, fp in enumerate(c.fps):
                if fp in fps:
                    c.listbox.selection_set(i)
                    c.listbox.see(i)
        c.select = select
        tk.Label(parent, text="MESAJ", bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(fill="x")
        tbox = tk.Frame(parent, bg=INPUT, highlightthickness=1, highlightbackground=LINE, highlightcolor=CYAN)
        tbox.pack(fill="both", expand=True, pady=(4, 8))
        c.text = tk.Text(tbox, height=4 if compact else 6, wrap="word", bg=INPUT, fg=FG, insertbackground=AMBER,
                         relief="flat", padx=10, pady=8, font=F["mono"], highlightthickness=0, undo=True)
        c.text.pack(fill="both", expand=True)
        c.counter = tk.Label(parent, text="", bg=PANEL, fg=DIM, font=F["mono_xs"], anchor="e")
        c.counter.pack(fill="x")
        c.text.bind("<KeyRelease>", lambda _e: c.counter.configure(text=f"{len(c.text.get('1.0', 'end-1c'))} KARAKTER"))
        bar = tk.Frame(parent, bg=PANEL)
        bar.pack(fill="x", pady=(6, 0))
        enc = StudioButton(bar, "ŞİFRELE VE KOPYALA", lambda: _encrypt(), "primary", "lock")
        enc.pack(side="left")
        StudioButton(bar, "PANODAN ÇÖZ", lambda: self.open_text(self._clipboard_text() or ""), "secondary", "unlock").pack(
            side="left", padx=6)
        c.parts = tk.Frame(parent, bg=PANEL)
        c.parts.pack(fill="x", pady=(8, 0))
        c.text.bind("<Control-Return>", lambda _e: (_encrypt(), "break")[1])

        def _mode_changed():
            pw = c.mode.value == "password"
            state = "disabled" if pw else "normal"
            c.listbox.configure(state=state)
            c.rec_label.configure(fg=MUTED if not pw else DIM, text="ALICILAR · ORTAK PAROLA MODUNDA GEREKMEZ" if pw else
                                  "ALICILAR · CTRL/SHIFT İLE ÇOKLU SEÇİM = GRUP MESAJI")

        def _encrypt():
            parts = self.bridge_encrypt(c.text.get("1.0", "end-1c"), c.selected(), sign=c.sign.value, mode=c.mode.value)
            for ch in c.parts.winfo_children():
                ch.destroy()
            if not parts:
                return
            self._set_clipboard(parts[0])
            c.text.delete("1.0", "end")
            c.counter.configure(text="")
            if len(parts) == 1:
                tk.Label(c.parts, text=f"✓ Panoya kopyalandı · {len(parts[0])} karakter · sohbet penceresine yapıştır (Ctrl+V)",
                         bg=PANEL, fg=GREEN, font=F["tiny"], anchor="w").pack(fill="x")
                return
            tk.Label(c.parts, text=f"Mesaj {len(parts)} parçaya bölündü. Sırayla kopyala ve gönder (1. parça panoda):",
                     bg=PANEL, fg=AMBER, font=F["tiny"], anchor="w").pack(fill="x", pady=(0, 4))
            row = tk.Frame(c.parts, bg=PANEL)
            row.pack(fill="x")
            for i, p in enumerate(parts, start=1):
                StudioButton(row, f"{i}/{len(parts)}", lambda p=p, i=i: (self._set_clipboard(p),
                             self.status(f"Parça {i} panoya kopyalandı", "success")), "secondary", "copy", "sm").pack(side="left", padx=(0, 4))
        reload()
        self.composers.append(c)
        self._paint_session(c)
        return c

    # ------------------------------------------------------------ mini köprü penceresi
    def toggle_mini(self):
        if self.mini is not None and self.mini.winfo_exists():
            self.mini.destroy()
            self.mini = None
        else:
            self.open_mini()

    def open_mini(self):
        if self.mini is not None and self.mini.winfo_exists():
            self.mini.deiconify()
            self.mini.lift()
            return self.mini
        win = tk.Toplevel(self)
        win.title("ElfCaesar · Mesaj Köprüsü")
        win.configure(bg=PANEL)
        win.geometry("420x620")
        win.minsize(360, 520)
        win.attributes("-topmost", bool(self.prefs.get("mini_topmost", True)))
        if self.img("mark_32") is not None:
            try:
                win.iconphoto(False, self.img("mark_32"))
            except tk.TclError:
                pass
        head = tk.Frame(win, bg=PANEL)
        head.pack(fill="x", padx=16, pady=(14, 8))
        if self.img("mark_40") is not None:
            tk.Label(head, image=self.img("mark_40"), bg=PANEL).pack(side="left", padx=(0, 10))
        ht = tk.Frame(head, bg=PANEL)
        ht.pack(side="left")
        tk.Label(ht, text="Mesaj Köprüsü", bg=PANEL, fg=FG, font=F["h2"]).pack(anchor="w")
        tk.Label(ht, text="WhatsApp · Telegram · e-posta · her sohbet", bg=PANEL, fg=MUTED, font=F["tiny"]).pack(anchor="w")
        pin = tk.Frame(head, bg=PANEL)
        pin.pack(side="right")
        tk.Label(pin, text="ÜSTTE", bg=PANEL, fg=DIM, font=F["label"]).pack(side="left", padx=(0, 4))
        ToggleSwitch(pin, bool(self.prefs.get("mini_topmost", True)),
                     lambda v: (win.attributes("-topmost", v), self.set_pref("mini_topmost", v))).pack(side="left")
        tk.Frame(win, bg=LINE, height=1).pack(fill="x")
        body = tk.Frame(win, bg=PANEL)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        comp = self._composer(body, compact=True)
        hint = ("Ctrl+Alt+E seçili metni yerinde şifreler · Ctrl+Alt+D seçili mesajı çözer" if self.hotkeys_ok else
                "Genel kısayollar yalnızca Windows'ta · burada kopyala → PANODAN ÇÖZ kullan")
        tk.Label(win, text=hint, bg=PANEL, fg=DIM, font=F["tiny"], wraplength=380).pack(pady=(0, 12))
        win.protocol("WM_DELETE_WINDOW", lambda: (win.destroy(), setattr(self, "mini", None)))
        self.mini = win
        self.shield(win)
        comp.text.focus_set()
        return win

    # ------------------------------------------------------------ genel kısayollar (Windows)
    def _grab_selection(self, callback):
        """Seçili metni etkin uygulamadan (WhatsApp, Telegram…) Ctrl+C ile alır."""
        sentinel = f"\u2063elfcaesar-{time.monotonic()}"
        self._set_clipboard(sentinel, own=True)
        winbridge.send_ctrl("c")

        def wait(n=0):
            text = self._clipboard_text()
            if text and text != sentinel:
                self._radar_last = text
                callback(text)
            elif n < 15:
                self.after(60, lambda: wait(n + 1))
            else:
                self._set_clipboard("", own=True)
                self.notify("warning", "vault", "Seçili metin alınamadı", "Önce sohbet kutusunda metni seç, sonra kısayola bas")
        self.after(80, wait)

    def hotkey_encrypt(self):
        comp = next((c for c in self.composers if c.listbox.winfo_exists()), None)
        fps = comp.selected() if comp else [f for f in (self.prefs.get("last_recipients") or "").split(",") if self.book.get(f)]
        if not fps:
            self.open_mini()
            self.notify("warning", "vault", "Önce alıcı seç", "Mesaj Köprüsü'nde alıcıyı seçip kısayolu tekrar kullan")
            return

        def got(text):
            if ca.detect(text):
                self.notify("info", "vault", "Seçili metin zaten şifreli", "Çözmek için Ctrl+Alt+D")
                return
            parts = self.bridge_encrypt(text, fps, sign=True)
            if not parts:
                return
            self._set_clipboard(parts[0])
            if len(parts) == 1:
                self.after(60, lambda: winbridge.send_ctrl("v"))
                self.notify("success", "vault", "Mesaj yerinde şifrelendi", "Enter ile gönder")
            else:
                self.open_mini()
                self.notify("warning", "vault", f"Uzun mesaj {len(parts)} parçaya bölündü", "Parçaları Mesaj Köprüsü'nden sırayla gönder")
        self._grab_selection(got)

    def hotkey_decrypt(self):
        self._grab_selection(self.open_text)

    # ------------------------------------------------------------ Mesaj Köprüsü sayfası
    def _page_bridge(self):
        self._page_intro("09 / MESSAGE BRIDGE", "WhatsApp ve Telegram için uçtan uca şifreli mesaj",
                         "Mesajı ElfCaesar şifreler, sohbet uygulaması yalnızca anlamsız bir 🔐ELF1 bloğu taşır. Karşı taraf kendi "
                         "bilgisayarındaki ElfCaesar ile çözer ve imzayla senin yazdığını doğrular.", CYAN, "X25519 · ED25519", "send")
        flow = self._card(self.content, "NASIL ÇALIŞIR", "4 ADIM", "spark", CYAN)
        flow.pack(fill="x", pady=(0, 12))
        canvas = tk.Canvas(flow, height=118, bg=PANEL, highlightthickness=0)
        canvas.pack(fill="x", padx=16, pady=(0, 6))
        steps = [("1", "Kartları değiş", "KARTIMI PAYLAŞ → sohbete yapıştır", VIOLET),
                 ("2", "Sesli doğrula", "6 güvenlik kelimesini karşılaştır", GREEN),
                 ("3", "Seç · Ctrl+Alt+E", "metin yerinde şifrelenir", AMBER),
                 ("4", "Seç · Ctrl+Alt+D", "mühürlü balonda okunur", CYAN)]

        def draw(_e=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            if w < 300:
                return
            bw = (w - 3 * 28) / 4
            for i, (n, t, s, col) in enumerate(steps):
                x = i * (bw + 28)
                canvas.create_polygon(rounded_points(x + 1, 8, x + bw, 104, 12), smooth=True, fill=mix(col, PANEL, .88),
                                      outline=mix(col, PANEL, .45))
                canvas.create_oval(x + 14, 22, x + 40, 48, fill=col, outline="")
                canvas.create_text(x + 27, 35, text=n, fill="#101722", font=F["mono_b"])
                canvas.create_text(x + 50, 35, text=t, fill=FG, font=F["body_b"], anchor="w")
                canvas.create_text(x + 16, 74, text=s, fill=MUTED, font=F["tiny"], anchor="w", width=bw - 24)
                if i < 3:
                    canvas.create_line(x + bw + 6, 56, x + bw + 22, 56, fill=LINE_2, width=2, arrow="last")
        canvas.bind("<Configure>", draw)
        self._wrap(tk.Label(flow, text="Not: WhatsApp ve Telegram, kendi sağ tık menülerine başka uygulamaların öğe eklemesine izin "
                            "vermez. Bu yüzden ElfCaesar, her uygulamada seçili metin üzerinde çalışan genel kısayollar, pano radarı "
                            "ve Windows Gezgini sağ tık menüsü (dosyalar için) kullanır.", bg=PANEL, fg=DIM, font=F["tiny"],
                            justify="left")).pack(fill="x", padx=16, pady=(0, 14))

        row = tk.Frame(self.content, bg=BG)
        row.pack(fill="x", pady=(0, 12))
        sess = self._card(row, "KİMLİK OTURUMU", "ÖZEL ANAHTAR YALNIZCA BELLEKTE", "idcard", VIOLET)
        self.br_session = tk.Frame(sess, bg=PANEL)
        self.br_session.pack(fill="x", padx=16, pady=(0, 14))
        self.br_session_chip = Chip(self.br_session, "", AMBER)
        integ = self._card(row, "ENTEGRASYONLAR", "WINDOWS · PANO · ZAMANLAYICI", "spark", AMBER)
        self._integrations(integ)
        self._auto_grid(row, [sess, integ], 440, 2, gap=12)
        self._paint_session_card()

        cards = self._card(self.content, "KİŞİ DEFTERİ", "YALNIZCA AÇIK ANAHTARLAR SAKLANIR", "user", GREEN)
        cards.pack(fill="x", pady=(0, 12))
        bar = tk.Frame(cards, bg=PANEL, height=30)
        bar.pack(fill="x", padx=16, pady=(0, 10))
        self._flow(bar, [StudioButton(bar, "KARTIMI SOHBETTE PAYLAŞ", self.share_my_card, "primary", "send", "sm"),
                         StudioButton(bar, ".ELFCONTACT İÇE AKTAR", self.import_contact_file, "secondary", "open", "sm"),
                         StudioButton(bar, "PANODAN KART EKLE", lambda: self.open_text(self._clipboard_text() or ""),
                                      "secondary", "paste", "sm")])
        self.br_contacts = tk.Frame(cards, bg=PANEL)
        self.br_contacts.pack(fill="x", padx=14, pady=(0, 14))
        self._render_contacts()

        both = tk.Frame(self.content, bg=BG)
        both.pack(fill="x", pady=(0, 12))
        compc = self._card(both, "MESAJ YAZ", "ŞİFRELE · PANOYA KOPYALA · SOHBETE YAPIŞTIR", "lock", AMBER)
        inner = tk.Frame(compc, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._composer(inner)
        dec = self._card(both, "GELEN MESAJI ÇÖZ", "YAPIŞTIR VEYA PANODAN AL", "unlock", CYAN)
        dinner = tk.Frame(dec, bg=PANEL)
        dinner.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        box = tk.Frame(dinner, bg=INPUT, highlightthickness=1, highlightbackground=LINE, highlightcolor=CYAN)
        box.pack(fill="both", expand=True)
        self.br_in = tk.Text(box, height=9, wrap="char", bg=INPUT, fg=FG_2, insertbackground=CYAN, relief="flat", padx=10,
                             pady=8, font=F["mono_xs"], highlightthickness=0)
        self.br_in.pack(fill="both", expand=True)
        db = tk.Frame(dinner, bg=PANEL)
        db.pack(fill="x", pady=(10, 0))
        StudioButton(db, "ÇÖZ", lambda: self.open_text(self.br_in.get("1.0", "end-1c")), "primary", "unlock").pack(side="left")
        StudioButton(db, "PANODAN ÇÖZ", lambda: self.open_text(self._clipboard_text() or ""), "secondary", "paste").pack(
            side="left", padx=6)
        StudioButton(db, "", lambda: self.br_in.delete("1.0", "end"), "ghost", "clear", tooltip="Temizle").pack(side="right")
        self._auto_grid(both, [compc, dec], 460, 2, gap=12)
        StudioButton(self.content, "MİNİ KÖPRÜ PENCERESİNİ AÇ  ·  CTRL+ALT+B", self.open_mini, "accent", "send").pack(anchor="w")

    def _paint_session_card(self):
        f = self.br_session
        for ch in f.winfo_children():
            if ch is not self.br_session_chip:
                ch.destroy()
        self.br_session_chip.pack_forget()
        if self.session:
            own = self._own_contact()
            top = tk.Frame(f, bg=PANEL)
            top.pack(fill="x")
            mini_sigil(top, own["fingerprint"], 44).pack(side="left")
            t = tk.Frame(top, bg=PANEL)
            t.pack(side="left", padx=12)
            self.br_session_chip.set("● OTURUM AÇIK", GREEN)
            self.br_session_chip.pack(in_=t, anchor="w")
            tk.Label(t, text=own["name"], bg=PANEL, fg=FG, font=F["h3"]).pack(anchor="w", pady=(4, 0))
            tk.Label(t, text=short_fingerprint(own["fingerprint"]), bg=PANEL, fg=VIOLET, font=F["mono_xs"]).pack(anchor="w")
            tk.Label(f, text="Senin güvenlik kelimelerin:  " + " · ".join(ca.safety_words(own["fingerprint"])),
                     bg=PANEL, fg=FG_2, font=F["small"]).pack(anchor="w", pady=(10, 2))
            tk.Label(f, text="Oturum kilit, panik veya uygulama kapanınca otomatik kapanır.", bg=PANEL, fg=DIM,
                     font=F["tiny"]).pack(anchor="w")
            StudioButton(f, "OTURUMU KAPAT", self.session_close, "secondary", "lock", "sm").pack(anchor="w", pady=(10, 0))
        else:
            self.br_session_chip.set("○ KİMLİK KAPALI", AMBER)
            self.br_session_chip.pack(in_=f, anchor="w")
            tk.Label(f, text="Mesajları imzalamak ve sana gelenleri çözmek için .elfid kimliğini bir kez aç.\n"
                     "Kimliğin yoksa Güvenli Kasa > YENİ KİMLİK ile oluştur.", bg=PANEL, fg=MUTED, font=F["small"],
                     justify="left").pack(anchor="w", pady=(8, 10))
            StudioButton(f, "KİMLİĞİ AÇ", self.session_open, "primary", "key", "sm").pack(anchor="w")

    def _integrations(self, card):
        def row(title, desc, right_builder, last=False):
            r = tk.Frame(card, bg=PANEL)
            r.pack(fill="x", padx=16, pady=(0, 2))
            left = tk.Frame(r, bg=PANEL)
            left.pack(side="left", fill="x", expand=True, pady=6)
            tk.Label(left, text=title, bg=PANEL, fg=FG, font=F["body_b"], anchor="w").pack(fill="x")
            tk.Label(left, text=desc, bg=PANEL, fg=DIM, font=F["tiny"], anchor="w", justify="left", wraplength=300).pack(fill="x")
            right_builder(r)
            if not last:
                tk.Frame(card, bg=LINE, height=1).pack(fill="x", padx=16)
        status = ("Etkin · " + ", ".join(self.hotkeys.registered)) if self.hotkeys_ok else (
            "Yalnızca Windows" if not winbridge.IS_WINDOWS else "Kapalı veya başka uygulama kullanıyor")
        row("Genel kısayollar", f"Ctrl+Alt+E şifrele · Ctrl+Alt+D çöz · Ctrl+Alt+B köprü · Ctrl+Alt+P hızlı doldur — {status}",
            lambda r: ToggleSwitch(r, self.prefs.get("hotkeys"), lambda v: (self.set_pref("hotkeys", v), self.notify(
                "info", "system", "Kısayol ayarı kaydedildi", "Uygulamayı yeniden başlatınca uygulanır"))).pack(side="right"))
        row("Pano radarı", "Panoya şifreli mesaj veya kişi kartı kopyalandığında çözmeyi önerir.",
            lambda r: ToggleSwitch(r, self.prefs.get("radar"), lambda v: self.set_pref("radar", v)).pack(side="right"))
        row("Okuduktan sonra yok et", "Çözülen mesaj balonu bu süre sonunda kapanır.",
            lambda r: Segmented(r, BURN_PRESETS, lambda v: self.set_pref("burn_seconds", v), self.prefs.get("burn_seconds")).pack(side="right"))
        row("Parça boyutu", "Uzun mesajlar sohbet sınırına göre numaralı parçalara bölünür.",
            lambda r: Segmented(r, CHUNK_PRESETS, lambda v: self.set_pref("chunk_limit", v), self.prefs.get("chunk_limit")).pack(side="right"))

        def menu(r):
            if not winbridge.IS_WINDOWS:
                Chip(r, "YALNIZCA WINDOWS", DIM).pack(side="right")
                return
            on = winbridge.context_menu_installed()
            ToggleSwitch(r, on, self._toggle_context_menu).pack(side="right")
        row("Gezgin sağ tık menüsü", "Dosyalarda “ElfCaesar ile şifrele”, .elfvault'ta “çöz”, .elfcontact'ta “deftere ekle”.",
            menu, last=True)
        tk.Frame(card, bg=PANEL, height=8).pack()

    def _toggle_context_menu(self, value):
        from . import runtime
        gui_path = runtime.resource_dir() / "gui.py"
        icon = runtime.resource_dir() / "assets" / "elfcaesar.ico"
        ok = winbridge.install_context_menu(gui_path, icon if icon.exists() else None) if value else winbridge.uninstall_context_menu()
        self.notify("success" if ok else "error", "system",
                    ("Sağ tık menüsü eklendi" if value else "Sağ tık menüsü kaldırıldı") if ok else "Sağ tık menüsü değiştirilemedi",
                    "Windows 11'de “Diğer seçenekleri göster” altında" if value and ok else "")

    def _render_contacts(self):
        f = self.br_contacts
        for ch in f.winfo_children():
            ch.destroy()
        entries = self.book.sorted()
        if not entries:
            empty = tk.Frame(f, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            empty.pack(fill="x")
            tk.Label(empty, text="Kişi defteri boş", bg=INPUT, fg=FG_2, font=F["body_b"]).pack(pady=(14, 2))
            tk.Label(empty, text="Karşı taraf KARTIMI SOHBETTE PAYLAŞ ile kartını gönderir; sen kopyalarsın, pano radarı yakalar.",
                     bg=INPUT, fg=DIM, font=F["tiny"]).pack(pady=(0, 14))
            return
        for e in entries:
            fp = e["card"]["fingerprint"]
            col = GREEN if e["verified"] else AMBER
            r = tk.Frame(f, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            r.pack(fill="x", pady=3)
            tk.Frame(r, bg=col, width=3).pack(side="left", fill="y")
            mini_sigil(r, fp, 34).pack(side="left", padx=(10, 10), pady=8)
            t = tk.Frame(r, bg=INPUT)
            t.pack(side="left", fill="x", expand=True, pady=6)
            top = tk.Frame(t, bg=INPUT)
            top.pack(fill="x")
            tk.Label(top, text=e["alias"], bg=INPUT, fg=FG, font=F["body_b"]).pack(side="left")
            Chip(top, "DOĞRULANDI" if e["verified"] else "DOĞRULANMADI", col).pack(side="left", padx=8)
            tk.Label(t, text=f"{short_fingerprint(fp)}   ·   " + " · ".join(ca.safety_words(fp)), bg=INPUT, fg=DIM,
                     font=F["mono_xs"], anchor="w").pack(fill="x")
            StudioButton(r, "", lambda fp=fp: self.remove_contact(fp), "ghost", "trash", "sm", tooltip="Sil").pack(side="right", padx=(0, 8))
            StudioButton(r, "YAZ", lambda fp=fp: self.reply_to(fp), "secondary", "send", "sm").pack(side="right", padx=4)
            if not e["verified"]:
                StudioButton(r, "SESLİ DOĞRULA", lambda fp=fp: self.verify_contact(fp), "accent", "check", "sm").pack(side="right", padx=4)
