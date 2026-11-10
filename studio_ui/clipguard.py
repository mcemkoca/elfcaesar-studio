"""Hassas pano yazma (Windows): parola Pano Geçmişi'ne (Win+V) ve bulut panosuna düşmesin.

Windows'un tanıdığı biçimler:
  • ExcludeClipboardContentFromMonitorProcessing — pano izleyicileri / geçmiş içeriği almaz
  • CanIncludeInClipboardHistory = 0 — Win+V geçmişine eklenmez
  • CanUploadToCloudClipboard = 0 — cihazlar arası bulut panosuna gönderilmez
Windows dışında veya hata olursa False döner; çağıran normal Tk panosuna düşer.
"""
from __future__ import annotations

import ctypes
import sys

IS_WINDOWS = sys.platform == "win32"
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


def set_sensitive(text: str) -> bool:
    if not IS_WINDOWS:
        return False
    try:  # pragma: no cover - yalnızca Windows
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel32.GlobalLock.restype = wintypes.LPVOID
        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        user32.SetClipboardData.restype = wintypes.HANDLE
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.RegisterClipboardFormatW.restype = wintypes.UINT
        user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]

        def put(fmt, data: bytes):
            h = kernel32.GlobalAlloc(GMEM_MOVEABLE, max(1, len(data)))
            if not h:
                return False
            p = kernel32.GlobalLock(h)
            ctypes.memmove(p, data, len(data))
            kernel32.GlobalUnlock(h)
            return bool(user32.SetClipboardData(fmt, h))

        for _ in range(10):
            if user32.OpenClipboard(None):
                break
            import time
            time.sleep(0.02)
        else:
            return False
        try:
            user32.EmptyClipboard()
            ok = put(CF_UNICODETEXT, (text + "\0").encode("utf-16-le"))
            zero = (0).to_bytes(4, "little")
            put(user32.RegisterClipboardFormatW("ExcludeClipboardContentFromMonitorProcessing"), zero)
            put(user32.RegisterClipboardFormatW("CanIncludeInClipboardHistory"), zero)
            put(user32.RegisterClipboardFormatW("CanUploadToCloudClipboard"), zero)
            return ok
        finally:
            user32.CloseClipboard()
    except Exception:
        return False
