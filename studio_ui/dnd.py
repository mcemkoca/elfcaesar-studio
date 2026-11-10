"""İsteğe bağlı sürükle-bırak desteği (tkinterdnd2).

Paket kurulu değilse uygulama normal çalışır; bırakma alanları tıklanınca dosya
seçme penceresi açar.
"""
from __future__ import annotations

try:  # pragma: no cover - ortam bağımlı
    from tkinterdnd2 import TkinterDnD, DND_FILES  # type: ignore
    AVAILABLE = True
except Exception:  # pragma: no cover
    TkinterDnD = None
    DND_FILES = None
    AVAILABLE = False


def parse_drop(data: str) -> list[str]:
    """Tk DND verisini yollara ayırır: ``{C:/a b.txt} C:/c.txt`` -> iki yol."""
    paths, buf, depth = [], [], 0
    for ch in data.strip():
        if ch == "{":
            if depth:
                buf.append(ch)
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth:
                buf.append(ch)
            else:
                paths.append("".join(buf)); buf = []
        elif ch.isspace() and depth == 0:
            if buf:
                paths.append("".join(buf)); buf = []
        else:
            buf.append(ch)
    if buf:
        paths.append("".join(buf))
    return [p for p in paths if p]


def enable(root) -> bool:
    """tkdnd'yi mevcut Tk köküne yükler; başarısızsa False döner."""
    if not AVAILABLE:
        return False
    try:  # pragma: no cover - ortam bağımlı
        loader = getattr(TkinterDnD, "require", None) or getattr(TkinterDnD, "_require")
        loader(root)
        return True
    except Exception:
        return False
