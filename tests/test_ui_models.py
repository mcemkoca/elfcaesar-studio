"""6.5 arayüz yardımcıları için testler (motorlara dokunmaz)."""
from studio_ui.activity import ActivityLog
from studio_ui.scoring import turkish_score, rank, best_shift
from studio_ui.sigil import sigil, format_fingerprint, short_fingerprint
from studio_ui.dnd import parse_drop
from elfcaesar.engine import encode, brute_force

FP = "a3f1" * 16


def test_activity_never_needs_content_and_is_bounded():
    log = ActivityLog(limit=3)
    for i in range(5):
        log.add("codec", "success", f"İşlem {i}")
    assert len(log) == 3 and log.recent(1)[0].title == "İşlem 4"


def test_activity_unknown_category_and_level_normalised():
    item = ActivityLog().add("weird", "loud", "x")
    assert item.category == "system" and item.level == "info"


def test_activity_per_minute_buckets():
    log = ActivityLog()
    now = 10_000.0
    log.add("codec", "success", "a", timestamp=now - 5)
    log.add("vault", "success", "b", timestamp=now - 65)
    log.add("vault", "error", "c", timestamp=now - 3600)
    buckets = log.per_minute(30, now=now)
    assert len(buckets) == 30 and buckets[-1] == 1 and buckets[-2] == 1 and sum(buckets) == 2


def test_activity_filter_and_rate():
    log = ActivityLog()
    log.add("vault", "success", "Mesaj şifrelendi")
    log.add("vault", "error", "Parola hatalı")
    log.add("codec", "success", "Kodlama")
    assert len(log.filtered("vault")) == 2
    assert [i.title for i in log.filtered(query="parola")] == ["Parola hatalı"]
    assert abs(log.success_rate() - 2 / 3) < 1e-9
    assert log.by_category()["vault"] == 2


def test_turkish_score_prefers_real_text():
    plain = "Merhaba dünya, bu bir deneme metnidir ve Türkçe yazılmıştır."
    scored = rank(brute_force(encode(plain, 11)))
    assert best_shift(scored) == 11
    assert turkish_score(plain) > 60
    assert turkish_score("") == 0 and turkish_score("12345 !!!") == 0


def test_sigil_deterministic_and_symmetric():
    a, b = sigil(FP), sigil(FP)
    assert a == b and a["cells"]
    size = a["size"]
    cells = set(a["cells"])
    assert all((r, size - 1 - c) in cells for r, c in cells)
    assert sigil("b" * 64) != a


def test_fingerprint_formatting():
    text = format_fingerprint(FP)
    assert text.count("\n") == 1 and text.split()[0] == "A3F1"
    assert short_fingerprint(FP).startswith("A3F1 A3F1 …")


def test_parse_drop_handles_braces_and_spaces():
    assert parse_drop("{C:/My Files/a b.txt} C:/c.txt") == ["C:/My Files/a b.txt", "C:/c.txt"]
    assert parse_drop("/tmp/x.elfvault") == ["/tmp/x.elfvault"]
    assert parse_drop("") == []
