from studio_ui import diagnostics


def test_report_has_no_content(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    logs = tmp_path / "ElfCaesar" / "logs"
    logs.mkdir(parents=True)
    (logs / "crash.log").write_text("Traceback...\nFileNotFoundError: C:\\Users\\ayse\\gizli-sozlesme.pdf bulunamadı\n", encoding="utf-8")
    r = diagnostics.report(None)
    assert "ElfCaesar Studio" in r and "FileNotFoundError" in r
    assert "gizli-sozlesme" not in r and "ayse" not in r
