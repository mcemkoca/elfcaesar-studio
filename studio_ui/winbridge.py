"""Windows entegrasyonu: genel kısayollar, seçili metni kopyala/yapıştır ve Gezgin sağ tık menüsü.

Yalnızca Windows'ta etkindir; diğer sistemlerde tüm işlevler zararsız şekilde devre dışı kalır.
WhatsApp / Telegram uygulamalarının kendi sağ tık menüsüne üçüncü taraf eklenemez; bunun yerine
seçili metin üzerinde çalışan genel kısayollar kullanılır (her uygulamada çalışır).
"""
from __future__ import annotations

import os
import queue
import sys
import threading
import time
from pathlib import Path

IS_WINDOWS = os.name == "nt"
HOTKEYS = {1: ("encrypt", "Ctrl+Alt+E", 0x45), 2: ("decrypt", "Ctrl+Alt+D", 0x44), 3: ("bridge", "Ctrl+Alt+B", 0x42),
           4: ("fill", "Ctrl+Alt+P", 0x50)}
MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x0001, 0x0002, 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012
VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN = 0x11, 0x12, 0x10, 0x5B
KEYUP = 0x0002

MENU_KEYS = {
    "encrypt": (r"Software\Classes\*\shell\ElfCaesar.Encrypt", "ElfCaesar ile şifrele", "encrypt-file"),
    "decrypt": (r"Software\Classes\SystemFileAssociations\.elfvault\shell\ElfCaesar.Decrypt", "ElfCaesar ile çöz", "decrypt-file"),
    "contact": (r"Software\Classes\SystemFileAssociations\.elfcontact\shell\ElfCaesar.AddContact",
                "ElfCaesar kişi defterine ekle", "add-contact"),
}


class HotkeyListener:
    """RegisterHotKey + mesaj döngüsü ayrı iş parçacığında; olaylar kuyruğa yazılır."""

    def __init__(self):
        self.events: "queue.Queue[str]" = queue.Queue()
        self.thread = None
        self.thread_id = None
        self.registered: list[str] = []
        self.failed: list[str] = []
        self._ready = threading.Event()

    def start(self) -> bool:
        if not IS_WINDOWS:
            return False
        self.thread = threading.Thread(target=self._run, name="ElfCaesarHotkeys", daemon=True)
        self.thread.start()
        self._ready.wait(2.0)
        return bool(self.registered)

    def _run(self):  # pragma: no cover - yalnızca Windows
        import ctypes
        from ctypes import wintypes
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        self.thread_id = kernel32.GetCurrentThreadId()
        for hid, (name, label, vk) in HOTKEYS.items():
            if user32.RegisterHotKey(None, hid, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, vk):
                self.registered.append(label)
            else:
                self.failed.append(label)
        self._ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam in HOTKEYS:
                name, _label, vk = HOTKEYS[msg.wParam]
                wait_release(vk)
                self.events.put(name)
        for hid in HOTKEYS:
            user32.UnregisterHotKey(None, hid)

    def stop(self):
        if IS_WINDOWS and self.thread_id:  # pragma: no cover
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)

    def poll(self) -> list[str]:
        out = []
        while True:
            try:
                out.append(self.events.get_nowait())
            except queue.Empty:
                return out


def wait_release(vk: int, timeout: float = 1.5):  # pragma: no cover - Windows
    """Kullanıcı Ctrl/Alt'ı bırakmadan Ctrl+C göndermek Ctrl+Alt+C olur; bırakılmasını bekle."""
    import ctypes
    user32 = ctypes.windll.user32
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if not any(user32.GetAsyncKeyState(k) & 0x8000 for k in (VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, vk)):
            return
        time.sleep(0.02)


def send_ctrl(letter: str) -> bool:
    """Etkin pencereye Ctrl+<harf> gönderir (C = kopyala, V = yapıştır)."""
    if not IS_WINDOWS:
        return False
    import ctypes  # pragma: no cover
    user32 = ctypes.windll.user32
    vk = ord(letter.upper())
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYUP, 0)
    return True


def cursor_pos() -> tuple[int, int] | None:
    if not IS_WINDOWS:
        return None
    import ctypes  # pragma: no cover
    from ctypes import wintypes
    pt = wintypes.POINT()
    return (pt.x, pt.y) if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)) else None


# ------------------------------------------------------------------ Gezgin sağ tık menüsü
def launcher_command(gui_path: str | Path | None, action: str, python_exe: str | None = None) -> str:
    if getattr(sys, "frozen", False) and python_exe is None:
        return f'"{sys.executable}" --action {action} "%1"'
    exe = Path(python_exe or sys.executable)
    pyw = exe.with_name("pythonw.exe")
    runner = pyw if pyw.exists() else exe
    return f'"{runner}" "{Path(gui_path).resolve()}" --action {action} "%1"'


def context_menu_installed() -> bool:
    if not IS_WINDOWS:
        return False
    import winreg  # pragma: no cover
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CURRENT_USER, MENU_KEYS["encrypt"][0]))
        return True
    except OSError:
        return False


def install_context_menu(gui_path: str | Path, icon: str | Path | None) -> bool:
    """Yalnızca geçerli kullanıcı için (HKCU, yönetici gerekmez) menü öğelerini ekler."""
    if not IS_WINDOWS:
        return False
    import winreg  # pragma: no cover
    try:
        for key, label, action in MENU_KEYS.values():
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
                winreg.SetValueEx(k, None, 0, winreg.REG_SZ, label)
                if icon:
                    winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, str(icon))
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key + r"\command") as c:
                winreg.SetValueEx(c, None, 0, winreg.REG_SZ, launcher_command(gui_path, action))
        return True
    except OSError:
        return False


def uninstall_context_menu() -> bool:
    if not IS_WINDOWS:
        return False
    import winreg  # pragma: no cover
    ok = True
    for key, _label, _action in MENU_KEYS.values():
        for sub in (key + r"\command", key):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
            except FileNotFoundError:
                pass
            except OSError:
                ok = False
    return ok
