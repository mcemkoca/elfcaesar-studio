"""Dijital imza (Kleopatra / GPG boşluğu) ve Dante sürüm imzası.

• Belge imzalama: kullanıcının mevcut ElfCaesar kimliğindeki Ed25519 anahtarıyla dosyanın SHA-256 özetini
  imzalar ve yanına <dosya>.elfsig koyar. Doğrulayan kişi imzalayanın kişi kartını rehberinde
  "doğrulandı" olarak işaretlediyse imza "güvenilir" görünür. Kimlik motoru değişmez; yalnızca okunur.
• Sürüm imzası: kurulum klasöründeki her dosyanın özeti MANIFEST.json'da toplanır ve Dante sürüm
  anahtarıyla imzalanır. Uygulama gömülü genel anahtarla kendi kurulumunu doğrular (kurcalama tespiti).
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path

SIG_FORMAT = "ELFSIG1"
MANIFEST_FORMAT = "ELFMANIFEST1"
# Dante sürüm anahtarı (Ed25519, genel). Özel anahtar yalnızca yayıncıdadır.
DANTE_RELEASE_PUB = "JxaM23vrlWv4uPCGcLUSXH3OiBCKCnyilpI/chdvXNo="
MANIFEST_NAME = "MANIFEST.json"
MANIFEST_SIG = "MANIFEST.json.sig"


class SignatureError(ValueError):
    pass


def _ed():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    return Ed25519PrivateKey, Ed25519PublicKey


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def release_fingerprint(pub_b64: str = DANTE_RELEASE_PUB) -> str:
    d = hashlib.sha256(base64.b64decode(pub_b64)).hexdigest()[:16].upper()
    return " ".join(d[i:i + 4] for i in range(0, 16, 4))


# ------------------------------------------------------------------ belge imzası
def sign_file(path: str | Path, identity: dict, note: str = "") -> Path:
    """identity: elfcaesar.identity.load_identity() çıktısı. <path>.elfsig yazar ve yolunu döner."""
    Priv, _ = _ed()
    p = Path(path)
    key = Priv.from_private_bytes(base64.b64decode(identity["ed25519_private"]))
    contact = identity["contact"]
    body = {"format": SIG_FORMAT, "file": p.name, "size": p.stat().st_size, "sha256": file_sha256(p),
            "signed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "note": note[:200],
            "signer": {"name": contact["name"], "fingerprint": contact["fingerprint"],
                       "ed25519_public": contact["ed25519_public"], "x25519_public": contact["x25519_public"]}}
    body["signature"] = base64.b64encode(key.sign(canonical(body))).decode()
    out = p.with_name(p.name + ".elfsig")
    out.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def verify_file(path: str | Path, sig_path: str | Path | None = None, book=None) -> dict:
    """Sonuç: {'valid','trusted','signer','signed_at','reason'}. book: ContactBook (isteğe bağlı)."""
    _, Pub = _ed()
    p = Path(path)
    sp = Path(sig_path) if sig_path else p.with_name(p.name + ".elfsig")
    try:
        data = json.loads(sp.read_text(encoding="utf-8"))
        sig = base64.b64decode(data.pop("signature"))
        if data.get("format") != SIG_FORMAT:
            raise ValueError
        signer = data["signer"]
    except Exception as exc:
        raise SignatureError("İmza dosyası okunamadı veya biçimi bozuk.") from exc
    res = {"valid": False, "trusted": False, "signer": signer, "signed_at": data.get("signed_at", ""),
           "note": data.get("note", ""), "reason": ""}
    try:
        Pub.from_public_bytes(base64.b64decode(signer["ed25519_public"])).verify(sig, canonical(data))
    except Exception:
        res["reason"] = "İmza geçersiz: imza dosyası değiştirilmiş veya başka anahtarla üretilmiş."
        return res
    # kişi kartının parmak izi ile anahtar tutarlı mı?
    fp = hashlib.sha256(b"ELFCAESAR-ID-v1\0" + base64.b64decode(signer["x25519_public"]) +
                        base64.b64decode(signer["ed25519_public"])).hexdigest()
    if fp != signer.get("fingerprint"):
        res["reason"] = "İmzalayan parmak izi anahtarla uyuşmuyor."
        return res
    if p.stat().st_size != data["size"] or file_sha256(p) != data["sha256"]:
        res["reason"] = "Dosya imzalandıktan SONRA değiştirilmiş."
        return res
    res["valid"] = True
    if book is not None:
        c = book.get(fp)
        res["trusted"] = bool(c and c.get("verified"))
        res["known"] = bool(c)
    res["reason"] = "İmza geçerli; dosya imzalandığı andan beri değişmemiş."
    return res


# ------------------------------------------------------------------ sürüm manifesti
def build_manifest(root: str | Path, version: str, build: int) -> dict:
    root = Path(root)
    files = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name not in (MANIFEST_NAME, MANIFEST_SIG) and "__pycache__" not in p.parts:
            files[p.relative_to(root).as_posix()] = file_sha256(p)
    return {"format": MANIFEST_FORMAT, "app": "ElfCaesar Studio", "version": version, "build": build,
            "publisher": "Dante", "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": files}


def sign_manifest(manifest: dict, private_key) -> str:
    return base64.b64encode(private_key.sign(canonical(manifest))).decode()


def verify_install(root: str | Path, pub_b64: str = DANTE_RELEASE_PUB) -> dict:
    """Kurulum klasörünü Dante imzalı manifeste göre doğrular."""
    _, Pub = _ed()
    root = Path(root)
    mp, sp = root / MANIFEST_NAME, root / MANIFEST_SIG
    res = {"status": "missing", "version": "", "checked": 0, "changed": [], "missing": [], "extra": 0}
    if not mp.exists() or not sp.exists():
        return res
    try:
        manifest = json.loads(mp.read_text(encoding="utf-8"))
        Pub.from_public_bytes(base64.b64decode(pub_b64)).verify(base64.b64decode(sp.read_text().strip()), canonical(manifest))
    except Exception:
        res["status"] = "bad_signature"
        return res
    res["version"] = manifest.get("version", "")
    for rel, digest in manifest["files"].items():
        p = root / rel
        if not p.exists():
            res["missing"].append(rel)
        elif file_sha256(p) != digest:
            res["changed"].append(rel)
        res["checked"] += 1
    res["status"] = "ok" if not res["changed"] and not res["missing"] else "tampered"
    return res
