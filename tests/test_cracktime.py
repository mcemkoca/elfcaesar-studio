from studio_ui.cracktime import estimate, format_duration, risk_level, SECONDS_PER_YEAR, elfc2_crack, method_risks


def test_format_duration_turkish():
    assert format_duration(0.2) == "anında"
    assert format_duration(45) == "45 saniye"
    assert format_duration(7200) == "2 saat"
    assert format_duration(3 * 86400) == "3 gün"
    assert format_duration(5 * SECONDS_PER_YEAR) == "5 yıl"
    assert format_duration(2.5e6 * SECONDS_PER_YEAR) == "2,5 milyon yıl"
    assert format_duration(1e30) == "evrenin yaşından uzun"


def test_scenarios_order_and_vault_slower_than_fast_hash():
    r = estimate("mavi-kuzgun-taş-köprü-fener-yedi")
    secs = {row["key"]: row["seconds"] for row in r["scenarios"]}
    assert secs["online_limited"] > secs["online_fast"] > secs["vault_1gpu"] > secs["vault_farm"] > secs["fast_hash"]
    assert secs["vault_1gpu"] / secs["fast_hash"] > 1e7


def test_weak_password_is_critical_strong_is_safe():
    weak = {row["key"]: row["risk"] for row in estimate("Galatasaray1905")["scenarios"]}
    strong = {row["key"]: row["risk"] for row in estimate("KutupYildizi!2026-Mavi-Fener")["scenarios"]}
    assert weak["vault_farm"] in ("critical", "weak")
    assert strong["vault_farm"] == "excellent"
    assert risk_level(10) == "critical"


def test_method_risks_detect_patterns():
    m = {x["key"]: x["level"] for x in method_risks("Parola2024!")}
    assert m["dictionary"] == "high" and m["hybrid"] == "high" and m["brute"] == "high"
    m2 = {x["key"]: x["level"] for x in method_risks("mavi-kuzgun-taş-köprü-fener-yedi")}
    assert m2["dictionary"] == "low" and m2["brute"] == "low"


def test_elfc2_is_instant():
    assert elfc2_crack()["guesses"] == 29


def test_leak_database_and_blocking():
    from studio_ui import leaks
    assert leaks.size() > 10000
    for weak in ("Galatasaray1905", "P@ssw0rd", "Zeynep1990", "parolaparola", "Qwerty123!"):
        assert leaks.is_blocked(weak), weak
    for strong in ("KutupYildizi!2026-Mavi", "mavi-kuzgun-taş-köprü-fener-yedi", "Tr9#kLm2!vQx"):
        assert leaks.check(strong) is None, strong
    assert leaks.check("İSTANBUL34")["base"] == "istanbul"


def test_hardware_profiles_and_cost():
    from studio_ui.cracktime import estimate_hw, format_money, HARDWARE_ORDER
    pw = "mavi-kuzgun-taş-köprü-fener-yedi"
    times = [ {r["key"]: r["seconds"] for r in estimate_hw(pw, hw)["scenarios"]}["vault_hw"] for hw in HARDWARE_ORDER]
    assert times == sorted(times, reverse=True)
    cloud = {r["key"]: r for r in estimate_hw(pw, "cloud")["scenarios"]}
    assert cloud["vault_hw"]["cost"] > 1e6 and cloud["online_fast"]["cost"] is None
    assert estimate_hw(pw, "rtx4090")["scenarios"][2]["cost"] is None
    assert format_money(1234) == "1,2 bin $" and format_money(5e6) == "5,0 milyon $"
    assert format_money(1e20).startswith("dünya")


def test_stuffing_method_uses_leak_list():
    m = {x["key"]: x for x in method_risks("Galatasaray1905")}
    assert m["stuffing"]["level"] == "high" and "galatasaray" in m["stuffing"]["why"]


def test_selftest_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    import gui
    assert gui.parse_args(["--selftest"]) == ("selftest", None)
    r = gui.selftest()
    assert r["ok"] and r["checks"]["leak_detects_turkish"]
    assert (tmp_path / "ElfCaesar" / "selftest.json").exists()
