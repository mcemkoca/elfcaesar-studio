"""KVKK maskeli kopya: belgedeki kişisel verileri maskeleyerek paylaşılabilir kopya üretir.

Orijinal dosyaya dokunulmaz; yanına "<ad>.maskeli.<uzantı>" yazılır. Desteklenen: metin tabanlı dosyalar
(TXT, CSV, TSV, JSON, XML, MD, LOG, EML, HTML, VCF). Maskeleme stili: kısmi (son haneler görünür) veya tam.
"""
from __future__ import annotations

import re
from pathlib import Path

from .kvkk import TEXT_EXT
from .security import _luhn, _tc_kimlik

MASK = "•"


def _keep_last(s: str, n: int) -> str:
    """Rakam/harfleri maskeler, ayırıcıları korur; son n anlamlı karakteri bırakır."""
    sig = [i for i, c in enumerate(s) if c.isalnum()]
    keep = set(sig[-n:]) if n else set()
    return "".join(c if (i in keep or not c.isalnum()) else MASK for i, c in enumerate(s))


def mask_text(text: str, style: str = "partial") -> tuple[str, dict]:
    counts: dict[str, int] = {}
    full = style == "full"

    def bump(k):
        counts[k] = counts.get(k, 0) + 1

    def email(m):
        bump("email")
        user, dom = m.group(1), m.group(2)
        return (MASK * 6 if full else user[:1] + MASK * max(len(user) - 1, 2)) + "@" + dom

    text = re.sub(r"([\w.+-]+)@([\w-]+\.[\w.-]+)", email, text)

    def iban(m):
        bump("iban")
        return _keep_last(m.group(), 0 if full else 4)

    text = re.sub(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", iban, text, flags=re.IGNORECASE)

    def card(m):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn(digits) and not digits.startswith("90"):
            bump("card")
            return _keep_last(m.group(), 0 if full else 4)
        return m.group()

    text = re.sub(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)", card, text)

    def tckn(m):
        if _tc_kimlik(m.group()):
            bump("tckn")
            return _keep_last(m.group(), 0 if full else 3)
        return m.group()

    text = re.sub(r"(?<!\d)\d{11}(?!\d)", tckn, text)

    def phone(m):
        bump("phone")
        return _keep_last(m.group(), 0 if full else 2)

    text = re.sub(r"(?<!\d)(?:\+?90[\s-]?)?0?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)", phone, text)

    def secret(m):
        bump("secret")
        return m.group(1) + m.group(2) + MASK * 8

    text = re.sub(r"\b(şifre|sifre|parola|password|pin|pass)(\s*[:=]\s*)\S+", secret, text, flags=re.IGNORECASE)
    return text, counts


def masked_copy(path: str | Path, style: str = "partial") -> tuple[Path, dict]:
    p = Path(path)
    if p.suffix.lower() not in TEXT_EXT:
        raise ValueError(f"{p.suffix or 'Uzantısız'} dosyalar için maskeli kopya henüz desteklenmiyor (metin tabanlı dosyalar destekleniyor).")
    raw = p.read_bytes()
    for enc in ("utf-8", "cp1254", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    masked, counts = mask_text(text, style)
    out = p.with_name(f"{p.stem}.maskeli{p.suffix}")
    n = 2
    while out.exists():
        out = p.with_name(f"{p.stem}.maskeli-{n}{p.suffix}")
        n += 1
    out.write_text(masked, encoding="utf-8")
    return out, counts
