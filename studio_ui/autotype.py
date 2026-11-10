"""Hızlı Doldur (otomatik yazma): ön plandaki pencereyi tanır, kullanıcı adı + Tab + parola yazar.

Windows SendInput + KEYEVENTF_UNICODE ile her karakter klavyeden yazılmış gibi gönderilir; pano kullanılmaz,
böylece parola panoda iz bırakmaz. Diğer sistemlerde devre dışıdır.
"""
from __future__ import annotations

import ctypes
import sys
import time

IS_WINDOWS = sys.platform == "win32"
KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x0002, 0x0004
VK_TAB, VK_RETURN = 0x09, 0x0D
INPUT_KEYBOARD = 1

if IS_WINDOWS:  # pragma: no cover - yalnızca Windows
    from ctypes import wintypes

    ULONG_PTR = ctypes.c_size_t

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _U)]

    user32 = ctypes.WinDLL("user32", use_last_error=True)


def foreground() -> tuple[int, str]:
    """(pencere tanıtıcısı, başlık)"""
    if not IS_WINDOWS:
        return 0, ""
    hwnd = user32.GetForegroundWindow()  # pragma: no cover
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return hwnd, buf.value


def activate(hwnd: int) -> bool:
    """Hedef pencereyi öne getirir (Windows odak çalma korumasına uygun AttachThreadInput yöntemiyle)."""
    if not IS_WINDOWS or not hwnd:
        return False
    fg = user32.GetForegroundWindow()  # pragma: no cover
    if fg == hwnd:
        return True
    kernel32 = ctypes.WinDLL("kernel32")
    cur = kernel32.GetCurrentThreadId()
    other = user32.GetWindowThreadProcessId(fg, None)
    attached = bool(other and other != cur and user32.AttachThreadInput(cur, other, True))
    try:
        user32.ShowWindow(hwnd, 9 if user32.IsIconic(hwnd) else 5)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(cur, other, False)
    return user32.GetForegroundWindow() == hwnd


def perform_to(hwnd: int, steps, timeout: float = 1.2) -> bool:
    """GÜVENLİK: Yalnızca hedef pencere gerçekten öndeyse yazar; değilse hiçbir tuş göndermez ve False döner.
    Böylece parola yanlışlıkla başka bir pencereye (ör. sohbet kutusu) yazılmaz."""
    if not IS_WINDOWS or not hwnd:
        return False
    end = time.time() + timeout
    while time.time() < end:  # pragma: no cover
        if activate(hwnd) and foreground()[0] == hwnd:
            time.sleep(0.12)
            if foreground()[0] != hwnd:
                return False
            for kind, val in steps:
                if foreground()[0] != hwnd:  # yazarken odak değişirse dur
                    return False
                (type_text(val) if kind == "text" else press(val))
                time.sleep(0.03)
            return True
        time.sleep(0.08)
    return False


def _send(events):  # pragma: no cover - Windows
    arr = (INPUT * len(events))(*events)
    user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))


def _key(vk=0, scan=0, flags=0):  # pragma: no cover - Windows
    return INPUT(type=INPUT_KEYBOARD, u=_U(ki=KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)))


def type_text(text: str, delay: float = 0.004) -> bool:
    if not IS_WINDOWS:
        return False
    for ch in text:  # pragma: no cover
        units = ch.encode("utf-16-le")
        for i in range(0, len(units), 2):
            code = int.from_bytes(units[i:i + 2], "little")
            _send([_key(scan=code, flags=KEYEVENTF_UNICODE), _key(scan=code, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)])
        time.sleep(delay)
    return True


def press(vk: int) -> bool:
    if not IS_WINDOWS:
        return False
    _send([_key(vk=vk), _key(vk=vk, flags=KEYEVENTF_KEYUP)])  # pragma: no cover
    return True


def sequence(entry, mode: str = "both", submit: bool = False) -> list[tuple]:
    """Yazılacak adımlar (test edilebilir): ('text', s) / ('key', vk)."""
    steps = []
    if mode in ("both", "user") and entry.username:
        steps.append(("text", entry.username))
        if mode == "both":
            steps.append(("key", VK_TAB))
    if mode in ("both", "pass"):
        steps.append(("text", entry.password))
    if submit:
        steps.append(("key", VK_RETURN))
    return steps


def perform(steps) -> bool:
    ok = True
    for kind, val in steps:
        ok &= type_text(val) if kind == "text" else press(val)
        time.sleep(0.03)
    return ok
