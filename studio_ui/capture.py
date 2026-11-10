"""Ekran görüntüsü kalkanı: hassas pencereler ekran görüntüsünde ve ekran paylaşımında siyah görünür.

Windows 10 2004+ SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE). Diğer sistemlerde etkisizdir.
Not: Telefonla ekranın fotoğrafını çekmeyi engelleyemez.
"""
from __future__ import annotations

import os

WDA_NONE, WDA_MONITOR, WDA_EXCLUDEFROMCAPTURE = 0x0, 0x1, 0x11
MODES = ("off", "sensitive", "all")


def supported() -> bool:
    return os.name == "nt"


def protect(window, enabled: bool = True) -> bool:
    """Tk penceresini (Tk veya Toplevel) ekran yakalamadan hariç tutar. Başarıda True."""
    if not supported():
        return False
    try:  # pragma: no cover - yalnızca Windows
        import ctypes
        window.update_idletasks()
        user32 = ctypes.windll.user32
        hwnd = user32.GetAncestor(window.winfo_id(), 2)  # GA_ROOT
        flag = WDA_EXCLUDEFROMCAPTURE if enabled else WDA_NONE
        if not user32.SetWindowDisplayAffinity(hwnd, flag) and enabled:
            return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR))  # eski Windows: siyah kutu
        return True
    except Exception:
        return False
