"""İsteğe bağlı arayüz duman testi.

Pencere açtığı için varsayılan olarak atlanır. Çalıştırmak için:
    set ELFCAESAR_GUI_TESTS=1   (Windows)   /   export ELFCAESAR_GUI_TESTS=1
    py -3 -m pytest -q tests/test_gui_smoke.py
"""
import os
import pytest

pytestmark = pytest.mark.skipif(os.environ.get("ELFCAESAR_GUI_TESTS") != "1",
                                reason="GUI testi için ELFCAESAR_GUI_TESTS=1 gerekli")


@pytest.fixture()
def app(tmp_path, monkeypatch):
    tk = pytest.importorskip("tkinter")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("ELFCAESAR_NO_SPLASH", "1")
    try:
        import gui
        studio = gui.Studio()
    except tk.TclError as exc:  # ekran yok
        pytest.skip(f"Tk ekranı yok: {exc}")
    studio.geometry("1200x800+0+0")
    studio.update()
    yield studio
    studio._on_close()


def pump(app, n=8):
    for _ in range(n):
        app.update()


def test_all_pages_open(app):
    import gui
    for key, *_ in gui.PAGES:
        app.show_page(key)
        pump(app)
        assert app.active_page == key and key in app.pages


def test_counters_update_after_programmatic_changes(app):
    app.show_page("encode")
    app.put(app.enc_in, "Merhaba Dünya\nikinci satır")
    pump(app)
    app.do_encode()
    pump(app)
    assert app.get(app.enc_out).startswith("ELFC2:")
    # Çıktı editörünün sayacı programatik put() sonrasında güncellenmiş olmalı
    labels = []
    def walk(w):
        for c in w.winfo_children():
            if c.winfo_class() == "Label":
                labels.append(c.cget("text"))
            walk(c)
    walk(app.pages["encode"])
    assert any("13 KARAKTER" in t or "26 KARAKTER" in t for t in labels)
    assert any(t.startswith(f"{len(app.get(app.enc_out))} KARAKTER") for t in labels)


def test_tabs_keep_state_and_close(app):
    app.show_page("encode")
    app.put(app.enc_in, "kalıcı metin")
    app.show_page("vault")
    app.show_page("encode")
    assert app.get(app.enc_in) == "kalıcı metin"
    app.close_tab("encode")
    assert "encode" not in app.tabs and app.active_page != "encode"
    app.close_tab("home")
    assert "home" in app.tabs


def test_notify_updates_history_and_badge(app):
    app.show_page("home")
    before = len(app.log)
    app.notify("success", "codec", "Deneme işlemi")
    assert len(app.log) == before + 1 and app.unread >= 1
    app.show_page("history")
    pump(app)
    assert app.unread == 0
    assert len(app.hist_tree.get_children()) == len(app.log)


def test_analysis_ranks_best_shift(app):
    from elfcaesar.engine import encode
    app.show_page("analysis")
    app.put(app.brute_in, encode("Yarın sabah saat dokuzda kapının önünde buluşalım.", 9))
    app.do_brute()
    pump(app)
    assert len(app.tree.get_children()) == 29
    assert app.tree.selection() == ("9",)
    app.analysis_filter.set("buluşalım")
    pump(app)
    assert app.tree.get_children() == ("9",)


def test_security_level_reacts_to_settings(app):
    app.show_page("security")
    pump(app)
    start = app.assessment["score"]
    app.set_pref("clipboard_guard", False)
    assert app.assessment["score"] < start
    assert any(a["action"] == "enable_clipboard" for a in app.assessment["advice"])
    assert "GÜVENLİK" in app.pill_label.cget("text")
    app._advice_action("enable_clipboard")
    pump(app)
    assert app.sec.clipboard_guard and app.assessment["score"] == start


def test_panic_clears_editors_and_locks(app):
    app.show_page("encode")
    app.put(app.enc_in, "gizli")
    app.show_page("vault")
    app.put(app.sec_msg_out, "açık metin")
    app.panic()
    pump(app)
    assert app.get(app.enc_in) == "" and app.get(app.sec_msg_out) == ""
    assert app._locked
    app._unlock()
    assert not app._locked


def test_logo_assets_loaded(app):
    assert app.img("mark_40") is not None and app.img("logo_256") is not None


def test_message_bridge_end_to_end(app, tmp_path):
    from elfcaesar.identity import create_identity, load_identity
    pw = "KutupYildizi!2026-Mavi"
    a = create_identity("Mehmet Cem", pw, tmp_path / "a.elfid")
    b = create_identity("Arwen", pw, tmp_path / "b.elfid")
    ia, ib = load_identity(tmp_path / "a.elfid", pw), load_identity(tmp_path / "b.elfid", pw)
    app.show_page("bridge")
    pump(app)
    # Mehmet → Arwen (imzalı)
    app.session = {"identity": ia, "path": "a", "opened": 0}
    app.book.add(b, verified=True)
    parts = app.bridge_encrypt("Yarın 10'da köprüde.", [b["fingerprint"]], sign=True)
    assert parts and parts[0].startswith("🔐ELF1:M:")
    # Arwen tarafı: Mehmet doğrulanmış kişi, pano radarı yakalar
    app.session = {"identity": ib, "path": "b", "opened": 0}
    app.book.add(a, verified=True)
    app._contacts_changed()
    app.clipboard_clear(); app.clipboard_append(parts[0])
    app._own_armor.clear(); app._radar_last = None
    app._radar_scan()
    assert app._radar_pending and app._radar_pending[0][0] == "M"
    app.open_items(app._radar_pending)
    pump(app)
    bubble = app.bubbles[-1]
    texts = []
    def walk(w):
        for c in w.winfo_children():
            if c.winfo_class() == "Text":
                texts.append(c.get("1.0", "end-1c"))
            elif c.winfo_class() == "Label":
                texts.append(c.cget("text"))
            walk(c)
    walk(bubble)
    assert "Yarın 10'da köprüde." in texts and "DOĞRULANMIŞ KİŞİ" in texts
    assert app.sec.pinned_opens == 1
    # panik: oturum ve balonlar kapanır
    app.panic()
    pump(app)
    assert app.session is None and not app.bubbles
    app._unlock()


def test_cli_args():
    import gui
    assert gui.parse_args(["--action", "encrypt-file", "C:/x.pdf"]) == ("encrypt-file", "C:/x.pdf")
    assert gui.parse_args([]) is None


def test_intro_whatsnew_and_crack_lab(app):
    app.play_intro(first=True)
    for _ in range(5):
        app.update()
    assert app.prefs["founder_id"] and app.intro.frame.winfo_exists()
    app.intro.finish()
    pump(app)
    assert app.prefs["intro_seen"] and app.prefs["last_version"]
    app.prefs["last_version"] = "6.8.0"
    app._maybe_whats_new()
    assert app.prefs["last_version"] != "6.8.0"
    app.show_page("security")
    app.lab_pw.set("Galatasaray1905")
    pump(app)
    labels = []
    def walk(w):
        for c in w.winfo_children():
            if c.winfo_class() == "Label":
                labels.append(str(c.cget("text")))
            walk(c)
    walk(app.pages["security"])
    assert any(t.startswith("Sızıntı / yaygın parola listesinde") for t in labels)
    assert any(t == "ElfCaesar kasası" for t in labels) and any(t == "anında" for t in labels)


def test_kvkk_page_scan_and_render(app, tmp_path):
    from studio_ui import kvkk
    (tmp_path / "musteri.txt").write_text("TC 10000000146 kart 4111 1111 1111 1111", encoding="utf-8")
    (tmp_path / "temiz.txt").write_text("merhaba", encoding="utf-8")
    app.show_page("kvkk")
    pump(app)
    app.kv_roots = [str(tmp_path)]
    app._kvkk_render_roots()
    app.kv_result = kvkk.scan([tmp_path])
    app._kvkk_render()
    pump(app)
    rows = [app.kv_tree.item(i, "values") for i in app.kv_tree.get_children()]
    assert len(rows) == 1 and rows[0][0] == "YÜKSEK" and "T.C. kimlik" in rows[0][2]
    assert "10000000146" not in str(rows)


def test_capture_setting_and_backup_advice(app):
    app.prefs["identity_path"] = "x.elfid"
    app.sec.identity_known = True
    app.set_pref("capture_shield", "off")
    actions = {a["action"] for a in app.assessment["advice"]}
    assert {"paper_backup", "enable_capture"} <= actions
    app.set_pref("capture_shield", "sensitive")
