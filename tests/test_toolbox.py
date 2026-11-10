"""6.9.1 Araç Kutusu: anahtar dosyası, klasör kasası, güvenli imha, dijital imza, maskeli kopya, sürüm manifesti."""
import base64
import json

import pytest

from elfcaesar.identity import create_identity, load_identity
from elfcaesar.secure import SecureFormatError, open_bytes
from studio_ui import folderlock, keyfile, masking, shred, signing

PW = "orman-kartal-demir-ates-2026"


def test_keyfile_combine(tmp_path):
    kf = keyfile.create(tmp_path / "anahtar.key")
    assert kf.stat().st_size == 64
    assert keyfile.combine(PW, None) == PW
    c = keyfile.combine(PW, kf)
    assert c.startswith(PW) and c != PW and c == keyfile.combine(PW, kf)
    other = keyfile.create(tmp_path / "b.key")
    assert keyfile.combine(PW, other) != c
    with pytest.raises(FileExistsError):
        keyfile.create(kf)


def test_folder_lock_roundtrip_with_keyfile(tmp_path):
    src = tmp_path / "Muhasebe"
    (src / "2026" / "Ekim").mkdir(parents=True)
    (src / "2026" / "Ekim" / "fatura.txt").write_text("IBAN TR33 0006 1005 1978 6457 8413 26", encoding="utf-8")
    (src / "bos").mkdir()
    (src / "logo.bin").write_bytes(bytes(range(256)) * 10)
    kf = keyfile.create(tmp_path / "k.key")
    secret = keyfile.combine(PW, kf)
    vault = folderlock.lock(src, tmp_path / "Muhasebe.elfvault", secret)
    raw = vault.read_bytes()
    assert b"fatura" not in raw and b"Muhasebe/" not in raw  # adlar da şifreli
    with pytest.raises(SecureFormatError):
        folderlock.unlock(vault, tmp_path / "out", PW)  # anahtar dosyası olmadan açılmaz
    (tmp_path / "out").mkdir()
    out = folderlock.unlock(vault, tmp_path / "out", secret)
    assert (out / "2026" / "Ekim" / "fatura.txt").read_text(encoding="utf-8").startswith("IBAN")
    assert (out / "logo.bin").read_bytes() == (src / "logo.bin").read_bytes()
    assert (out / "bos").is_dir()
    out2 = folderlock.unlock(vault, tmp_path / "out", secret)  # üzerine yazmaz
    assert out2.name == "Muhasebe (2)"
    _clear, h = open_bytes(raw, secret)
    assert folderlock.is_folder_vault(h)


def test_folder_unlock_rejects_zip_slip(tmp_path):
    import io, zipfile
    from elfcaesar.secure import seal_bytes
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../kotu.txt", "x")
    blob = seal_bytes(buf.getvalue(), PW, kind="file", filename="x.zip", content_type=folderlock.CONTENT_TYPE)
    (tmp_path / "v").write_bytes(blob)
    (tmp_path / "o").mkdir()
    with pytest.raises(SecureFormatError):
        folderlock.unlock(tmp_path / "v", tmp_path / "o", PW)
    assert not (tmp_path / "kotu.txt").exists()


def test_shred_and_tutanak(tmp_path):
    f = tmp_path / "personel.csv"
    f.write_text("ad,tckn\nAli,10000000146\n", encoding="utf-8")
    digest = signing.file_sha256(f)
    recs = shred.shred_many([f, tmp_path / "yok.txt"], "random3")
    assert not f.exists() and list(tmp_path.iterdir()) == []
    assert recs[0].ok and recs[0].sha256 == digest and not recs[1].ok
    page = shred.tutanak_html(recs, "Örnek A.Ş.", "Saklama süresi doldu", "6.9.1")
    assert "İmha Tutanağı" in page and "personel.csv" in page and "10000000146" not in page and "1 / 2" in page


def test_sign_and_verify(tmp_path):
    create_identity("Dante", PW, tmp_path / "me.elfid")
    ident = load_identity(tmp_path / "me.elfid", PW)
    doc = tmp_path / "sozlesme.pdf"
    doc.write_bytes(b"%PDF-1.7 sozlesme")
    sig = signing.sign_file(doc, ident, "Onaylıyorum")
    r = signing.verify_file(doc)
    assert r["valid"] and r["signer"]["name"] == "Dante" and r["note"] == "Onaylıyorum"

    class Book:
        def get(self, fp):
            return {"verified": True} if fp == ident["contact"]["fingerprint"] else None
    assert signing.verify_file(doc, book=Book())["trusted"]
    doc.write_bytes(b"%PDF-1.7 sozlesme DEGISTI")
    r = signing.verify_file(doc)
    assert not r["valid"] and "SONRA" in r["reason"]
    doc.write_bytes(b"%PDF-1.7 sozlesme")
    data = json.loads(sig.read_text(encoding="utf-8"))
    data["note"] = "sahte"
    sig.write_text(json.dumps(data), encoding="utf-8")
    assert not signing.verify_file(doc)["valid"]


def test_masking():
    text = "Ali 10000000146 TR33 0006 1005 1978 6457 8413 26 kart 4111 1111 1111 1111 ali.veli@ornek.com 0532 123 45 67 şifre: Gizli123"
    out, counts = masking.mask_text(text)
    for leaked in ("10000000146", "4111 1111 1111 1111", "ali.veli@", "Gizli123", "123 45 67"):
        assert leaked not in out
    assert out.count("146") >= 1 and "1111" in out and "@ornek.com" in out
    assert counts == {"email": 1, "iban": 1, "card": 1, "tckn": 1, "phone": 1, "secret": 1}
    full, _ = masking.mask_text(text, "full")
    assert "146" not in full.replace("•", "")[:10]


def test_masked_copy(tmp_path):
    f = tmp_path / "liste.csv"
    f.write_text("tc;10000000146\n", encoding="utf-8")
    out, counts = masking.masked_copy(f)
    assert out.name == "liste.maskeli.csv" and "10000000146" not in out.read_text(encoding="utf-8") and counts["tckn"] == 1
    assert f.read_text(encoding="utf-8") == "tc;10000000146\n"
    with pytest.raises(ValueError):
        masking.masked_copy(tmp_path / "a.pdf")


def test_release_manifest(tmp_path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization as s
    key = Ed25519PrivateKey.generate()
    pub = base64.b64encode(key.public_key().public_bytes(s.Encoding.Raw, s.PublicFormat.Raw)).decode()
    (tmp_path / "_internal").mkdir()
    (tmp_path / "app.exe").write_bytes(b"MZ app")
    (tmp_path / "_internal" / "lib.dll").write_bytes(b"MZ lib")
    assert signing.verify_install(tmp_path, pub)["status"] == "missing"
    m = signing.build_manifest(tmp_path, "6.9.1", 691)
    (tmp_path / signing.MANIFEST_NAME).write_text(json.dumps(m), encoding="utf-8")
    (tmp_path / signing.MANIFEST_SIG).write_text(signing.sign_manifest(m, key))
    r = signing.verify_install(tmp_path, pub)
    assert r["status"] == "ok" and r["checked"] == 2
    assert signing.verify_install(tmp_path)["status"] == "bad_signature"  # başka anahtar (Dante) ile değil
    (tmp_path / "_internal" / "lib.dll").write_bytes(b"MZ evil")
    r = signing.verify_install(tmp_path, pub)
    assert r["status"] == "tampered" and r["changed"] == ["_internal/lib.dll"]


def test_release_fingerprint():
    assert signing.release_fingerprint() == "B715 8370 19A2 935F"
