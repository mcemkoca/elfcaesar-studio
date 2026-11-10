"""Dijital Miras: Shamir'in Gizli Paylaşımı (GF(256)).

Kurtarma anahtarı N parçaya bölünür; herhangi K parça anahtarı geri verir, K-1 parça hiçbir bilgi vermez.
Parça biçimi: ELFMIRAS1-<k>-<n>-<no>-<base32 veri>-<CRC32 8 hane>  (elle yazılabilir, QR'a sığar)
"""
from __future__ import annotations

import base64
import secrets
import zlib

PREFIX = "ELFMIRAS1"

# GF(256) üstel/logaritma tabloları (AES polinomu 0x11B, üreteç 3)
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x ^= (_x << 1) ^ (0x11B if _x & 0x80 else 0)
    _x &= 0xFF
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a, b):
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _div(a, b):
    if b == 0:
        raise ZeroDivisionError
    return 0 if a == 0 else _EXP[(_LOG[a] - _LOG[b]) % 255]


def split(secret: bytes, k: int, n: int) -> list[tuple[int, bytes]]:
    if not 2 <= k <= n <= 10:
        raise ValueError("Eşik 2 ile parça sayısı arasında, parça sayısı en çok 10 olmalı.")
    coeffs = [[b] + [secrets.randbelow(256) for _ in range(k - 1)] for b in secret]
    shares = []
    for x in range(1, n + 1):
        out = bytearray()
        for c in coeffs:
            y = 0
            for a in reversed(c):  # Horner
                y = _mul(y, x) ^ a
            out.append(y)
        shares.append((x, bytes(out)))
    return shares


def combine(shares: list[tuple[int, bytes]]) -> bytes:
    xs = [x for x, _ in shares]
    if len(set(xs)) != len(xs):
        raise ValueError("Aynı parça iki kez verildi.")
    length = len(shares[0][1])
    out = bytearray()
    for i in range(length):
        acc = 0
        for j, (xj, yj) in enumerate(shares):
            num = den = 1
            for m, (xm, _y) in enumerate(shares):
                if m != j:
                    num = _mul(num, xm)
                    den = _mul(den, xm ^ xj)
            acc ^= _mul(yj[i], _div(num, den))
        out.append(acc)
    return bytes(out)


def encode_share(k: int, n: int, x: int, data: bytes) -> str:
    body = base64.b32encode(data).decode().rstrip("=")
    head = f"{PREFIX}-{k}-{n}-{x}-{body}"
    return f"{head}-{zlib.crc32(head.encode()) & 0xFFFFFFFF:08X}"


def decode_share(text: str) -> tuple[int, int, int, bytes]:
    t = "".join(text.split()).upper()
    parts = t.split("-")
    if len(parts) != 6 or parts[0] != PREFIX:
        raise ValueError("Miras parçası tanınmadı.")
    head = "-".join(parts[:5])
    if f"{zlib.crc32(head.encode()) & 0xFFFFFFFF:08X}" != parts[5]:
        raise ValueError("Parça yanlış yazılmış (sağlama tutmuyor).")
    k, n, x = int(parts[1]), int(parts[2]), int(parts[3])
    body = parts[4]
    data = base64.b32decode(body + "=" * (-len(body) % 8))
    return k, n, x, data


def split_text(secret: bytes, k: int, n: int) -> list[str]:
    return [encode_share(k, n, x, d) for x, d in split(secret, k, n)]


def combine_text(texts: list[str]) -> bytes:
    decoded = [decode_share(t) for t in texts if t.strip()]
    if not decoded:
        raise ValueError("Parça girilmedi.")
    k = decoded[0][0]
    if any(d[0] != k for d in decoded):
        raise ValueError("Parçalar farklı miras setlerinden.")
    if len(decoded) < k:
        raise ValueError(f"Bu miras için en az {k} parça gerekir; {len(decoded)} parça girildi.")
    return combine([(d[2], d[3]) for d in decoded[:k]])
