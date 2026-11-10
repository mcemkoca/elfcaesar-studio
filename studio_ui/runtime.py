"""Çalışma ortamı yardımcıları: paketlenmiş (PyInstaller) mod, Windows entegrasyonu, tek örnek ve çökme günlüğü.

Hiçbir mesaj, parola veya anahtar günlüğe yazılmaz; yalnızca hata türü ve kod satırları.
"""
from __future__ import annotations

import json
import os
import secrets
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

from .version import APP_VERSION, MUTEX_NAME, APP_USER_MODEL_ID

IS_WINDOWS = os.name == "nt"
_mutex_handle = None


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_dir() -> Path:
    """Varlık klasörlerinin (assets) kökü: paketlenmişse _MEIPASS, değilse proje klasörü."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def local_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    root = Path(base) / "ElfCaesar" if base else Path.home() / ".elfcaesar"
    root.mkdir(parents=True, exist_ok=True)
    return root


# ------------------------------------------------------------------ Windows entegrasyonu
def windows_setup() -> bool:
    """DPI farkındalığı, görev çubuğu kimliği ve kurulum programının tanıyacağı mutex.

    Dönüş: başka bir ElfCaesar örneği zaten çalışıyorsa True.
    """
    global _mutex_handle
    if not IS_WINDOWS:
        return False
    import ctypes  # pragma: no cover - yalnızca Windows
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass
    try:
        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
        return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return False


# ------------------------------------------------------------------ çökme günlüğü
def crash_log_path() -> Path:
    d = local_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"crash-{time.strftime('%Y%m%d')}.log"


def write_crash(exc_type, exc, tb) -> Path | None:
    """Yalnızca hata türü ve yığın izi (kod satırları) yazılır; yerel değişken değerleri yazılmaz."""
    try:
        path = crash_log_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} · ElfCaesar {APP_VERSION} · "
                    f"{'paketli' if is_frozen() else 'kaynak'} · {sys.platform} ===\n")
            f.write("".join(traceback.format_exception(exc_type, exc, tb)))
        return path
    except OSError:
        return None


# ------------------------------------------------------------------ tek örnek (sağ tık işlemleri açık pencereye gider)
def _instance_file() -> Path:
    return local_data_dir() / "instance.json"


class InstanceServer:
    """Çalışan uygulama; ikinci başlatmadan gelen komutları (yerel, belirteçli) kabul eder."""

    def __init__(self):
        self.commands: list[dict] = []
        self._lock = threading.Lock()
        self.sock = None
        self.token = secrets.token_hex(16)
        self.request_handler = None  # tarayıcı köprüsü: istek → yanıt (sunucu iş parçacığında çağrılır)

    def start(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(("127.0.0.1", 0))
            self.sock.listen(4)
            port = self.sock.getsockname()[1]
            _instance_file().write_text(json.dumps({"port": port, "token": self.token, "pid": os.getpid()}), encoding="utf-8")
            threading.Thread(target=self._serve, name="ElfCaesarInstance", daemon=True).start()
            return True
        except OSError:
            return False

    def _serve(self):
        while self.sock:
            try:
                conn, _addr = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), name="ElfCaesarConn", daemon=True).start()

    def _handle(self, conn):
        with conn:
            conn.settimeout(5)
            try:
                buf = b""
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                    try:
                        data = json.loads(buf.decode("utf-8"))
                        break
                    except ValueError:
                        if len(buf) > 1_000_000:
                            return
                if data.get("token") != self.token:
                    return
                if "request" in data:
                    handler = self.request_handler
                    resp = handler(data) if handler else {"ok": False, "error": "not_ready"}
                    conn.sendall(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
                    return
                if data.get("action") in ALLOWED_ACTIONS:
                    with self._lock:
                        self.commands.append({"action": data["action"], "path": data.get("path")})
                    conn.sendall(b"ok")
            except (OSError, ValueError, UnboundLocalError):
                pass

    def poll(self) -> list[dict]:
        with self._lock:
            out, self.commands = self.commands, []
        return out

    def stop(self):
        sock, self.sock = self.sock, None
        if sock:
            try:
                sock.close()
            except OSError:
                pass
        try:
            info = json.loads(_instance_file().read_text(encoding="utf-8"))
            if info.get("token") == self.token:
                _instance_file().unlink()
        except (OSError, ValueError):
            pass


ALLOWED_ACTIONS = {"show", "encrypt-file", "decrypt-file", "add-contact", "bridge", "background", "open-message", "lock-folder", "sign-file", "verify-sig"}


def forward_to_running(action: str | None, path: str | None) -> bool:
    """Açık bir ElfCaesar varsa komutu ona iletir ve True döner."""
    try:
        info = json.loads(_instance_file().read_text(encoding="utf-8"))
        with socket.create_connection(("127.0.0.1", int(info["port"])), timeout=1.5) as s:
            s.sendall(json.dumps({"token": info["token"], "action": action or "show", "path": path}).encode("utf-8"))
            return s.recv(8) == b"ok"
    except (OSError, ValueError, KeyError):
        return False


def request(payload: dict, timeout: float = 95.0) -> dict:
    """Çalışan uygulamaya istek gönderir ve JSON yanıtı döndürür (tarayıcı köprüsü / yerel istemciler)."""
    try:
        info = json.loads(_instance_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"ok": False, "error": "app_not_running"}
    try:
        with socket.create_connection(("127.0.0.1", int(info["port"])), timeout=3) as s:
            s.settimeout(timeout)
            s.sendall(json.dumps({**payload, "token": info["token"]}).encode("utf-8"))
            s.shutdown(socket.SHUT_WR)
            buf = b""
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
        return json.loads(buf.decode("utf-8")) if buf else {"ok": False, "error": "no_response"}
    except (OSError, ValueError, KeyError):
        return {"ok": False, "error": "app_not_running"}
