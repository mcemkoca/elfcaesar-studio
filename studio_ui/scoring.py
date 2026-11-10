"""Kaydırma analizi için Türkçe benzerlik puanı (yalnızca sıralama ipucu).

Harf sıklığı profiline göre 0–100 arası bir tahmin üretir. Kısa metinlerde
yanıltıcı olabilir; kesin doğrulama değildir.
"""
from __future__ import annotations

import math

# Yaklaşık Türkçe harf sıklıkları (yüzde).
TURKISH_FREQ = {
    "a": 11.92, "b": 2.84, "c": 0.96, "ç": 1.15, "d": 4.70, "e": 8.91, "f": 0.46,
    "g": 1.25, "ğ": 1.12, "h": 1.21, "ı": 5.11, "i": 8.60, "j": 0.03, "k": 4.68,
    "l": 5.92, "m": 3.75, "n": 7.49, "o": 2.48, "ö": 0.78, "p": 0.89, "r": 6.95,
    "s": 3.01, "ş": 1.78, "t": 3.01, "u": 3.23, "ü": 1.97, "v": 0.96, "y": 3.34,
    "z": 1.50,
}
_COMMON_WORDS = {"ve", "bir", "bu", "da", "de", "için", "ile", "ne", "çok", "ama",
                 "gibi", "daha", "olan", "var", "ben", "sen", "biz", "mi", "mı", "merhaba"}


def _lower(ch: str) -> str:
    if ch == "I":
        return "ı"
    if ch == "İ":
        return "i"
    return ch.lower()


def turkish_score(text: str) -> int:
    letters = [c for c in (_lower(ch) for ch in text) if c in TURKISH_FREQ]
    if not letters:
        return 0
    counts = {k: 0 for k in TURKISH_FREQ}
    for c in letters:
        counts[c] += 1
    dot = sum(counts[k] * TURKISH_FREQ[k] for k in TURKISH_FREQ)
    na = math.sqrt(sum(v * v for v in counts.values()))
    nb = math.sqrt(sum(v * v for v in TURKISH_FREQ.values()))
    cosine = dot / (na * nb) if na and nb else 0.0
    words = [w.strip(".,;:!?\"'()").casefold() for w in text.split()]
    bonus = min(0.15, 0.05 * sum(1 for w in words if w in _COMMON_WORDS))
    # Rastgele dağılım ~0.55–0.7 civarındadır; aralığı 0–100'e yay.
    scaled = (cosine - 0.55) / 0.42
    return max(0, min(100, round((scaled + bonus) * 100)))


def rank(results: list[tuple[int, str]]) -> list[tuple[int, str, int]]:
    """(shift, text) listesini (shift, text, score) olarak döndürür; sıra korunur."""
    return [(shift, text, turkish_score(text)) for shift, text in results]


def best_shift(scored: list[tuple[int, str, int]]) -> int | None:
    if not scored:
        return None
    return max(scored, key=lambda row: (row[2], -row[0]))[0]
