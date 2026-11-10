"""6.6 güvenlik zekâsı testleri (motorlara dokunmaz)."""
from studio_ui.security import (password_strength, scan_sensitive, SecurityState, assess, tier_for,
                                SECURITY_TIERS)
from studio_ui import settings
from elfcaesar.secure import generate_passphrase


def test_password_levels_order():
    weak = password_strength("123456")
    mid = password_strength("Kalem2024!x")
    strong = password_strength("mavi-kuzgun-taş-köprü-fener-yedi")
    assert weak["level"] == 0 and not weak["meets_min"]
    assert mid["level"] <= 1  # 12 bayt altı en fazla Tahta Kalkan
    assert strong["level"] >= 3 and strong["meets_min"]
    assert strong["bits"] > weak["bits"]


def test_common_word_penalised():
    assert password_strength("ParolaParola1!")["bits"] < password_strength("KuzgunMavi71!x")["bits"]


def test_generated_passphrase_is_mithril():
    assert password_strength(generate_passphrase(5))["level"] == 4


def test_empty_password():
    r = password_strength("")
    assert r["level"] == 0 and r["hints"]


def test_scan_sensitive_detects_types_without_values():
    text = ("mail: ali@ornek.com IBAN TR33 0006 1005 1978 6457 8413 26 kart 4111 1111 1111 1111 "
            "tc 10000000146 tel 0532 123 45 67 şifre: gizli123")
    kinds = {f["kind"] for f in scan_sensitive(text)}
    assert {"email", "iban", "card", "tckn", "phone", "secret"} <= kinds
    assert all("ali@" not in str(f) and "4111" not in str(f) for f in scan_sensitive(text))


def test_scan_ignores_plain_text_and_bad_numbers():
    assert scan_sensitive("Merhaba dünya, yarın 10:30'da buluşalım.") == []
    assert not any(f["kind"] == "card" for f in scan_sensitive("4111 1111 1111 1112"))
    assert not any(f["kind"] == "tckn" for f in scan_sensitive("12345678901"))


def test_assess_perfect_and_tiers():
    r = assess(SecurityState(identity_known=True, password_vault=True, paper_backup=True, vault_health=95))
    assert r["score"] == 100 and r["tier_name"] == "Mithril" and r["open_issues"] == 0
    fresh = assess(SecurityState())  # 6.10.2: yeni kurulum artık Mithril 100 göstermez
    assert fresh["score"] < 92 and fresh["tier_name"] != "Mithril" and fresh["open_issues"] >= 2
    risky = assess(SecurityState(identity_known=True, password_vault=True, paper_backup=True, vault_health=69))
    assert risky["tier_name"] != "Mithril"
    assert tier_for(0)[1] == SECURITY_TIERS[0][1] and tier_for(85)[1] == "Kale"


def test_assess_orders_by_advice_level():
    s = SecurityState(crypto_ok=False, clipboard_guard=False, unpinned_opens=2, last_password_level=0)
    r = assess(s)
    levels = [a["level"] for a in r["advice"]]
    assert levels[0] == "critical" and levels.index("high") < levels.index("medium")
    assert r["score"] < 40 and r["tier_name"] == "Çırak"
    assert r["next_tier"][1] == "Muhafız"


def test_settings_roundtrip_and_type_safety(tmp_path):
    p = tmp_path / "s.json"
    assert settings.save({"clipboard_seconds": 15, "idle_lock_minutes": 0, "password": "x"}, p)
    assert "password" not in p.read_text()
    data = settings.load(p)
    assert data["clipboard_seconds"] == 15 and data["idle_lock_minutes"] == 0
    p.write_text('{"clipboard_seconds": "çok"}')
    assert settings.load(p)["clipboard_seconds"] == 30
