"""6.11 Tarayıcı köprüsü: yeni parola önerme, form denetimi, kaydetme / güncelleme / değişim onayı."""
import threading

from studio_ui import browser_bridge as bb, lifecycle, pwgen
from studio_ui.pwvault import Entry, PasswordVault
import native_host


class FakeApp:
    def __init__(self, tmp_path):
        self.prefs = {"browser_keys": []}
        self._pv = PasswordVault(tmp_path / "k.elfvault")
        self._pv.create("Test-Ana-Parola-2026!")
        self._pv.add(Entry("Elf Market", "ayse@ornek.com", "Eski-Parola-1!", "https://www.elfmarket.com"))

    @property
    def pv(self):
        return self._pv

    def gen_policy(self, domain=""):
        return pwgen.Policy(length=20)

    def generate_for(self, domain="", via="", policy=None):
        pw = pwgen.generate(policy)
        lifecycle.add_generated(self._pv.meta, pw, domain, via)
        return pw


def _paired(tmp_path):
    app = FakeApp(tmp_path)
    br = bb.BrowserBridge(app)
    key = "k" * 40
    app.prefs["browser_keys"] = [{"hash": bb.key_hash(key)}]
    stop = threading.Event()

    def pump():  # Tk iş parçacığının yerine
        while not stop.is_set():
            try:
                kind, payload = br.ui_tasks.get(timeout=0.05)
            except Exception:
                continue
            if kind == "call":
                fn, box, done = payload
                try:
                    box["result"] = fn()
                except Exception as exc:
                    box["error"] = str(exc)
                done.set()
    t = threading.Thread(target=pump, daemon=True)
    t.start()
    return app, br, key, stop


def test_generate_follows_site_rules_and_is_remembered(tmp_path):
    app, br, key, stop = _paired(tmp_path)
    try:
        r = br.handle({"request": "generate", "key": key, "origin": "https://www.elfmarket.com",
                       "rules": {"maxlength": 12, "passwordrules": "required: lower, upper, digit; allowed: [-_]"}})
        assert r["ok"] and len(r["password"]) == 12 and set(r["password"]) <= set(pwgen.LOWER + pwgen.UPPER + pwgen.DIGITS + "-_")
        assert app.pv.meta["gen_history"][0]["p"] == r["password"] and app.pv.meta["gen_history"][0]["d"] == "elfmarket.com"
        assert br.handle({"request": "generate", "origin": "https://www.elfmarket.com"})["error"] == "not_paired"
        ph = br.handle({"request": "generate", "key": key, "origin": "https://elfmarket.com.giris-yap.xyz"})
        assert ph["error"] == "lookalike"
    finally:
        stop.set()


def test_check_and_save_flow(tmp_path):
    app, br, key, stop = _paired(tmp_path)
    o = "https://www.elfmarket.com"
    try:
        def check(u, p):
            return br.handle({"request": "check", "key": key, "origin": o, "username": u, "password": p})["state"]
        assert check("ayse@ornek.com", "Eski-Parola-1!") == "same"
        assert check("ayse@ornek.com", "Baska-Parola-2!") == "different"
        assert check("yeni@ornek.com", "X-1") == "new"
        assert br.handle({"request": "check", "key": key, "origin": "http://www.elfmarket.com", "username": "a", "password": "b"})["state"] == "insecure"
        # yeni kayıt
        r = br.handle({"request": "save", "key": key, "origin": "https://kayit.yenisite.com.tr", "username": "ali", "password": "Yeni-1-Parola!"})
        assert r == {"ok": True, "result": "created", "title": "Yenisite"}
        assert any(e.domain == "yenisite.com.tr" and e.source == "Tarayıcı eklentisi" for e in app.pv.entries)
        # güncelleme: eski parola geçmişe
        r = br.handle({"request": "save", "key": key, "origin": o, "username": "ayse@ornek.com", "password": "Guncel-Parola-3!"})
        e = next(x for x in app.pv.entries if x.domain == "elfmarket.com")
        assert r["result"] == "updated" and e.password == "Guncel-Parola-3!" and e.history[0]["password"] == "Eski-Parola-1!"
        # bekleyen değişim tarayıcıda onaylanır
        lifecycle.start_change(e, "Plan-Parolasi-4!", "test")
        assert check("ayse@ornek.com", "Plan-Parolasi-4!") == "pending_match"
        r = br.handle({"request": "save", "key": key, "origin": o, "username": "ayse@ornek.com", "password": "Plan-Parolasi-4!"})
        assert r["result"] == "confirmed" and e.password == "Plan-Parolasi-4!" and e.pending == {}
        assert app.pv.meta["timeline"][-1]["kind"] == "changed"
        # şifresiz sayfa ve oltalama reddedilir
        assert br.handle({"request": "save", "key": key, "origin": "http://www.elfmarket.com", "username": "a", "password": "b"})["error"] == "insecure_origin"
        assert br.handle({"request": "save", "key": key, "origin": "https://elfmarket.com.giris-yap.xyz", "username": "a", "password": "b"})["error"] == "lookalike"
        # kasa diske yazıldı
        pv2 = PasswordVault(app.pv.path)
        pv2.unlock("Test-Ana-Parola-2026!")
        assert {x.domain for x in pv2.entries} >= {"elfmarket.com", "yenisite.com.tr"}
    finally:
        stop.set()


def test_save_rate_limit_and_locked(tmp_path):
    app, br, key, stop = _paired(tmp_path)
    try:
        for i in range(bb.SAVE_LIMIT_PER_MIN):
            assert br.handle({"request": "save", "key": key, "origin": "https://a.com", "username": f"u{i}", "password": "P-1!xxxxxx"})["ok"]
        assert br.handle({"request": "save", "key": key, "origin": "https://a.com", "username": "z", "password": "P"})["error"] == "rate_limited"
        app.pv.lock()
        assert br.handle({"request": "generate", "key": key, "origin": "https://a.com"})["error"] == "locked"
    finally:
        stop.set()


def test_native_host_forwards_new_fields_only():
    seen = {}
    native_host.handle({"request": "save", "origin": "https://a.com", "username": "u", "password": "p", "rules": {}, "evil": 1},
                       forward=lambda p: seen.update(p) or {"ok": True})
    assert seen == {"request": "save", "origin": "https://a.com", "username": "u", "password": "p", "rules": {}}
