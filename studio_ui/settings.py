"""Kullanıcı tercihleri (yalnızca açık/kapalı ayarlar; asla parola veya içerik değil)."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

DEFAULTS = {"clipboard_guard": True, "clipboard_seconds": 30, "idle_lock_minutes": 5,
            "sensitive_warning": True, "splash": True, "hotkeys": True, "radar": True, "burn_seconds": 60,
            "chunk_limit": 3500, "identity_path": "", "mini_topmost": True, "last_recipients": "",
            "intro_seen": False, "founder_id": "", "founder_date": "", "last_version": "", "attacker_hw": "rtx4090",
            "capture_shield": "sensitive", "paper_backup_date": "", "badges": {}, "visited": [], "pw_vault_path": "", "pw_decoy_path": "", "browser_keys": [], "ui_mode": "full"}


def settings_path() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) / "ElfCaesar" if base else Path.home() / ".elfcaesar"
    return root / "settings.json"


def load(path: Path | None = None) -> dict:
    data = copy.deepcopy(DEFAULTS)
    try:
        raw = json.loads((path or settings_path()).read_text(encoding="utf-8"))
        for key, default in DEFAULTS.items():
            if key in raw and isinstance(raw[key], type(default)):
                data[key] = raw[key]
    except (OSError, ValueError):
        pass
    return data


def save(values: dict, path: Path | None = None) -> bool:
    target = path or settings_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        clean = {k: values[k] for k in DEFAULTS if k in values}
        target.write_text(json.dumps(clean, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False
