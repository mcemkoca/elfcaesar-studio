"""Dante sürüm manifesti: kurulum klasöründeki her dosyanın SHA-256 özetini imzalar.

Kullanım:
  set DANTE_KEY_PASS=<anahtar parolası>
  python packaging/sign_release.py build/dist/ElfCaesarStudio C:\\yol\\dante_release_ed25519.pem
Özel anahtar asla depoya konmaz. Uygulama gömülü genel anahtarla (studio_ui/signing.py) doğrular.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives import serialization  # noqa: E402

from studio_ui import signing  # noqa: E402
from studio_ui.version import APP_VERSION, APP_BUILD  # noqa: E402


def main(dist: str, key_path: str) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    pw = os.environ.get("DANTE_KEY_PASS")
    if not pw:
        print("DANTE_KEY_PASS ortam değişkeni gerekli", file=sys.stderr)
        return 2
    key = serialization.load_pem_private_key(Path(key_path).read_bytes(), pw.encode())
    root = Path(dist)
    manifest = signing.build_manifest(root, APP_VERSION, APP_BUILD)
    (root / signing.MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    (root / signing.MANIFEST_SIG).write_text(signing.sign_manifest(manifest, key) + "\n", encoding="ascii")
    res = signing.verify_install(root)
    print(f"{len(manifest['files'])} dosya imzalandı · doğrulama: {res['status']} · anahtar {signing.release_fingerprint()}")
    return 0 if res["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:3]))
