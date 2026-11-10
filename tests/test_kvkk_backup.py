"""6.8.3 kâğıt yedek ve 6.9.0 KVKK Kalkanı testleri."""
import zipfile
import pytest
from studio_ui import kvkk, paperbackup as pb
from studio_ui.capture import protect, supported

SAMPLE = "Müşteri: Ali Veli, TC 10000000146, IBAN TR33 0006 1005 1978 6457 8413 26, kart 4111 1111 1111 1111, ali@ornek.com"


def test_scan_text_docx_xlsx_and_skips(tmp_path):
    (tmp_path / "musteri.txt").write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "eski.csv").write_bytes("ad;tel\nAyşe;0532 123 45 67\n".encode("cp1254"))
    (tmp_path / "temiz.md").write_text("Toplantı notları, kişisel veri yok.", encoding="utf-8")
    (tmp_path / "foto.jpg").write_bytes(b"\xff\xd8binary")
    with zipfile.ZipFile(tmp_path / "sozlesme.docx", "w") as z:
        z.writestr("word/document.xml", "<w:document><w:t>TC: 10000000146</w:t><w:t>iletisim: veli@ornek.com</w:t></w:document>")
    with zipfile.ZipFile(tmp_path / "liste.xlsx", "w") as z:
        z.writestr("xl/sharedStrings.xml", "<sst><si><t>4111 1111 1111 1111</t></si></sst>")
        z.writestr("xl/worksheets/sheet1.xml", "<c><v>10000000146</v></c>")
    hidden = tmp_path / "node_modules"; hidden.mkdir(); (hidden / "x.txt").write_text(SAMPLE, encoding="utf-8")
    r = kvkk.scan([tmp_path])
    names = {p.split("/")[-1].split("\\")[-1]: f for f in r.findings for p in [f.path]}
    assert set(names) == {"musteri.txt", "eski.csv", "sozlesme.docx", "liste.xlsx"}
    assert names["musteri.txt"].level == "high" and names["eski.csv"].level == "medium"
    assert r.files_skipped >= 1 and r.totals()["tckn"] >= 3
    assert r.findings[0].score >= r.findings[-1].score


def test_report_contains_no_values(tmp_path):
    (tmp_path / "musteri.txt").write_text(SAMPLE, encoding="utf-8")
    html = kvkk.report_html(kvkk.scan([tmp_path]), org="Örnek A.Ş.", version="6.9.0")
    assert "Kişisel Veri Envanteri" in html and "musteri.txt" in html and "SHA-256" in html
    for value in ("10000000146", "4111", "TR33", "ali@ornek.com"):
        assert value not in html


def test_scan_cancel(tmp_path):
    import threading
    for i in range(60):
        (tmp_path / f"f{i}.txt").write_text(SAMPLE, encoding="utf-8")
    ev = threading.Event(); ev.set()
    assert kvkk.scan([tmp_path], cancel=ev).cancelled


def test_paper_backup_roundtrip_lines_and_qr():
    data = b"ELFVAULT1\n" + bytes(range(256)) * 3
    lines = pb.encode_lines(data)
    assert pb.decode_text("\n".join(lines)) == data
    assert pb.decode_text("çöp\n" + pb.qr_payload(data) + "\n") == data
    parts = pb.qr_parts(data)
    assert len(parts) >= 2 and all(set(p) <= set("ELFBACKUP0123456789:/ABCDEFGHIJKLMNOPQRSTUVWXYZ") for p in parts)
    assert pb.decode_text("\n".join(reversed(parts))) == data
    with pytest.raises(pb.BackupError, match="Eksik QR"):
        pb.decode_text(parts[0])
    bad = lines[:]; bad[3] = bad[3][:5] + ("A" if bad[3][5] != "A" else "B") + bad[3][6:]
    with pytest.raises(pb.BackupError, match="4. satır"):
        pb.decode_text("\n".join(bad))
    with pytest.raises(pb.BackupError, match="Eksik satır"):
        pb.decode_text("\n".join(lines[:2] + lines[3:]))


def test_paper_backup_html_with_real_identity(tmp_path):
    from elfcaesar.identity import create_identity, load_identity
    from studio_ui.chatarmor import armor_contact, safety_words
    c = create_identity("Mehmet Cem", "KutupYildizi!2026-Mavi", tmp_path / "a.elfid")
    raw = (tmp_path / "a.elfid").read_bytes()
    assert pb.looks_like_identity(raw)
    html = pb.make_html(raw, c, safety_words(c["fingerprint"]), armor_contact(c), "6.9.0")
    assert "<svg" in html and "KutupYildizi" not in html and "Kurtarma Kitapçığı" in html
    restored = pb.decode_text("\n".join(pb.qr_parts(raw)))
    (tmp_path / "b.elfid").write_bytes(restored)
    assert load_identity(tmp_path / "b.elfid", "KutupYildizi!2026-Mavi")["contact"] == c


def test_capture_protect_is_safe_off_windows():
    if not supported():
        assert protect(object()) is False
