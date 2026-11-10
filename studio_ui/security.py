"""Güvenlik zekâsı: parola seviyesi, hassas veri dedektörü, güvenlik seviyesi ve öneri seviyeleri.

Bu modül yalnızca yerel hesaplama yapar; hiçbir parola, metin veya bulgu saklanmaz.
Şifreleme motorlarını değiştirmez — yalnızca kullanıcıyı yönlendirir.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# ------------------------------------------------------------------ parola seviyesi
PASSWORD_LEVELS = [
    # (eşik bit, ad, kısa açıklama, renk anahtarı)
    (0, "Kâğıt Kalkan", "Saniyeler içinde tahmin edilebilir", "red"),
    (36, "Tahta Kalkan", "Çevrimdışı saldırıya dayanıksız", "orange"),
    (52, "Demir Kalkan", "Makul, ama daha uzun olabilir", "amber"),
    (68, "Çelik Kale", "Güçlü parola", "green"),
    (84, "Mithril Zırh", "Çok güçlü parola cümlesi", "cyan"),
]
MIN_BYTES = 12  # secure.py ile aynı alt sınır

_COMMON = {"password", "parola", "sifre", "şifre", "123456", "12345678", "123456789", "qwerty",
           "qwertyuiop", "asdfgh", "admin", "letmein", "iloveyou", "welcome", "elfcaesar",
           "galatasaray", "fenerbahce", "fenerbahçe", "besiktas", "beşiktaş", "trabzonspor",
           "abc123", "111111", "000000", "ankara", "istanbul", "izmir", "sevgilim", "askim", "aşkım"}
_SEQUENCES = ("abcdefghijklmnopqrstuvwxyz", "0123456789", "qwertyuiop", "asdfghjkl", "zxcvbnm",
              "abcçdefgğhıijklmnoöprsştuüvyz")


def _charset(pw: str) -> int:
    size = 0
    if re.search(r"[a-zçğıöşü]", pw):
        size += 32
    if re.search(r"[A-ZÇĞİÖŞÜ]", pw):
        size += 32
    if re.search(r"\d", pw):
        size += 10
    if re.search(r"[^\w\s]", pw):
        size += 33
    if " " in pw:
        size += 1
    if any(ord(c) > 0x2FF for c in pw):
        size += 64
    return max(size, 1)


def _penalties(pw: str) -> tuple[float, list[str]]:
    low = pw.casefold()
    factor, notes = 1.0, []
    if any(word in low for word in _COMMON):
        factor *= 0.45
        notes.append("Çok bilinen bir kelime veya dizi içeriyor")
    if re.search(r"(.)\1{2,}", pw):
        factor *= 0.8
        notes.append("Aynı karakter art arda tekrarlanıyor")
    for seq in _SEQUENCES:
        for i in range(len(seq) - 3):
            if seq[i:i + 4] in low or seq[i:i + 4][::-1] in low:
                factor *= 0.8
                notes.append("Klavye veya alfabe sırası var (abcd, 1234, qwer)")
                break
        else:
            continue
        break
    if re.search(r"(19|20)\d{2}", pw):
        factor *= 0.9
        notes.append("Yıl gibi tahmin edilebilir bir sayı içeriyor")
    if len(set(low)) <= max(3, len(low) // 4):
        factor *= 0.7
        notes.append("Karakter çeşitliliği çok düşük")
    return factor, notes


def password_strength(pw: str) -> dict:
    """Parolayı 0–4 seviyede değerlendirir. Parola saklanmaz, yalnızca analiz edilir."""
    if not pw:
        return {"level": 0, "score": 0, "bits": 0.0, "name": PASSWORD_LEVELS[0][1],
                "summary": "Parola girilmedi", "color": "red", "meets_min": False,
                "hints": ["En az 12 karakterlik bir parola cümlesi gir"]}
    parts = [p for p in re.split(r"[\s\-_.,;:/+]+", pw) if p]
    factor, hints = _penalties(pw)
    if len(parts) >= 4 and all(p.isalpha() and len(p) >= 3 for p in parts):
        # Kelime tabanlı parola cümlesi: kelime başına ~12 bit (insan seçimi varsayımı)
        extra = sum(bool(re.search(rx, pw)) for rx in (r"[A-ZÇĞİÖŞÜ]", r"\d", r"[^\w\s\-_.,;:/+]"))
        bits = (len(parts) * 12 + extra * 4) * factor
    else:
        # Rastgele karakter varsayımı iyimserdir; insan seçimine karşı %25 temkin payı
        bits = len(pw) * math.log2(_charset(pw)) * 0.75 * factor
    from .leaks import check as _leak_check
    leak = _leak_check(pw)
    if leak and leak["bits"] < bits:
        bits = leak["bits"]
        hints.insert(0, f"Yaygın/sızmış parola listesinde: “{leak['base']}” (#{leak['rank']:,} sırada)".replace(",", "."))
    meets_min = len(pw.encode("utf-8")) >= MIN_BYTES
    level = 0
    for i, (threshold, *_rest) in enumerate(PASSWORD_LEVELS):
        if bits >= threshold:
            level = i
    if not meets_min:
        level = min(level, 1)
        hints.insert(0, f"Kasa en az {MIN_BYTES} bayt ister; şu an {len(pw.encode('utf-8'))}")
    if len(pw) < 16 and meets_min:
        hints.append("16+ karakter veya 4+ kelimelik parola cümlesi daha güçlüdür")
    if _charset(pw) <= 42 and len(parts) < 4:
        hints.append("Büyük harf, rakam ve sembol karıştır ya da kelime sayısını artır")
    _t, name, summary, color = PASSWORD_LEVELS[level]
    score = max(0, min(100, round(bits / 100 * 100)))
    return {"level": level, "score": score, "bits": round(bits, 1), "name": name, "summary": summary,
            "color": color, "meets_min": meets_min, "hints": list(dict.fromkeys(hints))[:4], "leak": leak}


# ------------------------------------------------------------------ hassas veri dedektörü
def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for d in reversed(digits):
        n = int(d)
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alt = not alt
    return total % 10 == 0


def _tc_kimlik(d: str) -> bool:
    if len(d) != 11 or d[0] == "0":
        return False
    n = [int(c) for c in d]
    ten = ((sum(n[0:9:2]) * 7) - sum(n[1:8:2])) % 10
    return ten == n[9] and sum(n[:10]) % 10 == n[10]


def scan_sensitive(text: str) -> list[dict]:
    """Metindeki olası hassas veri türlerini sayar. Bulunan değerleri döndürmez."""
    findings: dict[str, int] = {}

    def add(kind):
        findings[kind] = findings.get(kind, 0) + 1

    for _m in re.finditer(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        add("email")
    for m in re.finditer(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", text, re.IGNORECASE):
        add("iban")
    for m in re.finditer(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", text):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn(digits) and not digits.startswith("90"):
            add("card")
    for m in re.finditer(r"(?<!\d)\d{11}(?!\d)", text):
        if _tc_kimlik(m.group()):
            add("tckn")
    for _m in re.finditer(r"(?<!\d)(?:\+?90[\s-]?)?0?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)", text):
        add("phone")
    for _m in re.finditer(r"\b(şifre|sifre|parola|password|pin|pass)\s*[:=]\s*\S+", text, re.IGNORECASE):
        add("secret")
    labels = {"email": "E-posta adresi", "iban": "IBAN", "card": "Kart numarası",
              "tckn": "T.C. kimlik numarası", "phone": "Telefon numarası", "secret": "Parola / PIN ifadesi"}
    order = ["secret", "card", "iban", "tckn", "phone", "email"]
    return [{"kind": k, "label": labels[k], "count": findings[k]} for k in order if k in findings]


# ------------------------------------------------------------------ güvenlik seviyesi ve öneri seviyeleri
SECURITY_TIERS = [
    (0, "Çırak", "Temel korumalar eksik"),
    (40, "Muhafız", "Önemli açıklar var"),
    (60, "Şövalye", "İyi, ama güçlendirilebilir"),
    (80, "Kale", "Güçlü yapılandırma"),
    (92, "Mithril", "Örnek güvenlik hijyeni"),
]
ADVICE_LEVELS = {  # öneri seviyesi → (sıra, etiket)
    "critical": (0, "KRİTİK"), "high": (1, "YÜKSEK"), "medium": (2, "ORTA"),
    "low": (3, "DÜŞÜK"), "info": (4, "BİLGİ"),
}


@dataclass
class SecurityState:
    crypto_ok: bool = True
    clipboard_guard: bool = True
    clipboard_seconds: int = 30
    idle_lock_minutes: int = 5
    sensitive_warning: bool = True
    last_password_level: int | None = None
    signed_sends: int = 0
    unsigned_sends: int = 0
    pinned_opens: int = 0
    unpinned_opens: int = 0
    sensitive_encodes: int = 0
    panic_used: int = 0
    contacts_total: int = 0
    contacts_verified: int = 0
    capture_shield: str = "sensitive"
    paper_backup: bool = False
    identity_known: bool = False
    password_vault: bool = False
    vault_health: int | None = None  # Parola Denetimi sağlık puanı (kasa açıkken bilinir)
    extra: dict = field(default_factory=dict)


def tier_for(score: int) -> tuple[int, str, str]:
    idx = 0
    for i, (threshold, _n, _d) in enumerate(SECURITY_TIERS):
        if score >= threshold:
            idx = i
    _t, name, desc = SECURITY_TIERS[idx]
    return idx, name, desc


def assess(state: SecurityState) -> dict:
    """Güvenlik seviyesi (0–100), kademe ve önceliklendirilmiş öneriler."""
    score = 100
    advice = []

    def issue(level, penalty, title, detail, action=None):
        nonlocal score
        score -= penalty
        advice.append({"level": level, "label": ADVICE_LEVELS[level][1], "title": title,
                       "detail": detail, "action": action, "impact": penalty})

    if not state.crypto_ok:
        issue("critical", 45, "Kasa motoru eksik",
              "cryptography paketi kurulu değil; AES-GCM, kimlik ve mesaj işlevleri çalışmaz.", "install")
    if state.last_password_level is not None and state.last_password_level <= 1:
        issue("high", 18, "Son kasa parolası zayıf",
              "Yeni kasalar için en az ‘Çelik Kale’ seviyesinde bir parola cümlesi kullan.", "password_lab")
    elif state.last_password_level == 2:
        issue("medium", 7, "Son kasa parolası orta seviyede",
              "Bir iki kelime eklemek seviyeyi ‘Çelik Kale’ye çıkarır.", "password_lab")
    if state.unpinned_opens:
        issue("high", min(16, 8 + 4 * state.unpinned_opens), "Gönderen parmak izi sabitlenmedi",
              f"{state.unpinned_opens} imzalı mesaj güvenilen kişi kartı olmadan açıldı. "
              "Kişi kartını ayrı kanaldan doğrulayıp sabitle.", "open_identity")
    if state.sensitive_encodes:
        issue("high", min(18, 10 + 4 * state.sensitive_encodes), "Hassas veri ELFC2 ile kodlandı",
              "ELFC2 şifreleme değildir. Kişisel veriler için Güvenli Kasa'yı kullan.", "open_vault")
    if not state.clipboard_guard:
        issue("medium", 10, "Pano koruması kapalı",
              "Kopyalanan parolalar ve şifreli içerik panoda kalabilir.", "enable_clipboard")
    if not state.idle_lock_minutes:
        issue("medium", 9, "Otomatik gizlilik kilidi kapalı",
              "Bilgisayar başından kalkınca açık mesajlar ekranda kalır.", "enable_idle")
    if state.unsigned_sends:
        issue("medium", min(12, 5 + 2 * state.unsigned_sends), "İmzasız kişiye özel mesaj",
              f"{state.unsigned_sends} mesaj Ed25519 imzası olmadan gönderildi; alıcı göndereni doğrulayamaz.",
              "open_vault")
    unverified = state.contacts_total - state.contacts_verified
    if unverified > 0:
        issue("medium", min(12, 4 + 2 * unverified), "Doğrulanmamış kişiler var",
              f"Kişi defterindeki {unverified} kişinin güvenlik kelimeleri henüz sesli karşılaştırılmadı.", "open_bridge")
    if not state.identity_known:
        issue("medium", 10, "Kişisel kimliğin yok",
              "Kişiye özel şifreli mesaj, dijital imza ve tarayıcı paylaşımı için kendi X25519 / Ed25519 kimliğini oluştur.",
              "create_identity")
    if not state.password_vault:
        issue("medium", 8, "Parola kasası kurulmadı",
              "Parolaların tarayıcıda veya not dosyalarında açık duruyor olabilir. Parola Kasası'nı kurup içe aktar.",
              "open_passwords")
    if state.vault_health is not None and state.vault_health < 85:
        pen = min(20, max(6, (90 - state.vault_health) // 2))
        issue("high" if state.vault_health < 60 else "medium", pen, "Parola kasasında riskli parolalar",
              f"Kasa sağlığı {state.vault_health}/100: sızmış, tekrar eden veya zayıf parolaları değiştir.", "fix_passwords")
    if state.identity_known and not state.paper_backup:
        issue("medium", 8, "Kimliğinin kâğıt yedeği yok",
              "Disk arızasında .elfid kaybolursa kimliğin geri gelmez. Kurtarma kitapçığı oluşturup kasada sakla.", "paper_backup")
    if state.capture_shield == "off":
        issue("low", 3, "Ekran görüntüsü kalkanı kapalı",
              "Ekran paylaşımı veya ekran kaydı yapan yazılımlar parola ve çözülen mesaj pencerelerini görebilir.", "enable_capture")
    if not state.sensitive_warning:
        issue("low", 4, "Hassas veri uyarısı kapalı",
              "ELFC2 kodlamasından önce e-posta, IBAN, kart gibi verileri yakalayan uyarı devre dışı.",
              "enable_sensitive")
    if state.idle_lock_minutes and state.idle_lock_minutes > 10:
        issue("low", 3, "Otomatik kilit süresi uzun", "5 dakika veya daha kısa bir süre önerilir.", "enable_idle")
    advice.append({"level": "info", "label": "BİLGİ", "title": "Parmak izini sesli veya yüz yüze karşılaştır",
                   "detail": "Görsel mühür kolay tanıma içindir; asıl doğrulama 64 karakterlik parmak izidir.",
                   "action": None, "impact": 0})
    advice.append({"level": "info", "label": "BİLGİ", "title": "Kasa dosyalarını yedekle",
                   "detail": ".elfid ve .elfvault dosyaları kaybolursa geri getirilemez; parolasız yedek tutmak güvenlidir.",
                   "action": None, "impact": 0})
    score = max(0, min(100, score))
    idx, name, desc = tier_for(score)
    advice.sort(key=lambda a: (ADVICE_LEVELS[a["level"]][0], -a["impact"]))
    actionable = [a for a in advice if a["level"] != "info"]
    return {"score": score, "tier": idx, "tier_name": name, "tier_desc": desc,
            "advice": advice, "open_issues": len(actionable),
            "next_tier": None if idx == len(SECURITY_TIERS) - 1 else SECURITY_TIERS[idx + 1]}
