"""Parola Üretici: rastgele, heceli (söylenebilir) ve PIN; sitenin parola kurallarına uyumlu.

• Rastgelelik yalnızca `secrets` (işletim sisteminin kriptografik üreteci) ile sağlanır.
• Entropi, üretim yönteminden TAM olarak hesaplanır (tahmin değil): log2(havuz^uzunluk) ve sınıf zorunlulukları.
• Üretilen her parola, uygulamayla gelen sızıntı listesine karşı süzülür; listede bulunursa yeniden üretilir.
• Site kuralları: HTML `maxlength` / `minlength`, Apple `passwordrules` özniteliği
  (ör. "minlength: 8; maxlength: 20; required: lower; required: upper; required: digit; allowed: [-_!]")
  ve kullanıcının elle girdiği "en fazla N karakter, şu semboller" bilgisi.
"""
from __future__ import annotations

import math
import re
import secrets
from dataclasses import dataclass, field, replace

_AMBIG = set("Il1O0o|`'\"")
LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = LOWER.upper()
DIGITS = "0123456789"
SYMBOLS = "!#$%&*+-=?@^_.:"
_CONSONANTS = "bcdfghjklmnprstvyz"
_VOWELS = "aeiou"

MODES = ("random", "syllable", "pin")
MODE_LABELS = {"random": "Rastgele", "syllable": "Heceli (söylenebilir)", "pin": "PIN (yalnız rakam)"}


@dataclass
class Policy:
    mode: str = "random"
    length: int = 20          # rastgele/PIN: karakter; heceli: hece grubu sayısı ayrı (groups)
    lower: bool = True
    upper: bool = True
    digits: bool = True
    symbols: bool = True
    symbol_set: str = SYMBOLS
    avoid_ambiguous: bool = True
    groups: int = 4           # heceli: kelime-grup sayısı (her grup 2 hece = 4 harf)
    min_length: int = 0
    max_length: int = 0       # 0 = sınırsız
    required: list = field(default_factory=list)  # passwordrules "required" sınıfları

    def clamp(self) -> "Policy":
        p = replace(self)
        if p.mode not in MODES:
            p.mode = "random"
        if p.max_length and p.max_length < 4:
            p.max_length = 4
        lo = max(4 if p.mode == "pin" else 8, p.min_length or 0)
        hi = min(p.max_length or 128, 128)
        p.length = max(lo, min(int(p.length or 20), hi))
        p.groups = max(2, min(int(p.groups or 4), 8))
        if p.mode == "random" and not (p.lower or p.upper or p.digits or p.symbols):
            p.lower = True
        if not p.symbol_set:
            p.symbols = False
        return p


def _filter(chars: str, avoid: bool) -> str:
    return "".join(c for c in chars if not (avoid and c in _AMBIG))


def _pools(p: Policy) -> list[str]:
    pools = []
    if p.lower:
        pools.append(_filter(LOWER, p.avoid_ambiguous))
    if p.upper:
        pools.append(_filter(UPPER, p.avoid_ambiguous))
    if p.digits:
        pools.append(_filter(DIGITS, p.avoid_ambiguous))
    if p.symbols:
        pools.append(_filter(p.symbol_set, p.avoid_ambiguous))
    return [x for x in pools if x]


def _shuffle(items: list) -> list:
    secrets.SystemRandom().shuffle(items)
    return items


def _random(p: Policy) -> str:
    pools = _pools(p)
    allc = "".join(pools)
    while True:
        need = pools[: p.length]
        chars = [secrets.choice(x) for x in need] + [secrets.choice(allc) for _ in range(p.length - len(need))]
        s = "".join(_shuffle(chars))
        # bazı siteler sembolle başlamayı reddeder
        if p.symbols and len(pools) > 1 and s[0] in p.symbol_set:
            continue
        return s


def _syllable_group() -> str:
    return "".join(secrets.choice(_CONSONANTS) + secrets.choice(_VOWELS) for _ in range(2))


def _syllable(p: Policy) -> str:
    """Ör. 'Kavu-mirta-Selo-dene-47': 2 heceli gruplar, bir grup büyük harfle, sonda 2 rakam."""
    groups = [_syllable_group() for _ in range(p.groups)]
    cap = secrets.randbelow(p.groups)
    groups[cap] = groups[cap].capitalize()
    sep = "-" if (not p.symbol_set or "-" in p.symbol_set or not p.symbols) else p.symbol_set[0]
    tail = f"{secrets.randbelow(90) + 10}"
    s = sep.join(groups) + sep + tail
    if p.max_length and len(s) > p.max_length:
        s = s[: p.max_length]
    return s


def _pin(p: Policy) -> str:
    while True:
        s = "".join(secrets.choice(DIGITS) for _ in range(p.length))
        # kolay tahmin edilen PIN'leri ele: tek rakam tekrarı, artan/azalan dizi
        if len(set(s)) == 1 or s in "01234567890123456789" or s in "98765432109876543210":
            continue
        return s


def entropy_bits(p: Policy) -> float:
    p = p.clamp()
    if p.mode == "pin":
        return p.length * math.log2(10)
    if p.mode == "syllable":
        per_group = 2 * (math.log2(len(_CONSONANTS)) + math.log2(len(_VOWELS)))
        bits = p.groups * per_group + math.log2(p.groups) + math.log2(90)
        if p.max_length:
            full = p.groups * 5 + 2
            bits *= min(1.0, p.max_length / full)
        return bits
    pools = _pools(p)
    n = sum(len(x) for x in pools)
    return p.length * math.log2(max(n, 2))


def generate(policy: Policy | None = None, check_leaks: bool = True, tries: int = 50) -> str:
    p = (policy or Policy()).clamp()
    fn = {"random": _random, "syllable": _syllable, "pin": _pin}[p.mode]
    pw = fn(p)
    if check_leaks and p.mode != "pin":
        from . import leaks
        for _ in range(tries):
            if not leaks.check(pw):
                break
            pw = fn(p)
    return pw


# ------------------------------------------------------------------ site kuralları
_CLASS = {"lower": "lower", "upper": "upper", "digit": "digits", "special": "symbols", "ascii-printable": "all",
          "unicode": "all"}


def parse_passwordrules(text: str) -> dict:
    """Apple passwordrules biçimini çözer. Döner: {minlength, maxlength, required:[...], allowed:[...], symbols}."""
    out = {"minlength": 0, "maxlength": 0, "required": [], "allowed": [], "symbols": ""}
    for part in (text or "").split(";"):
        if ":" not in part:
            continue
        key, _, val = part.partition(":")
        key, val = key.strip().lower(), val.strip()
        if key in ("minlength", "maxlength", "max-consecutive"):
            m = re.search(r"\d+", val)
            if m and key != "max-consecutive":
                out[key] = int(m.group())
            continue
        if key not in ("required", "allowed"):
            continue
        for tok in re.findall(r"\[[^\]]*\]|[\w-]+", val):
            if tok.startswith("["):
                syms = "".join(c for c in tok[1:-1] if not c.isalnum() and not c.isspace())
                out["symbols"] += syms
                tok = "special"
            cls = _CLASS.get(tok.lower())
            if cls:
                out[key].append(cls)
    out["symbols"] = "".join(dict.fromkeys(out["symbols"]))
    return out


def policy_for_site(base: Policy | None = None, *, maxlength=0, minlength=0, passwordrules: str = "",
                    pattern: str = "") -> Policy:
    """Sayfadaki parola alanının özniteliklerinden uyumlu bir Policy üretir."""
    p = replace(base or Policy())
    rules = parse_passwordrules(passwordrules)
    try:
        maxlength = int(maxlength or 0)
        minlength = int(minlength or 0)
    except (TypeError, ValueError):
        maxlength = minlength = 0
    mx = min([x for x in (maxlength, rules["maxlength"]) if x > 0], default=0)
    mn = max(minlength, rules["minlength"])
    if mx:
        p.max_length = mx
        p.length = min(p.length, mx)
    if mn:
        p.min_length = mn
        p.length = max(p.length, mn)
    if pattern and re.fullmatch(r"\^?\\d\{?\d*,?\d*\}?\$?|\^?\[0-9\]\{?\d*,?\d*\}?\$?|\^?\\d\+\$?", pattern.strip()):
        p.mode = "pin"
    classes = set(rules["required"]) | set(rules["allowed"])
    if classes and "all" not in classes:
        p.lower = "lower" in classes
        p.upper = "upper" in classes
        p.digits = "digits" in classes
        p.symbols = "symbols" in classes
        if classes == {"digits"}:
            p.mode = "pin"
    if rules["symbols"]:
        p.symbol_set = rules["symbols"]
        p.symbols = True
    p.required = rules["required"]
    return p.clamp()


def describe(p: Policy) -> str:
    p = p.clamp()
    if p.mode == "pin":
        return f"{p.length} haneli PIN"
    if p.mode == "syllable":
        return f"{p.groups} heceli grup" + (f" · en fazla {p.max_length}" if p.max_length else "")
    cls = [n for n, on in (("küçük", p.lower), ("büyük", p.upper), ("rakam", p.digits), ("sembol", p.symbols)) if on]
    s = f"{p.length} karakter · " + ", ".join(cls)
    if p.max_length:
        s += f" · site sınırı {p.max_length}"
    return s


def change_password_url(url_or_domain: str) -> str:
    """W3C 'well-known change-password' adresi: destekleyen siteler doğrudan parola değiştirme sayfasına yönlendirir."""
    from .pwvault import host_of
    host = host_of(url_or_domain) or url_or_domain.strip().strip("/")
    return f"https://{host}/.well-known/change-password" if host else ""
