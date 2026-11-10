"""Rozetler: tanımlar, görseller, olay ve durum kuralları."""
from pathlib import Path

from studio_ui import badges as B

ROOT = Path(__file__).resolve().parent.parent


def test_fifteen_badges_with_assets():
    assert len(B.BADGES) == 15 and len(B.BY_ID) == 15
    for bid, name, lang, meaning, title, how, rarity in B.BADGES:
        assert rarity in B.RARITY and name and meaning and how
        for s in (40, 64, 128, 256):
            assert (ROOT / "assets" / "badges" / f"{bid}_{s}.png").exists()
        for s in (40, 64, 128):
            assert (ROOT / "assets" / "badges" / f"{bid}_{s}_off.png").exists()


def test_event_rules():
    assert B.for_event("Kodlama tamamlandı") == ["tiw"]
    assert B.for_event("Klasör kasası oluşturuldu ve doğrulandı") == ["elessar"]
    assert B.for_event("Kaydedildi") == []
    for _p, bid in B.EVENT_RULES:
        assert bid in B.BY_ID


def test_award_once_and_aran():
    prefs = {"badges": {}}
    assert B.award(prefs, "tiw") and not B.award(prefs, "tiw")
    assert not B.award(prefs, "yok")
    for bid in B.BY_ID:
        if bid != "aran":
            B.award(prefs, bid)
    assert "aran" in B.state_badges(prefs, 0)
    assert B.progress(prefs) == (14, 15)


def test_state_rules():
    prefs = {"visited": ["home", "encode", "decode", "analysis", "vault", "bridge", "security", "tengwar"],
             "capture_shield": "all", "idle_lock_minutes": 5, "identity_path": "x.elfid", "paper_backup_date": "", "badges": {}}
    got = B.state_badges(prefs, 95)
    assert "galadh" in got and "tirith" in got and "certh" not in got and "mithril" not in got
    prefs["visited"].append("alphabet")
    prefs["paper_backup_date"] = "10.11.2026"
    got = B.state_badges(prefs, 95)
    assert "certh" in got and "mithril" in got
    assert "mithril" not in B.state_badges(prefs, 80)


def test_settings_keep_badges(tmp_path):
    from studio_ui import settings
    p = tmp_path / "s.json"
    prefs = settings.load(p)
    prefs["badges"]["tiw"] = "10.11.2026"
    settings.save(prefs, p)
    assert settings.load(p)["badges"] == {"tiw": "10.11.2026"}
    assert settings.load(tmp_path / "yok.json")["badges"] == {}
