"""Renk belirteçleri ve platforma göre çözülen yazı tipleri."""
from __future__ import annotations

import tkinter.font as tkfont

# Obsidiyen / amber / camgöbeği kimlik — 6.5 rafine paleti
BG = "#070c13"
SIDEBAR = "#0a111b"
PANEL = "#0f1a27"
PANEL_2 = "#152335"
PANEL_3 = "#1b2d42"
INPUT = "#0a131e"
LINE = "#22364b"
LINE_2 = "#2f4a63"
FG = "#e9f0f7"
FG_2 = "#c3d1df"
MUTED = "#8a9db1"
DIM = "#5d7186"
AMBER = "#f4b65e"
AMBER_2 = "#ffd08a"
CYAN = "#62d9e8"
GREEN = "#7bd8a7"
RED = "#ff7777"
VIOLET = "#b59cff"
ORANGE = "#ff9e5e"
SELECT = "#25415a"

TIER_COLORS = [RED, ORANGE, AMBER, GREEN, CYAN]
STRENGTH_COLORS = {"red": RED, "orange": ORANGE, "amber": AMBER, "green": GREEN, "cyan": CYAN}
ADVICE_COLORS = {"critical": RED, "high": ORANGE, "medium": AMBER, "low": CYAN, "info": MUTED}
LEVEL_COLORS = {"success": GREEN, "info": CYAN, "warning": AMBER, "error": RED}
CATEGORY_COLORS = {"codec": AMBER, "analysis": GREEN, "vault": CYAN,
                   "identity": VIOLET, "file": "#8fb8ff", "system": MUTED}

F: dict[str, tuple] = {}


def _pick(available: set[str], *names: str) -> str | None:
    for name in names:
        if name in available:
            return name
    return None


def init_fonts(root) -> dict[str, tuple]:
    available = set(tkfont.families(root))
    regular = _pick(available, "Segoe UI", "Inter", "Noto Sans", "DejaVu Sans") or "TkDefaultFont"
    semibold = _pick(available, "Segoe UI Semibold")
    black = _pick(available, "Segoe UI Black")
    mono = _pick(available, "Cascadia Mono", "Cascadia Code", "Consolas", "JetBrains Mono",
                 "DejaVu Sans Mono") or "TkFixedFont"

    def strong(size):
        return (semibold, size) if semibold else (regular, size, "bold")

    F.update({
        "brand": (black, 15) if black else (regular, 15, "bold"),
        "display": strong(24), "h1": strong(17), "h2": strong(13), "h3": strong(11),
        "metric": strong(20), "body": (regular, 10), "small": (regular, 9), "tiny": (regular, 8),
        "body_b": strong(10), "button": strong(9), "button_sm": strong(8),
        "label": (mono, 8, "bold"), "mono": (mono, 10), "mono_sm": (mono, 9), "mono_xs": (mono, 8),
        "mono_b": (mono, 9, "bold"), "letter": strong(18),
    })
    return F


def mix(c1: str, c2: str, t: float) -> str:
    """İki hex rengi karıştır (t=0 → c1, t=1 → c2)."""
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))
