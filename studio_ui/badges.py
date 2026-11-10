"""Rozetler (başarımlar) — adları Tolkien'in Elf dillerinden (Sindarce / Quenya).

Rozet kazanmak için içerik kaydedilmez: yalnızca rozet kimliği ve kazanma tarihi settings.json'a yazılır.
"""
from __future__ import annotations

import time

# kimlik, ad, dil, anlam, başarım başlığı, nasıl kazanılır, nadirlik
BADGES = [
    ("annon", "Annon", "Sindarce", "kapı", "İlk kasa",
     "Bir dosyayı ya da mesajı parolayla AES-256-GCM kasasına kilitle.", "common"),
    ("tiw", "Tîw", "Sindarce", "harfler", "İlk Elf yazısı",
     "Kodlama ekranında bir metni ELFC2 Elf yazısına çevir.", "common"),
    ("parf", "Parf", "Sindarce", "kitap", "Kılavuz okuru",
     "Kılavuzu aç: F1 ya da herhangi bir ⓘ düğmesi.", "common"),
    ("draug", "Draug", "Sindarce", "kurt", "İz sürücü",
     "Kaydırma Analizi ile 29 olasılığı tara ve şifreli metnin izini sür.", "common"),
    ("certh", "Certh", "Sindarce", "rün", "Rün bilgini",
     "Sindarin · Tengwar ve Alfabe Laboratuvarı ekranlarının ikisini de ziyaret et.", "common"),
    ("istar", "Istar", "Quenya", "büyücü", "Parola büyücüsü",
     "Yerel parola üreticisiyle güçlü bir parola cümlesi üret.", "common"),
    ("galadh", "Galadh", "Sindarce", "ağaç", "Kökleri derinde",
     "Uygulamanın en az 8 farklı bölümünü keşfet.", "rare"),
    ("ithildin", "Ithildin", "Sindarce", "ay-yıldız gümüşü", "Kimlik sahibi",
     "Kendi X25519 / Ed25519 kimliğini oluştur ya da kimlik oturumu aç.", "rare"),
    ("thoron", "Thoron", "Sindarce", "kartal", "Kartalların ulağı",
     "Bir kişiye uçtan uca şifreli mesaj gönder (Mesaj Köprüsü veya kişiye şifrele).", "rare"),
    ("lasse", "Lassë", "Quenya", "yaprak", "Mühür sahibi",
     "Bir dosyayı kimliğinle dijital olarak imzala.", "rare"),
    ("elen", "Elen", "Sindarce · Quenya", "yıldız", "Yol gösteren yıldız",
     "KVKK Kalkanı ile bir klasörde kişisel veri taraması yap.", "rare"),
    ("elessar", "Elessar", "Quenya", "elf taşı", "Taş muhafızı",
     "Bütün bir klasörü Araç Kutusu'nda tek kasaya kilitle.", "rare"),
    ("tirith", "Tirith", "Sindarce", "nöbet", "Nöbetçi",
     "Ekran görüntüsü kalkanını TÜM UYGULAMA yap ve otomatik kilidi açık tut.", "epic"),
    ("mithril", "Mithril", "Sindarce", "gri parıltı", "Mithril zırh",
     "Güvenlik seviyesi 92+, kimliğin hazır ve kâğıt kurtarma kitapçığın basılmış olsun.", "epic"),
    ("aran", "Aran", "Sindarce", "kral", "Elflerin kralı",
     "Diğer 14 rozetin hepsini topla.", "legendary"),
]
BY_ID = {b[0]: b for b in BADGES}
RARITY = {"common": ("YAYGIN", "#8a9db1"), "rare": ("NADİR", "#62d9e8"), "epic": ("DESTANSI", "#b59cff"),
          "legendary": ("EFSANEVİ", "#f4b65e")}

# başarılı bildirim başlığı → rozet
EVENT_RULES = [
    ("Dosya kasaya alındı", "annon"), ("Mesaj şifrelendi", "annon"),
    ("Kodlama tamamlandı", "tiw"),
    ("29 kaydırma analiz edildi", "draug"),
    ("Parola üretildi", "istar"),
    ("Kimlik oluşturuldu", "ithildin"), ("Kimlik oturumu açıldı", "ithildin"), ("Kimlik geri yüklendi", "ithildin"),
    ("Sohbet mesajı şifrelendi", "thoron"), ("Mesaj yerinde şifrelendi", "thoron"), ("Alıcıya özel mesaj paketi", "thoron"),
    ("Dosya imzalandı", "lasse"),
    ("KVKK taraması tamamlandı", "elen"),
    ("Klasör kasası oluşturuldu", "elessar"),
]


def for_event(title: str) -> list[str]:
    return [bid for prefix, bid in EVENT_RULES if title.startswith(prefix)]


def state_badges(prefs: dict, score: int) -> list[str]:
    """Ayarlardan / durumdan türeyen rozetler."""
    out = []
    visited = set(prefs.get("visited") or [])
    if len(visited) >= 8:
        out.append("galadh")
    if {"tengwar", "alphabet"} <= visited:
        out.append("certh")
    if prefs.get("capture_shield") == "all" and int(prefs.get("idle_lock_minutes") or 0) > 0:
        out.append("tirith")
    if score >= 92 and prefs.get("identity_path") and prefs.get("paper_backup_date"):
        out.append("mithril")
    earned = set((prefs.get("badges") or {}).keys())
    if len((earned | set(out)) - {"aran"}) >= len(BADGES) - 1:
        out.append("aran")
    return out


def award(prefs: dict, badge_id: str) -> bool:
    """Yeni kazanıldıysa True. prefs['badges'] = {kimlik: 'gg.aa.yyyy'}"""
    got = prefs.setdefault("badges", {})
    if badge_id in got or badge_id not in BY_ID:
        return False
    got[badge_id] = time.strftime("%d.%m.%Y")
    return True


def progress(prefs: dict) -> tuple[int, int]:
    return len([b for b in (prefs.get("badges") or {}) if b in BY_ID]), len(BADGES)
