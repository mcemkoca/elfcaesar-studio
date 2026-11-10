"""Parola kırılma süresi tahmini: saldırı senaryoları ve yöntemleri.

Tahminler bilgilendirme amaçlıdır; varsayılan saldırgan hızları açıkça gösterilir.
ElfCaesar kasası scrypt (N=2^15, r=8, p=1) kullanır: her tahmin ~32 MB bellek ve
belirgin işlem süresi ister. Bu, sızan hızlı özetlere (MD5/NTLM) kıyasla tahmin hızını
milyonlarca kat düşürür. Parolanın kendisi saklanmaz; yalnızca seviye tahmini kullanılır.
"""
from __future__ import annotations

import math
import re

from .security import password_strength, _COMMON, _SEQUENCES

SECONDS_PER_YEAR = 365.25 * 24 * 3600
UNIVERSE_AGE_YEARS = 1.38e10

# (anahtar, ad, açıklama, saniyedeki tahmin)
SCENARIOS = [
    ("online_limited", "Çevrim içi · hız sınırlı", "Hesap kilidi veya gecikmesi olan giriş ekranı", 100 / 3600),
    ("online_fast", "Çevrim içi · korumasız", "Hız sınırı olmayan bir çevrim içi servis", 10),
    ("vault_1gpu", "ElfCaesar kasası · 1 GPU", "scrypt N=2¹⁵ r=8 · tek üst düzey ekran kartı", 3.5e3),
    ("vault_farm", "ElfCaesar kasası · 1.000 GPU", "Büyük bir saldırı çiftliği", 3.5e6),
    ("fast_hash", "Sızan hızlı özet · 1 GPU", "MD5/NTLM gibi korumasız özet (karşılaştırma)", 1e11),
]

METHODS = [
    ("brute", "Kaba kuvvet", "Tüm karakter kombinasyonlarını sırayla dener."),
    ("dictionary", "Sözlük saldırısı", "Sık kullanılan parolalar ve kelime listeleriyle dener."),
    ("hybrid", "Hibrit / kural tabanlı", "Kelimelere rakam, yıl, sembol ekler; harf değiştirir (a→@, o→0)."),
    ("pattern", "Örüntü / klavye dizisi", "abcd, 1234, qwerty, tekrarlar ve tarih gibi kalıpları önceliklendirir."),
    ("stuffing", "Sızıntı listesi (credential stuffing)", "Başka sitelerden sızmış parolaları dener; yeniden kullanılan parolalar risklidir."),
]


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return "anında"
    if seconds < 60:
        return f"{round(seconds)} saniye"
    if seconds < 3600:
        return f"{round(seconds / 60)} dakika"
    if seconds < 86400:
        return f"{round(seconds / 3600)} saat"
    if seconds < SECONDS_PER_YEAR / 12:
        return f"{round(seconds / 86400)} gün"
    if seconds < SECONDS_PER_YEAR:
        return f"{round(seconds / (SECONDS_PER_YEAR / 12))} ay"
    years = seconds / SECONDS_PER_YEAR
    if years > UNIVERSE_AGE_YEARS:
        return "evrenin yaşından uzun"
    for value, name in ((1e9, "milyar yıl"), (1e6, "milyon yıl"), (1e3, "bin yıl")):
        if years >= value:
            n = years / value
            return f"{n:,.1f} {name}".replace(",", "X").replace(".", ",").replace("X", ".") if n < 10 else f"{round(n):,} {name}".replace(",", ".")
    return f"{round(years)} yıl"


def risk_level(seconds: float) -> str:
    """kritik < 1 gün ≤ zayıf < 1 yıl ≤ orta < 1.000 yıl ≤ güçlü < 1 milyon yıl ≤ çok güçlü"""
    years = seconds / SECONDS_PER_YEAR
    if seconds < 86400:
        return "critical"
    if years < 1:
        return "weak"
    if years < 1e3:
        return "fair"
    if years < 1e6:
        return "strong"
    return "excellent"


def estimate(password: str) -> dict:
    """Ortalama kırılma süresi = 2^(bit-1) / hız (anahtar uzayının yarısı)."""
    s = password_strength(password)
    bits = s["bits"]
    guesses = 2 ** max(0.0, bits - 1)
    rows = []
    for key, name, desc, rate in SCENARIOS:
        secs = guesses / rate
        rows.append({"key": key, "name": name, "desc": desc, "rate": rate, "seconds": secs,
                     "text": format_duration(secs), "risk": risk_level(secs)})
    return {"bits": bits, "guesses": guesses, "strength": s, "scenarios": rows, "methods": method_risks(password)}


def method_risks(password: str) -> list[dict]:
    low = password.casefold()
    common = any(w in low for w in _COMMON)
    seq = any(seq[i:i + 4] in low or seq[i:i + 4][::-1] in low for seq in _SEQUENCES for i in range(len(seq) - 3))
    year = bool(re.search(r"(19|20)\d{2}", password))
    repeat = bool(re.search(r"(.)\1{2,}", password))
    word_plus_digits = bool(re.fullmatch(r"[^\W\d_]+[\d!.?*_@#-]{1,6}", password))
    short = len(password) < 12
    out = []
    for key, name, desc in METHODS:
        if key == "brute":
            level, why = ("high", "12 karakterden kısa") if short else (("medium", "16 karakterden kısa") if len(password) < 16 else ("low", "uzunluk yeterli"))
        elif key == "dictionary":
            level, why = ("high", "bilinen kelime/parola içeriyor") if common else ("low", "bilinen parola bulunmadı")
        elif key == "hybrid":
            level, why = ("high", "kelime + rakam/sembol kalıbı") if word_plus_digits or (common and year) else ("low", "basit ek kalıbı yok")
        elif key == "pattern":
            hits = [t for t, v in (("sıralı dizi", seq), ("yıl", year), ("tekrar", repeat)) if v]
            level, why = ("high" if len(hits) > 1 else "medium", ", ".join(hits)) if hits else ("low", "örüntü bulunmadı")
        else:
            from .leaks import check as _leak
            hit = _leak(password)
            level, why = (("high", f"sızıntı listelerinde “{hit['base']}” tabanı (#{hit['rank']})") if hit else
                          ("medium", "listelerde yok; yine de başka yerde kullanma"))
        out.append({"key": key, "name": name, "desc": desc, "level": level, "why": why})
    return out


def elfc2_crack() -> dict:
    """ELFC2 bir şifreleme değildir: 29 kaydırma anında denenir."""
    return {"guesses": 29, "text": "anında", "note": "ELFC2 yalnızca kodlamadır; Kaydırma Analizi 29 olasılığı bir saniyenin altında listeler."}


def bits_needed(years: float, rate: float) -> float:
    return math.log2(years * SECONDS_PER_YEAR * rate) + 1


# ------------------------------------------------------------------ saldırgan donanımı (6.8.2)
# Yaklaşık hızlar: scrypt (N=2^15, r=8, p=1) ve MD5. Maliyet: saatlik kiralama/işletme (USD), varsayımdır.
HARDWARE = {
    "rtx3060": {"name": "Ev bilgisayarı", "gear": "1× RTX 3060", "vault": 1.2e3, "md5": 2.5e10, "usd_hour": None},
    "rtx4090": {"name": "Oyun bilgisayarı", "gear": "1× RTX 4090", "vault": 3.5e3, "md5": 1.6e11, "usd_hour": None},
    "cloud": {"name": "Bulut kiralama", "gear": "8× H100 sunucu", "vault": 3.6e4, "md5": 1.6e12, "usd_hour": 30.0},
    "farm": {"name": "Saldırı çiftliği", "gear": "1.000× RTX 4090", "vault": 3.5e6, "md5": 1.6e14, "usd_hour": 400.0},
}
HARDWARE_ORDER = ["rtx3060", "rtx4090", "cloud", "farm"]
WORLD_GDP_USD = 1.1e14


def format_money(usd: float) -> str:
    if usd < 1:
        return "1 dolardan az"
    if usd > WORLD_GDP_USD:
        return "dünya ekonomisinin yıllık hacminden fazla"
    for value, name in ((1e12, "trilyon"), (1e9, "milyar"), (1e6, "milyon"), (1e3, "bin")):
        if usd >= value:
            n = usd / value
            return (f"{n:.1f}".replace(".", ",") if n < 10 else f"{round(n):,}".replace(",", ".")) + f" {name} $"
    return f"{round(usd)} $"


def estimate_hw(password: str, hardware: str = "rtx4090") -> dict:
    """Seçilen saldırgan donanımına göre: çevrim içi ×2, ElfCaesar kasası, sızan MD5 (+ kiralama maliyeti)."""
    hw = HARDWARE.get(hardware, HARDWARE["rtx4090"])
    s = password_strength(password)
    guesses = 2 ** max(0.0, s["bits"] - 1)
    specs = [("online_limited", SCENARIOS[0][1], SCENARIOS[0][2], SCENARIOS[0][3], False),
             ("online_fast", SCENARIOS[1][1], SCENARIOS[1][2], SCENARIOS[1][3], False),
             ("vault_hw", "ElfCaesar kasası", f"scrypt N=2¹⁵ r=8 · {hw['gear']}", hw["vault"], True),
             ("md5_hw", "Sızan hızlı özet (MD5)", f"Korumasız özet, karşılaştırma · {hw['gear']}", hw["md5"], True)]
    rows = []
    for key, name, desc, rate, costly in specs:
        secs = guesses / rate
        cost = secs / 3600 * hw["usd_hour"] if costly and hw["usd_hour"] else None
        rows.append({"key": key, "name": name, "desc": desc, "rate": rate, "seconds": secs, "text": format_duration(secs),
                     "risk": risk_level(secs), "cost": cost, "cost_text": format_money(cost) if cost is not None else None})
    return {"bits": s["bits"], "strength": s, "hardware": hardware, "hw": hw, "scenarios": rows,
            "methods": method_risks(password), "leak": s.get("leak")}
