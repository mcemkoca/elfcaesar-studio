"""Çevrimdışı yaygın / sızmış parola denetimi.

Kaynaklar (uygulamayla birlikte gelir, internete bağlanılmaz):
  • common_global.txt — SecLists “10k most common” (MIT, Daniel Miessler)
  • common_tr.txt     — Türkiye'de yaygın parola tabanları (ElfCaesar Studio)

Eşleştirme zxcvbn benzeri: tam eşleşme, Türkçe karakter katlama (ş→s), leet çözümü (@→a, 0→o …)
ve “taban kelime + sondaki ek” (galatasaray + 1905!). Tahmini tahmin sayısı, saldırganın listeyi
yaygınlık sırasıyla denediği varsayımıyla hesaplanır. Parola hiçbir yere yazılmaz.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path

def _data_dir() -> Path:
    from .runtime import resource_dir
    for cand in (resource_dir() / "studio_ui" / "data", Path(__file__).resolve().parent / "data"):
        if (cand / "common_global.txt").exists():
            return cand
    return Path(__file__).resolve().parent / "data"


DATA = _data_dir()
_TR_FOLD = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u",
                          "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"})
_LEET = str.maketrans({"@": "a", "4": "a", "3": "e", "1": "i", "!": "i", "0": "o", "$": "s", "5": "s", "7": "t", "+": "t"})
_SUFFIX = re.compile(r"^(?P<base>.*?[^\W\d_].*?)(?P<suffix>[\d\W_]{1,10})$")
_PREFIX = re.compile(r"^(?P<prefix>[\d\W_]{1,6})(?P<base>[^\W\d_].*)$")


def fold(text: str) -> str:
    return text.translate(_TR_FOLD).casefold()


@lru_cache(maxsize=1)
def _ranks() -> dict[str, int]:
    ranks: dict[str, int] = {}
    try:
        for i, line in enumerate((DATA / "common_global.txt").read_text(encoding="utf-8").splitlines(), start=1):
            w = fold(line.strip())
            if w and w not in ranks:
                ranks[w] = i
    except OSError:
        pass
    try:
        n = 0
        for line in (DATA / "common_tr.txt").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            n += 1
            w = fold(line)
            ranks[w] = min(ranks.get(w, 10 ** 9), 20 + n * 4)  # Türkçe tabanlar üst sıralarda kabul edilir
    except OSError:
        pass
    return ranks


def size() -> int:
    return len(_ranks())


def _affix_bits(affix: str) -> float:
    if not affix:
        return 0.0
    if re.fullmatch(r"(19|20)\d\d", affix):
        return math.log2(130)  # yıl
    bits = 0.0
    digits = re.findall(r"\d", affix)
    if digits:
        run = "".join(digits)
        bits += 3.0 if run in ("1", "12", "123", "1234", "12345", "123456", "0", "00", "01", "11") else len(digits) * 3.32
    bits += sum(5.0 for c in affix if not c.isdigit())
    return bits + 1.0


def check(password: str) -> dict | None:
    """Eşleşme varsa {'rank','base','kind','bits'} döner, yoksa None."""
    if not password:
        return None
    ranks = _ranks()
    best = None

    def consider(word, kind, extra_bits):
        nonlocal best
        r = ranks.get(word)
        if r is None:
            return
        bits = math.log2(r) + 1 + extra_bits
        if best is None or bits < best["bits"]:
            best = {"rank": r, "base": word, "kind": kind, "bits": round(bits, 1)}

    caps = 1.0 if password[:1].isupper() and password[1:] == password[1:].lower() else (
        0.0 if password == password.lower() else 2.0)
    low = fold(password)
    consider(low, "exact", caps)
    consider(low.translate(_LEET), "leet", caps + 1.5)
    m = _SUFFIX.match(password)
    if m:
        base = fold(m.group("base"))
        consider(base, "base+suffix", caps + _affix_bits(m.group("suffix")))
        consider(base.translate(_LEET), "leet+suffix", caps + 1.5 + _affix_bits(m.group("suffix")))
    p = _PREFIX.match(password)
    if p:
        consider(fold(p.group("base")), "prefix+base", caps + _affix_bits(p.group("prefix")) + 1)
    # tekrar: parolaparola, 123123
    half = len(low) // 2
    if len(low) % 2 == 0 and half >= 3 and low[:half] == low[half:]:
        consider(low[:half], "repeat", caps + 1)
    return best


def is_blocked(password: str, threshold_bits: float = 40.0) -> dict | None:
    """NIST SP 800-63B: bilinen/sızmış parola veya basit türevi yeni parola olarak seçilmemeli."""
    hit = check(password)
    return hit if hit and hit["bits"] < threshold_bits else None
