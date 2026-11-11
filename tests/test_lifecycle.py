import gzip
import json
import time

from studio_ui import breaches, lifecycle
from studio_ui.pwvault import Entry, PasswordVault

DAY = 86400


def _cat(items):
    return breaches.Catalog({"items": items, "latest": "2026-01-01", "fetched": ""})


def test_bundled_catalog_loads_and_matches():
    cat = breaches.Catalog.load()
    assert cat.size > 500 and cat.latest >= "2026-01-01"
    assert cat.for_domain("https://www.linkedin.com/login"), "LinkedIn ihlali katalogda olmalı"
    assert cat.for_domain("example-that-does-not-exist.tr") == []


def test_breach_status_respects_change_date_and_ack():
    b = {"n": "Ornek", "t": "Örnek", "d": "ornek.com", "bd": "2025-05-01", "ad": "2025-06-01", "c": 1000, "pw": True, "v": True}
    info = {"n": "Info", "t": "Info", "d": "ornek.com", "bd": "2025-05-01", "ad": "2025-06-01", "c": 5, "pw": False, "v": True}
    cat = _cat([b, info])
    old = Entry("Ö", "a", "Parola-123456!", "https://giris.ornek.com")
    old.changed = time.mktime((2024, 1, 1, 0, 0, 0, 0, 0, -1))
    st = cat.status(old)
    assert [x["n"] for x in st["open"]] == ["Ornek"] and [x["n"] for x in st["safe"]] == ["Info"]
    new = Entry("Ö", "a", "Parola-123456!", "https://ornek.com")
    new.changed = time.mktime((2025, 7, 1, 0, 0, 0, 0, 0, -1))
    assert cat.status(new)["open"] == []
    lifecycle.ack_breach(old, "Ornek")
    assert cat.status(old)["open"] == []


def test_plan_orders_and_states():
    now = time.time()
    cat = _cat([{"n": "X", "t": "X", "d": "x.com", "bd": "2026-01-01", "ad": "2026-01-02", "c": 9, "pw": True, "v": True}])
    a = Entry("X", "u", "Zq8#mVt2-LpW9xRk", "https://x.com"); a.changed = now - 400 * DAY
    b = Entry("Tekrar1", "u", "AyniParola-2026!", "https://a.com")
    c = Entry("Tekrar2", "u", "AyniParola-2026!", "https://b.com")
    d = Entry("Saglam", "u", "Hv7$kQ2-pLm9#Tz4", "https://d.com")
    e = Entry("Hatirlatma", "u", "Rt5!wQ8-zXn3@Kp6", "https://e.com"); e.rotate_days = 90; e.changed = now - 100 * DAY
    p = lifecycle.plan([d, c, b, a, e], cat, now=now)
    states = {i["entry"].title: i["state"] for i in p["items"]}
    assert states["X"] == "urgent" and states["Saglam"] == "ok"
    assert states["Tekrar1"] == "recommended" and states["Hatirlatma"] == "recommended"
    assert p["items"][0]["entry"].title == "X"
    assert any(r["key"] == "rotation_due" for i in p["items"] if i["entry"] is e for r in i["reasons"])
    lifecycle.snooze(b, 7, now=now)
    assert {i["entry"].title: i["state"] for i in lifecycle.plan([b, c], now=now)["items"]}["Tekrar1"] == "snoozed"


def test_change_flow_keeps_old_password_until_confirmed():
    meta = {}
    e = Entry("Site", "u", "Eski-Parola-2020!", "https://s.com")
    lifecycle.record_hibp(e, 42)
    assert lifecycle.hibp_valid(e)
    lifecycle.start_change(e, "Yeni-Guclu-Parola-77", "Sızıntı")
    assert e.password == "Eski-Parola-2020!" and e.pending["password"] == "Yeni-Guclu-Parola-77"
    p = lifecycle.plan([e])
    assert p["items"][0]["state"] == "pending"
    assert lifecycle.confirm_change(meta, e)
    assert e.password == "Yeni-Guclu-Parola-77" and e.pending == {}
    assert e.history[0]["password"] == "Eski-Parola-2020!"
    assert not lifecycle.hibp_valid(e), "parola değişince eski HIBP sonucu geçersiz"
    assert meta["timeline"][-1]["kind"] == "changed"
    assert lifecycle.stats(meta)["changed_30d"] == 1
    lifecycle.start_change(e, "Baska-1", "")
    lifecycle.cancel_change(e)
    assert e.pending == {} and e.password == "Yeni-Guclu-Parola-77"


def test_hibp_reason_in_plan():
    e = Entry("H", "u", "Hv7$kQ2-pLm9#Tz4", "https://h.com")
    lifecycle.record_hibp(e, 3)
    keys = [r["key"] for r in lifecycle.plan([e])["items"][0]["reasons"]]
    assert "hibp" in keys


def test_score_log_and_generated_history():
    meta = {}
    t = time.time()
    assert lifecycle.record_score(meta, 60, now=t)
    assert not lifecycle.record_score(meta, 60, now=t + 10)
    assert lifecycle.record_score(meta, 75, now=t + 20) and len(meta["score_log"]) == 1
    lifecycle.record_score(meta, 80, now=t + 2 * DAY)
    assert [x["s"] for x in meta["score_log"]] == [75, 80]
    for i in range(40):
        lifecycle.add_generated(meta, f"p{i}", "x.com")
    assert len(meta["gen_history"]) == 30 and meta["gen_history"][0]["p"] == "p39"


def test_new_fields_survive_save_and_old_vault_loads(tmp_path):
    path = tmp_path / "k.elfvault"
    pv = PasswordVault(path)
    pv.create("Ana-Parola-Uzun-2026!")
    e = Entry("S", "u", "Eski-Parola-2020!", "https://s.com", rotate_days=90)
    pv.add(e)
    lifecycle.start_change(e, "Yeni-1-Parola!!", "test")
    lifecycle.add_generated(pv.meta, "Yeni-1-Parola!!", "s.com")
    pv.save()
    pv2 = PasswordVault(path)
    pv2.unlock("Ana-Parola-Uzun-2026!")
    e2 = pv2.entries[0]
    assert e2.rotate_days == 90 and e2.pending["password"] == "Yeni-1-Parola!!"
    assert pv2.meta["gen_history"][0]["d"] == "s.com"


def test_compact_filters_and_gz_roundtrip(tmp_path):
    raw = [{"Name": "A", "Title": "A", "Domain": "A.com", "BreachDate": "2020-01-01", "AddedDate": "2020-02-01T00:00:00Z",
            "PwnCount": 5, "DataClasses": ["Passwords", "Email addresses"], "IsVerified": True},
           {"Name": "Spam", "Domain": "s.com", "IsSpamList": True, "DataClasses": []},
           {"Name": "NoDomain", "Domain": "", "DataClasses": []}]
    cat = breaches.compact(raw)
    assert [i["n"] for i in cat["items"]] == ["A"] and cat["items"][0]["d"] == "a.com" and cat["items"][0]["pw"]
    calls = []

    def fetch(url):
        calls.append(url)
        return json.dumps(raw).encode()
    import studio_ui.runtime as rt
    orig = rt.local_data_dir
    rt.local_data_dir = lambda: tmp_path
    try:
        breaches.refresh(fetch)
        d = json.loads(gzip.decompress((tmp_path / breaches.LOCAL_NAME).read_bytes()))
        assert d["items"][0]["n"] == "A" and calls == [breaches.API_URL]
    finally:
        rt.local_data_dir = orig
