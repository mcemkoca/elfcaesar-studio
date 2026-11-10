"""Anahtar dosyası (keyfile) — ikinci faktör.

VeraCrypt / KeePassXC / Picocrypt'teki gibi: kasayı açmak için parola + belirli bir dosyanın kendisi gerekir.
Motor değişmez; anahtar dosyasının SHA-256 özeti parolaya alan ayırıcıyla eklenip motora verilir.
Herhangi bir dosya (foto, müzik) anahtar olabilir; dosyanın tek baytı değişirse kasa açılmaz.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path

TAG = "\x1fELFKF1:"
MAX_KEYFILE = 64 * 1024 * 1024


def digest(path: str | Path) -> str:
    p = Path(path)
    if p.stat().st_size > MAX_KEYFILE:
        raise ValueError("Anahtar dosyası 64 MB'tan büyük olamaz.")
    if p.stat().st_size == 0:
        raise ValueError("Boş dosya anahtar dosyası olamaz.")
    h = hashlib.sha256(b"ELFCAESAR-KEYFILE-v1\0")
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def combine(password: str, keyfile: str | Path | None) -> str:
    """Parola + anahtar dosyası → motora verilecek tek gizli değer. Anahtar dosyası yoksa parola aynen döner."""
    if not keyfile:
        return password
    return password + TAG + digest(keyfile)


def create(path: str | Path, size: int = 64) -> Path:
    """Rastgele anahtar dosyası üretir (varsayılan 64 bayt = 512 bit)."""
    p = Path(path)
    with open(p, "xb") as f:
        f.write(secrets.token_bytes(size))
        f.flush()
        os.fsync(f.fileno())
    return p


def short_id(path: str | Path) -> str:
    """Kullanıcıya gösterilecek kısa parmak izi (gizli değil, karşılaştırma için)."""
    d = digest(path)
    return f"{d[:4]}-{d[4:8]}".upper()
