"""SHA256SUMS.txt üretir ve Dante sürüm anahtarıyla (Ed25519) imzalar.

  set DANTE_KEY_PASS=<anahtar parolası>
  python packaging/sign_sums.py <dosyalar_klasörü> <dante_release_ed25519.pem>
Çıktı: <klasör>/SHA256SUMS.txt ve SHA256SUMS.txt.sig (base64). Doğrulama: tools/verify_release.py
"""
from __future__ import annotations

import base64
import hashlib
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization

DOMAIN = b"ELFSUMS1\n"  # imza başka bir bağlamda yeniden kullanılamasın


def build_sums(folder: Path) -> str:
    lines = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and not p.name.startswith("SHA256SUMS"):
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
    return "\n".join(lines) + "\n"


def main(folder: str, key_path: str) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    pw = os.environ.get("DANTE_KEY_PASS")
    if not pw:
        print("DANTE_KEY_PASS ortam değişkeni gerekli", file=sys.stderr)
        return 2
    key = serialization.load_pem_private_key(Path(key_path).read_bytes(), pw.encode())
    root = Path(folder)
    sums = build_sums(root).encode("utf-8")
    (root / "SHA256SUMS.txt").write_bytes(sums)
    sig = base64.b64encode(key.sign(DOMAIN + sums)).decode()
    (root / "SHA256SUMS.txt.sig").write_text(sig + "\n", encoding="ascii")
    print(f"{sums.count(b'\n')} dosya listelendi ve imzalandı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:3]))
