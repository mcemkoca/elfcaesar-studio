"""Klasör kasası: bütün bir klasörü tek .elfvault dosyasına şifreler (Picocrypt / Cryptomator boşluğu).

Klasör bellekte ZIP'lenir (sıkıştırmalı), ardından değişmeyen motorla AES-256-GCM + scrypt ile mühürlenir.
Dosya adları ve klasör yapısı da şifrelenir; dışarıdan yalnızca tek bir dosya görünür.
Açarken ZIP-slip (../) ve mutlak yollar reddedilir.
"""
from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path, PurePosixPath

from elfcaesar.secure import open_bytes, seal_bytes, _atomic_write, SecureFormatError

CONTENT_TYPE = "application/vnd.elfcaesar.folder+zip"
MAX_FOLDER = 1024 * 1024 * 1024  # 1 GB (bellekte işlendiği için)


def folder_stats(folder: str | Path) -> tuple[int, int]:
    files, total = 0, 0
    for dp, _dn, fn in os.walk(folder):
        for n in fn:
            try:
                total += (Path(dp) / n).stat().st_size
                files += 1
            except OSError:
                pass
    return files, total


def pack(folder: str | Path) -> bytes:
    root = Path(folder)
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    files, total = folder_stats(root)
    if total > MAX_FOLDER:
        raise ValueError("Klasör 1 GB'tan büyük; şimdilik daha küçük parçalar hâlinde kilitleyin.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr(root.name + "/", b"")
        for dp, dn, fn in os.walk(root):
            dn.sort()
            rel_dir = Path(dp).relative_to(root.parent)
            for d in dn:
                z.writestr((rel_dir / d).as_posix() + "/", b"")
            for n in sorted(fn):
                p = Path(dp) / n
                z.write(p, (rel_dir / n).as_posix())
    return buf.getvalue()


def lock(folder: str | Path, destination: str | Path, password: str) -> Path:
    root = Path(folder)
    sealed = seal_bytes(pack(root), password, kind="file", filename=root.name + ".zip", content_type=CONTENT_TYPE)
    dst = Path(destination)
    _atomic_write(dst, sealed)
    return dst


def is_folder_vault(header: dict) -> bool:
    return header.get("content_type") == CONTENT_TYPE


def _safe_members(z: zipfile.ZipFile):
    for info in z.infolist():
        name = info.filename
        pp = PurePosixPath(name)
        if pp.is_absolute() or ".." in pp.parts or ":" in name or name.startswith("\\"):
            raise SecureFormatError(f"Güvensiz yol reddedildi: {name}")
        yield info


def unlock(source: str | Path, destination_dir: str | Path, password: str) -> Path:
    """Klasör kasasını açar; oluşturulan klasörün yolunu döner. Var olan klasörün üzerine yazmaz."""
    clear, header = open_bytes(Path(source).read_bytes(), password)
    if not is_folder_vault(header):
        raise SecureFormatError("Bu dosya klasör kasası değil (normal dosya kasası olabilir).")
    out = Path(destination_dir)
    with zipfile.ZipFile(io.BytesIO(clear)) as z:
        members = list(_safe_members(z))
        top = PurePosixPath(members[0].filename).parts[0] if members else "klasor"
        target = out / top
        n = 2
        final = target
        while final.exists():
            final = out / f"{top} ({n})"
            n += 1
        for info in members:
            parts = PurePosixPath(info.filename).parts
            rel = Path(final.name, *parts[1:]) if parts and parts[0] == top else Path(final.name, *parts)
            dest = out / rel
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, "xb") as dst:
                while chunk := src.read(1 << 20):
                    dst.write(chunk)
    return final


def peek_is_folder_vault(path: str | Path) -> bool:
    """Parola sormadan (açık başlıktan) kasanın klasör kasası olup olmadığını söyler."""
    import json
    try:
        with open(path, "rb") as f:
            head = f.read(4096).decode("utf-8", errors="ignore")
        return f'"content_type":"{CONTENT_TYPE}"' in head.replace(" ", "")
    except OSError:
        return False
