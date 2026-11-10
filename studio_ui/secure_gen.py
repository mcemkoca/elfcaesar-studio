"""Güçlü rastgele parola üretici (site parolaları için): 20 karakter, karışık, okunması karışan harfler hariç."""
from __future__ import annotations

import secrets
import string

_AMBIG = set("Il1O0o")
LOWER = "".join(c for c in string.ascii_lowercase if c not in _AMBIG)
UPPER = "".join(c for c in string.ascii_uppercase if c not in _AMBIG)
DIGITS = "".join(c for c in string.digits if c not in _AMBIG)
SYMBOLS = "!#$%&*+-=?@^_"


def random_password(length: int = 20) -> str:
    pools = [LOWER, UPPER, DIGITS, SYMBOLS]
    allc = "".join(pools)
    while True:
        pw = [secrets.choice(p) for p in pools] + [secrets.choice(allc) for _ in range(length - len(pools))]
        secrets.SystemRandom().shuffle(pw)
        s = "".join(pw)
        if s[0] not in SYMBOLS:
            return s
