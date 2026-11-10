"""6.7 mesaj köprüsü testleri: sohbet zırhı, grup, parçalama, kişi defteri (motorlar değişmeden kullanılır)."""
import json
import pytest
from elfcaesar.identity import create_identity, load_identity, encrypt_for_contact, decrypt_from_contact, validate_contact
from elfcaesar.secure import encrypt_message, decrypt_message
from studio_ui import chatarmor as ca
from studio_ui.contacts import ContactBook

PW = "KutupYildizi!2026-Mavi"


@pytest.fixture(scope="module")
def people(tmp_path_factory):
    d = tmp_path_factory.mktemp("ids")
    out = {}
    for name in ("Mehmet Cem", "Arwen", "Legolas"):
        c = create_identity(name, PW, d / f"{name}.elfid")
        out[name] = (c, load_identity(d / f"{name}.elfid", PW))
    return out


def roundtrip(text):
    (kind, data), = ca.Reassembler().feed(text)
    return kind, data


def test_signed_dm_armor_roundtrip_and_smaller(people):
    me, arwen = people["Mehmet Cem"], people["Arwen"]
    payload = encrypt_for_contact("Yarın 10'da buluşalım ✓", arwen[0], me[1])
    armored = ca.armor_dm(payload)
    assert armored.startswith("🔐ELF1:M:") and len(armored) < len(payload) * .75
    assert not any(ch in armored for ch in "_*~`")
    kind, blob = roundtrip("şunu aç lütfen:\n" + armored + "\nteşekkürler")
    clear, sender = decrypt_from_contact(ca.unpack_dm(blob), arwen[1])
    assert clear == "Yarın 10'da buluşalım ✓" and sender["fingerprint"] == me[0]["fingerprint"]


def test_unsigned_dm_and_tamper_detection(people):
    arwen = people["Arwen"]
    armored = ca.armor_dm(encrypt_for_contact("gizli", arwen[0], None))
    _k, blob = roundtrip(armored)
    assert decrypt_from_contact(ca.unpack_dm(blob), arwen[1]) == ("gizli", None)
    body = armored.split(":")[2]
    flipped = armored.replace(body, body[:-3] + ("A" if body[-3] != "A" else "B") + body[-2:])
    with pytest.raises(ca.ArmorError):
        roundtrip(flipped)


def test_chat_line_wrapping_tolerated(people):
    armored = ca.armor_dm(encrypt_for_contact("satır", people["Arwen"][0], people["Legolas"][1]))
    wrapped = armored[:60] + "\n" + armored[60:120] + " " + armored[120:]
    _k, blob = roundtrip(wrapped)
    assert decrypt_from_contact(ca.unpack_dm(blob), people["Arwen"][1])[0] == "satır"


def test_group_message_each_recipient_can_open(people):
    me = people["Mehmet Cem"]
    recips = [people["Arwen"], people["Legolas"]]
    armored = ca.armor_group([encrypt_for_contact("herkese merhaba", r[0], me[1]) for r in recips])
    kind, blob = roundtrip(armored)
    assert kind == "G"
    items = ca.unpack_group(blob)
    for r in recips:
        mine = [b for b in items if ca.dm_recipient(b) == r[0]["fingerprint"]]
        assert decrypt_from_contact(ca.unpack_dm(mine[0]), r[1])[0] == "herkese merhaba"


def test_split_and_reassemble_across_copies(people):
    long = "uzun mesaj " * 900
    armored = ca.armor_dm(encrypt_for_contact(long, people["Arwen"][0], people["Mehmet Cem"][1]))
    parts = ca.split(armored, 3500)
    assert len(parts) >= 3 and all(len(p) <= 3500 for p in parts)
    r = ca.Reassembler()
    assert r.feed(parts[2]) == [] and r.feed(parts[0]) == []
    assert r.pending()[0][1:] == (2, len(parts))
    done = []
    for p in parts[1:2] + parts[3:]:
        done += r.feed(p)
    assert len(done) == 1
    assert decrypt_from_contact(ca.unpack_dm(done[0][1]), people["Arwen"][1])[0] == long


def test_password_message_armor():
    armored = ca.armor_password(encrypt_message("parolalı not", PW))
    kind, data = roundtrip(armored)
    assert kind == "P" and decrypt_message(data.decode(), PW) == "parolalı not"


def test_contact_card_armor(people):
    card = people["Arwen"][0]
    kind, blob = roundtrip(ca.armor_contact(card))
    assert kind == "K" and validate_contact(ca.unpack_contact(blob)) == card


def test_safety_words_stable_and_distinct(people):
    a, b = people["Arwen"][0]["fingerprint"], people["Legolas"][0]["fingerprint"]
    assert ca.safety_words(a) == ca.safety_words(a) and len(ca.safety_words(a)) == 6
    assert ca.safety_words(a) != ca.safety_words(b)


def test_contact_book_public_only_and_verification(tmp_path, people):
    path = tmp_path / "contacts.json"
    book = ContactBook(path, validate_contact)
    entry, new = book.add(people["Arwen"][0], alias="Arwen (iş)")
    assert new and not entry["verified"]
    with pytest.raises(Exception):
        book.add(dict(people["Legolas"][0], fingerprint="00" * 32))
    with pytest.raises(ValueError):
        book._check({"x25519_private": "x"})
    book.set_verified(people["Arwen"][0]["fingerprint"])
    again = ContactBook(path, validate_contact)
    assert again.stats() == (1, 1)
    assert "private" not in path.read_text()
    assert json.loads(path.read_text())["format"] == "ELFCONTACTBOOK1"


def test_winbridge_safe_off_windows():
    from studio_ui import winbridge
    cmd = winbridge.launcher_command("C:/ElfCaesar/gui.py", "encrypt-file", python_exe="C:/Python/python.exe")
    assert cmd.endswith('--action encrypt-file "%1"') and "gui.py" in cmd
    if not winbridge.IS_WINDOWS:
        assert winbridge.HotkeyListener().start() is False
        assert winbridge.send_ctrl("c") is False and winbridge.install_context_menu("x", None) is False


def test_single_instance_forwarding(tmp_path, monkeypatch):
    from studio_ui import runtime
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert runtime.forward_to_running("show", None) is False
    server = runtime.InstanceServer()
    assert server.start()
    try:
        assert runtime.forward_to_running("encrypt-file", "C:/belge.pdf") is True
        import time
        for _ in range(50):
            cmds = server.poll()
            if cmds:
                break
            time.sleep(0.02)
        assert cmds == [{"action": "encrypt-file", "path": "C:/belge.pdf"}]
        info = (tmp_path / "ElfCaesar" / "instance.json").read_text()
        assert "token" in info
    finally:
        server.stop()
    assert not (tmp_path / "ElfCaesar" / "instance.json").exists()


def test_instance_rejects_bad_token_and_actions(tmp_path, monkeypatch):
    import json, socket
    from studio_ui import runtime
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    server = runtime.InstanceServer(); server.start()
    try:
        port = json.loads((tmp_path / "ElfCaesar" / "instance.json").read_text())["port"]
        for payload in ({"token": "yanlış", "action": "show"}, {"token": server.token, "action": "rm -rf"}):
            with socket.create_connection(("127.0.0.1", port), timeout=1) as s:
                s.sendall(json.dumps(payload).encode()); s.settimeout(1)
                assert s.recv(8) == b""
        assert server.poll() == []
    finally:
        server.stop()


def test_crash_log_and_resources(tmp_path, monkeypatch):
    from studio_ui import runtime
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    try:
        raise ValueError("deneme")
    except ValueError as exc:
        path = runtime.write_crash(type(exc), exc, exc.__traceback__)
    assert path and "ValueError" in path.read_text(encoding="utf-8")
    assert (runtime.resource_dir() / "assets" / "elfcaesar.ico").exists()
