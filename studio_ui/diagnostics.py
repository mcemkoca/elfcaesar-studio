"""Hata bildirimi için tanı raporu. İÇERİK İÇERMEZ: parola, mesaj, dosya adı, kişi, kasa yolu yazılmaz."""
from __future__ import annotations

import platform
import sys
import time

BETA_URL = "https://claude.ai/artifact/UK9QFQfT4DWdBPTAP2ZKgb"


def report(app=None) -> str:
    from .version import APP_VERSION, APP_BUILD
    from . import runtime
    lines = [f"ElfCaesar Studio {APP_VERSION} (yapı {APP_BUILD})",
             f"Tarih: {time.strftime('%d.%m.%Y %H:%M')}",
             f"Sistem: {platform.system()} {platform.release()} · {platform.version()} · {platform.machine()}",
             f"Paket: {'kurulu' if runtime.is_frozen() else 'geliştirici'} · Python {sys.version.split()[0]}"]
    if app is not None:
        try:
            lines.append(f"Ekran: {app.winfo_screenwidth()}×{app.winfo_screenheight()} · ölçek {app.winfo_fpixels('1i') / 96:.2f}")
            p = app.prefs
            lines.append("Ayarlar: " + ", ".join(f"{k}={p.get(k)}" for k in (
                "ui_mode", "capture_shield", "hotkeys", "radar", "clipboard_guard", "idle_lock_minutes")))
            lines.append(f"Güvenlik: {app.assessment['tier_name']} {app.assessment['score']} · eşleşen tarayıcı: {len(p.get('browser_keys') or [])}")
            lines.append(f"Parola kasası: {'açık' if app.__dict__.get('_pv') is not None and app.pv.is_open else 'kapalı'}")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"(uygulama bilgisi alınamadı: {type(exc).__name__})")
    try:
        import json
        st = json.loads((runtime.local_data_dir() / "selftest.json").read_text(encoding="utf-8"))
        bad = [k for k, v in st.get("checks", {}).items() if v is False or k.endswith("_error")]
        lines.append(f"Son sistem denetimi ({st.get('version')}): {'BAŞARILI' if st.get('ok') else 'SORUNLU'}" + (f" · {', '.join(bad)}" if bad else ""))
    except (OSError, ValueError):
        lines.append("Son sistem denetimi: yok")
    try:
        logs = sorted((runtime.local_data_dir() / "logs").glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
        for lp in logs:
            last = [l for l in lp.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()][-1:]
            lines.append(f"Hata günlüğü {time.strftime('%d.%m %H:%M', time.localtime(lp.stat().st_mtime))}: {last[0].split(':')[0][:80] if last else '-'} (yalnızca hata türü)")
    except OSError:
        pass
    if app is not None:
        try:
            errs = [a for a in app.log.items() if a.level == "error"][-5:]
            for a in errs:
                lines.append(f"Uygulama hatası: {a.category} · {a.title}")
        except Exception:  # noqa: BLE001
            pass
    lines.append("— Bu rapor parola, mesaj, dosya adı veya kişi bilgisi içermez. —")
    return "\n".join(lines)
