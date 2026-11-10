"""Parmak izinden deterministik görsel mühür (identicon).

Yalnızca görsel tanıma kolaylığı içindir; güvenlik doğrulaması parmak izinin
tamamının ayrı kanaldan karşılaştırılmasıyla yapılmalıdır.
"""
from __future__ import annotations

import hashlib

PALETTE = ["#f4b65e", "#62d9e8", "#7bd8a7", "#c39bff", "#ff9e7a", "#8fb8ff", "#ffd36e", "#5fe0c0"]


def sigil(fingerprint: str, size: int = 7) -> dict:
    digest = hashlib.sha256(("ELFCAESAR-SIGIL\0" + fingerprint.strip().lower()).encode()).digest()
    half = (size + 1) // 2
    bits = int.from_bytes(digest, "big")
    cells = []
    for row in range(size):
        for col in range(half):
            if (bits >> (row * half + col)) & 1:
                cells.append((row, col))
                mirror = size - 1 - col
                if mirror != col:
                    cells.append((row, mirror))
    primary = PALETTE[digest[-1] % len(PALETTE)]
    secondary = PALETTE[digest[-2] % len(PALETTE)]
    if secondary == primary:
        secondary = PALETTE[(digest[-2] + 3) % len(PALETTE)]
    return {"size": size, "cells": sorted(set(cells)), "primary": primary, "secondary": secondary}


def format_fingerprint(fingerprint: str, group: int = 4, per_line: int = 8) -> str:
    fp = fingerprint.strip().upper()
    groups = [fp[i:i + group] for i in range(0, len(fp), group)]
    lines = [" ".join(groups[i:i + per_line]) for i in range(0, len(groups), per_line)]
    return "\n".join(lines)


def short_fingerprint(fingerprint: str) -> str:
    fp = fingerprint.strip().upper()
    return f"{fp[:4]} {fp[4:8]} … {fp[-8:-4]} {fp[-4:]}" if len(fp) >= 16 else fp
