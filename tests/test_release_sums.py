import base64
import os
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import verify_release  # noqa: E402


def test_sums_sign_and_verify(tmp_path, monkeypatch):
    key = Ed25519PrivateKey.generate()
    rel = tmp_path / "rel"
    rel.mkdir()
    (rel / "Setup.exe").write_bytes(b"setup" * 50)
    (rel / "eklenti.xpi").write_bytes(b"xpi")
    pem = tmp_path / "k.pem"
    pem.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.BestAvailableEncryption(b"pw")))
    env = dict(os.environ, DANTE_KEY_PASS="pw")
    subprocess.run([sys.executable, str(ROOT / "packaging" / "sign_sums.py"), str(rel), str(pem)], env=env, check=True)
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    monkeypatch.setattr(verify_release, "DANTE_RELEASE_PUB", base64.b64encode(pub).decode())
    sums, sig = str(rel / "SHA256SUMS.txt"), str(rel / "SHA256SUMS.txt.sig")
    assert verify_release.verify(sums, sig) == 0
    (rel / "eklenti.xpi").write_bytes(b"degisti")
    assert verify_release.verify(sums, sig) == 1


def test_wrong_key_rejected(tmp_path):
    rel = tmp_path
    (rel / "SHA256SUMS.txt").write_text("00  a\n")
    (rel / "SHA256SUMS.txt.sig").write_text(base64.b64encode(b"\0" * 64).decode())
    assert verify_release.verify(str(rel / "SHA256SUMS.txt"), str(rel / "SHA256SUMS.txt.sig")) == 1


def test_embedded_key_matches_app():
    from studio_ui import signing
    assert verify_release.DANTE_RELEASE_PUB == signing.DANTE_RELEASE_PUB
    assert verify_release.fingerprint() == signing.release_fingerprint()
