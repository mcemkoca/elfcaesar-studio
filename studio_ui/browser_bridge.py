"""Tarayıcı köprüsü: ElfCaesar tarayıcı eklentisi ↔ yerel yardımcı (native messaging) ↔ çalışan uygulama.

Güvenlik kuralları
  • Eklenti önce EŞLEŞİR: uygulamada kullanıcı onay verir, eklentiye rastgele bir anahtar verilir; uygulama
    yalnızca anahtarın SHA-256 özetini saklar. Eşleşmemiş istekler reddedilir.
  • Parola yalnızca sayfanın kayıtlı alan adıyla BİREBİR aynı kayıt için verilir (alt alan adları dahil,
    ör. accounts.google.com → google.com). Benzer görünen alan adına hiçbir şey verilmez, oltalama uyarısı döner.
  • Parola kasası kilitliyse hiçbir şey dönmez.
"""
from __future__ import annotations

import hashlib
import queue
import secrets
import threading
import time

from . import pwaudit
from .pwvault import registrable_domain

HOST_NAME = "com.dante.elfcaesar"
PROTOCOL = 1


def key_hash(key: str) -> str:
    return hashlib.sha256(("ELFBROWSER1\0" + key).encode()).hexdigest()


class BrowserBridge:
    def __init__(self, app):
        self.app = app
        self._assoc_lock = threading.Lock()
        self._assoc_block_until = 0.0
        self.ui_tasks: queue.Queue = queue.Queue()
        self.events: queue.Queue = queue.Queue()

    # ------------------------------------------------------------ sunucu iş parçacığı
    def handle(self, data: dict) -> dict:
        req = data.get("request")
        try:
            if req == "status":
                return self._status(data)
            if req == "associate":
                return self._associate(data)
            if not self._paired(data.get("key", "")):
                return {"ok": False, "error": "not_paired"}
            if req == "query":
                return self._query(data)
            if req == "get":
                return self._get(data)
            if req == "open_app":
                self.ui_tasks.put(("open", None))
                return {"ok": True}
            return {"ok": False, "error": "unknown_request"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": "internal", "detail": str(exc)[:200]}

    def _vault(self):
        pv = self.app.__dict__.get("_pv")
        return pv if pv is not None and pv.is_open else None

    def _paired(self, key: str) -> bool:
        if not key:
            return False
        h = key_hash(key)
        return any(secrets.compare_digest(h, k.get("hash", "")) for k in self.app.prefs.get("browser_keys") or [])

    def _status(self, data):
        from .version import APP_VERSION
        return {"ok": True, "protocol": PROTOCOL, "version": APP_VERSION, "paired": self._paired(data.get("key", "")),
                "vault_open": self._vault() is not None}

    def _associate(self, data):
        browser = str(data.get("browser") or "Tarayıcı")[:40]
        # Kötüye kullanım koruması: aynı anda tek istek; reddedilen istekten sonra 30 sn bekleme
        if time.time() < self._assoc_block_until or not self._assoc_lock.acquire(blocking=False):
            return {"ok": False, "error": "busy"}
        try:
            return self._associate_locked(data, browser)
        finally:
            self._assoc_lock.release()

    def _associate_locked(self, data, browser):
        done = threading.Event()
        box = {"ok": False}
        code = str(data.get("code") or "")[:6] or f"{secrets.randbelow(10000):04d}"
        self.ui_tasks.put(("associate", (browser, code, box, done)))
        if not done.wait(90):
            return {"ok": False, "error": "timeout"}
        if not box["ok"]:
            self._assoc_block_until = time.time() + 30
            return {"ok": False, "error": "denied"}
        key = secrets.token_urlsafe(32)
        keys = list(self.app.prefs.get("browser_keys") or [])
        keys.append({"hash": key_hash(key), "browser": browser, "date": time.strftime("%d.%m.%Y")})
        self.ui_tasks.put(("save_keys", keys[-8:]))
        return {"ok": True, "key": key, "code": code}

    def _query(self, data):
        origin = str(data.get("origin") or "")
        domain = registrable_domain(origin)
        pv = self._vault()
        if pv is None:
            return {"ok": True, "locked": True, "entries": [], "lookalike": None}
        known = {e.domain for e in pv.entries if e.domain}
        look = pwaudit.lookalike(origin, known)
        if look:
            self.events.put(("phish", look))
            return {"ok": True, "locked": False, "entries": [], "lookalike": look, "domain": domain}
        entries = [{"id": e.id, "title": e.title, "username": e.username}
                   for e in sorted(pv.entries, key=lambda e: -e.used) if e.domain and e.domain == domain]
        return {"ok": True, "locked": False, "entries": entries, "lookalike": None, "domain": domain}

    def _get(self, data):
        pv = self._vault()
        if pv is None:
            return {"ok": False, "error": "locked"}
        origin = str(data.get("origin") or "")
        if not origin.lower().startswith("https://") and not origin.lower().startswith("http://localhost"):
            insecure = True
        else:
            insecure = False
        e = pv.get(str(data.get("id") or ""))
        if e is None or not e.domain or e.domain != registrable_domain(origin):
            return {"ok": False, "error": "domain_mismatch"}
        # Sürüm düşürme koruması: kayıt https ise şifresiz (http) sayfaya parola verilmez (ağdaki saldırgan sahte form ekleyebilir)
        if (e.url or "").lower().startswith("https://") and origin.lower().startswith("http://") and \
                not origin.lower().startswith(("http://localhost", "http://127.0.0.1")):
            self.events.put(("downgrade", (e.title, registrable_domain(origin))))
            return {"ok": False, "error": "insecure_origin"}
        e.used = time.time()
        self.events.put(("filled", (e.title, registrable_domain(origin), insecure)))
        return {"ok": True, "username": e.username, "password": e.password, "insecure": insecure}

    # ------------------------------------------------------------ Tk iş parçacığı
    def pump(self):
        """Tk döngüsünden çağrılır: onay pencereleri ve bildirimler."""
        from tkinter import messagebox
        app = self.app
        while True:
            try:
                kind, payload = self.ui_tasks.get_nowait()
            except queue.Empty:
                break
            if kind == "associate":
                browser, code, box, done = payload
                app.deiconify()
                app.lift()
                box["ok"] = messagebox.askyesno(
                    "Tarayıcı eklentisi eşleştirme",
                    f"{browser} içindeki ElfCaesar eklentisi parola kasana bağlanmak istiyor.\n\n"
                    f"Eklentide görünen kod: {code}\n\nKodlar aynıysa ve bu isteği sen başlattıysan EVET'e bas. "
                    "Eklenti yalnızca ziyaret ettiğin sitenin birebir kayıtlarını görebilir.", parent=app)
                done.set()
                app.notify("success" if box["ok"] else "warning", "vault",
                           "Tarayıcı eklentisi eşleştirildi" if box["ok"] else "Tarayıcı eşleştirmesi reddedildi", browser)
            elif kind == "save_keys":
                app.set_pref("browser_keys", payload)
            elif kind == "open":
                app.deiconify()
                app.lift()
                app.show_page("passwords")
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "filled":
                title, domain, insecure = payload
                app.notify("warning" if insecure else "success", "vault", "Tarayıcıda dolduruldu",
                           f"{title} · {domain}" + (" · DİKKAT: şifresiz bağlantı" if insecure else ""), toast=False)
                try:
                    app.pv.save()
                except Exception:
                    pass
            elif kind == "downgrade":
                app.notify("warning", "vault", "Şifresiz sayfaya parola verilmedi",
                           f"{payload[0]} kaydı https; sayfa http · {payload[1]}")
            elif kind == "phish":
                app.notify("error", "vault", "Oltalama uyarısı: tarayıcıda sahte site",
                           f"{payload['fake']} gerçek {payload['real']} değil · {payload['why']}")
