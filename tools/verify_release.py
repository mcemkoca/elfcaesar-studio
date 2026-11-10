"""ElfCaesar Studio sürüm doğrulayıcı (bağımsız; yalnızca `cryptography` gerekir).

  python verify_release.py SHA256SUMS.txt SHA256SUMS.txt.sig
1) SHA256SUMS.txt dosyasının Dante sürüm anahtarıyla imzalandığını doğrular.
2) Aynı klasördeki her dosyanın SHA-256 özetini listeyle karşılaştırır.
Dante sürüm anahtarı parmak izi: B715 8370 19A2 935F
"""
from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path

DANTE_RELEASE_PUB = "JxaM23vrlWv4uPCGcLUSXH3OiBCKCnyilpI/chdvXNo="
DOMAIN = b"ELFSUMS1\n"


def fingerprint() -> str:
    d = hashlib.sha256(base64.b64decode(DANTE_RELEASE_PUB)).hexdigest()[:16].upper()
    return " ".join(d[i:i + 4] for i in range(0, 16, 4))


def verify(sums_path: str, sig_path: str) -> int:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    sums = Path(sums_path).read_bytes()
    sig = base64.b64decode(Path(sig_path).read_text(encoding="ascii").strip())
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(DANTE_RELEASE_PUB)).verify(sig, DOMAIN + sums)
    except InvalidSignature:
        print("İMZA GEÇERSİZ — dosyalar Dante tarafından yayımlanmamış ya da değiştirilmiş.")
        return 1
    print(f"İmza geçerli · Dante sürüm anahtarı {fingerprint()}")
    folder, bad, checked = Path(sums_path).parent, 0, 0
    for line in sums.decode("utf-8").splitlines():
        digest, _, name = line.partition("  ")
        f = folder / name
        if not f.exists():
            continue
        checked += 1
        ok = hashlib.sha256(f.read_bytes()).hexdigest() == digest
        bad += not ok
        print(f"  {'TAMAM ' if ok else 'BOZUK!'}  {name}")
    if checked == 0:
        print("Klasörde listedeki dosyalardan hiçbiri yok; yalnızca imza doğrulandı.")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(verify(sys.argv[1], sys.argv[2]))
