"""6.10.1 Tarayıcı köprüsü: eşleştirme, birebir alan adı, oltalama, kilitli kasa, yerel yardımcı çerçeveleme."""
import io
import json
import threading

import pytest

from studio_ui import browser_bridge as bb, runtime
from studio_ui.pwvault import Entry, PasswordVault
import native_host


class FakeApp:
    def __init__(self, tmp_path):
        self.prefs = {"browser_keys": []}
        self._pv = PasswordVault(tmp_path / "k.elfvault")
        self._pv.create("Test-Ana-Parola-2026!")
        self._pv.add(Entry("Trendyol", "ayse@gmail.com", "T-parola-1", "https://www.trendyol.com"))
        self._pv.add(Entry("Google", "ayse@gmail.com", "G-parola-2", "https://accounts.google.com"))


def _approve(bridge, app, ok=True):
    kind, payload = bridge.ui_tasks.get(timeout=5)
    assert kind == "associate"
    browser, code, box, done = payload
    assert code == "4821"
    box["ok"] = ok
    done.set()
    if ok:
        kind, keys = bridge.ui_tasks.get(timeout=5)
        app.prefs["browser_keys"] = keys


def _pair(bridge, app):
    t = threading.Thread(target=_approve, args=(bridge, app))
    t.start()
    r = bridge.handle({"request": "associate", "browser": "Google Chrome", "code": "4821"})
    t.join()
    return r


def test_pairing_and_strict_domain(tmp_path):
    app = FakeApp(tmp_path)
    br = bb.BrowserBridge(app)
    assert br.handle({"request": "query", "origin": "https://www.trendyol.com"})["error"] == "not_paired"
    r = _pair(br, app)
    assert r["ok"] and r["key"] and r["key"] not in json.dumps(app.prefs)  # yalnızca özet saklanır
    key = r["key"]
    q = br.handle({"request": "query", "key": key, "origin": "https://www.trendyol.com"})
    assert [e["title"] for e in q["entries"]] == ["Trendyol"] and "password" not in json.dumps(q)
    eid = q["entries"][0]["id"]
    g = br.handle({"request": "get", "key": key, "origin": "https://www.trendyol.com", "id": eid})
    assert g["ok"] and g["password"] == "T-parola-1"
    # aynı kayıt başka alan adına verilmez
    assert br.handle({"request": "get", "key": key, "origin": "https://evil.example", "id": eid})["error"] == "domain_mismatch"
    # alt alan adı: mail.google.com → google.com kaydı
    q2 = br.handle({"request": "query", "key": key, "origin": "https://mail.google.com"})
    assert [e["title"] for e in q2["entries"]] == ["Google"]
    # oltalama
    q3 = br.handle({"request": "query", "key": key, "origin": "https://trendyol.com.giris-yap.xyz"})
    assert q3["lookalike"]["real"] == "trendyol.com" and q3["entries"] == []
    # yanlış anahtar
    assert br.handle({"request": "query", "key": "sahte", "origin": "https://www.trendyol.com"})["error"] == "not_paired"
    # kilitli kasa
    app._pv.lock()
    assert br.handle({"request": "query", "key": key, "origin": "https://www.trendyol.com"})["locked"]
    assert br.handle({"request": "get", "key": key, "origin": "https://www.trendyol.com", "id": eid})["error"] == "locked"


def test_pairing_denied(tmp_path):
    app = FakeApp(tmp_path)
    br = bb.BrowserBridge(app)
    t = threading.Thread(target=_approve, args=(br, app, False))
    t.start()
    r = br.handle({"request": "associate", "browser": "Edge", "code": "4821"})
    t.join()
    assert r == {"ok": False, "error": "denied"} and app.prefs["browser_keys"] == []


def test_server_roundtrip_and_native_host(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app = FakeApp(tmp_path)
    br = bb.BrowserBridge(app)
    srv = runtime.InstanceServer()
    srv.request_handler = br.handle
    assert srv.start()
    try:
        s = runtime.request({"request": "status"})
        assert s["ok"] and s["vault_open"] and not s["paired"]
        # yerel yardımcı: 4 bayt uzunluk + JSON
        buf = io.BytesIO()
        native_host.write_message(buf, {"request": "status", "rid": 7})
        buf.seek(0)
        msg = native_host.read_message(buf)
        resp = native_host.handle(msg)
        assert resp["ok"] and resp["rid"] == 7
        assert native_host.handle({"request": "rm -rf"})["error"] == "unknown_request"
        # eski komut yolu hâlâ çalışır
        assert runtime.forward_to_running("show", None)
        assert srv.poll() == [{"action": "show", "path": None}]
    finally:
        srv.stop()
    assert runtime.request({"request": "status"})["error"] == "app_not_running"


def test_extension_manifest_matches_host():
    from pathlib import Path
    import base64, hashlib
    root = Path(__file__).resolve().parent.parent / "browser-extension"
    man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    host = json.loads((root / "com.dante.elfcaesar.json").read_text(encoding="utf-8"))
    der = base64.b64decode(man["key"])
    ext_id = "".join(chr(ord("a") + int(c, 16)) for c in hashlib.sha256(der).hexdigest()[:32])
    assert host["allowed_origins"] == [f"chrome-extension://{ext_id}/"]
    assert host["name"] == bb.HOST_NAME and "nativeMessaging" in man["permissions"]
    from studio_ui.version import APP_VERSION
    assert man["version"] == APP_VERSION


def test_security_review_fixes(tmp_path):
    from studio_ui.pwvault import registrable_domain
    # paylaşımlı barındırma: farklı sahipler aynı alan adı sayılmaz
    assert registrable_domain("https://ayse.github.io/") == "ayse.github.io"
    assert registrable_domain("https://saldirgan.github.io/") != registrable_domain("https://ayse.github.io/")
    assert registrable_domain("x.y.herokuapp.com") == "y.herokuapp.com"
    assert registrable_domain("https://www.trendyol.com") == "trendyol.com"
    app = FakeApp(tmp_path)
    app._pv.add(Entry("Blog", "ayse", "B-parola", "https://ayse.github.io"))
    br = bb.BrowserBridge(app)
    key = _pair(br, app)["key"]
    assert br.handle({"request": "query", "key": key, "origin": "https://saldirgan.github.io"})["entries"] == []
    # https kaydı http sayfasına verilmez (sürüm düşürme)
    tid = br.handle({"request": "query", "key": key, "origin": "https://www.trendyol.com"})["entries"][0]["id"]
    assert br.handle({"request": "get", "key": key, "origin": "http://www.trendyol.com", "id": tid})["error"] == "insecure_origin"
    # eşleştirme: reddedilince 30 sn kilit, aynı anda tek istek
    t = threading.Thread(target=_approve, args=(br, app, False))
    t.start()
    assert br.handle({"request": "associate", "browser": "X", "code": "4821"})["error"] == "denied"
    t.join()
    assert br.handle({"request": "associate", "browser": "X", "code": "4821"})["error"] == "busy"


def test_native_host_passes_pairing_code():
    seen = {}
    native_host.handle({"request": "associate", "code": "4821", "browser": "Edge", "evil": 1}, forward=lambda p: seen.update(p) or {"ok": True})
    assert seen == {"request": "associate", "code": "4821", "browser": "Edge"}


def test_extension_packages(tmp_path):
    import zipfile
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packaging"))
    import package_extensions as pe
    r = pe.build(tmp_path)
    store = json.loads(zipfile.ZipFile(r["store"]).read("manifest.json"))
    ff = json.loads(zipfile.ZipFile(r["xpi"]).read("manifest.json"))
    assert "key" not in store and "key" not in ff and "service_worker" in store["background"]
    assert ff["background"] == {"scripts": ["background.js"]} and ff["browser_specific_settings"]["gecko"]["id"] == pe.FIREFOX_ID
    host = json.loads((tmp_path / "com.dante.elfcaesar.firefox.json").read_text(encoding="utf-8"))
    assert host["allowed_extensions"] == [pe.FIREFOX_ID] and host["name"] == bb.HOST_NAME
    assert "web_accessible_resources" not in store
